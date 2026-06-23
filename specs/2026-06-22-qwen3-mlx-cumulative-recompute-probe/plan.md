# Plan - Qwen3-ASR MLX Cumulative Recompute Probe

## Implementation Sequence

1. Add `eval/asr_streaming/qwen3_mlx_cumulative_probe.py`.
2. Reuse existing WAV validation, case loading, CER/WER, metadata, JSON, and text-stability helpers from `run_eval.py`.
3. Reuse Qwen3 MLX model loading and API-surface classification from `qwen3_mlx_realtime_probe.py`.
4. Implement cumulative-prefix runs with configurable prefix step, maximum prefixes, and case filtering.
5. Record per-case and aggregate JSON summaries.
6. Add script compile/self-test coverage to `eval/asr_streaming/validate.sh`.
7. Run smoke and at least one long-form local probe if local model weights are available.
8. Record validation evidence and update the feature matrix.

## Touched Areas

- `eval/asr_streaming/qwen3_mlx_cumulative_probe.py`
- `eval/asr_streaming/README.md`
- `eval/asr_streaming/validate.sh`
- `eval/asr_streaming/runtime_feasibility.md`
- `eval/asr_streaming/model_registry.json`
- `specs/feature_matrix.json`
- `specs/progress.md`
- `specs/2026-06-22-qwen3-mlx-cumulative-recompute-probe/*`

## Risk Controls

- The probe will explicitly report `native_realtime_gate_eligible=false`.
- The final recommendation will keep `use_as_app_realtime_backend_now=false`.
- Any promising result is only evidence for a future local service prototype with scheduling, cancellation, stale-result isolation, and an equivalent realtime gate.

## PMB Promotion Candidates

- Promote only the stable conclusion about Qwen3-ASR MLX cumulative recompute feasibility after validation.
