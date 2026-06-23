#!/usr/bin/env python3
"""Small localhost HTTP service for incremental UX transport validation.

This is not an ASR model. It only validates that `incremental_ux_gate.py` can
drive a real process/HTTP boundary with the same start/chunk/finish contract
used by future local model services.
"""

from __future__ import annotations

import argparse
import base64
import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


@dataclass
class SessionState:
    session_id: str
    session_token: int
    case_id: str
    expected_text: str
    partial_emitted: bool = False


class FakeIncrementalState:
    def __init__(self) -> None:
        self.sessions: dict[str, SessionState] = {}

    def start(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        session = SessionState(
            session_id=str(payload["session_id"]),
            session_token=int(payload["session_token"]),
            case_id=str(payload.get("case_id", payload["session_id"])),
            expected_text=str(payload.get("expected_text", "")),
        )
        self.sessions[session.session_id] = session
        return []

    def chunk(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        session_id = str(payload["session_id"])
        session = self.sessions.get(session_id)
        if session is None:
            return [
                {
                    "kind": "ignored_missing_session",
                    "session_id": session_id,
                    "session_token": payload.get("session_token"),
                    "recv_offset_ms": payload.get("recv_offset_ms", 0.0),
                    "reason": "missing_session",
                }
            ]
        pcm_base64 = str(payload.get("pcm_base64", ""))
        if pcm_base64:
            base64.b64decode(pcm_base64.encode("ascii"), validate=True)
        audio_end_ms = float(payload.get("audio_end_ms", 0.0))
        if session.partial_emitted or audio_end_ms < 500.0:
            return []
        session.partial_emitted = True
        text = session.expected_text[: max(1, len(session.expected_text) // 2)]
        return [
            {
                "kind": "partial",
                "session_id": session.session_id,
                "session_token": session.session_token,
                "case_id": session.case_id,
                "recv_offset_ms": payload.get("recv_offset_ms", 0.0),
                "audio_end_ms": audio_end_ms,
                "mode": "fake_http_partial",
                "text": text,
            }
        ]

    def finish(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        session_id = str(payload["session_id"])
        session = self.sessions.get(session_id)
        if session is None:
            return [
                {
                    "kind": "ignored_missing_session",
                    "session_id": session_id,
                    "session_token": payload.get("session_token"),
                    "recv_offset_ms": payload.get("recv_offset_ms", 0.0),
                    "reason": "missing_session",
                }
            ]
        return [
            {
                "kind": "final",
                "session_id": session.session_id,
                "session_token": session.session_token,
                "case_id": session.case_id,
                "recv_offset_ms": payload.get("recv_offset_ms", 0.0),
                "mode": "fake_http_final",
                "text": session.expected_text,
            }
        ]

    def cancel(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        session_id = str(payload["session_id"])
        self.sessions.pop(session_id, None)
        return []


class Handler(BaseHTTPRequestHandler):
    state = FakeIncrementalState()

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_payload()
            if self.path == "/start":
                events = self.state.start(payload)
            elif self.path == "/chunk":
                events = self.state.chunk(payload)
            elif self.path == "/finish":
                events = self.state.finish(payload)
            elif self.path == "/cancel":
                events = self.state.cancel(payload)
            else:
                self._write_json({"error": f"unsupported path: {self.path}"}, status=404)
                return
            self._write_json({"events": events})
        except Exception as exc:
            self._write_json({"error": str(exc)}, status=500)

    def log_message(self, format: str, *args: Any) -> None:
        return None

    def _read_payload(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        payload = json.loads(raw) if raw else {}
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def _write_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18095)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"fake incremental HTTP service listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
