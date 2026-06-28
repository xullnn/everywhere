# Requirements - Qwen3-ASR MLX Segmented-Cache App Smoke

## Problem

The segmented-cache Qwen3-ASR MLX service prototype now exposes the same local HTTP `start/chunk/finish/cancel` contract as the cumulative wrapper while internally committing bounded segments and caching audio. The macOS App already has a local HTTP ASR client, but it has not been validated against the segmented-cache service in a user-facing App smoke path.

The next step is to make this backend easy to launch for manual App smoke testing without changing the App default backend or weakening output safety.

## Scope

### IN

- Add a repeatable script that starts the segmented-cache service and launches `LocalVoiceInputMac` against it.
- Keep the service manually supervised by the smoke script for this feature.
- Reuse existing `LocalHTTPASRClient` and CLI flags:
  - `--local-http-asr`
  - `--asr-http-url`
- Confirm the Swift HTTP client tolerates segmented service diagnostic events such as `segment_final` while only surfacing user-visible `partial/final`.
- Record exact manual smoke steps for Notes, browser input, no-input clipboard fallback, Esc cancel, and long draft mode.
- Preserve all existing paste, focus, clipboard, hotkey, and floating-panel behavior.

### OUT

- No default backend switch.
- No App-managed Python service supervision.
- No LaunchAgent/login item/background daemon.
- No new IPC protocol beyond existing local HTTP JSON.
- No change to focus detection, paste engine, clipboard manager, hotkeys, or floating panel behavior.
- No cloud upload, remote ASR, or LLM correction.
- No attempt to solve production segment boundary, deduplication, or crash-recovery UX in this feature.

## Requirements

- R1: The smoke script must verify local runtime paths before launching the service.
- R2: The smoke script must start `qwen3_mlx_segmented_cache_service.py serve` with configurable host, port, model, language, and segment policy.
- R3: The script must wait for `/health` before launching the App.
- R4: The script must launch the App with `--local-http-asr --asr-http-url <service-url>`.
- R5: The script must write service logs, app logs, and run metadata under `eval/asr_streaming/results/`.
- R6: The script must clean up the child service process when the App exits or the script is interrupted.
- R7: The Swift HTTP client must ignore unsupported diagnostic events and still emit valid partial/final events.
- R8: Automated validation must pass without requiring manual microphone interaction.
- R9: Manual validation must be explicitly recorded before this path is considered ready for broader product use.

## Constraints

- Local-only execution.
- Default App config remains FunASR WebSocket.
- Existing local HTTP loopback restriction remains in place.
- Segmented service is not native realtime model evidence; it remains a wrapper service.

## Dependencies

- `2026-06-23-qwen3-mlx-swift-http-adapter`
- `2026-06-23-qwen3-mlx-real-app-smoke`
- `2026-06-26-qwen3-mlx-segmented-cache-service`

## Related PMB context

- `project_memory_bank/core/project_brief.md`
- `project_memory_bank/core/system_overview.md`
- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/modules/macos_app/summary.md`
- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/modules/output_safety/summary.md`
