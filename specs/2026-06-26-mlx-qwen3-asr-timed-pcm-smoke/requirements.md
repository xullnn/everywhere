# Requirements - mlx-qwen3-asr Timed PCM Smoke

## Problem

The previous long-dictation evaluation found that the current Qwen3-ASR MLX app path uses a cumulative recompute wrapper and starts to slow down as audio grows. A community `mlx-qwen3-asr` source probe found a session-like API (`init_streaming`, `feed_audio`, `finish_streaming`) with cache and tail-refinement signals, but LocalVoiceInput still needs local evidence that this API can accept microphone-like timed PCM chunks and produce usable partial/final output.

## Scope

### IN

- Add an independent timed PCM smoke probe for local `mlx-qwen3-asr`.
- Load local 16 kHz mono int16 WAV cases from existing JSONL manifests.
- Feed audio as PCM chunks into `init_streaming/feed_audio/finish_streaming`.
- Record pre-stop partial events, post-stop final output, latency, chunk timing, partial stability, rewrite rate, finalization delta, CER, WER, and RTF.
- Distinguish model/package load failures, model-format incompatibility, API incompatibility, and gate failures.
- Keep all work local and inside `eval/asr_streaming/` plus this SDD feature folder.

### OUT

- No Swift App integration.
- No change to hotkeys, focus, paste, clipboard, AVAudioEngine, floating panel, or app runtime safety logic.
- No cloud inference or uploading audio/text.
- No default backend switch.
- No claim that `mlx-qwen3-asr` is production-ready from source/API shape alone.
- No large public corpus acquisition in this feature.

## Requirements

- R1: The probe must run in a dry-run mode without importing/loading `mlx-qwen3-asr`.
- R2: The probe must support a local source checkout path so the project can test uninstalled source under `.external/repos/mlx-qwen3-asr`.
- R3: The probe must accept a local model path or repo id, but must report local load/compatibility failures explicitly.
- R4: The probe must read the same case JSONL format used by existing ASR eval tooling.
- R5: The probe must feed 16 kHz mono int16 PCM as sequential chunks and optionally sleep to mimic realtime input.
- R6: A case can count as LocalVoiceInput realtime-eligible only when it has at least one accepted partial before simulated user stop and a final output after finish.
- R7: The generated JSON summary must include Chinese explanations for abbreviations: CER, WER, RTF, TTFP, partial cadence, final latency, partial stability, rewrite rate, and finalization delta.
- R8: Model/source/package claims must be recorded separately from local smoke evidence.
- R9: Any failure is valid evidence if the script records the failure category, message, command context, and result directory.
- R10: The probe must distinguish protocol success from selection success. Protocol success means partial/final timing works. Selection success also requires configured CER/WER quality thresholds.

## Constraints

- Use only local files after model/source checkout is present.
- Keep result artifacts under `eval/asr_streaming/results/`.
- Do not weaken existing incremental UX gate semantics.
- Do not treat `state.text` printed after complete-audio processing as sufficient; events must be timestamped relative to chunk feed and finish.

## Dependencies

- `2026-06-20-asr-backend-eval-harness`
- `2026-06-22-realtime-streaming-gate`
- `2026-06-22-incremental-ux-asr-gate`
- `2026-06-25-long-dictation-asr-evaluation`

## Related PMB Context

- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/core/system_overview.md`
