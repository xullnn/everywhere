# Plan — ASR Backend Evaluation Harness

## Implementation sequence

1. Create SDD contract and feature matrix entry.
2. Add a model evidence registry and survey notes under `eval/asr_streaming/`.
3. Add a JSONL case schema and example cases derived from existing ASR smoke cases.
4. Implement `run_eval.py` with:
   - `list-models`
   - `validate-cases`
   - `run`
5. Implement the first runnable adapter: `funasr-ws`.
6. Add a shell validation script for non-server checks.
7. Run syntax and schema validation locally.

## Touched areas

- `specs/`
- `eval/asr_streaming/`

## Validation implementation notes

- Required checks:
  - `python3 -m py_compile eval/asr_streaming/run_eval.py`
  - `python3 eval/asr_streaming/run_eval.py list-models --registry eval/asr_streaming/model_registry.json`
  - `python3 eval/asr_streaming/run_eval.py validate-cases --cases eval/asr_streaming/cases.example.jsonl --allow-missing-audio`
  - `bash eval/asr_streaming/validate.sh`
- Optional server check:
  - start `bash scripts/run_funasr_python_server.sh`
  - run the harness against real WAV files and `ws://127.0.0.1:10095`

## PMB promotion candidates

- Add a durable note about the ASR eval harness only after it is validated with real audio.

## Risks and mitigations

- Risk: Public benchmark results do not reflect user dictation behavior.
  Mitigation: Keep a project-specific user recording set as the primary decision input.
- Risk: Mac M4 local runtime support differs from official CUDA/vLLM examples.
  Mitigation: Treat non-FunASR adapters as candidates until locally validated.
- Risk: Harness accidentally becomes production path.
  Mitigation: Keep it under `eval/` and do not import it from Swift targets.
