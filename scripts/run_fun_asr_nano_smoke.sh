#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
CASES_FILE="${CASES_FILE:-eval/asr_streaming/cases.local.jsonl}"
OUT_DIR="${OUT_DIR:-eval/asr_streaming/results/fun-asr-nano-smoke}"
FUNASR_HUB="${FUNASR_HUB:-ms}"
FUNASR_DEVICE="${FUNASR_DEVICE:-cpu}"
FUNASR_NANO_MODEL="${FUNASR_NANO_MODEL:-FunAudioLLM/Fun-ASR-Nano-2512}"
FUNASR_REMOTE_CODE="${FUNASR_REMOTE_CODE:-./model.py}"
FUNASR_VAD_MODEL="${FUNASR_VAD_MODEL:-}"
SMOKE_CASE_FILE="${SMOKE_CASE_FILE:-/tmp/localvoiceinput-fun-asr-nano-smoke.jsonl}"
DRY_RUN="${DRY_RUN:-0}"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Missing Python runtime: $PYTHON_BIN" >&2
  echo "Run scripts/setup_funasr_venv.sh first." >&2
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
  --adapter funasr-nano-local \
  --model-id fun-asr-nano-2512 \
  --cases "$SMOKE_CASE_FILE" \
  --out-dir "$OUT_DIR" \
  --funasr-hub "$FUNASR_HUB" \
  --funasr-device "$FUNASR_DEVICE" \
  --funasr-nano-model "$FUNASR_NANO_MODEL" \
  --funasr-remote-code "$FUNASR_REMOTE_CODE" \
  --funasr-vad-model "$FUNASR_VAD_MODEL"
)

if [ "$DRY_RUN" = "1" ]; then
  printf 'Dry run command:'
  printf ' %q' "${cmd[@]}"
  printf '\n'
  exit 0
fi

exec "${cmd[@]}"
