# Requirements — ASR Recording CLI

## Problem

The user needs a one-command guided recording flow for ASR evaluation cases. Manual file naming, directory setup, audio conversion, and case selection are too error-prone.

## Scope

### IN

- Add a command-line recording tool under `eval/asr_streaming/`.
- Add a wrapper script so the user can start with one command.
- Automatically create `cases.local.jsonl` from the first 10 lines of `cases.local.template.jsonl` when missing.
- Automatically create required audio directories.
- Display one case at a time with the exact text to read.
- Record directly to 16 kHz mono signed 16-bit WAV files named by case id.
- Support skip, rerecord, quit, and device listing.
- Validate produced WAV metadata.

### OUT

- Do not modify the macOS app runtime.
- Do not add a browser UI in this feature.
- Do not upload audio or text.
- Do not automatically run ASR evaluation after recording unless the user explicitly runs it.

## Requirements

- R1: `bash scripts/record_asr_cases.sh` starts the guided recording flow.
- R2: The tool must create `eval/asr_streaming/cases.local.jsonl` from the pilot template when it does not exist.
- R3: The tool must save audio as `eval/asr_streaming/audio/<case_id>.wav`.
- R4: Output audio must be 16 kHz, mono, signed 16-bit WAV.
- R5: Existing recordings must not be overwritten without an explicit user action.
- R6: The tool must give actionable errors for missing `ffmpeg`, microphone permission failure, or device selection failure.
- R7: The tool must remain local-only.

## Constraints

- Use `ffmpeg` with macOS `avfoundation` for microphone capture.
- Default audio input is `:0`, matching the current MacBook Pro microphone listing.
- Keep the implementation Python standard-library only, except for invoking the installed `ffmpeg` binary.

## Dependencies

- `ffmpeg` at `/opt/homebrew/bin/ffmpeg` or otherwise available on `PATH`.
- macOS microphone permission for the terminal process used to run the script.

## Related PMB context

- `project_memory_bank/modules/asr_audio/summary.md`
