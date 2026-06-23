# Validation - Incremental UX Real Backend Adapters

## Completion Rule

This feature can be marked `passes=true` only after the real transport adapter works against a controlled local process-boundary service, existing fake-adapter regressions still pass, and evidence is recorded in `specs/progress.md`.

## Acceptance Criteria

- A1: `incremental_ux_gate.py` compiles.
- A2: Existing fake-adapter `self-test` still passes.
- A3: `http-json` adapter rejects missing `--service-url`.
- A4: A controlled local HTTP service can pass the incremental UX gate through real localhost transport.
- A5: Per-case summaries from the HTTP run preserve chunk trace path, event trace path, Chinese metric explanations, and gate metrics.
- A6: The feature does not touch Swift/macOS app runtime files.
- A7: The feature does not claim Qwen3, MiMo, FunASR, or any real model has passed.

## Automated Checks

```bash
python3 -m py_compile eval/asr_streaming/incremental_ux_gate.py
python3 -m py_compile eval/asr_streaming/fake_incremental_http_service.py
python3 eval/asr_streaming/incremental_ux_gate.py self-test
bash eval/asr_streaming/validate.sh
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-23-incremental-ux-real-backend-adapters/feature.json >/dev/null
```

## HTTP Transport Smoke

```bash
python3 eval/asr_streaming/fake_incremental_http_service.py --host 127.0.0.1 --port 18095
python3 eval/asr_streaming/incremental_ux_gate.py run \
  --adapter http-json \
  --service-url http://127.0.0.1:18095 \
  --cases eval/asr_streaming/cases.example.jsonl \
  --out-dir eval/asr_streaming/results/incremental-ux-http-fake-smoke \
  --no-realtime \
  --warn-only
```

## Optional / Not Applicable Checks

- `swift build` and `swift test` are optional because this feature does not change Swift code.
- Real Qwen3/MiMo/FunASR model services are not part of this feature.

## Evidence Required In `specs/progress.md`

- Commands run and pass/fail results.
- HTTP smoke output directory.
- Explicit statement that Swift runtime files were not changed.
