#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-.venv-mimo/bin/python}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-18107}"
MODEL_ID="${MODEL_ID:-qwen3-asr-0.6b-mlx-8bit}"
MODEL="${MODEL:-.external/models/mlx-community__Qwen3-ASR-0.6B-8bit}"
MLX_AUDIO_SOURCE="${MLX_AUDIO_SOURCE:-.external/repos/mlx-audio}"
CASES="${CASES:-eval/asr_streaming/cases.extended.local.jsonl}"
OUT_DIR="${OUT_DIR:-eval/asr_streaming/results/qwen3-mlx-http-service-0.6b-extended-$(date +%Y%m%d-%H%M%S)}"
LANGUAGE="${LANGUAGE:-Chinese}"
MAX_FIRST_PARTIAL_MS="${MAX_FIRST_PARTIAL_MS:-3000}"
MAX_FINAL_LATENCY_MS="${MAX_FINAL_LATENCY_MS:-3000}"
REQUEST_TIMEOUT_SEC="${REQUEST_TIMEOUT_SEC:-180}"
MAX_TOKENS="${MAX_TOKENS:-512}"
RESOURCE_INTERVAL_SEC="${RESOURCE_INTERVAL_SEC:-1.0}"

SERVICE_PID=""
MONITOR_PID=""
GATE_EXIT=99

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

if [ ! -f "$CASES" ]; then
  echo "Missing cases file: $CASES" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"
SERVICE_LOG="$OUT_DIR/service.log"
SERVICE_URL="http://$HOST:$PORT"
RESOURCE_SAMPLES="$OUT_DIR/resource_samples.jsonl"
RESOURCE_SUMMARY="$OUT_DIR/resource_summary.json"
RESOURCE_MONITOR_LOG="$OUT_DIR/resource_monitor.log"
RUN_METADATA="$OUT_DIR/run_metadata.json"
GATE_SUMMARY="$OUT_DIR/summary.json"

cleanup() {
  if [ -n "${MONITOR_PID:-}" ] && kill -0 "$MONITOR_PID" >/dev/null 2>&1; then
    kill -TERM "$MONITOR_PID" >/dev/null 2>&1 || true
    wait "$MONITOR_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "${SERVICE_PID:-}" ] && kill -0 "$SERVICE_PID" >/dev/null 2>&1; then
    kill "$SERVICE_PID" >/dev/null 2>&1 || true
    wait "$SERVICE_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

RUN_STARTED_EPOCH_MS="$(python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
)"

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

python3 eval/asr_streaming/monitor_pid_resources.py \
  --pid "$SERVICE_PID" \
  --samples "$RESOURCE_SAMPLES" \
  --summary "$RESOURCE_SUMMARY" \
  --interval-sec "$RESOURCE_INTERVAL_SEC" \
  --label "qwen3_mlx_http_service" \
  >"$RESOURCE_MONITOR_LOG" 2>&1 &
MONITOR_PID=$!

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

set +e
python3 eval/asr_streaming/incremental_ux_gate.py run \
  --adapter http-json \
  --service-url "$SERVICE_URL" \
  --request-timeout-sec "$REQUEST_TIMEOUT_SEC" \
  --model-id "$MODEL_ID" \
  --cases "$CASES" \
  --out-dir "$OUT_DIR" \
  --max-first-partial-ms "$MAX_FIRST_PARTIAL_MS" \
  --max-final-latency-ms "$MAX_FINAL_LATENCY_MS"
GATE_EXIT=$?
set -e

if [ -n "${MONITOR_PID:-}" ] && kill -0 "$MONITOR_PID" >/dev/null 2>&1; then
  kill -TERM "$MONITOR_PID" >/dev/null 2>&1 || true
  wait "$MONITOR_PID" >/dev/null 2>&1 || true
fi

if [ -n "${SERVICE_PID:-}" ] && kill -0 "$SERVICE_PID" >/dev/null 2>&1; then
  kill "$SERVICE_PID" >/dev/null 2>&1 || true
  wait "$SERVICE_PID" >/dev/null 2>&1 || true
fi

RUN_FINISHED_EPOCH_MS="$(python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
)"

python3 - "$RUN_METADATA" <<PY
import json
import os
import sys
from pathlib import Path

metadata = {
    "schema_version": "1.0",
    "runner": "run_qwen3_mlx_http_extended_gate.sh",
    "started_epoch_ms": int("$RUN_STARTED_EPOCH_MS"),
    "finished_epoch_ms": int("$RUN_FINISHED_EPOCH_MS"),
    "duration_seconds": (int("$RUN_FINISHED_EPOCH_MS") - int("$RUN_STARTED_EPOCH_MS")) / 1000.0,
    "gate_exit_code": int("$GATE_EXIT"),
    "service_pid": int("$SERVICE_PID"),
    "service_url": "$SERVICE_URL",
    "model_id": "$MODEL_ID",
    "model": "$MODEL",
    "mlx_audio_source": "$MLX_AUDIO_SOURCE",
    "cases": "$CASES",
    "out_dir": "$OUT_DIR",
    "paths": {
        "gate_summary": "$GATE_SUMMARY",
        "resource_samples": "$RESOURCE_SAMPLES",
        "resource_summary": "$RESOURCE_SUMMARY",
        "service_log": "$SERVICE_LOG",
        "resource_monitor_log": "$RESOURCE_MONITOR_LOG",
    },
}
path = Path(sys.argv[1])
path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(metadata, ensure_ascii=False, sort_keys=True))
PY

echo "Qwen3 MLX HTTP extended gate wrote: $OUT_DIR"
exit "$GATE_EXIT"
