# Decisions - Incremental UX Real Backend Adapters

## Confirmed Decisions

- D1: Use HTTP JSON over localhost as the first real transport seam because it is backend-neutral, standard-library friendly, and easy for future Python model services to implement.
- D2: Transfer PCM in base64 JSON for the first implementation. This is not the most efficient transport, but it is sufficient for gate validation and avoids adding dependencies.
- D3: The fake HTTP service validates process/transport behavior only. It is not ASR model evidence.
- D4: Real Qwen3, MiMo, FunASR, or other services must be implemented in separate features and run through the same adapter before model-role decisions.

## Open Questions / Unresolved Choices

- Q1: Whether the future production model service should remain HTTP JSON, switch to WebSocket, or use another local IPC after the gate contract is proven.

## PMB Promotion Candidates

- None until a real backend uses this transport seam and the pattern becomes durable.
