# Requirements - ASR Runtime Feasibility Comparison

## Problem

The file-level ASR evaluation now shows strong candidates, especially MiMo-V2.5-ASR MLX and Qwen3-ASR. Before changing the macOS app runtime, the project needs a practical comparison of candidate backends as a local, low-latency, privacy-preserving dictation service.

## Scope

### IN

- Compare MiMo-V2.5-ASR MLX, Qwen3-ASR 0.6B, and Qwen3-ASR 1.7B for runtime feasibility.
- Inspect local runtime code and docs for realtime partial support, chunked inference, serving APIs, context/hotword hooks, and model reuse behavior.
- Reuse existing file-level evaluation outputs for accuracy and per-case latency.
- Add lightweight local probes or documentation where needed to make the comparison reproducible.
- Produce a ranked recommendation for the next backend integration experiment.

### OUT

- Do not integrate a new ASR backend into the macOS app runtime in this feature.
- Do not change hotkeys, focus detection, clipboard, paste engine, floating panel, or output safety behavior.
- Do not use cloud/API transcription paths.
- Do not default-enable LLM correction, auto-send, or any upload path.

## Requirements

- R1: Keep all runtime checks local/offline after model and dependency caches are present.
- R2: Separate file-level quality metrics from realtime partial/session behavior.
- R3: Treat missing realtime partial support as a runtime integration risk, even if file-level CER/WER is strong.
- R4: Preserve existing validated candidate eval outputs and registry metadata.
- R5: Include memory footprint, cold start, model reuse, and hotword/context feasibility in the recommendation.

## Constraints

- The current MVP requires realtime partial text in a non-focus-stealing floating panel.
- Final output still must go through existing safe paste/copy routing; ASR backend selection must not weaken output safety.
- MiMo MLX evidence currently comes from file-level `mlx-audio` inference.
- Qwen3-ASR evidence currently comes from file-level `qwen-asr` transformers inference; vLLM or streaming serving remains a follow-up unless locally proven.

## Dependencies

- `specs/2026-06-20-asr-backend-eval-harness`
- `specs/2026-06-21-qwen3-asr-local-eval`
- `specs/2026-06-22-mimo-v25-asr-mlx-local-eval`

## Related PMB context

- `project_memory_bank/core/current_focus.md`
