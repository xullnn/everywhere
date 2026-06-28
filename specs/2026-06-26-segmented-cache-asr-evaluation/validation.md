# Validation - Segmented Cache ASR Evaluation

## Completion Rule

This feature can be marked `passes=true` only when the new script compiles, dry-run preparation works, generated cases validate, at least one analysis output is produced, and concrete evidence is appended to `specs/progress.md`. A real Qwen3 MLX pilot should run when the local runtime is available; otherwise the blocker must be recorded.

## Acceptance Criteria

- A1: The segmented-cache tool can generate a manifest and segment case JSONL from existing local WAV cases.
- A2: Generated segment case JSONL validates through the existing ASR harness.
- A3: The analysis output aggregates segment results back to source case plus strategy.
- A4: The analysis reports segment count, total model wall time, max segment wall time, serial-worker backlog, final wait, aggregate CER, WER, and coverage with Chinese explanations.
- A5: The analysis warns when a strategy loses substantial text, has high error rate, or would leave the user waiting too long after stop.
- A6: The feature does not alter macOS App behavior.

## Automated Checks

```bash
python3 -m py_compile eval/asr_streaming/segment_cache_eval.py
python3 eval/asr_streaming/segment_cache_eval.py prepare --dry-run --case-id existing_long_400_001
python3 eval/asr_streaming/segment_cache_eval.py prepare --case-id existing_long_400_001 --strategy s45_c250_o0:45:250:0 --strategy s60_c250_o0:60:250:0
python3 eval/asr_streaming/run_eval.py validate-cases --cases eval/asr_streaming/cases.segment_cache.local.jsonl
PYTHONPATH=.external/repos/mlx-audio .venv-mimo/bin/python eval/asr_streaming/run_eval.py run --adapter mlx-stt-local --model-id qwen3-asr-0.6b-mlx-8bit --mlx-stt-model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit --mlx-stt-language Chinese --cases eval/asr_streaming/cases.segment_cache.local.jsonl --out-dir eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626
python3 eval/asr_streaming/segment_cache_eval.py analyze --manifest eval/asr_streaming/results/segment-cache/manifest.json --run-summary eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626/summary.json --out-dir eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626-analysis
```

The concrete result directory may include a suffix if rerun during local testing.

## Manual Smoke Checks

- Read generated `analysis.md` and confirm recommendations remain evaluation-only and do not imply App behavior changes.

## Optional / Not-Applicable Checks

- Broad natural long-speech strategy sweeps are recommended follow-up work, not required for this first implementation pass.

## Evidence Required In `specs/progress.md`

- commands run;
- result paths;
- strategy table or summary;
- validation failures or blockers;
- recommended next action.
