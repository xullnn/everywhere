#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PARTS="${PARTS:-24}"
MODEL_ROOT="${MODEL_ROOT:-.external/models}"
OFFLINE_DIR="$MODEL_ROOT/paraformer-offline-small"
ONLINE_DIR="$MODEL_ROOT/paraformer-online-small"
VAD_DIR="$MODEL_ROOT/fsmn-vad"

mkdir -p "$OFFLINE_DIR/fig" "$OFFLINE_DIR/example" "$ONLINE_DIR/fig" "$ONLINE_DIR/example" "$VAD_DIR/fig" "$VAD_DIR/example"

file_size() {
  if [ -f "$1" ]; then
    wc -c < "$1" | tr -d '[:space:]'
  else
    echo 0
  fi
}

download_simple() {
  local url="$1"
  local dest="$2"
  local expected_size="${3:-}"

  if [ -f "$dest" ]; then
    if [ -n "$expected_size" ] && [ "$(file_size "$dest")" = "$expected_size" ]; then
      echo "exists $dest"
      return
    fi
    if [ -z "$expected_size" ] && [ "$(file_size "$dest")" != "0" ]; then
      echo "exists $dest"
      return
    fi
  fi

  mkdir -p "$(dirname "$dest")"
  echo "download $dest"
  curl -fL --retry 5 --retry-all-errors --connect-timeout 20 --speed-time 30 --speed-limit 1024 "$url" -o "$dest.tmp"

  if [ -n "$expected_size" ]; then
    local actual_size
    actual_size="$(file_size "$dest.tmp")"
    if [ "$actual_size" != "$expected_size" ]; then
      rm -f "$dest.tmp"
      echo "size mismatch for $dest: expected $expected_size, got $actual_size" >&2
      exit 1
    fi
  fi

  mv "$dest.tmp" "$dest"
}

download_parallel() {
  local url="$1"
  local dest="$2"
  local expected_size="$3"
  local parts="${4:-$PARTS}"

  if [ "$(file_size "$dest")" = "$expected_size" ]; then
    echo "exists $dest"
    return
  fi

  mkdir -p "$(dirname "$dest")"
  local tmp_dir="$dest.parts"
  rm -f "$dest.tmp"
  mkdir -p "$tmp_dir"

  local chunk_size=$(( (expected_size + parts - 1) / parts ))
  echo "parallel download $dest ($expected_size bytes, $parts parts)"

  export url tmp_dir expected_size chunk_size
  seq 0 $((parts - 1)) | xargs -I {} -P "$parts" bash -c '
    set -euo pipefail
    index="$1"
    start=$((index * chunk_size))
    end=$((start + chunk_size - 1))
    if [ "$end" -ge "$expected_size" ]; then
      end=$((expected_size - 1))
    fi
    part_path="$tmp_dir/part-$(printf "%04d" "$index")"
    if [ "$start" -le "$end" ]; then
      expected_part_size=$((end - start + 1))
      current_size=0
      if [ -f "$part_path" ]; then
        current_size="$(wc -c < "$part_path" | tr -d "[:space:]")"
      fi
      if [ "$current_size" = "$expected_part_size" ]; then
        exit 0
      fi

      attempt=1
      while [ "$attempt" -le 8 ]; do
        rm -f "$part_path"
        if curl -fsSL --retry 5 --retry-all-errors --connect-timeout 20 --speed-time 30 --speed-limit 1024 -r "${start}-${end}" "$url" -o "$part_path"; then
          current_size="$(wc -c < "$part_path" | tr -d "[:space:]")"
          if [ "$current_size" = "$expected_part_size" ]; then
            exit 0
          fi
        fi
        attempt=$((attempt + 1))
        sleep "$attempt"
      done
      current_size=0
      if [ -f "$part_path" ]; then
        current_size="$(wc -c < "$part_path" | tr -d "[:space:]")"
      fi
      echo "failed part $index for $url: expected $expected_part_size, got $current_size" >&2
      exit 1
    else
      : > "$part_path"
    fi
  ' bash {}

  for part in "$tmp_dir"/part-*; do
    cat "$part" >> "$dest.tmp"
  done

  local actual_size
  actual_size="$(file_size "$dest.tmp")"
  if [ "$actual_size" != "$expected_size" ]; then
    rm -rf "$tmp_dir" "$dest.tmp"
    echo "size mismatch for $dest: expected $expected_size, got $actual_size" >&2
    exit 1
  fi

  mv "$dest.tmp" "$dest"
  rm -rf "$tmp_dir"
}

download_modelscope_offline() {
  local repo="damo/speech_paraformer_asr_nat-zh-cn-16k-common-vocab8358-tensorflow1"
  local revision="v2.0.4"
  local resolve_base="https://modelscope.cn/models/$repo/resolve/$revision"
  local model_url="https://www.modelscope.cn/api/v1/models/$repo/repo?Revision=$revision&FilePath=model.pt"

  download_simple "$resolve_base/am.mvn" "$OFFLINE_DIR/am.mvn"
  download_simple "$resolve_base/config.yaml" "$OFFLINE_DIR/config.yaml"
  download_simple "$resolve_base/configuration.json" "$OFFLINE_DIR/configuration.json"
  download_simple "$resolve_base/README.md" "$OFFLINE_DIR/README.md"
  download_simple "$resolve_base/tokens.json" "$OFFLINE_DIR/tokens.json"
  download_simple "$resolve_base/example/asr_example.wav" "$OFFLINE_DIR/example/asr_example.wav"
  download_simple "$resolve_base/fig/struct.png" "$OFFLINE_DIR/fig/struct.png"
  download_simple "$resolve_base/fig/error_type.png" "$OFFLINE_DIR/fig/error_type.png"
  download_parallel "$resolve_base/seg_dict" "$OFFLINE_DIR/seg_dict" 8347725 16
  download_parallel "$model_url" "$OFFLINE_DIR/model.pt" 284469859 "$PARTS"
}

download_huggingface_online() {
  local repo="alextomcat/speech_paraformer_asr_nat-zh-cn-16k-common-vocab8404-online-pytorch"
  local resolve_base="https://huggingface.co/$repo/resolve/main"

  download_simple "$resolve_base/am.mvn" "$ONLINE_DIR/am.mvn"
  download_simple "$resolve_base/config.yaml" "$ONLINE_DIR/config.yaml"
  download_simple "$resolve_base/configuration.json" "$ONLINE_DIR/configuration.json"
  download_simple "$resolve_base/README.md" "$ONLINE_DIR/README.md"
  download_simple "$resolve_base/tokens.json" "$ONLINE_DIR/tokens.json"
  download_simple "$resolve_base/example/asr_example.wav" "$ONLINE_DIR/example/asr_example.wav"
  download_simple "$resolve_base/fig/struct.png" "$ONLINE_DIR/fig/struct.png"
  download_parallel "$resolve_base/seg_dict" "$ONLINE_DIR/seg_dict" 8287834 8
  download_parallel "$resolve_base/model.pt" "$ONLINE_DIR/model.pt" 284585251 "$PARTS"
}

download_huggingface_vad() {
  local repo="funasr/fsmn-vad"
  local resolve_base="https://huggingface.co/$repo/resolve/main"

  download_simple "$resolve_base/am.mvn" "$VAD_DIR/am.mvn"
  download_simple "$resolve_base/config.yaml" "$VAD_DIR/config.yaml"
  download_simple "$resolve_base/configuration.json" "$VAD_DIR/configuration.json"
  download_simple "$resolve_base/README.md" "$VAD_DIR/README.md"
  download_simple "$resolve_base/example/vad_example.wav" "$VAD_DIR/example/vad_example.wav"
  download_simple "$resolve_base/fig/struct.png" "$VAD_DIR/fig/struct.png"
  download_simple "$resolve_base/model.pt" "$VAD_DIR/model.pt"
}

download_modelscope_offline
download_huggingface_online
download_huggingface_vad

echo "FunASR smoke models ready:"
echo "  offline: $OFFLINE_DIR"
echo "  online:  $ONLINE_DIR"
echo "  vad:     $VAD_DIR"
