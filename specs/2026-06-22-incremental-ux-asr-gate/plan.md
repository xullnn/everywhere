# Plan - Incremental UX ASR Gate

## Implementation Sequence

1. Add a new `eval/asr_streaming/incremental_ux_gate.py` script.
2. Define a small backend protocol used by the gate:
   - `start(session_id)`
   - `push_pcm(...)`
   - `finish(...)`
   - `cancel(...)`
   - event collection for partial/final/ignored-stale events
3. Implement fake adapters:
   - valid incremental backend
   - final-only backend
   - late-partial backend
   - stale-session service-level self-test
   - cancel service-level self-test
4. Implement gate evaluation:
   - partial before user stop
   - final after user stop
   - final latency threshold
   - first partial threshold
   - final coverage threshold
   - no accepted partial after final
   - no accepted output after cancel
   - stale events ignored
5. Add per-case and aggregate JSON output.
6. Add self-tests that run without model weights or network services.
7. Add the new script to `eval/asr_streaming/validate.sh`.
8. Update `eval/asr_streaming/README.md` with the new gate and follow-up backend adapter expectations.
9. Record implementation evidence in `specs/progress.md`.

## Touched Areas

- `eval/asr_streaming/incremental_ux_gate.py`
- `eval/asr_streaming/validate.sh`
- `eval/asr_streaming/README.md`
- `specs/2026-06-22-incremental-ux-asr-gate/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

## Validation Implementation Notes

- Self-tests must use only fake adapters.
- Routine validation must not import MLX or load model weights.
- Real model/service adapters should be follow-up work unless the gate protocol itself is complete.
- Swift build/test are optional unless Swift files change.

## PMB Promotion Candidates

- After validation, promote the durable distinction between file-level quality, native streaming, and incremental UX gate evidence to `project_memory_bank/modules/asr_audio/summary.md`.

## Risks And Mitigations

- Risk: A diagnostic non-realtime run is mistaken for product latency.
  Mitigation: Summaries explicitly record `input_realtime_pacing` and `native_realtime_gate_eligible`.
- Risk: File-level model quality is conflated with incremental UX readiness.
  Mitigation: The final-only fake adapter must fail the gate by design.
- Risk: A future Qwen/MiMo adapter accepts stale output after cancel/final.
  Mitigation: Self-tests encode stale-session, cancel, and late-partial failures before real adapters are added.

## Notes

- This feature provides the shared gate. A real Qwen3-ASR MLX service boundary and MiMo final/coarse incremental probes should be separate SDD features.
