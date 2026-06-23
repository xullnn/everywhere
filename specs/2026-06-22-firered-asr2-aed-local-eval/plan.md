# Plan - FireRedASR2-AED Local Evaluation Adapter

## Implementation sequence

1. Finish syncing `FireRedTeam/FireRedASR2-AED` from the 2015 MacBook Pro cache.
2. Inspect local model files, README, config, and official runtime entry points.
3. Obtain or reference the official `FireRedASR2S` inference code locally if the model files alone are insufficient.
4. Create an isolated Python runtime if dependencies conflict with the Qwen or GLM eval environments.
5. Add a minimal `firered-asr2-aed-local` file-level adapter if the runtime loads on macOS.
6. Run a one-case smoke test.
7. Run the full 10-case local WAV set if smoke passes.
8. Record validation evidence and any runtime blockers in `specs/progress.md`.

## Touched areas

- `eval/asr_streaming/run_eval.py`
- `eval/asr_streaming/model_registry.json`
- `specs/feature_matrix.json`
- `specs/progress.md`
- `specs/2026-06-22-firered-asr2-aed-local-eval/`

## Validation implementation notes

- Reuse existing case loading, normalization, metric, and summary-writing paths.
- If an adapter is added, keep it file-level and explicitly mark that it does not provide realtime partials.

## Risks and mitigations

- Risk: Official runtime code is required and not packaged inside the model repository.
  Mitigation: Use the official repository if available; otherwise record the missing-code blocker.
- Risk: Runtime dependencies conflict with existing Qwen or GLM environments.
  Mitigation: Use a separate virtual environment for FireRed.
- Risk: Upstream runtime assumes CUDA/Linux-specific behavior.
  Mitigation: Stop at a concrete blocker if macOS CPU/MPS execution is not practical.

## PMB promotion candidates

- None until the FireRed eval path is validated and durable.
