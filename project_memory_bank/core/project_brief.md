# Project Brief

LocalVoiceInput is a local-first macOS voice input MVP for universal dictation across apps.

The current product form is a menu-bar app, not an InputMethodKit input method. Users hold Right Option for push-to-talk dictation, use Option+Space for long-draft mode, and press Esc to cancel the active session. Partial text is shown only in a non-focus-stealing floating panel. Final text is routed to the current cursor or clipboard after the user stops recording.

Primary target hardware is a MacBook Pro M4 with 48 GB memory. The project prioritizes local operation, privacy, safety, not losing dictated text, avoiding unintended paste, and avoiding clipboard pollution.

Non-goals for the current MVP:

- Do not migrate to InputMethodKit yet.
- Do not introduce cloud ASR or upload audio/text by default.
- Do not enable LLM correction by default.
- Do not auto-send messages.
- Do not write partial text into the active app.

The ASR backbone is intended to be local FunASR WebSocket 2-pass: online results drive floating-panel partials, and offline results refine final segments. Offline segment events must not finalize a user session before the user releases the shortcut or stops long-draft mode.
