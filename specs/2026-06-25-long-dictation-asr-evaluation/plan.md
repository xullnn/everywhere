# Plan - Long-Dictation ASR Evaluation And Streaming-Route Validation

## Implementation Sequence

1. Create this SDD feature contract and add it to `specs/feature_matrix.json`.
2. Inspect existing ASR eval harness files and reuse current case/result conventions.
3. Add a long corpus manifest under `eval/asr_streaming/`.
4. Add a local media preparation script that can:
   - read a manifest;
   - validate local source paths;
   - call `ffmpeg` to produce 16 kHz mono int16 WAV;
   - write runnable JSONL cases only for prepared items.
5. Add a Qwen3 cumulative long-duration benchmark runner that:
   - starts the local Qwen3 HTTP service;
   - waits for health;
   - runs the incremental UX gate on the prepared long cases;
   - records duration class and result paths;
   - keeps service cleanup behavior.
6. Add an initial `mlx-qwen3-asr` streaming surface probe that:
   - imports the package if available;
   - records package version/source;
   - introspects candidate streaming/session methods;
   - optionally runs a local smoke when model and audio are available;
   - emits JSON evidence without treating claims as pass results.
7. Run syntax and dry-run checks.
8. Record evidence in `specs/progress.md`.

## Touched Areas

- `specs/2026-06-25-long-dictation-asr-evaluation/*`
- `specs/feature_matrix.json`
- `specs/progress.md`
- `eval/asr_streaming/long_corpus_manifest.json`
- `eval/asr_streaming/prepare_long_corpus.py`
- `eval/asr_streaming/probe_mlx_qwen3_asr_streaming.py`
- `scripts/run_qwen3_mlx_http_long_benchmark.sh`
- `eval/asr_streaming/README.md`

## Validation Implementation Notes

- Keep the first implementation pass dry-run friendly so it does not require immediate large downloads.
- Use manifest placeholders for public datasets and talks until the local source audio is acquired.
- If `ffmpeg` is unavailable, preparation must fail with a clear local prerequisite message.
- Do not automatically download random public videos in this feature. Download/acquisition should remain explicit and license-recorded.
- Do not promote `mlx-qwen3-asr` to a backend candidate from README claims alone; local probe evidence is required.

## PMB Promotion Candidates

- Only after validation: durable conclusions about long-dictation corpus policy, Qwen3 long-duration limits, and whether `mlx-qwen3-asr` exposes a locally useful streaming surface.

## Risks And Mitigations

- Risk: Public interview/talk audio lacks a reliable transcript.
  Mitigation: Mark it as experience-smoke only and do not compute CER/WER.
- Risk: The test corpus becomes a copyright/licensing mess.
  Mitigation: Require source/license metadata before cases become runnable.
- Risk: Long benchmarks take a long time.
  Mitigation: Support duration-class subsets and dry-runs.
- Risk: Qwen3 cumulative route fails long benchmarks.
  Mitigation: Treat failures as selection evidence and proceed to streaming-surface and segmented-prefix prototypes.
