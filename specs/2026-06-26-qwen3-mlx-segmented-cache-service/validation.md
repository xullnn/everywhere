# Validation - Qwen3-ASR MLX Segmented Cache Service Prototype

## Completion Rule

This feature can be marked `passes=true` only when the new service script compiles, fake self-tests pass, the fake HTTP boundary passes the incremental UX gate, and concrete validation evidence is recorded in `specs/progress.md`.

## Acceptance Criteria

- A1: The service accepts timed 16 kHz mono PCM chunks and emits at least one useful partial before user stop in fake mode.
- A2: The service emits exactly one accepted final after finish in fake gate validation.
- A3: `cancel` does not emit accepted partial/final output after cancellation.
- A4: Stale session tokens are rejected and recorded as ignored diagnostic events.
- A5: Incoming audio is written into a local cache directory with session metadata.
- A6: Segment finalization can happen before user stop and does not require full-session recompute.
- A7: The existing cumulative service remains unchanged and usable.
- A8: macOS App behavior is unchanged.

## Automated Checks

```bash
python3 -m py_compile eval/asr_streaming/qwen3_mlx_segmented_cache_service.py
python3 eval/asr_streaming/qwen3_mlx_segmented_cache_service.py self-test
python3 eval/asr_streaming/qwen3_mlx_segmented_cache_service.py run --fake-backend --cases eval/asr_streaming/cases.smoke.local.jsonl --case-id zh_short_001 --max-segment-sec 1.5 --min-segment-sec 0.5 --out-dir eval/asr_streaming/results/qwen3-mlx-segmented-cache-service-fake-smoke
python3 eval/asr_streaming/incremental_ux_gate.py run --adapter http-json --service-url http://127.0.0.1:18096 --cases eval/asr_streaming/cases.smoke.local.jsonl --out-dir eval/asr_streaming/results/incremental-ux-gate-qwen3-segmented-cache-fake-smoke-realtime
```

The HTTP gate requires starting the service separately:

```bash
python3 eval/asr_streaming/qwen3_mlx_segmented_cache_service.py serve --fake-backend --port 18096 --max-segment-sec 1.5 --min-segment-sec 0.5
```

Use realtime pacing for the HTTP gate. `--no-realtime` pushes all audio almost instantly, so services that timestamp partials by audio time can correctly emit partials but still fail the gate's "before user stop" assertion.

## Optional Real-Model Check

```bash
PYTHONPATH=.external/repos/mlx-audio .venv-mimo/bin/python eval/asr_streaming/qwen3_mlx_segmented_cache_service.py run --model-id qwen3-asr-0.6b-mlx-8bit --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit --cases eval/asr_streaming/cases.long_prepared.local.jsonl --case-id existing_long_120_001 --language Chinese --max-segment-sec 30 --out-dir eval/asr_streaming/results/qwen3-mlx-segmented-cache-service-real-pilot
```

## Evidence Required In `specs/progress.md`

- commands run;
- result paths;
- whether fake protocol checks passed;
- whether real model check was run or skipped;
- known limitations before App integration.
