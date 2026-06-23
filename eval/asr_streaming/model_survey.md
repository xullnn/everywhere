# ASR Model Survey For Local Backend Testing

This file separates public evidence from local validation.

## Current baseline

- `paraformer-current-funasr-ws`
- Local cached files:
  - online Paraformer `model.pt`: about 271 MB
  - offline Paraformer `model.pt`: about 271 MB
  - FSMN VAD `model.pt`: about 1.6 MB
- Status: runnable through the existing local FunASR WebSocket server.

## Public Evidence And Local Status

| Model | Public benchmark evidence | Local validation status |
|---|---|---|
| Fun-ASR-Nano-2512 | Official report includes open-source/industry WER, streaming decoding, noise, code-switching, and hotword customization. | Locally evaluated as a file-level comparison path. Not selected as the first partial/final backend. |
| Qwen3-ASR-0.6B / 1.7B | Official report includes public benchmark and streaming tables, including LibriSpeech, FLEURS-en, and FLEURS-zh streaming results. | Qwen3-ASR MLX 0.6B is the current first integration candidate through a validated cumulative-wrapper HTTP boundary. 1.7B remains a comparison/final-quality candidate. |
| MiMo-V2.5-ASR | Xiaomi page lists AISHELL-2, FLEURS-Zh, Wenet Meeting/Net, CommonVoice-Zh, English leaderboard, dialect, lyrics, and code-switch results. | Locally evaluated with strong file-level quality. Kept as offline quality reference unless a chunk/session path is proven. |
| FireRedASR2S | Paper page reports public Mandarin, dialect/accent, English, VAD, LID, and punctuation benchmarks. | Locally evaluated. Not selected for the near-term Mac MVP integration path. |
| GLM-ASR-Nano-2512 | Public deployment recipe and model page describe Chinese, English, dialect, and benchmark claims. | Locally evaluated. Not selected over Qwen3 MLX for the current incremental UX path. |
| Nemotron 3.5 ASR Streaming 0.6B MLX | Model name and implementation expose streaming-oriented surfaces. | Locally probed. Not selected: no validated session-style PCM API and weak Chinese/technical-term evidence on current local cases. |

## Why local testing is still required

Public scores are useful for shortlisting, but LocalVoiceInput must validate:

- MacBook Pro M4 runtime feasibility.
- First partial latency.
- Final latency after user stop.
- Streaming partial stability.
- Robustness on user-specific dictation style.
- Technical terms and hotwords used by this project.
- Whether the backend can integrate without uploading audio or text.

## First local benchmark set

Start with 30-100 local recordings:

- short Mandarin dictation
- long draft dictation
- Chinese-English code switching
- technical terms
- app and model names
- low voice / fast speech / noisy room
- known failure cases from real use

## Current Inventory

See `model_inventory.md` for the current local model/cache paths, approximate sizes, keep/drop decisions, and cleanup notes.
