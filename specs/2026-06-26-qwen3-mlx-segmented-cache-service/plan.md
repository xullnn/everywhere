# Plan - Qwen3-ASR MLX Segmented Cache Service Prototype

## Implementation Sequence

1. Create this SDD feature contract and add it to `specs/feature_matrix.json`.
2. Add `eval/asr_streaming/qwen3_mlx_segmented_cache_service.py`.
3. Implement an in-process segmented service:
   - session token lifecycle;
   - chunk ingestion;
   - local audio cache;
   - live partial generation for the active segment;
   - segment commit and merge;
   - finish/cancel semantics.
4. Add fake-backend self-tests covering stale events, cancel, cache writes, segment commit, and final merge.
5. Add an optional HTTP server mode matching the current JSON boundary.
6. Run fake HTTP service through `incremental_ux_gate.py --adapter http-json`.
7. Run real Qwen3 MLX pilot if local runtime is available and time permits.
8. Record validation evidence in `specs/progress.md` and update `specs/feature_matrix.json`.

## Touched Areas

- `eval/asr_streaming/qwen3_mlx_segmented_cache_service.py`
- `eval/asr_streaming/README.md`
- `eval/asr_streaming/results/qwen3-mlx-segmented-cache-service-*`
- `specs/2026-06-26-qwen3-mlx-segmented-cache-service/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

## Validation Notes

- Use `python3 -m py_compile` for syntax validation.
- Use `self-test` before model-backed commands.
- Use fake HTTP mode plus `incremental_ux_gate.py --adapter http-json` to validate the transport contract without model weights.
- Keep real-model validation small; broader quality thresholds belong to the previous segmented-cache evaluation harness.

## PMB Promotion Candidates

- After validation, promote the durable architecture direction: long dictation should use a local ASR service with bounded segment commit and durable local audio cache, while Swift remains the lightweight interaction layer.

## Risks and Mitigations

- Risk: Segment boundary choices are still naive.
  Mitigation: Keep policy configurable and record diagnostics; do not wire into App defaults yet.
- Risk: Segment concatenation can duplicate or miss text near boundaries.
  Mitigation: Default to zero overlap and record merge strategy; add dedup/alignment as a later spec.
- Risk: HTTP fake mode can pass protocol checks without proving model quality.
  Mitigation: Label fake validation as transport/session evidence only.
- Risk: Running model finalization inside a single worker can backlog under long input.
  Mitigation: Record compute wall time and backlog fields; use future evidence to tune segment size.
