# Current Focus

Current phase: hardening the reviewed MVP and preparing a real local ASR backend integration spike after repeatable local-recording evaluation.

Stable status:

- Build and core tests pass on the local Mac with full Xcode selected.
- Mock ASR mode validates the app shell, global hotkey path, focus routing, Notes auto-paste, no-input clipboard draft behavior, paste verification, and clipboard restoration.
- The packaged app is now signed with a stable Apple Development identity instead of ad-hoc signing, so macOS TCC permissions should remain stable across rebuilds as long as bundle id and signing identity remain unchanged.
- Local FunASR smoke-test models are cached under `.external/models/` for offline ASR, online ASR, and VAD so first-run validation does not depend on the slow default ModelScope downloader path.
- The local FunASR websocket runtime is patched so a final `is_speaking=false` message flushes remaining PCM through offline ASR instead of producing only online partials.
- The independent ASR eval harness, recording CLI, realtime streaming gate, Qwen3 MLX realtime probe, and Qwen3 MLX cumulative recompute probe are the gate for backend selection. File-level final transcription quality is tracked separately from microphone-style realtime behavior.
- Qwen3-ASR MLX has local file/token streaming, but the loaded 0.6B and 1.7B MLX models do not expose a session-style `feed/step/close` API. Qwen3-ASR MLX 0.6B cumulative recompute has passed the in-process service prototype gate, the local HTTP process-boundary gate, the extended resource gate, and the first Swift-side local HTTP client validation. It is still not native realtime streaming and still needs service supervision, formal resource thresholds, real app smoke testing, and code-switch accuracy handling before becoming the default app backend. The first segmented-cache evaluation shows long dictation should move away from whole-session cumulative final recompute toward bounded segment finalization with durable local audio cache and hybrid budget controls. Nemotron MLX also lacks a local session API despite model-level streaming terminology. MiMo-V2.5-ASR MLX remains an offline-quality reference unless a chunked or streaming API is proven.
- Local model cache has been pruned to the current working set: Qwen3-ASR MLX 0.6B/1.7B, MiMo-V2.5-ASR MLX plus tokenizer, and the FunASR Paraformer/VAD baseline. Non-mainline historical model caches and transfer duplicates should be re-downloaded only when rerunning old experiments.

Immediate next focus:

- Run a real app smoke against the local Qwen3-ASR MLX HTTP service while preserving the existing macOS safety contract: Right Option, Option+Space, Esc cancel, focus-change downgrade, secure-field clipboard fallback, and no partial insertion into the active app.
- Define the service supervision and production runtime policy for the local Qwen3 HTTP service, including startup, health checks, timeout/fallback behavior, resource thresholds, and service-side segmented-cache behavior for long dictation.

Current operational caution:

- Prefer Python 3.10 or 3.11 for the FunASR runtime.
- Real ASR setup may download models on first run; after model cache is available, operation should remain local/offline.
- Running the FunASR websocket service as a durable background process may require a user terminal session or a LaunchAgent; short-lived agent shell sessions can clean up child server processes.
- File-level model evaluation and token streaming over an already materialized audio buffer do not prove realtime partial behavior, floating-panel latency, or streaming session semantics; a backend must produce pre-stop partials and post-stop final/offline output under timed PCM chunk input to qualify as realtime.
- Cumulative recompute over accumulated prefixes can inform wrapper feasibility, but it needs service-level scheduling, cancellation, stale-result isolation, and an equivalent timed-PCM gate before app integration.
- Whole-session cumulative final recompute is not the right long-dictation endpoint. Use segmented-cache evaluation evidence as the starting point for a service design with bounded segment finalization, durable local audio cache, merge/dedup rules, and backlog pressure controls.
- The Qwen3 HTTP service boundary and Swift client validate the local IPC shape for the cumulative wrapper, but not process supervision, app lifecycle management, memory ceilings, or real user-facing macOS smoke behavior.
- The Qwen3 MLX service should keep model load and inference on the same thread; `ThreadingHTTPServer` triggered MLX's thread-local GPU stream error during validation.
- The Qwen3 cumulative wrapper should reset service worker timing on every new session start; otherwise session-relative gate runs can inherit prior-session delay and falsely miss pre-stop partial gates.
- The first extended Qwen3 HTTP resource run observed roughly 1.4 GB peak RSS for the Python service. Treat this as initial evidence, not a formal product threshold.
- AMD can work as a large-model download/cache transfer host via foreground PowerShell snapshot commands and `scp`, but unattended Windows OpenSSH background downloads remain unreliable.
- Treat `eval/asr_streaming/model_inventory.md` as the operational source of truth for local ASR model cache paths and cleanup status.
