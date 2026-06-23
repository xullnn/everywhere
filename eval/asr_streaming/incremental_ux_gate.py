#!/usr/bin/env python3
"""Gate ASR backends for user-perceived incremental dictation UX.

This gate is backend-neutral. It replays 16 kHz mono int16 WAV files as timed
PCM chunks and checks whether a backend behaves like a local dictation service:
partial text appears before user stop, final text appears after stop, stale
session output is ignored, and cancel does not leak text.

The gate is intentionally separate from file-level ASR quality evaluation. A
model can produce excellent final transcripts and still fail this gate if it
cannot provide safe incremental session behavior.
"""

from __future__ import annotations

import argparse
import base64
import json
import statistics
import sys
import tempfile
import time
import urllib.error
import urllib.request
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_eval import (  # noqa: E402
    DEFAULT_CHUNK_MS,
    DEFAULT_MIN_COMPLETE_TEXT_RATIO,
    METRIC_EXPLANATIONS_ZH,
    EvalCase,
    append_jsonl,
    cer,
    char_length_ratio,
    load_cases,
    load_model_metadata,
    monotonic_ms,
    now_ms,
    partial_rewrite_rate,
    read_wav_16k_mono_int16,
    wer,
    write_json,
)


UX_GATE_SCHEMA_VERSION = "1.0"

UX_METRIC_EXPLANATIONS_ZH: dict[str, str] = {
    **METRIC_EXPLANATIONS_ZH,
    "incremental_ux_gate_passed": "是否通过用户感知实时语音输入门槛。true 表示该 case 同时满足录音期间有 partial、用户停止后有 final、事件顺序安全、延迟和覆盖率达标。",
    "gate_fail_reasons": "未通过 incremental UX gate 的原因列表，用于区分 final-only、延迟、late partial、cancel 泄漏和旧 session 污染等问题。",
    "native_realtime_gate_eligible": "是否证明为模型原生实时流式。该 gate 只验证用户感知实时行为；累计重算 wrapper 仍应标记为 false。",
    "input_realtime_pacing": "是否按真实音频时间 sleep 推送 PCM chunk。true 更接近麦克风输入；false 只适合快速协议测试。",
    "input_finished_offset_ms": "最后一个 PCM chunk 推送完成的本地相对时间，近似用户松开快捷键或停止长文本模式的时间。",
    "first_partial_latency_ms": "从开始推送音频到首个 accepted partial 到达的时间，单位毫秒，越低越好。",
    "partial_cadence_ms": "相邻 accepted partial 的平均到达间隔，单位毫秒，用于观察浮窗更新密度。",
    "final_latency_ms": "用户停止输入后 accepted final 到达的延迟，单位毫秒，越低越好。",
    "partial_before_stop_count": "用户停止输入前 accepted partial 数量。实时浮窗体验要求该值大于 0。",
    "final_after_stop_count": "用户停止输入后 accepted final 数量。最终输出必须发生在停止之后。",
    "partial_rewrite_rate": "相邻 partial 之间文本被改写的粗略比例，越高说明浮窗文本越不稳定。",
    "final_coverage_ratio": "最终文本归一化字符长度与标准答案长度之比。过低说明 final 疑似漏识别或严重不完整。",
    "partial_after_final": "是否存在 accepted final 之后又出现 accepted partial。true 表示事件顺序不适合直接接入 App。",
    "accepted_output_after_cancel": "cancel 后是否仍出现 accepted partial/final。true 表示取消路径会泄漏文本，不能接入 App。",
    "ignored_stale_event_count": "被服务拒绝的旧 session、cancel 后、final 后或 token 不匹配事件数量。非 0 不一定失败，关键是它们不能变成 accepted 输出。",
}


@dataclass
class GateSession:
    session_id: str
    token: int
    case_id: str
    expected_text: str
    status: str = "recording"
    input_finished_offset_ms: float | None = None


class IncrementalBackend(Protocol):
    name: str
    native_realtime_gate_eligible: bool

    def on_start(self, service: "IncrementalSessionService", session: GateSession, *, recv_offset_ms: float) -> None:
        ...

    def on_chunk(
        self,
        service: "IncrementalSessionService",
        session: GateSession,
        *,
        recv_offset_ms: float,
        audio_start_ms: float,
        audio_end_ms: float,
        chunk_index: int,
        pcm: bytes,
    ) -> None:
        ...

    def on_finish(self, service: "IncrementalSessionService", session: GateSession, *, recv_offset_ms: float) -> None:
        ...


class IncrementalSessionService:
    def __init__(self, backend: IncrementalBackend):
        self.backend = backend
        self.sessions: dict[str, GateSession] = {}
        self.events: list[dict[str, Any]] = []
        self._token_counter = 0

    def start(self, session_id: str, *, case_id: str, expected_text: str, recv_offset_ms: float = 0.0) -> int:
        self._token_counter += 1
        session = GateSession(
            session_id=session_id,
            token=self._token_counter,
            case_id=case_id,
            expected_text=expected_text,
        )
        self.sessions[session_id] = session
        self._append_event(
            {
                "kind": "session_started",
                "session_id": session_id,
                "session_token": session.token,
                "case_id": case_id,
                "recv_offset_ms": recv_offset_ms,
                "accepted": False,
                "is_final": False,
            }
        )
        self.backend.on_start(self, session, recv_offset_ms=recv_offset_ms)
        return session.token

    def push_pcm(
        self,
        session_id: str,
        pcm: bytes,
        *,
        recv_offset_ms: float,
        audio_start_ms: float,
        audio_end_ms: float,
        chunk_index: int,
    ) -> None:
        session = self.sessions.get(session_id)
        if session is None or session.status != "recording":
            self._append_ignored(
                kind="ignored_chunk",
                session_id=session_id,
                recv_offset_ms=recv_offset_ms,
                reason="session_not_recording",
                chunk_index=chunk_index,
                audio_start_ms=audio_start_ms,
                audio_end_ms=audio_end_ms,
            )
            return
        self._append_event(
            {
                "kind": "chunk_received",
                "session_id": session_id,
                "session_token": session.token,
                "case_id": session.case_id,
                "recv_offset_ms": recv_offset_ms,
                "chunk_index": chunk_index,
                "audio_start_ms": audio_start_ms,
                "audio_end_ms": audio_end_ms,
                "byte_count": len(pcm),
                "accepted": False,
                "is_final": False,
            }
        )
        self.backend.on_chunk(
            self,
            session,
            recv_offset_ms=recv_offset_ms,
            audio_start_ms=audio_start_ms,
            audio_end_ms=audio_end_ms,
            chunk_index=chunk_index,
            pcm=pcm,
        )

    def finish(self, session_id: str, *, recv_offset_ms: float) -> None:
        session = self.sessions.get(session_id)
        if session is None:
            self._append_ignored(
                kind="ignored_finish",
                session_id=session_id,
                recv_offset_ms=recv_offset_ms,
                reason="missing_session",
            )
            return
        if session.status == "canceled":
            self._append_ignored(
                kind="ignored_finish",
                session_id=session_id,
                session_token=session.token,
                recv_offset_ms=recv_offset_ms,
                reason="session_canceled",
            )
            return
        if session.status == "finalized":
            self._append_ignored(
                kind="ignored_finish",
                session_id=session_id,
                session_token=session.token,
                recv_offset_ms=recv_offset_ms,
                reason="session_finalized",
            )
            return
        session.input_finished_offset_ms = recv_offset_ms
        session.status = "finishing"
        self._append_event(
            {
                "kind": "finish_requested",
                "session_id": session_id,
                "session_token": session.token,
                "case_id": session.case_id,
                "recv_offset_ms": recv_offset_ms,
                "accepted": False,
                "is_final": False,
            }
        )
        self.backend.on_finish(self, session, recv_offset_ms=recv_offset_ms)

    def cancel(self, session_id: str, *, recv_offset_ms: float) -> None:
        session = self.sessions.get(session_id)
        token = None
        case_id = None
        if session is not None:
            session.status = "canceled"
            token = session.token
            case_id = session.case_id
        self._append_event(
            {
                "kind": "session_canceled",
                "session_id": session_id,
                "session_token": token,
                "case_id": case_id,
                "recv_offset_ms": recv_offset_ms,
                "accepted": False,
                "is_final": False,
            }
        )
        on_cancel = getattr(self.backend, "on_cancel", None)
        if callable(on_cancel) and session is not None:
            on_cancel(self, session, recv_offset_ms=recv_offset_ms)

    def emit_partial(
        self,
        session_id: str,
        session_token: int,
        *,
        text: str,
        recv_offset_ms: float,
        audio_end_ms: float | None = None,
        mode: str = "partial",
    ) -> bool:
        session = self.sessions.get(session_id)
        if session is None:
            self._append_ignored(
                kind="ignored_stale_partial",
                session_id=session_id,
                session_token=session_token,
                recv_offset_ms=recv_offset_ms,
                reason="missing_session",
                text=text,
            )
            return False
        if session.token != session_token:
            self._append_ignored(
                kind="ignored_stale_partial",
                session_id=session_id,
                session_token=session_token,
                current_session_token=session.token,
                recv_offset_ms=recv_offset_ms,
                reason="session_token_mismatch",
                text=text,
            )
            return False
        if session.status != "recording":
            self._append_ignored(
                kind="ignored_stale_partial",
                session_id=session_id,
                session_token=session_token,
                recv_offset_ms=recv_offset_ms,
                reason=f"session_not_recording:{session.status}",
                text=text,
            )
            return False
        self._append_event(
            {
                "kind": "partial",
                "session_id": session_id,
                "session_token": session_token,
                "case_id": session.case_id,
                "recv_offset_ms": recv_offset_ms,
                "audio_end_ms": audio_end_ms,
                "mode": mode,
                "text": text,
                "accepted": True,
                "is_final": False,
            }
        )
        return True

    def emit_final(
        self,
        session_id: str,
        session_token: int,
        *,
        text: str,
        recv_offset_ms: float,
        mode: str = "final",
    ) -> bool:
        session = self.sessions.get(session_id)
        if session is None:
            self._append_ignored(
                kind="ignored_stale_final",
                session_id=session_id,
                session_token=session_token,
                recv_offset_ms=recv_offset_ms,
                reason="missing_session",
                text=text,
            )
            return False
        if session.token != session_token:
            self._append_ignored(
                kind="ignored_stale_final",
                session_id=session_id,
                session_token=session_token,
                current_session_token=session.token,
                recv_offset_ms=recv_offset_ms,
                reason="session_token_mismatch",
                text=text,
            )
            return False
        if session.status not in {"recording", "finishing"}:
            self._append_ignored(
                kind="ignored_stale_final",
                session_id=session_id,
                session_token=session_token,
                recv_offset_ms=recv_offset_ms,
                reason=f"session_not_recording_or_finishing:{session.status}",
                text=text,
            )
            return False
        session.status = "finalized"
        self._append_event(
            {
                "kind": "final",
                "session_id": session_id,
                "session_token": session_token,
                "case_id": session.case_id,
                "recv_offset_ms": recv_offset_ms,
                "mode": mode,
                "text": text,
                "accepted": True,
                "is_final": True,
            }
        )
        return True

    def force_accepted_event(self, event: dict[str, Any]) -> None:
        """Append a deliberately unsafe event for negative gate tests."""
        event.setdefault("accepted", True)
        event.setdefault("recv_epoch_ms", now_ms())
        self.events.append(event)

    def _append_ignored(self, **event: Any) -> None:
        event.setdefault("accepted", False)
        event.setdefault("is_final", False)
        self._append_event(event)

    def _append_event(self, event: dict[str, Any]) -> None:
        event.setdefault("recv_epoch_ms", now_ms())
        self.events.append(event)


class FakeValidBackend:
    name = "fake-valid"
    native_realtime_gate_eligible = False

    def __init__(self) -> None:
        self._partial_emitted: set[tuple[str, int]] = set()

    def on_start(self, service: IncrementalSessionService, session: GateSession, *, recv_offset_ms: float) -> None:
        return None

    def on_chunk(
        self,
        service: IncrementalSessionService,
        session: GateSession,
        *,
        recv_offset_ms: float,
        audio_start_ms: float,
        audio_end_ms: float,
        chunk_index: int,
        pcm: bytes,
    ) -> None:
        key = (session.session_id, session.token)
        if audio_end_ms >= 500.0 and key not in self._partial_emitted:
            text = session.expected_text[: max(1, len(session.expected_text) // 2)]
            service.emit_partial(
                session.session_id,
                session.token,
                text=text,
                recv_offset_ms=recv_offset_ms,
                audio_end_ms=audio_end_ms,
                mode="fake_valid_partial",
            )
            self._partial_emitted.add(key)

    def on_finish(self, service: IncrementalSessionService, session: GateSession, *, recv_offset_ms: float) -> None:
        service.emit_final(
            session.session_id,
            session.token,
            text=session.expected_text,
            recv_offset_ms=recv_offset_ms,
            mode="fake_valid_final",
        )


class FakeFinalOnlyBackend(FakeValidBackend):
    name = "fake-final-only"

    def on_chunk(
        self,
        service: IncrementalSessionService,
        session: GateSession,
        *,
        recv_offset_ms: float,
        audio_start_ms: float,
        audio_end_ms: float,
        chunk_index: int,
        pcm: bytes,
    ) -> None:
        return None


class FakeLatePartialBackend(FakeValidBackend):
    name = "fake-late-partial"

    def on_finish(self, service: IncrementalSessionService, session: GateSession, *, recv_offset_ms: float) -> None:
        service.emit_final(
            session.session_id,
            session.token,
            text=session.expected_text,
            recv_offset_ms=recv_offset_ms,
            mode="fake_late_final",
        )
        service.force_accepted_event(
            {
                "kind": "partial",
                "session_id": session.session_id,
                "session_token": session.token,
                "case_id": session.case_id,
                "recv_offset_ms": recv_offset_ms + 1.0,
                "mode": "fake_unsafe_late_partial",
                "text": "late partial should fail",
                "accepted": True,
                "is_final": False,
            }
        )


class HttpJsonBackend:
    name = "http-json"
    native_realtime_gate_eligible = False

    def __init__(self, *, service_url: str, timeout_sec: float):
        if not service_url:
            raise ValueError("--service-url is required for --adapter http-json")
        self.service_url = service_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def on_start(self, service: IncrementalSessionService, session: GateSession, *, recv_offset_ms: float) -> None:
        response = self._post(
            "/start",
            {
                "session_id": session.session_id,
                "session_token": session.token,
                "case_id": session.case_id,
                "expected_text": session.expected_text,
                "recv_offset_ms": recv_offset_ms,
            },
        )
        self._emit_response_events(service, session, response, default_recv_offset_ms=recv_offset_ms)

    def on_chunk(
        self,
        service: IncrementalSessionService,
        session: GateSession,
        *,
        recv_offset_ms: float,
        audio_start_ms: float,
        audio_end_ms: float,
        chunk_index: int,
        pcm: bytes,
    ) -> None:
        response = self._post(
            "/chunk",
            {
                "session_id": session.session_id,
                "session_token": session.token,
                "case_id": session.case_id,
                "recv_offset_ms": recv_offset_ms,
                "audio_start_ms": audio_start_ms,
                "audio_end_ms": audio_end_ms,
                "chunk_index": chunk_index,
                "pcm_base64": base64.b64encode(pcm).decode("ascii"),
                "sample_rate": 16000,
                "sample_width_bytes": 2,
                "channels": 1,
            },
        )
        self._emit_response_events(service, session, response, default_recv_offset_ms=recv_offset_ms)

    def on_finish(self, service: IncrementalSessionService, session: GateSession, *, recv_offset_ms: float) -> None:
        response = self._post(
            "/finish",
            {
                "session_id": session.session_id,
                "session_token": session.token,
                "case_id": session.case_id,
                "recv_offset_ms": recv_offset_ms,
            },
        )
        self._emit_response_events(service, session, response, default_recv_offset_ms=recv_offset_ms)

    def on_cancel(self, service: IncrementalSessionService, session: GateSession, *, recv_offset_ms: float) -> None:
        response = self._post(
            "/cancel",
            {
                "session_id": session.session_id,
                "session_token": session.token,
                "case_id": session.case_id,
                "recv_offset_ms": recv_offset_ms,
            },
        )
        self._emit_response_events(service, session, response, default_recv_offset_ms=recv_offset_ms)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.service_url}{path}",
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw_error = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"http-json backend request failed for {path}: HTTP {exc.code}: {raw_error[:500]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"http-json backend request failed for {path}: {exc}") from exc
        if not raw.strip():
            return {"events": []}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"http-json backend returned invalid JSON for {path}: {raw[:200]}") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError(f"http-json backend response must be a JSON object for {path}")
        if parsed.get("error"):
            raise RuntimeError(f"http-json backend error for {path}: {parsed['error']}")
        return parsed

    def _emit_response_events(
        self,
        service: IncrementalSessionService,
        session: GateSession,
        response: dict[str, Any],
        *,
        default_recv_offset_ms: float,
    ) -> None:
        raw_events = response.get("events", [])
        if isinstance(response.get("kind"), str):
            raw_events = [response]
        if not isinstance(raw_events, list):
            raise RuntimeError("http-json backend response field 'events' must be a list")
        for raw_event in raw_events:
            if not isinstance(raw_event, dict):
                service._append_ignored(
                    kind="ignored_backend_event",
                    session_id=session.session_id,
                    session_token=session.token,
                    recv_offset_ms=default_recv_offset_ms,
                    reason="event_not_object",
                    event_repr=repr(raw_event),
                )
                continue
            kind = str(raw_event.get("kind", ""))
            event_session_id = str(raw_event.get("session_id") or session.session_id)
            event_token = int(raw_event.get("session_token", session.token))
            recv_offset_ms = float(raw_event.get("recv_offset_ms", default_recv_offset_ms))
            text = str(raw_event.get("text", ""))
            if kind == "partial":
                service.emit_partial(
                    event_session_id,
                    event_token,
                    text=text,
                    recv_offset_ms=recv_offset_ms,
                    audio_end_ms=raw_event.get("audio_end_ms"),
                    mode=str(raw_event.get("mode", "http_json_partial")),
                )
            elif kind == "final":
                service.emit_final(
                    event_session_id,
                    event_token,
                    text=text,
                    recv_offset_ms=recv_offset_ms,
                    mode=str(raw_event.get("mode", "http_json_final")),
                )
            elif kind.startswith("ignored"):
                service._append_ignored(**{**raw_event, "recv_offset_ms": recv_offset_ms})
            elif kind:
                service._append_ignored(
                    kind="ignored_backend_event",
                    session_id=event_session_id,
                    session_token=event_token,
                    recv_offset_ms=recv_offset_ms,
                    reason=f"unsupported_backend_event:{kind}",
                    text=text,
                )


def create_backend(adapter: str, *, service_url: str | None = None, request_timeout_sec: float = 30.0) -> IncrementalBackend:
    if adapter == "fake-valid":
        return FakeValidBackend()
    if adapter == "fake-final-only":
        return FakeFinalOnlyBackend()
    if adapter == "fake-late-partial":
        return FakeLatePartialBackend()
    if adapter == "http-json":
        return HttpJsonBackend(service_url=service_url or "", timeout_sec=request_timeout_sec)
    raise ValueError(f"unsupported incremental UX gate adapter: {adapter}")


def mean_number(values: list[Any]) -> float | None:
    numbers = [float(value) for value in values if isinstance(value, (int, float))]
    return statistics.mean(numbers) if numbers else None


def summarize_partial_cadence(partials: list[dict[str, Any]]) -> float | None:
    offsets = [float(e["recv_offset_ms"]) for e in partials if isinstance(e.get("recv_offset_ms"), (int, float))]
    if len(offsets) < 2:
        return None
    return statistics.mean([b - a for a, b in zip(offsets, offsets[1:])])


def evaluate_incremental_gate(
    *,
    events: list[dict[str, Any]],
    expected_text: str,
    input_finished_offset_ms: float,
    duration_seconds: float,
    run_wall_seconds: float,
    max_first_partial_ms: float,
    max_final_latency_ms: float,
    min_final_coverage_ratio: float,
    max_rtf: float,
    fail_on_high_rtf: bool,
) -> dict[str, Any]:
    accepted_partials = [
        e for e in events if e.get("accepted") is True and e.get("kind") == "partial" and str(e.get("text", "")).strip()
    ]
    accepted_finals = [
        e for e in events if e.get("accepted") is True and e.get("kind") == "final" and str(e.get("text", "")).strip()
    ]
    ignored_events = [e for e in events if str(e.get("kind", "")).startswith("ignored")]
    partials_before_stop = [
        e
        for e in accepted_partials
        if isinstance(e.get("recv_offset_ms"), (int, float)) and float(e["recv_offset_ms"]) <= input_finished_offset_ms
    ]
    finals_after_stop = [
        e
        for e in accepted_finals
        if isinstance(e.get("recv_offset_ms"), (int, float)) and float(e["recv_offset_ms"]) >= input_finished_offset_ms
    ]
    first_partial_latency = (
        float(accepted_partials[0]["recv_offset_ms"])
        if accepted_partials and isinstance(accepted_partials[0].get("recv_offset_ms"), (int, float))
        else None
    )
    final_text = str(accepted_finals[-1]["text"]) if accepted_finals else ""
    final_offset = (
        float(accepted_finals[-1]["recv_offset_ms"])
        if accepted_finals and isinstance(accepted_finals[-1].get("recv_offset_ms"), (int, float))
        else None
    )
    final_latency = None if final_offset is None else final_offset - input_finished_offset_ms
    final_coverage_ratio = char_length_ratio(final_text, expected_text)
    rtf = (run_wall_seconds / duration_seconds) if duration_seconds > 0 else None
    partial_after_final = bool(
        final_offset is not None
        and any(
            isinstance(e.get("recv_offset_ms"), (int, float)) and float(e["recv_offset_ms"]) > final_offset
            for e in accepted_partials
        )
    )
    accepted_output_after_cancel = any(
        e.get("accepted") is True
        and e.get("kind") in {"partial", "final"}
        and bool(e.get("after_cancel"))
        for e in events
    )
    accepted_stale_event = any(
        e.get("accepted") is True
        and e.get("kind") in {"partial", "final"}
        and bool(e.get("stale_acceptance"))
        for e in events
    )

    fail_reasons: list[str] = []
    if not accepted_partials:
        fail_reasons.append("no_partial_events")
    if not partials_before_stop:
        fail_reasons.append("no_partial_before_user_stop")
    if first_partial_latency is None:
        fail_reasons.append("missing_first_partial_latency")
    elif first_partial_latency > max_first_partial_ms:
        fail_reasons.append("first_partial_too_slow")
    if not final_text:
        fail_reasons.append("missing_final_text")
    if not finals_after_stop:
        fail_reasons.append("no_final_after_user_stop")
    if final_latency is None:
        fail_reasons.append("missing_final_latency")
    elif final_latency > max_final_latency_ms:
        fail_reasons.append("final_latency_too_slow")
    if final_coverage_ratio is not None and final_coverage_ratio < min_final_coverage_ratio:
        fail_reasons.append("final_coverage_too_low")
    if partial_after_final:
        fail_reasons.append("partial_after_final")
    if accepted_output_after_cancel:
        fail_reasons.append("accepted_output_after_cancel")
    if accepted_stale_event:
        fail_reasons.append("accepted_stale_event")
    if fail_on_high_rtf and isinstance(rtf, (int, float)) and rtf > max_rtf:
        fail_reasons.append("rtf_too_high")

    partial_texts = [str(e.get("text", "")) for e in accepted_partials]
    return {
        "gate_schema_version": UX_GATE_SCHEMA_VERSION,
        "incremental_ux_gate_passed": not fail_reasons,
        "gate_fail_reasons": fail_reasons,
        "gate_thresholds": {
            "max_first_partial_ms": max_first_partial_ms,
            "max_final_latency_ms": max_final_latency_ms,
            "min_final_coverage_ratio": min_final_coverage_ratio,
            "max_rtf": max_rtf,
            "fail_on_high_rtf": fail_on_high_rtf,
        },
        "partial_before_stop_count": len(partials_before_stop),
        "final_after_stop_count": len(finals_after_stop),
        "first_partial_latency_ms": first_partial_latency,
        "partial_cadence_ms": summarize_partial_cadence(accepted_partials),
        "final_latency_ms": final_latency,
        "partial_rewrite_rate": partial_rewrite_rate(partial_texts),
        "final_coverage_ratio": final_coverage_ratio,
        "partial_after_final": partial_after_final,
        "accepted_output_after_cancel": accepted_output_after_cancel,
        "accepted_stale_event": accepted_stale_event,
        "ignored_stale_event_count": len(ignored_events),
        "final_text": final_text,
        "cer": cer(expected_text, final_text),
        "wer": wer(expected_text, final_text),
        "rtf": rtf,
    }


def run_gate_case(
    *,
    case: EvalCase,
    backend: IncrementalBackend,
    out_dir: Path,
    chunk_ms: int,
    realtime: bool,
    model_info: dict[str, Any],
    max_first_partial_ms: float,
    max_final_latency_ms: float,
    min_final_coverage_ratio: float,
    max_rtf: float,
    fail_on_high_rtf: bool,
) -> dict[str, Any]:
    audio = read_wav_16k_mono_int16(case.audio_path)
    case_out = out_dir / case.case_id
    events_path = case_out / "events.jsonl"
    chunks_path = case_out / "chunks.jsonl"
    for path in (events_path, chunks_path):
        if path.exists():
            path.unlink()
    case_out.mkdir(parents=True, exist_ok=True)

    bytes_per_ms = audio.sample_rate * audio.sample_width * audio.channels / 1000.0
    stride = max(audio.sample_width, int(bytes_per_ms * chunk_ms))
    if stride % audio.sample_width:
        stride += audio.sample_width - (stride % audio.sample_width)

    service = IncrementalSessionService(backend)
    start_perf = time.perf_counter()
    session_id = case.case_id
    service.start(session_id, case_id=case.case_id, expected_text=case.expected_text, recv_offset_ms=0.0)
    chunk_records: list[dict[str, Any]] = []

    for index, offset in enumerate(range(0, len(audio.pcm), stride)):
        chunk = audio.pcm[offset : offset + stride]
        recv_offset = monotonic_ms(start_perf)
        audio_start_ms = offset / bytes_per_ms
        audio_end_ms = (offset + len(chunk)) / bytes_per_ms
        chunk_record = {
            "case_id": case.case_id,
            "chunk_index": index,
            "send_offset_ms": recv_offset,
            "audio_start_ms": audio_start_ms,
            "audio_end_ms": audio_end_ms,
            "byte_count": len(chunk),
        }
        chunk_records.append(chunk_record)
        append_jsonl(chunks_path, chunk_record)
        service.push_pcm(
            session_id,
            chunk,
            recv_offset_ms=recv_offset,
            audio_start_ms=audio_start_ms,
            audio_end_ms=audio_end_ms,
            chunk_index=index,
        )
        if realtime:
            time.sleep(chunk_ms / 1000.0)

    input_finished_offset_ms = monotonic_ms(start_perf)
    service.finish(session_id, recv_offset_ms=input_finished_offset_ms)
    run_wall_seconds = time.perf_counter() - start_perf
    case_events = [e for e in service.events if e.get("case_id") in {None, case.case_id}]
    for event in case_events:
        append_jsonl(events_path, event)

    gate = evaluate_incremental_gate(
        events=case_events,
        expected_text=case.expected_text,
        input_finished_offset_ms=input_finished_offset_ms,
        duration_seconds=audio.duration_seconds,
        run_wall_seconds=run_wall_seconds,
        max_first_partial_ms=max_first_partial_ms,
        max_final_latency_ms=max_final_latency_ms,
        min_final_coverage_ratio=min_final_coverage_ratio,
        max_rtf=max_rtf,
        fail_on_high_rtf=fail_on_high_rtf,
    )
    summary = {
        "schema_version": UX_GATE_SCHEMA_VERSION,
        "created_epoch_ms": now_ms(),
        "case_id": case.case_id,
        "adapter": backend.name,
        "model_info": model_info,
        "metric_explanations_zh": UX_METRIC_EXPLANATIONS_ZH,
        "audio": str(case.audio_path),
        "duration_seconds": audio.duration_seconds,
        "lang": case.lang,
        "scenario": case.scenario,
        "expected_text": case.expected_text,
        "input_realtime_pacing": realtime,
        "input_finished_offset_ms": input_finished_offset_ms,
        "chunk_ms": chunk_ms,
        "input_chunk_count": len(chunk_records),
        "input_chunk_trace": str(chunks_path),
        "event_trace": str(events_path),
        "event_count": len(case_events),
        "native_realtime_gate_eligible": backend.native_realtime_gate_eligible,
        **gate,
    }
    write_json(case_out / "summary.json", summary)
    return summary


def aggregate_results(*, summaries: list[dict[str, Any]], adapter: str, model_info: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    passed = [s for s in summaries if bool(s.get("incremental_ux_gate_passed"))]
    failed = [s for s in summaries if not bool(s.get("incremental_ux_gate_passed"))]
    fail_reason_counts: dict[str, int] = {}
    for summary in failed:
        for reason in summary.get("gate_fail_reasons") or []:
            fail_reason_counts[str(reason)] = fail_reason_counts.get(str(reason), 0) + 1
    return {
        "schema_version": UX_GATE_SCHEMA_VERSION,
        "created_epoch_ms": now_ms(),
        "adapter": adapter,
        "model_info": model_info,
        "metric_explanations_zh": UX_METRIC_EXPLANATIONS_ZH,
        "incremental_ux_gate_passed": bool(summaries) and not failed,
        "native_realtime_gate_eligible": False,
        "aggregate_metrics": {
            "case_count": len(summaries),
            "passed_count": len(passed),
            "failed_count": len(failed),
            "mean_cer": mean_number([s.get("cer") for s in summaries]),
            "mean_wer": mean_number([s.get("wer") for s in summaries]),
            "mean_rtf": mean_number([s.get("rtf") for s in summaries]),
            "mean_first_partial_latency_ms": mean_number([s.get("first_partial_latency_ms") for s in summaries]),
            "mean_partial_cadence_ms": mean_number([s.get("partial_cadence_ms") for s in summaries]),
            "mean_final_latency_ms": mean_number([s.get("final_latency_ms") for s in summaries]),
            "mean_partial_rewrite_rate": mean_number([s.get("partial_rewrite_rate") for s in summaries]),
            "mean_final_coverage_ratio": mean_number([s.get("final_coverage_ratio") for s in summaries]),
            "fail_reason_counts": fail_reason_counts,
        },
        "gate_config": {
            "chunk_ms": args.chunk_ms,
            "input_realtime_pacing": not args.no_realtime,
            "transport": args.adapter,
            "service_url": args.service_url if args.adapter == "http-json" else None,
            "max_first_partial_ms": args.max_first_partial_ms,
            "max_final_latency_ms": args.max_final_latency_ms,
            "min_final_coverage_ratio": args.min_final_coverage_ratio,
            "max_rtf": args.max_rtf,
            "fail_on_high_rtf": args.fail_on_high_rtf,
            "warn_only": args.warn_only,
        },
        "cases": summaries,
    }


def command_run(args: argparse.Namespace) -> int:
    cases = load_cases(Path(args.cases), allow_missing_audio=False)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_info = load_model_metadata(Path(args.registry), args.model_id)
    backend = create_backend(
        args.adapter,
        service_url=args.service_url,
        request_timeout_sec=args.request_timeout_sec,
    )
    summaries = [
        run_gate_case(
            case=case,
            backend=backend,
            out_dir=out_dir,
            chunk_ms=args.chunk_ms,
            realtime=not args.no_realtime,
            model_info=model_info,
            max_first_partial_ms=args.max_first_partial_ms,
            max_final_latency_ms=args.max_final_latency_ms,
            min_final_coverage_ratio=args.min_final_coverage_ratio,
            max_rtf=args.max_rtf,
            fail_on_high_rtf=args.fail_on_high_rtf,
        )
        for case in cases
    ]
    aggregate = aggregate_results(summaries=summaries, adapter=args.adapter, model_info=model_info, args=args)
    write_json(out_dir / "summary.json", aggregate)
    print(json.dumps(aggregate, ensure_ascii=False, sort_keys=True))
    if args.warn_only:
        return 0
    return 0 if bool(aggregate["incremental_ux_gate_passed"]) else 1


def write_test_wav(path: Path, duration_ms: int = 1200) -> None:
    frame_count = int(16000 * duration_ms / 1000.0)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * frame_count)


def run_temp_case(adapter: str, tmp: Path) -> dict[str, Any]:
    wav_path = tmp / "unit.wav"
    write_test_wav(wav_path)
    case = EvalCase(
        case_id=f"unit_{adapter.replace('-', '_')}",
        audio_path=wav_path,
        expected_text="今天测试本地语音输入",
        lang="zh",
        scenario="unit",
        metadata={},
    )
    return run_gate_case(
        case=case,
        backend=create_backend(adapter),
        out_dir=tmp / adapter,
        chunk_ms=100,
        realtime=False,
        model_info={},
        max_first_partial_ms=1000.0,
        max_final_latency_ms=500.0,
        min_final_coverage_ratio=0.70,
        max_rtf=1.50,
        fail_on_high_rtf=False,
    )


def command_self_test(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="localvoiceinput-incremental-gate-") as raw_tmp:
        tmp = Path(raw_tmp)
        valid = run_temp_case("fake-valid", tmp)
        if not valid["incremental_ux_gate_passed"]:
            raise AssertionError(f"valid fake backend should pass: {valid}")

        final_only = run_temp_case("fake-final-only", tmp)
        expected_reasons = {"no_partial_events", "no_partial_before_user_stop"}
        if final_only["incremental_ux_gate_passed"] or not expected_reasons.issubset(set(final_only["gate_fail_reasons"])):
            raise AssertionError(f"final-only backend should fail as non-incremental: {final_only}")

        late = run_temp_case("fake-late-partial", tmp)
        if late["incremental_ux_gate_passed"] or "partial_after_final" not in set(late["gate_fail_reasons"]):
            raise AssertionError(f"late partial backend should fail: {late}")

    service = IncrementalSessionService(FakeValidBackend())
    old_token = service.start("same", case_id="same_old", expected_text="旧文本", recv_offset_ms=0.0)
    new_token = service.start("same", case_id="same_new", expected_text="新文本", recv_offset_ms=10.0)
    accepted_old = service.emit_partial("same", old_token, text="old should ignore", recv_offset_ms=20.0)
    accepted_new = service.emit_partial("same", new_token, text="new should accept", recv_offset_ms=30.0)
    if accepted_old or not accepted_new:
        raise AssertionError(f"stale token handling failed: {service.events}")
    if not any(e.get("kind") == "ignored_stale_partial" for e in service.events):
        raise AssertionError(f"missing ignored stale event: {service.events}")

    cancel_service = IncrementalSessionService(FakeValidBackend())
    cancel_token = cancel_service.start("cancel", case_id="cancel", expected_text="取消文本", recv_offset_ms=0.0)
    cancel_service.cancel("cancel", recv_offset_ms=100.0)
    accepted_partial = cancel_service.emit_partial("cancel", cancel_token, text="leak", recv_offset_ms=120.0)
    accepted_final = cancel_service.emit_final("cancel", cancel_token, text="leak", recv_offset_ms=130.0)
    if accepted_partial or accepted_final:
        raise AssertionError(f"cancel leaked accepted output: {cancel_service.events}")
    cancel_gate = evaluate_incremental_gate(
        events=cancel_service.events,
        expected_text="取消文本",
        input_finished_offset_ms=100.0,
        duration_seconds=1.0,
        run_wall_seconds=0.1,
        max_first_partial_ms=1000.0,
        max_final_latency_ms=500.0,
        min_final_coverage_ratio=0.70,
        max_rtf=1.50,
        fail_on_high_rtf=False,
    )
    if cancel_gate["accepted_output_after_cancel"]:
        raise AssertionError(f"cancel gate saw accepted output: {cancel_gate}")

    print("Incremental UX ASR gate self-test passed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    self_test = sub.add_parser("self-test", help="Run fake-backend gate self-tests.")
    self_test.set_defaults(func=command_self_test)

    run = sub.add_parser("run", help="Run incremental UX gate cases.")
    run.add_argument("--adapter", required=True, choices=["fake-valid", "fake-final-only", "fake-late-partial", "http-json"])
    run.add_argument("--service-url", default=None, help="Required for http-json, for example http://127.0.0.1:18095")
    run.add_argument("--request-timeout-sec", type=float, default=30.0, help="Per-request timeout for transport adapters.")
    run.add_argument("--cases", required=True)
    run.add_argument("--out-dir", default="eval/asr_streaming/results/incremental-ux-gate")
    run.add_argument("--registry", default="eval/asr_streaming/model_registry.json")
    run.add_argument("--model-id", default="paraformer-current-funasr-ws")
    run.add_argument("--chunk-ms", type=int, default=DEFAULT_CHUNK_MS)
    run.add_argument("--no-realtime", action="store_true", help="Send chunks without realtime sleeps; diagnostic only.")
    run.add_argument("--max-first-partial-ms", type=float, default=1500.0)
    run.add_argument("--max-final-latency-ms", type=float, default=2500.0)
    run.add_argument("--min-final-coverage-ratio", type=float, default=DEFAULT_MIN_COMPLETE_TEXT_RATIO)
    run.add_argument("--max-rtf", type=float, default=1.50)
    run.add_argument("--fail-on-high-rtf", action="store_true")
    run.add_argument("--warn-only", action="store_true", help="Write summaries but return zero even when the gate fails.")
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
