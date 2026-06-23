# Plan - Qwen3-ASR MLX HTTP Resource And Extended Gate Validation

## Implementation Sequence

1. Add a long-case JSONL subset for existing recordings.
2. Add a resource sampler that can monitor an existing PID and write JSONL plus summary JSON.
3. Add a one-command Qwen3 MLX HTTP extended gate runner that starts the service, starts the sampler, runs the gate, stops both processes, and writes summary metadata.
4. Run syntax/self-tests and the existing eval harness validation.
5. Run the extended Qwen3 0.6B MLX HTTP gate on the long-case subset when the local MLX runtime is available.
6. Record validation evidence and risks in `specs/progress.md`.

## Touched Areas

- `eval/asr_streaming/cases.extended.local.jsonl`
- `eval/asr_streaming/monitor_pid_resources.py`
- `scripts/run_qwen3_mlx_http_extended_gate.sh`
- `specs/2026-06-23-qwen3-mlx-http-resource-validation/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

## Validation Implementation Notes

- The extended gate should reuse `incremental_ux_gate.py` instead of adding a new transcript scoring path.
- Resource sampling should keep running while the gate is active and include service startup/model-load phase when possible.
- If a long case fails the gate, record the fail reasons and do not weaken gate logic to force a pass.

## PMB Promotion Candidates

- Promote only durable conclusions: whether extended Qwen3 HTTP gates are viable and any resource caveats that affect Swift integration.

## Risks And Mitigations

- Risk: Long realtime gates take several minutes.
  Mitigation: Use existing three-case subset first; keep broader runs as follow-up.
- Risk: `ps` output varies across platforms.
  Mitigation: Target macOS because this is a macOS local app project and parse conservative fields only.
- Risk: Resource metrics are noisy.
  Mitigation: Record peak and mean values with sample count rather than treating one sample as definitive.
