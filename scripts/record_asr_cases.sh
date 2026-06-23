#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 eval/asr_streaming/record_cases.py "$@"
