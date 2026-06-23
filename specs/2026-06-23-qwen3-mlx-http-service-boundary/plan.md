# Plan - Qwen3-ASR MLX HTTP Service Boundary

## Implementation Sequence

1. Allow `CumulativeRecomputeService.start(...)` to accept an externally supplied session token.
2. Add `eval/asr_streaming/qwen3_mlx_http_service.py`.
3. Implement fake-backend mode first, then real Qwen3 MLX mode behind the same HTTP endpoints.
4. Add service health/startup metadata so smoke scripts can confirm the server is ready.
5. Add a helper script to start the service and run `incremental_ux_gate.py --adapter http-json` against it.
6. Extend `eval/asr_streaming/validate.sh` to compile the new service script.
7. Run lightweight validation and, when local model/environment are available, run Qwen3 0.6B MLX smoke and long-form gate cases.
8. Record evidence in `specs/progress.md`.

## Touched Areas

- `eval/asr_streaming/qwen3_mlx_cumulative_service.py`
- `eval/asr_streaming/qwen3_mlx_http_service.py`
- `eval/asr_streaming/validate.sh`
- `scripts/run_qwen3_mlx_http_gate_smoke.sh`
- `specs/2026-06-23-qwen3-mlx-http-service-boundary/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

## Validation Implementation Notes

- Fake-backend HTTP gate is required and should be fast.
- Real-model gate is required when `.external/models/mlx-community__Qwen3-ASR-0.6B-8bit`, `.external/repos/mlx-audio`, and the project MLX Python environment are available.
- If the real model cannot run because of missing local files or Python dependencies, record the skipped/blocked reason.

## PMB Promotion Candidates

- Promote only after a real Qwen3 HTTP service pass is stable enough to become durable project knowledge.

## Risks And Mitigations

- Risk: The service token differs from the gate token, causing false stale-event behavior.
  Mitigation: Use the client-provided `session_token` as the service session token.
- Risk: The first service is synchronous and can block HTTP request handling.
  Mitigation: Accept this for gate validation; record async scheduling as a follow-up before Swift integration.
- Risk: Fake service evidence is mistaken for real ASR evidence.
  Mitigation: Separate fake-backend smoke from real Qwen3 smoke in output directories and progress notes.
