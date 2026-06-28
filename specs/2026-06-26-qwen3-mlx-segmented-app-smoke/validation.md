# Validation - Qwen3-ASR MLX Segmented-Cache App Smoke

## Completion Rule

This feature can be marked `passes=true` only when automated checks pass and evidence is recorded in `specs/progress.md`. Manual App smoke is required before promoting this path as user-ready, but it is allowed to remain pending for this feature if the implementation is only the smoke runner and compatibility tests.

## Acceptance Criteria

- A1: The smoke script has a dry-run mode that prints service and App commands.
- A2: The smoke script checks Python runtime, model directory, and `mlx-audio` source directory before non-dry launch.
- A3: The smoke script starts `qwen3_mlx_segmented_cache_service.py serve` and waits for `/health`.
- A4: The smoke script launches `swift run LocalVoiceInputMac --local-http-asr --asr-http-url <service-url>`.
- A5: The smoke script writes service log, App log, and run metadata.
- A6: `LocalHTTPASRClient` ignores segmented service diagnostic events and only emits valid partial/final events.
- A7: `swift build` and `swift test` pass.
- A8: Default App backend remains unchanged.

## Automated Checks

```bash
DRY_RUN=1 bash scripts/run_qwen3_mlx_segmented_app_smoke.sh
python3 -m py_compile eval/asr_streaming/qwen3_mlx_segmented_cache_service.py
swift build
swift test
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-26-qwen3-mlx-segmented-app-smoke/feature.json >/dev/null
git diff --check
```

## Manual Smoke Checks

- Start the smoke script normally and wait for the App to open.
- Apple Notes text field:
  - focus a normal text area;
  - hold Right Option, say a short sentence, release;
  - expected: final text is pasted and original clipboard is restored.
- Browser input field:
  - focus Chrome/ChatGPT or Google input;
  - hold Right Option, say a short sentence, release;
  - expected: paste succeeds when the browser exposes an editable AX target; otherwise text remains on clipboard.
- No-input browser page:
  - focus a non-editable page area;
  - dictate and release;
  - expected: result is copied to clipboard and not restored away.
- Esc cancel:
  - start recording, press Esc;
  - expected: no copy, no paste, floating panel closes or cancels.
- Option+Space long draft:
  - start/stop long draft mode;
  - expected: no Right Option state conflict and final output follows the same safe routing.
- Focus change during recording:
  - start in an editable field, switch apps while recording, release;
  - expected: downgrade to clipboard draft, no forced paste.

## Optional / Not-Applicable Checks

- Automatic App-managed service launch is not applicable in this feature.
- LaunchAgent/service restart validation is not applicable in this feature.
- Segment boundary quality tuning is not applicable in this feature.

## Evidence Required In `specs/progress.md`

- commands run;
- pass/fail/skipped result;
- result directory when a real smoke is run;
- whether manual UI smoke was run or left pending;
- remaining blockers before default backend consideration.
