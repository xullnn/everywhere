# Plan - Segment Budget ASR Evaluation

## Implementation Sequence

1. Add `eval/asr_streaming/prepare_segment_budget_cases.py`.
2. Add `eval/asr_streaming/analyze_segment_budget_results.py`.
3. Generate a controlled case JSONL under `eval/asr_streaming/cases.segment_budget.local.jsonl` and WAV files under `eval/asr_streaming/audio/segment_budget/`.
4. Run `mlx-stt-local` with Qwen3-ASR MLX 0.6B 8bit on the generated cases.
5. Run the analysis script and record evidence in `specs/progress.md`.

## Touched Areas

- `eval/asr_streaming/prepare_segment_budget_cases.py`
- `eval/asr_streaming/analyze_segment_budget_results.py`
- `eval/asr_streaming/cases.segment_budget.local.jsonl`
- `eval/asr_streaming/audio/segment_budget/`
- `eval/asr_streaming/results/segment-budget-*`
- `specs/2026-06-26-segment-budget-asr-evaluation/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

## Validation Implementation Notes

- Use py_compile for new scripts.
- Validate generated JSONL with the existing `run_eval.py validate-cases`.
- Run a real local model pilot if `.venv-mimo`, `mlx-audio`, and the local Qwen3 0.6B 8bit model cache are available.

## PMB Promotion Candidates

- Durable segment-boundary recommendation after enough local evidence exists.

## Risks And Mitigations

- Risk: Silence-padded synthetic cases are not natural dictation.
  Mitigation: Use them only to isolate compute cost, not accuracy or UX quality.
- Risk: One pilot run may be noisy because model warmup and OS scheduling affect timing.
  Mitigation: Record it as pilot evidence and recommend repeat runs before final thresholds.
- Risk: Text length and audio duration are correlated in natural speech.
  Mitigation: Include same-text padded cases and silence-only cases to partially separate the variables.
