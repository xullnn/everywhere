# Validation - Segment Budget ASR Evaluation

## Completion Rule

This feature can be marked `passes=true` only when the scripts compile, generated cases validate, at least one local Qwen3 MLX final-budget pilot run completes or a concrete local blocker is recorded, and evidence is appended to `specs/progress.md`.

## Acceptance Criteria

- A1: Controlled segment-budget cases can be regenerated from existing local WAV files.
- A2: Generated cases validate through the existing ASR harness case validator.
- A3: The Qwen3 MLX final/file-level run produces per-case timing and accuracy summaries.
- A4: The analysis output explains whether time, text length, or both should drive segmentation.
- A5: The analysis clearly labels synthetic cases as compute evidence only.

## Automated Checks

```bash
python3 -m py_compile eval/asr_streaming/prepare_segment_budget_cases.py
python3 -m py_compile eval/asr_streaming/analyze_segment_budget_results.py
python3 eval/asr_streaming/prepare_segment_budget_cases.py --dry-run
python3 eval/asr_streaming/prepare_segment_budget_cases.py
python3 eval/asr_streaming/run_eval.py validate-cases --cases eval/asr_streaming/cases.segment_budget.local.jsonl
PYTHONPATH=.external/repos/mlx-audio .venv-mimo/bin/python eval/asr_streaming/run_eval.py run --adapter mlx-stt-local --model-id qwen3-asr-0.6b-mlx-8bit --mlx-stt-model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit --mlx-stt-language Chinese --cases eval/asr_streaming/cases.segment_budget.local.jsonl --out-dir eval/asr_streaming/results/segment-budget-qwen3-mlx-0.6b-20260626
python3 eval/asr_streaming/analyze_segment_budget_results.py --summary eval/asr_streaming/results/segment-budget-qwen3-mlx-0.6b-20260626/summary.json --out-dir eval/asr_streaming/results/segment-budget-qwen3-mlx-0.6b-20260626-analysis
```

The concrete output directory may include a run suffix such as `-warmup-4x`; the command shape and required artifacts are the same.

## Manual Smoke Checks

- Read the generated `analysis.md` and confirm the recommendation does not imply changing App behavior before a follow-up implementation spec.

## Optional / Not-Applicable Checks

- Multiple repeated benchmark runs are recommended before final product thresholds, but not required for this first pilot feature.

## Evidence Required In `specs/progress.md`

- commands run;
- result paths;
- timing/accuracy table;
- segment-boundary recommendation and residual uncertainty.
