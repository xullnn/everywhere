# Validation — Fun-ASR-Nano Local Evaluation Adapter

## Completion rule

This feature can be marked `passes=true` only after non-server checks pass and at least one real local WAV is processed by the `funasr-nano-local` adapter. A full 10-case run is preferred but not required for initial adapter validation if runtime is too slow or a dependency blocker is documented.

## Acceptance criteria

- A1: `run_eval.py` exposes a `funasr-nano-local` adapter.
- A2: `model_registry.json` lists `fun-asr-nano-2512` with the adapter and metadata.
- A3: A short WAV smoke run writes `events.jsonl`, per-case `summary.json`, and aggregate `summary.json`.
- A4: Summary output includes Chinese metric explanations and model metadata.
- A5: File-level inference does not claim realtime partial behavior.
- A6: No macOS app runtime code changes are made.

## Automated checks

```bash
python3 -m py_compile eval/asr_streaming/run_eval.py
python3 -m json.tool eval/asr_streaming/model_registry.json
bash eval/asr_streaming/validate.sh
```

## Manual smoke checks

```bash
DRY_RUN=1 bash scripts/run_fun_asr_nano_smoke.sh
bash scripts/run_fun_asr_nano_smoke.sh
```

Direct equivalent:

```bash
.venv/bin/python eval/asr_streaming/run_eval.py run \
  --adapter funasr-nano-local \
  --model-id fun-asr-nano-2512 \
  --cases /tmp/localvoiceinput-fun-asr-nano-smoke.jsonl \
  --out-dir eval/asr_streaming/results/fun-asr-nano-smoke
```

## Optional / not-applicable checks

- Full 10-case run is optional for initial feasibility if the one-case run exposes a runtime blocker.
- vLLM streaming service validation is out of scope for this feature.

## Evidence required in `specs/progress.md`

- Commands run.
- Results.
- Smoke output directory.
- Any dependency/runtime blockers.
- Whether a full 10-case run was completed or deferred.
