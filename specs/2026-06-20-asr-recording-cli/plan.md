# Plan — ASR Recording CLI

## Implementation sequence

1. Add `eval/asr_streaming/record_cases.py`.
2. Add wrapper `scripts/record_asr_cases.sh`.
3. Update `eval/asr_streaming/README.md` with one-command usage.
4. Extend `eval/asr_streaming/validate.sh` to syntax-check the recording tool.
5. Run static validation and existing Swift checks.

## Touched areas

- `eval/asr_streaming/`
- `scripts/`
- `specs/`

## Validation implementation notes

- Required:
  - `python3 -m py_compile eval/asr_streaming/record_cases.py`
  - `bash eval/asr_streaming/validate.sh`
  - `bash scripts/record_asr_cases.sh --dry-run`
  - `bash scripts/record_asr_cases.sh --list-devices`
  - `swift build`
  - `swift test`
- Manual:
  - Run `bash scripts/record_asr_cases.sh` and record one sample after granting microphone permission.

## PMB promotion candidates

- Record the stable one-command recording entry point after validation.

## Risks and mitigations

- Risk: macOS microphone permission blocks ffmpeg.
  Mitigation: provide explicit error message and device-list command.
- Risk: wrong audio device selected.
  Mitigation: support `--list-devices` and `--audio-device`.
- Risk: accidental overwrite.
  Mitigation: skip existing recordings by default unless user chooses rerecord.
