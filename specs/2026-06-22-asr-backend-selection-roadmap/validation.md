# Validation - ASR Backend Selection Roadmap

## Completion Rule

This roadmap can be marked `passes=true` only after backend role selection is complete and validated with recorded evidence. Creating this contract alone does not complete the feature.

The roadmap may enter implementation only after the corrected executable goal has no orphaned candidate models, separates role-applicable tests from skipped tests, and distinguishes fixed hard gates from thresholds that must be set in later implementation features.

## Roadmap Acceptance Criteria

- A1: A single canonical gate is used for perceived-realtime backend readiness.
- A2: Real backend transport adapters exist before any real model is compared as a partial backend candidate.
- A3: File-level quality evidence and incremental UX evidence are reported separately.
- A4: CER/WER are hard quality dimensions for backend selection.
- A5: `final_coverage_ratio` is treated only as an omission/truncation signal.
- A6: Compute RTF is measured in non-realtime mode; realtime mode measures latency, cadence, and drift.
- A7: Thresholds are mode-specific for short push-to-talk and long draft.
- A8: First partial latency, cadence, and rewrite rate are soft UX signals unless a later feature calibrates hard thresholds from real data.
- A9: RSS, cold start, warm start, and long-session drift are reported before app integration; RSS must have a hard threshold in the implementation feature.
- A10: Backend role recommendations include partial, final, fallback, and reference-only categories.
- A11: Swift app integration is blocked until real service boundary and real microphone/control-flow validation pass.
- A12: Every standalone registry candidate has an initial role tier and a final role assignment path; support artifacts are recorded only as dependencies.
- A13: Reference-only candidates are not forced through realtime/session/process-boundary tests unless a later feature upgrades their role.

## Overall Completion Goal

This roadmap is complete only when all standalone candidate models have completed all role-applicable required tests or have explicit skipped-test rationale, and all required data has been collected for the tests that were run.

The final evidence set must answer these questions for every model:

- Can it produce accurate final transcription on the local recorded case set?
- Can it produce usable perceived-realtime partials before user stop, or is it final-only/reference-only?
- Can it run behind a real local process/service boundary if it is a backend candidate?
- Does it satisfy session safety: cancel, stale event rejection, no late partial after final, and final only after stop?
- Does it satisfy short push-to-talk and long-draft latency expectations?
- Does it fit the M4 / 48GB memory budget with acceptable cold/warm start behavior?
- Does it handle Chinese, Chinese-English mixed dictation, technical terms, punctuation, numbers, safety text, and long text?
- Should it be assigned to partial backend, final backend, fallback backend, reference-only, or rejected?

The final output must include one comparison table and one role-decision record that lists every candidate model, every required metric, every skipped test with reason, and all result directory paths.

## Hard Gates For Real Backend Role Selection

These fixed gates must pass before a backend can enter Swift integration:

- H1: Accepted partial appears before stop for partial-role candidates.
- H2: Accepted final appears only after stop.
- H3: No accepted partial appears after accepted final.
- H4: Cancel produces no accepted partial/final output.
- H5: Old session or token-mismatched events are ignored.
- H6: Final output is not truncated or severely incomplete; `final_coverage_ratio >= 0.70` is a minimum truncation guard, not a quality substitute.
- H7: Compute RTF in non-realtime mode is `<= 1.0` for partial-role candidates unless explicitly waived with evidence.
- H8: Short push-to-talk final latency is `<= 2.5s` in realtime mode.
- H9: Long draft final latency is `<= 8s` in realtime mode.
- H10: Long-session latency does not show monotonic drift that would prevent 120s draft usage.
- H11: Runtime failure or timeout has a documented local fallback path.
- H12: A backend passes real process-boundary validation; in-process prototype results alone do not count.

These gates must be defined by the relevant implementation feature before the backend can be selected for app integration:

- H13: CER/WER pass thresholds for short push-to-talk, long draft, Chinese-English mixed, and technical-term cases.
- H14: Steady RSS is below the hard limit set for a background local ASR service on the MacBook Pro M4 / 48GB target.

## Soft Review Signals

These must be reported, but they do not automatically fail a candidate until calibrated:

- S1: First partial latency.
- S2: Partial cadence.
- S3: Partial rewrite rate.
- S4: Cold start time.
- S5: Hot/warm start time.
- S6: Coarse incremental behavior for final-oriented models such as MiMo.

## Required Evidence Per Phase

Each implementation phase must record in `specs/progress.md`:

- Commands run.
- Result directory paths.
- Model id, model path, and revision/pin when available.
- Case file used.
- Aggregate metrics and per-case summary paths.
- Hard gate pass/fail.
- Soft review signals.
- Skipped checks with explicit reason.
  - Example: official non-MLX Qwen3 realtime-session tests skipped because the streaming path depends on vLLM/CUDA and is not locally proven on M4.
  - Example: MiMo native partial tests skipped unless a chunked/session API is proven.

## Required Final Evidence Package

Before this roadmap can be marked `validated`, `specs/progress.md` must point to a final comparison artifact containing:

- Candidate model inventory and tested model revisions.
- Test matrix showing which model ran which test type.
- Per-run result directories.
- Aggregate metrics for each model and mode.
- Hard-gate pass/fail table.
- Soft-signal review notes.
- Role assignment for every model.
- Remaining risks and manual verification still required before Swift app integration.

## Contract Validation Checks

```bash
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-22-asr-backend-selection-roadmap/feature.json >/dev/null
test -f specs/2026-06-22-asr-backend-selection-roadmap/requirements.md
test -f specs/2026-06-22-asr-backend-selection-roadmap/plan.md
test -f specs/2026-06-22-asr-backend-selection-roadmap/validation.md
test -f specs/2026-06-22-asr-backend-selection-roadmap/decisions.md
```

## Optional / Not Applicable Checks

- `swift build` and `swift test` are not required for this contract-only feature.
- Model runtime probes are not required until their implementation feature starts.
