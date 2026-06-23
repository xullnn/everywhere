#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
MODEL_ID="${MODEL_ID:-FunAudioLLM/Fun-ASR-Nano-2512}"
MAX_WORKERS="${MAX_WORKERS:-1}"
MODEL_REL_PATH="${MODEL_REL_PATH:-model.pt}"
MODEL_REVISION="${MODEL_REVISION:-db823224e5c2510001b4a3d3ed97f430bd52ac88}"
EXPECTED_BYTES="${EXPECTED_BYTES:-2127426538}"
EXPECTED_SHA256="${EXPECTED_SHA256:-81fec8616083c69377f3ceef36aba3655660ee0ca69a5d4a1e9810cd340ca499}"
CACHE_ROOT="${CACHE_ROOT:-$HOME/.cache/modelscope/hub/models}"
MODEL_DIR="$CACHE_ROOT/$MODEL_ID"
TEMP_DIR="$CACHE_ROOT/._____temp/$MODEL_ID"
API_URL="https://www.modelscope.cn/api/v1/models/$MODEL_ID/repo?Revision=master&FilePath=$MODEL_REL_PATH"

register_cache_entry() {
  "$PYTHON_BIN" - "$MODEL_DIR" "$MODEL_REL_PATH" "$MODEL_REVISION" <<'PY'
import pickle
import sys
from pathlib import Path

model_dir = Path(sys.argv[1])
rel_path = sys.argv[2]
revision = sys.argv[3]
index_path = model_dir / ".msc"

if index_path.exists():
    entries = pickle.loads(index_path.read_bytes())
else:
    entries = []

entries = [
    entry
    for entry in entries
    if not (isinstance(entry, dict) and entry.get("Path") == rel_path)
]
entries.append({"Path": rel_path, "Revision": revision})
index_path.write_bytes(pickle.dumps(entries))
print(f"Registered {rel_path} in {index_path}")
PY
}

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Missing Python runtime: $PYTHON_BIN" >&2
  echo "Run scripts/setup_funasr_venv.sh first." >&2
  exit 1
fi

"$PYTHON_BIN" - "$MODEL_ID" "$MAX_WORKERS" <<'PY'
import os
import sys
from pathlib import Path

from modelscope.hub.snapshot_download import snapshot_download

model_id = sys.argv[1]
max_workers = int(sys.argv[2])

print(f"Downloading {model_id} via ModelScope snapshot_download...")
model_dir = snapshot_download(
    model_id=model_id,
    ignore_patterns=["model.pt", "images/*", "example/*"],
    max_workers=max_workers,
)
model_path = Path(model_dir)
print(f"Model directory: {model_path}")
if not model_path.exists():
    raise SystemExit(f"Download did not create expected directory: {model_path}")

total_size = 0
for root, _, files in os.walk(model_path):
    for name in files:
        total_size += (Path(root) / name).stat().st_size
print(f"Cached size: {total_size / (1024 ** 3):.2f} GiB")

PY

mkdir -p "$MODEL_DIR" "$TEMP_DIR"
target="$MODEL_DIR/$MODEL_REL_PATH"
partial="$TEMP_DIR/$MODEL_REL_PATH"

if [ -f "$target" ]; then
  actual_bytes="$(wc -c < "$target" | tr -d ' ')"
  if [ "$actual_bytes" = "$EXPECTED_BYTES" ]; then
    actual_sha="$(shasum -a 256 "$target" | awk '{print $1}')"
    if [ "$actual_sha" = "$EXPECTED_SHA256" ]; then
      register_cache_entry
      echo "$target already exists and passed size/SHA256 validation."
      exit 0
    fi
  fi
  echo "Existing $target failed validation; moving it to $partial for resume/retry." >&2
  mv "$target" "$partial"
fi

echo "Downloading $MODEL_REL_PATH with curl resume support..."
echo "URL: $API_URL"
curl \
  --fail \
  --location \
  --continue-at - \
  --retry 20 \
  --retry-delay 5 \
  --connect-timeout 30 \
  --output "$partial" \
  "$API_URL"

actual_bytes="$(wc -c < "$partial" | tr -d ' ')"
if [ "$actual_bytes" != "$EXPECTED_BYTES" ]; then
  echo "Unexpected $MODEL_REL_PATH size: $actual_bytes bytes, expected $EXPECTED_BYTES." >&2
  exit 1
fi

actual_sha="$(shasum -a 256 "$partial" | awk '{print $1}')"
if [ "$actual_sha" != "$EXPECTED_SHA256" ]; then
  echo "Unexpected $MODEL_REL_PATH sha256: $actual_sha, expected $EXPECTED_SHA256." >&2
  exit 1
fi

mv "$partial" "$target"
register_cache_entry
echo "Downloaded and verified: $target"
du -sh "$MODEL_DIR"
