# Decisions - Qwen3-ASR MLX Cumulative Service Prototype

## Confirmed Decisions

- D1: Prototype the service contract in-process first; do not add an HTTP/WebSocket server until session semantics pass.
- D2: Use cumulative recompute as a wrapper strategy only; do not mark Qwen3-ASR MLX as native realtime-gate eligible.
- D3: Use one model load per CLI run so runtime probes approximate a long-running local service more closely than repeated cold starts.
- D4: Keep default validation model-free by using a fake backend for service-state self-tests.
- D5: The in-process service prototype passes smoke and `long_120_001` service gates with Qwen3-ASR 0.6B MLX, but it is still not a process boundary suitable for Swift integration.
- D6: Service summaries distinguish `service_gate_passed=true` from `native_realtime_gate_eligible=false` so wrapper feasibility is not confused with model-native streaming.

## Open Questions / Unresolved Choices

- Whether to expose the eventual service over WebSocket, local HTTP, or stdin/stdout JSON once the in-process service contract passes.
- Whether final generation should preempt queued partial jobs in the production service or wait for a single worker to drain.
- Whether a 500ms prefix step improves perceived partial latency enough to justify extra compute.

## Follow-up candidates

- FUP-001: Add a real local service process boundary such as WebSocket, local HTTP, or stdin/stdout JSON.
- FUP-002: Probe 500ms cumulative prefix cadence.

## PMB Promotion Candidates

- Promote the validated service contract shape and any stable runtime conclusion after closeout.
