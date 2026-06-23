# Decisions - Qwen3-ASR MLX HTTP Resource And Extended Gate Validation

## Confirmed Decisions

- D1: Use the existing HTTP service and `incremental_ux_gate.py --adapter http-json` as the validation surface.
- D2: Run only existing recorded cases in this feature; do not require new user recordings.
- D3: Track resource behavior with a sidecar PID monitor rather than adding resource logic to the gate itself.
- D4: Keep this feature eval-only and do not touch Swift app runtime files.
- D5: Reset the cumulative wrapper worker clock on every new session start. The first extended run showed that carrying prior session relative time into the next gate case can artificially delay partials by tens of seconds.

## Open Questions / Unresolved Choices

- Q1: Exact RSS and CPU thresholds for product acceptance remain provisional until this run collects first extended evidence.
- Q2: Whether the future Swift adapter should supervise this Python service directly or call a separate LaunchAgent remains out of scope.
- Q3: Whether code-switch technical term errors should be handled by model prompting, hotword correction, final correction, or a larger final model remains out of scope.

## PMB Promotion Candidates

- Promote extended gate viability and resource caveats only after validation evidence is recorded.
