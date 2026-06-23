#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
CASES_FILE="${CASES_FILE:-eval/asr_streaming/cases.local.jsonl}"
OUT_DIR="${OUT_DIR:-eval/asr_streaming/results/qwen3-asr-0.6b-smoke}"
QWEN3_MODEL="${QWEN3_MODEL:-.external/models/Qwen3-ASR-0.6B}"
QWEN3_DEVICE="${QWEN3_DEVICE:-cpu}"
QWEN3_DTYPE="${QWEN3_DTYPE:-auto}"
QWEN3_LANGUAGE="${QWEN3_LANGUAGE:-Chinese}"
QWEN3_CONTEXT="${QWEN3_CONTEXT:-}"
SMOKE_CASE_FILE="${SMOKE_CASE_FILE:-/tmp/localvoiceinput-qwen3-asr-smoke.jsonl}"
DRY_RUN="${DRY_RUN:-0}"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Missing Python runtime: $PYTHON_BIN" >&2
  echo "Run scripts/setup_qwen3_asr_venv.sh first." >&2
  exit 1
fi

"$PYTHON_BIN" - "$CASES_FILE" "$SMOKE_CASE_FILE" <<'PY'
import json
import sys
from pathlib import Path

cases_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
base = cases_path.parent.resolve()
for line in cases_path.read_text(encoding="utf-8").splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        continue
    case = json.loads(stripped)
    audio = Path(str(case["audio"]))
    if not audio.is_absolute():
        audio = (base / audio).resolve()
    case["audio"] = str(audio)
    out_path.write_text(json.dumps(case, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Prepared smoke case {case['id']} -> {audio}")
    break
else:
    raise SystemExit(f"No cases found in {cases_path}")
PY

cmd=(
  "$PYTHON_BIN" eval/asr_streaming/run_eval.py run
  --adapter qwen3-asr-local \
  --model-id qwen3-asr-0.6b \
  --cases "$SMOKE_CASE_FILE" \
  --out-dir "$OUT_DIR" \
  --qwen3-model "$QWEN3_MODEL" \
  --qwen3-device "$QWEN3_DEVICE" \
  --qwen3-dtype "$QWEN3_DTYPE" \
  --qwen3-language "$QWEN3_LANGUAGE" \
  --qwen3-context "$QWEN3_CONTEXT"
)

if [ "$DRY_RUN" = "1" ]; then
  printf 'Dry run command:'
  printf ' %q' "${cmd[@]}"
  printf '\n'
  exit 0
fi

exec "${cmd[@]}"
