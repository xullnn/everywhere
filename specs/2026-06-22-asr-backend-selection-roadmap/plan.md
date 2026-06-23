# Plan - ASR Backend Selection Roadmap

## Phase 0 - Roadmap Contract And Evidence Rules

1. Create this roadmap feature contract.
2. Record the corrected measurement model:
   - `incremental_ux_gate.py` is the target canonical gate.
   - The current canonical gate has only fake CLI adapters, so real backend adapters are a required follow-up.
   - `qwen3_mlx_cumulative_service.py` remains prototype evidence until its semantics are driven through the canonical gate.
3. Define hard gates, soft signals, candidate roles, and phase order.
4. Record model version/revision pinning as required before final selection.
5. Record an initial role tier for every standalone registry candidate so the execution plan has no orphaned models.
6. Define role-based test applicability so the goal does not require realtime/process-boundary work for reference-only models unless later evidence upgrades them.

## Phase 1 - Canonical Gate Real Backend Support

1. Extend `incremental_ux_gate.py` with real backend transport adapters.
2. Support localhost service clients for future Qwen3/FunASR/MiMo-style services.
3. Keep fake adapters and fake self-tests as protocol regression tests.
4. Add or preserve explicit events for start, chunk, partial, finish, final, cancel, timeout, and ignored stale events.
5. Add mode metadata for short push-to-talk and long draft.
6. Add CER/WER hard quality dimensions to gate evaluation, with thresholds supplied by the implementation feature.
7. Keep `final_coverage_ratio` only as an omission/truncation signal.
8. Separate compute RTF measurement (`--no-realtime`) from realtime latency/cadence/drift measurement.
9. Preserve fake adapter self-tests for final-only rejection, late partial rejection, cancel, and stale-session behavior.

## Phase 2 - Qwen3-ASR MLX 0.6B Real Service Boundary

1. Build a persistent local Python service around Qwen3-ASR MLX 0.6B.
2. Load the model once at process start.
3. Receive 16 kHz mono PCM chunks over localhost WebSocket or HTTP.
4. Emit session events: start, partial, finish, final, cancel, ignored stale events.
5. Move model computation off the PCM ingestion path.
6. Run the service through the canonical gate with real process and transport boundaries.
7. Measure cold start, warm start, steady RSS, compute RTF, realtime latency, cadence, partial rewrite, long-session drift, CER/WER, and stale/cancel safety.

## Phase 3 - Qwen3-ASR MLX 1.7B Final/Long-Draft Comparison

1. Run the same canonical quality and runtime evidence path against Qwen3-ASR MLX 1.7B.
2. Compare it against 0.6B for final and long-draft roles.
3. Do not promote it to partial backend unless it independently passes partial-role thresholds.

## Phase 4 - MiMo-V2.5-ASR MLX Final-Only And Coarse Incremental Probe

1. Validate MiMo as final-only backend first.
2. Measure steady RSS, cold/warm start, final latency, and quality on the same case set.
3. Optionally probe coarse incremental windows such as 3s and 5s.
4. Demote MiMo to reference-only if memory or final latency fail hard thresholds.

## Phase 5 - FunASR 2pass Fallback And Baseline Preservation

1. Keep FunASR 2pass as fallback unless a later backend proves both quality/runtime superiority and fallback safety.
2. Use FunASR baseline results as comparison anchors.
3. Require any default replacement to have a documented fallback path back to FunASR or Mock ASR for operational safety.

## Phase 6 - Backend Role Decision

1. Produce a single comparison artifact with role recommendations:
   - partial backend
   - final backend
   - fallback backend
   - reference-only models
   - rejected models
2. Include evidence paths, model metadata, metric explanations, hard gate pass/fail, soft signal notes, and open risks.
3. Assign every standalone candidate to exactly one role.
4. Record decision evidence in `specs/progress.md`.
5. Promote durable outcomes to PMB only after validation.

## Phase 7 - Real Audio, Control Flow, And App-Safety Preintegration

1. Before Swift integration, run real microphone/control-flow validation for:
   - Right Option push-to-talk
   - Option+Space long draft
   - Esc cancel
   - focus change during recording
   - secure/password fields
   - fallback behavior on service failure or timeout
2. Confirm partial text never enters the active input field.
3. Confirm final output still obeys existing paste/clipboard/focus safety.
4. Only then create a separate Swift app integration feature.

## Touched Areas

- `specs/2026-06-22-asr-backend-selection-roadmap/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

Future phases may touch:

- `eval/asr_streaming/incremental_ux_gate.py`
- `eval/asr_streaming/qwen3_mlx_cumulative_service.py`
- `eval/asr_streaming/README.md`
- service scripts under `scripts/`
- later Swift files only after backend selection evidence is complete

## Validation Implementation Notes

- This roadmap contract does not itself implement Phase 1-7.
- Each implementation phase should create or update a separate feature contract with its own validation commands.
- The next implementation feature should be Phase 1, because real model comparisons cannot be canonical until real backend adapters enter `incremental_ux_gate.py`.
- Phase 1 is complete only when at least one real localhost transport adapter can run through the canonical gate against a controlled local test service or backend, while fake-adapter regressions still pass.

## PMB Promotion Candidates

- Promote only after a backend role decision is validated:
  - canonical ASR backend roles
  - selected partial/final/fallback backend
  - durable operating and safety constraints

## Risks And Mitigations

- Risk: Existing fake-only gate is mistaken for completed model evaluation.
  Mitigation: Requirements and validation explicitly state that real backend adapters are required before model selection.
- Risk: Length coverage is mistaken for transcription quality.
  Mitigation: CER/WER must become hard quality dimensions; coverage is only a truncation signal.
- Risk: Realtime-mode RTF is used as compute evidence.
  Mitigation: Compute RTF is measured only in non-realtime mode; realtime mode measures latency/cadence/drift.
- Risk: Qwen3 first partial appears too slow under a naive 1.5s hard threshold.
  Mitigation: First partial is soft or measured relative to minimum audio window until calibrated by real service data.
- Risk: A high-quality final model consumes too much memory.
  Mitigation: RSS hard thresholds are required before app integration.
