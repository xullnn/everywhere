# Requirements - Long-Dictation ASR Evaluation And Streaming-Route Validation

## Problem

Manual Qwen3-ASR MLX app smoke shows that short and medium dictation work, but long dictation can slow down because the current local HTTP backend uses cumulative recompute rather than native stateful streaming. LocalVoiceInput needs a reproducible, local-first way to measure that limit, prepare longer test audio without requiring the user to record many minutes manually, and validate whether a newer Qwen3 MLX streaming route can replace or augment the cumulative wrapper.

## Scope

### IN

- Define and prepare a long-dictation evaluation corpus manifest.
- Prefer public, license-trackable speech datasets with transcripts for metric-bearing tests.
- Allow public interview/talk audio only as explicitly marked experience-smoke material when license and transcript quality are suitable.
- Add repeatable tooling for preparing 16 kHz mono int16 WAV inputs from local source files.
- Add a Qwen3 cumulative-wrapper long-duration benchmark runner for 30s, 60s, 180s, and 600s classes when source audio exists.
- Add an initial probe entry for the community `mlx-qwen3-asr` package and its claimed streaming/KV-cache surface.
- Keep all runtime work local/offline once source material and model snapshots are present.
- Keep backend evaluation separate from macOS hotkey, focus, paste, clipboard, and floating-panel app logic.
- Keep metric summaries user-facing in Chinese, including abbreviations such as CER, WER, RTF, TTFP, P50, and P95.

### OUT

- No Swift App runtime integration.
- No change to current paste, clipboard, focus, hotkey, floating-panel, or AVAudioEngine behavior.
- No cloud ASR, remote inference, or uploading user audio/text.
- No default LLM correction.
- No random scraping of copyrighted interview/talk media without license and source metadata.
- No use of older-than-one-year ASR models as new primary candidates, except as baselines or architecture references.
- No final backend selection in this feature.

## Requirements

- R1: Provide a corpus manifest schema that records id, source type, license, source URL or local path, transcript path or text availability, language mix, duration target, and test purpose.
- R2: Separate metric-bearing cases from experience-smoke cases. Metric-bearing cases must have trusted transcripts. Experience-smoke cases may omit CER/WER and report latency/stability only.
- R3: Provide a local preparation command that converts local audio/video source files into 16 kHz mono int16 WAV without uploading data.
- R4: Provide a seed manifest with public dataset candidates and placeholders for long Chinese, English, and Chinese-English mixed material.
- R5: Provide a long-duration Qwen3 cumulative-wrapper runner that uses existing local HTTP service tooling and records result directories by duration class.
- R6: The long-duration runner must not silently weaken incremental UX gate semantics; failures are evidence.
- R7: Provide a streaming-surface probe command for `mlx-qwen3-asr` that can be run after the package/source is available locally.
- R8: The streaming probe must distinguish package claims from locally verified support for incremental PCM feed, state/cache reuse, tail refinement, cancel, and repeated sessions.
- R9: Preserve the current Qwen3 MLX cumulative route as an MVP/medium-dictation candidate until evidence proves a better route.
- R10: Do not test newly selected primary ASR models older than one year unless explicitly recorded as baseline/reference-only.
- R11: Record all result paths, skipped checks, and blockers in `specs/progress.md`.

## Constraints

- All tools must work from local files after initial material acquisition.
- Public dataset/video material must carry explicit source and license notes before it becomes runnable evidence.
- Evaluation files must remain under `eval/asr_streaming/` and avoid macOS app side effects.
- Use existing `incremental_ux_gate.py`, `qwen3_mlx_http_service.py`, and resource tooling where practical.

## Dependencies

- `2026-06-20-asr-backend-eval-harness`
- `2026-06-22-incremental-ux-asr-gate`
- `2026-06-23-qwen3-mlx-http-service-boundary`
- `2026-06-23-qwen3-mlx-http-resource-validation`
- `2026-06-22-asr-backend-selection-roadmap`

## Related PMB Context

- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/core/system_overview.md`
