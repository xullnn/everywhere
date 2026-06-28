# Validation - Qwen3-ASR MLX Real App Smoke

## Completion Rule

This feature can be marked `implemented` after the smoke runner, documentation, and automated checks pass. It can be marked `validated` with `passes=true` only after real manual macOS app smoke evidence is recorded.

## Acceptance Criteria

- A1: `scripts/run_qwen3_mlx_app_smoke.sh` exists and has a dry-run mode.
- A2: The runner starts the local Qwen3 HTTP service and waits for `/health` before launching the app when not in dry-run mode.
- A3: The app command uses `swift run LocalVoiceInputMac --local-http-asr --asr-http-url <service-url>`.
- A4: The runner traps exit/interruption and cleans up the service process.
- A5: The runner writes service log and run metadata under `eval/asr_streaming/results/`.
- A6: README documents the Qwen3 app smoke command and manual checklist.
- A7: Existing Swift and eval checks continue to pass.
- A8: Real manual app smoke must cover the safety checklist before this feature becomes validated.
- A9: `scripts/setup_qwen3_mlx_runtime.sh` exists, validates local model/source paths, and can recreate the `.venv-mimo` runtime.

## Automated Checks

```bash
bash -n scripts/setup_qwen3_mlx_runtime.sh
bash -n scripts/run_qwen3_mlx_app_smoke.sh
DRY_RUN=1 bash scripts/run_qwen3_mlx_app_smoke.sh
swift build
swift test
bash eval/asr_streaming/validate.sh
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-23-qwen3-mlx-real-app-smoke/feature.json >/dev/null
```

## Manual Smoke Checks

- Launch with `bash scripts/run_qwen3_mlx_app_smoke.sh`.
- Notes focused text field: hold/release Right Option; final text appears at cursor and clipboard restores after confirmed paste.
- Browser no-input area: hold/release Right Option; final text remains on clipboard for manual paste.
- ChatGPT or browser text input: final text auto-pastes only when focus is stable.
- Password or secure field: no auto-paste; final text goes to clipboard draft.
- Recording while switching apps: final output downgrades to clipboard draft.
- Esc during active recording: no copy, no paste, session stops, panel shows cancel state.
- Option+Space long draft: starts/stops without conflict with Right Option.
- Partial text appears only in the floating panel, never inside the active input field.
- Service failure or timeout: app must not lose recognized text already available through partials, and must not force paste.

## Optional / Not Applicable Checks

- Packaging and LaunchAgent supervision are not applicable in this feature.
- Switching Qwen3 to the default backend is not applicable in this feature.

## Evidence Required In `specs/progress.md`

- Automated commands run and results.
- Dry-run output summary.
- Runtime setup result or reason it was not run.
- If manual smoke is not run, record feature as `implemented`, not `validated`.
- If manual smoke is run, record target apps, outcomes, failures, and whether the service was cleaned up.
