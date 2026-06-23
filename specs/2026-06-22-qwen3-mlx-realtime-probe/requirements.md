# Requirements - Qwen3-ASR MLX Realtime Probe

## Problem

Qwen3-ASR MLX has strong local file-level quality and token streaming from complete audio input, but LocalVoiceInput needs microphone-style realtime behavior. The project needs a reproducible probe that distinguishes true session streaming from token streaming over an already available audio buffer.

## Scope

### IN

- Inspect the loaded Qwen3-ASR MLX model API surface.
- Verify whether the model exposes a session API equivalent to `feed(samples)`, `step()`, and `close()`.
- Optionally run a prefix-audio diagnostic that feeds only the first N seconds of an existing WAV into `stream_transcribe(...)`.
- Write machine-readable summaries that say whether the model is eligible for the realtime gate.

### OUT

- Do not integrate Qwen3-ASR MLX into the Swift macOS app.
- Do not claim `stream_transcribe(audio_array)` is true realtime if the model still requires an already materialized audio buffer.
- Do not add cloud or upload paths.
- Do not change hotkeys, focus routing, paste/clipboard behavior, or floating panel behavior.

## Requirements

- R1: The probe must mark Qwen3-ASR MLX as realtime-gate eligible only if it exposes a session-style streaming API.
- R2: The probe must separately report file/token streaming support.
- R3: Prefix/cumulative diagnostics must be labeled as not equivalent to the realtime gate.
- R4: The probe output must include Chinese metric/explanation fields where results are recorded.
- R5: The probe must have a self-test path that does not require loading MLX or model weights.

## Constraints

- Use local model paths under `.external/models/`.
- Use local `mlx-audio` source when available.
- Keep all generated results under `eval/asr_streaming/results/`.

## Dependencies

- `specs/2026-06-22-realtime-streaming-gate`
- `specs/2026-06-22-mlx-asr-model-download-and-eval`

## Related PMB context

- `project_memory_bank/modules/asr_audio/summary.md`
