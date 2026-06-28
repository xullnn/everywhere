# Decisions - Qwen3-ASR MLX Segmented-Cache App Smoke

## Confirmed Decisions

- D1: Use the existing `LocalHTTPASRClient` and CLI flags for this smoke path.
- D2: Keep the default App backend as FunASR WebSocket.
- D3: The service is manually supervised by the smoke script in this feature.
- D4: App UI consumes only `partial/final`; segmented service diagnostics remain internal.
- D5: Automated checks validate script/config/client compatibility; real UI paste behavior remains a manual smoke requirement.

## Open Questions / Unresolved Choices

- Should App-managed service supervision use a child process, LaunchAgent, or external user-managed service in the next feature?
- Should long draft mode eventually write committed segments incrementally, or continue final-only insertion?
- How should cached audio/text be surfaced if the service or App crashes mid-dictation?

## Rejected For This Feature

- Defaulting the App to segmented-cache Qwen3.
- LaunchAgent or background daemon installation.
- Changing output safety logic to accommodate the new backend.
- Adding overlap deduplication or segment-boundary quality tuning.
