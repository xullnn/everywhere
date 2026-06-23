# Validation — ASR Recording CLI

## Completion rule

This feature can be marked `passes=true` when static checks pass and the CLI can perform dry-run/device-list setup. A real microphone recording is a manual smoke check because it requires interactive user permission and input.

## Acceptance criteria

- A1: `bash scripts/record_asr_cases.sh` starts the recording tool with useful defaults.
- A2: Missing `cases.local.jsonl` is created from the first 10 template cases.
- A3: The tool records or plans output to `eval/asr_streaming/audio/<case_id>.wav`.
- A4: The implementation does not affect the macOS app runtime.
- A5: The tool can list available avfoundation audio devices.

## Automated checks

```bash
python3 -m py_compile eval/asr_streaming/record_cases.py
bash eval/asr_streaming/validate.sh
bash scripts/record_asr_cases.sh --dry-run
bash scripts/record_asr_cases.sh --list-devices
swift build
swift test
```

## Manual smoke checks

- Run `bash scripts/record_asr_cases.sh`.
- Grant microphone permission if macOS prompts.
- Record one case.
- Validate `eval/asr_streaming/audio/<case_id>.wav` with `python3 eval/asr_streaming/run_eval.py validate-cases --cases eval/asr_streaming/cases.local.jsonl`.

## Optional / not-applicable checks

- Browser UI is out of scope for this feature.

## Evidence required in `specs/progress.md`

- Commands run and results.
- Whether real microphone recording was skipped or completed.
