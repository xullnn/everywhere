# Validation - MLX ASR Model Download And Local Evaluation

## Completion rule

This feature can be marked `passes=true` only when the required candidate set has been downloaded or explicitly skipped with evidence, every runnable candidate has Mac-local smoke/full evaluation evidence, and the final comparison recommends a backend direction with runtime feasibility evidence. A skipped check is acceptable only if listed as optional/not applicable below or explicitly approved by the user.

## Acceptance criteria

- A1: AMD download host, remote cache path, local cache path, and sync method are documented.
- A2: Each required candidate has metadata: supplier/vendor, Chinese supplier name, release timing, parameter scale, model size, model ID, source, and local path or concrete skip reason.
- A3: Each runnable candidate has a Mac-local smoke result on at least one WAV case.
- A4: Each smoke-passing candidate has a Mac-local full 10-case result under `eval/asr_streaming/results/`.
- A5: Result summaries include CER, WER, RTF, latency, success/failure counts, and Chinese metric explanations.
- A6: Runtime suitability is assessed independently from file-level accuracy, including partial output, session lifecycle, startup/model reuse, memory/RSS, and integration complexity.
- A7: The final comparison identifies a recommended next backend integration candidate and at least one fallback.
- A8: No Swift/macOS app runtime files are changed by this feature.

## Automated checks

```bash
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-22-mlx-asr-model-download-and-eval/feature.json >/dev/null
python3 -m json.tool eval/asr_streaming/model_registry.json >/dev/null
bash eval/asr_streaming/validate.sh
```

## Manual / operational checks

- Confirm AMD SSH command works.
- Confirm AMD model cache free space before large downloads.
- Confirm Mac local free space before syncing each model.
- Confirm each model directory has expected files before running inference.

## Optional / not-applicable checks

- Swift `swift build` and `swift test` are not required unless Swift app files are changed.
- AMD inference tests are optional and must not be used as final Mac performance evidence.
- `mlx-community/Mega-ASR-8bit` is optional unless the required candidate set does not produce a viable recommendation.

## Evidence required in `specs/progress.md`

- AMD host and cache probe command results.
- Download commands, sync commands, and local verification commands.
- Per-model smoke/full evaluation commands and result directories.
- Failure/skip reasons for any candidate that cannot run.
- Final comparison table and recommendation.
