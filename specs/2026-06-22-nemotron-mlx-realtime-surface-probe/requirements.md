# Requirements - Nemotron MLX Realtime Surface Probe

## Problem

`mlx-community/nemotron-3.5-asr-streaming-0.6b-8bit` is labeled as a streaming ASR model, but LocalVoiceInput needs a local runtime that accepts incremental microphone PCM and exposes session-style partial/final behavior. The project needs to verify whether the local MLX runtime exposes a true `feed/step/close` style API or only file/token streaming over a provided audio buffer.

## Scope

### IN

- Load the local Nemotron MLX snapshot through the available local `mlx-audio` source.
- Add the smallest reproducibility shim needed when the local source has a model implementation but the generic STT loader lacks a remapping entry.
- Record the loaded model API surface and realtime-gate eligibility.

### OUT

- Do not integrate Nemotron into the Swift macOS app.
- Do not patch vendored `mlx-audio` source files.
- Do not claim model-name streaming equals microphone-session streaming.
- Do not introduce cloud ASR paths.

## Requirements

- R1: The probe must confirm whether `create_streaming_session` or an equivalent session API exists.
- R2: The probe output must distinguish `stream_generate(audio)` from incremental PCM feed semantics.
- R3: The loader shim must be limited to known local model-type remappings.
- R4: The result must be recorded in the model registry and runtime feasibility notes.

## Constraints

- Use local model snapshots under `.external/models/`.
- Use local `mlx-audio-main-src` only as a source path; do not edit it.
- Keep generated output under `eval/asr_streaming/results/`.

## Dependencies

- `specs/2026-06-22-realtime-streaming-gate`
- `specs/2026-06-22-qwen3-mlx-realtime-probe`
- `specs/2026-06-22-mlx-asr-model-download-and-eval`

## Related PMB context

- `project_memory_bank/modules/asr_audio/summary.md`
