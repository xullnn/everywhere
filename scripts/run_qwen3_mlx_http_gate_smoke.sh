#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-.venv-mimo/bin/python}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-18106}"
MODEL_ID="${MODEL_ID:-qwen3-asr-0.6b-mlx-8bit}"
MODEL="${MODEL:-.external/models/mlx-community__Qwen3-ASR-0.6B-8bit}"
MLX_AUDIO_SOURCE="${MLX_AUDIO_SOURCE:-.external/repos/mlx-audio}"
CASES="${CASES:-eval/asr_streaming/cases.smoke.local.jsonl}"
OUT_DIR="${OUT_DIR:-eval/asr_streaming/results/qwen3-mlx-http-service-0.6b-smoke-$(date +%Y%m%d-%H%M%S)}"
LANGUAGE="${LANGUAGE:-Chinese}"
MAX_FIRST_PARTIAL_MS="${MAX_FIRST_PARTIAL_MS:-3000}"
MAX_FINAL_LATENCY_MS="${MAX_FINAL_LATENCY_MS:-3000}"
REQUEST_TIMEOUT_SEC="${REQUEST_TIMEOUT_SEC:-120}"
MAX_TOKENS="${MAX_TOKENS:-256}"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Missing Python runtime: $PYTHON_BIN" >&2
  echo "Set PYTHON_BIN or prepare the MLX runtime first." >&2
  exit 2
fi

if [ ! -d "$MODEL" ]; then
  echo "Missing Qwen3 MLX model directory: $MODEL" >&2
  exit 2
fi

if [ ! -d "$MLX_AUDIO_SOURCE" ]; then
  echo "Missing mlx-audio source directory: $MLX_AUDIO_SOURCE" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"
SERVICE_LOG="$OUT_DIR/service.log"
SERVICE_URL="http://$HOST:$PORT"

PYTHONPATH="$MLX_AUDIO_SOURCE${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" \
  eval/asr_streaming/qwen3_mlx_http_service.py \
  --host "$HOST" \
  --port "$PORT" \
  --model-id "$MODEL_ID" \
  --model "$MODEL" \
  --mlx-audio-source "$MLX_AUDIO_SOURCE" \
  --language "$LANGUAGE" \
  --max-tokens "$MAX_TOKENS" \
  >"$SERVICE_LOG" 2>&1 &
SERVICE_PID=$!

cleanup() {
  if kill -0 "$SERVICE_PID" >/dev/null 2>&1; then
    kill "$SERVICE_PID" >/dev/null 2>&1 || true
    wait "$SERVICE_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

python3 - "$SERVICE_URL" "$SERVICE_LOG" <<'PY'
import json
import sys
import time
import urllib.request
from pathlib import Path

url = sys.argv[1].rstrip("/") + "/health"
log_path = Path(sys.argv[2])
deadline = time.time() + 180
last_error = ""
while time.time() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("ok"):
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            raise SystemExit(0)
    except Exception as exc:
        last_error = str(exc)
        if log_path.exists():
            text = log_path.read_text(encoding="utf-8", errors="replace")
            if "Traceback" in text:
                print(text[-4000:], file=sys.stderr)
                raise SystemExit(1)
    time.sleep(1)
print(f"service did not become healthy: {last_error}", file=sys.stderr)
if log_path.exists():
    print(log_path.read_text(encoding="utf-8", errors="replace")[-4000:], file=sys.stderr)
raise SystemExit(1)
PY

python3 eval/asr_streaming/incremental_ux_gate.py run \
  --adapter http-json \
  --service-url "$SERVICE_URL" \
  --request-timeout-sec "$REQUEST_TIMEOUT_SEC" \
  --model-id "$MODEL_ID" \
  --cases "$CASES" \
  --out-dir "$OUT_DIR" \
  --max-first-partial-ms "$MAX_FIRST_PARTIAL_MS" \
  --max-final-latency-ms "$MAX_FINAL_LATENCY_MS"

echo "Qwen3 MLX HTTP gate smoke wrote: $OUT_DIR"
