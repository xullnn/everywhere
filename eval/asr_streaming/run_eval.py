#!/usr/bin/env python3
"""Evaluate local ASR backends with WAV files streamed like microphone input."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import re
import statistics
import sys
import time
import unicodedata
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


DEFAULT_CHUNK_MS = 48
DEFAULT_FUNASR_CHUNK_SIZE = [8, 8, 4]
DEFAULT_FUNASR_CHUNK_INTERVAL = 10
DEFAULT_MIN_COMPLETE_TEXT_RATIO = 0.70
DEFAULT_FUNASR_NANO_MODEL = "FunAudioLLM/Fun-ASR-Nano-2512"
DEFAULT_QWEN3_ASR_MODEL = "Qwen/Qwen3-ASR-0.6B"
DEFAULT_GLM_ASR_MODEL = "zai-org/GLM-ASR-Nano-2512"
DEFAULT_FIRERED_ASR2_AED_MODEL = "FireRedTeam/FireRedASR2-AED"
DEFAULT_FIRERED_ASR2S_SOURCE = ".external/repos/FireRedASR2S"
DEFAULT_MIMO_ASR_MLX_MODEL = ".external/models/MiMo-V2.5-ASR-MLX"
DEFAULT_MIMO_AUDIO_TOKENIZER = ".external/models/MiMo-Audio-Tokenizer"
DEFAULT_MLX_STT_MODEL = ".external/models/mlx-community__Qwen3-ASR-0.6B-8bit"

METRIC_EXPLANATIONS_ZH: dict[str, str] = {
    "cer": "字符错误率，越低越好。按标准答案字符级编辑距离除以标准答案字符数计算，主要用于中文转写准确率判断。",
    "wer": "词或 token 错误率，越低越好。中文近似按单字 token，连续英文/数字/符号按一个 token，适合观察中英混合和技术词错误。",
    "first_partial_ms": "首个实时 partial 返回延迟，单位毫秒，越低说明浮窗越快出现实时转写。",
    "final_latency_ms": "音频发送结束到最后一个 final/offline 事件返回的延迟，单位毫秒，越低说明松开快捷键后最终结果越快。",
    "rtf": "实时因子，等于整次评测耗时除以音频时长。小于 1 表示快于实时，大于 1 表示慢于实时。",
    "partial_event_count": "实时 partial 事件数量，用于观察流式输出密度。",
    "final_event_count": "final/offline 事件数量，用于观察后端是否把最终结果拆成多个离线分段。",
    "event_count": "本 case 收到的后端事件总数。",
    "partial_rewrite_rate": "相邻 partial 文本的平均变化率，越高说明实时文本越不稳定。",
    "final_text_strategy": "最终文本选择策略。offline_segments 表示使用离线结果；online_text_fallback_after_short_offline 表示离线结果覆盖不足，回退到 online 聚合文本。",
    "suspect_incomplete_final": "是否怀疑 final/offline 结果不完整。true 表示不能把该 case 的 offline final 当作完整整段结果。",
    "final_to_expected_char_ratio": "最终文本归一化字符数与标准答案归一化字符数的比例，用于发现过短或过长输出。",
    "offline_to_expected_char_ratio": "offline 分段拼接文本与标准答案的字符长度比例，用于判断离线 final 覆盖是否不足。",
    "online_to_expected_char_ratio": "online partial 聚合文本与标准答案的字符长度比例，用于判断实时聚合文本覆盖是否更完整。",
}


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    audio_path: Path
    expected_text: str
    lang: str
    scenario: str
    metadata: dict[str, Any]


@dataclass
class WavAudio:
    path: Path
    sample_rate: int
    channels: int
    sample_width: int
    frame_count: int
    pcm: bytes

    @property
    def duration_seconds(self) -> float:
        return self.frame_count / float(self.sample_rate)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_model_metadata(registry_path: Path, model_id: str) -> dict[str, Any]:
    registry = load_json(registry_path)
    models = registry.get("models", [])
    for model in models:
        if model.get("id") == model_id:
            keys = [
                "id",
                "vendor",
                "vendor_zh",
                "parameter_scale",
                "parameter_scale_zh",
                "release_date",
                "release_date_precision",
                "release_date_zh",
                "status",
                "license",
                "local_weight_size",
                "streaming",
                "runtime",
                "adapter",
                "local_validation",
            ]
            return {key: model.get(key) for key in keys if key in model}
    return {
        "id": model_id,
        "metadata_status": "not_found_in_registry",
        "registry": str(registry_path),
    }


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if hasattr(value, "tolist"):
        return json_safe(value.tolist())
    return str(value)


def load_cases(path: Path, allow_missing_audio: bool = False) -> list[EvalCase]:
    base = path.parent
    cases: list[EvalCase] = []
    required = {"id", "audio", "text", "lang", "scenario"}
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            missing = sorted(required - set(obj))
            if missing:
                raise ValueError(f"{path}:{lineno}: missing required keys: {', '.join(missing)}")
            case_id = str(obj["id"]).strip()
            if not case_id:
                raise ValueError(f"{path}:{lineno}: id must not be empty")
            audio_path = Path(str(obj["audio"]))
            if not audio_path.is_absolute():
                audio_path = base / audio_path
            if not allow_missing_audio and not audio_path.exists():
                raise FileNotFoundError(f"{path}:{lineno}: audio not found: {audio_path}")
            expected = str(obj["text"])
            cases.append(
                EvalCase(
                    case_id=case_id,
                    audio_path=audio_path,
                    expected_text=expected,
                    lang=str(obj["lang"]),
                    scenario=str(obj["scenario"]),
                    metadata={k: v for k, v in obj.items() if k not in required},
                )
            )
    if not cases:
        raise ValueError(f"{path}: no cases found")
    seen: set[str] = set()
    duplicates: list[str] = []
    for case in cases:
        if case.case_id in seen:
            duplicates.append(case.case_id)
        seen.add(case.case_id)
    if duplicates:
        raise ValueError(f"{path}: duplicate case ids: {', '.join(sorted(set(duplicates)))}")
    return cases


def read_wav_16k_mono_int16(path: Path) -> WavAudio:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frame_count = wav.getnframes()
        pcm = wav.readframes(frame_count)
    if channels != 1 or sample_width != 2 or sample_rate != 16000:
        raise ValueError(
            f"{path} must be 16 kHz mono signed 16-bit PCM WAV; "
            f"got {sample_rate} Hz, {channels} channels, sample width {sample_width}"
        )
    return WavAudio(
        path=path,
        sample_rate=sample_rate,
        channels=channels,
        sample_width=sample_width,
        frame_count=frame_count,
        pcm=pcm,
    )


def normalize_for_cer(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    chars: list[str] = []
    for ch in normalized:
        category = unicodedata.category(ch)
        if category.startswith("P") or category.startswith("Z") or category.startswith("C"):
            continue
        chars.append(ch)
    return "".join(chars)


def tokenize_for_wer(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    tokens: list[str] = []
    buf: list[str] = []
    for ch in normalized:
        if re.match(r"[a-z0-9_#+.-]", ch):
            buf.append(ch)
            continue
        if buf:
            tokens.append("".join(buf))
            buf = []
        if "\u4e00" <= ch <= "\u9fff":
            tokens.append(ch)
        elif ch.isspace() or unicodedata.category(ch).startswith("P"):
            continue
        elif not unicodedata.category(ch).startswith("C"):
            tokens.append(ch)
    if buf:
        tokens.append("".join(buf))
    return tokens


def edit_distance(a: list[str], b: list[str]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + cost,
                )
            )
        previous = current
    return previous[-1]


def error_rate(reference: Iterable[str], hypothesis: Iterable[str]) -> float | None:
    ref = list(reference)
    hyp = list(hypothesis)
    if not ref:
        return 0.0 if not hyp else None
    return edit_distance(ref, hyp) / len(ref)


def cer(reference: str, hypothesis: str) -> float | None:
    return error_rate(list(normalize_for_cer(reference)), list(normalize_for_cer(hypothesis)))


def wer(reference: str, hypothesis: str) -> float | None:
    return error_rate(tokenize_for_wer(reference), tokenize_for_wer(hypothesis))


def now_ms() -> int:
    return int(time.time() * 1000)


def monotonic_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000.0


def build_result_summary(
    *,
    case: EvalCase,
    adapter: str,
    final_text: str,
    events: list[dict[str, Any]],
    send_started_at: float,
    send_finished_at: float,
    run_finished_at: float,
    audio: WavAudio,
    status: str,
    model_info: dict[str, Any],
    error: str | None = None,
) -> dict[str, Any]:
    partial_events = [e for e in events if e.get("kind") == "partial" and e.get("text")]
    final_events = [e for e in events if e.get("kind") == "final" and e.get("text")]
    first_partial_ms = None
    if partial_events:
        first_partial_ms = partial_events[0].get("recv_offset_ms")
    last_final_ms = None
    if final_events:
        last_final_ms = final_events[-1].get("recv_offset_ms")
    elapsed = max(0.001, run_finished_at - send_started_at)
    rtf = elapsed / max(0.001, audio.duration_seconds)
    partial_texts = [str(e.get("text", "")) for e in partial_events]
    rewrite_rate = partial_rewrite_rate(partial_texts)
    return {
        "case_id": case.case_id,
        "adapter": adapter,
        "model_info": model_info,
        "metric_explanations_zh": METRIC_EXPLANATIONS_ZH,
        "audio": str(case.audio_path),
        "duration_seconds": round(audio.duration_seconds, 3),
        "lang": case.lang,
        "scenario": case.scenario,
        "expected_text": case.expected_text,
        "final_text": final_text,
        "cer": cer(case.expected_text, final_text),
        "wer": wer(case.expected_text, final_text),
        "first_partial_ms": first_partial_ms,
        "final_latency_ms": None if last_final_ms is None else last_final_ms - ((send_finished_at - send_started_at) * 1000.0),
        "rtf": rtf,
        "partial_event_count": len(partial_events),
        "final_event_count": len(final_events),
        "event_count": len(events),
        "partial_rewrite_rate": rewrite_rate,
        "status": status,
        "error": error,
    }


def extract_funasr_text(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, dict):
        text = result.get("text")
        if isinstance(text, str):
            return text.strip()
        for value in result.values():
            nested = extract_funasr_text(value)
            if nested:
                return nested
        return ""
    if isinstance(result, list) or isinstance(result, tuple):
        texts: list[str] = []
        for item in result:
            text = extract_funasr_text(item)
            if text:
                texts.append(text)
        return "".join(texts).strip()
    return ""


def run_funasr_nano_local_case(
    *,
    case: EvalCase,
    out_dir: Path,
    model_info: dict[str, Any],
    model: Any,
    language: str,
    hotwords: str,
    batch_size: int,
) -> dict[str, Any]:
    audio = read_wav_16k_mono_int16(case.audio_path)
    case_out = out_dir / case.case_id
    events_path = case_out / "events.jsonl"
    summary_path = case_out / "summary.json"
    if events_path.exists():
        events_path.unlink()
    case_out.mkdir(parents=True, exist_ok=True)

    started_at = time.perf_counter()
    hotword_values = [h.strip() for h in hotwords.split(",") if h.strip()]
    generate_kwargs: dict[str, Any] = {
        "input": [str(case.audio_path)],
        "cache": {},
        "batch_size": batch_size,
        "language": language,
    }
    if hotword_values:
        generate_kwargs["hotwords"] = hotword_values
    raw_result = model.generate(**generate_kwargs)
    finished_at = time.perf_counter()
    final_text = extract_funasr_text(raw_result)
    event = {
        "recv_epoch_ms": now_ms(),
        "recv_offset_ms": monotonic_ms(started_at),
        "case_id": case.case_id,
        "kind": "final",
        "mode": "funasr-nano-local",
        "text": final_text,
        "is_final": True,
        "raw": json_safe(raw_result),
    }
    append_jsonl(events_path, event)
    summary = build_result_summary(
        case=case,
        adapter="funasr-nano-local",
        final_text=final_text,
        events=[event],
        send_started_at=started_at,
        send_finished_at=started_at,
        run_finished_at=finished_at,
        audio=audio,
        status="ok" if final_text else "no_text",
        model_info=model_info,
    )
    summary.update(
        {
            "final_text_strategy": "file_level_final",
            "offline_segments": [final_text] if final_text else [],
            "online_partials": [],
            "online_text": "",
            "last_partial_text": "",
            "segment_count": 1 if final_text else 0,
            "online_partial_count": 0,
            "partial_after_final": False,
            "suspect_incomplete_final": False if final_text else True,
            "final_to_expected_char_ratio": char_length_ratio(final_text, case.expected_text),
            "offline_to_expected_char_ratio": char_length_ratio(final_text, case.expected_text),
            "online_to_expected_char_ratio": None,
            "adapter_notes_zh": "Fun-ASR-Nano 本地文件级推理；本 adapter 不提供实时 partial，不能用该结果判断浮窗实时体验。",
        }
    )
    write_json(summary_path, summary)
    return summary


def extract_qwen3_asr_text(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result.strip()
    text = getattr(result, "text", None)
    if isinstance(text, str):
        return text.strip()
    if isinstance(result, dict):
        text = result.get("text")
        if isinstance(text, str):
            return text.strip()
        for value in result.values():
            nested = extract_qwen3_asr_text(value)
            if nested:
                return nested
        return ""
    if isinstance(result, (list, tuple)):
        return "".join(extract_qwen3_asr_text(item) for item in result).strip()
    return str(result).strip()


def qwen3_asr_result_payload(result: Any) -> dict[str, Any]:
    if result is None:
        return {}
    payload: dict[str, Any] = {}
    for key in ("language", "text", "time_stamps"):
        if hasattr(result, key):
            payload[key] = json_safe(getattr(result, key))
    if payload:
        return payload
    return {"raw": json_safe(result)}


def run_qwen3_asr_local_case(
    *,
    case: EvalCase,
    out_dir: Path,
    model_info: dict[str, Any],
    model: Any,
    language: str | None,
    context: str,
) -> dict[str, Any]:
    audio = read_wav_16k_mono_int16(case.audio_path)
    case_out = out_dir / case.case_id
    events_path = case_out / "events.jsonl"
    summary_path = case_out / "summary.json"
    if events_path.exists():
        events_path.unlink()
    case_out.mkdir(parents=True, exist_ok=True)

    started_at = time.perf_counter()
    results = model.transcribe(
        audio=str(case.audio_path),
        language=language,
        context=context,
        return_time_stamps=False,
    )
    finished_at = time.perf_counter()
    first_result = results[0] if isinstance(results, list) and results else results
    final_text = extract_qwen3_asr_text(first_result)
    event = {
        "recv_epoch_ms": now_ms(),
        "recv_offset_ms": monotonic_ms(started_at),
        "case_id": case.case_id,
        "kind": "final",
        "mode": "qwen3-asr-local",
        "text": final_text,
        "is_final": True,
        "raw": qwen3_asr_result_payload(first_result),
    }
    append_jsonl(events_path, event)
    summary = build_result_summary(
        case=case,
        adapter="qwen3-asr-local",
        final_text=final_text,
        events=[event],
        send_started_at=started_at,
        send_finished_at=started_at,
        run_finished_at=finished_at,
        audio=audio,
        status="ok" if final_text else "no_text",
        model_info=model_info,
    )
    summary.update(
        {
            "final_text_strategy": "file_level_final",
            "offline_segments": [final_text] if final_text else [],
            "online_partials": [],
            "online_text": "",
            "last_partial_text": "",
            "segment_count": 1 if final_text else 0,
            "online_partial_count": 0,
            "partial_after_final": False,
            "suspect_incomplete_final": False if final_text else True,
            "final_to_expected_char_ratio": char_length_ratio(final_text, case.expected_text),
            "offline_to_expected_char_ratio": char_length_ratio(final_text, case.expected_text),
            "online_to_expected_char_ratio": None,
            "adapter_notes_zh": "Qwen3-ASR 本地文件级 transformers 后端推理；本 adapter 不提供实时 partial，不能用该结果判断浮窗实时体验。",
        }
    )
    write_json(summary_path, summary)
    return summary


def wav_audio_to_float32_array(audio: WavAudio) -> Any:
    import numpy as np

    return np.frombuffer(audio.pcm, dtype="<i2").astype(np.float32) / 32768.0


def extract_glm_asr_text(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, (list, tuple)):
        return "".join(extract_glm_asr_text(item) for item in result).strip()
    return str(result).strip()


def run_glm_asr_local_case(
    *,
    case: EvalCase,
    out_dir: Path,
    model_info: dict[str, Any],
    model_bundle: dict[str, Any],
    max_new_tokens: int,
) -> dict[str, Any]:
    audio = read_wav_16k_mono_int16(case.audio_path)
    case_out = out_dir / case.case_id
    events_path = case_out / "events.jsonl"
    summary_path = case_out / "summary.json"
    if events_path.exists():
        events_path.unlink()
    case_out.mkdir(parents=True, exist_ok=True)

    processor = model_bundle["processor"]
    model = model_bundle["model"]
    torch = model_bundle["torch"]
    device = model_bundle["device"]
    dtype = model_bundle["dtype"]

    started_at = time.perf_counter()
    samples = wav_audio_to_float32_array(audio)
    inputs = processor.apply_transcription_request(samples)
    inputs = inputs.to(device, dtype=dtype)
    with torch.inference_mode():
        outputs = model.generate(**inputs, do_sample=False, max_new_tokens=max_new_tokens)
    prefix_len = inputs.input_ids.shape[1]
    decoded_outputs = processor.batch_decode(outputs[:, prefix_len:], skip_special_tokens=True)
    finished_at = time.perf_counter()

    final_text = extract_glm_asr_text(decoded_outputs)
    event = {
        "recv_epoch_ms": now_ms(),
        "recv_offset_ms": monotonic_ms(started_at),
        "case_id": case.case_id,
        "kind": "final",
        "mode": "glm-asr-local",
        "text": final_text,
        "is_final": True,
        "raw": {"decoded_outputs": json_safe(decoded_outputs)},
    }
    append_jsonl(events_path, event)
    summary = build_result_summary(
        case=case,
        adapter="glm-asr-local",
        final_text=final_text,
        events=[event],
        send_started_at=started_at,
        send_finished_at=started_at,
        run_finished_at=finished_at,
        audio=audio,
        status="ok" if final_text else "no_text",
        model_info=model_info,
    )
    summary.update(
        {
            "final_text_strategy": "file_level_final",
            "offline_segments": [final_text] if final_text else [],
            "online_partials": [],
            "online_text": "",
            "last_partial_text": "",
            "segment_count": 1 if final_text else 0,
            "online_partial_count": 0,
            "partial_after_final": False,
            "suspect_incomplete_final": False if final_text else True,
            "final_to_expected_char_ratio": char_length_ratio(final_text, case.expected_text),
            "offline_to_expected_char_ratio": char_length_ratio(final_text, case.expected_text),
            "online_to_expected_char_ratio": None,
            "adapter_notes_zh": "GLM-ASR-Nano 本地文件级 transformers 后端推理；本 adapter 不提供实时 partial，不能用该结果判断浮窗实时体验。",
        }
    )
    write_json(summary_path, summary)
    return summary


def extract_firered_asr2_text(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, dict):
        text = result.get("text")
        if isinstance(text, str):
            return text.strip()
        for value in result.values():
            nested = extract_firered_asr2_text(value)
            if nested:
                return nested
        return ""
    if isinstance(result, (list, tuple)):
        return "".join(extract_firered_asr2_text(item) for item in result).strip()
    return str(result).strip()


def run_firered_asr2_aed_local_case(
    *,
    case: EvalCase,
    out_dir: Path,
    model_info: dict[str, Any],
    model: Any,
) -> dict[str, Any]:
    audio = read_wav_16k_mono_int16(case.audio_path)
    case_out = out_dir / case.case_id
    events_path = case_out / "events.jsonl"
    summary_path = case_out / "summary.json"
    if events_path.exists():
        events_path.unlink()
    case_out.mkdir(parents=True, exist_ok=True)

    started_at = time.perf_counter()
    raw_results = model.transcribe([case.case_id], [str(case.audio_path)])
    finished_at = time.perf_counter()
    first_result = raw_results[0] if isinstance(raw_results, list) and raw_results else raw_results
    final_text = extract_firered_asr2_text(first_result)
    event = {
        "recv_epoch_ms": now_ms(),
        "recv_offset_ms": monotonic_ms(started_at),
        "case_id": case.case_id,
        "kind": "final",
        "mode": "firered-asr2-aed-local",
        "text": final_text,
        "is_final": True,
        "raw": json_safe(first_result),
    }
    append_jsonl(events_path, event)
    summary = build_result_summary(
        case=case,
        adapter="firered-asr2-aed-local",
        final_text=final_text,
        events=[event],
        send_started_at=started_at,
        send_finished_at=started_at,
        run_finished_at=finished_at,
        audio=audio,
        status="ok" if final_text else "no_text",
        model_info=model_info,
    )
    summary.update(
        {
            "final_text_strategy": "file_level_final",
            "offline_segments": [final_text] if final_text else [],
            "online_partials": [],
            "online_text": "",
            "last_partial_text": "",
            "segment_count": 1 if final_text else 0,
            "online_partial_count": 0,
            "partial_after_final": False,
            "suspect_incomplete_final": False if final_text else True,
            "final_to_expected_char_ratio": char_length_ratio(final_text, case.expected_text),
            "offline_to_expected_char_ratio": char_length_ratio(final_text, case.expected_text),
            "online_to_expected_char_ratio": None,
            "adapter_notes_zh": "FireRedASR2-AED 官方 PyTorch 本地文件级推理；本 adapter 不提供实时 partial，不能用该结果判断浮窗实时体验。",
        }
    )
    write_json(summary_path, summary)
    return summary


def extract_mimo_asr_text(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result.strip()
    text = getattr(result, "text", None)
    if isinstance(text, str):
        return text.strip()
    if isinstance(result, dict):
        text = result.get("text")
        if isinstance(text, str):
            return text.strip()
        for value in result.values():
            nested = extract_mimo_asr_text(value)
            if nested:
                return nested
        return ""
    if isinstance(result, (list, tuple)):
        return "".join(extract_mimo_asr_text(item) for item in result).strip()
    return str(result).strip()


def mimo_asr_result_payload(result: Any) -> dict[str, Any]:
    if result is None:
        return {}
    payload: dict[str, Any] = {}
    for key in ("text", "language", "segments", "tokens"):
        if hasattr(result, key):
            payload[key] = json_safe(getattr(result, key))
    if payload:
        return payload
    return {"raw": json_safe(result)}


def run_mimo_asr_mlx_local_case(
    *,
    case: EvalCase,
    out_dir: Path,
    model_info: dict[str, Any],
    model: Any,
    language: str | None,
) -> dict[str, Any]:
    audio = read_wav_16k_mono_int16(case.audio_path)
    case_out = out_dir / case.case_id
    events_path = case_out / "events.jsonl"
    summary_path = case_out / "summary.json"
    if events_path.exists():
        events_path.unlink()
    case_out.mkdir(parents=True, exist_ok=True)

    started_at = time.perf_counter()
    result = model.generate(str(case.audio_path), language=language)
    finished_at = time.perf_counter()
    final_text = extract_mimo_asr_text(result)
    event = {
        "recv_epoch_ms": now_ms(),
        "recv_offset_ms": monotonic_ms(started_at),
        "case_id": case.case_id,
        "kind": "final",
        "mode": "mimo-asr-mlx-local",
        "text": final_text,
        "is_final": True,
        "raw": mimo_asr_result_payload(result),
    }
    append_jsonl(events_path, event)
    summary = build_result_summary(
        case=case,
        adapter="mimo-asr-mlx-local",
        final_text=final_text,
        events=[event],
        send_started_at=started_at,
        send_finished_at=started_at,
        run_finished_at=finished_at,
        audio=audio,
        status="ok" if final_text else "no_text",
        model_info=model_info,
    )
    summary.update(
        {
            "final_text_strategy": "file_level_final",
            "offline_segments": [final_text] if final_text else [],
            "online_partials": [],
            "online_text": "",
            "last_partial_text": "",
            "segment_count": 1 if final_text else 0,
            "online_partial_count": 0,
            "partial_after_final": False,
            "suspect_incomplete_final": False if final_text else True,
            "final_to_expected_char_ratio": char_length_ratio(final_text, case.expected_text),
            "offline_to_expected_char_ratio": char_length_ratio(final_text, case.expected_text),
            "online_to_expected_char_ratio": None,
            "adapter_notes_zh": "MiMo-V2.5-ASR MLX 本地文件级推理；本 adapter 不提供实时 partial，不能用该结果判断浮窗实时体验。",
        }
    )
    write_json(summary_path, summary)
    return summary


def run_mlx_stt_local_case(
    *,
    case: EvalCase,
    out_dir: Path,
    model_info: dict[str, Any],
    model: Any,
    language: str | None,
) -> dict[str, Any]:
    audio = read_wav_16k_mono_int16(case.audio_path)
    case_out = out_dir / case.case_id
    events_path = case_out / "events.jsonl"
    summary_path = case_out / "summary.json"
    if events_path.exists():
        events_path.unlink()
    case_out.mkdir(parents=True, exist_ok=True)

    started_at = time.perf_counter()
    result = model.generate(str(case.audio_path), language=language)
    finished_at = time.perf_counter()
    final_text = extract_mimo_asr_text(result)
    event = {
        "recv_epoch_ms": now_ms(),
        "recv_offset_ms": monotonic_ms(started_at),
        "case_id": case.case_id,
        "kind": "final",
        "mode": "mlx-stt-local",
        "text": final_text,
        "is_final": True,
        "raw": mimo_asr_result_payload(result),
    }
    append_jsonl(events_path, event)
    summary = build_result_summary(
        case=case,
        adapter="mlx-stt-local",
        final_text=final_text,
        events=[event],
        send_started_at=started_at,
        send_finished_at=started_at,
        run_finished_at=finished_at,
        audio=audio,
        status="ok" if final_text else "no_text",
        model_info=model_info,
    )
    summary.update(
        {
            "final_text_strategy": "file_level_final",
            "offline_segments": [final_text] if final_text else [],
            "online_partials": [],
            "online_text": "",
            "last_partial_text": "",
            "segment_count": 1 if final_text else 0,
            "online_partial_count": 0,
            "partial_after_final": False,
            "suspect_incomplete_final": False if final_text else True,
            "final_to_expected_char_ratio": char_length_ratio(final_text, case.expected_text),
            "offline_to_expected_char_ratio": char_length_ratio(final_text, case.expected_text),
            "online_to_expected_char_ratio": None,
            "adapter_notes_zh": "通用 MLX STT 本地文件级推理；本 adapter 使用 generate(...) 得到 final，不用它判断麦克风实时 partial 体验。",
        }
    )
    write_json(summary_path, summary)
    return summary


def partial_rewrite_rate(partials: list[str]) -> float | None:
    if len(partials) < 2:
        return None
    distances = []
    for before, after in zip(partials, partials[1:]):
        before_norm = normalize_for_cer(before)
        after_norm = normalize_for_cer(after)
        denom = max(1, len(after_norm))
        distances.append(edit_distance(list(before_norm), list(after_norm)) / denom)
    return statistics.mean(distances) if distances else None


def char_length_ratio(text: str, expected_text: str) -> float | None:
    expected_len = len(normalize_for_cer(expected_text))
    if expected_len == 0:
        return None
    return len(normalize_for_cer(text)) / expected_len


def merge_partial_texts(partials: list[str]) -> str:
    cleaned = [partial.strip() for partial in partials if partial.strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]

    cumulative_pairs = 0
    comparable_pairs = 0
    for before, after in zip(cleaned, cleaned[1:]):
        before_norm = normalize_for_cer(before)
        after_norm = normalize_for_cer(after)
        if not before_norm or not after_norm:
            continue
        comparable_pairs += 1
        if after_norm.startswith(before_norm) and len(after_norm) >= len(before_norm):
            cumulative_pairs += 1

    # Some backends emit cumulative partials, while FunASR 2-pass online events
    # commonly arrive as incremental chunks. Prefer the cumulative interpretation
    # only when every comparable transition supports it.
    if comparable_pairs > 0 and cumulative_pairs == comparable_pairs:
        return cleaned[-1]
    return "".join(cleaned).strip()


def has_partial_after_final(events: list[dict[str, Any]]) -> bool:
    final_offsets = [
        float(e.get("recv_offset_ms", 0.0))
        for e in events
        if e.get("kind") == "final" and e.get("text")
    ]
    if not final_offsets:
        return False
    last_final_offset = max(final_offsets)
    return any(
        float(e.get("recv_offset_ms", 0.0)) > last_final_offset
        for e in events
        if e.get("kind") == "partial" and e.get("text")
    )


def select_funasr_transcript(
    *,
    events: list[dict[str, Any]],
    expected_text: str,
    min_complete_ratio: float = DEFAULT_MIN_COMPLETE_TEXT_RATIO,
) -> dict[str, Any]:
    partial_texts = [str(e.get("text", "")) for e in events if e.get("kind") == "partial" and e.get("text")]
    offline_segments = [str(e.get("text", "")) for e in events if e.get("kind") == "final" and e.get("text")]

    online_text = merge_partial_texts(partial_texts)
    last_partial_text = partial_texts[-1].strip() if partial_texts else ""
    final_text_from_segments = "".join(offline_segments).strip()

    offline_ratio = char_length_ratio(final_text_from_segments, expected_text)
    online_ratio = char_length_ratio(online_text, expected_text)

    final_text = final_text_from_segments or online_text or last_partial_text
    final_text_strategy = "offline_segments" if final_text_from_segments else "online_text"
    suspect_incomplete_final = False

    if final_text_from_segments:
        offline_complete = offline_ratio is None or offline_ratio >= min_complete_ratio
        online_is_better_coverage = (
            bool(online_text)
            and len(normalize_for_cer(online_text)) > len(normalize_for_cer(final_text_from_segments))
            and (online_ratio or 0.0) > (offline_ratio or 0.0)
        )
        if offline_complete:
            final_text = final_text_from_segments
            final_text_strategy = "offline_segments"
        elif online_is_better_coverage:
            final_text = online_text
            final_text_strategy = "online_text_fallback_after_short_offline"
            suspect_incomplete_final = True
        else:
            final_text = final_text_from_segments
            final_text_strategy = "offline_segments_short"
            suspect_incomplete_final = True
    elif online_text:
        final_text = online_text
        final_text_strategy = "online_text_no_offline"
        suspect_incomplete_final = True
    elif last_partial_text:
        final_text = last_partial_text
        final_text_strategy = "last_partial_no_offline"
        suspect_incomplete_final = True

    final_ratio = char_length_ratio(final_text, expected_text)
    if final_ratio is not None and final_ratio < min_complete_ratio:
        suspect_incomplete_final = True

    return {
        "final_text": final_text,
        "final_text_strategy": final_text_strategy,
        "final_text_from_segments": final_text_from_segments,
        "offline_segments": offline_segments,
        "online_text": online_text,
        "online_partials": partial_texts,
        "last_partial_text": last_partial_text,
        "segment_count": len(offline_segments),
        "online_partial_count": len(partial_texts),
        "partial_after_final": has_partial_after_final(events),
        "suspect_incomplete_final": suspect_incomplete_final,
        "final_to_expected_char_ratio": final_ratio,
        "offline_to_expected_char_ratio": offline_ratio,
        "online_to_expected_char_ratio": online_ratio,
    }


def _assert_self_test(name: str, condition: bool, details: str) -> None:
    if not condition:
        raise AssertionError(f"{name}: {details}")


def command_self_test(args: argparse.Namespace) -> int:
    expected = "今天我们测试一段比较长的语音输入内容"
    incomplete_offline_events = [
        {"kind": "partial", "text": "今天我们测试", "recv_offset_ms": 100.0},
        {"kind": "partial", "text": "一段比较长的", "recv_offset_ms": 200.0},
        {"kind": "partial", "text": "语音输入内容", "recv_offset_ms": 300.0},
        {"kind": "final", "text": "今天我们测试", "recv_offset_ms": 400.0},
    ]
    selected = select_funasr_transcript(events=incomplete_offline_events, expected_text=expected)
    _assert_self_test(
        "short-offline-fallback",
        selected["final_text"] == expected,
        f"expected online fallback, got {selected['final_text']!r}",
    )
    _assert_self_test(
        "short-offline-strategy",
        selected["final_text_strategy"] == "online_text_fallback_after_short_offline",
        f"unexpected strategy {selected['final_text_strategy']}",
    )
    _assert_self_test(
        "short-offline-suspect",
        bool(selected["suspect_incomplete_final"]),
        "expected suspect_incomplete_final",
    )

    complete_offline_events = [
        {"kind": "partial", "text": "今天我们测试", "recv_offset_ms": 100.0},
        {"kind": "final", "text": expected, "recv_offset_ms": 500.0},
    ]
    selected = select_funasr_transcript(events=complete_offline_events, expected_text=expected)
    _assert_self_test(
        "complete-offline",
        selected["final_text"] == expected and selected["final_text_strategy"] == "offline_segments",
        f"expected offline final, got {selected}",
    )
    _assert_self_test(
        "complete-offline-not-suspect",
        not bool(selected["suspect_incomplete_final"]),
        "complete offline final should not be suspect",
    )

    late_partial_events = [
        {"kind": "final", "text": expected, "recv_offset_ms": 100.0},
        {"kind": "partial", "text": "迟到 partial", "recv_offset_ms": 150.0},
    ]
    selected = select_funasr_transcript(events=late_partial_events, expected_text=expected)
    _assert_self_test(
        "late-partial-flag",
        bool(selected["partial_after_final"]),
        "expected partial_after_final flag",
    )

    print("ASR eval transcript self-test passed.")
    return 0


async def run_funasr_ws_case(
    *,
    case: EvalCase,
    ws_url: str,
    out_dir: Path,
    chunk_ms: int,
    realtime: bool,
    receive_timeout_sec: float,
    hotwords: str,
    use_itn: bool,
    mode: str,
    model_info: dict[str, Any],
) -> dict[str, Any]:
    try:
        import websockets
    except ImportError as exc:
        raise RuntimeError(
            "Missing Python package 'websockets'. Activate the FunASR venv or install FunASR websocket requirements."
        ) from exc

    audio = read_wav_16k_mono_int16(case.audio_path)
    parsed = urlparse(ws_url)
    if parsed.scheme not in {"ws", "wss"}:
        raise ValueError(f"ws-url must start with ws:// or wss://, got {ws_url}")

    case_out = out_dir / case.case_id
    events_path = case_out / "events.jsonl"
    summary_path = case_out / "summary.json"
    if events_path.exists():
        events_path.unlink()
    case_out.mkdir(parents=True, exist_ok=True)

    bytes_per_ms = audio.sample_rate * audio.sample_width * audio.channels / 1000.0
    stride = max(2, int(bytes_per_ms * chunk_ms))
    if stride % 2:
        stride += 1

    events: list[dict[str, Any]] = []
    start_perf = time.perf_counter()
    send_started_at = start_perf
    send_finished_at = start_perf
    sender_done = asyncio.Event()

    async with websockets.connect(ws_url, subprotocols=["binary"], ping_interval=None) as websocket:
        start_message = {
            "mode": mode,
            "chunk_size": DEFAULT_FUNASR_CHUNK_SIZE,
            "chunk_interval": DEFAULT_FUNASR_CHUNK_INTERVAL,
            "encoder_chunk_look_back": 4,
            "decoder_chunk_look_back": 0,
            "audio_fs": audio.sample_rate,
            "wav_name": case.case_id,
            "wav_format": "pcm",
            "is_speaking": True,
            "hotwords": hotwords,
            "itn": use_itn,
        }
        await websocket.send(json.dumps(start_message, ensure_ascii=False))

        async def sender() -> None:
            nonlocal send_started_at, send_finished_at
            try:
                send_started_at = time.perf_counter()
                for offset in range(0, len(audio.pcm), stride):
                    chunk = audio.pcm[offset : offset + stride]
                    await websocket.send(chunk)
                    if realtime:
                        await asyncio.sleep(chunk_ms / 1000.0)
                send_finished_at = time.perf_counter()
                await websocket.send(json.dumps({"is_speaking": False}, ensure_ascii=False))
            finally:
                sender_done.set()

        async def receiver() -> None:
            while True:
                try:
                    raw_message = await asyncio.wait_for(websocket.recv(), timeout=receive_timeout_sec)
                except asyncio.TimeoutError:
                    if sender_done.is_set():
                        break
                    continue
                recv_offset = monotonic_ms(send_started_at)
                try:
                    payload = json.loads(raw_message)
                except json.JSONDecodeError:
                    payload = {"raw": raw_message}
                text = str(payload.get("text", ""))
                event_mode = str(payload.get("mode", ""))
                kind = classify_funasr_event(event_mode)
                event = {
                    "recv_epoch_ms": now_ms(),
                    "recv_offset_ms": recv_offset,
                    "case_id": case.case_id,
                    "kind": kind,
                    "mode": event_mode,
                    "text": text,
                    "is_final": bool(payload.get("is_final", False)),
                    "raw": payload,
                }
                events.append(event)
                append_jsonl(events_path, event)

        await asyncio.gather(sender(), receiver())

    run_finished_at = time.perf_counter()
    transcript = select_funasr_transcript(events=events, expected_text=case.expected_text)
    summary = build_result_summary(
        case=case,
        adapter="funasr-ws",
        final_text=str(transcript["final_text"]),
        events=events,
        send_started_at=send_started_at,
        send_finished_at=send_finished_at,
        run_finished_at=run_finished_at,
        audio=audio,
        status="ok" if transcript["final_text"] else "no_text",
        model_info=model_info,
    )
    summary.update(transcript)
    write_json(summary_path, summary)
    return summary


def classify_funasr_event(mode: str) -> str:
    if mode in {"online", "2pass-online"}:
        return "partial"
    if mode in {"offline", "2pass-offline"}:
        return "final"
    return "event"


def resolve_funasr_device(requested: str) -> str:
    if requested != "auto":
        return requested
    try:
        import torch

        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


def resolve_funasr_remote_code(requested: str) -> str | None:
    if not requested:
        return None
    path = Path(requested).expanduser()
    if path.exists():
        return str(path.resolve())
    if requested == "./model.py":
        spec = importlib.util.find_spec("funasr.models.fun_asr_nano.model")
        if spec is not None and spec.origin:
            module_path = Path(spec.origin).resolve()
            if module_path.exists():
                return str(module_path)
    return requested


def load_funasr_nano_model(args: argparse.Namespace) -> Any:
    try:
        from funasr import AutoModel
    except ImportError as exc:
        raise RuntimeError(
            "Missing Python package 'funasr'. Activate .venv or run scripts/setup_funasr_venv.sh first."
        ) from exc

    device = resolve_funasr_device(args.funasr_device)
    kwargs: dict[str, Any] = {
        "model": args.funasr_nano_model,
        "trust_remote_code": True,
        "device": device,
        "hub": args.funasr_hub,
        "disable_update": True,
    }
    if args.funasr_vad_model:
        kwargs["vad_model"] = args.funasr_vad_model
        kwargs["vad_kwargs"] = {"max_single_segment_time": args.funasr_max_segment_ms}
    remote_code = resolve_funasr_remote_code(args.funasr_remote_code)
    if remote_code:
        kwargs["remote_code"] = remote_code
    return AutoModel(**kwargs)


def resolve_qwen3_device(requested: str) -> str:
    if requested != "auto":
        return requested
    try:
        import torch

        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


def resolve_torch_dtype(requested: str, device: str) -> Any:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("Missing Python package 'torch'. Install the Qwen3-ASR runtime first.") from exc

    if requested == "auto":
        return torch.float32 if device == "cpu" else torch.bfloat16
    mapping = {
        "float32": torch.float32,
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
    }
    return mapping[requested]


def load_qwen3_asr_model(args: argparse.Namespace) -> Any:
    try:
        import torch
        from qwen_asr import Qwen3ASRModel
    except ImportError as exc:
        raise RuntimeError(
            "Missing Python package 'qwen-asr'. Run scripts/setup_qwen3_asr_venv.sh first."
        ) from exc

    device = resolve_qwen3_device(args.qwen3_device)
    dtype = resolve_torch_dtype(args.qwen3_dtype, device)
    kwargs: dict[str, Any] = {
        "dtype": dtype,
        "max_inference_batch_size": args.qwen3_batch_size,
        "max_new_tokens": args.qwen3_max_new_tokens,
    }
    if args.qwen3_local_files_only:
        kwargs["local_files_only"] = True
    if args.qwen3_device_map:
        kwargs["device_map"] = args.qwen3_device_map

    model = Qwen3ASRModel.from_pretrained(args.qwen3_model, **kwargs)
    if not args.qwen3_device_map and device in {"cpu", "mps"}:
        model.model.to(torch.device(device))
        model.device = torch.device(device)
        model.dtype = getattr(model.model, "dtype", dtype)
    return model


def load_glm_asr_model(args: argparse.Namespace) -> dict[str, Any]:
    try:
        import torch
        from transformers import AutoProcessor, GlmAsrForConditionalGeneration
    except ImportError as exc:
        raise RuntimeError(
            "Missing GLM-ASR runtime. Run the GLM-specific venv with transformers 5.x."
        ) from exc

    device = resolve_qwen3_device(args.glm_asr_device)
    dtype = resolve_torch_dtype(args.glm_asr_dtype, device)
    model_kwargs: dict[str, Any] = {"dtype": dtype}
    processor_kwargs: dict[str, Any] = {}
    if args.glm_asr_local_files_only:
        model_kwargs["local_files_only"] = True
        processor_kwargs["local_files_only"] = True
    if args.glm_asr_device_map:
        model_kwargs["device_map"] = args.glm_asr_device_map

    processor = AutoProcessor.from_pretrained(args.glm_asr_model, **processor_kwargs)
    model = GlmAsrForConditionalGeneration.from_pretrained(args.glm_asr_model, **model_kwargs)
    if args.glm_asr_device_map:
        model_device = next(model.parameters()).device
    else:
        model_device = torch.device(device)
        model.to(model_device)
    model.eval()
    return {
        "processor": processor,
        "model": model,
        "torch": torch,
        "device": model_device,
        "dtype": getattr(model, "dtype", dtype),
    }


def load_firered_asr2_aed_model(args: argparse.Namespace) -> Any:
    source_root = Path(args.firered_source).expanduser().resolve()
    package_root = source_root / "fireredasr2s"
    if not package_root.exists():
        raise RuntimeError(f"FireRedASR2S source package not found: {package_root}")
    for path in (str(package_root), str(source_root)):
        if path not in sys.path:
            sys.path.insert(0, path)

    try:
        from fireredasr2.asr import FireRedAsr2, FireRedAsr2Config
    except ImportError as exc:
        raise RuntimeError(
            "Missing FireRedASR2S runtime. Ensure .venv-firered has kaldi_native_fbank, "
            "textgrid, sentencepiece, torch, and torchaudio installed."
        ) from exc

    config = FireRedAsr2Config(
        use_gpu=bool(args.firered_use_gpu),
        use_half=bool(args.firered_use_half),
        beam_size=args.firered_beam_size,
        nbest=1,
        decode_max_len=args.firered_decode_max_len,
        softmax_smoothing=args.firered_softmax_smoothing,
        aed_length_penalty=args.firered_aed_length_penalty,
        eos_penalty=args.firered_eos_penalty,
        return_timestamp=bool(args.firered_return_timestamp),
    )
    return FireRedAsr2.from_pretrained("aed", args.firered_model, config)


def load_mimo_asr_mlx_model(args: argparse.Namespace) -> Any:
    try:
        from mlx_audio.stt import load
    except ImportError as exc:
        raise RuntimeError(
            "Missing MLX MiMo runtime. Run .venv-mimo/bin/python -m pip install "
            "-e '.external/repos/mlx-audio[stt]' first."
        ) from exc
    audio_tokenizer_dir = args.mimo_audio_tokenizer_dir.strip() or None
    return load(args.mimo_model, audio_tokenizer_dir=audio_tokenizer_dir)


def load_mlx_stt_model(args: argparse.Namespace) -> Any:
    model_type = None
    config_path = Path(args.mlx_stt_model) / "config.json"
    if config_path.exists():
        try:
            config = load_json(config_path)
            model_type = config.get("model_type")
        except Exception:
            model_type = None

    load_error: Exception | None = None
    try:
        from mlx_audio.stt import load

        return load(args.mlx_stt_model)
    except ImportError as exc:
        load_error = exc
    except Exception as exc:
        if model_type != "funasr":
            raise
        load_error = exc

    if model_type == "funasr":
        try:
            from mlx_audio.stt.models.funasr import Model
        except ImportError as exc:
            raise RuntimeError(
                "Missing MLX FunASR runtime. Install or expose mlx-audio-plus 0.1.8 "
                "on PYTHONPATH; this MLX conversion is not supported by mlx-audio 0.4.x."
            ) from exc
        return Model.from_pretrained(args.mlx_stt_model)

    if load_error is not None:
        raise RuntimeError(
            "Missing MLX STT runtime. Run .venv-mimo/bin/python -m pip install "
            "-e '.external/repos/mlx-audio[stt]' first."
        ) from load_error
    raise RuntimeError(f"Unsupported MLX STT model: {args.mlx_stt_model}")


def command_list_models(args: argparse.Namespace) -> int:
    registry = load_json(Path(args.registry))
    models = registry.get("models", [])
    for model in models:
        adapter = model.get("adapter") or "-"
        streaming = model.get("streaming")
        vendor = model.get("vendor_zh") or model.get("vendor") or "-"
        parameter_scale = model.get("parameter_scale_zh") or model.get("parameter_scale") or "-"
        release_date = model.get("release_date_zh") or model.get("release_date") or "-"
        print(
            f"{model.get('id')}\tstatus={model.get('status')}\t"
            f"streaming={streaming}\tadapter={adapter}\tvendor={vendor}\t"
            f"params={parameter_scale}\trelease={release_date}"
        )
    return 0


def command_validate_cases(args: argparse.Namespace) -> int:
    cases = load_cases(Path(args.cases), allow_missing_audio=args.allow_missing_audio)
    print(f"validated {len(cases)} cases from {args.cases}")
    return 0


async def run_cases_async(args: argparse.Namespace) -> int:
    cases = load_cases(Path(args.cases), allow_missing_audio=False)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_info = load_model_metadata(Path(args.registry), args.model_id)
    local_model = None
    if args.adapter == "funasr-nano-local":
        local_model = load_funasr_nano_model(args)
    elif args.adapter == "qwen3-asr-local":
        local_model = load_qwen3_asr_model(args)
    elif args.adapter == "glm-asr-local":
        local_model = load_glm_asr_model(args)
    elif args.adapter == "firered-asr2-aed-local":
        local_model = load_firered_asr2_aed_model(args)
    elif args.adapter == "mimo-asr-mlx-local":
        local_model = load_mimo_asr_mlx_model(args)
    elif args.adapter == "mlx-stt-local":
        local_model = load_mlx_stt_model(args)
    summaries: list[dict[str, Any]] = []
    for case in cases:
        print(f"run {case.case_id} via {args.adapter}")
        try:
            if args.adapter == "funasr-ws":
                summary = await run_funasr_ws_case(
                    case=case,
                    ws_url=args.ws_url,
                    out_dir=out_dir,
                    chunk_ms=args.chunk_ms,
                    realtime=not args.no_realtime,
                    receive_timeout_sec=args.receive_timeout_sec,
                    hotwords=args.hotwords,
                    use_itn=not args.no_itn,
                    mode=args.mode,
                    model_info=model_info,
                )
            elif args.adapter == "funasr-nano-local":
                summary = run_funasr_nano_local_case(
                    case=case,
                    out_dir=out_dir,
                    model_info=model_info,
                    model=local_model,
                    language=args.funasr_language,
                    hotwords=args.hotwords,
                    batch_size=args.funasr_batch_size,
                )
            elif args.adapter == "qwen3-asr-local":
                qwen3_language = args.qwen3_language.strip() or None
                summary = run_qwen3_asr_local_case(
                    case=case,
                    out_dir=out_dir,
                    model_info=model_info,
                    model=local_model,
                    language=qwen3_language,
                    context=args.qwen3_context,
                )
            elif args.adapter == "glm-asr-local":
                summary = run_glm_asr_local_case(
                    case=case,
                    out_dir=out_dir,
                    model_info=model_info,
                    model_bundle=local_model,
                    max_new_tokens=args.glm_asr_max_new_tokens,
                )
            elif args.adapter == "firered-asr2-aed-local":
                summary = run_firered_asr2_aed_local_case(
                    case=case,
                    out_dir=out_dir,
                    model_info=model_info,
                    model=local_model,
                )
            elif args.adapter == "mimo-asr-mlx-local":
                mimo_language = args.mimo_language.strip() or None
                summary = run_mimo_asr_mlx_local_case(
                    case=case,
                    out_dir=out_dir,
                    model_info=model_info,
                    model=local_model,
                    language=mimo_language,
                )
            elif args.adapter == "mlx-stt-local":
                mlx_stt_language = args.mlx_stt_language.strip() or None
                summary = run_mlx_stt_local_case(
                    case=case,
                    out_dir=out_dir,
                    model_info=model_info,
                    model=local_model,
                    language=mlx_stt_language,
                )
            else:
                raise ValueError(f"unsupported adapter: {args.adapter}")
        except Exception as exc:
            summary = {
                "case_id": case.case_id,
                "adapter": args.adapter,
                "model_info": model_info,
                "metric_explanations_zh": METRIC_EXPLANATIONS_ZH,
                "audio": str(case.audio_path),
                "expected_text": case.expected_text,
                "final_text": "",
                "status": "error",
                "error": str(exc),
            }
            write_json(out_dir / case.case_id / "summary.json", summary)
        summaries.append(summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    aggregate_path = out_dir / "summary.json"
    write_json(
        aggregate_path,
        {
            "model_info": model_info,
            "metric_explanations_zh": METRIC_EXPLANATIONS_ZH,
            "cases": summaries,
            "created_epoch_ms": now_ms(),
        },
    )
    failed = [s for s in summaries if s.get("status") not in {"ok", "no_text"}]
    return 1 if failed else 0


def command_run(args: argparse.Namespace) -> int:
    return asyncio.run(run_cases_async(args))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    list_models = sub.add_parser("list-models", help="List ASR model candidates from the registry.")
    list_models.add_argument("--registry", default="eval/asr_streaming/model_registry.json")
    list_models.set_defaults(func=command_list_models)

    validate_cases = sub.add_parser("validate-cases", help="Validate a case JSONL file.")
    validate_cases.add_argument("--cases", required=True)
    validate_cases.add_argument("--allow-missing-audio", action="store_true")
    validate_cases.set_defaults(func=command_validate_cases)

    self_test = sub.add_parser("self-test", help="Run internal transcript aggregation checks.")
    self_test.set_defaults(func=command_self_test)

    run = sub.add_parser("run", help="Run ASR evaluation cases.")
    run.add_argument(
        "--adapter",
        required=True,
        choices=[
            "funasr-ws",
            "funasr-nano-local",
            "qwen3-asr-local",
            "glm-asr-local",
            "firered-asr2-aed-local",
            "mimo-asr-mlx-local",
            "mlx-stt-local",
        ],
    )
    run.add_argument("--cases", required=True)
    run.add_argument("--out-dir", default="eval/asr_streaming/results")
    run.add_argument("--registry", default="eval/asr_streaming/model_registry.json")
    run.add_argument("--model-id", default="paraformer-current-funasr-ws")
    run.add_argument("--ws-url", default="ws://127.0.0.1:10095")
    run.add_argument("--chunk-ms", type=int, default=DEFAULT_CHUNK_MS)
    run.add_argument("--no-realtime", action="store_true", help="Send chunks without realtime sleeps.")
    run.add_argument("--receive-timeout-sec", type=float, default=3.0)
    run.add_argument("--hotwords", default="")
    run.add_argument("--no-itn", action="store_true")
    run.add_argument("--mode", default="2pass", choices=["online", "offline", "2pass"])
    run.add_argument("--funasr-nano-model", default=DEFAULT_FUNASR_NANO_MODEL)
    run.add_argument("--funasr-device", default="cpu")
    run.add_argument("--funasr-hub", default="hf", choices=["hf", "ms"])
    run.add_argument("--funasr-remote-code", default="./model.py")
    run.add_argument("--funasr-vad-model", default="")
    run.add_argument("--funasr-max-segment-ms", type=int, default=30000)
    run.add_argument("--funasr-language", default="中文")
    run.add_argument("--funasr-batch-size", type=int, default=1)
    run.add_argument("--qwen3-model", default=DEFAULT_QWEN3_ASR_MODEL)
    run.add_argument("--qwen3-device", default="cpu", choices=["auto", "cpu", "mps"])
    run.add_argument("--qwen3-device-map", default="")
    run.add_argument("--qwen3-dtype", default="auto", choices=["auto", "float32", "float16", "bfloat16"])
    run.add_argument("--qwen3-language", default="Chinese")
    run.add_argument("--qwen3-context", default="")
    run.add_argument("--qwen3-batch-size", type=int, default=1)
    run.add_argument("--qwen3-max-new-tokens", type=int, default=512)
    run.add_argument("--qwen3-local-files-only", action="store_true")
    run.add_argument("--glm-asr-model", default=DEFAULT_GLM_ASR_MODEL)
    run.add_argument("--glm-asr-device", default="cpu", choices=["auto", "cpu", "mps"])
    run.add_argument("--glm-asr-device-map", default="")
    run.add_argument("--glm-asr-dtype", default="auto", choices=["auto", "float32", "float16", "bfloat16"])
    run.add_argument("--glm-asr-max-new-tokens", type=int, default=512)
    run.add_argument("--glm-asr-local-files-only", action="store_true")
    run.add_argument("--firered-model", default=DEFAULT_FIRERED_ASR2_AED_MODEL)
    run.add_argument("--firered-source", default=DEFAULT_FIRERED_ASR2S_SOURCE)
    run.add_argument("--firered-use-gpu", action="store_true")
    run.add_argument("--firered-use-half", action="store_true")
    run.add_argument("--firered-beam-size", type=int, default=3)
    run.add_argument("--firered-decode-max-len", type=int, default=300)
    run.add_argument("--firered-softmax-smoothing", type=float, default=1.25)
    run.add_argument("--firered-aed-length-penalty", type=float, default=0.6)
    run.add_argument("--firered-eos-penalty", type=float, default=1.0)
    run.add_argument("--firered-return-timestamp", action="store_true")
    run.add_argument("--mimo-model", default=DEFAULT_MIMO_ASR_MLX_MODEL)
    run.add_argument("--mimo-audio-tokenizer-dir", default=DEFAULT_MIMO_AUDIO_TOKENIZER)
    run.add_argument("--mimo-language", default="zh")
    run.add_argument("--mlx-stt-model", default=DEFAULT_MLX_STT_MODEL)
    run.add_argument("--mlx-stt-language", default="Chinese")
    run.set_defaults(func=command_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
