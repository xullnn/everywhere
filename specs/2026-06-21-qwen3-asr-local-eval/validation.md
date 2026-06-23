# Validation - Qwen3-ASR Local Evaluation Adapter

## Completion rule

This feature can be marked `passes=true` only after non-runtime checks pass and at least one real local WAV is processed by the `qwen3-asr-local` adapter. A full 10-case run is preferred but not required if the official runtime exposes a local Mac blocker that is documented in `specs/progress.md`.

## Acceptance criteria

- A1: `run_eval.py` exposes a `qwen3-asr-local` adapter.
- A2: `model_registry.json` lists `qwen3-asr-0.6b` with adapter and metadata.
- A3: A one-case smoke command exists and supports `DRY_RUN=1`.
- A4: A dependency/model preparation command exists.
- A5: A short WAV smoke run writes `events.jsonl`, per-case `summary.json`, and aggregate `summary.json` when runtime dependencies are available.
- A6: Summary output includes Chinese metric explanations and model metadata.
- A7: File-level inference does not claim realtime partial behavior.
- A8: No macOS app runtime code changes are made.

## Automated checks

```bash
python3 -m py_compile eval/asr_streaming/run_eval.py
python3 -m json.tool eval/asr_streaming/model_registry.json >/dev/null
python3 -m json.tool specs/feature_matrix.json >/dev/null
bash -n scripts/setup_qwen3_asr_venv.sh
bash -n scripts/download_qwen3_asr.sh
bash -n scripts/run_qwen3_asr_smoke.sh
bash eval/asr_streaming/validate.sh
```

## Manual smoke checks

```bash
DRY_RUN=1 bash scripts/run_qwen3_asr_smoke.sh
bash scripts/setup_qwen3_asr_venv.sh
bash scripts/download_qwen3_asr.sh
bash scripts/run_qwen3_asr_smoke.sh
```

Direct equivalent:

```bash
.venv/bin/python eval/asr_streaming/run_eval.py run \
  --adapter qwen3-asr-local \
  --model-id qwen3-asr-0.6b \
  --cases /tmp/localvoiceinput-qwen3-asr-smoke.jsonl \
  --out-dir eval/asr_streaming/results/qwen3-asr-0.6b-smoke
```

## Optional / not-applicable checks

- Full 10-case run is optional for initial feasibility if the one-case smoke run exposes a runtime blocker.
- Qwen3-ASR 1.7B validation is out of scope for this feature.
- vLLM streaming validation is out of scope for this feature.

## Evidence required in `specs/progress.md`

- Commands run.
- Results.
- Smoke output directory when available.
- Any dependency/runtime blockers.
- Whether a full 10-case run was completed or deferred.
