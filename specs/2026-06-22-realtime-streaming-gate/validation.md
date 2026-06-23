# Validation - Realtime ASR Streaming Gate

## Completion Rule

This feature can be marked `passes=true` only after the realtime gate script compiles, self-tests pass, the ASR harness validation passes, and at least one local FunASR WebSocket gate run is either executed or explicitly recorded as unavailable.

## Acceptance Criteria

- A1: `realtime_gate.py` rejects file-level final-only behavior in self-test.
- A2: `realtime_gate.py` rejects late partial after final in self-test.
- A3: `realtime_gate.py` records chunk traces separately from backend events.
- A4: Per-case summaries include realtime pass/fail status and Chinese metric explanations.
- A5: Aggregate summary includes pass/fail counts and fail reason counts.
- A6: Existing `eval/asr_streaming/validate.sh` passes.
- A7: No Swift/macOS app runtime files are changed.

## Automated Checks

```bash
python3 -m py_compile eval/asr_streaming/realtime_gate.py
python3 eval/asr_streaming/realtime_gate.py self-test
bash eval/asr_streaming/validate.sh
python3 -m json.tool specs/feature_matrix.json >/dev/null
python3 -m json.tool specs/2026-06-22-realtime-streaming-gate/feature.json >/dev/null
```

## Manual / Operational Checks

When the local FunASR WebSocket server is available:

```bash
bash scripts/run_funasr_python_server.sh
python3 eval/asr_streaming/realtime_gate.py run \
  --adapter funasr-ws \
  --model-id paraformer-current-funasr-ws \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --ws-url ws://127.0.0.1:10095 \
  --out-dir eval/asr_streaming/results/realtime-gate-funasr-smoke
```

For exploratory runs where failures should still produce summaries without failing the shell command, add `--warn-only`.

## Optional / Not Applicable Checks

- `swift build` and `swift test` are optional unless Swift files change.
- Qwen3-ASR MLX and MiMo MLX realtime gates are follow-up features because their current local paths do not yet expose an equivalent `push_pcm` streaming session.

## Evidence Required In `specs/progress.md`

- Commands run and pass/fail results.
- Any local FunASR gate result directory if executed.
- Explicit note that Swift app runtime was not changed.
