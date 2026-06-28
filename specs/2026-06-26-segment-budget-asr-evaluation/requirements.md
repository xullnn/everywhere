# Requirements - Segment Budget ASR Evaluation

## Problem

The long-dictation architecture needs evidence-based segment thresholds. A fixed two-minute segment was only an example. The project must determine whether Qwen3-ASR MLX final recompute cost is driven mainly by audio duration, recognized content/text length, or both, before choosing time-based, text-length-based, or hybrid segmentation.

## Scope

### IN

- Generate local, controlled 16 kHz mono int16 WAV cases from existing local recordings.
- Include cases that isolate:
  - same speech content with longer audio duration via silence padding;
  - silence-only duration cost;
  - repeated speech where both audio duration and text length grow.
- Run current Qwen3-ASR MLX 0.6B 8bit final/file-level inference through the existing `mlx-stt-local` adapter.
- Produce a machine-readable and human-readable analysis explaining whether segmentation should use time, text length, or both.

### OUT

- Do not change macOS App hotkeys, paste behavior, floating panel, or ASR client runtime.
- Do not integrate a new streaming model.
- Do not use cloud ASR or upload audio/text.
- Do not treat synthetic/repeated audio as natural long-dictation UX quality evidence.

## Requirements

- R1: The generated corpus must be reproducible from repository-local WAV cases.
- R2: The generated corpus must preserve the existing ASR harness case JSONL format.
- R3: The benchmark analysis must report duration, expected text length, output text length, wall time, RTF, CER, and WER with Chinese metric explanations.
- R4: The analysis must explicitly compare same-text/longer-duration cases against repeated-content cases.
- R5: The result must support a product recommendation for segment-boundary policy, but must not hard-code App behavior yet.

## Constraints

- Local-only execution.
- Existing model cache paths must be reused.
- Existing safety architecture remains unchanged.

## Dependencies

- `2026-06-20-asr-backend-eval-harness`
- `2026-06-22-qwen3-mlx-cumulative-recompute-probe`
- `2026-06-25-long-dictation-asr-evaluation`

## Related PMB context

- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/core/current_focus.md`
