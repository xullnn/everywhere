# Decisions — ASR Recording CLI

## Confirmed decisions

- D1: Implement a terminal-first one-command recording flow before building any browser UI.
- D2: Use `ffmpeg` + macOS `avfoundation` because `ffmpeg` is already installed locally.
- D3: Record directly to 16 kHz mono signed 16-bit WAV so no separate conversion step is required.
- D4: Use the first 10 template cases as the default pilot set.

## Open questions / unresolved choices

- Whether a future browser UI is worth adding after the CLI flow is tested.
- Whether the default audio device should be changed if the user prefers an external microphone.

## PMB promotion candidates

- Promote the one-command recording entry point after validation.
