# Requirements - Qwen3-ASR MLX Real App Smoke

## Problem

The Swift app can now select `LocalHTTPASRClient`, and the Qwen3-ASR MLX 0.6B HTTP service has passed backend gates. The next risk is user-facing integration: the app must be run against the real local Qwen3 service in actual macOS apps without weakening focus, paste, clipboard, hotkey, cancellation, or floating-panel safety behavior.

## Scope

### IN

- Add a one-command smoke runner that starts the local Qwen3 MLX HTTP service and launches `LocalVoiceInputMac` with `--local-http-asr`.
- Add a reproducible Qwen3 MLX runtime setup command for the local Python service dependency.
- Keep the Qwen3 service foreground-owned by the smoke script so it is cleaned up when the app exits.
- Write service logs and smoke metadata under `eval/asr_streaming/results/`.
- Provide a dry-run mode for automated validation without loading the model or launching the UI.
- Document the exact manual smoke checklist for real macOS apps and safety flows.
- Keep Qwen3 optional; do not change the app default backend.

### OUT

- No automatic LaunchAgent, login item, daemon, or restart supervisor.
- No packaged `.app` default switch to Qwen3.
- No InputMethodKit migration.
- No cloud ASR, remote inference, or audio/text upload.
- No LLM correction enabled by default.
- No technical-term correction work.
- No weakening of output safety rules.

## Requirements

- R1: The smoke command must start `eval/asr_streaming/qwen3_mlx_http_service.py` with local model paths only.
- R2: The smoke command must wait for `/health` before launching the Swift app.
- R3: The Swift app launch command must use `--local-http-asr --asr-http-url http://127.0.0.1:<port>`.
- R4: The smoke command must clean up the Qwen3 service when the app exits or the script is interrupted.
- R5: The smoke command must write service logs and run metadata under a timestamped result directory.
- R6: Dry-run mode must verify command construction and local path checks without starting the model or app.
- R7: The manual smoke checklist must cover Right Option, Option+Space, Esc, focused input auto-paste, no-input clipboard draft, secure-field clipboard fallback, focus-change downgrade, paste failure fallback, clipboard restore, and no partial insertion into the active app.
- R8: This feature can be `implemented` after script/docs/automated checks pass, but can only be `validated` after real manual app smoke evidence is recorded.
- R9: The runtime setup command must recreate `.venv-mimo` or clearly fail with missing model/source/Python prerequisites.

## Constraints

- Preserve FunASR WebSocket as the default backend.
- Keep all runtime work local/offline after cached model files are present.
- Keep user-facing test artifacts out of Git when they contain local audio or private text.

## Dependencies

- `2026-06-23-qwen3-mlx-swift-http-adapter`
- `2026-06-23-qwen3-mlx-http-service-boundary`
- `2026-06-23-qwen3-mlx-http-resource-validation`

## Related PMB Context

- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/modules/macos_app/summary.md`
- `project_memory_bank/modules/output_safety/summary.md`
