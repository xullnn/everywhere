# Plan - ASR Runtime Feasibility Comparison

## Implementation sequence

1. Inspect local Qwen3-ASR and MiMo runtime packages, helper scripts, and model docs.
2. Identify whether each runtime offers streaming partials, chunked decoding, or only file-level final generation.
3. Extract existing full-run metrics from result directories into a comparable table.
4. Add a concise runtime feasibility artifact under `eval/asr_streaming/` if the findings should be preserved outside chat.
5. Run lightweight local import/load or command probes only when they add useful evidence and do not duplicate expensive full eval runs.
6. Update `specs/progress.md` with concrete evidence and a recommendation.

## Touched areas

- `eval/asr_streaming/runtime_feasibility.md`
- `specs/2026-06-22-asr-runtime-feasibility-comparison/`
- `specs/feature_matrix.json`
- `specs/progress.md`

## Validation implementation notes

- Validate any new Markdown/JSON-adjacent artifacts by checking referenced result paths and summary JSON files.
- If scripts are added, run `py_compile` and existing `bash eval/asr_streaming/validate.sh`.

## Risks and mitigations

- Risk: File-level metrics may bias the recommendation toward a model without usable realtime partials.
  Mitigation: Keep a separate runtime-feasibility score and avoid selecting an app backend only from CER/WER.
- Risk: Runtime docs may be incomplete or stale.
  Mitigation: Prefer local code inspection and executable smoke evidence over broad claims.
- Risk: Full model load probes are expensive.
  Mitigation: Reuse existing runs when possible and only run targeted probes.

## PMB promotion candidates

- Promote only after a backend integration direction is selected and validated.
