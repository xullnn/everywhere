#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
QWEN_ASR_VERSION="${QWEN_ASR_VERSION:-0.0.6}"
QWEN3_INSTALL_MODE="${QWEN3_INSTALL_MODE:-runtime}"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Missing Python runtime: $PYTHON_BIN" >&2
  echo "Run scripts/setup_funasr_venv.sh first, or set PYTHON_BIN to an existing Python in a virtualenv." >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit("qwen-asr requires Python >= 3.9.")
print(f"Using Python {sys.version.split()[0]}")
PY

"$PYTHON_BIN" -m pip install --upgrade "pip<26" "setuptools<82" wheel -i "$PIP_INDEX_URL"
if [ "$QWEN3_INSTALL_MODE" = "full" ]; then
  "$PYTHON_BIN" -m pip install -U -i "$PIP_INDEX_URL" "qwen-asr==$QWEN_ASR_VERSION"
else
  # The qwen-asr package depends on Gradio/Flask demo tools by default. The eval
  # adapter only needs the transformers backend, so keep the local runtime lean.
  "$PYTHON_BIN" -m pip install -U -i "$PIP_INDEX_URL" \
    "transformers==4.57.6" \
    "accelerate==1.12.0" \
    "nagisa==0.2.11" \
    "soynlp==0.0.493"
  "$PYTHON_BIN" -m pip install -U --no-deps -i "$PIP_INDEX_URL" "qwen-asr==$QWEN_ASR_VERSION"
fi

"$PYTHON_BIN" - <<'PY'
from qwen_asr import Qwen3ASRModel
print("qwen-asr import OK:", Qwen3ASRModel.__name__)
PY

echo "Qwen3-ASR runtime ready in $PYTHON_BIN"
