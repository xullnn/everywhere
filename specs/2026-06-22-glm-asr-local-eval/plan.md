# Plan - GLM-ASR-Nano Local Evaluation Adapter

## Sequence

1. Sync the completed remote model cache to `.external/models/GLM-ASR-Nano-2512`.
2. Inspect the model repository README and config files for the local inference API.
3. Create an isolated GLM runtime if the required Transformers version differs from the existing Qwen3 runtime.
4. Add a minimal `glm-asr-local` file-level adapter if the runtime loads on macOS.
5. Run a one-case smoke test.
6. Run the full 10-case local WAV set if smoke passes.
7. Record validation evidence and any runtime blockers in `specs/progress.md`.

## Risk

- GLM-ASR-Nano requires a Transformers development version with `GlmAsrForConditionalGeneration` and `GlmAsrProcessor`. The current Qwen3 venv uses Transformers `4.57.6`, which does not expose those classes.
