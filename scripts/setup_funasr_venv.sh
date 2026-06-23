#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON_BIN:-python3}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
python - <<'PY'
import sys
if sys.version_info >= (3, 13):
    raise SystemExit("FunASR runtime is not validated with Python 3.13 here. Use Python 3.10 or 3.11, e.g. PYTHON_BIN=/path/to/python3.11.")
PY
python -m pip install --upgrade "pip<26" setuptools wheel -i "$PIP_INDEX_URL"
# The FunASR websocket runtime pulls models on first use. After that cache is available offline.
# Fun-ASR-Nano additionally needs the Hugging Face/Qwen tokenizer stack.
pip install --no-cache-dir -i "$PIP_INDEX_URL" \
  "funasr" \
  "modelscope" \
  "websockets" \
  "numpy" \
  "sounddevice" \
  "torch" \
  "torchaudio" \
  "transformers>=4.51.0" \
  "accelerate" \
  "safetensors" \
  "tokenizers" \
  "tiktoken"
echo "Virtualenv ready with $(python --version). Activate with: source .venv/bin/activate"
