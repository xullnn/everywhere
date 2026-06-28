# Requirements - Qwen3-ASR MLX Segmented Cache Service Prototype

## Problem

The current Qwen3-ASR MLX App path uses a cumulative recompute service: while the user speaks, the service repeatedly recognizes accumulated audio prefixes, and on stop it recognizes the whole session again. This gives useful short-dictation behavior, but long dictation becomes structurally risky because the final recompute grows with the full recording.

The validated segmented-cache evaluation shows bounded segment finalization can reduce stop-time wait and backlog. The next step is a service-side prototype that turns that evaluation shape into a runtime contract without changing the macOS App safety layer.

## Scope

### IN

- Add a local-only Python service prototype under `eval/asr_streaming/`.
- Preserve the existing user-visible ASR contract:
  - `start`
  - timed PCM chunk input
  - pre-stop `partial`
  - post-stop `final`
  - `cancel`
  - stale session isolation
- Cache incoming audio to local disk while also keeping active in-memory chunks.
- Finalize bounded active segments during recording when segment policy triggers.
- Merge committed segment text plus active segment text into user-visible partial/final text.
- Expose internal diagnostic events for segment commit, cache path, model wall time, and backlog behavior.
- Provide fake-backend self-tests that do not require model weights.
- Provide an optional local HTTP boundary compatible with `incremental_ux_gate.py --adapter http-json`.
- Keep `native_realtime_gate_eligible=false`; this remains a wrapper around file-level recognition.

### OUT

- No Swift App default backend change.
- No changes to hotkeys, focus routing, paste, clipboard, floating panel, or macOS permissions logic.
- No cloud ASR or audio/text upload.
- No InputMethodKit migration.
- No default LLM correction or auto-send behavior.
- No claim that this prototype is the final production boundary detector.
- No overlap deduplication unless explicitly implemented and validated later.

## Requirements

- R1: The service must ignore stale chunk, finish, cancel, partial, and final operations whose session token no longer matches the current session.
- R2: `cancel` must prevent any accepted final output for that session.
- R3: User-visible output must use only `partial` and `final` events; segment diagnostics must not be required by the App UI.
- R4: The service must write incoming audio into a durable local session cache directory with machine-readable metadata.
- R5: Segment finalization must be bounded by runtime policy, initially hard duration plus optional soft partial-text character budget.
- R6: A committed segment must not require recomputing the whole prior session again.
- R7: On finish, the service must finalize only the current active segment and merge with already committed segment text.
- R8: The HTTP fake-backend path must be testable through the existing incremental UX gate without model weights.
- R9: Real-model validation should reuse the current Qwen3-ASR MLX 0.6B 8bit cache when available, but fake self-tests are sufficient for the first service-contract implementation.

## Constraints

- Local-only execution.
- Repository-local result and cache paths.
- Existing cumulative service remains available for A/B comparison.
- This feature is service/runtime experimentation only until a separate Swift integration spec is approved.

## Dependencies

- `2026-06-22-incremental-ux-asr-gate`
- `2026-06-22-qwen3-mlx-cumulative-service-prototype`
- `2026-06-23-qwen3-mlx-http-service-boundary`
- `2026-06-23-qwen3-mlx-http-resource-validation`
- `2026-06-26-segmented-cache-asr-evaluation`

## Related PMB context

- `project_memory_bank/core/current_focus.md`
- `project_memory_bank/modules/asr_audio/summary.md`
