#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -d ".venv" ]; then
  echo "Missing .venv. Run scripts/setup_funasr_venv.sh first." >&2
  exit 1
fi
source .venv/bin/activate
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
WEBSOCKET_DIR=".external/FunASR/runtime/python/websocket"
SERVER_PY="$WEBSOCKET_DIR/funasr_wss_server.py"

mkdir -p "$WEBSOCKET_DIR"
if [ ! -f "$SERVER_PY" ]; then
  curl -fL "https://raw.githubusercontent.com/modelscope/FunASR/main/runtime/python/websocket/funasr_wss_server.py" -o "$SERVER_PY"
fi
if [ ! -f "$WEBSOCKET_DIR/requirements_server.txt" ]; then
  curl -fL "https://raw.githubusercontent.com/modelscope/FunASR/main/runtime/python/websocket/requirements_server.txt" -o "$WEBSOCKET_DIR/requirements_server.txt"
fi

python -m pip install --no-cache-dir -i "$PIP_INDEX_URL" -r "$WEBSOCKET_DIR/requirements_server.txt"

FUNASR_HOST="${FUNASR_HOST:-127.0.0.1}"
FUNASR_PORT="${FUNASR_PORT:-10095}"
FUNASR_DEVICE="${FUNASR_DEVICE:-cpu}"
FUNASR_NGPU="${FUNASR_NGPU:-0}"
FUNASR_NCPU="${FUNASR_NCPU:-8}"

LOCAL_OFFLINE_MODEL=".external/models/paraformer-offline-small"
LOCAL_ONLINE_MODEL=".external/models/paraformer-online-small"
LOCAL_VAD_MODEL=".external/models/fsmn-vad"
if [ -f "$LOCAL_OFFLINE_MODEL/model.pt" ]; then
  DEFAULT_ASR_MODEL="$LOCAL_OFFLINE_MODEL"
else
  DEFAULT_ASR_MODEL="damo/speech_paraformer_asr_nat-zh-cn-16k-common-vocab8358-tensorflow1"
fi
if [ -f "$LOCAL_ONLINE_MODEL/model.pt" ]; then
  DEFAULT_ASR_MODEL_ONLINE="$LOCAL_ONLINE_MODEL"
else
  DEFAULT_ASR_MODEL_ONLINE="damo/speech_paraformer_asr_nat-zh-cn-16k-common-vocab8404-online"
fi
if [ -f "$LOCAL_VAD_MODEL/model.pt" ]; then
  DEFAULT_VAD_MODEL="$LOCAL_VAD_MODEL"
else
  DEFAULT_VAD_MODEL="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
fi

# Defaults are intentionally smaller than FunASR large models so first-run local validation is practical.
FUNASR_ASR_MODEL="${FUNASR_ASR_MODEL:-$DEFAULT_ASR_MODEL}"
FUNASR_ASR_MODEL_REVISION="${FUNASR_ASR_MODEL_REVISION:-v2.0.4}"
FUNASR_ASR_MODEL_ONLINE="${FUNASR_ASR_MODEL_ONLINE:-$DEFAULT_ASR_MODEL_ONLINE}"
FUNASR_ASR_MODEL_ONLINE_REVISION="${FUNASR_ASR_MODEL_ONLINE_REVISION:-v2.0.4}"
FUNASR_VAD_MODEL="${FUNASR_VAD_MODEL:-$DEFAULT_VAD_MODEL}"
FUNASR_VAD_MODEL_REVISION="${FUNASR_VAD_MODEL_REVISION:-v2.0.4}"
FUNASR_PUNC_MODEL="${FUNASR_PUNC_MODEL:-}"
FUNASR_PUNC_MODEL_REVISION="${FUNASR_PUNC_MODEL_REVISION:-v2.0.4}"
FUNASR_SV_MODEL="${FUNASR_SV_MODEL:-}"
FUNASR_SV_MODEL_REVISION="${FUNASR_SV_MODEL_REVISION:-v2.0.4}"

echo "Starting FunASR websocket server on ws://$FUNASR_HOST:$FUNASR_PORT"
echo "offline=$FUNASR_ASR_MODEL"
echo "online=$FUNASR_ASR_MODEL_ONLINE"

exec python "$SERVER_PY" \
  --host "$FUNASR_HOST" \
  --port "$FUNASR_PORT" \
  --certfile "" \
  --keyfile "" \
  --device "$FUNASR_DEVICE" \
  --ngpu "$FUNASR_NGPU" \
  --ncpu "$FUNASR_NCPU" \
  --asr_model "$FUNASR_ASR_MODEL" \
  --asr_model_revision "$FUNASR_ASR_MODEL_REVISION" \
  --asr_model_online "$FUNASR_ASR_MODEL_ONLINE" \
  --asr_model_online_revision "$FUNASR_ASR_MODEL_ONLINE_REVISION" \
  --vad_model "$FUNASR_VAD_MODEL" \
  --vad_model_revision "$FUNASR_VAD_MODEL_REVISION" \
  --punc_model "$FUNASR_PUNC_MODEL" \
  --punc_model_revision "$FUNASR_PUNC_MODEL_REVISION" \
  --sv_model "$FUNASR_SV_MODEL" \
  --sv_model_revision "$FUNASR_SV_MODEL_REVISION"
