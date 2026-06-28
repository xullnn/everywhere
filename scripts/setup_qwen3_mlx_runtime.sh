#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

VENV_DIR="${VENV_DIR:-.venv-mimo}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
CREATE_WITH_CONDA="${CREATE_WITH_CONDA:-auto}"
CONDA_PYTHON_VERSION="${CONDA_PYTHON_VERSION:-3.12}"
MLX_AUDIO_SOURCE="${MLX_AUDIO_SOURCE:-.external/repos/mlx-audio}"
MODEL="${MODEL:-.external/models/mlx-community__Qwen3-ASR-0.6B-8bit}"
VERIFY_MODEL_LOAD="${VERIFY_MODEL_LOAD:-0}"

python_is_preferred() {
  "$1" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if (3, 10) <= sys.version_info < (3, 13) else 1)
PY
}

python_is_usable() {
  "$1" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
}

create_runtime() {
  if [ -x "$VENV_DIR/bin/python" ]; then
    return
  fi

  if [ -e "$VENV_DIR" ]; then
    echo "Runtime path exists but has no executable Python: $VENV_DIR" >&2
    echo "Move or remove that path, then rerun this script." >&2
    exit 2
  fi

  if [ "$CREATE_WITH_CONDA" != "0" ] && command -v conda >/dev/null 2>&1 && ! python_is_preferred "$PYTHON_BIN"; then
    echo "Creating conda runtime at $VENV_DIR with Python $CONDA_PYTHON_VERSION"
    conda create -y -p "$VENV_DIR" "python=$CONDA_PYTHON_VERSION"
    return
  fi

  if ! python_is_usable "$PYTHON_BIN"; then
    echo "Python runtime must be >= 3.10 for mlx-audio: $PYTHON_BIN" >&2
    echo "Set PYTHON_BIN to Python 3.10-3.12, or install conda and rerun." >&2
    exit 2
  fi

  if ! python_is_preferred "$PYTHON_BIN"; then
    echo "Warning: $PYTHON_BIN is usable but not the previously validated Python range 3.10-3.12." >&2
    echo "Continuing because CREATE_WITH_CONDA=$CREATE_WITH_CONDA." >&2
  fi

  echo "Creating venv runtime at $VENV_DIR with $PYTHON_BIN"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
}

require_paths() {
  if [ ! -d "$MLX_AUDIO_SOURCE" ]; then
    echo "Missing mlx-audio source directory: $MLX_AUDIO_SOURCE" >&2
    exit 2
  fi
  if [ ! -d "$MODEL" ]; then
    echo "Missing Qwen3 MLX model directory: $MODEL" >&2
    exit 2
  fi
}

create_runtime
require_paths

RUNTIME_PY="$VENV_DIR/bin/python"

"$RUNTIME_PY" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("mlx-audio requires Python >= 3.10")
print(f"Using Python {sys.version.split()[0]}")
PY

"$RUNTIME_PY" -m pip install --upgrade "pip<26" "setuptools<82" wheel -i "$PIP_INDEX_URL"
"$RUNTIME_PY" -m pip install -U -i "$PIP_INDEX_URL" \
  "numpy>=1.26.4" \
  "scipy>=1.10.0" \
  "huggingface_hub>=1.0,<2.0" \
  "mlx>=0.31.1" \
  "mlx-lm>=0.31.1" \
  "miniaudio>=1.61" \
  "sounddevice>=0.5.3" \
  "tqdm>=4.67.1" \
  "sentencepiece>=0.2.0" \
  "transformers>=5.5.0,<6.0" \
  "safetensors>=0.4.0" \
  "tokenizers>=0.21.0" \
  "tiktoken>=0.7.0" \
  "protobuf>=4.25.0"

PYTHONPATH="$MLX_AUDIO_SOURCE${PYTHONPATH:+:$PYTHONPATH}" "$RUNTIME_PY" - "$MLX_AUDIO_SOURCE" "$MODEL" "$VERIFY_MODEL_LOAD" <<'PY'
import json
import sys
from pathlib import Path

source, model, verify_model_load = sys.argv[1:]
import mlx.core as mx
import numpy as np
from mlx_audio.stt import load

status = {
    "python": sys.executable,
    "mlx_audio_source": source,
    "mlx_audio_source_exists": Path(source).is_dir(),
    "model": model,
    "model_exists": Path(model).is_dir(),
    "mlx_metal_available": bool(mx.metal.is_available()),
    "numpy_version": np.__version__,
}

if verify_model_load == "1":
    loaded = load(model, lazy=True)
    status["model_class"] = type(loaded).__name__

print(json.dumps(status, ensure_ascii=False, sort_keys=True))
PY

echo "Qwen3 MLX runtime ready in $RUNTIME_PY"
echo "Run app smoke with: bash scripts/run_qwen3_mlx_app_smoke.sh"
