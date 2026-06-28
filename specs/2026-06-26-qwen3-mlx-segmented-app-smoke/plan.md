# Plan - Qwen3-ASR MLX Segmented-Cache App Smoke

## Implementation Sequence

1. Create this SDD feature contract and add it to `specs/feature_matrix.json`.
2. Add a segmented-cache App smoke runner script under `scripts/`.
3. Add or update Swift HTTP client tests so segmented service diagnostic events do not leak into App transcript state.
4. Update ASR README with one-command dry-run and manual smoke commands.
5. Run automated checks:
   - script dry-run;
   - Python compile for the segmented service;
   - Swift build/test;
   - JSON validation;
   - diff whitespace check.
6. If runtime is available, optionally run the service health path without launching the App.
7. Record evidence and leave manual smoke checklist for the user.

## Touched Areas

- `scripts/run_qwen3_mlx_segmented_app_smoke.sh`
- `Tests/LocalVoiceInputMacTests/LocalHTTPASRClientTests.swift`
- `eval/asr_streaming/README.md`
- `specs/2026-06-26-qwen3-mlx-segmented-app-smoke/*`
- `specs/feature_matrix.json`
- `specs/progress.md`
- `eval/asr_streaming/results/qwen3-mlx-segmented-app-smoke-*`

## Validation Implementation Notes

- `DRY_RUN=1 bash scripts/run_qwen3_mlx_segmented_app_smoke.sh` must print the exact service and App commands without launching either.
- `RUN_APP=0` can be used later to hold the service open for manual App launch from another terminal.
- Manual App smoke must be performed on the real macOS UI because Accessibility permissions, active app focus, and paste verification cannot be fully validated headlessly.

## PMB Promotion Candidates

- After manual validation, promote the stable operational pattern: Swift App remains the interaction layer and segmented-cache ASR runs as a local service selected explicitly by config/CLI.

## Risks and Mitigations

- Risk: The smoke script could leave a Python service process running.
  Mitigation: Use a trap to kill the child service process on exit or interruption.
- Risk: Manual smoke might be confused with product default readiness.
  Mitigation: Keep default config unchanged and label the script as smoke-only.
- Risk: HTTP diagnostics could appear in App transcript state.
  Mitigation: Add a Swift unit test asserting unsupported diagnostic events are ignored.
- Risk: Real App smoke requires user permissions and active target apps.
  Mitigation: Provide a manual checklist and keep automated checks separate from manual validation.
