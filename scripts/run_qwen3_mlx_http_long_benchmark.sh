#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-.venv-mimo/bin/python}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-18108}"
MODEL_ID="${MODEL_ID:-qwen3-asr-0.6b-mlx-8bit}"
MODEL="${MODEL:-.external/models/mlx-community__Qwen3-ASR-0.6B-8bit}"
MLX_AUDIO_SOURCE="${MLX_AUDIO_SOURCE:-.external/repos/mlx-audio}"
MANIFEST="${MANIFEST:-eval/asr_streaming/long_corpus_manifest.json}"
CASES="${CASES:-eval/asr_streaming/cases.long_prepared.local.jsonl}"
OUT_DIR="${OUT_DIR:-eval/asr_streaming/results/qwen3-mlx-http-long-benchmark-$(date +%Y%m%d-%H%M%S)}"
LANGUAGE="${LANGUAGE:-Chinese}"
CHUNK_MS="${CHUNK_MS:-480}"
MAX_FIRST_PARTIAL_MS="${MAX_FIRST_PARTIAL_MS:-5000}"
MAX_FINAL_LATENCY_MS="${MAX_FINAL_LATENCY_MS:-120000}"
REQUEST_TIMEOUT_SEC="${REQUEST_TIMEOUT_SEC:-300}"
MAX_TOKENS="${MAX_TOKENS:-1024}"
MIN_PREFIX_SEC="${MIN_PREFIX_SEC:-1.0}"
PREFIX_STEP_SEC="${PREFIX_STEP_SEC:-1.5}"
MAX_PREFIXES="${MAX_PREFIXES:-400}"
RESOURCE_INTERVAL_SEC="${RESOURCE_INTERVAL_SEC:-1.0}"
PREPARE_CASES="${PREPARE_CASES:-1}"
DRY_RUN="${DRY_RUN:-0}"

SERVICE_PID=""
MONITOR_PID=""
GATE_EXIT=99

SERVICE_URL="http://$HOST:$PORT"

print_config() {
  python3 - <<PY
import json
from pathlib import Path

config = {
    "schema_version": "1.0",
    "runner": "run_qwen3_mlx_http_long_benchmark.sh",
    "dry_run": "$DRY_RUN" == "1",
    "python_bin": "$PYTHON_BIN",
    "service_url": "$SERVICE_URL",
    "model_id": "$MODEL_ID",
    "model": "$MODEL",
    "mlx_audio_source": "$MLX_AUDIO_SOURCE",
    "manifest": "$MANIFEST",
    "cases": "$CASES",
    "out_dir": "$OUT_DIR",
    "language": "$LANGUAGE",
    "chunk_ms": int("$CHUNK_MS"),
    "max_first_partial_ms": float("$MAX_FIRST_PARTIAL_MS"),
    "max_final_latency_ms": float("$MAX_FINAL_LATENCY_MS"),
    "request_timeout_sec": float("$REQUEST_TIMEOUT_SEC"),
    "max_tokens": int("$MAX_TOKENS"),
    "min_prefix_sec": float("$MIN_PREFIX_SEC"),
    "prefix_step_sec": float("$PREFIX_STEP_SEC"),
    "max_prefixes": int("$MAX_PREFIXES"),
    "prepare_cases": "$PREPARE_CASES" == "1",
    "path_status": {
        "python_bin_exists": Path("$PYTHON_BIN").exists(),
        "model_exists": Path("$MODEL").exists(),
        "mlx_audio_source_exists": Path("$MLX_AUDIO_SOURCE").exists(),
        "manifest_exists": Path("$MANIFEST").exists(),
        "cases_exists": Path("$CASES").exists(),
    },
}
print(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True))
PY
}

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

if [ "$DRY_RUN" = "1" ]; then
  print_config
  exit 0
fi

if [ "$PREPARE_CASES" = "1" ]; then
  python3 eval/asr_streaming/prepare_long_corpus.py \
    --manifest "$MANIFEST" \
    --out-cases "$CASES"
fi

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Missing Python runtime: $PYTHON_BIN" >&2
  echo "Run: bash scripts/setup_qwen3_mlx_runtime.sh" >&2
  echo "Or set PYTHON_BIN to an existing MLX/mlx-audio runtime." >&2
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
  echo "Run: python3 eval/asr_streaming/prepare_long_corpus.py --manifest $MANIFEST --out-cases $CASES" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"
SERVICE_LOG="$OUT_DIR/service.log"
RESOURCE_SAMPLES="$OUT_DIR/resource_samples.jsonl"
RESOURCE_SUMMARY="$OUT_DIR/resource_summary.json"
RESOURCE_MONITOR_LOG="$OUT_DIR/resource_monitor.log"
RUN_METADATA="$OUT_DIR/run_metadata.json"
GATE_SUMMARY="$OUT_DIR/summary.json"

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
  --min-prefix-sec "$MIN_PREFIX_SEC" \
  --prefix-step-sec "$PREFIX_STEP_SEC" \
  --max-prefixes "$MAX_PREFIXES" \
  >"$SERVICE_LOG" 2>&1 &
SERVICE_PID=$!

python3 eval/asr_streaming/monitor_pid_resources.py \
  --pid "$SERVICE_PID" \
  --samples "$RESOURCE_SAMPLES" \
  --summary "$RESOURCE_SUMMARY" \
  --interval-sec "$RESOURCE_INTERVAL_SEC" \
  --label "qwen3_mlx_http_long_benchmark" \
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
  --chunk-ms "$CHUNK_MS" \
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
import sys
from pathlib import Path

metadata = {
    "schema_version": "1.0",
    "runner": "run_qwen3_mlx_http_long_benchmark.sh",
    "started_epoch_ms": int("$RUN_STARTED_EPOCH_MS"),
    "finished_epoch_ms": int("$RUN_FINISHED_EPOCH_MS"),
    "duration_seconds": (int("$RUN_FINISHED_EPOCH_MS") - int("$RUN_STARTED_EPOCH_MS")) / 1000.0,
    "gate_exit_code": int("$GATE_EXIT"),
    "service_pid": int("$SERVICE_PID"),
    "service_url": "$SERVICE_URL",
    "model_id": "$MODEL_ID",
    "model": "$MODEL",
    "mlx_audio_source": "$MLX_AUDIO_SOURCE",
    "manifest": "$MANIFEST",
    "cases": "$CASES",
    "out_dir": "$OUT_DIR",
    "parameters": {
        "chunk_ms": int("$CHUNK_MS"),
        "max_first_partial_ms": float("$MAX_FIRST_PARTIAL_MS"),
        "max_final_latency_ms": float("$MAX_FINAL_LATENCY_MS"),
        "request_timeout_sec": float("$REQUEST_TIMEOUT_SEC"),
        "max_tokens": int("$MAX_TOKENS"),
        "min_prefix_sec": float("$MIN_PREFIX_SEC"),
        "prefix_step_sec": float("$PREFIX_STEP_SEC"),
        "max_prefixes": int("$MAX_PREFIXES"),
    },
    "metric_explanations_zh": {
        "TTFP": "首个 partial 出现时间，从开始输入音频到首次显示中间结果的耗时。",
        "P50": "中位数，50% 的样本不超过该值。",
        "P95": "95 分位，95% 的样本不超过该值，反映长尾卡顿。",
        "RTF": "实时因子，处理 1 秒音频需要多少秒；低于 1 表示快于实时。",
        "CER": "字符错误率，主要用于中文；越低越好。",
        "WER": "词错误率，主要用于英文或空格分词文本；越低越好。"
    },
    "paths": {
        "gate_summary": "$GATE_SUMMARY",
        "resource_samples": "$RESOURCE_SAMPLES",
        "resource_summary": "$RESOURCE_SUMMARY",
        "service_log": "$SERVICE_LOG",
        "resource_monitor_log": "$RESOURCE_MONITOR_LOG"
    }
}
path = Path(sys.argv[1])
path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(metadata, ensure_ascii=False, sort_keys=True))
PY

echo "Qwen3 MLX HTTP long benchmark wrote: $OUT_DIR"
exit "$GATE_EXIT"
