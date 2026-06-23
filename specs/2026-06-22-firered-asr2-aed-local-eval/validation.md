# Validation - FireRedASR2-AED Local Evaluation Adapter

## Completion rule

This feature can be marked `passes=true` only when all required checks pass. If local runtime is blocked, record the blocker and leave the feature `blocked` or `implemented` with `passes=false`.

## Acceptance criteria

- A1: The local FireRed model files are present under `.external/models/FireRedASR2-AED`.
- A2: The official runtime either loads locally or a concrete macOS/runtime blocker is recorded.
- A3: If runtime loads, at least one local WAV smoke case writes `events.jsonl`, per-case `summary.json`, and aggregate `summary.json`.
- A4: If smoke passes, run the full 10-case set.
- A5: Outputs include model metadata and Chinese metric explanations.
- A6: No macOS app runtime code is changed.

## Automated checks

```bash
python3 -m json.tool eval/asr_streaming/model_registry.json >/dev/null
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-22-firered-asr2-aed-local-eval/feature.json >/dev/null
bash eval/asr_streaming/validate.sh
```

Optional when adapter is implemented:

```bash
<firered-venv>/bin/python eval/asr_streaming/run_eval.py run --adapter firered-asr2-aed-local --model-id firered-asr2s --firered-model .external/models/FireRedASR2-AED --cases /tmp/localvoiceinput-firered-smoke.jsonl --out-dir eval/asr_streaming/results/firered-asr2-aed-smoke
```

## Evidence required in `specs/progress.md`

- Sync command and result.
- Runtime setup command and result, or concrete blocker.
- Smoke/full-run output directories if executed.
- Aggregate metrics and interpretation if full run executes.
