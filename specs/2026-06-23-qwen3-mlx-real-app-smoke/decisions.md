# Decisions - Qwen3-ASR MLX Real App Smoke

## Confirmed Decisions

- D1: Use a foreground smoke script, not production service supervision.
- D2: Keep Qwen3 HTTP optional and explicitly selected; FunASR WebSocket remains default.
- D3: Automated validation uses dry-run mode so CI-style checks do not load a large model or launch the UI.
- D4: Real validation requires manual macOS app checks because global hotkeys, focus, Accessibility, pasteboard, and microphone behavior cannot be fully proven by unit tests.
- D5: The setup script may create `.venv-mimo` with conda Python 3.12 when the default `python3` is outside the previously validated 3.10-3.12 range.

## Open Questions / Unresolved Choices

- Q1: Whether production service supervision should live inside the Swift app, a helper process, or a LaunchAgent.
- Q2: Whether real app smoke reveals latency or focus behavior that requires client-side timeout or UI changes before broader use.

## PMB Promotion Candidates

- Promote only after real manual app smoke validates the optional Qwen3 path as a durable app workflow.
