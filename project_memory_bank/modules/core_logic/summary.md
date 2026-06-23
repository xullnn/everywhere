# Core Logic Module

`Sources/LocalVoiceInputCore` owns platform-independent behavior.

Stable responsibilities:

- Voice session state transitions.
- Hotkey state machine for Right Option, Option+Space, and Esc behavior.
- Focus snapshot data model and sticky focus-change detection.
- Output mode routing based on focus, session type, policy, secure fields, and focus changes.
- ASR event disposition so online partials update the floating panel and offline segments do not finalize until user stop.
- Transcript merging with stale-session and late-partial protection.
- Rule-based correction, hotword correction, homophone correction, and history reduction.

Tests live under `Tests/LocalVoiceInputCoreTests` and cover most pure logic contracts.

Go Deeper:

- See `../../core/system_overview.md` for the runtime flow.
- See `../../integration/output_safety_flow.md` for output routing constraints.
