# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Shared utilities for the civic-services mesh simulator agents.

Three concerns:

1. The referral envelope shape — must round-trip with the
   ``propose_referral`` MCP tool's output (see
   ``company_discovery/mcp_tools.py:propose_referral``).
2. A per-agent append-only JSONL audit log so the end-to-end
   demo can show the decision trail across every agent.
3. A minimal BaseHTTPRequestHandler subclass that handles JSON
   POST + GET routing without adding any external dependency.
"""

from __future__ import annotations

import contextlib
import json
import threading
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Referral envelope (must mirror MCP propose_referral output)
# ---------------------------------------------------------------------------


REFERRAL_SCHEMA_VERSION = "0.1.0"


def now_iso() -> str:
    """UTC ISO-8601 timestamp with seconds precision."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_referral_id() -> str:
    return f"ref-{uuid.uuid4().hex[:12]}"


def validate_referral(referral: dict[str, Any]) -> tuple[bool, str | None]:
    """Verify a referral envelope conforms to the protocol schema.

    Returns ``(True, None)`` on pass, ``(False, error_code)`` on
    fail. Used by every receiving agent before doing anything else.
    """

    if not isinstance(referral, dict):
        return False, "envelope_not_object"
    for required in (
        "referralId",
        "schemaVersion",
        "sourceAgent",
        "targetAgent",
        "userId",
        "intent",
        "reasonCode",
    ):
        if required not in referral:
            return False, f"missing_field:{required}"
    if referral["schemaVersion"] != REFERRAL_SCHEMA_VERSION:
        return False, "schema_version_mismatch"
    if referral["intent"] not in {"proposed", "active", "completed"}:
        return False, "unknown_intent"
    if not referral.get("userConsentRequired", True):
        # Defence: receiving agents reject any referral that claims
        # consent isn't required. The sourceAgent is supposed to
        # have obtained user consent before sending.
        return False, "consent_must_be_required"
    return True, None


# ---------------------------------------------------------------------------
# Per-agent append-only audit log
# ---------------------------------------------------------------------------


class AgentAuditLog:
    """Tiny append-only JSONL log per agent. Same shape ethos as
    the main app's ``audit_log.py`` — one line per event, sortable,
    replayable. Thread-safe via a per-instance lock.

    Records carry a monotonic ``sequence_no`` (per agent, not per
    mesh) so a regulator can detect deletion. The full HMAC-chain
    machinery from the main app would be appropriate for a real
    deployment of a receiving agent; the simulators ship the
    sequence_no marker so the demo can show 'agent A logged the
    referral receipt, agent B logged its decision', and the chain
    can be added by the integrator when they port these stubs.
    """

    def __init__(self, log_path: Path) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._next_seq = self._load_next_sequence()

    def _load_next_sequence(self) -> int:
        if not self.log_path.exists():
            return 1
        last = 0
        try:
            with self.log_path.open("r", encoding="utf-8") as fh:
                for raw in fh:
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    seq = rec.get("sequence_no")
                    if isinstance(seq, int) and seq > last:
                        last = seq
        except OSError:
            return 1
        return last + 1

    def emit(self, event_type: str, payload: dict[str, Any]) -> int:
        """Append one event. Returns the assigned sequence_no."""
        with self._lock:
            seq = self._next_seq
            self._next_seq += 1
            record = {
                "sequence_no": seq,
                "event_type": event_type,
                "timestamp": now_iso(),
                "payload": payload,
            }
            with self.log_path.open("a", encoding="utf-8") as fh:
                json.dump(record, fh, ensure_ascii=False, sort_keys=True)
                fh.write("\n")
            return seq

    def replay(self) -> list[dict[str, Any]]:
        """Read every record in order — used by the demo script
        to display the full decision trail."""
        if not self.log_path.exists():
            return []
        out: list[dict[str, Any]] = []
        with self.log_path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                with contextlib.suppress(json.JSONDecodeError):
                    out.append(json.loads(line))
        out.sort(key=lambda r: r.get("sequence_no", 0))
        return out


# ---------------------------------------------------------------------------
# Minimal JSON handler base
# ---------------------------------------------------------------------------


class JsonRequestHandler(BaseHTTPRequestHandler):
    """BaseHTTPRequestHandler with JSON helpers + a tidy route
    table. Subclasses set ``routes`` as a dict of
    ``(method, path) -> handler_callable(self, payload) -> dict``.

    Same minimalism as ``app.py`` — zero external deps.
    """

    routes: dict[tuple[str, str], Callable[..., Any]] = {}
    server_version = "helpmefindthejob-mesh-agent/0.1"

    def _send_json(self, status: int, body: dict[str, Any]) -> None:
        encoded = json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json(self) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        try:
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _dispatch(self, method: str) -> None:
        path = self.path.split("?", 1)[0]
        handler = self.routes.get((method, path))
        if handler is None:
            # Pattern-match: parametrised routes like /v1/status/<id>
            for (m, p), h in self.routes.items():
                if m != method:
                    continue
                if "<" not in p:
                    continue
                # Replace each <name> with a non-slash capture
                import re

                pattern = "^" + re.sub(r"<[^/]+>", r"([^/]+)", p) + "$"
                match = re.match(pattern, path)
                if match:
                    handler = lambda self, payload, _g=match.groups(), _h=h: _h(
                        self, payload, *_g
                    )
                    break
        if handler is None:
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"status": "error", "code": "not_found", "path": path},
            )
            return
        payload: dict[str, Any] | None
        if method == "GET":
            payload = {}
        else:
            payload = self._read_json()
            if payload is None:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"status": "error", "code": "invalid_json"},
                )
                return
        try:
            result = handler(self, payload)
            if not isinstance(result, dict):
                raise TypeError(
                    f"handler {handler} returned {type(result).__name__}, expected dict"
                )
            status = int(result.pop("_http_status", HTTPStatus.OK))
            self._send_json(status, result)
        except Exception as exc:  # noqa: BLE001 - top-level HTTP boundary; never crash
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "status": "error",
                    "code": "internal_error",
                    "detail": f"{type(exc).__name__}: {exc}"[:200],
                },
            )

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def log_message(self, fmt: str, *args: Any) -> None:
        # Suppress noisy default access-log to stderr; agents emit
        # their own structured audit log instead.
        return


def serve_until_stopped(
    handler_cls: type[JsonRequestHandler],
    host: str,
    port: int,
) -> ThreadingHTTPServer:
    """Bind + serve in a background thread. Returns the server
    so the caller can call ``server.shutdown()`` at teardown."""

    server = ThreadingHTTPServer((host, port), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
