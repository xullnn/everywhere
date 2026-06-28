# Plan - Qwen3-ASR MLX Real App Smoke

## Implementation Sequence

1. Add `scripts/run_qwen3_mlx_app_smoke.sh`.
2. Reuse the existing Qwen3 HTTP service startup pattern from the gate scripts.
3. Add dry-run mode that prints the service and app command without launching the model or app.
4. Add result metadata paths for service log and app-smoke run metadata.
5. Add `scripts/setup_qwen3_mlx_runtime.sh` so the MLX Python service runtime can be recreated.
6. Document the runtime setup command and manual smoke checklist in this feature and README.
7. Run syntax, dry-run, Swift build/test, and eval harness checks.
8. Leave the feature as `implemented` until real manual smoke evidence is recorded.

## Touched Areas

- `scripts/run_qwen3_mlx_app_smoke.sh`
- `scripts/setup_qwen3_mlx_runtime.sh`
- `scripts/run_qwen3_mlx_http_gate_smoke.sh`
- `scripts/run_qwen3_mlx_http_extended_gate.sh`
- `README.md`
- `specs/2026-06-23-qwen3-mlx-real-app-smoke/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

## Validation Implementation Notes

- Automated checks should not launch the UI or load Qwen3 by default.
- Manual smoke must be performed in real apps and recorded separately.
- If the real service cannot load because of missing `.venv-mimo`, MLX, or model files, run `bash scripts/setup_qwen3_mlx_runtime.sh` first; if setup still fails, record it as blocked rather than weakening the checklist.

## PMB Promotion Candidates

- Promote only after real manual smoke validates the app-level behavior.

## Risks And Mitigations

- Risk: The smoke runner leaves a heavy Python model service running.
  Mitigation: Trap exit and interrupt signals and kill the service PID.
- Risk: The smoke runner is mistaken for production supervision.
  Mitigation: Document that it is foreground manual smoke only.
- Risk: A successful backend service gate is mistaken for app smoke.
  Mitigation: Require manual checks in Notes/browser/secure fields/focus-change flows.
