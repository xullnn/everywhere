#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  download_hf_snapshot.sh --repo REPO_ID [--revision main] [--base-url URL] [--dest-root DIR]

Example:
  bash eval/asr_streaming/download_hf_snapshot.sh \
    --repo mlx-community/Qwen3-ASR-0.6B-8bit \
    --base-url https://huggingface.co \
    --dest-root .external/models
USAGE
}

repo_id=""
revision="main"
base_url="https://huggingface.co"
dest_root=".external/models"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      repo_id="${2:-}"
      shift 2
      ;;
    --revision)
      revision="${2:-}"
      shift 2
      ;;
    --base-url)
      base_url="${2:-}"
      shift 2
      ;;
    --dest-root)
      dest_root="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$repo_id" ]]; then
  echo "--repo is required" >&2
  usage >&2
  exit 2
fi

safe_repo="${repo_id//\//__}"
dest="$dest_root/$safe_repo"
marker_dir="$dest/.download_complete"
api_url="${base_url%/}/api/models/$repo_id/revision/$revision"
info_path="$dest/_snapshot_info.json"

mkdir -p "$dest" "$marker_dir"

echo "repo     $repo_id"
echo "revision $revision"
echo "base     ${base_url%/}"
echo "dest     $dest"
echo "api      $api_url"

curl -L --fail --retry 20 --retry-delay 5 --connect-timeout 30 -o "$info_path" "$api_url"

python3 - "$info_path" <<'PY' > "$dest/_snapshot_files.txt"
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = json.load(f)
for sibling in data.get("siblings", []):
    name = sibling.get("rfilename")
    if name:
        print(name)
PY

escape_path() {
  python3 - "$1" <<'PY'
import sys
from urllib.parse import quote

print("/".join(quote(part) for part in sys.argv[1].split("/")))
PY
}

marker_name() {
  python3 - "$1" <<'PY'
import hashlib
import sys

print(hashlib.sha256(sys.argv[1].encode("utf-8")).hexdigest())
PY
}

while IFS= read -r file; do
  [[ -n "$file" ]] || continue
  escaped_file="$(escape_path "$file")"
  marker="$marker_dir/$(marker_name "$file")"
  target="$dest/$file"
  target_dir="$(dirname "$target")"
  url="${base_url%/}/$repo_id/resolve/$revision/$escaped_file"
  resume="false"

  case "$file" in
    *.safetensors|*.bin|*.pt|*.pth|*.tar|*.zip)
      resume="true"
      ;;
  esac

  if [[ -f "$marker" ]]; then
    echo "skip     $target"
    continue
  fi

  mkdir -p "$target_dir"
  if [[ "$resume" != "true" && -f "$target" ]]; then
    rm -f "$target"
  fi

  echo "download $url"
  echo "target   $target"
  echo "resume   $resume"

  if [[ "$resume" == "true" && -f "$target" ]]; then
    curl -L --fail --retry 20 --retry-delay 5 --connect-timeout 30 -C - -o "$target" "$url"
  else
    curl -L --fail --retry 20 --retry-delay 5 --connect-timeout 30 -o "$target" "$url"
  fi

  printf 'complete\n' > "$marker"
done < "$dest/_snapshot_files.txt"

python3 - "$dest" <<'PY'
import os
import sys

root = sys.argv[1]
total = 0
files = 0
for base, _, names in os.walk(root):
    if os.path.basename(base) == ".download_complete":
        continue
    for name in names:
        path = os.path.join(base, name)
        try:
            total += os.path.getsize(path)
            files += 1
        except OSError:
            pass
print(f"completed {root}")
print(f"files    {files}")
print(f"bytes    {total}")
print(f"gib      {total / 1024 / 1024 / 1024:.3f}")
PY
