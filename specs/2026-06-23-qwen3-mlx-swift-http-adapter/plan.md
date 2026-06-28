# Plan - Qwen3-ASR MLX Swift HTTP Adapter

## Implementation Sequence

1. Add backend selection to `AppConfig`, keeping FunASR WebSocket as the default unless explicitly configured.
2. Add a Swift local HTTP ASR client that conforms to `ASRClientProtocol`.
3. Keep request construction, response decoding, token filtering, and local-loopback URL validation in small testable units.
4. Update `AppController.startASR(...)` to choose Mock, FunASR, or local HTTP based on config/CLI flags.
5. Add tests using a fake URL loading layer so request/response behavior is validated without loading Qwen3 or starting Python.
6. Run Swift build/test and the existing ASR eval validation.
7. Optionally run the real Qwen3 HTTP service smoke from the app only after the local service is already running; manual app smoke remains separate from automated completion.

## Touched Areas

- `Sources/LocalVoiceInputMac/AppConfig.swift`
- `Sources/LocalVoiceInputMac/AppController.swift`
- `Sources/LocalVoiceInputMac/ASRClientProtocol.swift`
- `Sources/LocalVoiceInputMac/LocalHTTPASRClient.swift`
- `Package.swift`
- `Tests/LocalVoiceInputMacTests/*`
- `specs/2026-06-23-qwen3-mlx-swift-http-adapter/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

## Validation Implementation Notes

- Use a fake `URLProtocol` or injectable HTTP transport for unit tests.
- Tests should prove that cancel nils callbacks and rejects late responses.
- Tests should prove token mismatch is ignored before creating `ASREvent`.
- Tests should prove final output is not emitted merely because `/chunk` returns partials.
- Live Qwen3 model loading is not required for the first automated Swift adapter validation.

## PMB Promotion Candidates

- Promote the final Swift adapter boundary only after validation and after it becomes the durable default path or durable optional backend.

## Risks And Mitigations

- Risk: The Swift client accidentally permits non-local service URLs.
  Mitigation: Validate loopback URLs before creating network requests.
- Risk: HTTP callbacks from a cancelled session reach the app.
  Mitigation: Keep per-client active token state and nil callbacks on cancel, plus preserve `AppController` client identity checks.
- Risk: Tests depend on a running Qwen3 Python service.
  Mitigation: Use fake transport tests for completion; keep real-service app smoke optional/manual.
- Risk: Service startup/supervision scope expands.
  Mitigation: Record it as `FUP-001` and keep this feature client-only.
