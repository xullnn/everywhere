#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

trap 'rm -rf eval/asr_streaming/__pycache__' EXIT

python3 -m py_compile eval/asr_streaming/run_eval.py
python3 -m py_compile eval/asr_streaming/record_cases.py
python3 -m py_compile eval/asr_streaming/realtime_gate.py
python3 -m py_compile eval/asr_streaming/incremental_ux_gate.py
python3 -m py_compile eval/asr_streaming/fake_incremental_http_service.py
python3 -m py_compile eval/asr_streaming/monitor_pid_resources.py
python3 -m py_compile eval/asr_streaming/qwen3_mlx_realtime_probe.py
python3 -m py_compile eval/asr_streaming/qwen3_mlx_cumulative_probe.py
python3 -m py_compile eval/asr_streaming/qwen3_mlx_cumulative_service.py
python3 -m py_compile eval/asr_streaming/qwen3_mlx_http_service.py
python3 eval/asr_streaming/run_eval.py list-models --registry eval/asr_streaming/model_registry.json >/dev/null
python3 eval/asr_streaming/run_eval.py validate-cases --cases eval/asr_streaming/cases.example.jsonl --allow-missing-audio
python3 eval/asr_streaming/run_eval.py self-test
python3 eval/asr_streaming/realtime_gate.py self-test
python3 eval/asr_streaming/incremental_ux_gate.py self-test
python3 eval/asr_streaming/qwen3_mlx_realtime_probe.py self-test
python3 eval/asr_streaming/qwen3_mlx_cumulative_probe.py self-test
python3 eval/asr_streaming/qwen3_mlx_cumulative_service.py self-test

echo "ASR streaming eval harness validation passed."
