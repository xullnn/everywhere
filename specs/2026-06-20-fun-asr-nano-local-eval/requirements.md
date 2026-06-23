# Requirements — Fun-ASR-Nano Local Evaluation Adapter

## Problem

The current Paraformer/FunASR baseline is runnable but weak on long-form final completeness, Chinese-English mixed dictation, and technical/product names. LocalVoiceInput needs a reproducible local-first way to evaluate Fun-ASR-Nano-2512 against the same user-recorded WAV set before considering any macOS app runtime changes.

## Scope

### IN

- Add a candidate eval adapter for `FunAudioLLM/Fun-ASR-Nano-2512` under `eval/asr_streaming/`.
- Use existing 16 kHz mono int16 WAV case files as input.
- Record per-case summaries with the same core metrics and Chinese metric explanations as existing runs.
- Embed model metadata from `model_registry.json` using `--model-id fun-asr-nano-2512`.
- Support a one-case smoke run before attempting the full 10-case local benchmark.
- Keep all audio and text local; no cloud ASR API calls.

### OUT

- Do not modify macOS app hotkeys, focus detection, clipboard, paste, floating panel, or production ASR runtime.
- Do not make Fun-ASR-Nano the default app backend.
- Do not require CUDA or cloud services.
- Do not claim local validation until at least one real WAV run completes.
- Do not implement vLLM streaming service in this pass unless the direct local adapter proves insufficient and the user expands scope.

## Requirements

- R1: The adapter must load and run through the existing eval harness command surface.
- R2: The adapter must fail clearly if optional Fun-ASR-Nano dependencies or model runtime requirements are missing.
- R3: The adapter must write `events.jsonl`, per-case `summary.json`, and aggregate `summary.json`.
- R4: The summary must include model metadata, Chinese metric explanations, final text, CER, WER, RTF, latency fields where applicable, and status.
- R5: For file-level Fun-ASR-Nano inference, missing realtime partial events must be explicit rather than disguised as streaming behavior.
- R6: The first validation step must use a short single-case smoke run before any full benchmark.

## Constraints

- Keep implementation in Python eval tooling; do not import from Swift targets.
- Use the existing `.venv` where practical.
- Model download is acceptable for this explicitly requested candidate test, but the result must remain local after download.
- Prefer CPU/MPS-compatible execution on MacBook Pro M4; CUDA-only paths are not sufficient for this feature.

## Dependencies

- Existing feature: `2026-06-20-asr-backend-eval-harness`
- Existing local cases: `eval/asr_streaming/cases.local.jsonl`
- Optional runtime dependency: FunASR `AutoModel` with `trust_remote_code=True` for `FunAudioLLM/Fun-ASR-Nano-2512`

## Related PMB context

- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/core/current_focus.md`
