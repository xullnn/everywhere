# Decisions - Qwen3-ASR MLX HTTP Service Boundary

## Confirmed Decisions

- D1: Use HTTP JSON for the first real Qwen3 service boundary because the canonical gate already supports it.
- D2: Keep cumulative recompute marked as non-native realtime streaming even if it passes user-perceived incremental UX gates.
- D3: Use the gate-provided `session_token` inside the service to keep stale-event behavior meaningful across process boundaries.
- D4: Include fake-backend mode so transport regressions can be tested without loading MLX weights.
- D5: Do not touch Swift App integration in this feature.
- D6: Use a single-threaded Python `HTTPServer` for the first Qwen3 MLX service boundary. MLX raised `There is no Stream(gpu, 1) in current thread` when the model was loaded in the main thread and inference ran in a `ThreadingHTTPServer` request thread.

## Open Questions / Unresolved Choices

- Q1: Whether the eventual production service should remain synchronous HTTP, move to WebSocket, or add an async worker queue while keeping MLX inference on its owning thread.
- Q2: What RSS threshold is acceptable after real Qwen3 service memory is measured.

## PMB Promotion Candidates

- If real Qwen3 HTTP gate passes, promote the service contract shape and next integration constraints after SDD closeout.
