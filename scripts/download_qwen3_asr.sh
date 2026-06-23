#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
QWEN3_MODEL_ID="${QWEN3_MODEL_ID:-Qwen/Qwen3-ASR-0.6B}"
QWEN3_LOCAL_DIR="${QWEN3_LOCAL_DIR:-.external/models/Qwen3-ASR-0.6B}"
MAX_WORKERS="${MAX_WORKERS:-1}"
MODEL_REL_PATH="${MODEL_REL_PATH:-model.safetensors}"
EXPECTED_BYTES="${EXPECTED_BYTES:-1876091704}"
API_URL="https://www.modelscope.cn/api/v1/models/$QWEN3_MODEL_ID/repo?Revision=master&FilePath=$MODEL_REL_PATH"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Missing Python runtime: $PYTHON_BIN" >&2
  echo "Run scripts/setup_qwen3_asr_venv.sh first." >&2
  exit 1
fi

"$PYTHON_BIN" - "$QWEN3_MODEL_ID" "$QWEN3_LOCAL_DIR" "$MAX_WORKERS" "$MODEL_REL_PATH" <<'PY'
import os
import sys
from pathlib import Path

try:
    from modelscope.hub.snapshot_download import snapshot_download
except ImportError as exc:
    raise SystemExit("Missing modelscope. Run scripts/setup_funasr_venv.sh or install modelscope first.") from exc

model_id = sys.argv[1]
local_dir = Path(sys.argv[2])
max_workers = int(sys.argv[3])
model_rel_path = sys.argv[4]
local_dir.mkdir(parents=True, exist_ok=True)

print(f"Downloading {model_id} metadata to {local_dir} via ModelScope...")
resolved = snapshot_download(
    model_id=model_id,
    local_dir=str(local_dir),
    ignore_patterns=[model_rel_path],
    max_workers=max_workers,
)
model_path = Path(resolved)
print(f"Model directory: {model_path}")

required = ["config.json", "preprocessor_config.json", "tokenizer_config.json", "vocab.json"]
missing = [name for name in required if not (model_path / name).exists()]
if missing:
    raise SystemExit(f"Downloaded model is missing required files: {', '.join(missing)}")

total_size = 0
for root, _, files in os.walk(model_path):
    for name in files:
        total_size += (Path(root) / name).stat().st_size
print(f"Cached size: {total_size / (1024 ** 3):.2f} GiB")
PY

target="$QWEN3_LOCAL_DIR/$MODEL_REL_PATH"
partial="$QWEN3_LOCAL_DIR/._____temp/$MODEL_REL_PATH"
mkdir -p "$(dirname "$partial")"

if [ -f "$target" ]; then
  actual_bytes="$(wc -c < "$target" | tr -d ' ')"
  if [ "$actual_bytes" = "$EXPECTED_BYTES" ]; then
    echo "$target already exists and passed size validation."
    exit 0
  fi
  echo "Existing $target has unexpected size $actual_bytes; moving it to $partial for resume/retry." >&2
  mv "$target" "$partial"
fi

if [ -f "$partial" ]; then
  partial_bytes="$(wc -c < "$partial" | tr -d ' ')"
  if [ "$partial_bytes" -gt "$EXPECTED_BYTES" ]; then
    echo "Existing partial is larger than expected: $partial_bytes > $EXPECTED_BYTES. Remove $partial and retry." >&2
    exit 1
  fi
  echo "Resuming $MODEL_REL_PATH from $partial_bytes of $EXPECTED_BYTES bytes..."
else
  echo "Downloading $MODEL_REL_PATH from 0 of $EXPECTED_BYTES bytes..."
fi

echo "URL: $API_URL"
curl \
  --fail \
  --location \
  --continue-at - \
  --retry 30 \
  --retry-delay 5 \
  --connect-timeout 30 \
  --speed-limit 1024 \
  --speed-time 300 \
  --output "$partial" \
  "$API_URL"

actual_bytes="$(wc -c < "$partial" | tr -d ' ')"
if [ "$actual_bytes" != "$EXPECTED_BYTES" ]; then
  echo "Unexpected $MODEL_REL_PATH size: $actual_bytes bytes, expected $EXPECTED_BYTES." >&2
  exit 1
fi

mv "$partial" "$target"
echo "Downloaded Qwen3-ASR model to $QWEN3_LOCAL_DIR"
du -sh "$QWEN3_LOCAL_DIR"
