# Requirements - Qwen3-ASR MLX Swift HTTP Adapter

## Problem

The Qwen3-ASR MLX 0.6B cumulative service now works behind a local HTTP process boundary, but the macOS app still only has `MockASRClient` and `FunASRClient`. LocalVoiceInput needs a Swift-side ASR client that can talk to the already validated localhost HTTP service while preserving the existing app safety rules: no cloud upload, no partial insertion into the active app, cancel safety, stale-session isolation, and final-only paste/copy routing.

## Scope

### IN

- Add a Swift HTTP ASR client that conforms to the existing `ASRClientProtocol`.
- Support the current local service endpoints: `/health`, `/start`, `/chunk`, `/finish`, and `/cancel`.
- Send 16 kHz mono int16 PCM chunks as base64 JSON to localhost.
- Emit `ASREvent` partial/final callbacks that flow through the existing `AppController` session ownership checks.
- Add config/CLI selection for the local HTTP backend without removing FunASR WebSocket or Mock ASR.
- Add tests for HTTP request/response mapping, session token handling, final-only-after-finish behavior, cancel behavior, stale response rejection, and error surfacing.
- Keep existing focus, paste, clipboard, hotkey, floating-panel, correction, and history behavior unchanged.

### OUT

- No automatic Python/Qwen3 service launch or restart manager in this feature.
- No LaunchAgent, packaging, login item, or background daemon work.
- No InputMethodKit migration.
- No cloud ASR, remote inference, or audio/text upload.
- No LLM correction enabled by default.
- No partial text insertion into the active input field.
- No replacement of FunASR as fallback.
- No technical-term correction implementation beyond preserving existing hotword/correction pipeline behavior.

## Requirements

- R1: The Swift adapter must only accept `http://127.0.0.1`, `http://localhost`, or equivalent local loopback service URLs by default.
- R2: The adapter must create an internal session token when `start(sessionId:hotwords:)` is called and must ignore backend events whose token does not match the active token.
- R3: The adapter must POST `/start` with `session_id`, `session_token`, hotwords, and audio metadata.
- R4: `sendPCM(_:)` must POST `/chunk` with `session_id`, `session_token`, chunk index, and base64 PCM bytes.
- R5: `finish()` must POST `/finish` and only backend final events returned from or after finish may become final `ASREvent` callbacks.
- R6: `cancel()` must POST `/cancel` when possible and must prevent later callbacks from reaching `AppController`.
- R7: Transport errors, malformed JSON, unsupported service URLs, and non-2xx responses must call `onError` for the active session only.
- R8: Existing `AppController` session id plus client identity checks must remain the final guard against stale callbacks.
- R9: The first implementation may connect only to an already running local service; app-managed service supervision is a follow-up.
- R10: The feature must preserve successful `swift build`, `swift test`, and existing eval harness validation.

## Constraints

- Use Foundation networking only; do not add a package dependency.
- Keep the wire protocol compatible with `eval/asr_streaming/qwen3_mlx_http_service.py`.
- Do not weaken existing output safety behavior.
- Keep the adapter local-first and privacy-preserving.
- Prefer testable protocol/transport seams over live network-only tests.

## Dependencies

- `2026-06-23-qwen3-mlx-http-service-boundary`
- `2026-06-23-qwen3-mlx-http-resource-validation`
- `2026-06-22-asr-backend-selection-roadmap`

## Related PMB Context

- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/modules/macos_app/summary.md`
- `project_memory_bank/modules/output_safety/summary.md`
- `project_memory_bank/core/system_overview.md`
