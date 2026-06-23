# Requirements - MiMo-V2.5-ASR MLX Local Evaluation Adapter

## Problem

MiMo-V2.5-ASR is a recent Xiaomi open-weight ASR candidate with a community MLX conversion for Apple Silicon. It should be screened on the same local WAV set before any macOS runtime integration decision.

## Scope

### IN

- Sync the completed remote MiMo MLX model cache to `.external/models/MiMo-V2.5-ASR-MLX`.
- Sync the required audio tokenizer to `.external/models/MiMo-Audio-Tokenizer`.
- Install a local MLX runtime in an isolated `.venv-mimo` environment.
- Add a file-level `mimo-asr-mlx-local` adapter to `eval/asr_streaming/run_eval.py`.
- Run one smoke case, then the full 10-case local WAV set if smoke passes.
- Record supplier, parameter scale, release date, model size, and Chinese metric explanations in outputs.

### OUT

- Do not integrate MiMo into the macOS app runtime yet.
- Do not change hotkey, focus, clipboard, paste, floating-panel, or app insertion behavior.
- Do not use cloud/API transcription paths.
- Do not claim realtime partial behavior from file-level inference.

## Requirements

- R1: Keep the runtime local/offline after model, tokenizer, and Python dependencies are available.
- R2: Preserve the existing Fun-ASR-Nano, Qwen3-ASR, GLM-ASR-Nano, and FireRed evaluation paths.
- R3: Use the official/community MLX loading path rather than guessed low-level weight loading.
- R4: Treat file-level inference as backend screening only.

## Constraints

- MiMo MLX requires the companion `MiMo-Audio-Tokenizer` assets.
- The current tested package is the MLX int4 conversion, not the larger upstream full-precision release.
- File-level MLX inference does not prove realtime partial behavior or app-session latency.

## Dependencies

- `specs/2026-06-20-asr-backend-eval-harness`
- `.external/models/MiMo-V2.5-ASR-MLX`
- `.external/models/MiMo-Audio-Tokenizer`
- `.external/repos/mlx-audio`
- `.external/repos/MiMo-V2.5-ASR-MLX`

## Related PMB context

- `project_memory_bank/core/current_focus.md`
