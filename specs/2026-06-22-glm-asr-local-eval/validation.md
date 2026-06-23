# Validation - GLM-ASR-Nano Local Evaluation Adapter

## Acceptance criteria

- A1: The local GLM model files are present under `.external/models/GLM-ASR-Nano-2512`.
- A2: A GLM runtime either loads locally or a concrete macOS/runtime blocker is recorded.
- A3: If runtime loads, at least one local WAV smoke case writes `events.jsonl`, per-case `summary.json`, and aggregate `summary.json`.
- A4: If smoke passes, run the full 10-case set.
- A5: Outputs include model metadata and Chinese metric explanations.
- A6: No macOS app runtime code is changed.

## Checks

```bash
python3 -m json.tool eval/asr_streaming/model_registry.json >/dev/null
python3 -m json.tool specs/feature_matrix.json >/dev/null
bash eval/asr_streaming/validate.sh
```

Optional when adapter is implemented:

```bash
.venv-glm-asr/bin/python eval/asr_streaming/run_eval.py run --adapter glm-asr-local --model-id glm-asr-nano-2512 --glm-asr-model .external/models/GLM-ASR-Nano-2512 --cases /tmp/localvoiceinput-glm-smoke.jsonl --out-dir eval/asr_streaming/results/glm-asr-nano-smoke
```
