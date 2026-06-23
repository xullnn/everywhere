# FunASR Local Runtime

Local FunASR validation should avoid depending on ad hoc first-run downloads during product testing.

Durable operating pattern:

- Use Python 3.10 or 3.11 for the FunASR runtime.
- Cache known smoke-test model directories under `.external/models/` before starting the server.
- Prefer local model paths in the websocket server command when those directories exist.
- Keep punctuation and speaker verification optional for first-pass validation; they can add downloads and latency without being required to prove microphone-to-text routing.
- Treat `is_speaking=false` as a required offline flush trigger. The macOS app sends it after all pending PCM has been flushed, so the server must not wait for another binary audio frame before running offline ASR.
- Use `eval/asr_streaming/run_eval.py` for repeatable backend tests: it streams local 16 kHz mono int16 WAV files to the FunASR WebSocket endpoint and records partial/final events, latency, realtime factor, CER, and WER.
- Use `scripts/record_asr_cases.sh` to create the local pilot recordings before backend comparison; it wraps the case template, file naming, and 16 kHz mono int16 WAV capture.
- Use `scripts/download_fun_asr_nano.sh` for Fun-ASR-Nano-2512 acquisition; it separates metadata preparation, resumable weight download, checksum validation, and ModelScope cache registration.
- Use `scripts/run_fun_asr_nano_smoke.sh` for the Nano smoke path after download. The default path is local file-level inference against the existing WAV cases, not realtime app integration.
- For Fun-ASR-Nano with FunASR 1.3.1, default VAD off. The `fsmn-vad` model can load, but the runtime's VAD merge path fails when combining VAD segments with Nano result dictionaries.
- When the Nano model repository does not include `model.py`, use the installed `funasr.models.fun_asr_nano.model.py` as the local `remote_code` path.
- Treat Fun-ASR-Nano pilot results as model-selection evidence: it is faster and more accurate than the current Paraformer pilot baseline on the local file-level cases, while technical/product terms and realtime partial behavior still require follow-up before app integration.

Operational note:

- A short-lived agent shell may clean up background child processes. For sustained manual testing, run the FunASR server from a user terminal session or install a LaunchAgent.
