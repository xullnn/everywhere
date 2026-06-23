# Validation - MiMo-V2.5-ASR MLX Local Evaluation Adapter

## Completion rule

This feature can be marked `passes=true` only when all required checks pass. If local runtime is blocked, record the blocker and leave the feature `blocked` or `implemented` with `passes=false`.

## Acceptance criteria

- A1: Local MiMo ASR and audio tokenizer files are present under `.external/models/`.
- A2: The MLX runtime loads locally or a concrete macOS/runtime blocker is recorded.
- A3: At least one local WAV smoke case writes `events.jsonl`, per-case `summary.json`, and aggregate `summary.json`.
- A4: If smoke passes, run the full 10-case set.
- A5: Outputs include model metadata and Chinese metric explanations.
- A6: No macOS app runtime code is changed.

## Automated checks

```bash
.venv-mimo/bin/python -m py_compile eval/asr_streaming/run_eval.py
python3 -m json.tool eval/asr_streaming/model_registry.json >/dev/null
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-22-mimo-v25-asr-mlx-local-eval/feature.json >/dev/null
bash eval/asr_streaming/validate.sh
```

Optional when adapter is implemented:

```bash
.venv-mimo/bin/python eval/asr_streaming/run_eval.py run \
  --adapter mimo-asr-mlx-local \
  --model-id mimo-v2.5-asr \
  --mimo-model .external/models/MiMo-V2.5-ASR-MLX \
  --mimo-audio-tokenizer-dir .external/models/MiMo-Audio-Tokenizer \
  --cases /tmp/localvoiceinput-mimo-smoke.jsonl \
  --out-dir eval/asr_streaming/results/mimo-v25-asr-mlx-smoke
```

## Evidence required in `specs/progress.md`

- Sync command and result.
- Runtime setup command and result, or concrete blocker.
- Smoke/full-run output directories if executed.
- Aggregate metrics and interpretation if full run executes.
