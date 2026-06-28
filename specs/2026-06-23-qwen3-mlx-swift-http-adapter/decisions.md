# Decisions - Qwen3-ASR MLX Swift HTTP Adapter

## Confirmed Decisions

- D1: Implement the first Swift adapter as a client for an already running local HTTP service, not as a service supervisor.
- D2: Keep FunASR WebSocket as the default backend unless the user explicitly selects the local HTTP backend.
- D3: Use loopback-only URL validation by default to preserve the local-first privacy boundary.
- D4: Preserve the existing `AppController` session id and ASR client identity checks; the new adapter adds token filtering but does not replace app-level guards.
- D5: Automated completion uses fake transport tests, not a live Qwen3 model, so tests stay fast and deterministic.
- D6: `cancel()` must be non-blocking for UI safety. It immediately clears callbacks and marks the client cancelled, then posts `/cancel` best-effort on the client queue.

## Open Questions / Unresolved Choices

- Q1: Whether the production backend transport should remain HTTP JSON, switch to WebSocket, or use a macOS-native IPC after real app smoke testing.
- Q2: What exact RSS/CPU/cold-start thresholds should block making Qwen3 HTTP the default backend.
- Q3: How to handle long code-switch technical terms before enabling Qwen3 as the default user-facing backend.

## PMB Promotion Candidates

- The Swift adapter boundary and backend selection flags after the feature is validated.
