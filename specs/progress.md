# SDD Progress

## 2026-06-20 — ASR backend evaluation harness

- Created feature contract for an independent ASR backend evaluation harness.
- Planned first implementation pass: model evidence registry, case schema, WAV-to-realtime-stream harness, and FunASR WebSocket baseline adapter.
- Implemented `eval/asr_streaming/` with model registry, survey notes, example JSONL cases, validation script, and `funasr-ws` streaming adapter.

### Files changed

- `specs/feature_matrix.json`
- `specs/progress.md`
- `specs/2026-06-20-asr-backend-eval-harness/*`
- `eval/asr_streaming/README.md`
- `eval/asr_streaming/model_registry.json`
- `eval/asr_streaming/model_survey.md`
- `eval/asr_streaming/cases.example.jsonl`
- `eval/asr_streaming/run_eval.py`
- `eval/asr_streaming/validate.sh`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/run_eval.py`
  Result: pass
  Notes: Python syntax check completed.
- Command: `python3 eval/asr_streaming/run_eval.py list-models --registry eval/asr_streaming/model_registry.json`
  Result: pass
  Notes: Listed baseline and candidate model registry entries.
- Command: `python3 eval/asr_streaming/run_eval.py validate-cases --cases eval/asr_streaming/cases.example.jsonl --allow-missing-audio`
  Result: pass
  Notes: Validated 5 example cases without requiring audio files.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Combined harness validation passed.
- Command: `swift build`
  Result: pass
  Notes: Swift package still builds after adding eval/spec files.
- Command: `swift test`
  Result: pass
  Notes: 45 XCTest tests passed with 0 failures.
- Command: `bash -n scripts/run_fun_asr_nano_smoke.sh`
  Result: pass
  Notes: Smoke wrapper shell syntax is valid.
- Command: `DRY_RUN=1 bash scripts/run_fun_asr_nano_smoke.sh`
  Result: pass
  Notes: Prepared `zh_short_001` with absolute audio path `/Users/xulelong/2025/projects/LocalVoiceInput/eval/asr_streaming/audio/zh_short_001.wav` and printed the expected `funasr-nano-local` run command without loading or downloading the model.
- Command: `.venv/bin/python eval/asr_streaming/run_eval.py run --adapter funasr-ws --cases /tmp/localvoiceinput-asr-smoke-cases.jsonl --ws-url ws://127.0.0.1:10095 --out-dir /tmp/localvoiceinput-asr-eval-smoke-2 --receive-timeout-sec 8 --no-realtime`
  Result: pass
  Notes: Existing FunASR sample WAV produced final text `每一天都要快乐哦`, CER 0.0, WER 0.0, 4 partial events, 1 final event.

### Blockers / open questions

- Need user/project-specific 16 kHz mono int16 WAV recordings before judging model quality for real dictation.
- Need separate runtime feasibility checks before adding Qwen3-ASR, Fun-ASR-Nano, MiMo, FireRed, or GLM adapters.

### Next recommended action

- Record or collect the first 30-100 local dictation WAV cases and run them through the current baseline.
- Then add the Fun-ASR-Nano adapter or runtime path as the first candidate beyond the current Paraformer baseline.

## 2026-06-20 — ASR recording CLI

### Summary

- Implemented a one-command guided recording flow for local ASR evaluation cases.
- The command `bash scripts/record_asr_cases.sh` prepares the pilot case file when missing, displays one case at a time, and records directly to `eval/asr_streaming/audio/<case_id>.wav`.
- The tool uses local `ffmpeg` with macOS `avfoundation` and does not upload audio or text.

### Files changed

- `scripts/record_asr_cases.sh`
- `eval/asr_streaming/record_cases.py`
- `eval/asr_streaming/README.md`
- `eval/asr_streaming/validate.sh`
- `specs/2026-06-20-asr-recording-cli/*`
- `specs/feature_matrix.json`

### Validation

- Command: `bash scripts/record_asr_cases.sh --dry-run`
  Result: pass
  Notes: Created `eval/asr_streaming/cases.local.jsonl` from the first 10 template cases and showed all planned output WAV paths.
- Command: `bash scripts/record_asr_cases.sh --list-devices`
  Result: pass
  Notes: Listed avfoundation devices including audio device `[0] MacBook Pro Microphone`.
- Command: `python3 eval/asr_streaming/run_eval.py validate-cases --cases eval/asr_streaming/cases.local.jsonl --allow-missing-audio`
  Result: pass
  Notes: Validated 10 pilot cases.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Syntax-checked both eval and recording tools; example case validation passed.
- Command: `swift build`
  Result: pass
  Notes: Swift package still builds.
- Command: `swift test`
  Result: pass
  Notes: 45 XCTest tests passed with 0 failures.

### Blockers / open questions

- Real microphone recording still requires the user to run the command interactively and grant macOS microphone permission to the terminal app if prompted.

### Next recommended action

- Run `bash scripts/record_asr_cases.sh`, record the 10 pilot cases, then validate and run the current FunASR baseline.

### Follow-up fix

- Fixed the recording CLI start flow so pressing `Enter` at `[Enter] start recording` immediately starts capture; the next `Enter` stops capture.
- Removed the extra pre-recording `input()` that made users press Enter twice before recording began.
- Cleared previously recorded local WAV files from `eval/asr_streaming/audio/`.
- Re-ran `bash eval/asr_streaming/validate.sh`, `bash scripts/record_asr_cases.sh --dry-run`, `bash scripts/record_asr_cases.sh --list-devices`, `swift build`, and `swift test`; all passed.

## 2026-06-20 — ASR eval long-text aggregation and local baseline rerun

### Summary

- Hardened the FunASR WebSocket eval summary so long-form `2pass-offline` segments are not blindly treated as complete whole-recording finals.
- Added summary diagnostics for offline segments, online partial aggregation, final selection strategy, partial-after-final, expected-text coverage ratio, and suspect incomplete final detection.
- Added an internal `self-test` command and included it in `eval/asr_streaming/validate.sh`.
- Ran the current local Paraformer/FunASR baseline against the 10 user-recorded pilot WAV files.

### Files changed

- `eval/asr_streaming/run_eval.py`
- `eval/asr_streaming/validate.sh`
- `specs/2026-06-20-asr-backend-eval-harness/decisions.md`
- `specs/progress.md`

### Validation

- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Python compile checks, example case validation, and transcript aggregation self-test passed.
- Command: `python3 eval/asr_streaming/run_eval.py validate-cases --cases eval/asr_streaming/cases.local.jsonl`
  Result: pass
  Notes: Validated all 10 local pilot cases with audio present.
- Command: `swift build`
  Result: pass
  Notes: Swift package still builds; eval harness changes are isolated from app runtime.
- Command: `swift test`
  Result: pass
  Notes: 45 XCTest tests passed with 0 failures.
- Command: `bash scripts/run_funasr_python_server.sh`
  Result: pass
  Notes: Local FunASR WebSocket server loaded `.external/models/paraformer-offline-small`, `.external/models/paraformer-online-small`, and `.external/models/fsmn-vad`.
- Command: `.venv/bin/python eval/asr_streaming/run_eval.py run --adapter funasr-ws --cases eval/asr_streaming/cases.local.jsonl --ws-url ws://127.0.0.1:10095 --out-dir eval/asr_streaming/results/baseline-paraformer-20260620-150952 --receive-timeout-sec 20`
  Result: pass
  Notes: Completed 10/10 user-recorded pilot cases. Per-case `events.jsonl` and `summary.json` files were written.

### Baseline result snapshot

| Case | CER | WER | Strategy | Suspect incomplete final |
|---|---:|---:|---|---|
| `zh_short_001` | 0.1053 | 0.1053 | `offline_segments` | false |
| `mix_tech_001` | 0.2121 | 0.6154 | `offline_segments` | false |
| `hotword_001` | 0.0159 | 0.7500 | `offline_segments` | false |
| `punctuation_001` | 0.0000 | 0.0000 | `offline_segments` | false |
| `zh_numbers_001` | 0.0800 | 0.0800 | `offline_segments` | false |
| `safety_001` | 0.0769 | 0.0769 | `offline_segments` | false |
| `long_120_001` | 0.0820 | 0.0820 | `online_text_fallback_after_short_offline` | true |
| `long_200_001` | 0.0658 | 0.0658 | `online_text_fallback_after_short_offline` | true |
| `long_400_001` | 0.1265 | 0.0769 | `online_text_fallback_after_short_offline` | true |
| `long_code_switch_001` | 0.4587 | 0.5000 | `online_text_fallback_after_short_offline` | true |

### Findings

- Current small Paraformer/FunASR baseline is usable for short Chinese dictation but repeatedly misrecognizes `语音` as `云`, and struggles with English product/model names.
- For long text, server `2pass-offline` output often covers only part of the recording. The harness now preserves raw events and flags those cases instead of presenting a short offline segment as complete final text.
- `long_code_switch_001` is the clearest stress failure: high CER/WER and severe degradation on technical English terms, product names, and mixed-language names.

### Next recommended action

- Use this result directory as the baseline when adding the next local candidate adapter.
- Prioritize a candidate with stronger Chinese-English mixed ASR behavior before spending time tuning hotwords for the current small Paraformer baseline.

## 2026-06-20 — ASR eval result metadata and Chinese metric explanations

### Summary

- Added Chinese explanations for core ASR evaluation metrics to future aggregate and per-case `summary.json` outputs.
- Added `--model-id` and `--registry` support so each run can embed tested model metadata in result JSON.
- Expanded `model_registry.json` so candidate models include Chinese supplier name, parameter scale, and release date with precision/uncertainty.
- Updated README and SDD requirements/decisions to make Chinese metric explanations and model metadata mandatory for future ASR result reviews.

### Files changed

- `eval/asr_streaming/run_eval.py`
- `eval/asr_streaming/model_registry.json`
- `eval/asr_streaming/README.md`
- `specs/2026-06-20-asr-backend-eval-harness/requirements.md`
- `specs/2026-06-20-asr-backend-eval-harness/decisions.md`
- `specs/progress.md`

### Validation

- Command: `python3 -m json.tool eval/asr_streaming/model_registry.json >/dev/null`
  Result: pass
  Notes: Model registry JSON is valid.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Python compile checks, example case validation, and transcript aggregation self-test passed.
- Command: `python3 eval/asr_streaming/run_eval.py list-models --registry eval/asr_streaming/model_registry.json`
  Result: pass
  Notes: Model list now prints Chinese vendor, parameter scale, and release date metadata.

### Next recommended action

- When adding the next adapter, pass the matching `--model-id` so result directories remain self-describing.

## 2026-06-20 — Fun-ASR-Nano local adapter implemented; smoke blocked by model download

### Summary

- Added a `funasr-nano-local` adapter to the independent ASR eval harness.
- The adapter loads `FunAudioLLM/Fun-ASR-Nano-2512` through FunASR `AutoModel`, processes existing 16 kHz mono WAV cases, writes one final event per case, and labels the result as file-level inference instead of realtime partial streaming.
- Added a one-command smoke wrapper: `bash scripts/run_fun_asr_nano_smoke.sh`.
- Kept this work isolated from the macOS app runtime, hotkeys, focus detection, clipboard, paste engine, and floating panel.

### Files changed

- `eval/asr_streaming/run_eval.py`
- `eval/asr_streaming/model_registry.json`
- `eval/asr_streaming/README.md`
- `scripts/run_fun_asr_nano_smoke.sh`
- `specs/2026-06-20-fun-asr-nano-local-eval/feature.json`
- `specs/2026-06-20-fun-asr-nano-local-eval/requirements.md`
- `specs/2026-06-20-fun-asr-nano-local-eval/plan.md`
- `specs/2026-06-20-fun-asr-nano-local-eval/validation.md`
- `specs/2026-06-20-fun-asr-nano-local-eval/decisions.md`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/run_eval.py`
  Result: pass
  Notes: Eval runner compiles.
- Command: `python3 -m json.tool eval/asr_streaming/model_registry.json >/dev/null`
  Result: pass
  Notes: Model registry JSON is valid.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null`
  Result: pass
  Notes: Feature matrix JSON is valid.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Existing eval harness schema and transcript aggregation checks pass.
- Command: `python3 eval/asr_streaming/run_eval.py list-models --registry eval/asr_streaming/model_registry.json`
  Result: pass
  Notes: `fun-asr-nano-2512` is listed with adapter `funasr-nano-local`, supplier, parameter scale, and release date metadata.
- Command: `swift build`
  Result: pass
  Notes: macOS app package still builds.
- Command: `swift test`
  Result: pass
  Notes: 45 XCTest tests passed with 0 failures.

### Blocked smoke

- Command attempted: `.venv/bin/python eval/asr_streaming/run_eval.py run --adapter funasr-nano-local --model-id fun-asr-nano-2512 --cases /tmp/localvoiceinput-fun-asr-nano-smoke.jsonl --out-dir eval/asr_streaming/results/fun-asr-nano-smoke-20260620 --funasr-hub ms --funasr-device cpu`

  Result: blocked
  Notes: ModelScope started downloading `FunAudioLLM/Fun-ASR-Nano-2512`; `model.pt` is about 1.98 GB and was downloading around 0.5 MB/s. The run was interrupted after roughly 59 MB because completion would take about an hour or longer.
- Command attempted: `.venv/bin/python -m pip install --no-cache-dir 'huggingface_hub[hf_xet]'`
  Result: blocked
  Notes: Hugging Face tooling download was even slower, around 9-10 KB/s for `hf_xet`; installation was interrupted.

### Current status

- `specs/feature_matrix.json` marks `2026-06-20-fun-asr-nano-local-eval` as `blocked`, `passes=false`.
- The blocker is dependency/model download speed, not harness compilation or app runtime failure.
- Next action: retry `bash scripts/run_fun_asr_nano_smoke.sh` on a faster network or after manually pre-downloading/caching the model, then run the full 10-case local pilot if the one-case smoke succeeds.

## 2026-06-20 — Fun-ASR-Nano download switched to resumable background job

### Summary

- Added `scripts/download_fun_asr_nano.sh` to separate model download from smoke inference.
- The script uses ModelScope `snapshot_download` for metadata and `curl --continue-at -` for `model.pt`, then validates byte size and SHA256 before moving the file into the ModelScope cache.
- Started a one-shot macOS launchd job with label `localvoiceinput.fun-asr-nano.download`.

### Current download state

- Log file: `eval/asr_streaming/results/fun-asr-nano-download.log`
- Temp file: `~/.cache/modelscope/hub/models/._____temp/FunAudioLLM/Fun-ASR-Nano-2512/model.pt`
- Final target: `~/.cache/modelscope/hub/models/FunAudioLLM/Fun-ASR-Nano-2512/model.pt`
- Resume point at launch: `83,640,320` bytes of `2,127,426,538` bytes.
- Observed speed remained low, roughly 100-150 KB/s, so completion may take several hours unless network conditions improve.

### Useful monitor commands

```bash
launchctl list | grep localvoiceinput.fun-asr-nano.download
tail -f eval/asr_streaming/results/fun-asr-nano-download.log
ls -lh ~/.cache/modelscope/hub/models/._____temp/FunAudioLLM/Fun-ASR-Nano-2512/model.pt
```

### Next action after download completes

```bash
bash scripts/run_fun_asr_nano_smoke.sh
```

## 2026-06-21 — Fun-ASR-Nano local smoke and full 10-case run passed

### Summary

- Completed Fun-ASR-Nano model download and verified `model.pt` size/SHA256.
- Registered `model.pt` in the ModelScope `.msc` cache index to prevent repeated downloads after manual resumable `curl` download.
- Installed local Nano runtime dependencies in `.venv`: `transformers`, `accelerate`, `safetensors`, `tokenizers`, and `tiktoken`.
- Updated `scripts/setup_funasr_venv.sh` so recreated environments include the Nano dependency stack.
- Resolved missing `remote_code` by using the installed `funasr.models.fun_asr_nano.model.py` when the model repo has no `model.py`.
- Disabled VAD by default for `funasr-nano-local`; FunASR 1.3.1 loads `fsmn-vad`, but `AutoModel.inference_with_vad` raises `KeyError(0)` when merging VAD segments with Fun-ASR-Nano result dictionaries.

### Validation

- Command: `bash scripts/download_fun_asr_nano.sh`
  Result: pass
  Notes: `model.pt` exists at `~/.cache/modelscope/hub/models/FunAudioLLM/Fun-ASR-Nano-2512/model.pt`, size `2,127,426,538` bytes, SHA256 `81fec8616083c69377f3ceef36aba3655660ee0ca69a5d4a1e9810cd340ca499`.
- Command: `FUNASR_HUB=ms FUNASR_DEVICE=cpu bash scripts/run_fun_asr_nano_smoke.sh`
  Result: pass
  Notes: Output directory `eval/asr_streaming/results/fun-asr-nano-smoke`; case `zh_short_001` completed with `status=ok`, CER `0.1053`, WER `0.1053`, RTF `0.3779`. Final text was `我想要做一个本地离线的中文云输入工具。`.
- Command: `.venv/bin/python eval/asr_streaming/run_eval.py run --adapter funasr-nano-local --model-id fun-asr-nano-2512 --cases eval/asr_streaming/cases.local.jsonl --out-dir eval/asr_streaming/results/fun-asr-nano-local-20260621-131234 --funasr-hub ms --funasr-device cpu`
  Result: pass
  Notes: Completed 10/10 local cases with `status=ok`.

### Full-run result snapshot

- Result directory: `eval/asr_streaming/results/fun-asr-nano-local-20260621-131234`
- Average CER: `0.0758`
- Average WER: `0.2236`
- Average RTF: `0.2080`
- Average final latency: `3961.5 ms`
- Baseline Paraformer comparison from `eval/asr_streaming/results/baseline-paraformer-20260620-150952`: average CER improved from `0.1223` to `0.0758`; average WER improved from `0.2352` to `0.2236`; average RTF improved from `3.6341` to `0.2080`.

### Findings

- Fun-ASR-Nano is much faster than the current Paraformer WebSocket baseline in this file-level CPU path.
- Long Chinese cases improved strongly: `long_120_001` CER `0.0082`, `long_200_001` CER `0.0000`.
- The model still repeatedly misrecognizes `语音` as `云`, including `zh_short_001` and `zh_numbers_001`.
- Numeric normalization affects direct CER: `zh_numbers_001` expected Chinese date words, while Nano emitted `2026年5月13日`, causing CER `0.3600` despite semantically reasonable output.
- Technical English/product names remain unstable. Examples include `Qwen3-ASR` -> `千问三杠ASR`, `ClipboardManager` -> `Clip Word Manager`, `Cursor` -> `Cursory`, and `Right Option` in the long script -> `New Option`.
- This adapter is still file-level only. It does not measure first partial latency, partial rewrite stability, or floating-panel realtime behavior.

### Status update

- `eval/asr_streaming/model_registry.json` marks `fun-asr-nano-2512.local_validation` as `full_10_case_passed_2026-06-21_no_vad`.
- `specs/feature_matrix.json` marks `2026-06-20-fun-asr-nano-local-eval` as `validated`, `passes=true`.
- Next recommended action: create the next candidate adapter for Qwen3-ASR 0.6B/1.7B, or investigate Fun-ASR-Nano streaming/GGUF only if we accept its technical-term weaknesses and can fix hotwords or normalization.

## 2026-06-21 — 2026-06-20-fun-asr-nano-local-eval closeout

### Summary

- Closed out the Fun-ASR-Nano local evaluation adapter as validated.
- Confirmed the adapter stays independent from the macOS app runtime.
- Added follow-up candidates for Qwen3-ASR evaluation and deeper Fun-ASR-Nano runtime investigation.

### Files changed

- `eval/asr_streaming/run_eval.py`
- `eval/asr_streaming/model_registry.json`
- `eval/asr_streaming/README.md`
- `scripts/download_fun_asr_nano.sh`
- `scripts/run_fun_asr_nano_smoke.sh`
- `scripts/setup_funasr_venv.sh`
- `specs/2026-06-20-fun-asr-nano-local-eval/feature.json`
- `specs/2026-06-20-fun-asr-nano-local-eval/decisions.md`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/run_eval.py`
  Result: pass
  Notes: Eval runner compiles.
- Command: `python3 -m json.tool eval/asr_streaming/model_registry.json >/dev/null && python3 -m json.tool specs/feature_matrix.json >/dev/null`
  Result: pass
  Notes: Registry and feature matrix JSON are valid.
- Command: `bash -n scripts/download_fun_asr_nano.sh && bash -n scripts/run_fun_asr_nano_smoke.sh && bash -n scripts/setup_funasr_venv.sh`
  Result: pass
  Notes: Shell scripts parse.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Example schema and transcript aggregation checks pass.
- Command: `swift build`
  Result: pass
  Notes: Swift package still builds; no macOS runtime code was changed.
- Command: `swift test`
  Result: pass
  Notes: 45 XCTest tests passed with 0 failures.

### Blockers / open questions

- No blocker remains for the file-level local adapter.
- Open follow-up: FunASR 1.3.1 VAD merge path fails with `KeyError(0)` for Nano result dictionaries.
- Open follow-up: realtime partial behavior is not validated by this adapter.
- Open follow-up: technical/product terms still need either stronger model comparison or hotword/domain correction work.

### Next recommended action

- Evaluate Qwen3-ASR 0.6B/1.7B on the same 10 local WAV cases before committing to a streaming integration path.

## 2026-06-21 — 2026-06-21-qwen3-asr-local-eval implementation pass blocked at dependency download

### Summary

- Created the Qwen3-ASR local evaluation feature contract.
- Added a `qwen3-asr-local` file-level adapter to the eval harness.
- Added Qwen3-ASR 0.6B model registry wiring and README commands.
- Added scripts for Qwen3-ASR runtime setup, model download, and one-case smoke.
- Kept all changes scoped to eval/scripts/specs; no macOS app runtime, hotkey, focus, clipboard, paste, audio capture, or floating-panel code was changed.

### Files changed

- `eval/asr_streaming/run_eval.py`
- `eval/asr_streaming/model_registry.json`
- `eval/asr_streaming/README.md`
- `scripts/setup_qwen3_asr_venv.sh`
- `scripts/download_qwen3_asr.sh`
- `scripts/run_qwen3_asr_smoke.sh`
- `specs/2026-06-21-qwen3-asr-local-eval/feature.json`
- `specs/2026-06-21-qwen3-asr-local-eval/requirements.md`
- `specs/2026-06-21-qwen3-asr-local-eval/plan.md`
- `specs/2026-06-21-qwen3-asr-local-eval/validation.md`
- `specs/2026-06-21-qwen3-asr-local-eval/decisions.md`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/run_eval.py`
  Result: pass
  Notes: Eval runner compiles with the new `qwen3-asr-local` adapter.
- Command: `python3 -m json.tool eval/asr_streaming/model_registry.json >/dev/null && python3 -m json.tool specs/feature_matrix.json >/dev/null && python3 -m json.tool specs/2026-06-21-qwen3-asr-local-eval/feature.json >/dev/null`
  Result: pass
  Notes: Model registry, feature matrix, and feature metadata JSON are valid.
- Command: `bash -n scripts/setup_qwen3_asr_venv.sh && bash -n scripts/download_qwen3_asr.sh && bash -n scripts/run_qwen3_asr_smoke.sh`
  Result: pass
  Notes: New shell scripts parse.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Existing eval harness schema and transcript aggregation checks pass.
- Command: `python3 eval/asr_streaming/run_eval.py list-models --registry eval/asr_streaming/model_registry.json`
  Result: pass
  Notes: `qwen3-asr-0.6b` is listed with adapter `qwen3-asr-local`, supplier, parameter scale, and release date metadata.
- Command: `DRY_RUN=1 bash scripts/run_qwen3_asr_smoke.sh`
  Result: pass
  Notes: Prepared `zh_short_001` and printed the direct `qwen3-asr-local` smoke command.
- Command: `.venv/bin/python eval/asr_streaming/run_eval.py run --adapter qwen3-asr-local --model-id qwen3-asr-0.6b --cases /tmp/localvoiceinput-qwen3-asr-smoke.jsonl --out-dir eval/asr_streaming/results/qwen3-asr-0.6b-smoke --qwen3-model .external/models/Qwen3-ASR-0.6B --qwen3-device cpu --qwen3-dtype auto --qwen3-language Chinese`
  Result: blocked
  Notes: Runtime dependency `qwen-asr` is not installed yet; the error is explicit: `Missing Python package 'qwen-asr'. Run scripts/setup_qwen3_asr_venv.sh first.`

### Blockers / open questions

- `qwen-asr` dependency installation was blocked by slow wheel download. The default full install pulled Gradio/Flask demo dependencies; the setup script was changed to install a lean transformers runtime by default.
- The slow dependency was `nagisa==0.2.11`; observed download speed was roughly 18-21 KB/s and the install was interrupted at about 2.4 MB of 21.3 MB in the final lean attempt.
- The local environment was restored to `setuptools 81.0.0` because `setuptools 82.0.1` conflicts with the current `torch 2.12.0` requirement of `setuptools<82`.
- Qwen3-ASR 0.6B model download has not started in this pass. The model is expected to be about 1.88 GB and should be downloaded only after dependency setup can complete or through a detached/resumable job.

### Next recommended action

- Retry `QWEN3_INSTALL_MODE=runtime bash scripts/setup_qwen3_asr_venv.sh` on a better network or as a long-running detached job, then run `bash scripts/download_qwen3_asr.sh` and `bash scripts/run_qwen3_asr_smoke.sh`.

### Detached job started

- Command: `launchctl submit -l localvoiceinput.qwen3-asr.setup-download -- /bin/zsh -lc '<setup then download>'`
  Result: started
  Notes: Background job label is `localvoiceinput.qwen3-asr.setup-download`; log path is `eval/asr_streaming/results/qwen3-asr-setup-download.log`. Initial log confirmed the job entered `nagisa==0.2.11` download.

## 2026-06-21 — Qwen3-ASR download switched to curl resume

### Summary

- Confirmed the original ModelScope `snapshot_download` process stopped making reliable progress on `model.safetensors`.
- Stopped the old `localvoiceinput.qwen3-asr.setup-download` launchd job and preserved the partial file.
- Updated `scripts/download_qwen3_asr.sh` to use ModelScope `snapshot_download` only for metadata/small files and `curl --continue-at -` for `model.safetensors`.
- Restarted the same launchd label with the curl resume path.

### Files changed

- `scripts/download_qwen3_asr.sh`
- `specs/2026-06-21-qwen3-asr-local-eval/decisions.md`
- `specs/progress.md`

### Validation

- Command: `bash -n scripts/download_qwen3_asr.sh`
  Result: pass
  Notes: Download script parses after the curl-resume change.
- Command: `curl -I -L --connect-timeout 20 'https://www.modelscope.cn/api/v1/models/Qwen/Qwen3-ASR-0.6B/repo?Revision=master&FilePath=model.safetensors'`
  Result: pass
  Notes: Response includes `Content-Length: 1876091704` and `Accept-Ranges: bytes`.
- Command: `launchctl submit -l localvoiceinput.qwen3-asr.setup-download -- /bin/zsh -lc '<curl-resume download>'`
  Result: started
  Notes: The resumed transfer started from byte `559939584`.

### Blockers / open questions

- The curl resume path is now moving data, but the observed one-minute rate was only about 11-12 KB/s.
- At that rate, the remaining model file can still take more than a day.

### Next recommended action

- Keep the curl resume job running for now; if speed remains around 10-20 KB/s, switch networks or use a faster mirror/manual transfer before running Qwen3-ASR smoke.

## 2026-06-21 — Qwen3-ASR remote download comparison on MBP2015

### Summary

- Kept the local curl-resume download running under launchd label `localvoiceinput.qwen3-asr.setup-download`.
- Verified the LAN/EasyTier SSH target `mbp2015-easytier` is reachable and has enough free disk space.
- Started a second resumable download on the 2015 MacBook Pro at `~/LocalVoiceInputModels/Qwen3-ASR-0.6B/model.safetensors`.

### Validation

- Local status: `.external/models/Qwen3-ASR-0.6B/._____temp/model.safetensors` had `608825344` bytes, about `32.45%`.
- Remote status: `~/LocalVoiceInputModels/Qwen3-ASR-0.6B/model.safetensors` had `18395136` bytes, about `0.98%`.
- Command: 60-second size sampling across local and remote files.
  Result: remote download was not materially faster in this sample.
  Notes: Local measured about `17.68 KiB/s` with estimated `19.42 h` remaining; remote measured about `22.60 KiB/s` with estimated `22.28 h` remaining because it started from zero.

### Blockers / open questions

- The remote machine being off VPN did not produce a clear speedup in the first measured sample.
- Both transfers are safe to leave running, but the local partial remains the leading candidate unless the remote speed improves substantially.

## 2026-06-22 — Qwen3-ASR model download completed

### Summary

- The Qwen3-ASR 0.6B `model.safetensors` file is complete on both the local Mac and the 2015 MacBook Pro.
- The local launchd download job was removed after completion because it had entered a repeat validation loop.
- No remote curl download process remains running.

### Validation

- Local file: `.external/models/Qwen3-ASR-0.6B/model.safetensors`
  Size: `1876091704` bytes, `100.00%`.
- Remote file: `~/LocalVoiceInputModels/Qwen3-ASR-0.6B/model.safetensors`
  Size: `1876091704` bytes, `100.00%`.
- Local SHA-256: `79d6cbd4c98c7bbffe9db2edac07f56cd6637d0d5944b27f6c2b8353840323ea`
- Remote SHA-256: `79d6cbd4c98c7bbffe9db2edac07f56cd6637d0d5944b27f6c2b8353840323ea`
- Command: `launchctl remove localvoiceinput.qwen3-asr.setup-download`
  Result: pass
  Notes: Subsequent process check found no local download/curl job.

### Next recommended action

- Run the Qwen3-ASR one-case smoke test now that the local model file is available.

## 2026-06-22 — P1 plus MiMo MLX remote downloads started

### Summary

- Started a resumable manifest-based download job on the 2015 MacBook Pro through `mbp2015-easytier`.
- Download targets:
  - `Qwen/Qwen3-ASR-1.7B`
  - `zai-org/GLM-ASR-Nano-2512`
  - `FireRedTeam/FireRedASR2-AED`
  - `mlx-community/MiMo-V2.5-ASR-MLX`
  - `mlx-community/MiMo-Audio-Tokenizer`
- Direct `huggingface.co` access from the remote machine timed out, so the manifest URLs were switched to `hf-mirror.com` for transfer.
- The manifest still came from the Hugging Face API and retains expected file sizes and SHA-256 values for large LFS files, so completed downloads can still be integrity checked against original HF metadata.

### Validation

- Remote base path: `~/LocalVoiceInputModels/hf`.
- Remote manifest: `~/LocalVoiceInputModels/hf/download_manifest.json`.
- Remote log: `~/LocalVoiceInputModels/hf/download_from_manifest.log`.
- Remote PID file: `~/LocalVoiceInputModels/hf/download_from_manifest.pid`.
- Manifest status: 5 models, 51 files, all 51 URLs rewritten to `https://hf-mirror.com/`.
- Known total selected download size: about `19.61 GiB`.
- The restarted job began downloading `Qwen/Qwen3-ASR-1.7B`; small files completed and the first large safetensors shard started transferring.

### Blockers / open questions

- Completion is not yet confirmed. Need monitor the remote job until all files finish and SHA checks pass.
- After completion, decide whether to copy the selected model directories back to the local M4 machine first or run early adapter feasibility checks directly against the remote cache.

## 2026-06-22 — Qwen3-ASR 0.6B one-case smoke passed

### Summary

- Ran the Qwen3-ASR 0.6B local file-level adapter against one local WAV case.
- The adapter loaded the local model from `.external/models/Qwen3-ASR-0.6B` and produced a final transcript.
- This validates the local file-level screening path only. It does not validate realtime partial behavior, vLLM streaming, floating-panel latency, or macOS app insertion behavior.

### Validation

- Command: `DRY_RUN=1 bash scripts/run_qwen3_asr_smoke.sh`
  Result: pass
  Notes: Prepared `zh_short_001` and resolved the command to `.venv/bin/python eval/asr_streaming/run_eval.py run --adapter qwen3-asr-local --model-id qwen3-asr-0.6b ... --qwen3-device cpu`.
- Command: `bash scripts/run_qwen3_asr_smoke.sh`
  Result: pass
  Output directory: `eval/asr_streaming/results/qwen3-asr-0.6b-smoke`.
- Output files:
  - `eval/asr_streaming/results/qwen3-asr-0.6b-smoke/summary.json`
  - `eval/asr_streaming/results/qwen3-asr-0.6b-smoke/zh_short_001/events.jsonl`
  - `eval/asr_streaming/results/qwen3-asr-0.6b-smoke/zh_short_001/summary.json`

### Smoke result

- Case: `zh_short_001`.
- Expected: `我想要做一个本地离线的中文语音输入工具。`
- Final: `我想要做一个本地离线的中文云输入工具。`
- CER: `0.1053`, meaning the character error rate was about `10.53%`; lower is better.
- WER: `0.1053`, meaning the token/word error rate was about `10.53%`; lower is better.
- RTF: `2.2101`, meaning CPU file-level inference took about `2.21x` the audio duration; lower than `1` would be faster than realtime.
- Final latency: `13909 ms`.

### Follow-up

- Run the full local 10-case set for Qwen3-ASR 0.6B or test MPS before full-case evaluation if CPU latency remains a concern.
- Keep Qwen3-ASR 1.7B as a follow-up after its remote download completes.

## 2026-06-22 — Qwen3-ASR 0.6B full 10-case CPU run passed

### Summary

- Ran Qwen3-ASR 0.6B through all 10 local WAV cases with the CPU file-level adapter.
- All 10 cases completed with `status=ok`.
- Compared against the existing Fun-ASR-Nano 10-case run using the same local cases and metric definitions.
- This remains file-level screening evidence only. It does not validate realtime partial behavior, vLLM streaming, floating-panel latency, or macOS app insertion behavior.

### Validation

- Command: `.venv/bin/python eval/asr_streaming/run_eval.py run --adapter qwen3-asr-local --model-id qwen3-asr-0.6b --qwen3-model .external/models/Qwen3-ASR-0.6B --qwen3-device cpu --qwen3-dtype auto --qwen3-language Chinese --cases eval/asr_streaming/cases.local.jsonl --out-dir eval/asr_streaming/results/qwen3-asr-0.6b-full-20260622-100827`
  Result: pass.
- Output directory: `eval/asr_streaming/results/qwen3-asr-0.6b-full-20260622-100827`.
- Output files: aggregate `summary.json`, plus per-case `events.jsonl` and `summary.json` for all 10 cases.

### Aggregate metrics

- Qwen3-ASR 0.6B:
  - Case count: `10`, ok count: `10`.
  - Mean CER: `0.0470`, meaning average character error rate was about `4.70%`; lower is better.
  - Mean WER: `0.1918`, meaning average token/word error rate was about `19.18%`; lower is better.
  - Mean RTF: `0.1264`, meaning file-level CPU inference averaged about `0.13x` audio duration; lower than `1` is faster than realtime.
  - Mean final latency: `3291 ms`.
- Existing Fun-ASR-Nano full run for comparison:
  - Mean CER: `0.0758`.
  - Mean WER: `0.2236`.
  - Mean RTF: `0.2080`.
  - Mean final latency: `3962 ms`.

### Per-case observations

- Strong cases:
  - `long_200_001`, `punctuation_001`, and `safety_001` reached `CER=0`, `WER=0`.
  - `long_120_001` had `CER=0.0082`, with the recurring `本机` -> `手机` error.
- Weak cases:
  - `mix_tech_001`: `CER=0.1515`, `WER=0.5385`; model names still degrade to forms such as `Fun ASR`, `千问三`, and `杠 ASR`.
  - `zh_short_001`: `CER=0.1053`; `语音输入` became `云输入`.
  - `zh_numbers_001`: `CER=0.1200`; `语音输入` became `云输入`, and `规整` became `归整`.
  - `long_code_switch_001`: `CER=0.0480`, `WER=0.3333`; technical model names and product/module names still need hotword normalization.

### Follow-up

- Keep Qwen3-ASR 0.6B in the shortlist because it improved aggregate CER, WER, and RTF versus Fun-ASR-Nano on the local 10-case set.
- Do not choose it as the app runtime yet because file-level results do not prove realtime partial UX or streaming session behavior.
- Next useful comparisons: Qwen3-ASR 1.7B after download, GLM-ASR-Nano-2512, FireRedASR2-AED, and MiMo-V2.5-ASR-MLX.

## 2026-06-22 — Remote P1 plus MiMo download checkpoint

### Summary

- Checked the `mbp2015-easytier` background manifest downloader.
- `Qwen/Qwen3-ASR-1.7B` completed on the remote machine.
- `zai-org/GLM-ASR-Nano-2512` completed on the remote machine.
- `FireRedTeam/FireRedASR2-AED` was in progress at about `800MB`.
- `mlx-community/MiMo-V2.5-ASR-MLX` and `mlx-community/MiMo-Audio-Tokenizer` had not started yet.

### Validation

- Remote process: `~/LocalVoiceInputModels/hf/download_from_manifest.py`, still running.
- Remote status file: `~/LocalVoiceInputModels/hf/download_status.json`.
- Remote directories observed:
  - `~/LocalVoiceInputModels/hf/Qwen__Qwen3-ASR-1.7B`: about `4.4G`.
  - `~/LocalVoiceInputModels/hf/zai-org__GLM-ASR-Nano-2512`: about `4.2G`.
  - `~/LocalVoiceInputModels/hf/FireRedTeam__FireRedASR2-AED`: about `800M`.

## 2026-06-22 — Qwen3-ASR 1.7B local sync and full 10-case CPU run passed

### Summary

- Synced `Qwen/Qwen3-ASR-1.7B` from the 2015 MacBook Pro cache to `.external/models/Qwen3-ASR-1.7B`.
- Ran a one-case smoke test and then the full 10-case local WAV set through the same `qwen3-asr-local` CPU file-level adapter.
- All 10 full-run cases completed with `status=ok`.
- This remains file-level screening evidence only. It does not validate realtime partial behavior, vLLM streaming, floating-panel latency, or macOS app insertion behavior.

### Validation

- Sync command: `rsync -aP --partial --stats mbp2015-easytier:'$HOME/LocalVoiceInputModels/hf/Qwen__Qwen3-ASR-1.7B/' .external/models/Qwen3-ASR-1.7B/`
  Result: pass.
- Local model directory: `.external/models/Qwen3-ASR-1.7B`, about `4.4G`.
- Full run command: `.venv/bin/python eval/asr_streaming/run_eval.py run --adapter qwen3-asr-local --model-id qwen3-asr-1.7b --qwen3-model .external/models/Qwen3-ASR-1.7B --qwen3-device cpu --qwen3-dtype auto --qwen3-language Chinese --cases eval/asr_streaming/cases.local.jsonl --out-dir eval/asr_streaming/results/qwen3-asr-1.7b-full-20260622-102709`
  Result: pass.
- Output directory: `eval/asr_streaming/results/qwen3-asr-1.7b-full-20260622-102709`.

### Aggregate comparison

| Model | Mean CER | Mean WER | Mean RTF | Mean final latency |
|---|---:|---:|---:|---:|
| Fun-ASR-Nano | `0.0758` | `0.2236` | `0.2080` | `3962 ms` |
| Qwen3-ASR 0.6B | `0.0470` | `0.1918` | `0.1264` | `3291 ms` |
| Qwen3-ASR 1.7B | `0.0431` | `0.1760` | `0.1849` | `5065 ms` |

### Interpretation

- Qwen3-ASR 1.7B improved quality slightly over 0.6B on this local 10-case set.
- The clearest 1.7B improvement was `long_code_switch_001`: WER improved from `0.3333` on 0.6B to `0.1944`.
- 1.7B was slower than 0.6B in this CPU file-level path: mean RTF increased from `0.1264` to `0.1849`.
- The recurring domain errors remain:
  - `语音输入` -> `云输入`.
  - `FunASR`, `Qwen3-ASR`, `MiMo-V2.5-ASR`, `LocalVoiceInput`, and module names still need hotword normalization.

### Follow-up

- Keep both Qwen3-ASR 0.6B and 1.7B in the shortlist.
- Treat 1.7B as higher quality but slower in the current CPU file-level path.
- Do not choose a runtime backend until GLM-ASR-Nano-2512, FireRedASR2-AED, and MiMo-V2.5-ASR-MLX have comparable local results or documented blockers.

## 2026-06-22 — GLM-ASR-Nano local sync and full 10-case CPU run passed

### Summary

- Synced `zai-org/GLM-ASR-Nano-2512` from the 2015 MacBook Pro cache to `.external/models/GLM-ASR-Nano-2512`.
- Created a separate `.venv-glm-asr` runtime using Python 3.11 with `transformers==5.12.1`, because the existing Qwen runtime's `transformers==4.57.6` does not include `GlmAsrForConditionalGeneration` or `GlmAsrProcessor`.
- Added a local file-level `glm-asr-local` adapter to the independent eval harness.
- Ran a one-case smoke test and then the full 10-case local WAV set.
- All 10 full-run cases completed with `status=ok`.
- This remains file-level screening evidence only. It does not validate realtime partial behavior, floating-panel latency, or macOS app insertion behavior.

### Validation

- Sync command: `rsync -aP --partial --stats mbp2015-easytier:'$HOME/LocalVoiceInputModels/hf/zai-org__GLM-ASR-Nano-2512/' .external/models/GLM-ASR-Nano-2512/`
  Result: pass.
- Local model directory: `.external/models/GLM-ASR-Nano-2512`, about `4.2G`.
- Smoke run command: `.venv-glm-asr/bin/python eval/asr_streaming/run_eval.py run --adapter glm-asr-local --model-id glm-asr-nano-2512 --glm-asr-model .external/models/GLM-ASR-Nano-2512 --glm-asr-device cpu --glm-asr-dtype auto --glm-asr-local-files-only --cases /tmp/localvoiceinput-glm-asr-smoke.jsonl --out-dir eval/asr_streaming/results/glm-asr-nano-smoke-20260622-104743`
  Result: pass.
- Full run command: `.venv-glm-asr/bin/python eval/asr_streaming/run_eval.py run --adapter glm-asr-local --model-id glm-asr-nano-2512 --glm-asr-model .external/models/GLM-ASR-Nano-2512 --glm-asr-device cpu --glm-asr-dtype auto --glm-asr-local-files-only --cases eval/asr_streaming/cases.local.jsonl --out-dir eval/asr_streaming/results/glm-asr-nano-full-20260622-104840`
  Result: pass.
- Output directory: `eval/asr_streaming/results/glm-asr-nano-full-20260622-104840`.

### Aggregate comparison

| Model | Mean CER | Mean WER | Mean RTF | Mean final latency |
|---|---:|---:|---:|---:|
| Fun-ASR-Nano | `0.0758` | `0.2236` | `0.2080` | `3962 ms` |
| Qwen3-ASR 0.6B | `0.0470` | `0.1918` | `0.1264` | `3291 ms` |
| Qwen3-ASR 1.7B | `0.0431` | `0.1760` | `0.1849` | `5065 ms` |
| GLM-ASR-Nano | `0.0818` | `0.2813` | `0.2465` | `5638 ms` |

Metric meanings:

- CER: character error rate, lower is better. It is the character-level edit distance divided by the reference character count, useful for Chinese transcription accuracy.
- WER: word or token error rate, lower is better. In this harness Chinese is approximated by single-character tokens while English/numbers/symbol spans are grouped, so it is useful for mixed Chinese-English and technical-token errors.
- RTF: realtime factor, lower is better. `0.25` means the file-level run took about one quarter of the audio duration; below `1` is faster than realtime.
- Mean final latency: the elapsed time for file-level final output in this adapter path. It is not yet streaming UI latency.

### Interpretation

- GLM-ASR-Nano is runnable locally and passes the full 10-case file-level harness.
- It underperforms both Qwen3-ASR variants on this local set:
  - Mean CER is `0.0818`, worse than Fun-ASR-Nano `0.0758`, Qwen3-ASR 0.6B `0.0470`, and Qwen3-ASR 1.7B `0.0431`.
  - Mean WER is `0.2813`, the weakest among the four compared runs.
  - Mean RTF is `0.2465`, also slower than the Qwen file-level CPU paths.
- The weakest cases were:
  - `zh_numbers_001`: `CER=0.3600`, including numeric formatting changes and the recurring `语音输入` -> `云输入` error.
  - `mix_tech_001`: `CER=0.1818`, `WER=0.8462`, with poor handling of model names and ASR abbreviations.
  - `long_code_switch_001`: `CER=0.1253`, `WER=0.6852`, with traditional Chinese output and degraded technical/product terms.
- GLM-ASR-Nano should stay documented as runnable but should not be the next default app backend unless later streaming/runtime evidence changes the ranking.

### Follow-up

- Keep Qwen3-ASR 0.6B and 1.7B ahead of GLM-ASR-Nano in the current shortlist.
- Continue with FireRedASR2-AED once the remote download completes, then MiMo-V2.5-ASR-MLX plus MiMo-Audio-Tokenizer.
- Do not integrate GLM-ASR-Nano into the macOS app runtime from this evidence alone.

### Files changed

- `eval/asr_streaming/run_eval.py`: added the `glm-asr-local` file-level adapter and GLM-specific CLI options.
- `eval/asr_streaming/model_registry.json`: marked GLM-ASR-Nano as locally validated on the 10-case CPU file-level run.
- `specs/2026-06-22-glm-asr-local-eval/*`: recorded feature metadata, plan, requirements, validation, and decisions.
- `specs/feature_matrix.json`: marked the GLM local evaluation feature as `validated` with `passes=true`.
- `specs/progress.md`: recorded validation evidence and comparison metrics.

### Blockers / open questions

- GLM-ASR-Nano realtime streaming and partial-output behavior remains unvalidated.
- GLM-ASR-Nano should not be integrated into the app runtime based on this file-level evidence, because it is weaker than both Qwen3-ASR variants on the current local cases.

### Next recommended action

- Wait for FireRedASR2-AED to finish downloading on the 2015 MacBook Pro, sync it locally, and run the same smoke plus full 10-case file-level harness.

## 2026-06-22 — FireRedASR2-AED local sync and full 10-case CPU run passed

### Summary

- Synced `FireRedTeam/FireRedASR2-AED` from the 2015 MacBook Pro cache to `.external/models/FireRedASR2-AED`.
- Synced official `FireRedASR2S` source to `.external/repos/FireRedASR2S`.
- Created a separate `.venv-firered` runtime that reuses the existing macOS torch stack and installs missing dependencies: `kaldi_native_fbank==1.22.3`, `cn2an==0.5.23`, and `textgrid==1.6.1`.
- Added a local file-level `firered-asr2-aed-local` adapter to the independent eval harness.
- Ran a one-case smoke test and then the full 10-case local WAV set.
- All 10 full-run cases completed with `status=ok`.
- This remains file-level screening evidence only. It does not validate realtime partial behavior, floating-panel latency, or macOS app insertion behavior.

### Validation

- Sync command: `rsync -aP --partial --stats mbp2015-easytier:'$HOME/LocalVoiceInputModels/hf/FireRedTeam__FireRedASR2-AED/' .external/models/FireRedASR2-AED/`
  Result: pass.
- Local model directory: `.external/models/FireRedASR2-AED`, with `model.pth.tar` about `4.73GB`.
- Official source sync: remote GitHub ZIP download on `mbp2015-easytier`, then `rsync` to `.external/repos/FireRedASR2S`.
  Result: pass.
- Runtime smoke command: official `speech2text.py` with `--use_gpu 0` on `zh_short_001.wav`.
  Result: pass; output `我想要做一个本地离线的中文云输入工具`, internal RTF `0.4165`.
- Harness smoke command: `.venv-firered/bin/python eval/asr_streaming/run_eval.py run --adapter firered-asr2-aed-local --model-id firered-asr2s --firered-model .external/models/FireRedASR2-AED --firered-source .external/repos/FireRedASR2S --firered-beam-size 3 --firered-decode-max-len 300 --cases /tmp/localvoiceinput-firered-smoke.jsonl --out-dir eval/asr_streaming/results/firered-asr2-aed-smoke-20260622-110840`
  Result: pass.
- Full run command: `.venv-firered/bin/python eval/asr_streaming/run_eval.py run --adapter firered-asr2-aed-local --model-id firered-asr2s --firered-model .external/models/FireRedASR2-AED --firered-source .external/repos/FireRedASR2S --firered-beam-size 3 --firered-decode-max-len 300 --cases eval/asr_streaming/cases.local.jsonl --out-dir eval/asr_streaming/results/firered-asr2-aed-full-20260622-110901`
  Result: pass.
- Output directory: `eval/asr_streaming/results/firered-asr2-aed-full-20260622-110901`.

### Aggregate comparison

| Model | Mean CER | Mean WER | Mean RTF | Mean final latency |
|---|---:|---:|---:|---:|
| Fun-ASR-Nano | `0.0758` | `0.2236` | `0.2080` | `3962 ms` |
| Qwen3-ASR 0.6B | `0.0470` | `0.1918` | `0.1264` | `3291 ms` |
| Qwen3-ASR 1.7B | `0.0431` | `0.1760` | `0.1849` | `5065 ms` |
| GLM-ASR-Nano | `0.0818` | `0.2813` | `0.2465` | `5638 ms` |
| FireRedASR2-AED | `0.0666` | `0.1978` | `0.8755` | `32925 ms` |

Metric meanings:

- CER: character error rate, lower is better. It is the character-level edit distance divided by the reference character count, useful for Chinese transcription accuracy.
- WER: word or token error rate, lower is better. In this harness Chinese is approximated by single-character tokens while English/numbers/symbol spans are grouped, so it is useful for mixed Chinese-English and technical-token errors.
- RTF: realtime factor, lower is better. `0.88` means the file-level run took about 88% of the audio duration on average; above `1` is slower than realtime.
- Mean final latency: the elapsed time for file-level final output in this adapter path. It is not yet streaming UI latency.

### Interpretation

- FireRedASR2-AED is runnable locally on CPU and passes the full 10-case file-level harness.
- It is better than GLM-ASR-Nano on aggregate CER/WER in this local set, but worse than both Qwen3-ASR variants.
- Its largest weakness for the MVP is latency:
  - Mean RTF: `0.8755`, much slower than Qwen3-ASR 0.6B `0.1264` and Qwen3-ASR 1.7B `0.1849`.
  - `long_200_001`: RTF `1.0788`, slower than realtime.
  - `long_400_001`: RTF `1.6750`, final latency `136179 ms`.
- Weak accuracy cases:
  - `mix_tech_001`: `CER=0.2121`, `WER=0.4615`; technical model names degrade to forms such as `foundasr` and `千问三杠 asr`.
  - `zh_numbers_001`: `CER=0.1600`; still includes `语音输入` -> `云输入` and `规整` -> `归整`.
  - `long_400_001`: `CER=0.1296`, including dropped clause content and technical-term degradation.
- FireRedASR2-AED should stay documented as runnable but should not outrank Qwen3-ASR for the current MacBook Pro M4 MVP unless an optimized non-CPU runtime path is proven.

### Files changed

- `eval/asr_streaming/run_eval.py`: added the `firered-asr2-aed-local` file-level adapter and FireRed-specific CLI options.
- `eval/asr_streaming/model_registry.json`: marked FireRedASR2-AED as locally validated on the 10-case CPU file-level run.
- `specs/2026-06-22-firered-asr2-aed-local-eval/*`: recorded feature metadata, plan, requirements, validation, and decisions.
- `specs/feature_matrix.json`: marked the FireRed local evaluation feature as `validated` with `passes=true`.
- `specs/progress.md`: recorded validation evidence and comparison metrics.

### Blockers / open questions

- FireRedASR2-AED realtime streaming and partial-output behavior remains unvalidated.
- FireRedASR2-AED CPU long-form latency is currently too high for the target MVP interaction.
- A future MPS or optimized serving path could be investigated, but it is not the best next integration path based on current evidence.

### Next recommended action

- Keep Qwen3-ASR 0.6B and 1.7B at the top of the current shortlist.
- Let the remote MiMo-V2.5-ASR-MLX plus tokenizer downloads continue, then run the same local file-level harness if the MLX runtime can be wired safely.
## 2026-06-22 — MiMo-V2.5-ASR MLX local evaluation adapter

### Summary

- Synced `mlx-community/MiMo-V2.5-ASR-MLX` and `mlx-community/MiMo-Audio-Tokenizer` from the 2015 MacBook Pro cache to local `.external/models/`.
- Installed an isolated `.venv-mimo` runtime with MLX and local `mlx-audio[stt]`.
- Added a `mimo-asr-mlx-local` file-level adapter to the independent ASR eval harness.
- Ran official helper smoke, harness smoke, and the full 10-case local WAV evaluation.
- Kept this work isolated from the macOS app runtime, hotkeys, focus detection, clipboard, paste engine, and floating panel.

### Files changed

- `eval/asr_streaming/run_eval.py`
- `eval/asr_streaming/model_registry.json`
- `specs/feature_matrix.json`
- `specs/progress.md`
- `specs/2026-06-22-mimo-v25-asr-mlx-local-eval/*`

### Validation

- Command: `.venv-mimo/bin/python .external/repos/MiMo-V2.5-ASR-MLX/run_mimo_asr_mlx.py --model .external/models/MiMo-V2.5-ASR-MLX --audio-tokenizer-dir .external/models/MiMo-Audio-Tokenizer --audio eval/asr_streaming/audio/zh_short_001.wav --language zh`
  Result: pass
  Notes: Official helper script returned `我想要做一个本地离线的中文语音输入工具。`; cold command wall time was about 60.5s and peak memory footprint was about 9.17GB.
- Command: `.venv-mimo/bin/python -m py_compile eval/asr_streaming/run_eval.py`
  Result: pass
  Notes: Eval runner compiles in the MiMo runtime.
- Command: `python3 -m json.tool eval/asr_streaming/model_registry.json >/dev/null`
  Result: pass
  Notes: Model registry JSON is valid.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null`
  Result: pass
  Notes: Feature matrix JSON is valid.
- Command: `python3 -m json.tool specs/2026-06-22-mimo-v25-asr-mlx-local-eval/feature.json >/dev/null`
  Result: pass
  Notes: MiMo feature metadata JSON is valid.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Existing eval harness schema and transcript aggregation checks pass.
- Command: `.venv-mimo/bin/python eval/asr_streaming/run_eval.py run --adapter mimo-asr-mlx-local --model-id mimo-v2.5-asr --mimo-model .external/models/MiMo-V2.5-ASR-MLX --mimo-audio-tokenizer-dir .external/models/MiMo-Audio-Tokenizer --mimo-language zh --cases /tmp/localvoiceinput-mimo-smoke.jsonl --out-dir eval/asr_streaming/results/mimo-v25-asr-mlx-smoke-20260622-114713`
  Result: pass
  Notes: Smoke case `zh_short_001` passed with CER 0.0, WER 0.0, RTF 0.2339, final latency about 1472ms.
- Command: `.venv-mimo/bin/python eval/asr_streaming/run_eval.py run --adapter mimo-asr-mlx-local --model-id mimo-v2.5-asr --mimo-model .external/models/MiMo-V2.5-ASR-MLX --mimo-audio-tokenizer-dir .external/models/MiMo-Audio-Tokenizer --mimo-language zh --cases eval/asr_streaming/cases.local.jsonl --out-dir eval/asr_streaming/results/mimo-v25-asr-mlx-full-20260622-114759`
  Result: pass
  Notes: Full 10-case run completed with 10/10 ok. Mean CER 0.0311, mean WER 0.1613, mean RTF 0.1214, mean final latency 3217ms. Peak memory footprint for the command was about 28.1GB.

### Result snapshot

| Case | CER | WER | RTF | Notes |
|---|---:|---:|---:|---|
| `zh_short_001` | 0.0000 | 0.0000 | 0.1843 | Exact match |
| `mix_tech_001` | 0.1515 | 0.5385 | 0.1249 | `Qwen3-ASR` became `千问三杠 ASR` |
| `hotword_001` | 0.0159 | 0.7500 | 0.0957 | `PasteEngine` became `Haste Engine` |
| `punctuation_001` | 0.0000 | 0.0000 | 0.1158 | Exact match |
| `zh_numbers_001` | 0.0800 | 0.0800 | 0.0991 | `语音输入` became `云输入` |
| `safety_001` | 0.0000 | 0.0000 | 0.1229 | Exact match |
| `long_120_001` | 0.0082 | 0.0082 | 0.1171 | `本机` became `手机` |
| `long_200_001` | 0.0000 | 0.0000 | 0.1145 | Exact match |
| `long_400_001` | 0.0370 | 0.0513 | 0.1245 | Project/model names degraded |
| `long_code_switch_001` | 0.0187 | 0.1852 | 0.1152 | Mixed English casing and model names degraded |

### Findings

- MiMo-V2.5-ASR MLX is the strongest file-level candidate so far on the 10 local WAV set by mean CER, mean WER, and mean RTF.
- It is especially strong on long Chinese dictation and produces complete file-level finals without the FunASR offline-segment truncation issue.
- It still makes important product-name and model-name errors in code-switch/hotword scenarios, so hotword/context correction remains relevant.
- Current evidence does not prove realtime partial support; app runtime integration should wait until a streaming or chunked path is investigated.

### Blockers / open questions

- Need to determine whether MiMo/MLX can provide practical realtime partials for floating-panel display.
- Need to decide whether MiMo's 8B MLX runtime memory footprint is acceptable compared with Qwen3-ASR 0.6B and 1.7B.

### Next recommended action

- Compare MiMo against Qwen3-ASR 0.6B/1.7B on app-runtime feasibility: realtime partials, serving architecture, memory footprint, startup time, and hotword/context handling.

## 2026-06-22 — ASR runtime feasibility comparison

### Summary

- Compared Qwen3-ASR 0.6B, Qwen3-ASR 1.7B, and MiMo-V2.5-ASR MLX for runtime feasibility before any macOS app integration.
- Added `eval/asr_streaming/runtime_feasibility.md` as the comparison artifact.
- Kept this investigation separate from Swift app runtime code, hotkeys, focus detection, clipboard, paste engine, and floating panel behavior.

### Files inspected

- `.external/models/Qwen3-ASR-0.6B/README.md`
- `.external/models/Qwen3-ASR-1.7B/README.md`
- `.venv/lib/python3.11/site-packages/qwen_asr/inference/qwen3_asr.py`
- `.venv/lib/python3.11/site-packages/qwen_asr/cli/demo_streaming.py`
- `.external/repos/mlx-audio/mlx_audio/stt/models/qwen3_asr/README.md`
- `.external/repos/mlx-audio/mlx_audio/stt/models/qwen3_asr/qwen3_asr.py`
- `.external/repos/mlx-audio/mlx_audio/stt/models/mimo_v2_asr/README.md`
- `.external/repos/mlx-audio/mlx_audio/stt/models/mimo_v2_asr/asr.py`
- `.external/repos/MiMo-V2.5-ASR-MLX/run_mimo_asr_mlx.py`
- `eval/asr_streaming/model_registry.json`
- Existing result summaries under `eval/asr_streaming/results/`

### Result directories reused

- `eval/asr_streaming/results/qwen3-asr-0.6b-full-20260622-100827`
- `eval/asr_streaming/results/qwen3-asr-1.7b-full-20260622-102709`
- `eval/asr_streaming/results/mimo-v25-asr-mlx-full-20260622-114759`

### Validation

- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null`
  Result: pass
  Notes: Feature matrix JSON is valid after marking this feature validated.
- Command: `python3 -m json.tool specs/2026-06-22-asr-runtime-feasibility-comparison/feature.json >/dev/null`
  Result: pass
  Notes: Runtime feasibility feature metadata JSON is valid.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Existing eval harness schema and transcript aggregation checks pass.

### Runtime findings

- MiMo-V2.5-ASR MLX remains the strongest file-level candidate:
  - Mean CER `0.0311`
  - Mean WER `0.1613`
  - Mean RTF `0.1214`
  - Mean final latency `3217 ms`
- MiMo is not selected as the realtime app backend because the inspected MLX class only exposes `generate(...)`; it has no `stream_transcribe`, `stream_generate`, or `generate_streaming` method.
- Official Qwen3-ASR exposes streaming methods, but local source requires `backend="vllm"` for streaming and the current `.venv` does not have `vllm` installed.
- Official Qwen3-ASR README's vLLM installation path targets CUDA nightly wheels, so MacBook Pro M4 local feasibility is unproven.
- `mlx-audio` includes a Qwen3-ASR MLX implementation with `generate(..., stream=True)` and `stream_transcribe(...)`, plus documented 0.6B/1.7B 8-bit MLX models. This is the best next Mac-native runtime spike.
- Qwen3-ASR MLX streaming currently accepts a complete audio file/array and streams generated tokens; it still needs a live timed-PCM service simulation to prove microphone-style partial behavior.

### Size and memory notes

- Local model directories:
  - `.external/models/Qwen3-ASR-0.6B`: about `1.8G`
  - `.external/models/Qwen3-ASR-1.7B`: about `4.4G`
  - `.external/models/MiMo-V2.5-ASR-MLX`: about `4.2G`
  - `.external/models/MiMo-Audio-Tokenizer`: about `2.4G`
- MiMo official helper cold command on `zh_short_001`: about `60.5s` wall time and `9.17GB` peak memory footprint.
- MiMo full 10-case harness command: about `28.1GB` peak memory footprint. Treat this as command-level evidence, not steady long-running service RSS.
- Dedicated steady-state service RSS remains required for Qwen3-ASR MLX and any selected backend before app integration.

### Recommendation

- Do not integrate a new backend into the macOS app yet.
- Next implementation step: download/evaluate `mlx-community/Qwen3-ASR-0.6B-8bit`, then build a small local service simulation that feeds WAV files as timed PCM chunks and records partial cadence, final accuracy, model load time, steady RSS, and session cleanup behavior.
- Keep MiMo-V2.5-ASR MLX as the current file-level quality benchmark and potential final-only candidate, but not as the floating-panel realtime partial backend.

### Files changed

- `eval/asr_streaming/runtime_feasibility.md`
- `specs/2026-06-22-asr-runtime-feasibility-comparison/decisions.md`
- `specs/2026-06-22-asr-runtime-feasibility-comparison/feature.json`
- `specs/feature_matrix.json`
- `specs/progress.md`

## 2026-06-22 — MLX ASR model download and local evaluation

### Summary

- Created `specs/2026-06-22-mlx-asr-model-download-and-eval` to track the multi-model MLX download/evaluation phase.
- Probed the AMD Windows host as a download/cache transfer machine.
- Added repeatable Hugging Face snapshot download helpers:
  - `eval/asr_streaming/download_hf_snapshot_windows.ps1`
  - `eval/asr_streaming/start_hf_download_windows.ps1`
  - `eval/asr_streaming/show_hf_download_status_windows.ps1`
  - `eval/asr_streaming/download_hf_snapshot.sh`
  - `eval/asr_streaming/remote_model_acquisition.md`
- Downloaded and validated `mlx-community/Qwen3-ASR-0.6B-8bit` locally on the Mac.
- Added a generic `mlx-stt-local` adapter to the independent ASR eval harness.
- Ran smoke, full 10-case file-level eval, and a file-based token-streaming probe for Qwen3-ASR 0.6B MLX.

### AMD acquisition findings

- SSH aliases from current config:
  - `amd-local`: `192.168.0.163`
  - `amd-easytier`: `100.89.0.10`
- Host: `DESKTOP-44OENPE`
- User: `desktop-44oenpe\mac_xll`
- Free space observed:
  - `C:` about `359GB`
  - `D:` about `462GB`
  - `E:` about `783GB`
- Available remote tools: Windows `curl.exe`, PowerShell, `tar`, `certutil`, `robocopy`.
- Not available in PATH: Python, `huggingface-cli`, `hf`, `git`, `rsync`.
- `huggingface.co` from AMD timed out on API and resolve URLs.
- `hf-mirror.com` from AMD was reachable, but observed large-file throughput was only tens of KB/s in the tested SSH-run path.
- Windows `Start-Process`, `cmd /c start`, `schtasks`, and BITS did not provide a reliable unattended download path under the current SSH/non-interactive session. BITS returned `0x800704DD`.
- Decision for this run: keep AMD scripts and notes as fallback tooling, but use Mac-local download for the first model because it was materially faster and reliable.

### Qwen3-ASR 0.6B MLX download validation

- Command:

```bash
bash eval/asr_streaming/download_hf_snapshot.sh \
  --repo mlx-community/Qwen3-ASR-0.6B-8bit \
  --base-url https://huggingface.co \
  --dest-root .external/models
```

- Result: pass.
- Local path: `.external/models/mlx-community__Qwen3-ASR-0.6B-8bit`
- Hugging Face commit: `89e96d92ba34aca20b3e29fb10cc284097d1219f`
- Expected siblings from API: `11`
- Missing siblings after download: `0`
- `model.safetensors`: `1006229426` bytes
- Directory size: about `965M`

### Qwen3-ASR 0.6B MLX smoke

- Command:

```bash
/usr/bin/time -l .venv-mimo/bin/python eval/asr_streaming/run_eval.py run \
  --adapter mlx-stt-local \
  --model-id qwen3-asr-0.6b-mlx-8bit \
  --mlx-stt-model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit \
  --mlx-stt-language Chinese \
  --cases /tmp/localvoiceinput-qwen3-mlx-smoke.jsonl \
  --out-dir eval/asr_streaming/results/qwen3-asr-0.6b-mlx-smoke-20260622-1458
```

- Result: pass.
- Case: `zh_short_001`
- Final text: `我想要做一个本地离线的中文云输入工具。`
- CER: `0.1053`
- WER: `0.1053`
- RTF: `0.0306`
- Peak memory footprint: about `2.1GB`

### Qwen3-ASR 0.6B MLX full 10-case eval

- Command:

```bash
/usr/bin/time -l .venv-mimo/bin/python eval/asr_streaming/run_eval.py run \
  --adapter mlx-stt-local \
  --model-id qwen3-asr-0.6b-mlx-8bit \
  --mlx-stt-model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit \
  --mlx-stt-language Chinese \
  --cases eval/asr_streaming/cases.local.jsonl \
  --out-dir eval/asr_streaming/results/qwen3-asr-0.6b-mlx-full-20260622-1459
```

- Result: pass.
- Output directory: `eval/asr_streaming/results/qwen3-asr-0.6b-mlx-full-20260622-1459`
- Cases: `10/10 ok`
- Mean CER: `0.0510`
- Mean WER: `0.1898`
- Mean RTF: `0.0212`
- Mean final latency: about `532ms`
- Peak memory footprint for full command: about `3.6GB`

### Qwen3-ASR 0.6B MLX interpretation

- Accuracy is close to official Qwen3-ASR 0.6B file-level eval (`CER 0.0470`, `WER 0.1918`) and slightly worse than official Qwen3-ASR 1.7B and MiMo-V2.5-ASR MLX on this 10-case set.
- Runtime speed is much better than the previous official transformers/CPU file-level Qwen path in this harness:
  - Qwen3-ASR 0.6B MLX RTF: `0.0212`
  - Official Qwen3-ASR 0.6B file-level RTF: `0.1264`
- Weak cases remain product names, model names, and code-switching:
  - `语音输入` -> `云输入`
  - `Qwen3-ASR` -> `千问三、杠 ASR`
  - `Paraformer/Fun-ASR-Nano/MiMo` degraded in long code-switch case
  - `TranscriptBuffer` -> `Transcribed Buffer`
- `stream_transcribe(...)` emitted token chunks on a complete audio file:
  - `13` chunks on `zh_short_001`
  - first chunk observed around `136ms`
  - final chunk had `is_final=True`
- This token-streaming probe does not yet prove microphone-style timed PCM chunk sessions; that remains a runtime feasibility requirement before app integration.

### Validation commands

- `.venv-mimo/bin/python -m py_compile eval/asr_streaming/run_eval.py`
  Result: pass.
- `python3 -m json.tool eval/asr_streaming/model_registry.json >/dev/null`
  Result: pass.
- `bash eval/asr_streaming/validate.sh`
  Result: pass.

## 2026-06-22 - Qwen3-ASR 1.7B MLX local validation

### Download validation

- Command:

```bash
bash eval/asr_streaming/download_hf_snapshot.sh \
  --repo mlx-community/Qwen3-ASR-1.7B-8bit \
  --base-url https://huggingface.co \
  --dest-root .external/models
```

- Result: pass.
- Local path: `.external/models/mlx-community__Qwen3-ASR-1.7B-8bit`
- Hugging Face commit: `a8379a2e2f9e313c9292cdf1af4055ab56d50d55`
- Expected siblings from API: `11`
- Missing siblings after download: `0`
- `model.safetensors`: `2463307541` bytes
- Directory size: about `2.3G`

### Qwen3-ASR 1.7B MLX smoke

- Command:

```bash
/usr/bin/time -l .venv-mimo/bin/python eval/asr_streaming/run_eval.py run \
  --adapter mlx-stt-local \
  --model-id qwen3-asr-1.7b-mlx-8bit \
  --mlx-stt-model .external/models/mlx-community__Qwen3-ASR-1.7B-8bit \
  --mlx-stt-language Chinese \
  --cases /tmp/localvoiceinput-qwen3-1.7b-mlx-smoke.jsonl \
  --out-dir eval/asr_streaming/results/qwen3-asr-1.7b-mlx-smoke-20260622-1528
```

- Result: pass.
- Case: `zh_short_001`
- Final text: `我想要做一个本地离线的中文云输入工具。`
- CER: `0.1053`
- WER: `0.1053`
- RTF: `0.0468`
- Final latency: about `295ms`
- Maximum resident set size: about `2.67GB`
- Peak memory footprint: about `3.78GB`

### Qwen3-ASR 1.7B MLX full 10-case eval

- Command:

```bash
/usr/bin/time -l .venv-mimo/bin/python eval/asr_streaming/run_eval.py run \
  --adapter mlx-stt-local \
  --model-id qwen3-asr-1.7b-mlx-8bit \
  --mlx-stt-model .external/models/mlx-community__Qwen3-ASR-1.7B-8bit \
  --mlx-stt-language Chinese \
  --cases eval/asr_streaming/cases.local.jsonl \
  --out-dir eval/asr_streaming/results/qwen3-asr-1.7b-mlx-full-20260622-1529
```

- Result: pass.
- Output directory: `eval/asr_streaming/results/qwen3-asr-1.7b-mlx-full-20260622-1529`
- Cases: `10/10 ok`
- Mean CER: `0.0446`
- Mean WER: `0.1740`
- Mean RTF: `0.0357`
- Mean final latency: about `929ms`
- Maximum resident set size for full command: about `2.90GB`
- Peak memory footprint for full command: about `5.14GB`

### Qwen3-ASR 1.7B MLX stream probe

- Command:

```bash
/usr/bin/time -l .venv-mimo/bin/python - <<'PY'
import time
from mlx_audio.stt import load
model = load(".external/models/mlx-community__Qwen3-ASR-1.7B-8bit")
start = time.perf_counter()
chunks = list(model.stream_transcribe("eval/asr_streaming/audio/zh_short_001.wav", language="Chinese"))
print("chunk_count", len(chunks))
PY
```

- Result: pass.
- `stream_transcribe(...)` emitted token chunks on a complete audio file:
  - `13` chunks on `zh_short_001`
  - first chunk observed around `181ms`
  - final chunk observed around `286ms`
  - final chunk had `is_final=True`
- This still does not prove microphone-style timed PCM chunk sessions.

### Qwen3-ASR 1.7B MLX interpretation

- Compared with Qwen3-ASR 0.6B MLX, 1.7B MLX is more accurate on this 10-case set:
  - 0.6B MLX: `CER 0.0510`, `WER 0.1898`, `RTF 0.0212`, final latency about `532ms`
  - 1.7B MLX: `CER 0.0446`, `WER 0.1740`, `RTF 0.0357`, final latency about `929ms`
- Compared with official Qwen3-ASR 1.7B transformers file-level path, 1.7B MLX is similar in accuracy and much faster in this harness:
  - official 1.7B: `CER 0.0431`, `WER 0.1760`, `RTF 0.1849`, final latency about `5065ms`
  - MLX 1.7B: `CER 0.0446`, `WER 0.1740`, `RTF 0.0357`, final latency about `929ms`
- MiMo-V2.5-ASR MLX still has the best file-level accuracy among current validated runs (`CER 0.0311`, `WER 0.1613`), but its RTF and latency are materially slower than Qwen3-ASR MLX 1.7B.
- Weak cases remain `语音输入` -> `云输入`, product/model spelling, and code-switching model names such as `Paraformer`, `Fun-ASR-Nano`, `Qwen3-ASR`, and `MiMo-V2.5-ASR`.

## 2026-06-22 - Nemotron 3.5 ASR streaming 0.6B MLX local validation

### Runtime setup

- Downloaded model: `mlx-community/nemotron-3.5-asr-streaming-0.6b-8bit`
- Local path: `.external/models/mlx-community__nemotron-3.5-asr-streaming-0.6b-8bit`
- Hugging Face commit: `7279359e4481b5e9e185a318bd618e429c6d86cd`
- Expected siblings from API: `6`
- Missing siblings after download: `0`
- `model.safetensors`: `755,598,923` bytes
- Directory size: about `737M`
- Runtime note: installed PyPI `mlx-audio 0.4.3` returns `Model type nemotron_asr not supported for stt`; the local `mlx-audio main` source checkout works when placed first on `PYTHONPATH`.

### Nemotron smoke

- Command:

```bash
/usr/bin/time -l env PYTHONPATH=.external/repos/mlx-audio-main-src/mlx-audio-main \
  .venv-mimo/bin/python eval/asr_streaming/run_eval.py run \
  --adapter mlx-stt-local \
  --model-id nemotron-3.5-asr-streaming-0.6b-mlx-8bit \
  --mlx-stt-model .external/models/mlx-community__nemotron-3.5-asr-streaming-0.6b-8bit \
  --mlx-stt-language zh-CN \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --out-dir eval/asr_streaming/results/nemotron-3.5-asr-streaming-0.6b-mlx-smoke-20260622-1556
```

- Result: pass.
- Case: `zh_short_001`
- Final text: `我想要做一个本地离线的中文云输入工具。`
- CER: `0.1053`
- WER: `0.1053`
- RTF: `0.0976`
- Final latency: about `614ms`
- Maximum resident set size: about `845MB`
- Peak memory footprint: about `1.37GB`

### Nemotron full 10-case eval

- Command:

```bash
/usr/bin/time -l env PYTHONPATH=.external/repos/mlx-audio-main-src/mlx-audio-main \
  .venv-mimo/bin/python eval/asr_streaming/run_eval.py run \
  --adapter mlx-stt-local \
  --model-id nemotron-3.5-asr-streaming-0.6b-mlx-8bit \
  --mlx-stt-model .external/models/mlx-community__nemotron-3.5-asr-streaming-0.6b-8bit \
  --mlx-stt-language zh-CN \
  --cases eval/asr_streaming/cases.local.jsonl \
  --out-dir eval/asr_streaming/results/nemotron-3.5-asr-streaming-0.6b-mlx-full-20260622-1557
```

- Result: completed, but quality is a risk.
- Output directory: `eval/asr_streaming/results/nemotron-3.5-asr-streaming-0.6b-mlx-full-20260622-1557`
- Cases: `9/10 ok`, `1/10 no_text`
- Mean CER: `0.3090`
- Mean WER: `0.2993`
- Mean RTF: `0.0177`
- Mean final latency: about `480ms`
- Maximum resident set size for full command: about `904MB`
- Peak memory footprint for full command: about `3.73GB`

### Nemotron stream probe

- Command:

```bash
PYTHONPATH=.external/repos/mlx-audio-main-src/mlx-audio-main \
  .venv-mimo/bin/python - <<'PY'
import time
from mlx_audio.stt import load
model = load(".external/models/mlx-community__nemotron-3.5-asr-streaming-0.6b-8bit")
start = time.perf_counter()
chunks = list(model.stream_generate("eval/asr_streaming/audio/zh_short_001.wav", language="zh-CN"))
print("chunk_count", len(chunks))
PY
```

- Result: pass.
- `stream_generate(...)` emitted `6` cumulative chunks on `zh_short_001`.
- First non-empty chunk appeared around `88ms`.
- Final chunk appeared around `222ms`.
- This proves the MLX model exposes a streaming-style cumulative output API on a complete audio file; it still does not prove microphone PCM session integration.

### Nemotron interpretation

- Strength: very small model snapshot and very fast file-level inference (`RTF 0.0177`), with a native streaming-oriented architecture and `stream_generate(...)` support.
- Weakness: local Chinese and Chinese-English technical-term quality is much worse than Qwen3-ASR MLX and MiMo on the same 10 cases:
  - `hotword_001` produced no text.
  - `zh_numbers_001` had `CER 0.4400`.
  - `long_code_switch_001` had `CER 0.6827` and only `0.36` final-to-expected character ratio.
  - It hallucinated or corrupted terms such as `Qwen3-ASR`, `MacBook Pro`, `FocusDetector`, `PasteEngine`, `LocalVoiceInput`, and `Paraformer`.
- Current recommendation: keep Nemotron as a runtime/streaming reference candidate, but do not use it as the primary LocalVoiceInput backend candidate for Chinese-first mixed English dictation.

## 2026-06-22 - Fun-ASR-Nano-2512 4bit MLX local validation

### Download validation

- Command:

```bash
bash eval/asr_streaming/download_hf_snapshot.sh \
  --repo mlx-community/Fun-ASR-Nano-2512-4bit \
  --base-url https://huggingface.co \
  --dest-root .external/models
```

- Result: pass.
- Local path: `.external/models/mlx-community__Fun-ASR-Nano-2512-4bit`
- Hugging Face commit: `2e4e29b782a444757838db2ea5cf909b8446c229`
- Expected siblings from API: `8`
- Missing siblings after download: `0`
- `model.safetensors`: `1,319,780,726` bytes
- Directory size: about `1.3G` (`1.244GiB` from downloader summary)
- Hugging Face safetensors metadata reports about `603,168,352` parameters; upstream Fun-ASR-Nano is reported as about `800M` parameters.

### Runtime setup

- The model card says the conversion uses `mlx-audio-plus` and imports `mlx_audio.stt.models.funasr.Model`.
- Installed `mlx-audio-plus==0.1.4` package body for verification, but that package did not contain `mlx_audio.stt.models.funasr`.
- Installed `mlx-audio-plus==0.1.8` package body with `--no-deps`; that package contains the FunASR loader.
- Full dependency install was intentionally stopped because pip backtracked through `gradio/fastrtc/spacy` and other non-STT dependencies.
- Working runtime command pattern:

```bash
env PYTHONPATH=.venv-mlx-audio-plus/lib/python3.12/site-packages \
  .venv-mimo/bin/python ...
```

- This exposes the `mlx-audio-plus` FunASR loader while reusing `.venv-mimo` MLX, NumPy, transformers, soundfile, scipy, safetensors, and tokenizers dependencies.
- Added a small `mlx-stt-local` loader fallback: when `config.json` has `model_type=funasr` and generic `mlx_audio.stt.load` is unavailable or unsupported, use `mlx_audio.stt.models.funasr.Model.from_pretrained(...)`.

### Fun-ASR-Nano 4bit MLX smoke

- Command:

```bash
/usr/bin/time -l env PYTHONPATH=.venv-mlx-audio-plus/lib/python3.12/site-packages \
  .venv-mimo/bin/python eval/asr_streaming/run_eval.py run \
  --adapter mlx-stt-local \
  --model-id fun-asr-nano-2512-mlx-4bit \
  --mlx-stt-model .external/models/mlx-community__Fun-ASR-Nano-2512-4bit \
  --mlx-stt-language zh \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --out-dir eval/asr_streaming/results/fun-asr-nano-2512-mlx-4bit-smoke-20260622-1635
```

- Result: pass.
- Case: `zh_short_001`
- Final text: `我想要做一个本地离线的中文云输入工具。`
- CER: `0.1053`
- WER: `0.1053`
- RTF: `0.0947`
- Final latency: about `596ms`
- Maximum resident set size: about `1.62GB`
- Peak memory footprint: about `2.99GB`

### Fun-ASR-Nano 4bit MLX full 10-case eval

- Command:

```bash
/usr/bin/time -l env PYTHONPATH=.venv-mlx-audio-plus/lib/python3.12/site-packages \
  .venv-mimo/bin/python eval/asr_streaming/run_eval.py run \
  --adapter mlx-stt-local \
  --model-id fun-asr-nano-2512-mlx-4bit \
  --mlx-stt-model .external/models/mlx-community__Fun-ASR-Nano-2512-4bit \
  --mlx-stt-language zh \
  --cases eval/asr_streaming/cases.local.jsonl \
  --out-dir eval/asr_streaming/results/fun-asr-nano-2512-mlx-4bit-full-20260622-1636
```

- Result: completed, but quality is a major risk.
- Output directory: `eval/asr_streaming/results/fun-asr-nano-2512-mlx-4bit-full-20260622-1636`
- Cases: `10/10 ok`
- Mean CER: `0.3156`
- Mean WER: `0.4378`
- Mean RTF: `0.0566`
- Mean final latency: about `2425ms`
- Maximum resident set size for full command: about `1.66GB`
- Peak memory footprint for full command: about `37.1GB`

### Fun-ASR-Nano 4bit MLX stream probe

- Command:

```bash
env PYTHONPATH=.venv-mlx-audio-plus/lib/python3.12/site-packages \
  .venv-mimo/bin/python - <<'PY'
import time
from mlx_audio.stt.models.funasr import Model
model = Model.from_pretrained(".external/models/mlx-community__Fun-ASR-Nano-2512-4bit")
start = time.perf_counter()
chunks = list(model.generate("eval/asr_streaming/audio/zh_short_001.wav", language="zh", stream=True))
print("chunk_count", len(chunks))
PY
```

- Result: pass.
- `generate(..., stream=True)` emitted `12` token chunks on `zh_short_001`.
- First chunk appeared around `289ms`.
- Final chunk appeared around `416ms`.
- This proves file-based token streaming exists; it does not prove microphone PCM session integration.

### Fun-ASR-Nano 4bit MLX interpretation

- Strength: file-level token streaming works, short Chinese and some medium Chinese cases are acceptable, and the model is smaller than full upstream Fun-ASR-Nano.
- Weakness: long-form reliability is not acceptable for LocalVoiceInput:
  - `long_400_001` degenerated into a long repetition of `是`, with `CER 1.3889`, `WER 1.6484`, and final latency about `17.1s`.
  - `long_code_switch_001` collapsed to `不问。`, with `CER 0.9973`, `WER 0.9907`, and final-to-expected character ratio `0.0053`.
  - Technical model/product names still degrade: `FunASR` -> `放ASR`, `Qwen3` -> `千问三`, and English component names are spaced or normalized.
- Current recommendation: do not use this 4bit MLX conversion as the primary backend. Keep it only as a reference for MLX FunASR loader behavior and token streaming.

## 2026-06-22 - MLX candidate comparison artifact

- Added comparison artifact: `eval/asr_streaming/results/mlx_candidate_comparison_20260622.md`
- Models compared in the table:
  - Fun-ASR-Nano official file-level adapter
  - Qwen3-ASR 0.6B official local adapter
  - Qwen3-ASR 1.7B official local adapter
  - MiMo-V2.5-ASR MLX
  - Qwen3-ASR 0.6B MLX 8bit
  - Qwen3-ASR 1.7B MLX 8bit
  - Nemotron 3.5 ASR streaming 0.6B MLX 8bit
  - Fun-ASR-Nano-2512 4bit MLX
- Current recommendation in the artifact:
  - Primary next backend-integration spike: `mlx-community/Qwen3-ASR-1.7B-8bit`
  - Fallback candidate: `mlx-community/Qwen3-ASR-0.6B-8bit`
  - Accuracy-only reference: `MiMo-V2.5-ASR MLX`
  - Not recommended as primary backend: Nemotron 3.5 ASR 0.6B MLX 8bit and Fun-ASR-Nano-2512 4bit MLX
- Remaining runtime caveat: file-level/token-streaming probes still do not prove microphone PCM chunk session behavior inside `LocalVoiceInputMac`.

## 2026-06-22 - AMD transfer validation for Qwen3-ASR 0.6B MLX

### AMD host and network result

- SSH aliases verified:
  - `amd-easytier` -> `DESKTOP-44OENPE`
  - `amd-local` -> `DESKTOP-44OENPE`
- Remote cache root: `E:\LocalVoiceInputModels\hf`
- Remote helper scripts copied to `E:\LocalVoiceInputModels\bin`
- Free space at probe time:
  - `C:` about `359GB` free
  - `D:` about `462GB` free
  - `E:` about `783GB` free
- AMD direct Hugging Face API probe:

```bash
ssh amd-easytier 'powershell -NoProfile -Command "curl.exe -L --fail --connect-timeout 10 --max-time 25 -o NUL https://huggingface.co/api/models/mlx-community/Qwen3-ASR-0.6B-8bit/revision/main; Write-Output \"exit=$LASTEXITCODE\""'
```

- Result: failed with `curl: (28) Connection timed out after 10008 milliseconds`, `exit=28`.
- AMD `hf-mirror.com` API probe:

```bash
ssh amd-easytier 'powershell -NoProfile -Command "curl.exe -L --fail --connect-timeout 10 --max-time 25 -o NUL https://hf-mirror.com/api/models/mlx-community/Qwen3-ASR-0.6B-8bit/revision/main; Write-Output \"exit=$LASTEXITCODE\""'
```

- Result: pass, `exit=0`, but API response was slow.

### AMD download command

Detached helper startup still did not produce a durable download immediately:

```bash
ssh amd-easytier 'powershell -NoProfile -ExecutionPolicy Bypass -File E:\LocalVoiceInputModels\bin\start_hf_download_windows.ps1 -RepoId mlx-community/Qwen3-ASR-0.6B-8bit -BaseUrl https://hf-mirror.com'
ssh amd-easytier 'powershell -NoProfile -ExecutionPolicy Bypass -File E:\LocalVoiceInputModels\bin\show_hf_download_status_windows.ps1 -RepoId mlx-community/Qwen3-ASR-0.6B-8bit -Tail 30'
```

- Result: `process=not_found`, `files=0`, `bytes=0`.

The validated path was a foreground PowerShell snapshot command over SSH:

```bash
ssh amd-easytier 'powershell -NoProfile -ExecutionPolicy Bypass -File E:\LocalVoiceInputModels\bin\download_hf_snapshot_windows.ps1 -RepoId mlx-community/Qwen3-ASR-0.6B-8bit -BaseUrl https://hf-mirror.com'
```

- Result: completed.
- Remote path: `E:\LocalVoiceInputModels\hf\mlx-community__Qwen3-ASR-0.6B-8bit`
- Remote integrity check:
  - expected files from `_snapshot_info.json`: `11`
  - existing files: `11`
  - missing files: `0`
  - total remote bytes: `1,010,776,472`
  - `model.safetensors`: `1,006,229,426` bytes

### Mac sync and validation

- Sync command:

```bash
mkdir -p .external/models/amd-transfer__Qwen3-ASR-0.6B-8bit
scp -r amd-easytier:E:/LocalVoiceInputModels/hf/mlx-community__Qwen3-ASR-0.6B-8bit/. .external/models/amd-transfer__Qwen3-ASR-0.6B-8bit/
```

- Mac proof path: `.external/models/amd-transfer__Qwen3-ASR-0.6B-8bit`
- Mac integrity check:
  - expected files from `_snapshot_info.json`: `11`
  - existing files: `11`
  - missing files: `0`
  - total local bytes: `1,010,776,472`
  - directory size: about `965M`

Smoke command from the AMD-transferred directory:

```bash
/usr/bin/time -l .venv-mimo/bin/python eval/asr_streaming/run_eval.py run \
  --adapter mlx-stt-local \
  --model-id qwen3-asr-0.6b-mlx-8bit \
  --mlx-stt-model .external/models/amd-transfer__Qwen3-ASR-0.6B-8bit \
  --mlx-stt-language Chinese \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --out-dir eval/asr_streaming/results/qwen3-asr-0.6b-mlx-amd-transfer-smoke-20260622
```

- Result: pass.
- Case: `zh_short_001`
- Final text: `我想要做一个本地离线的中文云输入工具。`
- CER: `0.1053`
- WER: `0.1053`
- RTF: `0.0286`
- Final latency: about `180ms`
- Maximum resident set size: about `1.21GB`
- Peak memory footprint: about `2.11GB`

### Interpretation

- AMD can now satisfy the acquisition/transfer requirement for at least the first required candidate model when using `hf-mirror.com` and a foreground PowerShell snapshot command.
- Detached Windows background startup remains unreliable and should not be used as the primary unattended acquisition method without a separate fix.
- Mac-local evaluation remains authoritative; the AMD-transferred snapshot was only used to verify the download/cache/sync chain and a one-case Mac smoke from the transferred directory.

## 2026-06-22 - 2026-06-22-mlx-asr-model-download-and-eval closeout

### Summary

- Completed the required MLX candidate comparison without changing `LocalVoiceInputMac` Swift runtime behavior.
- Recorded metadata for each required candidate and support artifact in `eval/asr_streaming/model_registry.json`, including supplier/vendor, Chinese supplier name, release timing, parameter scale, model size, source/runtime notes, and local validation status.
- Validated AMD as a download/cache transfer host for `mlx-community/Qwen3-ASR-0.6B-8bit` through `hf-mirror.com`, then synced that snapshot back to the Mac and smoke-tested from the transferred directory.
- Compared runnable candidates on the same 10 local WAV cases from `eval/asr_streaming/cases.local.jsonl`.
- Final recommendation: primary next backend integration spike is `mlx-community/Qwen3-ASR-1.7B-8bit`; fallback is `mlx-community/Qwen3-ASR-0.6B-8bit`; `MiMo-V2.5-ASR MLX` remains the accuracy-only offline reference.

### Files changed

- `eval/asr_streaming/model_registry.json`
- `eval/asr_streaming/remote_model_acquisition.md`
- `eval/asr_streaming/results/mlx_candidate_comparison_20260622.md`
- `specs/2026-06-22-mlx-asr-model-download-and-eval/decisions.md`
- `specs/2026-06-22-mlx-asr-model-download-and-eval/feature.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m json.tool eval/asr_streaming/model_registry.json`
  Result: pass.
  Notes: model registry remains valid JSON after adding AMD transfer and MiMo tokenizer metadata.
- Command: `python3 -m json.tool specs/feature_matrix.json`
  Result: pass.
  Notes: feature matrix was valid before closeout status update.
- Command: `python3 -m json.tool specs/2026-06-22-mlx-asr-model-download-and-eval/feature.json`
  Result: pass.
  Notes: feature metadata and follow-up candidates are valid JSON.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass.
  Notes: validated 5 example cases, transcript self-test passed, ASR streaming eval harness validation passed.
- Command: `.venv-mimo/bin/python eval/asr_streaming/run_eval.py run --adapter mlx-stt-local --model-id qwen3-asr-0.6b-mlx-8bit --mlx-stt-model .external/models/amd-transfer__Qwen3-ASR-0.6B-8bit --mlx-stt-language Chinese --cases eval/asr_streaming/cases.smoke.local.jsonl --out-dir eval/asr_streaming/results/qwen3-asr-0.6b-mlx-amd-transfer-smoke-20260622`
  Result: pass.
  Notes: Mac smoke from AMD-transferred snapshot returned status `ok`, CER `0.1053`, WER `0.1053`, RTF `0.0286`.

### Acceptance audit

- A1: pass. AMD host, remote cache path, Mac proof path, and `scp` sync method are documented in `eval/asr_streaming/remote_model_acquisition.md` and this progress file.
- A2: pass. Required candidates and the MiMo tokenizer support artifact have metadata in `eval/asr_streaming/model_registry.json`; failed/quality-risk candidates include concrete status and validation notes.
- A3: pass. Runnable candidates have smoke evidence; the AMD-transferred Qwen3 0.6B MLX snapshot also has a dedicated smoke result.
- A4: pass. Smoke-passing runnable candidates have full 10-case result directories under `eval/asr_streaming/results/`.
- A5: pass. Summaries and comparison include CER, WER, RTF, latency, success/failure counts, and Chinese metric explanations.
- A6: pass. Runtime suitability is separated from file-level accuracy in `mlx_candidate_comparison_20260622.md`, including partial/token streaming caveats, session semantics, startup/model reuse, memory/RSS, and integration complexity.
- A7: pass. Final comparison recommends `mlx-community/Qwen3-ASR-1.7B-8bit` with `mlx-community/Qwen3-ASR-0.6B-8bit` fallback.
- A8: pass. This feature changed ASR eval/spec documentation and registry files only; no Swift/macOS app runtime files were changed.

### Blockers / open questions

- No blocker remains for this feature.
- Open follow-up: Qwen3-ASR 1.7B MLX still needs a separate realtime microphone-session integration spike before it can replace the current app ASR backend.
- Open follow-up: AMD Windows unattended background downloads remain unreliable; current validated route is a foreground PowerShell snapshot command over SSH.

### Next recommended action

- Create a separate backend integration spec for a Qwen3-ASR 1.7B MLX local realtime session prototype, explicitly covering timed PCM chunks, partial stability, cancellation, final correction, model reuse, memory after repeated sessions, and integration with the existing ASR session isolation rules.

## 2026-06-22 - Strict AMD all-candidate transfer audit follow-up

### Summary

- After closeout, the active goal was re-audited with a stricter reading of "download and sync candidate models through AMD".
- The completed AMD proof remains `mlx-community/Qwen3-ASR-0.6B-8bit`: AMD full snapshot, Mac sync, Mac smoke all passed.
- A second AMD attempt was started for the primary recommended model, `mlx-community/Qwen3-ASR-1.7B-8bit`, but it did not complete in this turn.

### Qwen3-ASR 1.7B AMD attempt

- Command:

```bash
ssh amd-easytier 'powershell -NoProfile -ExecutionPolicy Bypass -File E:\LocalVoiceInputModels\bin\download_hf_snapshot_windows.ps1 -RepoId mlx-community/Qwen3-ASR-1.7B-8bit -BaseUrl https://hf-mirror.com'
```

- Result: partial only.
- Observed behavior:
  - API and small metadata files downloaded successfully.
  - `model.safetensors` began downloading and reached about `108MB` in the foreground SSH output.
  - Observed transfer rate was roughly `1.1MB/s`, with an estimated remaining time around `30-40` minutes.
  - After interrupting the noisy foreground SSH session, the remote process still appeared alive, but the status script showed only small files on disk and no durable `model.safetensors` partial.
- Cleanup:
  - Stopped remote PIDs `12564` and `15988`.
  - Verified no remaining `download_hf_snapshot_windows.ps1` processes on AMD.

### Interpretation

- AMD is proven as a working download/cache/sync path for at least one required candidate.
- Strict "all candidates must be downloaded and synced through AMD" is not complete yet.
- The model-selection conclusion remains valid because all candidate smoke/full evaluations already ran on the Mac, but the broader active-goal wording should remain open if all-candidate AMD transfer proof is required.

## 2026-06-22 - AMD transfer validation for Qwen3-ASR 1.7B MLX

### Download script adjustment

- Updated `eval/asr_streaming/download_hf_snapshot_windows.ps1` to pass `--silent --show-error` to `curl.exe`.
- Reason: long foreground SSH downloads were flooding the terminal with progress-meter output.
- Scope: output-only change; resumable download behavior remains the same.

### AMD download command

- Resumed the AMD download with:

```bash
ssh amd-easytier 'powershell -NoProfile -ExecutionPolicy Bypass -File E:\LocalVoiceInputModels\bin\download_hf_snapshot_windows.ps1 -RepoId mlx-community/Qwen3-ASR-1.7B-8bit -BaseUrl https://hf-mirror.com'
```

- Result: completed.
- Remote path: `E:\LocalVoiceInputModels\hf\mlx-community__Qwen3-ASR-1.7B-8bit`
- Remote integrity check:
  - expected files from `_snapshot_info.json`: `11`
  - existing files: `11`
  - missing files: `0`
  - total remote bytes: `2,467,861,660`
  - `model.safetensors`: `2,463,307,541` bytes

### Mac sync and validation

- Sync command:

```bash
mkdir -p .external/models/amd-transfer__Qwen3-ASR-1.7B-8bit
scp -r amd-easytier:E:/LocalVoiceInputModels/hf/mlx-community__Qwen3-ASR-1.7B-8bit/. .external/models/amd-transfer__Qwen3-ASR-1.7B-8bit/
```

- Mac proof path: `.external/models/amd-transfer__Qwen3-ASR-1.7B-8bit`
- Mac integrity check:
  - expected files from `_snapshot_info.json`: `11`
  - existing files: `11`
  - missing files: `0`
  - total local bytes: `2,467,861,660`
  - `model.safetensors`: `2,463,307,541` bytes
  - directory size: about `2.3G`

Smoke command from the AMD-transferred directory:

```bash
/usr/bin/time -l .venv-mimo/bin/python eval/asr_streaming/run_eval.py run \
  --adapter mlx-stt-local \
  --model-id qwen3-asr-1.7b-mlx-8bit \
  --mlx-stt-model .external/models/amd-transfer__Qwen3-ASR-1.7B-8bit \
  --mlx-stt-language Chinese \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --out-dir eval/asr_streaming/results/qwen3-asr-1.7b-mlx-amd-transfer-smoke-20260622
```

- Result: pass.
- Case: `zh_short_001`
- Final text: `我想要做一个本地离线的中文云输入工具。`
- CER: `0.1053`
- WER: `0.1053`
- RTF: `0.0474`
- Final latency: about `298ms`
- Maximum resident set size: about `2.68GB`
- Peak memory footprint: about `3.79GB`

### Interpretation

- AMD transfer proof now covers both Qwen3-ASR MLX candidates:
  - `mlx-community/Qwen3-ASR-0.6B-8bit`
  - `mlx-community/Qwen3-ASR-1.7B-8bit`
- The primary recommended backend candidate now has full AMD download, Mac sync, and Mac smoke evidence.
- Remaining strict all-candidate AMD transfer proof gaps are the non-selected MLX candidates: Nemotron 3.5 ASR 0.6B MLX, Fun-ASR-Nano 2512 4bit MLX, MiMo-V2.5-ASR-MLX, and MiMo-Audio-Tokenizer.

## 2026-06-22 - AMD transfer validation for Nemotron 3.5 ASR 0.6B MLX

### AMD download command

```bash
ssh amd-easytier 'powershell -NoProfile -ExecutionPolicy Bypass -File E:\LocalVoiceInputModels\bin\download_hf_snapshot_windows.ps1 -RepoId mlx-community/nemotron-3.5-asr-streaming-0.6b-8bit -BaseUrl https://hf-mirror.com'
```

- Result: completed.
- Remote path: `E:\LocalVoiceInputModels\hf\mlx-community__nemotron-3.5-asr-streaming-0.6b-8bit`
- Remote integrity check:
  - expected files from `_snapshot_info.json`: `6`
  - existing files: `6`
  - missing files: `0`
  - total remote bytes: `756,249,995`
  - `model.safetensors`: `755,598,923` bytes

### Mac sync and validation

```bash
mkdir -p .external/models/amd-transfer__nemotron-3.5-asr-streaming-0.6b-8bit
scp -r amd-easytier:E:/LocalVoiceInputModels/hf/mlx-community__nemotron-3.5-asr-streaming-0.6b-8bit/. .external/models/amd-transfer__nemotron-3.5-asr-streaming-0.6b-8bit/
```

- Mac proof path: `.external/models/amd-transfer__nemotron-3.5-asr-streaming-0.6b-8bit`
- Mac integrity check:
  - expected files from `_snapshot_info.json`: `6`
  - existing files: `6`
  - missing files: `0`
  - total local bytes: `756,249,995`
  - `model.safetensors`: `755,598,923` bytes
  - directory size: about `737M`

Smoke command from the AMD-transferred directory:

```bash
/usr/bin/time -l env PYTHONPATH=.external/repos/mlx-audio-main-src/mlx-audio-main \
  .venv-mimo/bin/python eval/asr_streaming/run_eval.py run \
  --adapter mlx-stt-local \
  --model-id nemotron-3.5-asr-streaming-0.6b-mlx-8bit \
  --mlx-stt-model .external/models/amd-transfer__nemotron-3.5-asr-streaming-0.6b-8bit \
  --mlx-stt-language zh-CN \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --out-dir eval/asr_streaming/results/nemotron-3.5-asr-streaming-0.6b-mlx-amd-transfer-smoke-20260622
```

- Result: pass.
- Case: `zh_short_001`
- Final text: `我想要做一个本地离线的中文云输入工具。`
- CER: `0.1053`
- WER: `0.1053`
- RTF: `0.0209`
- Final latency: about `131ms`
- Maximum resident set size: about `885MB`
- Peak memory footprint: about `1.36GB`

### Interpretation

- AMD transfer proof now covers:
  - `mlx-community/Qwen3-ASR-0.6B-8bit`
  - `mlx-community/Qwen3-ASR-1.7B-8bit`
  - `mlx-community/nemotron-3.5-asr-streaming-0.6b-8bit`
- Remaining strict all-candidate AMD transfer proof gaps: `mlx-community/Fun-ASR-Nano-2512-4bit`, `mlx-community/MiMo-V2.5-ASR-MLX`, and `mlx-community/MiMo-Audio-Tokenizer`.

## 2026-06-22 - AMD transfer validation for Fun-ASR-Nano 2512 4bit MLX

### AMD download command

```bash
ssh amd-easytier 'powershell -NoProfile -ExecutionPolicy Bypass -File E:\LocalVoiceInputModels\bin\download_hf_snapshot_windows.ps1 -RepoId mlx-community/Fun-ASR-Nano-2512-4bit -BaseUrl https://hf-mirror.com'
```

- Result: completed.
- Remote path: `E:\LocalVoiceInputModels\hf\mlx-community__Fun-ASR-Nano-2512-4bit`
- Remote integrity check:
  - expected files from `_snapshot_info.json`: `8`
  - existing files: `8`
  - missing files: `0`
  - total remote bytes: `1,335,672,632`
  - `model.safetensors`: `1,319,780,726` bytes

### Mac sync and validation

```bash
mkdir -p .external/models/amd-transfer__Fun-ASR-Nano-2512-4bit
scp -r amd-easytier:E:/LocalVoiceInputModels/hf/mlx-community__Fun-ASR-Nano-2512-4bit/. .external/models/amd-transfer__Fun-ASR-Nano-2512-4bit/
```

- Mac proof path: `.external/models/amd-transfer__Fun-ASR-Nano-2512-4bit`
- Mac integrity check:
  - expected files from `_snapshot_info.json`: `8`
  - existing files: `8`
  - missing files: `0`
  - total local bytes: `1,335,672,632`
  - `model.safetensors`: `1,319,780,726` bytes
  - directory size: about `1.2G`

Smoke command from the AMD-transferred directory:

```bash
/usr/bin/time -l env PYTHONPATH=.venv-mlx-audio-plus/lib/python3.12/site-packages \
  .venv-mimo/bin/python eval/asr_streaming/run_eval.py run \
  --adapter mlx-stt-local \
  --model-id fun-asr-nano-2512-mlx-4bit \
  --mlx-stt-model .external/models/amd-transfer__Fun-ASR-Nano-2512-4bit \
  --mlx-stt-language zh \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --out-dir eval/asr_streaming/results/fun-asr-nano-2512-mlx-4bit-amd-transfer-smoke-20260622
```

- Result: pass.
- Case: `zh_short_001`
- Final text: `我想要做一个本地离线的中文云输入工具。`
- CER: `0.1053`
- WER: `0.1053`
- RTF: `0.0485`
- Final latency: about `305ms`
- Maximum resident set size: about `1.63GB`
- Peak memory footprint: about `3.21GB`

### Interpretation

- AMD transfer proof now covers:
  - `mlx-community/Qwen3-ASR-0.6B-8bit`
  - `mlx-community/Qwen3-ASR-1.7B-8bit`
  - `mlx-community/nemotron-3.5-asr-streaming-0.6b-8bit`
  - `mlx-community/Fun-ASR-Nano-2512-4bit`
- Remaining strict all-candidate AMD transfer proof gaps: `mlx-community/MiMo-V2.5-ASR-MLX` and `mlx-community/MiMo-Audio-Tokenizer`.

## 2026-06-22 - AMD transfer validation for MiMo-V2.5-ASR MLX and MiMo Audio Tokenizer

### MiMo Audio Tokenizer AMD download

```bash
ssh amd-easytier 'powershell -NoProfile -ExecutionPolicy Bypass -File E:\LocalVoiceInputModels\bin\download_hf_snapshot_windows.ps1 -RepoId mlx-community/MiMo-Audio-Tokenizer -BaseUrl https://hf-mirror.com'
```

- Result: completed after one resumable retry.
- First large-file attempt failed with `curl: (18) end of response with 1940936980 bytes missing`.
- The second run resumed from the partial `model.safetensors` and completed.
- Remote path: `E:\LocalVoiceInputModels\hf\mlx-community__MiMo-Audio-Tokenizer`
- Remote integrity check:
  - expected files from `_snapshot_info.json`: `7`
  - existing files: `7`
  - missing files: `0`
  - total remote bytes: `2,575,685,063`
  - `model.safetensors`: `2,575,648,345` bytes

### MiMo Audio Tokenizer Mac sync

```bash
mkdir -p .external/models/amd-transfer__MiMo-Audio-Tokenizer
scp -r amd-easytier:E:/LocalVoiceInputModels/hf/mlx-community__MiMo-Audio-Tokenizer/. .external/models/amd-transfer__MiMo-Audio-Tokenizer/
```

- Mac proof path: `.external/models/amd-transfer__MiMo-Audio-Tokenizer`
- Mac integrity check:
  - expected files from `_snapshot_info.json`: `7`
  - existing files: `7`
  - missing files: `0`
  - total local bytes: `2,575,685,063`
  - `model.safetensors`: `2,575,648,345` bytes
  - directory size: about `2.4G`

### MiMo-V2.5-ASR-MLX AMD download

```bash
ssh amd-easytier 'powershell -NoProfile -ExecutionPolicy Bypass -File E:\LocalVoiceInputModels\bin\download_hf_snapshot_windows.ps1 -RepoId mlx-community/MiMo-V2.5-ASR-MLX -BaseUrl https://hf-mirror.com'
```

- Result: completed after one resumable retry.
- First large-file attempt failed with `curl: (18) end of response with 2164730084 bytes missing`.
- The second run resumed from the partial `model.safetensors` and completed.
- Remote path: `E:\LocalVoiceInputModels\hf\mlx-community__MiMo-V2.5-ASR-MLX`
- Remote integrity check:
  - expected files from `_snapshot_info.json`: `15`
  - existing files: `15`
  - missing files: `0`
  - total remote bytes: `4,527,589,096`
  - `model.safetensors`: `4,511,552,749` bytes

### MiMo-V2.5-ASR-MLX Mac sync and validation

```bash
mkdir -p .external/models/amd-transfer__MiMo-V2.5-ASR-MLX
scp -r amd-easytier:E:/LocalVoiceInputModels/hf/mlx-community__MiMo-V2.5-ASR-MLX/. .external/models/amd-transfer__MiMo-V2.5-ASR-MLX/
```

- Mac proof path: `.external/models/amd-transfer__MiMo-V2.5-ASR-MLX`
- Mac integrity check:
  - expected files from `_snapshot_info.json`: `15`
  - existing files: `15`
  - missing files: `0`
  - total local bytes: `4,527,589,096`
  - `model.safetensors`: `4,511,552,749` bytes
  - directory size: about `4.2G`

Smoke command using both AMD-transferred MiMo directories:

```bash
/usr/bin/time -l .venv-mimo/bin/python eval/asr_streaming/run_eval.py run \
  --adapter mimo-asr-mlx-local \
  --model-id mimo-v2.5-asr \
  --mimo-model .external/models/amd-transfer__MiMo-V2.5-ASR-MLX \
  --mimo-audio-tokenizer-dir .external/models/amd-transfer__MiMo-Audio-Tokenizer \
  --mimo-language zh \
  --cases eval/asr_streaming/cases.smoke.local.jsonl \
  --out-dir eval/asr_streaming/results/mimo-v25-asr-mlx-amd-transfer-smoke-20260622
```

- Result: pass.
- Case: `zh_short_001`
- Final text: `我想要做一个本地离线的中文语音输入工具。`
- CER: `0.0000`
- WER: `0.0000`
- RTF: `0.2945`
- Final latency: about `1854ms`
- Maximum resident set size: about `5.54GB`
- Peak memory footprint: about `9.18GB`

### Final strict AMD proof status

- Strict AMD download/cache/sync proof now covers all required MLX candidates in `specs/2026-06-22-mlx-asr-model-download-and-eval/requirements.md`:
  - `mlx-community/Qwen3-ASR-0.6B-8bit`
  - `mlx-community/Qwen3-ASR-1.7B-8bit`
  - `mlx-community/nemotron-3.5-asr-streaming-0.6b-8bit`
  - `mlx-community/MiMo-V2.5-ASR-MLX`
  - `mlx-community/MiMo-Audio-Tokenizer`
  - `mlx-community/Fun-ASR-Nano-2512-4bit`
- `mlx-community/Mega-ASR-8bit` remains optional and was not required because the validated candidate set produced a viable recommendation.

## 2026-06-22 — Realtime ASR streaming gate

### Summary

- Added an independent realtime ASR gate so backend selection no longer mixes file-level final quality with microphone-style realtime behavior.
- The gate feeds existing 16 kHz mono int16 WAV cases as timed PCM chunks, records sent chunks, records backend events, and requires:
  - partial text before simulated user stop,
  - final/offline event after simulated user stop,
  - no late partial after final,
  - latency, RTF, and final coverage within configured thresholds.
- The first supported gate adapter is `funasr-ws`; file-level adapters remain quality screens only until they expose an equivalent push-PCM session.

### Files changed

- `eval/asr_streaming/realtime_gate.py`
- `eval/asr_streaming/README.md`
- `eval/asr_streaming/validate.sh`
- `specs/2026-06-22-realtime-streaming-gate/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/realtime_gate.py`
  Result: pass
  Notes: Realtime gate script syntax check completed.
- Command: `python3 eval/asr_streaming/realtime_gate.py self-test`
  Result: pass
  Notes: Covered passing realtime behavior, late partial rejection, and file-level final-only rejection.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null`
  Result: pass
  Notes: Feature matrix JSON is valid.
- Command: `python3 -m json.tool specs/2026-06-22-realtime-streaming-gate/feature.json >/dev/null`
  Result: pass
  Notes: New feature metadata JSON is valid.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Existing ASR harness validation plus realtime gate self-test passed.
- Command: `bash scripts/run_funasr_python_server.sh`
  Result: pass
  Notes: Local FunASR WebSocket server loaded cached Paraformer online/offline models and listened on `ws://127.0.0.1:10095`; server was stopped after smoke validation.
- Command: `.venv/bin/python eval/asr_streaming/realtime_gate.py run --adapter funasr-ws --model-id paraformer-current-funasr-ws --cases eval/asr_streaming/cases.smoke.local.jsonl --ws-url ws://127.0.0.1:10095 --chunk-ms 100 --receive-timeout-sec 8 --out-dir eval/asr_streaming/results/realtime-gate-funasr-smoke-20260622 --warn-only`
  Result: pass as an exploratory run; realtime gate status is fail for the baseline smoke case.
  Notes: Result directory `eval/asr_streaming/results/realtime-gate-funasr-smoke-20260622`.

### Smoke result snapshot

Case `zh_short_001` with 100ms realtime PCM chunks:

- `realtime_gate_passed`: false
- Fail reasons: `first_partial_too_slow`, `final_latency_too_slow`
- CER: `0.1053`
- WER: `0.1053`
- RTF: `1.4922`
- First partial latency: about `3152ms`
- Stop-to-final latency: about `2950ms`
- Partial events: `5`
- Partial events before user stop: `3`
- Final/offline events after user stop: `1`
- Final coverage ratio: `0.9474`

### Findings

- The current Paraformer/FunASR baseline is a true streaming backend, but it is too slow under the default realtime gate thresholds for first partial and final latency.
- The gate now gives a concrete contract for future model tests: Qwen3-ASR MLX or any other candidate must satisfy timed PCM input and pre-stop partial behavior, not only full-WAV transcription quality.
- No Swift/macOS app runtime files were changed.

### Next recommended action

- Implement the next backend spike as a service-session prototype against this gate: start with Qwen3-ASR MLX 0.6B/1.7B only if it can accept or emulate incremental PCM chunks without waiting for the complete WAV before producing partials.

## 2026-06-22 — Qwen3-ASR MLX realtime probe

### Summary

- Added a focused Qwen3-ASR MLX realtime probe to distinguish true session streaming from token streaming over an already materialized audio buffer.
- The probe checks loaded model methods and marks a model realtime-gate eligible only when it exposes a session-style API such as `create_streaming_session`.
- Ran the probe against both local Qwen3-ASR MLX snapshots:
  - `qwen3-asr-0.6b-mlx-8bit`
  - `qwen3-asr-1.7b-mlx-8bit`

### Files changed

- `eval/asr_streaming/qwen3_mlx_realtime_probe.py`
- `eval/asr_streaming/README.md`
- `eval/asr_streaming/validate.sh`
- `eval/asr_streaming/model_registry.json`
- `eval/asr_streaming/runtime_feasibility.md`
- `specs/2026-06-22-qwen3-mlx-realtime-probe/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/qwen3_mlx_realtime_probe.py`
  Result: pass
  Notes: Probe syntax check completed.
- Command: `python3 eval/asr_streaming/qwen3_mlx_realtime_probe.py self-test`
  Result: pass
  Notes: Covered token-stream-only rejection and session-capable acceptance.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Existing ASR harness validation plus Qwen3 MLX probe self-test passed.
- Command: `PYTHONPATH=.external/repos/mlx-audio .venv-mimo/bin/python eval/asr_streaming/qwen3_mlx_realtime_probe.py probe --model-id qwen3-asr-0.6b-mlx-8bit --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit --cases eval/asr_streaming/cases.smoke.local.jsonl --language Chinese --run-prefix-smoke --out-dir eval/asr_streaming/results/qwen3-mlx-realtime-probe-0.6b-smoke-20260622`
  Result: pass.
  Notes: Probe output directory `eval/asr_streaming/results/qwen3-mlx-realtime-probe-0.6b-smoke-20260622`.
- Command: `PYTHONPATH=.external/repos/mlx-audio .venv-mimo/bin/python eval/asr_streaming/qwen3_mlx_realtime_probe.py probe --model-id qwen3-asr-1.7b-mlx-8bit --model .external/models/mlx-community__Qwen3-ASR-1.7B-8bit --cases eval/asr_streaming/cases.smoke.local.jsonl --language Chinese --run-prefix-smoke --out-dir eval/asr_streaming/results/qwen3-mlx-realtime-probe-1.7b-smoke-20260622`
  Result: pass.
  Notes: Probe output directory `eval/asr_streaming/results/qwen3-mlx-realtime-probe-1.7b-smoke-20260622`.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null`
  Result: pass.
- Command: `python3 -m json.tool specs/2026-06-22-qwen3-mlx-realtime-probe/feature.json >/dev/null`
  Result: pass.

### Probe result snapshot

Both Qwen3-ASR MLX 0.6B and 1.7B:

- `generate`: present
- `stream_transcribe`: present
- `stream_generate`: present
- `generate_streaming`: absent
- `create_streaming_session`: absent
- `file_token_streaming.supported`: true
- `true_session_streaming.supported`: false
- `realtime_gate_eligible`: false
- Eligibility reason: `missing_session_api_for_incremental_pcm_feed_step_close`

Prefix-audio diagnostic on `zh_short_001`:

- 0.6B first prefix token: about `186ms`; prefix text: `我想要做一个。`
- 1.7B first prefix token: about `154ms`; prefix text: `我想要做一个。`
- The prefix diagnostic is explicitly not equivalent to realtime gate success because it calls the model on a materialized 2-second buffer without a persistent feed/step/close session.

### Findings

- Qwen3-ASR MLX token streaming is real, but it is token streaming over provided audio buffers, not microphone-session streaming.
- Qwen3-ASR MLX should not be selected as the current default realtime backend without building and validating a custom session wrapper.
- No Swift/macOS app runtime files were changed.

### Next recommended action

- Decide whether to invest in a custom cumulative-recompute Qwen3 MLX service wrapper, or pivot to a model/runtime that already exposes true streaming session support, such as a runtime with `create_streaming_session` semantics.

## 2026-06-22 — Qwen3-ASR MLX cumulative recompute probe

### Summary

- Added a cumulative recompute probe for Qwen3-ASR MLX that periodically reruns the model on accumulated audio prefixes and treats those outputs as simulated partials.
- The probe always reports `native_realtime_gate_eligible=false`; it measures whether a future local wrapper is worth prototyping, not whether Qwen3 MLX is already a realtime backend.
- Ran local probes against `qwen3-asr-0.6b-mlx-8bit` on smoke and `long_120_001`.

### Files changed

- `eval/asr_streaming/qwen3_mlx_cumulative_probe.py`
- `eval/asr_streaming/README.md`
- `eval/asr_streaming/validate.sh`
- `eval/asr_streaming/model_registry.json`
- `eval/asr_streaming/runtime_feasibility.md`
- `specs/2026-06-22-qwen3-mlx-cumulative-recompute-probe/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/qwen3_mlx_cumulative_probe.py`
  Result: pass
  Notes: Probe syntax check completed.
- Command: `python3 eval/asr_streaming/qwen3_mlx_cumulative_probe.py self-test`
  Result: pass
  Notes: Covered fast wrapper feasibility, slow prefix failure, empty-prefix failure, and native realtime never being set for cumulative recompute.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Existing ASR harness validation plus cumulative probe self-test passed.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null`
  Result: pass.
- Command: `python3 -m json.tool specs/2026-06-22-qwen3-mlx-cumulative-recompute-probe/feature.json >/dev/null`
  Result: pass.
- Command: `PYTHONPATH=.external/repos/mlx-audio /usr/bin/time -l .venv-mimo/bin/python eval/asr_streaming/qwen3_mlx_cumulative_probe.py run --model-id qwen3-asr-0.6b-mlx-8bit --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit --cases eval/asr_streaming/cases.smoke.local.jsonl --language Chinese --out-dir eval/asr_streaming/results/qwen3-mlx-cumulative-probe-0.6b-smoke-20260622`
  Result: pass.
  Notes: Wall time about `1.85s`; peak memory footprint about `2.13GB`; output directory `eval/asr_streaming/results/qwen3-mlx-cumulative-probe-0.6b-smoke-20260622`.
- Command: `PYTHONPATH=.external/repos/mlx-audio /usr/bin/time -l .venv-mimo/bin/python eval/asr_streaming/qwen3_mlx_cumulative_probe.py run --model-id qwen3-asr-0.6b-mlx-8bit --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit --cases eval/asr_streaming/cases.local.jsonl --case-id long_120_001 --language Chinese --max-prefixes 8 --out-dir eval/asr_streaming/results/qwen3-mlx-cumulative-probe-0.6b-long120-20260622`
  Result: pass.
  Notes: Wall time about `2.64s`; peak memory footprint about `2.84GB`; output directory `eval/asr_streaming/results/qwen3-mlx-cumulative-probe-0.6b-long120-20260622`.

### Result snapshot

Smoke `zh_short_001`:

- `custom_wrapper_viability`: `promising_smoke_only_requires_long_form_validation`
- `native_realtime_gate_eligible`: false
- First meaningful simulated partial: 2s prefix, visible at about `2086ms`
- Serial recompute RTF: `0.1065`
- Prefix rewrite rate: `0.2281`
- Final CER: `0.1053`
- Final WER: `0.1053`
- Final note: `语音` was recognized as `云`

Long `long_120_001`:

- `custom_wrapper_viability`: `promising_for_tested_long_case_not_native_realtime`
- `native_realtime_gate_eligible`: false
- First meaningful simulated partial: 1s prefix, visible at about `1106ms`
- Tested prefixes: 1s through 8s
- Serial recompute RTF: `0.1214`
- Prefix rewrite rate: `0.3158`
- Final CER: `0.0082`
- Final WER: `0.0082`
- Final note: `本机` was recognized as `手机`

### Findings

- Qwen3-ASR 0.6B MLX cumulative recompute is fast enough on these local probes to justify a future wrapper prototype.
- It still does not satisfy native realtime streaming semantics because each simulated partial reruns the model from the start of the accumulated prefix.
- No Swift/macOS app runtime files were changed.

### Next recommended action

- Either prototype a local cumulative-recompute service with scheduling, cancellation, stale-result isolation, and an equivalent timed-PCM gate, or pivot to a model/runtime that exposes native session streaming.

## 2026-06-22 — Nemotron MLX realtime surface probe

### Summary

- Verified the local `mlx-community/nemotron-3.5-asr-streaming-0.6b-8bit` runtime surface after adding a narrow in-process loader remapping shim to the reusable MLX surface probe.
- The loaded model exposes `generate` and `stream_generate`, but not `create_streaming_session`, `generate_streaming`, or `stream_transcribe`.
- Conclusion: local Nemotron MLX is not realtime-gate eligible under the current runtime, despite the model name including `streaming`.

### Files changed

- `eval/asr_streaming/qwen3_mlx_realtime_probe.py`
- `eval/asr_streaming/model_registry.json`
- `eval/asr_streaming/runtime_feasibility.md`
- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/core/current_focus.md`
- `specs/2026-06-22-nemotron-mlx-realtime-surface-probe/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Existing ASR harness validation, realtime gate self-test, Qwen3 surface probe self-test, and cumulative probe self-test passed.
- Command: `PYTHONPATH=.external/repos/mlx-audio-main-src/mlx-audio-main /usr/bin/time -l .venv-mimo/bin/python eval/asr_streaming/qwen3_mlx_realtime_probe.py probe --model-id nemotron-3.5-asr-streaming-0.6b-mlx-8bit --model .external/models/mlx-community__nemotron-3.5-asr-streaming-0.6b-8bit --mlx-audio-source .external/repos/mlx-audio-main-src/mlx-audio-main --cases eval/asr_streaming/cases.smoke.local.jsonl --language zh-CN --out-dir eval/asr_streaming/results/nemotron-mlx-realtime-surface-probe-20260622`
  Result: pass.
  Notes: Wall time about `0.95s`; peak memory footprint about `1.02GB`; output directory `eval/asr_streaming/results/nemotron-mlx-realtime-surface-probe-20260622`.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null`
  Result: pass.
- Command: `python3 -m json.tool eval/asr_streaming/model_registry.json >/dev/null`
  Result: pass.
- Command: `python3 -m json.tool specs/2026-06-22-nemotron-mlx-realtime-surface-probe/feature.json >/dev/null`
  Result: pass.

### Probe result snapshot

- `generate`: present
- `stream_generate`: present
- `stream_transcribe`: absent
- `generate_streaming`: absent
- `create_streaming_session`: absent
- `file_token_streaming.supported`: true
- `true_session_streaming.supported`: false
- `realtime_gate_eligible`: false
- Eligibility reason: `missing_session_api_for_incremental_pcm_feed_step_close`

### Findings

- Nemotron MLX has cache-aware streaming internals over provided audio, but the current local runtime does not expose the session API shape LocalVoiceInput needs.
- Existing local full-case evidence also shows quality risk on Chinese/technical-term dictation: mean CER `0.3090`, mean WER `0.2993`, mean RTF `0.0177`.
- No Swift/macOS app runtime files were changed.

### Next recommended action

- Keep Nemotron lower priority for app integration unless a true session runtime appears; prioritize Qwen3 MLX wrapper-service prototyping or another runtime with explicit incremental PCM session semantics.

## 2026-06-22 — Qwen3-ASR MLX cumulative service prototype

### Summary

- Added an in-process cumulative recompute service prototype for Qwen3-ASR MLX.
- The prototype validates the service contract shape before Swift integration: `start`, timed `push_pcm`, `partial`, `finish`, `final`, and `cancel`.
- The self-test covers old session event rejection, late partial rejection after final, and cancel producing no final.
- Runtime probes passed service gate on smoke and `long_120_001`, while still reporting `native_realtime_gate_eligible=false`.

### Files changed

- `eval/asr_streaming/qwen3_mlx_cumulative_service.py`
- `eval/asr_streaming/README.md`
- `eval/asr_streaming/validate.sh`
- `eval/asr_streaming/model_registry.json`
- `eval/asr_streaming/runtime_feasibility.md`
- `project_memory_bank/modules/asr_audio/summary.md`
- `project_memory_bank/core/current_focus.md`
- `specs/2026-06-22-qwen3-mlx-cumulative-service-prototype/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/qwen3_mlx_cumulative_service.py`
  Result: pass
  Notes: Service prototype syntax check completed.
- Command: `python3 eval/asr_streaming/qwen3_mlx_cumulative_service.py self-test`
  Result: pass
  Notes: Covered old session partial rejection, late partial after final rejection, cancel producing no final, and service gate classification.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Existing ASR harness validation plus Qwen3 cumulative service self-test passed.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null`
  Result: pass.
- Command: `python3 -m json.tool specs/2026-06-22-qwen3-mlx-cumulative-service-prototype/feature.json >/dev/null`
  Result: pass.
- Command: `PYTHONPATH=.external/repos/mlx-audio /usr/bin/time -l .venv-mimo/bin/python eval/asr_streaming/qwen3_mlx_cumulative_service.py run --model-id qwen3-asr-0.6b-mlx-8bit --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit --cases eval/asr_streaming/cases.smoke.local.jsonl --language Chinese --out-dir eval/asr_streaming/results/qwen3-mlx-cumulative-service-0.6b-smoke-20260622`
  Result: pass.
  Notes: Wall time about `2.35s`; peak memory footprint about `2.14GB`; output directory `eval/asr_streaming/results/qwen3-mlx-cumulative-service-0.6b-smoke-20260622`.
- Command: `PYTHONPATH=.external/repos/mlx-audio /usr/bin/time -l .venv-mimo/bin/python eval/asr_streaming/qwen3_mlx_cumulative_service.py run --model-id qwen3-asr-0.6b-mlx-8bit --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit --cases eval/asr_streaming/cases.local.jsonl --case-id long_120_001 --language Chinese --max-prefixes 8 --out-dir eval/asr_streaming/results/qwen3-mlx-cumulative-service-0.6b-long120-20260622`
  Result: pass.
  Notes: Wall time about `2.53s`; peak memory footprint about `2.84GB`; output directory `eval/asr_streaming/results/qwen3-mlx-cumulative-service-0.6b-long120-20260622`.

### Result snapshot

Smoke `zh_short_001`:

- `service_gate_passed`: true
- `wrapper_service_candidate`: true
- `native_realtime_gate_eligible`: false
- Stop-before partial count: `6`
- Stop-after final count: `1`
- First usable partial: about `2078ms`
- Final latency: about `137ms`
- Partial cadence: about `1002ms`
- Final CER: `0.1053`
- Final WER: `0.1053`
- Final note: `语音` was recognized as `云`

Long `long_120_001`:

- `service_gate_passed`: true
- `wrapper_service_candidate`: true
- `native_realtime_gate_eligible`: false
- Stop-before partial count: `8`
- Stop-after final count: `1`
- First usable partial: about `1092ms`
- Final latency: about `603ms`
- Partial cadence: about `1013ms`
- Final CER: `0.0082`
- Final WER: `0.0082`
- Final note: `本机` was recognized as `手机`

### Findings

- The in-process Qwen3-ASR 0.6B MLX cumulative service prototype passes the current service gate on the tested short and long cases.
- Session safety checks pass at the prototype layer: old session events are ignored, late partials after final are ignored, and cancel produces no final.
- This is still not a Swift app backend. It lacks a real local process boundary, process supervision, IPC/WebSocket behavior, Swift client behavior, and macOS runtime validation.
- No Swift/macOS app runtime files were changed.

### Follow-up candidates

- FUP-001: Add a real local service process boundary such as WebSocket, local HTTP, or stdin/stdout JSON.
- FUP-002: Probe 500ms cumulative prefix cadence.

### Next recommended action

- Create a separate spec for the real local service process boundary around the validated in-process Qwen3 cumulative wrapper contract.
## 2026-06-22 — Incremental UX ASR gate

### Summary

- Created the SDD contract for `2026-06-22-incremental-ux-asr-gate`.
- Added a backend-neutral incremental UX gate at `eval/asr_streaming/incremental_ux_gate.py`.
- The gate replays 16 kHz mono int16 WAV files as PCM chunks, records `chunks.jsonl` and `events.jsonl`, and writes per-case plus aggregate `summary.json` files.
- Added fake protocol adapters for valid incremental behavior, final-only rejection, and late-partial rejection.
- Added service-level self-tests for old-session event rejection and cancel producing no accepted partial/final output.
- Added Chinese metric explanations for incremental UX fields including first partial latency, partial cadence, final latency, partial rewrite rate, final coverage, ignored stale events, and cancel leakage.
- Updated `eval/asr_streaming/validate.sh` and README documentation.

### Files changed

- `eval/asr_streaming/incremental_ux_gate.py`
- `eval/asr_streaming/validate.sh`
- `eval/asr_streaming/README.md`
- `specs/2026-06-22-incremental-ux-asr-gate/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/incremental_ux_gate.py`
  Result: pass
  Notes: New incremental UX gate script compiles.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null && python3 -m json.tool specs/2026-06-22-incremental-ux-asr-gate/feature.json >/dev/null`
  Result: pass
  Notes: Feature matrix and new feature metadata are valid JSON.
- Command: `python3 eval/asr_streaming/incremental_ux_gate.py self-test`
  Result: pass
  Notes: Self-test accepts valid incremental behavior; rejects final-only and late partial behavior; verifies stale old-session events are ignored; verifies cancel produces no accepted partial/final output.
- Command: `python3 eval/asr_streaming/incremental_ux_gate.py run --adapter fake-valid --cases eval/asr_streaming/cases.smoke.local.jsonl --out-dir eval/asr_streaming/results/incremental-ux-gate-fake-smoke-20260622 --no-realtime`
  Result: pass
  Notes: Wrote `eval/asr_streaming/results/incremental-ux-gate-fake-smoke-20260622/summary.json`; aggregate passed 1/1 case with no gate failure reasons. This is a diagnostic protocol run, not product latency evidence because `--no-realtime` was used.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Existing ASR eval harness validation still passes, including realtime gate, incremental UX gate, Qwen3 MLX realtime probe, Qwen3 cumulative recompute probe, and Qwen3 cumulative service self-tests.

### Blockers / open questions

- No blockers for the gate itself.
- Real Qwen3-ASR MLX and MiMo adapters are not implemented in this feature; they remain follow-up feature candidates.
- Swift/macOS app runtime files were not changed, so `swift build` and `swift test` were not required by this feature validation.

### Next recommended action

- Create the Qwen3-ASR MLX real local service boundary feature, then add it as the first real backend adapter for `incremental_ux_gate.py`.
## 2026-06-22 — ASR backend selection roadmap contract

### Summary

- Consulted Claude Opus through the read-only advisory wrapper to independently review the ASR model evaluation and backend-selection route.
- Incorporated the review's corrections into a new total-control SDD contract: `specs/2026-06-22-asr-backend-selection-roadmap/`.
- The roadmap explicitly fixes four risks:
  - `incremental_ux_gate.py` is currently fake-adapter-only and needs real backend transport adapters before real model comparison.
  - `first partial <= 1.5s` must not be a universal hard fail because it conflicts with current Qwen3 cumulative evidence.
  - `final_coverage_ratio` is a length/truncation signal, not an accuracy metric.
  - RTF must be measured separately in non-realtime compute mode because realtime pacing makes realtime-mode RTF misleading.
- The roadmap defines four final backend roles: partial backend, final backend, fallback backend, and reference-only models.

### Files changed

- `specs/2026-06-22-asr-backend-selection-roadmap/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `codex-consult invoke --request -`
  Result: pass
  Notes: Claude Opus advisory completed successfully. Artifact written to `/Users/xulelong/2025/projects/LocalVoiceInput/consult_briefs/20260622/claude-localvoiceinput-asr-backend-selection-roadmap-review-a5ef44fe/review.md`.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null`
  Result: pass
  Notes: Feature matrix JSON is valid after adding `2026-06-22-asr-backend-selection-roadmap`.
- Command: `python3 -m json.tool specs/2026-06-22-asr-backend-selection-roadmap/feature.json >/dev/null`
  Result: pass
  Notes: Roadmap feature metadata JSON is valid.
- Command: `test -f specs/2026-06-22-asr-backend-selection-roadmap/requirements.md && test -f specs/2026-06-22-asr-backend-selection-roadmap/plan.md && test -f specs/2026-06-22-asr-backend-selection-roadmap/validation.md && test -f specs/2026-06-22-asr-backend-selection-roadmap/decisions.md`
  Result: pass
  Notes: All required roadmap contract files exist.

### Blockers / open questions

- Roadmap execution has not started; feature matrix status is `not_started`, `passes=false`.
- Exact CER/WER hard thresholds and RSS hard thresholds remain open until the next implementation feature collects more real backend evidence.

### Next recommended action

- Create the Phase 1 implementation feature to add real backend transport adapters to `incremental_ux_gate.py` and promote CER/WER to hard quality dimensions.

### Goal clarification

- The roadmap goal was clarified after contract creation: the intended goal is not Phase 1 alone, but completion of the full ASR model evaluation program.
- Updated `requirements.md`, `validation.md`, and `decisions.md` so roadmap completion requires all candidate models, all required test types, all required metrics/data, and final role decisions for partial, final, fallback, reference-only, or rejected status.
- Validation check: `test -f specs/2026-06-22-asr-backend-selection-roadmap/requirements.md && test -f specs/2026-06-22-asr-backend-selection-roadmap/validation.md && test -f specs/2026-06-22-asr-backend-selection-roadmap/decisions.md && python3 -m json.tool specs/2026-06-22-asr-backend-selection-roadmap/feature.json >/dev/null && python3 -m json.tool specs/feature_matrix.json >/dev/null`
  Result: pass.

## 2026-06-23 — Incremental UX real backend adapters

### Summary

- Corrected the ASR backend selection roadmap goal so it is executable: role-based test applicability, no orphaned standalone candidates, fake-only gate prerequisite, support-artifact exclusion, and fixed-vs-deferred hard gates are now explicit.
- Created `2026-06-23-incremental-ux-real-backend-adapters` as the first execution feature for the roadmap.
- Added an `http-json` localhost transport adapter to `eval/asr_streaming/incremental_ux_gate.py`.
- Added a controlled `fake_incremental_http_service.py` process to prove the canonical gate can drive a real HTTP/process boundary without loading any ASR model.
- Verified the HTTP transport path with the existing `zh_short_001` smoke WAV.

### Files changed

- `eval/asr_streaming/incremental_ux_gate.py`
- `eval/asr_streaming/fake_incremental_http_service.py`
- `eval/asr_streaming/validate.sh`
- `specs/2026-06-22-asr-backend-selection-roadmap/feature.json`
- `specs/2026-06-22-asr-backend-selection-roadmap/requirements.md`
- `specs/2026-06-22-asr-backend-selection-roadmap/plan.md`
- `specs/2026-06-22-asr-backend-selection-roadmap/validation.md`
- `specs/2026-06-22-asr-backend-selection-roadmap/decisions.md`
- `specs/2026-06-23-incremental-ux-real-backend-adapters/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/incremental_ux_gate.py eval/asr_streaming/fake_incremental_http_service.py`
  Result: pass
  Notes: Incremental gate and fake HTTP service both compile.
- Command: `python3 eval/asr_streaming/incremental_ux_gate.py self-test`
  Result: pass
  Notes: Existing fake adapter regressions still pass, including valid incremental, final-only rejection, late partial rejection, cancel, and stale-session handling.
- Command: `python3 eval/asr_streaming/incremental_ux_gate.py run --adapter http-json --cases eval/asr_streaming/cases.smoke.local.jsonl --out-dir /tmp/localvoiceinput-missing-service-url-test --no-realtime`
  Result: pass
  Notes: Expected failure path returned nonzero with `--service-url is required for --adapter http-json`.
- Command: `python3 eval/asr_streaming/fake_incremental_http_service.py --host 127.0.0.1 --port 18095`
  Result: pass
  Notes: Local fake HTTP service started and was shut down after the smoke run.
- Command: `python3 eval/asr_streaming/incremental_ux_gate.py run --adapter http-json --service-url http://127.0.0.1:18095 --cases eval/asr_streaming/cases.smoke.local.jsonl --out-dir eval/asr_streaming/results/incremental-ux-http-fake-smoke-20260623 --no-realtime`
  Result: pass
  Notes: `http-json` transport passed 1/1 cases; aggregate `incremental_ux_gate_passed=true`, mean CER 0.0, mean WER 0.0, first partial latency about 22.5 ms in non-realtime diagnostic mode, final coverage 1.0.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: ASR eval validation passed, including transcript self-test, realtime gate self-test, incremental UX gate self-test, Qwen3 MLX realtime probe self-test, Qwen3 cumulative probe self-test, and Qwen3 cumulative service self-test.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null && python3 -m json.tool specs/2026-06-23-incremental-ux-real-backend-adapters/feature.json >/dev/null && python3 -m json.tool specs/2026-06-22-asr-backend-selection-roadmap/feature.json >/dev/null`
  Result: pass
  Notes: SDD JSON files remain valid.

### Blockers / open questions

- This validates transport/process-boundary plumbing only; it is not real ASR model evidence.
- The next backend-selection blocker is to expose the existing Qwen3-ASR MLX cumulative wrapper as a real local service process and run it through `http-json`.

### Next recommended action

- Create the Qwen3-ASR MLX real service boundary feature and run `qwen3-asr-0.6b-mlx-8bit` through the canonical HTTP transport gate on smoke and long-draft cases.

## 2026-06-23 — Qwen3-ASR MLX HTTP service boundary

### Summary

- Created `2026-06-23-qwen3-mlx-http-service-boundary` for the first real local process boundary around the Qwen3-ASR 0.6B MLX cumulative recompute wrapper.
- Added `eval/asr_streaming/qwen3_mlx_http_service.py` with localhost JSON endpoints: `/health`, `/metadata`, `/start`, `/chunk`, `/finish`, and `/cancel`.
- Reused the canonical `incremental_ux_gate.py --adapter http-json` contract, including gate-owned `session_token` values.
- Added fake-backend mode for transport regression testing without loading MLX/model weights.
- Added `scripts/run_qwen3_mlx_http_gate_smoke.sh` for one-command real Qwen3 0.6B MLX HTTP gate runs.
- Added `eval/asr_streaming/cases.long120.local.jsonl` for a reproducible 33-second long-form HTTP gate case.
- Fixed a real runtime issue: MLX inference failed under `ThreadingHTTPServer` with `There is no Stream(gpu, 1) in current thread`; the service now uses single-threaded `HTTPServer` so model load and inference run on the same thread.

### Files changed

- `eval/asr_streaming/incremental_ux_gate.py`
- `eval/asr_streaming/qwen3_mlx_cumulative_service.py`
- `eval/asr_streaming/qwen3_mlx_http_service.py`
- `eval/asr_streaming/cases.long120.local.jsonl`
- `eval/asr_streaming/validate.sh`
- `scripts/run_qwen3_mlx_http_gate_smoke.sh`
- `specs/2026-06-23-qwen3-mlx-http-service-boundary/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/qwen3_mlx_http_service.py eval/asr_streaming/qwen3_mlx_cumulative_service.py`
  Result: pass
  Notes: New HTTP service and cumulative service compile.
- Command: `python3 eval/asr_streaming/qwen3_mlx_cumulative_service.py self-test`
  Result: pass
  Notes: Existing cumulative service session, stale partial, cancel, and finish tests pass.
- Command: `python3 eval/asr_streaming/incremental_ux_gate.py self-test`
  Result: pass
  Notes: Incremental UX gate fake backends, stale token handling, late partial rejection, and cancel handling pass.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: ASR streaming eval harness validation passes after adding the HTTP service compile check.
- Command: `python3 eval/asr_streaming/qwen3_mlx_http_service.py --fake-backend --host 127.0.0.1 --port 18105`
  Result: pass
  Notes: Fake HTTP service starts and responds to the canonical HTTP gate.
- Command: `python3 eval/asr_streaming/incremental_ux_gate.py run --adapter http-json --service-url http://127.0.0.1:18105 --model-id qwen3-asr-0.6b-mlx-8bit --cases eval/asr_streaming/cases.smoke.local.jsonl --out-dir eval/asr_streaming/results/qwen3-mlx-http-service-fake-smoke-20260623 --max-first-partial-ms 3000 --max-final-latency-ms 3000`
  Result: pass
  Notes: Fake process-boundary gate passed 1/1 case. Mean CER 0.0, WER 0.0, first partial 1025 ms, final latency 40 ms, final coverage 1.0.
- Command: `bash scripts/run_qwen3_mlx_http_gate_smoke.sh`
  Result: pass
  Notes: Real `qwen3-asr-0.6b-mlx-8bit` HTTP gate passed 1/1 smoke case. Result directory: `eval/asr_streaming/results/qwen3-mlx-http-service-0.6b-smoke-20260623-145919`. Mean CER 0.1053, WER 0.1053, first partial 1161 ms, partial cadence 1002 ms, final latency 180 ms, final coverage 0.9474, RTF 1.2969. Final text misrecognized `语音` as `云`, but passed the incremental UX gate thresholds.
- Command: `CASES=eval/asr_streaming/cases.long120.local.jsonl OUT_DIR=eval/asr_streaming/results/qwen3-mlx-http-service-0.6b-long120-20260623 bash scripts/run_qwen3_mlx_http_gate_smoke.sh`
  Result: pass
  Notes: Real `qwen3-asr-0.6b-mlx-8bit` HTTP gate passed 1/1 long_120 case. Mean CER 0.0082, WER 0.0082, first partial 1136 ms, partial cadence 1007 ms, final latency 577 ms, final coverage 1.0, RTF 1.1703. Final text misrecognized `本机` as `手机`.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null && python3 -m json.tool specs/2026-06-23-qwen3-mlx-http-service-boundary/feature.json >/dev/null`
  Result: pass
  Notes: SDD JSON files remain valid.

### Blockers / open questions

- No blocker remains for the Qwen3 MLX HTTP process boundary feature.
- This still does not prove native realtime streaming; the service remains a cumulative recompute wrapper with `native_realtime_gate_eligible=false`.
- RSS/memory and sustained CPU use under longer sessions still need measurement before Swift app integration.
- Swift/macOS app runtime files were not changed; `swift build` and `swift test` were not required for this eval-only feature.

### Next recommended action

- Create the Swift-side local ASR service adapter spec, but only after defining RSS/CPU acceptance thresholds and preserving the existing app safety contract: cancel, stale-session isolation, focus downgrade, clipboard fallback, and no partial text insertion into the active app.

## 2026-06-23 — Qwen3-ASR MLX HTTP resource and extended gate validation

### Summary

- Created `2026-06-23-qwen3-mlx-http-resource-validation` to extend Qwen3-ASR 0.6B MLX HTTP validation without requiring new recordings or touching the Swift app.
- Added a long-case subset covering existing `long_200_001`, `long_400_001`, and `long_code_switch_001` recordings.
- Added a PID resource sampler that writes `resource_samples.jsonl` and `resource_summary.json`.
- Added `scripts/run_qwen3_mlx_http_extended_gate.sh` to start the local Qwen3 HTTP service, run the canonical `http-json` gate, sample RSS/CPU, write run metadata, and clean up processes.
- First extended run failed 2/3 cases because the cumulative wrapper carried prior session worker time into later session-relative gate runs. Fixed by resetting `worker_available_ms` on every new session start and added a self-test for that regression.
- After the fix, the extended run passed 3/3 cases.

### Files changed

- `eval/asr_streaming/cases.extended.local.jsonl`
- `eval/asr_streaming/monitor_pid_resources.py`
- `eval/asr_streaming/qwen3_mlx_cumulative_service.py`
- `eval/asr_streaming/validate.sh`
- `scripts/run_qwen3_mlx_http_extended_gate.sh`
- `specs/2026-06-23-qwen3-mlx-http-resource-validation/*`
- `specs/2026-06-23-qwen3-mlx-http-service-boundary/feature.json`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/monitor_pid_resources.py`
  Result: pass
  Notes: Resource sampler compiles.
- Command: `python3 eval/asr_streaming/run_eval.py validate-cases --cases eval/asr_streaming/cases.extended.local.jsonl`
  Result: pass
  Notes: Extended case subset validates 3 cases and all referenced WAV files exist.
- Command: `python3 -m py_compile eval/asr_streaming/qwen3_mlx_cumulative_service.py && python3 eval/asr_streaming/qwen3_mlx_cumulative_service.py self-test`
  Result: pass
  Notes: Added regression coverage that a new session does not inherit a previous session's worker delay.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Full ASR streaming eval harness validation still passes after adding the resource sampler and multi-session timing fix.
- Command: `bash scripts/run_qwen3_mlx_http_extended_gate.sh`
  Result: fail, then pass after the multi-session timing fix
  Notes: Initial result directory `eval/asr_streaming/results/qwen3-mlx-http-service-0.6b-extended-20260623-152531` failed 2/3 with artificial `first_partial_too_slow` and `no_partial_before_user_stop` caused by worker clock carryover. Final result directory `eval/asr_streaming/results/qwen3-mlx-http-service-0.6b-extended-20260623-153042` passed 3/3 with no gate fail reasons.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null && python3 -m json.tool specs/2026-06-23-qwen3-mlx-http-resource-validation/feature.json >/dev/null`
  Result: pass
  Notes: SDD JSON files remain valid.

### Extended gate results

- Result directory: `eval/asr_streaming/results/qwen3-mlx-http-service-0.6b-extended-20260623-153042`
- Case count: 3
- Passed: 3
- Failed: 0
- Mean CER: 0.0259
- Mean WER: 0.1252
- Mean RTF: 1.1583
- Mean first partial latency: 1130 ms
- Mean partial cadence: 1017 ms
- Mean final latency: 1283 ms
- Mean final coverage ratio: 1.0010
- Resource samples: 215
- Mean RSS: 1284 MB
- Peak RSS: 1414 MB
- Mean CPU: 4.39%
- Peak CPU: 93.5%

### Blockers / open questions

- No blocker remains for extended Qwen3 HTTP gate/resource evidence.
- The service remains a cumulative recompute wrapper, not native realtime streaming.
- `long_code_switch_001` passed timing/safety gates but still had high WER 0.3148 because English/product names were substituted or normalized poorly.
- RSS/CPU thresholds are still not formal product gates; the current run only provides first evidence.
- Swift/macOS app runtime files were not changed; `swift build` and `swift test` were not required for this eval-only feature.

### Next recommended action

- Create the Swift-side service adapter spec only after deciding provisional RSS/CPU thresholds and how to handle code-switch technical-term accuracy, while preserving the existing app safety contract.

## 2026-06-23 — Qwen3-ASR MLX Swift HTTP adapter

### Summary

- Created `2026-06-23-qwen3-mlx-swift-http-adapter` for the first Swift-side client boundary to the already validated local Qwen3-ASR MLX HTTP service.
- Added `LocalHTTPASRClient`, an `ASRClientProtocol` implementation for localhost HTTP JSON endpoints `/start`, `/chunk`, `/finish`, and `/cancel`.
- Added explicit ASR backend selection in `AppConfig`: default remains FunASR WebSocket, while `--local-http-asr`, `--asr-backend local-http`, and `--asr-http-url` enable the local HTTP backend.
- Updated `AppController` backend selection without changing focus, paste, clipboard, hotkey, floating-panel, correction, or history routing.
- Added `LocalVoiceInputMacTests` and fake-transport tests for loopback URL validation, request fields, token filtering, partial/final mapping, final-only-after-finish behavior, non-blocking cancel callback suppression, and immediate-cancel start-response suppression.
- Kept Qwen3 service supervision, LaunchAgent packaging, and code-switch technical-term correction as follow-up candidates.

### Files changed

- `Package.swift`
- `Sources/LocalVoiceInputMac/ASRClientProtocol.swift`
- `Sources/LocalVoiceInputMac/AppConfig.swift`
- `Sources/LocalVoiceInputMac/AppController.swift`
- `Sources/LocalVoiceInputMac/LocalHTTPASRClient.swift`
- `Tests/LocalVoiceInputMacTests/LocalHTTPASRClientTests.swift`
- `specs/2026-06-23-qwen3-mlx-swift-http-adapter/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null`
  Result: pass
  Notes: Feature matrix JSON is valid after adding the Swift adapter feature.
- Command: `python3 -m json.tool specs/2026-06-23-qwen3-mlx-swift-http-adapter/feature.json >/dev/null`
  Result: pass
  Notes: Feature metadata JSON is valid.
- Command: `swift build`
  Result: pass
  Notes: `LocalVoiceInputMac` builds with the new local HTTP ASR client and backend selection.
- Command: `swift test`
  Result: pass
  Notes: 51 tests passed with 0 failures, including 6 new `LocalHTTPASRClientTests`.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Existing ASR eval harness validation still passes, including transcript aggregation, realtime gate, incremental UX gate, Qwen3 realtime probe, cumulative recompute probe, and cumulative service self-test.

### Blockers / open questions

- No blocker remains for the Swift client adapter feature.
- Real Qwen3 app smoke was not run because `validation.md` marks it optional for this feature; the Python Qwen3 service must already be running, and user-facing app permission/manual validation belongs to the next integration smoke.
- The adapter connects to an existing local service only; automatic service launch/restart remains a separate follow-up.
- Long code-switch technical-term accuracy still needs a separate correction or prompt/hotword strategy before making Qwen3 the default user-facing backend.

### Next recommended action

- Create the real app smoke/service-supervision feature: start or connect to the local Qwen3 HTTP service, run `swift run LocalVoiceInputMac --local-http-asr --asr-http-url http://127.0.0.1:<port>`, and manually validate Right Option, Option+Space, Esc cancel, focus-change downgrade, secure-field clipboard fallback, and no partial insertion into the active app.

## 2026-06-23 — Qwen3-ASR MLX real app smoke

### Summary

- Created `2026-06-23-qwen3-mlx-real-app-smoke` for the first user-facing macOS smoke against the real local Qwen3-ASR MLX HTTP backend.
- Added `scripts/run_qwen3_mlx_app_smoke.sh`, a one-command foreground smoke runner that starts the Qwen3 HTTP service, waits for `/health`, launches `LocalVoiceInputMac --local-http-asr`, writes service/app logs, and cleans up the service when the app exits.
- Added dry-run mode so command construction and local path status can be checked without loading Qwen3 or launching UI.
- Updated README plus default/example config templates with the Qwen3 app smoke command, the required manual safety checklist, and explicit `asrBackend` / `asrHTTPURL` fields.
- Kept the feature `implemented`, not `validated`, because real manual macOS app smoke has not been run yet.

### Files changed

- `scripts/run_qwen3_mlx_app_smoke.sh`
- `scripts/write_default_config.sh`
- `configs/config.example.json`
- `README.md`
- `specs/2026-06-23-qwen3-mlx-real-app-smoke/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `bash -n scripts/run_qwen3_mlx_app_smoke.sh`
  Result: pass
  Notes: Smoke runner shell syntax is valid.
- Command: `python3 -m json.tool configs/config.example.json >/dev/null && bash -n scripts/write_default_config.sh && bash -n scripts/run_qwen3_mlx_app_smoke.sh && DRY_RUN=1 bash scripts/run_qwen3_mlx_app_smoke.sh`
  Result: pass
  Notes: Config JSON and shell scripts are valid. Dry-run printed service/app commands and local path status. Model and `mlx-audio` source exist; default `.venv-mimo/bin/python` is currently not executable on this checkout.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null && python3 -m json.tool specs/2026-06-23-qwen3-mlx-real-app-smoke/feature.json >/dev/null`
  Result: pass
  Notes: SDD JSON files are valid.
- Command: `swift build`
  Result: pass
  Notes: Swift package still builds after adding smoke docs/scripts.
- Command: `swift test`
  Result: pass
  Notes: 51 tests passed with 0 failures.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Existing ASR eval harness validation still passes.

### Blockers / open questions

- Real Qwen3 app smoke is pending because the default MLX Python runtime path `.venv-mimo/bin/python` is missing or not executable. Run with a valid `PYTHON_BIN` or restore the MLX runtime first.
- Manual macOS verification is still required before marking this feature validated: Right Option, Option+Space, Esc cancel, focused input auto-paste, no-input clipboard draft, secure-field fallback, focus-change downgrade, clipboard restoration, and no partial insertion.
- This foreground smoke runner is not production service supervision.

### Next recommended action

- Restore or point `PYTHON_BIN` to the MLX runtime that can import MLX/mlx-audio, then run `bash scripts/run_qwen3_mlx_app_smoke.sh` and record the manual app smoke results.

## 2026-06-23 — Qwen3-ASR MLX real app smoke runtime recovery

### Summary

- Added `scripts/setup_qwen3_mlx_runtime.sh` to recreate the `.venv-mimo` runtime needed by the Qwen3 MLX HTTP service.
- The setup script validates the local Qwen3 model directory and local `mlx-audio` source directory before installing dependencies.
- On this machine, the default `python3` is Python 3.13 and `/usr/bin/python3` is Python 3.9, so the setup script used conda to create a project-local Python 3.12 runtime at `.venv-mimo`.
- Resolved dependency constraints to match the current local `mlx-audio` source: `mlx>=0.31.1`, `mlx-lm>=0.31.1`, `transformers>=5.5,<6`, and `huggingface_hub>=1,<2`.
- Tightened `LocalHTTPASRClientTests.testCancelSuppressesLateCallbacksAndPostsCancel` so it waits for the fake `/chunk` request before cancelling; this removes a test race without weakening cancel safety.
- Updated Qwen3 MLX smoke/gate scripts and README so missing runtime errors point to `bash scripts/setup_qwen3_mlx_runtime.sh`.
- Kept the real app smoke feature `implemented`, not `validated`, because real macOS app interaction still requires manual checks.

### Files changed

- `scripts/setup_qwen3_mlx_runtime.sh`
- `scripts/run_qwen3_mlx_app_smoke.sh`
- `scripts/run_qwen3_mlx_http_gate_smoke.sh`
- `scripts/run_qwen3_mlx_http_extended_gate.sh`
- `Tests/LocalVoiceInputMacTests/LocalHTTPASRClientTests.swift`
- `README.md`
- `specs/2026-06-23-qwen3-mlx-real-app-smoke/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `bash -n scripts/setup_qwen3_mlx_runtime.sh && bash -n scripts/run_qwen3_mlx_app_smoke.sh && bash -n scripts/run_qwen3_mlx_http_gate_smoke.sh && bash -n scripts/run_qwen3_mlx_http_extended_gate.sh`
  Result: pass
  Notes: Runtime setup and smoke/gate scripts have valid shell syntax.
- Command: `bash scripts/setup_qwen3_mlx_runtime.sh`
  Result: pass
  Notes: Created/reused `.venv-mimo` with Python 3.12.13, installed MLX/mlx-audio runtime dependencies, and import check passed with `mlx_metal_available=true`, model path present, and `mlx-audio` source present.
- Command: `DRY_RUN=1 bash scripts/run_qwen3_mlx_app_smoke.sh`
  Result: pass
  Notes: Dry-run now reports `.venv-mimo/bin/python` executable, Qwen3 model path present, and `mlx-audio` source path present.
- Command: `swift build`
  Result: pass
  Notes: Swift package builds after runtime-script and test changes.
- Command: `swift test`
  Result: pass
  Notes: 51 tests passed with 0 failures after fixing the asynchronous cancel test race.
- Command: `bash eval/asr_streaming/validate.sh`
  Result: pass
  Notes: Existing ASR eval harness validation still passes.
- Command: `bash scripts/run_qwen3_mlx_http_gate_smoke.sh`
  Result: pass
  Notes: Service loaded Qwen3 0.6B MLX in about 1606 ms and wrote `eval/asr_streaming/results/qwen3-mlx-http-service-0.6b-smoke-20260623-234626`. `zh_short_001` passed incremental UX gate with first partial latency about 1392 ms, final latency about 150 ms, RTF 1.3193, CER 0.1053, and WER 0.1053.

### Blockers / open questions

- No blocker remains for local Qwen3 MLX runtime recreation or backend HTTP smoke.
- Real app smoke is still pending and must be run manually in macOS apps before setting this feature to `validated`.
- The Qwen3 HTTP backend remains optional; FunASR WebSocket remains the default backend.
- This smoke runner is foreground test orchestration only, not production service supervision.

### Next recommended action

- Run `bash scripts/run_qwen3_mlx_app_smoke.sh`, then manually verify Notes, browser no-input area, browser/ChatGPT text input, secure field, focus-change downgrade, Esc cancel, Option+Space long draft, clipboard restoration, and no partial insertion into the active app.

## 2026-06-24 — Qwen3 real app smoke partial manual evidence: Chrome input paste

### Summary

- Manual smoke initially passed Apple Notes focused-input auto-paste and Chrome/browser no-input clipboard draft behavior.
- Chrome webpage input initially failed safe auto-paste because Chrome returned no focused accessibility element, producing `role=nil edit=F paste=F conf=low mode=clipboardDraft`; the app correctly downgraded to clipboard draft instead of forcing paste.
- Added a conservative `FocusDetector` enhancement for Chromium browsers:
  - fall back from system-wide focus to frontmost app/window focused elements;
  - request Chromium enhanced accessibility on the app/window before reading focus;
  - keep the existing safety rule that unknown focus remains clipboard draft.
- After restarting the app, Chrome webpage input auto-paste succeeded with diagnostics showing `role=AXTextArea edit=T paste=T secure=F conf=high mode=cursorPaste changed=F`.
- Paste verification was confirmed: `Output verify=confirmed status=pasted restored=T`, so the dictated text was inserted into the current Chrome input and the original clipboard was restored.

### Files changed

- `Sources/LocalVoiceInputMac/FocusDetector.swift`
- `specs/progress.md`

### Validation

- Command: `swift build`
  Result: pass
  Notes: FocusDetector changes compile.
- Command: `swift test`
  Result: pass
  Notes: 51 tests passed with 0 failures.
- Manual: Chrome webpage input field with Qwen3 HTTP app smoke
  Result: pass
  Notes: Final text auto-pasted into the Google input field. Floating panel diagnostics: `verify=confirmed status=pasted restored=T`, `Focus com.google.Chrome role=AXTextArea edit=T paste=T secure=F conf=high mode=cursorPaste changed=F`.

### Blockers / open questions

- Real app smoke is still partial. Remaining checks include secure/password field fallback, focus-change downgrade, Esc cancel, Option+Space long draft, paste-failure fallback, and broader app targets such as ChatGPT input, Cursor/VS Code, WeChat, Obsidian/Notion, and Finder rename.
- Chromium enhanced accessibility behavior may depend on browser state. If Chrome again reports `role=nil`, `chrome://accessibility` or `--force-renderer-accessibility` remains the manual fallback, but the app must continue to copy rather than force-paste when focus is unproven.

## 2026-06-24 — Qwen3 app smoke partial cadence tuning

### Summary

- Manual Notes smoke showed correct final output, clipboard restoration, and paste behavior, but the floating panel partial text could stall until the user released Right Option.
- Root cause candidate: the Qwen3 MLX HTTP service was launched from the app smoke runner with service defaults intended for bounded gate tests: `min_prefix_sec=1.0`, `prefix_step_sec=1.0`, and `max_prefixes=8`.
- The 8-prefix cap is not suitable for real app smoke because longer dictation can stop producing partial updates before the user stops recording.
- Tuned the app smoke runner only:
  - `MIN_PREFIX_SEC=0.75`
  - `PREFIX_STEP_SEC=0.75`
  - `MAX_PREFIXES=180`
- This keeps the backend local/offline and does not change paste safety, clipboard restoration, focus routing, or the default FunASR backend.

### Files changed

- `scripts/run_qwen3_mlx_app_smoke.sh`
- `specs/progress.md`

### Validation

- Command: `bash -n scripts/run_qwen3_mlx_app_smoke.sh`
  Result: pass
  Notes: Script syntax is valid after adding prefix cadence parameters.
- Command: `DRY_RUN=1 bash scripts/run_qwen3_mlx_app_smoke.sh`
  Result: pass
  Notes: Dry-run shows the service command now includes `--min-prefix-sec 0.75 --prefix-step-sec 0.75 --max-prefixes 180`.
- Manual restart: `bash scripts/run_qwen3_mlx_app_smoke.sh`
  Result: pass
  Notes: New running service PID includes the tuned arguments and `/health` remains OK.

### Blockers / open questions

- This reduces the obvious partial-stall risk, but Qwen3 MLX remains a cumulative-recompute wrapper rather than a native feed/step/close streaming session. Some partial lag is still possible under longer speech or high compute load.
- Need repeat manual Notes/Chrome tests to determine whether the observed 50% partial stall rate is resolved enough for the current MVP smoke.

## 2026-06-24 — Floating panel transcript wrapping fix

### Summary

- Manual Notes smoke with repeated long text showed correct dictation/paste behavior, but the floating panel transcript stayed on one long line instead of wrapping.
- Fixed the transcript label to wrap long recognized text by character and allow up to 4 visible lines.
- Increased the floating panel size from `720x180` to `760x220` so wrapped transcript text has enough vertical space.
- This is a UI-only change and does not affect ASR, focus detection, paste routing, clipboard restoration, or security fallback behavior.

### Files changed

- `Sources/LocalVoiceInputMac/FloatingPanelController.swift`
- `specs/progress.md`

### Validation

- Command: `swift build`
  Result: pass
  Notes: Floating panel UI changes compile.
- Command: `swift test`
  Result: pass
  Notes: 51 tests passed with 0 failures.
- Command: `git diff --check -- Sources/LocalVoiceInputMac/FloatingPanelController.swift specs/progress.md`
  Result: pass
  Notes: No whitespace errors in the touched files.

### Blockers / open questions

- Needs one manual retest with the same repeated sentence to visually confirm the transcript wraps in the live floating panel.

## 2026-06-24 — Long dictation floating transcript scroll and token cap fix

### Summary

- Manual long dictation smoke confirmed the previous wrapping fix still had poor UX after 4 lines: the transcript area stayed fixed but clipped later text instead of showing the newest recognized content.
- Replaced the floating transcript label with a read-only, non-selectable `NSTextView` inside an `NSScrollView`.
- The transcript area keeps a fixed height and automatically scrolls to the bottom after each partial/final update, so long dictation shows the latest text instead of truncating at the first 4 lines.
- Raised the Qwen3 app smoke default `MAX_TOKENS` from `256` to `1024` to reduce the risk that long final output is cut by the model generation limit during manual app tests.
- This preserves the product boundary: partial text remains only in the floating panel, not in the active app input field.

### Files changed

- `Sources/LocalVoiceInputMac/FloatingPanelController.swift`
- `scripts/run_qwen3_mlx_app_smoke.sh`
- `specs/progress.md`

### Validation

- Command: `swift build`
  Result: pass
  Notes: Floating panel scroll-view UI changes compile.
- Command: `swift test`
  Result: pass
  Notes: 51 tests passed with 0 failures.
- Command: `bash -n scripts/run_qwen3_mlx_app_smoke.sh && DRY_RUN=1 bash scripts/run_qwen3_mlx_app_smoke.sh`
  Result: pass
  Notes: Dry-run shows the Qwen3 service command now uses `--max-tokens 1024 --min-prefix-sec 0.75 --prefix-step-sec 0.75 --max-prefixes 180`.
- Command: `git diff --check -- Sources/LocalVoiceInputMac/FloatingPanelController.swift scripts/run_qwen3_mlx_app_smoke.sh specs/progress.md`
  Result: pass
  Notes: No whitespace errors in touched files.

### Blockers / open questions

- Needs manual retest with the same long dictation paragraph to confirm:
  - the floating transcript stays fixed height but follows the latest text;
  - the final pasted/copied output includes the full spoken content rather than being cut near the old 256-token limit.

## 2026-06-25 — Long dictation backlog and final timeout hardening

### Summary

- Manual long dictation smoke with several hundred Chinese characters showed two issues:
  - floating-panel partial updates slowed down as the utterance grew;
  - releasing Right Option could finalize with an incomplete tail when the local Qwen3 backend was still catching up.
- Root cause analysis:
  - Qwen3 MLX app smoke uses a cumulative-recompute wrapper, not a native realtime `feed/step/close` streaming session.
  - Frequent prefix recompute becomes increasingly expensive as audio length grows, because each partial can rerun over a longer accumulated prefix.
  - `LocalHTTPASRClient` posts chunk requests serially; if the service is busy computing partials, later chunks and `/finish` queue behind earlier work.
  - `AppController` used a fixed 3.5 second finalize timeout after user stop. For long local HTTP sessions, that could fire before `/finish` returned, causing the latest partial to be output as final and dropping the tail.
- Changes:
  - Tuned Qwen3 app smoke partial cadence from `min_prefix_sec=0.75`, `prefix_step_sec=0.75` to `min_prefix_sec=1.0`, `prefix_step_sec=1.5`.
  - Kept `max_prefixes=180` so long recordings do not stop partials due to the old 8-prefix cap.
  - Added App-side audio duration tracking and LocalHTTP-specific adaptive final timeout: `max(12s, audioSeconds * 0.75 + 10s)`, capped at `120s`.
- This prioritizes not losing text over instant finalization for long Qwen3 cumulative-wrapper sessions.

### Files changed

- `Sources/LocalVoiceInputMac/AppController.swift`
- `scripts/run_qwen3_mlx_app_smoke.sh`
- `specs/progress.md`

### Validation

- Command: `swift build`
  Result: pass
  Notes: AppController timeout hardening compiles.
- Command: `swift test`
  Result: pass
  Notes: 51 tests passed with 0 failures.
- Command: `bash -n scripts/run_qwen3_mlx_app_smoke.sh && DRY_RUN=1 bash scripts/run_qwen3_mlx_app_smoke.sh`
  Result: pass
  Notes: Dry-run shows `--max-tokens 1024 --min-prefix-sec 1.0 --prefix-step-sec 1.5 --max-prefixes 180`.
- Command: `git diff --check -- Sources/LocalVoiceInputMac/AppController.swift scripts/run_qwen3_mlx_app_smoke.sh specs/progress.md`
  Result: pass
  Notes: No whitespace errors in touched files.

### Blockers / open questions

- Needs manual long-dictation retest after app restart to confirm the final output no longer drops the tail.
- Current Qwen3 cumulative wrapper should be treated as a medium-length dictation candidate, not a proven production path for multi-minute continuous dictation.
- A robust long-dictation architecture should move toward segment-based commit/merge or a true streaming ASR backend so partial computation does not grow with full accumulated audio length.

## 2026-06-25 — 2026-06-25-long-dictation-asr-evaluation

### Summary

- Created an SDD feature contract for long-dictation ASR evaluation and streaming-route validation.
- Added a license-tracked long corpus manifest that separates metric-bearing cases from experience-smoke material.
- Added local corpus preparation tooling that writes runnable JSONL cases from local source WAV/media without downloading or uploading data.
- Generated:
  - `eval/asr_streaming/cases.long_prepared.local.jsonl` with 3 existing local long cases: 32.92s, 42.01s, and 81.30s.
  - `eval/asr_streaming/cases.long_synthetic.local.jsonl` with synthetic stress cases: 243.90s and 650.41s, clearly marked as synthetic repetition for compute/backlog stress only.
- Added `scripts/run_qwen3_mlx_http_long_benchmark.sh`, a dry-run friendly long benchmark runner that starts the local Qwen3 MLX HTTP service, runs the incremental UX gate, samples process resources, and writes structured metadata.
- Added `eval/asr_streaming/probe_mlx_qwen3_asr_streaming.py` to distinguish `mlx-qwen3-asr` source/API signals from locally verified timed PCM streaming.
- Cloned the community `mlx-qwen3-asr` source into `.external/repos/mlx-qwen3-asr` for code-surface probing only.

### Files changed

- `eval/asr_streaming/README.md`
- `eval/asr_streaming/long_corpus_manifest.json`
- `eval/asr_streaming/prepare_long_corpus.py`
- `eval/asr_streaming/probe_mlx_qwen3_asr_streaming.py`
- `scripts/run_qwen3_mlx_http_long_benchmark.sh`
- `specs/2026-06-25-long-dictation-asr-evaluation/feature.json`
- `specs/2026-06-25-long-dictation-asr-evaluation/requirements.md`
- `specs/2026-06-25-long-dictation-asr-evaluation/plan.md`
- `specs/2026-06-25-long-dictation-asr-evaluation/validation.md`
- `specs/2026-06-25-long-dictation-asr-evaluation/decisions.md`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null && python3 -m json.tool specs/2026-06-25-long-dictation-asr-evaluation/feature.json >/dev/null && python3 -m json.tool eval/asr_streaming/long_corpus_manifest.json >/dev/null`
  Result: pass
  Notes: Feature matrix, feature metadata, and corpus manifest are valid JSON.
- Command: `bash -n scripts/run_qwen3_mlx_http_long_benchmark.sh`
  Result: pass
  Notes: Shell syntax is valid.
- Command: `python3 -m py_compile eval/asr_streaming/prepare_long_corpus.py eval/asr_streaming/probe_mlx_qwen3_asr_streaming.py`
  Result: pass
  Notes: Python scripts compile.
- Command: `python3 eval/asr_streaming/prepare_long_corpus.py --manifest eval/asr_streaming/long_corpus_manifest.json --out-cases eval/asr_streaming/cases.long_prepared.local.jsonl --dry-run`
  Result: pass
  Notes: Dry-run selected 3 existing local cases and skipped disabled public/synthetic candidates.
- Command: `python3 eval/asr_streaming/prepare_long_corpus.py --manifest eval/asr_streaming/long_corpus_manifest.json --out-cases eval/asr_streaming/cases.long_prepared.local.jsonl`
  Result: pass
  Notes: Wrote 3 runnable existing local cases.
- Command: `python3 eval/asr_streaming/prepare_long_corpus.py --manifest eval/asr_streaming/long_corpus_manifest.json --out-cases eval/asr_streaming/cases.long_synthetic.local.jsonl --only-id synthetic_repeat_180_001 --only-id synthetic_repeat_600_001`
  Result: pass
  Notes: Wrote 2 synthetic repetition stress cases.
- Command: `python3 eval/asr_streaming/run_eval.py validate-cases --cases eval/asr_streaming/cases.long_prepared.local.jsonl`
  Result: pass
  Notes: Validated 3 prepared cases.
- Command: `python3 eval/asr_streaming/run_eval.py validate-cases --cases eval/asr_streaming/cases.long_synthetic.local.jsonl`
  Result: pass
  Notes: Validated 2 synthetic stress cases.
- Command: `DRY_RUN=1 bash scripts/run_qwen3_mlx_http_long_benchmark.sh`
  Result: pass
  Notes: Dry-run printed resolved model/service/case paths without loading the model.
- Command: `python3 eval/asr_streaming/probe_mlx_qwen3_asr_streaming.py --dry-run --out-dir eval/asr_streaming/results/probe-mock`
  Result: pass
  Notes: Dry-run wrote probe summary without importing external source.
- Command: `.venv-mimo/bin/python eval/asr_streaming/probe_mlx_qwen3_asr_streaming.py --source-dir .external/repos/mlx-qwen3-asr --out-dir eval/asr_streaming/results/mlx-qwen3-asr-streaming-probe-final-20260626-001630`
  Result: pass
  Notes: Source commit `f069a0f2158b401c205c4d68633d3e3f3c5af469`; imported 5 modules; found session-like surface (`init_streaming`, `feed_audio`, `finish_streaming`, `StreamingState`), cache signals, and tail-refinement signals. Classification remains `realtime_gate_eligible_now=false` because no timed PCM smoke has loaded the model and proven partial/final/cancel behavior.
- Command: `bash scripts/run_qwen3_mlx_http_long_benchmark.sh`
  Result: pass
  Notes: Result directory `eval/asr_streaming/results/qwen3-mlx-http-long-benchmark-20260626-001150`. Ran 3 existing local cases under realtime pacing with Qwen3-ASR MLX 0.6B cumulative wrapper.

### Qwen3 long benchmark evidence

- Cases: 32.92s, 42.01s, 81.30s.
- Aggregate result: 3/3 passed the incremental UX gate.
- Mean CER: `0.0153` (中文字符错误率，越低越好).
- Mean WER: `0.0230` (词/token 错误率，越低越好).
- Mean first partial latency: `1407 ms` (首个 partial 出现时间).
- Mean partial cadence: `1512 ms` (partial 平均更新间隔).
- Mean final latency: `999 ms` (用户停止后 final 返回时间).
- Mean partial rewrite rate: `0.1228` (partial 文本改写率).
- Mean RTF: `1.4077` (实时因子；大于 1 表示端到端慢于音频实时长度).
- 81.30s case RTF: `1.5791`, which is the first clear local signal that longer cumulative-wrapper sessions start to exceed realtime pace.
- Resource summary: peak RSS `2034.67 MB`, mean RSS `1455.16 MB`, peak CPU `104.1%`, mean CPU `24.66%`.

### Blockers / open questions

- No public dataset/talk material has been acquired yet. The manifest has placeholders for FLEURS, Common Voice, and public media candidates, but they remain disabled until license/source/transcript metadata is filled.
- The 243.90s and 650.41s synthetic cases are ready for explicit stress runs, but they are not natural speech evidence and should not be used for UX quality claims.
- `mlx-qwen3-asr` has promising source/API signals, but still needs a dedicated timed PCM smoke adapter before it can be treated as a validated streaming backend candidate.

### Next recommended action

- Create a follow-up feature for `mlx-qwen3-asr` timed PCM smoke using `init_streaming/feed_audio/finish_streaming`, then run the 32s/42s/81s prepared cases and optionally the 243s synthetic stress case.

## 2026-06-26 — 2026-06-26-mlx-qwen3-asr-timed-pcm-smoke

### Summary

- Created a follow-up SDD feature for local `mlx-qwen3-asr` timed PCM smoke.
- Added `eval/asr_streaming/probe_mlx_qwen3_asr_timed_pcm.py`, an independent probe that:
  - imports the local `.external/repos/mlx-qwen3-asr` checkout;
  - loads the local `.external/models/mlx-community__Qwen3-ASR-0.6B-8bit` model;
  - feeds existing 16 kHz mono int16 WAV cases as sequential PCM chunks;
  - calls `init_streaming`, `feed_audio`, and `finish_streaming`;
  - records pre-stop partials, post-stop final, TTFP, partial cadence, final latency, RTF, CER, WER, partial stability, rewrite rate, finalization delta, and Chinese metric explanations.
- Added explicit distinction between:
  - `timed_pcm_gate_passed`: protocol behavior works, meaning pre-stop partial plus post-stop final;
  - `selection_gate_passed`: protocol behavior plus configured quality thresholds.
- Validation result: the local `mlx-qwen3-asr` session API works for timed PCM, but the tested 0.6B 8bit route fails current selection quality threshold on the local Chinese long case, so it is not an app-integration target yet.

### Files changed

- `eval/asr_streaming/probe_mlx_qwen3_asr_timed_pcm.py`
- `eval/asr_streaming/README.md`
- `specs/2026-06-26-mlx-qwen3-asr-timed-pcm-smoke/feature.json`
- `specs/2026-06-26-mlx-qwen3-asr-timed-pcm-smoke/requirements.md`
- `specs/2026-06-26-mlx-qwen3-asr-timed-pcm-smoke/plan.md`
- `specs/2026-06-26-mlx-qwen3-asr-timed-pcm-smoke/validation.md`
- `specs/2026-06-26-mlx-qwen3-asr-timed-pcm-smoke/decisions.md`
- `specs/2026-06-25-long-dictation-asr-evaluation/feature.json`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/probe_mlx_qwen3_asr_timed_pcm.py`
  Result: pass
  Notes: Timed PCM probe compiles.
- Command: `python3 eval/asr_streaming/probe_mlx_qwen3_asr_timed_pcm.py --dry-run --out-dir eval/asr_streaming/results/mlx-qwen3-asr-timed-pcm-dry-run-v2`
  Result: pass
  Notes: Dry-run wrote `eval/asr_streaming/results/mlx-qwen3-asr-timed-pcm-dry-run-v2/summary.json` without importing or loading the model.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null`
  Result: pass
  Notes: Feature matrix JSON is valid.
- Command: `python3 -m json.tool specs/2026-06-26-mlx-qwen3-asr-timed-pcm-smoke/feature.json >/dev/null`
  Result: pass
  Notes: Feature metadata JSON is valid.
- Command: `.venv-mimo/bin/python eval/asr_streaming/probe_mlx_qwen3_asr_timed_pcm.py --source-dir .external/repos/mlx-qwen3-asr --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit --cases eval/asr_streaming/cases.long_prepared.local.jsonl --case-limit 1 --language Chinese --stream-chunk-sec 4.0 --no-realtime-sleep --out-dir eval/asr_streaming/results/mlx-qwen3-asr-timed-pcm-smoke-v2`
  Result: pass
  Notes: Result directory `eval/asr_streaming/results/mlx-qwen3-asr-timed-pcm-smoke-v2`; protocol passed but selection failed.
- Command: `.venv-mimo/bin/python eval/asr_streaming/probe_mlx_qwen3_asr_timed_pcm.py --source-dir .external/repos/mlx-qwen3-asr --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit --cases eval/asr_streaming/cases.long_prepared.local.jsonl --case-limit 1 --language Chinese --stream-chunk-sec 4.0 --realtime-sleep --out-dir eval/asr_streaming/results/mlx-qwen3-asr-timed-pcm-realtime-v1`
  Result: pass
  Notes: Result directory `eval/asr_streaming/results/mlx-qwen3-asr-timed-pcm-realtime-v1`; realtime-paced protocol passed but selection failed.

### Timed PCM Evidence

- Source checkout: `.external/repos/mlx-qwen3-asr`, commit `f069a0f2158b401c205c4d68633d3e3f3c5af469`.
- Model: `.external/models/mlx-community__Qwen3-ASR-0.6B-8bit`.
- Case: `existing_long_120_001`, duration `32.917s`.
- Fast compatibility run, 4s internal chunk:
  - `timed_pcm_gate_passed=true`.
  - `selection_gate_passed=false`, reason `high_cer`.
  - CER `0.1475` (字符错误率，越低越好).
  - WER `0.1475` (词/token 错误率，越低越好).
  - RTF `0.0377` (实时因子；no-sleep compatibility mode, not UX timing).
  - TTFP `199.9 ms` (首个 partial 延迟).
  - partial count `8`; final latency `43.6 ms`.
- Realtime-paced run, 4s internal chunk:
  - `timed_pcm_gate_passed=true`.
  - `selection_gate_passed=false`, reason `high_cer`.
  - CER `0.1475`; WER `0.1475`.
  - RTF `1.0020`, as expected for realtime-paced input.
  - TTFP `4202.3 ms`, matching a 4s chunk before first decode.
  - partial cadence `3991.6 ms`; final latency `55.6 ms`.
- Comparative context: the previous Qwen3 cumulative HTTP long benchmark on the same local long-case set had mean CER `0.0153` and mean WER `0.0230`, so this `mlx-qwen3-asr` streaming route is currently much worse in final text quality despite better stateful streaming API shape.

### Blockers / open questions

- The tested `mlx-qwen3-asr` route is technically streamable, but current quality is below the integration threshold.
- It may be worth investigating chunk-size tuning, context/language prompts, package-side fixes, or a larger compatible model only if we need a native stateful streaming alternative to the current cumulative wrapper.
- This feature does not validate cancel/stale-session isolation for a future service wrapper; it validates the model package's timed PCM session API and text quality only.

### Next recommended action

- Keep the current Qwen3 MLX HTTP cumulative wrapper as the first app path for medium-length dictation.
- Do not integrate `mlx-qwen3-asr` into the app yet.
- If native stateful streaming remains a priority, create a separate tuning/adapter feature that starts from the timed PCM probe and targets quality parity before service integration.

## 2026-06-26 — 2026-06-26-segment-budget-asr-evaluation

### Summary

- Created a measurement-only SDD feature for segment-budget evidence.
- Added controlled local case generation for:
  - same speech content with silence padding to 60s and 120s;
  - silence-only 33s/60s/120s;
  - repeated speech content 2x/3x/4x, with 4x at 131.669s.
- Added analysis tooling that reports wall time, RTF, CER, WER, expected/final normalized characters, warmup exclusion, quality warnings, and Chinese metric explanations.
- Ran Qwen3-ASR MLX 0.6B 8bit final/file-level inference through the existing `mlx-stt-local` adapter.

### Files changed

- `eval/asr_streaming/prepare_segment_budget_cases.py`
- `eval/asr_streaming/analyze_segment_budget_results.py`
- `eval/asr_streaming/cases.segment_budget.local.jsonl`
- `eval/asr_streaming/audio/segment_budget/*`
- `eval/asr_streaming/results/segment-budget-qwen3-mlx-0.6b-20260626-warmup-4x/*`
- `eval/asr_streaming/results/segment-budget-qwen3-mlx-0.6b-20260626-warmup-4x-analysis/*`
- `specs/2026-06-26-segment-budget-asr-evaluation/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/prepare_segment_budget_cases.py eval/asr_streaming/analyze_segment_budget_results.py`
  Result: pass
  Notes: New segment-budget scripts compile.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null && python3 -m json.tool specs/2026-06-26-segment-budget-asr-evaluation/feature.json >/dev/null`
  Result: pass
  Notes: Feature matrix and feature metadata JSON are valid.
- Command: `python3 eval/asr_streaming/prepare_segment_budget_cases.py --dry-run`
  Result: pass
  Notes: Planned 10 cases including one warmup case, 3 silence/time-control cases, 2 silence-padded same-text cases, and 3 repeated-content cases.
- Command: `python3 eval/asr_streaming/prepare_segment_budget_cases.py && python3 eval/asr_streaming/run_eval.py validate-cases --cases eval/asr_streaming/cases.segment_budget.local.jsonl`
  Result: pass
  Notes: Wrote `eval/asr_streaming/cases.segment_budget.local.jsonl`; validated 10 generated cases.
- Command: `PYTHONPATH=.external/repos/mlx-audio /usr/bin/time -l .venv-mimo/bin/python eval/asr_streaming/run_eval.py run --adapter mlx-stt-local --model-id qwen3-asr-0.6b-mlx-8bit --mlx-stt-model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit --mlx-stt-language Chinese --cases eval/asr_streaming/cases.segment_budget.local.jsonl --out-dir eval/asr_streaming/results/segment-budget-qwen3-mlx-0.6b-20260626-warmup-4x`
  Result: pass
  Notes: Result directory `eval/asr_streaming/results/segment-budget-qwen3-mlx-0.6b-20260626-warmup-4x`; wall time `10.98s`; maximum resident set size `1701658624` bytes; macOS peak memory footprint `4213328680` bytes.
- Command: `python3 eval/asr_streaming/analyze_segment_budget_results.py --summary eval/asr_streaming/results/segment-budget-qwen3-mlx-0.6b-20260626-warmup-4x/summary.json --cases eval/asr_streaming/cases.segment_budget.local.jsonl --out-dir eval/asr_streaming/results/segment-budget-qwen3-mlx-0.6b-20260626-warmup-4x-analysis`
  Result: pass
  Notes: Analysis written to `analysis.json` and `analysis.md`.

### Segment-budget pilot evidence

| Case | Audio sec | Expected chars | Final chars | Wall ms | RTF | CER/WER |
|---|---:|---:|---:|---:|---:|---:|
| same text base | 32.917 | 122 | 122 | 589.4 | 0.018 | 0.0082 |
| same text + silence | 60.000 | 122 | 122 | 772.1 | 0.013 | 0.0082 |
| same text + silence | 120.000 | 122 | 122 | 1240.7 | 0.010 | 0.0082 |
| silence only | 32.917 | 0 | 1 | 259.9 | 0.008 | n/a |
| silence only | 60.000 | 0 | 1 | 419.2 | 0.007 | n/a |
| silence only | 120.000 | 0 | 0 | 767.1 | 0.006 | 0.0000 |
| repeated content 2x | 65.835 | 244 | 244 | 1177.2 | 0.018 | 0.0082 |
| repeated content 3x | 98.752 | 366 | 366 | 1859.5 | 0.019 | 0.0082 |
| repeated content 4x | 131.669 | 488 | 366 | 2181.1 | 0.017 | 0.2561 |

### Conclusions

- Time-only is insufficient as the sole explanation, but audio duration clearly matters:
  - same text from 60s to 120s increased wall time from `772.1ms` to `1240.7ms`;
  - pure silence from 33s to 120s increased wall time from `259.9ms` to `767.1ms`.
- Text/content amount also matters:
  - repeated-content 2x/3x/4x had a higher duration-to-wall slope (`15.25ms/audio-sec`) than silence-padded same-text (`7.81ms/audio-sec`) or silence-only (`5.82ms/audio-sec`).
- The strongest product warning is quality, not speed:
  - the 131.669s / 488-character repeated-content case returned only 366 characters and CER/WER `0.2561`;
  - this means a fast final recompute can still be unusable if it silently drops the tail.
- Recommended segmentation policy remains hybrid:
  - hard audio-duration cap;
  - soft recognized/estimated text-length cap;
  - prefer silence/punctuation boundaries;
  - add queue/backlog pressure rules;
  - do not adopt a fixed 2-minute final-recompute segment without more natural-speech repeat evidence.

### Blockers / open questions

- These cases isolate compute behavior but are synthetic; they are not natural long-dictation UX evidence.
- Need repeat runs and natural long-speech cases before choosing hard product thresholds.
- Need investigate whether the 4x truncation is due to repeated synthetic content, generation/output limits, or a broader long-audio reliability boundary.

### Next recommended action

- Create a follow-up implementation spec for a hybrid segment budget controller only after one more validation pass with natural long speech.
- For now, treat the pilot as strong evidence against relying on either fixed time-only thresholds or text-length-only thresholds.

## 2026-06-26 — 2026-06-26-segmented-cache-asr-evaluation

### Summary

- Created a segmented-cache ASR evaluation feature contract.
- Added `eval/asr_streaming/segment_cache_eval.py` with:
  - `prepare`: generates segment WAVs, ASR case JSONL, and a segment manifest;
  - `analyze`: aggregates segment-level file-final results back to source-case plus strategy results.
- Ran two local Qwen3-ASR MLX 0.6B 8bit evaluation passes:
  - natural/local long-case matrix: 3 source cases, 4 strategies, 18 segment cases;
  - synthetic 244s stress case: 1 source case, 4 strategies, 23 segment cases.
- Updated `eval/asr_streaming/README.md` with repeatable segmented-cache commands.

### Files changed

- `eval/asr_streaming/segment_cache_eval.py`
- `eval/asr_streaming/README.md`
- `eval/asr_streaming/cases.segment_cache.local.jsonl`
- `eval/asr_streaming/cases.segment_cache.synthetic.local.jsonl`
- `eval/asr_streaming/audio/segment_cache/*`
- `eval/asr_streaming/audio/segment_cache_synthetic/*`
- `eval/asr_streaming/results/segment-cache/*`
- `eval/asr_streaming/results/segment-cache-synthetic/*`
- `eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626-pilot/*`
- `eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626-pilot-analysis/*`
- `eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626-matrix/*`
- `eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626-matrix-analysis/*`
- `eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626-synthetic/*`
- `eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626-synthetic-analysis/*`
- `specs/2026-06-26-segmented-cache-asr-evaluation/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/segment_cache_eval.py`
  Result: pass
  Notes: New segmented-cache evaluation script compiles.
- Command: `python3 eval/asr_streaming/segment_cache_eval.py prepare --dry-run --case-id existing_long_400_001 --strategy s45_c250_o0:45:250:0 --strategy s60_c250_o0:60:250:0`
  Result: pass
  Notes: Planned 4 segment cases from `existing_long_400_001`.
- Command: `python3 eval/asr_streaming/segment_cache_eval.py prepare`
  Result: pass
  Notes: Generated the natural/local matrix: 3 source cases, 4 strategies, 18 segment cases.
- Command: `python3 eval/asr_streaming/run_eval.py validate-cases --cases eval/asr_streaming/cases.segment_cache.local.jsonl`
  Result: pass
  Notes: Validated 18 generated segment cases.
- Command: `PYTHONPATH=.external/repos/mlx-audio .venv-mimo/bin/python eval/asr_streaming/run_eval.py run --adapter mlx-stt-local --model-id qwen3-asr-0.6b-mlx-8bit --mlx-stt-model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit --mlx-stt-language Chinese --cases eval/asr_streaming/cases.segment_cache.local.jsonl --out-dir eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626-matrix`
  Result: pass
  Notes: Ran Qwen3-ASR MLX over 18 natural/local segment cases.
- Command: `python3 eval/asr_streaming/segment_cache_eval.py analyze --manifest eval/asr_streaming/results/segment-cache/manifest.json --run-summary eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626-matrix/summary.json --out-dir eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626-matrix-analysis`
  Result: pass
  Notes: Wrote `analysis.json` and `analysis.md` for the natural/local matrix.
- Command: `python3 eval/asr_streaming/segment_cache_eval.py prepare --source-cases eval/asr_streaming/cases.long_synthetic.local.jsonl --case-id synthetic_repeat_180_001 --out-audio-dir eval/asr_streaming/audio/segment_cache_synthetic --out-cases eval/asr_streaming/cases.segment_cache.synthetic.local.jsonl --out-manifest eval/asr_streaming/results/segment-cache-synthetic/manifest.json`
  Result: pass
  Notes: Generated the 244s synthetic stress matrix: 1 source case, 4 strategies, 23 segment cases.
- Command: `python3 eval/asr_streaming/run_eval.py validate-cases --cases eval/asr_streaming/cases.segment_cache.synthetic.local.jsonl`
  Result: pass
  Notes: Validated 23 generated synthetic segment cases.
- Command: `PYTHONPATH=.external/repos/mlx-audio .venv-mimo/bin/python eval/asr_streaming/run_eval.py run --adapter mlx-stt-local --model-id qwen3-asr-0.6b-mlx-8bit --mlx-stt-model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit --mlx-stt-language Chinese --cases eval/asr_streaming/cases.segment_cache.synthetic.local.jsonl --out-dir eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626-synthetic`
  Result: pass
  Notes: Ran Qwen3-ASR MLX over 23 synthetic stress segment cases.
- Command: `python3 eval/asr_streaming/segment_cache_eval.py analyze --manifest eval/asr_streaming/results/segment-cache-synthetic/manifest.json --run-summary eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626-synthetic/summary.json --out-dir eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626-synthetic-analysis`
  Result: pass
  Notes: Wrote `analysis.json` and `analysis.md` for the synthetic stress matrix.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null && python3 -m json.tool specs/2026-06-26-segmented-cache-asr-evaluation/feature.json >/dev/null && python3 -m json.tool eval/asr_streaming/results/segment-cache/manifest.json >/dev/null && python3 -m json.tool eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626-matrix-analysis/analysis.json >/dev/null && python3 -m json.tool eval/asr_streaming/results/segment-cache-qwen3-mlx-0.6b-20260626-synthetic-analysis/analysis.json >/dev/null`
  Result: pass
  Notes: Key JSON artifacts are valid.
- Command: `git diff --check`
  Result: pass
  Notes: No whitespace errors.

### Natural/local matrix evidence

| Strategy | Cases | Max segments | Avg CER | Min coverage | Max final wait | Max backlog | Total model wall |
|---|---:|---:|---:|---:|---:|---:|---:|
| `s30_c150_o0` | 3 | 3 | 0.0143 | 1.000 | 396.2ms | 587.0ms | 3096.8ms |
| `s45_c250_o0` | 3 | 2 | 0.0174 | 1.000 | 771.7ms | 861.2ms | 2938.0ms |
| `s60_c250_o0` | 3 | 2 | 0.0164 | 1.000 | 765.5ms | 1170.8ms | 2912.0ms |
| `s90_c400_o0` | 3 | 1 | 0.0153 | 1.000 | 1583.7ms | 1583.7ms | 3001.8ms |

### Synthetic 244s stress evidence

| Strategy | Cases | Segments | CER | Coverage | Final wait | Max backlog | Total model wall |
|---|---:|---:|---:|---:|---:|---:|---:|
| `s30_c150_o0` | 1 | 9 | 0.0226 | 1.003 | 98.8ms | 596.6ms | 4344.4ms |
| `s45_c250_o0` | 1 | 6 | 0.0278 | 1.003 | 328.8ms | 804.1ms | 4259.4ms |
| `s60_c250_o0` | 1 | 5 | 0.0257 | 1.002 | 104.1ms | 1065.0ms | 4254.4ms |
| `s90_c400_o0` | 1 | 3 | 0.0257 | 1.004 | 1237.2ms | 1825.8ms | 4741.3ms |

### Conclusions

- The segmented-cache evaluation path is now reproducible and validated.
- On the current Qwen3-ASR MLX 0.6B 8bit local run, all tested zero-overlap strategies passed the first loose thresholds on these cases.
- Shorter segments reduced estimated user-stop final wait and backlog:
  - natural/local matrix favored `s30_c150_o0` on wait/backlog;
  - synthetic 244s stress also favored `s30_c150_o0` on wait/backlog.
- Larger segments reduced segment count but increased worst-case wait/backlog; this confirms why whole-session final recompute is structurally risky for very long dictation.
- This does not yet choose a product default:
  - `s30_c150_o0` may be operationally safer but may reduce context quality in less repetitive natural speech;
  - `s60_c250_o0` may be a reasonable ergonomic compromise;
  - more natural long-speech and repeat runs are needed before default thresholds.

### Blockers / open questions

- Segment text alignment in this harness is proportional and evaluation-only; production needs runtime boundary logic using partial text length, silence/VAD, punctuation, and backlog pressure.
- Non-zero overlap still needs deduplication or text alignment before production use.
- Need natural long-speech samples longer than 2-4 minutes to confirm thresholds under realistic pauses, corrections, and topic changes.

### Next recommended action

- Create a separate SDD feature for the service-side segmented-cache runtime:
  - durable local audio cache;
  - segment commit queue;
  - bounded final recompute;
  - merge/dedup policy;
  - cancellation and crash recovery;
  - local HTTP contract for App integration.

## 2026-06-26 — 2026-06-26-qwen3-mlx-segmented-cache-service

### Summary

- Created a segmented-cache service prototype contract.
- Added `eval/asr_streaming/qwen3_mlx_segmented_cache_service.py` with:
  - session token lifecycle;
  - timed PCM chunk ingestion;
  - durable local float32 audio cache plus session metadata;
  - user-visible `partial` and `final` events;
  - diagnostic `segment_final` events;
  - hard-duration and optional partial-text segment commit policy;
  - cancel and stale-token rejection;
  - fake backend, local WAV runner, and localhost HTTP server.
- Kept Swift App behavior unchanged.
- Added README commands for self-test, fake local WAV smoke, and fake HTTP incremental gate.

### Files changed

- `eval/asr_streaming/qwen3_mlx_segmented_cache_service.py`
- `eval/asr_streaming/README.md`
- `eval/asr_streaming/results/qwen3-mlx-segmented-cache-service-fake-smoke/*`
- `eval/asr_streaming/results/incremental-ux-gate-qwen3-segmented-cache-fake-smoke/*`
- `eval/asr_streaming/results/incremental-ux-gate-qwen3-segmented-cache-fake-smoke-realtime/*`
- `eval/asr_streaming/results/qwen3-mlx-segmented-cache-service-real-smoke/*`
- `eval/asr_streaming/results/qwen3-mlx-segmented-cache-service-spool/*`
- `specs/2026-06-26-qwen3-mlx-segmented-cache-service/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `python3 -m py_compile eval/asr_streaming/qwen3_mlx_segmented_cache_service.py`
  Result: pass
  Notes: New segmented-cache service script compiles.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null && python3 -m json.tool specs/2026-06-26-qwen3-mlx-segmented-cache-service/feature.json >/dev/null`
  Result: pass
  Notes: Feature matrix and feature metadata JSON are valid.
- Command: `python3 eval/asr_streaming/qwen3_mlx_segmented_cache_service.py self-test`
  Result: pass
  Notes: Covered hard-duration segment commit, local cache write, one final after finish, stale chunk rejection, and cancel leaking no accepted final.
- Command: `python3 eval/asr_streaming/qwen3_mlx_segmented_cache_service.py run --fake-backend --cases eval/asr_streaming/cases.smoke.local.jsonl --case-id zh_short_001 --max-segment-sec 1.5 --min-segment-sec 0.5 --out-dir eval/asr_streaming/results/qwen3-mlx-segmented-cache-service-fake-smoke`
  Result: pass
  Notes: Fake local WAV smoke passed; `zh_short_001` produced 5 segment commits, 8 partial events, 1 final event, and 402,772 cached bytes. Fake text repeats by design and is not accuracy evidence.
- Command: `python3 eval/asr_streaming/qwen3_mlx_segmented_cache_service.py serve --fake-backend --port 18096 --max-segment-sec 1.5 --min-segment-sec 0.5`
  Result: pass
  Notes: Fake localhost HTTP service started and returned metadata at `http://127.0.0.1:18096`.
- Command: `python3 eval/asr_streaming/incremental_ux_gate.py run --adapter http-json --service-url http://127.0.0.1:18096 --cases eval/asr_streaming/cases.smoke.local.jsonl --out-dir eval/asr_streaming/results/incremental-ux-gate-qwen3-segmented-cache-fake-smoke-realtime`
  Result: pass
  Notes: Realtime-paced HTTP gate passed; first partial 1025.0ms, final latency 50.0ms, no accepted stale/cancel leakage, no partial after final.
- Command: `python3 eval/asr_streaming/incremental_ux_gate.py run --adapter http-json --service-url http://127.0.0.1:18096 --cases eval/asr_streaming/cases.smoke.local.jsonl --no-realtime --out-dir eval/asr_streaming/results/incremental-ux-gate-qwen3-segmented-cache-fake-smoke`
  Result: expected fail
  Notes: No-realtime mode pushed 6.29s of audio in about 74ms, so audio-time partials appeared after the simulated stop timestamp. Documentation was updated to use realtime pacing for this gate.
- Command: `PYTHONPATH=.external/repos/mlx-audio .venv-mimo/bin/python eval/asr_streaming/qwen3_mlx_segmented_cache_service.py run --model-id qwen3-asr-0.6b-mlx-8bit --model .external/models/mlx-community__Qwen3-ASR-0.6B-8bit --cases eval/asr_streaming/cases.smoke.local.jsonl --case-id zh_short_001 --language Chinese --max-segment-sec 30 --min-segment-sec 5 --out-dir eval/asr_streaming/results/qwen3-mlx-segmented-cache-service-real-smoke`
  Result: pass
  Notes: Real Qwen3 MLX smoke passed; first usable partial 1146.1ms, final latency 133.1ms, CER 0.1053, WER 0.1053, coverage 0.9474. The model transcribed "语音输入" as "云输入" in this sample.
- Command: `lsof -nP -iTCP:18096 -sTCP:LISTEN || true`
  Result: pass
  Notes: No leftover HTTP service listener remained after validation.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null && python3 -m json.tool specs/2026-06-26-qwen3-mlx-segmented-cache-service/feature.json >/dev/null && python3 -m json.tool eval/asr_streaming/results/qwen3-mlx-segmented-cache-service-fake-smoke/summary.json >/dev/null && python3 -m json.tool eval/asr_streaming/results/incremental-ux-gate-qwen3-segmented-cache-fake-smoke-realtime/summary.json >/dev/null && python3 -m json.tool eval/asr_streaming/results/qwen3-mlx-segmented-cache-service-real-smoke/summary.json >/dev/null`
  Result: pass
  Notes: Key JSON artifacts are valid.
- Command: `git diff --check`
  Result: pass
  Notes: No whitespace errors.

### Blockers / open questions

- This prototype is not yet wired into the Swift App.
- Segment boundary policy is still simple; production should test silence/VAD, punctuation, backlog pressure, and more natural long speech before choosing defaults.
- Merge strategy is zero-overlap concatenation; overlap deduplication and crash-recovery UX remain follow-up work.
- Fake HTTP validation proves transport/session behavior, not ASR accuracy.

### Next recommended action

- Create a separate Swift integration spec for supervising this local HTTP service and validating App behavior end to end.
- In parallel, create a boundary-policy evaluation spec for VAD/punctuation/backlog-based segment commit and merge/dedup behavior on longer natural dictation.

## 2026-06-26 — 2026-06-26-qwen3-mlx-segmented-app-smoke

### Summary

- Created the segmented-cache App smoke SDD contract.
- Added `scripts/run_qwen3_mlx_segmented_app_smoke.sh`.
- The smoke runner starts `qwen3_mlx_segmented_cache_service.py serve`, waits for `/health`, then launches `LocalVoiceInputMac` with `--local-http-asr --asr-http-url <service-url>`.
- Added a Swift HTTP client test proving segmented service diagnostic events such as `segment_final` are ignored and only user-visible `partial/final` events enter App transcript state.
- Updated ASR README with dry-run and manual App smoke commands.
- Kept the default App backend unchanged as FunASR WebSocket.

### Files changed

- `scripts/run_qwen3_mlx_segmented_app_smoke.sh`
- `Tests/LocalVoiceInputMacTests/LocalHTTPASRClientTests.swift`
- `eval/asr_streaming/README.md`
- `specs/2026-06-26-qwen3-mlx-segmented-app-smoke/*`
- `specs/feature_matrix.json`
- `specs/progress.md`

### Validation

- Command: `bash -n scripts/run_qwen3_mlx_segmented_app_smoke.sh && DRY_RUN=1 bash scripts/run_qwen3_mlx_segmented_app_smoke.sh`
  Result: pass
  Notes: Script syntax passed. Dry-run printed runtime status, service command, App command, service URL, spool dir, and output dir without launching the service or App.
- Command: `python3 -m py_compile eval/asr_streaming/qwen3_mlx_segmented_cache_service.py`
  Result: pass
  Notes: Segmented-cache service script still compiles.
- Command: `python3 -m json.tool specs/feature_matrix.json >/dev/null && python3 -m json.tool specs/2026-06-26-qwen3-mlx-segmented-app-smoke/feature.json >/dev/null`
  Result: pass
  Notes: Feature matrix and new feature metadata JSON are valid.
- Command: `swift build`
  Result: pass
  Notes: App and package build passed.
- Command: `swift test`
  Result: pass
  Notes: 52 tests passed with 0 failures. New test: `LocalHTTPASRClientTests.testIgnoresSegmentDiagnosticsAndEmitsVisibleEventsOnly`.
- Command: `git diff --check`
  Result: pass
  Notes: No whitespace errors.

### Manual smoke status

- Manual UI smoke was not run in this automated implementation pass.
- The next manual command is:

```bash
bash scripts/run_qwen3_mlx_segmented_app_smoke.sh
```

- The script will open the App against `http://127.0.0.1:18096` and write logs under `eval/asr_streaming/results/qwen3-mlx-segmented-app-smoke-*`.

### Blockers / open questions

- This path is ready for user-run manual smoke, but it is not yet default-backend ready.
- App-managed service startup, health supervision, restart, fallback, and cleanup are still out of scope.
- Real macOS validation is still required for Notes paste, browser input paste, no-input clipboard fallback, Esc cancel, Option+Space long draft, and focus-change downgrade.

### Next recommended action

- Run `bash scripts/run_qwen3_mlx_segmented_app_smoke.sh` and perform the manual smoke checklist from `specs/2026-06-26-qwen3-mlx-segmented-app-smoke/validation.md`.
- After manual smoke, decide whether the next feature should be App-managed service supervision or segment boundary/dedup tuning.
