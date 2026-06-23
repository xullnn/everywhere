# Requirements - ASR Backend Selection Roadmap

## Problem

LocalVoiceInput needs a clear, reproducible, local-only model evaluation roadmap before replacing or augmenting the current ASR backend. Existing evidence is spread across file-level quality runs, FunASR WebSocket realtime runs, Qwen3-ASR MLX runtime probes, cumulative recompute prototypes, and the backend-neutral incremental UX gate. Without a single roadmap, the project can incorrectly compare incompatible evidence or wire a backend into the macOS app before it is safe.

## Product Definition

For this project, "realtime ASR" means user-perceived incremental dictation UX:

- Text should accumulate in the floating panel while the user is speaking.
- A short delay is acceptable.
- Pause-based segmentation, rolling windows, cumulative recompute, and stop-time final correction are acceptable.
- Strict word-by-word native streaming is not required.
- Partial text remains floating-panel-only; only final text may be pasted or copied.

## Target Outcome

The roadmap must select or explicitly reject candidates for four roles:

- `partial_backend`: drives floating-panel incremental partial text during speech.
- `final_backend`: produces final text after user stop; may be mode-specific for short push-to-talk and long draft.
- `fallback_backend`: known-good local backend used when the selected backend is unavailable, unsafe, or fails health checks.
- `reference_only_models`: models kept for offline quality comparison but not used in the app.

## Corrected Executable Goal

Complete the full local ASR backend evaluation program for LocalVoiceInput and produce a reproducible, evidence-backed backend selection decision. This roadmap is complete only when every standalone ASR candidate in `eval/asr_streaming/model_registry.json` has either completed all tests applicable to its role or has an explicit skipped-test rationale, and every candidate has exactly one final role: `partial_backend`, `final_backend`, `fallback_backend`, `reference_only`, or `rejected`.

The goal is executable only after the prerequisite is met:

- `incremental_ux_gate.py` is currently fake-adapter-only for canonical perceived-realtime gating. Real backend transport adapters must be added before any real model is compared as a canonical partial-backend candidate.
- `qwen3_mlx_cumulative_service.py` is in-process prototype evidence only. Its semantics must converge into the canonical gate, and it does not satisfy real process-boundary validation by itself.
- Complete-audio `generate(...)`, token streaming over a fully materialized audio buffer, or a model card that says "streaming" is not proof of LocalVoiceInput realtime readiness.

The final evaluation package must include:

- All standalone ASR candidates listed in the registry:
  - `paraformer-current-funasr-ws`
  - `fun-asr-nano-2512`
  - `fun-asr-nano-2512-mlx-4bit`
  - `qwen3-asr-0.6b`
  - `qwen3-asr-1.7b`
  - `qwen3-asr-0.6b-mlx-8bit`
  - `qwen3-asr-1.7b-mlx-8bit`
  - `nemotron-3.5-asr-streaming-0.6b-mlx-8bit`
  - `mimo-v2.5-asr`
  - `firered-asr2s`
  - `glm-asr-nano-2512`
- Support artifact recorded only as a dependency, not a standalone ASR candidate:
  - `mimo-audio-tokenizer-mlx`
- Role-based required test types:
  - all runnable standalone candidates: file-level final quality evaluation with CER/WER, final latency, final coverage, compute RTF, model metadata, and result paths;
  - backend-role candidates: perceived-realtime incremental UX gate, real local service/process-boundary test, session safety checks, runtime metrics, short push-to-talk mode, and long-draft mode;
  - offline-first final candidates such as MiMo: final-only test plus optional coarse incremental 3s/5s or pause-window probe, with native partial tests skipped unless a real API is proven;
  - reference-only models: file-level evaluation only by default; realtime/session/process-boundary tests skipped with explicit rationale unless later evidence upgrades the role.
- Required safety tests for backend-role candidates:
  - cancel;
  - stale-session or token-mismatch rejection;
  - late-partial rejection after final;
  - final only after user stop;
  - post-final event isolation;
  - timeout/failure fallback path.
- Required data:
  - per-case `events.jsonl`, `chunks.jsonl` where PCM chunk input is used, and `summary.json`;
  - aggregate `summary.json` for every model/test/mode run;
  - model id, vendor, parameter scale, release date, local model path, adapter type, runtime, and pinned revision or snapshot identifier when available;
  - CER, WER, final coverage ratio, first partial latency, partial cadence, partial rewrite rate, final latency, compute RTF, realtime drift, steady RSS, cold start, warm start, and hard-gate pass/fail;
  - explicit skipped-test records with reason for every test that is not applicable to a model.

The final decision must not rely on public benchmark claims alone, file-level quality alone, token streaming over full audio alone, or any single model's isolated smoke test.

## Scope

### IN

- Define the staged evaluation path for ASR backend selection.
- Define the canonical evidence categories: file-level quality, incremental UX readiness, runtime feasibility, memory/latency, and app-control safety.
- Define hard gates, soft review signals, mode-specific thresholds, and model role assignment rules.
- Define candidate priority and demotion/淘汰 rules.
- Define when a backend is allowed to enter Swift app integration.
- Define required evidence in `specs/progress.md`.

### OUT

- No Swift App runtime integration in this roadmap contract.
- No implementation of a real Qwen3 service boundary in this feature.
- No implementation of MiMo final/coarse incremental probes in this feature.
- No cloud ASR, uploaded audio/text, or remote inference.
- No InputMethodKit migration.
- No default LLM correction.
- No weakening of existing focus, paste, clipboard, hotkey, session, or cancellation safety rules.

## Requirements

- R1: The roadmap must keep file-level ASR quality separate from incremental UX readiness.
- R2: `incremental_ux_gate.py` is the intended canonical gate for perceived realtime candidates, but the roadmap must explicitly state that it is currently fake-adapter-only and must gain real backend transport adapters before real model comparison.
- R3: `qwen3_mlx_cumulative_service.py` is prototype evidence, not a second canonical gate. Its useful safety semantics must converge into the canonical gate.
- R4: CER/WER must become quality hard dimensions for candidate selection. `final_coverage_ratio` may only guard against truncation or severe omission because it is a length ratio, not an accuracy metric.
- R5: RTF must be measured in non-realtime compute mode. Realtime mode is for wall-clock latency, cadence, and drift, because realtime sleep makes RTF approximately equal to 1.
- R6: Latency thresholds must be mode-specific for short push-to-talk and long draft.
- R7: First partial latency must not be a universal hard fail until it is defined relative to the minimum audio window for cumulative recompute. It is a soft review signal by default.
- R8: Partial rewrite rate and partial cadence are soft UX review signals unless a later feature validates mode-specific hard thresholds.
- R9: Memory/RSS, cold start, warm start, and long-session drift must be reported for all real backends; RSS must become a hard threshold before app integration.
- R10: The roadmap must require model revision/path pinning and result directory evidence for reproducibility.
- R11: A backend may enter Swift integration only after passing real process boundary validation, not just in-process probes.
- R12: App integration may begin only after real microphone/control-flow validation is planned for Right Option, Option+Space, Esc cancel, focus change, fallback, and no-partial-in-input behavior.
- R13: The roadmap must assign an initial role tier to every standalone candidate, including `fun-asr-nano-2512`, `qwen3-asr-0.6b`, and `qwen3-asr-1.7b`; no listed candidate may remain orphaned.
- R14: The roadmap must distinguish gates with fixed thresholds from gates whose thresholds are intentionally deferred to an implementation feature.

## Candidate Roles And Priority

- First-priority partial candidate:
  1. Qwen3-ASR MLX 0.6B cumulative wrapper behind a real local service boundary.
  2. Any future local native session backend that passes the same canonical gate.
- Final/long-draft candidate priority:
  1. Qwen3-ASR MLX 1.7B if quality improves enough without unacceptable latency or memory.
  2. MiMo-V2.5-ASR MLX if final-only memory and latency pass hard thresholds.
  3. Qwen3-ASR MLX 0.6B if larger models fail runtime constraints.
- Fallback:
  - Existing local FunASR 2pass baseline unless replaced by a validated local backend with a working fallback path.
- Reference-only by default:
  - `qwen3-asr-0.6b` and `qwen3-asr-1.7b` through the official transformers path because local streaming depends on a vLLM/CUDA path that is not proven feasible on MacBook Pro M4.
  - `fun-asr-nano-2512`, `fun-asr-nano-2512-mlx-4bit`, `glm-asr-nano-2512`, `firered-asr2s`, and `nemotron-3.5-asr-streaming-0.6b-mlx-8bit` unless a later spec proves they pass the canonical gate and quality thresholds.
  - MiMo if memory/latency fail or if no acceptable final-only/coarse-incremental service path is proven.

## Constraints

- All evaluation and selected runtime paths must remain local/offline.
- All metrics in user-facing summaries must include Chinese explanations.
- The project must not present complete-audio `generate(...)` or token streaming over materialized audio as proof of microphone-style realtime behavior.
- New ASR work must stay separate from macOS hotkey/focus/clipboard/paste logic until backend session behavior is proven.

## Dependencies

- `2026-06-20-asr-backend-eval-harness`
- `2026-06-20-asr-recording-cli`
- `2026-06-22-realtime-streaming-gate`
- `2026-06-22-qwen3-mlx-cumulative-service-prototype`
- `2026-06-22-incremental-ux-asr-gate`

## Related PMB Context

- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/core/system_overview.md`
