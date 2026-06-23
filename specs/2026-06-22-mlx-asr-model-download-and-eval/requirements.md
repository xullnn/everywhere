# Requirements - MLX ASR Model Download And Local Evaluation

## Problem

The project has validated several file-level ASR candidates, but the current next step is to evaluate Mac-native or realtime-oriented MLX community variants before choosing a backend for LocalVoiceInput. The local Mac network is no longer reliable for large model downloads, so downloads should use an AMD machine on the current local network as a transfer/cache host, then sync models back to the Mac for deployment and evaluation.

## Scope

### IN

- Use the AMD machine as a model download and cache transfer host.
- Download and sync the selected candidate models to the Mac.
- Keep evaluation execution and backend suitability conclusions on the Mac, because the product target is MacBook Pro M4 / 48GB.
- Add or update repeatable acquisition, smoke-test, and evaluation notes/scripts only inside the independent ASR evaluation area.
- Evaluate each runnable candidate on the same local WAV cases used by the existing harness.
- Produce a final comparison that includes quality, runtime, resource, and integration-readiness evidence.

### OUT

- Do not integrate a new ASR backend into `LocalVoiceInputMac` in this feature.
- Do not change hotkeys, focus detection, paste/copy routing, clipboard restoration, floating panel behavior, or any output-safety code.
- Do not convert the app to InputMethodKit.
- Do not use cloud transcription or upload audio/text.
- Do not default-enable LLM correction or auto-send behavior.
- Do not treat AMD inference performance as the Mac product performance result.

## Candidate models

- `mlx-community/Qwen3-ASR-0.6B-8bit`
- `mlx-community/Qwen3-ASR-1.7B-8bit`
- `mlx-community/nemotron-3.5-asr-streaming-0.6b-8bit`
- `mlx-community/MiMo-V2.5-ASR-MLX-8bit`
- `mlx-community/MiMo-Audio-Tokenizer`
- `mlx-community/Fun-ASR-Nano-2512-4bit`
- Optional follow-up if the above set exposes a gap: `mlx-community/Mega-ASR-8bit`

## Requirements

- R1: For every candidate, record model ID, upstream/vendor, vendor in Chinese, release timing, parameter scale, license if available, downloaded size, local path, and source.
- R2: Use AMD only for download/cache acquisition and transfer; Mac local smoke/full evaluation remains authoritative.
- R3: Every runnable model must pass a one-case smoke test before a full 10-case evaluation.
- R4: Full evaluation must reuse `eval/asr_streaming/cases.local.jsonl` and the existing local WAV files unless a future spec explicitly expands the case set.
- R5: Results must include Chinese explanations for CER, WER, RTF, latency, event counts, and failure status.
- R6: Runtime suitability must be judged separately from file-level accuracy and must include partial-output capability, session semantics, cold start, model reuse, memory/RSS, and integration complexity.
- R7: Failed or skipped models must have a concrete failure reason and the command or evidence that produced it.
- R8: No macOS app runtime code may be touched unless a separate backend integration feature is approved.

## Constraints

- The final product remains local-first and privacy-preserving.
- The target hardware for deployment remains MacBook Pro M4 / 48GB.
- Existing output-safety behavior remains out of scope and must not be weakened to make ASR integration easier.
- Network downloads may be slow or interrupted; acquisition should prefer resumable tools and verifiable local caches.

## Dependencies

- `specs/2026-06-20-asr-backend-eval-harness`
- `specs/2026-06-22-asr-runtime-feasibility-comparison`

## Related PMB context

- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/modules/output_safety/summary.md`
