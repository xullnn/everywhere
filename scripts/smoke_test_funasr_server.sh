#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  echo "Missing .venv. Run scripts/setup_funasr_venv.sh first." >&2
  exit 1
fi

source .venv/bin/activate

python .external/FunASR/runtime/python/websocket/funasr_wss_client.py \
  --host "${FUNASR_HOST:-127.0.0.1}" \
  --port "${FUNASR_PORT:-10095}" \
  --ssl 0 \
  --mode 2pass \
  --chunk_size "8,8,4" \
  --audio_in "${FUNASR_SMOKE_WAV:-.external/models/paraformer-offline-small/example/asr_example.wav}" \
  --send_without_sleep
