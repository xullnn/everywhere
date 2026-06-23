# Plan - Qwen3-ASR MLX Cumulative Service Prototype

## Implementation Sequence

1. Add `eval/asr_streaming/qwen3_mlx_cumulative_service.py`.
2. Implement a small service/session state machine around cumulative prefix recompute:
   - session token ownership
   - revision numbers
   - timed chunk input
   - stale result rejection
   - cancel and finish behavior
3. Reuse Qwen3 MLX loading and text extraction helpers from the existing probes.
4. Add a fake-backend self-test covering old session events, late partial after final, and cancel.
5. Add compile/self-test coverage to `eval/asr_streaming/validate.sh`.
6. Run smoke and `long_120_001` probes against Qwen3-ASR 0.6B MLX if local weights are available.
7. Update README, runtime feasibility notes, SDD progress, and PMB only after validation.

## Touched Areas

- `eval/asr_streaming/qwen3_mlx_cumulative_service.py`
- `eval/asr_streaming/README.md`
- `eval/asr_streaming/validate.sh`
- `eval/asr_streaming/runtime_feasibility.md`
- `specs/feature_matrix.json`
- `specs/progress.md`
- `specs/2026-06-22-qwen3-mlx-cumulative-service-prototype/*`
- `project_memory_bank/modules/asr_audio/summary.md` after validation if durable
- `project_memory_bank/core/current_focus.md` after validation if durable

## Validation Implementation Notes

- Self-tests should use a fake backend and not import or load MLX model weights.
- Runtime probes should be explicit commands in `validation.md`, not part of default `validate.sh`.
- Summaries should include both service-level gate fields and final ASR metrics.

## Risks And Mitigations

- Risk: cumulative recompute looks fast in serial probe but service-level finish/cancel semantics are unsafe.
  Mitigation: self-test stale-result and cancel behavior before runtime model probing.
- Risk: wrapper output is misread as native realtime streaming.
  Mitigation: summaries always set `native_realtime_gate_eligible=false`.
- Risk: runtime model loading makes routine validation slow.
  Mitigation: keep model-weight probes outside default validation.

## PMB Promotion Candidates

- Promote only after the prototype validates the service contract and produces stable runtime evidence.
