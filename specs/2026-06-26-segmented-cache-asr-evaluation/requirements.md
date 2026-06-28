# Requirements - Segmented Cache ASR Evaluation

## Problem

The current Qwen3-ASR MLX path can provide user-perceived realtime output through a cumulative recompute wrapper, but recomputing the whole recording becomes increasingly unsuitable as dictation length grows. A fixed two-minute final recompute was only an example and has already shown quality risk in synthetic segment-budget evidence. The project needs a local, repeatable evaluation path for segmented caching before changing the macOS App runtime.

## Scope

### IN

- Add an independent segmented-cache evaluation tool under `eval/asr_streaming/`.
- Use repository-local 16 kHz mono int16 WAV cases and existing ASR case JSONL format.
- Generate segment WAV files for strategy matrices that combine:
  - hard audio-duration upper bounds;
  - soft text-length budgets estimated from the source transcript for evaluation only;
  - optional overlap metadata for future boundary experiments.
- Reuse the current local Qwen3-ASR MLX 0.6B 8bit `mlx-stt-local` file-level adapter for segment final recognition.
- Analyze each original case plus strategy as an aggregate long-dictation run:
  - segment count;
  - per-segment and total model wall time;
  - approximate serial-worker backlog;
  - user-stop final wait;
  - aggregate final text CER/WER/coverage;
  - warnings for missed tail, bad quality, or excessive backlog.
- Write machine-readable and human-readable output with Chinese metric explanations.

### OUT

- No changes to `Sources/LocalVoiceInputMac` or `Sources/LocalVoiceInputCore`.
- No change to hotkeys, focus routing, paste, clipboard, floating panel, audio capture, or App runtime safety logic.
- No cloud ASR or audio/text upload.
- No default App backend switch.
- No claim that proportional transcript splitting is a production algorithm; it is only an evaluation approximation.
- No product threshold hard-coding before local evidence is reviewed.

## Requirements

- R1: The generated segmented cases must be reproducible from repository-local WAV files.
- R2: Generated segment cases must validate through the existing `run_eval.py validate-cases` command.
- R3: The tool must preserve a manifest linking every segment back to its source case, strategy, segment index, logical audio range, physical audio range, and text-budget assumptions.
- R4: The analysis must aggregate segment outputs back to the original source case and report full-case CER, WER, coverage, wall time, backlog, and final-wait estimates.
- R5: The analysis must explain all abbreviations and key metrics in Chinese.
- R6: The tool must clearly label soft text budget decisions as evaluation-only estimates based on source transcript length, not as a production runtime mechanism.
- R7: The first implementation must be usable without loading the ASR model by supporting dry-run/prepare/analysis workflows independently.
- R8: Real model validation should reuse the current local Qwen3-ASR MLX 0.6B 8bit cache if available.

## Constraints

- Local-only execution.
- Existing model cache paths must be reused.
- Existing macOS safety architecture remains unchanged.
- Segment-level expected text is approximate and must not be treated as authoritative per-segment CER/WER evidence.

## Dependencies

- `2026-06-20-asr-backend-eval-harness`
- `2026-06-22-qwen3-mlx-cumulative-recompute-probe`
- `2026-06-25-long-dictation-asr-evaluation`
- `2026-06-26-segment-budget-asr-evaluation`

## Related PMB context

- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/core/system_overview.md`
