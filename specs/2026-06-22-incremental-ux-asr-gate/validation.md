# Validation - Incremental UX ASR Gate

## Completion Rule

This feature can be marked `passes=true` only when all required automated checks pass, the feature matrix remains valid JSON, and implementation evidence is recorded in `specs/progress.md`.

## Acceptance Criteria

- A1: `incremental_ux_gate.py` compiles.
- A2: Self-test accepts a fake valid incremental backend.
- A3: Self-test rejects a final-only backend.
- A4: Self-test rejects accepted late partial after final.
- A5: Self-test proves cancel produces no accepted partial/final output.
- A6: Self-test proves old-session events are ignored.
- A7: Per-case summaries include chunk trace path, event trace path, Chinese metric explanations, and gate failure reasons.
- A8: Aggregate summary includes pass/fail counts, fail reason counts, and gate configuration.
- A9: Existing ASR eval harness validation still passes.
- A10: No Swift/macOS app runtime files are changed.

## Automated Checks

```bash
python3 -m py_compile eval/asr_streaming/incremental_ux_gate.py
python3 eval/asr_streaming/incremental_ux_gate.py self-test
bash eval/asr_streaming/validate.sh
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-22-incremental-ux-asr-gate/feature.json >/dev/null
```

## Manual / Operational Checks

Optional diagnostic run with fake adapter output:

```bash
python3 eval/asr_streaming/incremental_ux_gate.py run \
  --adapter fake-valid \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --out-dir eval/asr_streaming/results/incremental-ux-gate-fake-smoke \
  --no-realtime
```

## Optional / Not Applicable Checks

- `swift build` and `swift test` are optional because this feature does not change Swift code.
- Real Qwen3-ASR MLX, MiMo, and FunASR adapters are follow-up work unless explicitly added to this feature later.

## Evidence Required In `specs/progress.md`

- Commands run and pass/fail results.
- Output directory for the fake smoke run if executed.
- Explicit statement that Swift runtime files were not changed.
