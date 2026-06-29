#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

SERVICE_URL="${SERVICE_URL:-${ASR_HTTP_URL:-http://127.0.0.1:18105}}"
CONFIG_PATH="${CONFIG_PATH:-$HOME/Library/Application Support/LocalVoiceInput/config.json}"
PYTHON_BIN="${PYTHON_BIN:-.venv-mimo/bin/python}"
MODEL="${MODEL:-.external/models/mlx-community__Qwen3-ASR-0.6B-8bit}"
MLX_AUDIO_SOURCE="${MLX_AUDIO_SOURCE:-.external/repos/mlx-audio}"
HTTP_TIMEOUT="${HTTP_TIMEOUT:-2}"
STRICT="${STRICT:-0}"

overall=0

section() {
  printf '\n== %s ==\n' "$1"
}

mark_problem() {
  overall=1
}

print_path_status() {
  local label="$1"
  local path="$2"
  local kind="$3"
  if [ "$kind" = "exec" ]; then
    if [ -x "$path" ]; then
      printf '%s: ok %s\n' "$label" "$path"
    else
      printf '%s: missing/not executable %s\n' "$label" "$path"
      mark_problem
    fi
  elif [ -d "$path" ]; then
    printf '%s: ok %s\n' "$label" "$path"
  else
    printf '%s: missing %s\n' "$label" "$path"
    mark_problem
  fi
}

print_processes() {
  local label="$1"
  local pattern="$2"
  local lines
  lines="$(pgrep -fl "$pattern" || true)"
  if [ -z "$lines" ]; then
    printf '%s: not running\n' "$label"
    mark_problem
    return
  fi
  printf '%s: running\n' "$label"
  printf '%s\n' "$lines" | sed 's/^/  /'
}

section "Project"
printf 'cwd: %s\n' "$PWD"
if command -v git >/dev/null 2>&1; then
  git status --short --branch | sed 's/^/git: /'
fi

section "Processes"
print_processes "App" 'LocalVoiceInput\.app/Contents/MacOS/LocalVoiceInput|LocalVoiceInputMac'
print_processes "Qwen3 HTTP ASR service" 'qwen3_mlx_http_service\.py'

section "Config"
python3 - "$CONFIG_PATH" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1]).expanduser()
print(f"config_path: {path}")
if not path.exists():
    print("config: missing")
    raise SystemExit(0)

try:
    data = json.loads(path.read_text())
except Exception as exc:
    print(f"config: unreadable ({type(exc).__name__}: {exc})")
    raise SystemExit(0)

print("config: ok")
defaults = {
    "asrBackend": "funasr-websocket",
    "asrURL": "ws://127.0.0.1:10095",
    "asrHTTPURL": "http://127.0.0.1:18105",
    "mockASR": False,
    "correctionMode": "clean",
    "historyMaxItems": 20,
}
for key, default in defaults.items():
    source = "config" if key in data else "default"
    print(f"{key}: {data.get(key, default)} ({source})")
policy = data.get("outputPolicy")
if isinstance(policy, dict):
    auto_paste = policy.get("autoPasteEnabled")
    restore = policy.get("restoreClipboardAfterPaste")
    low_conf = policy.get("preferClipboardForLowConfidence")
    print(f"outputPolicy: autoPaste={auto_paste} restoreClipboardAfterPaste={restore} preferClipboardForLowConfidence={low_conf}")
PY

section "Runtime Paths"
print_path_status "Python runtime" "$PYTHON_BIN" exec
print_path_status "Qwen3 model" "$MODEL" dir
print_path_status "mlx-audio source" "$MLX_AUDIO_SOURCE" dir

section "ASR HTTP"
if ! python3 - "$SERVICE_URL" "$HTTP_TIMEOUT" <<'PY'; then
import json
import sys
import urllib.error
import urllib.request

base_url = sys.argv[1].rstrip("/")
timeout = float(sys.argv[2])
last_error = ""

for endpoint in ("/status", "/health"):
    url = base_url + endpoint
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        last_error = f"{endpoint}: HTTP {exc.code}"
        continue
    except Exception as exc:
        last_error = f"{endpoint}: {type(exc).__name__}: {exc}"
        continue

    if not payload.get("ok"):
        last_error = f"{endpoint}: response ok=false"
        continue

    print(f"url: {base_url}")
    print(f"endpoint: {endpoint}")
    if endpoint != "/status":
        print("status_detail: /status unavailable; using /health")
    print(f"service: {payload.get('service', 'unknown')}")
    print(f"schema_version: {payload.get('schema_version', 'unknown')}")
    print(f"fake_backend: {payload.get('fake_backend', 'unknown')}")
    print(f"native_realtime_gate_eligible: {payload.get('native_realtime_gate_eligible', 'unknown')}")
    print(f"model_load_wall_ms: {payload.get('model_load_wall_ms', 'unknown')}")

    model_info = payload.get("model_info") or {}
    if model_info:
        print(f"model_id: {model_info.get('id', 'unknown')}")
        print(f"vendor: {model_info.get('vendor', 'unknown')}")
        print(f"parameter_scale: {model_info.get('parameter_scale', 'unknown')}")
        print(f"release_date: {model_info.get('release_date', 'unknown')}")

    process = payload.get("process") or {}
    if process:
        print(f"process_pid: {process.get('pid', 'unknown')}")
        print(f"process_rss_mb: {process.get('rss_mb', 'unknown')}")

    if "uptime_seconds" in payload:
        print(f"uptime_seconds: {payload['uptime_seconds']}")

    service_state = payload.get("service_state") or {}
    if service_state:
        print(f"active_session_count: {service_state.get('active_session_count', 'unknown')}")
        print(f"event_count: {service_state.get('event_count', 'unknown')}")
        print(f"event_cursor: {service_state.get('event_cursor', 'unknown')}")

    raise SystemExit(0)

print(f"url: {base_url}")
print(f"status: unreachable ({last_error or 'no response'})")
raise SystemExit(2)
PY
  mark_problem
fi

section "Result"
if [ "$overall" -eq 0 ]; then
  echo "overall: ok"
else
  echo "overall: needs attention"
fi

if [ "$STRICT" = "1" ]; then
  exit "$overall"
fi
