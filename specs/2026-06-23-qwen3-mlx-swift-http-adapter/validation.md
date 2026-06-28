# Validation - Qwen3-ASR MLX Swift HTTP Adapter

## Completion Rule

This feature can be marked `passes=true` only when the Swift adapter is implemented, automated tests pass without a live Qwen3 service, existing Swift and eval checks pass, and evidence is recorded in `specs/progress.md`. Real Qwen3 app smoke is optional for this feature because service supervision and manual app validation are separate follow-ups.

## Acceptance Criteria

- A1: `LocalHTTPASRClient` conforms to `ASRClientProtocol`.
- A2: Config/CLI can select the local HTTP backend explicitly without changing the default FunASR WebSocket behavior.
- A3: The adapter rejects non-loopback HTTP service URLs by default.
- A4: `/start`, `/chunk`, `/finish`, and `/cancel` requests include the active session id and session token.
- A5: Partial events before finish are emitted as `.online` non-final `ASREvent` values.
- A6: Final events are emitted only from finish/post-finish responses and become `.offline` final `ASREvent` values.
- A7: Token-mismatched or stale backend events are ignored.
- A8: `cancel()` suppresses late callbacks and attempts `/cancel` best-effort.
- A9: Existing Mock ASR and FunASR WebSocket paths still compile.
- A10: No focus, paste, clipboard, floating-panel, hotkey, or output safety behavior is weakened.

## Automated Checks

```bash
swift build
swift test
bash eval/asr_streaming/validate.sh
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-23-qwen3-mlx-swift-http-adapter/feature.json >/dev/null
```

## Optional / Not Applicable Checks

- Real Qwen3 app smoke against `http://127.0.0.1:18107` is optional in this feature because the Python service must already be running and user-facing app permission/manual validation belongs to the next integration smoke.
- Service launch, restart, and LaunchAgent validation are not applicable in this feature.

## Evidence Required In `specs/progress.md`

- Commands run and pass/fail/skipped results.
- Added Swift tests and what they cover.
- Explicit statement that output safety code paths were not weakened.
- Any skipped real-service app smoke reason.
