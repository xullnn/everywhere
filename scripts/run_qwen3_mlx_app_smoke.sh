#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-.venv-mimo/bin/python}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-18105}"
MODEL_ID="${MODEL_ID:-qwen3-asr-0.6b-mlx-8bit}"
MODEL="${MODEL:-.external/models/mlx-community__Qwen3-ASR-0.6B-8bit}"
MLX_AUDIO_SOURCE="${MLX_AUDIO_SOURCE:-.external/repos/mlx-audio}"
LANGUAGE="${LANGUAGE:-Chinese}"
MAX_TOKENS="${MAX_TOKENS:-1024}"
MIN_PREFIX_SEC="${MIN_PREFIX_SEC:-1.0}"
PREFIX_STEP_SEC="${PREFIX_STEP_SEC:-1.5}"
MAX_PREFIXES="${MAX_PREFIXES:-180}"
OUT_DIR="${OUT_DIR:-eval/asr_streaming/results/qwen3-mlx-real-app-smoke-$(date +%Y%m%d-%H%M%S)}"
DRY_RUN="${DRY_RUN:-0}"
RUN_APP="${RUN_APP:-1}"

SERVICE_PID=""
APP_EXIT=0
SERVICE_URL="http://$HOST:$PORT"
SERVICE_LOG="$OUT_DIR/service.log"
APP_LOG="$OUT_DIR/app.log"
RUN_METADATA="$OUT_DIR/run_metadata.json"

APP_CMD=(swift run LocalVoiceInputMac --local-http-asr --asr-http-url "$SERVICE_URL")
SERVICE_CMD=(
  "$PYTHON_BIN"
  eval/asr_streaming/qwen3_mlx_http_service.py
  --host "$HOST"
  --port "$PORT"
  --model-id "$MODEL_ID"
  --model "$MODEL"
  --mlx-audio-source "$MLX_AUDIO_SOURCE"
  --language "$LANGUAGE"
  --max-tokens "$MAX_TOKENS"
  --min-prefix-sec "$MIN_PREFIX_SEC"
  --prefix-step-sec "$PREFIX_STEP_SEC"
  --max-prefixes "$MAX_PREFIXES"
)

runtime_status_json() {
  python3 - "$PYTHON_BIN" "$MODEL" "$MLX_AUDIO_SOURCE" <<'PY'
import json
import os
import sys
from pathlib import Path

python_bin, model, mlx_audio = sys.argv[1:]
status = {
    "python_bin": python_bin,
    "python_bin_executable": os.access(python_bin, os.X_OK),
    "model": model,
    "model_exists": Path(model).is_dir(),
    "mlx_audio_source": mlx_audio,
    "mlx_audio_source_exists": Path(mlx_audio).is_dir(),
}
print(json.dumps(status, ensure_ascii=False, sort_keys=True))
PY
}

require_runtime_paths() {
  if [ ! -x "$PYTHON_BIN" ]; then
    echo "Missing executable Python runtime: $PYTHON_BIN" >&2
    echo "Run: bash scripts/setup_qwen3_mlx_runtime.sh" >&2
    echo "Or set PYTHON_BIN to a Python environment with MLX/mlx-audio dependencies." >&2
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
}

cleanup() {
  if [ -n "${SERVICE_PID:-}" ] && kill -0 "$SERVICE_PID" >/dev/null 2>&1; then
    kill "$SERVICE_PID" >/dev/null 2>&1 || true
    wait "$SERVICE_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

mkdir -p "$OUT_DIR"

if [ "$DRY_RUN" = "1" ]; then
  echo "Qwen3 app smoke dry run"
  echo "runtime_status=$(runtime_status_json)"
  printf 'service_cmd='
  printf '%q ' env "PYTHONPATH=$MLX_AUDIO_SOURCE\${PYTHONPATH:+:\$PYTHONPATH}" "${SERVICE_CMD[@]}"
  printf '\n'
  printf 'app_cmd='
  printf '%q ' "${APP_CMD[@]}"
  printf '\n'
  echo "out_dir=$OUT_DIR"
  exit 0
fi

require_runtime_paths

RUN_STARTED_EPOCH_MS="$(python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
)"

PYTHONPATH="$MLX_AUDIO_SOURCE${PYTHONPATH:+:$PYTHONPATH}" "${SERVICE_CMD[@]}" >"$SERVICE_LOG" 2>&1 &
SERVICE_PID=$!

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

echo "Qwen3 service is healthy at $SERVICE_URL"
echo "Service log: $SERVICE_LOG"

if [ "$RUN_APP" = "1" ]; then
  echo "Launching LocalVoiceInputMac for manual smoke. Quit the app to stop the service."
  set +e
  "${APP_CMD[@]}" 2>&1 | tee "$APP_LOG"
  APP_EXIT="${PIPESTATUS[0]}"
  set -e
else
  echo "RUN_APP=0, service is ready. Run this in another terminal:"
  printf '%q ' "${APP_CMD[@]}"
  printf '\n'
  echo "Press Ctrl-C here when manual smoke is done."
  while kill -0 "$SERVICE_PID" >/dev/null 2>&1; do
    sleep 2
  done
fi

RUN_FINISHED_EPOCH_MS="$(python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
)"

python3 - "$RUN_METADATA" <<PY
import json
import sys
from pathlib import Path

metadata = {
    "schema_version": "1.0",
    "runner": "run_qwen3_mlx_app_smoke.sh",
    "started_epoch_ms": int("$RUN_STARTED_EPOCH_MS"),
    "finished_epoch_ms": int("$RUN_FINISHED_EPOCH_MS"),
    "duration_seconds": (int("$RUN_FINISHED_EPOCH_MS") - int("$RUN_STARTED_EPOCH_MS")) / 1000.0,
    "service_pid": int("$SERVICE_PID"),
    "service_url": "$SERVICE_URL",
    "app_exit_code": int("$APP_EXIT"),
    "model_id": "$MODEL_ID",
    "model": "$MODEL",
    "mlx_audio_source": "$MLX_AUDIO_SOURCE",
    "max_tokens": int("$MAX_TOKENS"),
    "min_prefix_sec": float("$MIN_PREFIX_SEC"),
    "prefix_step_sec": float("$PREFIX_STEP_SEC"),
    "max_prefixes": int("$MAX_PREFIXES"),
    "out_dir": "$OUT_DIR",
    "paths": {
        "service_log": "$SERVICE_LOG",
        "app_log": "$APP_LOG",
    },
}
path = Path(sys.argv[1])
path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(metadata, ensure_ascii=False, sort_keys=True))
PY

echo "Qwen3 app smoke wrote: $OUT_DIR"
exit "$APP_EXIT"
