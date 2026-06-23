# Requirements — ASR Backend Evaluation Harness

## Problem

LocalVoiceInput needs a repeatable way to compare current Paraformer/FunASR ASR behavior with newer local-first ASR candidates before changing the macOS app runtime. Manual dictation is too slow and inconsistent for model selection.

## Scope

### IN

- Add an independent evaluation harness under `eval/asr_streaming/`.
- Use WAV files to simulate realtime microphone streaming.
- Support the existing local FunASR WebSocket server as the first runnable backend baseline.
- Record structured outputs for partial events, offline/final events, latency, realtime factor, CER, and WER.
- Add a model evidence registry that distinguishes public benchmark evidence from local validation status.
- Provide example case schema and documentation so user-provided recordings can be added later.

### OUT

- Do not modify `LocalVoiceInputMac` hotkey, focus, clipboard, paste, floating panel, or app runtime behavior.
- Do not download large ASR model weights by default.
- Do not call cloud ASR APIs.
- Do not claim Qwen3-ASR, Fun-ASR-Nano, MiMo, FireRed, or GLM are locally validated until a runnable adapter has been executed.
- Do not replace the production ASR backend in this feature.

## Requirements

- R1: The harness must load JSONL cases containing at least `id`, `audio`, `text`, `lang`, and `scenario`.
- R2: The harness must validate case schema without requiring audio files when explicitly requested for setup checks.
- R3: The runnable baseline must stream local 16 kHz mono int16 WAV audio to a FunASR WebSocket endpoint in realtime-like chunks.
- R4: The FunASR adapter must record every received event with timestamps, mode, text, and raw server payload.
- R5: The result summary must include final text, CER, WER, first partial latency, final latency, realtime factor, event counts, and status.
- R6: The harness must keep model survey evidence separate from local run results.
- R7: The implementation must remain local-first and must not upload audio or text by default.
- R8: Evaluation outputs must include Chinese explanations for core metrics so future result reviews do not rely on unexplained abbreviations.
- R9: Every tested model must have structured model metadata covering supplier/vendor, parameter scale, and release date. If an exact release date cannot be verified from first-party sources, the metadata must say so explicitly.

## Constraints

- Python harness code should use the standard library where practical.
- WebSocket execution may depend on the existing FunASR Python environment's `websockets` package.
- Audio resampling is not included in the first pass; run inputs must already be 16 kHz mono int16 WAV or fail with a clear message.
- Streaming chunks must be configurable, with a default close to the existing FunASR client behavior.

## Dependencies

- Optional runtime dependency: `websockets`, normally installed by `scripts/setup_funasr_venv.sh` / FunASR requirements.
- Existing local FunASR server script: `scripts/run_funasr_python_server.sh`.

## Related PMB context

- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/insights/funasr_local_runtime.md`
