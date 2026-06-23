# Plan - Incremental UX Real Backend Adapters

## Implementation Sequence

1. Add an HTTP JSON transport backend to `incremental_ux_gate.py`.
2. Add CLI options for service URL and request timeout.
3. Map service response events into the existing `IncrementalSessionService` accepted/ignored event model.
4. Add a small controlled fake HTTP incremental ASR service under `eval/asr_streaming/`.
5. Add validation commands that start the fake service, run the gate against it, and preserve existing fake self-tests.
6. Update `eval/asr_streaming/validate.sh` to compile the new fake service script.
7. Record evidence in `specs/progress.md`.

## Touched Areas

- `eval/asr_streaming/incremental_ux_gate.py`
- `eval/asr_streaming/fake_incremental_http_service.py`
- `eval/asr_streaming/validate.sh`
- `specs/2026-06-23-incremental-ux-real-backend-adapters/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

## Validation Implementation Notes

- Use standard Python only.
- The fake service is only a transport/process-boundary validator; it is not a model-quality signal.
- The real-model features that follow this work must still implement their own local service and run the same gate.

## PMB Promotion Candidates

- None until a real backend service passes and the role decision becomes durable.

## Risks And Mitigations

- Risk: A fake HTTP service is mistaken for model evidence.
  Mitigation: Requirements and summaries must state that it validates transport only.
- Risk: The new adapter bypasses existing event-safety checks.
  Mitigation: Normalize all backend events through `IncrementalSessionService.emit_partial` and `emit_final`.
- Risk: Transport schema drifts before Qwen service work starts.
  Mitigation: Keep request/response fields explicit and small.
