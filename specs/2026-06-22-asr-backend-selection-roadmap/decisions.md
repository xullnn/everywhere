# Decisions - ASR Backend Selection Roadmap

## Confirmed Decisions

- D1: The roadmap defines perceived realtime as incremental UX, not strict word-by-word native streaming.
- D2: Backend selection must output four categories: partial backend, final backend, fallback backend, and reference-only models.
- D3: `incremental_ux_gate.py` is the target canonical gate, but current fake-only status is not sufficient for real model comparison.
- D4: `qwen3_mlx_cumulative_service.py` remains prototype evidence and must not become a second canonical gate.
- D5: Real backend transport adapters are required before real model comparisons can be called canonical.
- D6: CER/WER must be hard quality dimensions; length coverage alone is insufficient.
- D7: Compute RTF must be measured separately from realtime latency because realtime sleep makes realtime-mode RTF misleading.
- D8: First partial latency is currently a soft signal or must be measured relative to minimum audio window; a universal `<= 1.5s` hard fail would conflict with Qwen3 cumulative recompute evidence.
- D9: Qwen3-ASR MLX 0.6B is the first preferred partial candidate, but only after a real local service boundary passes the canonical gate.
- D10: Qwen3-ASR MLX 1.7B and MiMo-V2.5-ASR MLX are final/long-draft candidates, not default partial candidates.
- D11: FunASR 2pass remains fallback/baseline until a replacement proves better quality, runtime behavior, and fallback safety.
- D12: Swift app integration is out of scope until backend service behavior, real audio/control flow, and existing app safety invariants are validated.
- D13: The roadmap goal is the full model evaluation program: all candidate models, all required test types, all required metrics, and all final role decisions. A single phase goal or one backend prototype does not satisfy this roadmap.
- D14: The first executable implementation step is to add real localhost backend transport support to the canonical `incremental_ux_gate.py`; real model partial-backend comparisons are not canonical while that gate remains fake-adapter-only.
- D15: Test applicability is role-based. Reference-only models require file-level evidence and explicit skipped-test rationale, not forced realtime/session/process-boundary work.
- D16: `qwen3-asr-0.6b`, `qwen3-asr-1.7b`, and `fun-asr-nano-2512` are no longer orphaned in the roadmap; they start as reference-only or baseline candidates unless later evidence upgrades them.

## Threshold Decisions

- T1: Short push-to-talk final latency hard threshold starts at `<= 2.5s`.
- T2: Long draft final latency hard threshold starts at `<= 8s`.
- T3: `final_coverage_ratio >= 0.70` is a truncation guard only.
- T4: Partial backend compute RTF target is `<= 1.0` in non-realtime mode.
- T5: First partial latency, cadence, and rewrite rate remain soft until real backend data calibrates mode-specific thresholds.
- T6: RSS hard thresholds are required before app integration but remain unresolved until Qwen/MiMo steady-state measurements are collected.
- T7: CER/WER are hard quality dimensions, but exact mode-specific thresholds remain unresolved until the implementation feature calibrates them on local recordings.

## Initial Role Tier For Standalone Candidates

- `qwen3-asr-0.6b-mlx-8bit`: first-priority partial backend candidate only after real service/process-boundary validation; also a possible final fallback if larger models fail constraints.
- `qwen3-asr-1.7b-mlx-8bit`: final/long-draft candidate; not a default partial candidate unless it independently passes partial-role gates.
- `mimo-v2.5-asr`: final-only and coarse-incremental candidate; reference-only if memory or latency fail.
- `paraformer-current-funasr-ws`: baseline and fallback candidate.
- `qwen3-asr-0.6b`: reference-only/file-level baseline by default because the official local streaming path depends on vLLM/CUDA and is not proven feasible on the M4 target.
- `qwen3-asr-1.7b`: reference-only/file-level baseline by default for the same vLLM/CUDA feasibility reason.
- `fun-asr-nano-2512`: reference-only/file-level baseline by default; do not conflate it with the existing FunASR 2pass fallback.
- `fun-asr-nano-2512-mlx-4bit`: reference-only by default because current evidence flags severe long-form quality risk and no proven session API.
- `glm-asr-nano-2512`: reference-only by default unless later evidence proves canonical gate and quality threshold pass.
- `firered-asr2s`: reference-only by default unless later evidence proves canonical gate and quality threshold pass.
- `nemotron-3.5-asr-streaming-0.6b-mlx-8bit`: reference-only by default because local evidence shows cache-aware file streaming without session API and weak Chinese/technical-term quality.
- `mimo-audio-tokenizer-mlx`: support artifact only; never a standalone ASR candidate.

## Open Questions / Unresolved Choices

- Q1: What exact CER/WER hard thresholds should apply to short push-to-talk, long draft, and technical-term cases after more real recordings are available?
- Q2: What RSS hard limit is acceptable for a background partial service on a 48GB M4 Mac while other work apps are open?
- Q3: Should Qwen3-ASR MLX 1.7B be a final backend, long-draft backend, or reference-only after real service measurements?
- Q4: Can MiMo-V2.5-ASR MLX meet final-only latency and RSS thresholds, or should it remain reference-only?
- Q5: Should FunASR remain permanent fallback even after a new default backend is selected?

## Claude Review Incorporated

- The Opus review identified four corrections now incorporated:
  - The existing incremental UX gate is fake-only and needs real backend transport adapters.
  - The proposed first partial `<= 1.5s` hard threshold conflicts with Qwen3 cumulative recompute evidence.
  - `final_coverage_ratio` is a length ratio, not a quality metric.
  - RTF in realtime pacing mode is misleading and must be separated from compute RTF.
