# Requirements - FireRedASR2-AED Local Evaluation Adapter

## Problem

FireRedASR2-AED is a strong recent open-weight ASR candidate with public Chinese, dialect, English, and code-switch benchmark claims. It should be screened on the same local WAV set before any macOS runtime integration decision.

## Scope

### IN

- Sync the completed remote FireRedASR2-AED model cache to `.external/models/FireRedASR2-AED`.
- Inspect the official runtime requirements and determine whether local macOS inference is practical.
- If the runtime loads locally, add a file-level `firered-asr2-aed-local` adapter to `eval/asr_streaming/run_eval.py`.
- Run one smoke case, then the full 10-case local WAV set if smoke passes.
- Record supplier, parameter scale, release date, model size, and Chinese metric explanations in outputs.

### OUT

- Do not integrate FireRedASR2-AED into the macOS app runtime yet.
- Do not change hotkey, focus, clipboard, paste, floating-panel, or app insertion behavior.
- Do not use cloud/API transcription paths.
- Do not claim realtime partial behavior from file-level inference.

## Requirements

- R1: Keep the runtime local/offline after model and code dependencies are available.
- R2: Preserve the existing Fun-ASR-Nano, Qwen3-ASR, and GLM-ASR-Nano evaluation paths.
- R3: If the official runtime cannot load on this macOS environment, record the concrete blocker instead of forcing a fragile workaround.
- R4: Treat file-level inference as backend screening only.

## Constraints

- Current model card indicates inference depends on the official `FireRedASR2S` Python codebase, not a generic Transformers AutoModel path.
- Current target machine is macOS on Apple Silicon; upstream runtime may assume Linux/CUDA or project-specific dependencies.

## Dependencies

- `specs/2026-06-20-asr-backend-eval-harness`
- `.external/models/FireRedASR2-AED`
- Official FireRedASR2S Python inference code if needed for local runtime.

## Related PMB context

- `project_memory_bank/core/current_focus.md`
