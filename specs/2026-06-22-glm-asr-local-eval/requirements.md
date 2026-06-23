# Requirements - GLM-ASR-Nano Local Evaluation Adapter

## Goal

Evaluate `zai-org/GLM-ASR-Nano-2512` on the existing local WAV cases without touching the macOS app runtime.

## Requirements

- Add or document a local file-level GLM-ASR-Nano evaluation path.
- Keep the runtime local/offline after model files are available.
- Preserve the existing Qwen3-ASR and Fun-ASR-Nano evaluation paths.
- Record supplier, parameter scale, release date, model size, and Chinese metric explanations in outputs.
- Treat file-level inference as backend screening only; do not claim realtime partial behavior or app insertion validation.

## Non-goals

- Do not integrate GLM-ASR-Nano into the macOS app runtime yet.
- Do not change hotkey, focus, clipboard, paste, or floating-panel behavior.
- Do not use cloud/API transcription paths.
