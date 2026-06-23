# Requirements - Qwen3-ASR Local Evaluation Adapter

## Problem

Fun-ASR-Nano improved speed and average CER over the current Paraformer baseline, but still misses key product and technical terms. LocalVoiceInput needs a repeatable local-first Qwen3-ASR evaluation on the same user-recorded WAV cases before deciding whether any backend deserves realtime app integration.

## Scope

### IN

- Add a local file-level eval adapter for `Qwen/Qwen3-ASR-0.6B`.
- Use the existing 16 kHz mono int16 WAV cases in `eval/asr_streaming/cases.local.jsonl`.
- Record the same metrics and Chinese metric explanations used by the existing harness.
- Add a one-command smoke path and dependency/download preparation path.
- Update `model_registry.json` so Qwen3-ASR 0.6B is runnable and self-describing.
- Keep all audio and text local; do not call DashScope or any cloud ASR API.

### OUT

- Do not change macOS app hotkeys, focus detection, clipboard, paste, floating panel, audio capture, or production ASR runtime.
- Do not make Qwen3-ASR the default app backend.
- Do not implement vLLM streaming or an OpenAI-compatible server in this pass.
- Do not evaluate Qwen3-ASR 1.7B in this pass unless the user explicitly expands scope.
- Do not claim realtime partial behavior from a file-level adapter.

## Requirements

- R1: `run_eval.py` must expose a Qwen3-ASR local adapter through the existing `run` command.
- R2: The adapter must use the official `qwen-asr` package transformers backend when available.
- R3: The adapter must fail clearly when `qwen-asr`, model files, or compatible runtime requirements are missing.
- R4: The adapter must write `events.jsonl`, per-case `summary.json`, and aggregate `summary.json`.
- R5: The summary must include model metadata, Chinese metric explanations, final text, CER, WER, RTF, latency fields where applicable, and status.
- R6: File-level inference must mark realtime partial metrics as unavailable rather than inventing partials.
- R7: The first runtime validation must be a one-case smoke run before any full 10-case benchmark.

## Constraints

- Use local files and local Python execution only.
- Prefer CPU/MPS-compatible execution on the MacBook Pro M4.
- Keep dependencies isolated to eval tooling and scripts.
- Official Qwen3-ASR streaming is vLLM-based; treat streaming as a follow-up until file-level quality and local runtime cost are known.

## Dependencies

- Existing feature: `2026-06-20-asr-backend-eval-harness`
- Existing local cases: `eval/asr_streaming/cases.local.jsonl`
- Runtime package: `qwen-asr`
- Candidate model: `Qwen/Qwen3-ASR-0.6B`

## Related PMB context

- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/insights/funasr_local_runtime.md`
