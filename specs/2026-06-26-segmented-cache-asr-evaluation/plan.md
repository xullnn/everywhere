# Plan - Segmented Cache ASR Evaluation

## Implementation Sequence

1. Create this SDD feature contract and add it to `specs/feature_matrix.json`.
2. Add `eval/asr_streaming/segment_cache_eval.py`.
3. Implement a `prepare` command that generates segment WAV files, case JSONL, and a manifest.
4. Implement an `analyze` command that reads a `run_eval.py` aggregate summary plus the manifest and reports aggregate long-dictation behavior per source case and strategy.
5. Run script compilation, dry-run, prepare, and generated case validation.
6. Run a small local Qwen3-ASR MLX 0.6B 8bit segment pilot if the local runtime is available.
7. Record validation evidence in `specs/progress.md` and update `specs/feature_matrix.json`.

## Touched Areas

- `specs/2026-06-26-segmented-cache-asr-evaluation/*`
- `specs/feature_matrix.json`
- `specs/progress.md`
- `eval/asr_streaming/segment_cache_eval.py`
- `eval/asr_streaming/audio/segment_cache/`
- `eval/asr_streaming/cases.segment_cache.local.jsonl`
- `eval/asr_streaming/results/segment-cache-*`

## Validation Implementation Notes

- Use `python3 -m py_compile` for syntax validation.
- Use `segment_cache_eval.py prepare --dry-run` before writing generated artifacts.
- Use the existing `run_eval.py validate-cases` command for generated case JSONL.
- Use `.venv-mimo/bin/python` with `PYTHONPATH=.external/repos/mlx-audio` for a real Qwen3 MLX run when available.
- Keep the first real model pilot small enough to complete interactively; broader strategy sweeps are follow-up work.

## PMB Promotion Candidates

- After validation, durable guidance that long dictation should use hybrid segmented caching rather than whole-session cumulative final recompute.

## Risks and Mitigations

- Risk: Proportional text splitting does not match actual speech timing.
  Mitigation: Use segment-level text only as a harness requirement; judge quality primarily on aggregate source-case CER/WER and mark the approximation in metadata.
- Risk: Naive concatenation can duplicate text when overlap is enabled.
  Mitigation: Default first pilot to zero overlap and report overlap as an explicit caveat when non-zero.
- Risk: Synthetic long cases are not natural dictation quality evidence.
  Mitigation: Label case metadata and analysis warnings; use them for stress/backlog signals, not final UX judgment.
- Risk: One pilot run can be noisy.
  Mitigation: Record it as first-pass evidence and require repeated wider sweeps before product defaults.
