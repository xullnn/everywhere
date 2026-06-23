# Validation — ASR Backend Evaluation Harness

## Completion rule

This feature can be marked `passes=true` only after the required checks pass and at least one FunASR WebSocket run has been completed against a real WAV file, unless the user explicitly approves deferring the server/audio run.

## Acceptance criteria

- A1: The repo contains an independent ASR backend eval harness under `eval/asr_streaming/`.
- A2: The harness validates case JSONL files and can list candidate model evidence.
- A3: The harness can stream 16 kHz mono int16 WAV data to the existing FunASR WebSocket server.
- A4: Run outputs include structured JSONL events and per-case JSON summaries with latency and accuracy metrics.
- A5: The feature does not alter macOS app behavior or default ASR provider.
- A6: Public benchmark evidence is labeled as public evidence and not confused with local validation.

## Automated checks

```bash
python3 -m py_compile eval/asr_streaming/run_eval.py
python3 eval/asr_streaming/run_eval.py list-models --registry eval/asr_streaming/model_registry.json
python3 eval/asr_streaming/run_eval.py validate-cases --cases eval/asr_streaming/cases.example.jsonl --allow-missing-audio
bash eval/asr_streaming/validate.sh
```

## Manual smoke checks

- Add or record one 16 kHz mono int16 WAV file.
- Start `bash scripts/run_funasr_python_server.sh`.
- Run:

```bash
python3 eval/asr_streaming/run_eval.py run \
  --adapter funasr-ws \
  --cases eval/asr_streaming/cases.local.jsonl \
  --ws-url ws://127.0.0.1:10095 \
  --out-dir eval/asr_streaming/results
```

## Optional / not-applicable checks

- Full AISHELL/WenetSpeech/FLEURS/Common Voice reruns are not required for this feature; public benchmark evidence is used for shortlist screening.
- Qwen3-ASR, MiMo, FireRed, and GLM local adapters are follow-up candidates, not required for this first implementation pass.

## Evidence required in `specs/progress.md`

- Commands run.
- Results.
- Any skipped checks with reasons.
- Whether a real FunASR server/audio run was completed or deferred.
