# Validation - Long-Dictation ASR Evaluation And Streaming-Route Validation

## Completion Rule

This feature can be marked `passes=true` only when the corpus manifest tooling, Qwen3 long benchmark runner, and `mlx-qwen3-asr` streaming probe entry are implemented, dry-run/syntax checks pass, and at least one local long-duration evaluation or explicit blocker is recorded in `specs/progress.md`.

## Acceptance Criteria

- A1: A corpus manifest exists and separates metric-bearing cases from experience-smoke cases.
- A2: Local preparation tooling can validate a manifest and produce runnable JSONL cases from local source files.
- A3: Prepared WAV files are required to be 16 kHz mono int16.
- A4: The long benchmark runner can be dry-run without starting the model.
- A5: The long benchmark runner can run against existing prepared long cases without changing macOS app logic.
- A6: The `mlx-qwen3-asr` probe records local evidence separately from package claims.
- A7: All user-facing metric names in generated summaries or documentation include Chinese explanations.
- A8: `specs/progress.md` records commands, results, skipped checks, and blockers.

## Automated Checks

```bash
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-25-long-dictation-asr-evaluation/feature.json >/dev/null
python3 -m json.tool eval/asr_streaming/long_corpus_manifest.json >/dev/null
python3 eval/asr_streaming/prepare_long_corpus.py --manifest eval/asr_streaming/long_corpus_manifest.json --dry-run
DRY_RUN=1 bash scripts/run_qwen3_mlx_http_long_benchmark.sh
python3 eval/asr_streaming/probe_mlx_qwen3_asr_streaming.py --dry-run --out-dir eval/asr_streaming/results/probe-mock
bash -n scripts/run_qwen3_mlx_http_long_benchmark.sh
```

## Optional / Not Applicable Checks

- `swift build` and `swift test` are not required unless this feature touches Swift code.
- Actual large public dataset/video download is not required for the first implementation pass.
- Real `mlx-qwen3-asr` timed PCM model execution is optional in this feature; source/API surface probing is required when the source is available. A full timed PCM smoke should be handled as a follow-up feature because it needs its own adapter and acceptance criteria.

## Evidence Required In `specs/progress.md`

- Commands run.
- Result status.
- Manifest and generated case paths.
- Any actual long benchmark result directories.
- `mlx-qwen3-asr` probe output path or explicit missing-package blocker.
- Skipped checks with reasons.
