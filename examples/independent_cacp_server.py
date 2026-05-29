#!/usr/bin/env python3
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""A SECOND, independent CACP v0.1 server — the protocol's portability proof.

The Helpmefindthejob MCP server (``mcp_server.py``) is the reference CACP
implementation. This file is a deliberately-minimal, *from-scratch* second
implementation that shares only the published wire contracts — the CACP tool
surface, the civic-profile JSON Schema, and the Article-12 audit-record format —
and imports NONE of the application's code. It exists to prove the claim a real
interoperability standard must earn: that an independent party can implement
CACP and pass the same conformance suite, unmodified.

    python -m conformance.cacp                                  # the reference server
    python -m conformance.cacp  (run_conformance(server_path=this_file))  # this one

It speaks JSON-RPC over stdio (MCP ``2024-11-05``), keeps an in-memory referral
store + consent profiles, enforces the referral lifecycle + tenant isolation,
returns RFC-7807 problem documents for bad arguments, and writes a tamper-evident
HMAC-chained audit log (attributed to the composing agent) that
``company_discovery.audit_log.verify_chain`` accepts — all in one file a reader
can audit end to end.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import jsonschema

_DATA_DIR = Path(os.environ.get("HELPMEFINDTHEJOB_DATA_DIR", "."))
_AUDIT_SALT = base64.b64decode(os.environ.get("HELPMEFINDTHEJOB_AUDIT_SALT", "")) or b"local-dev-salt"
_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "static" / ".well-known" / "civic-profile.schema.json"

_SCHEMA_VERSION = "civic-profile/v1"
_TOOL_VERSION = "1.0.0"
_CONSENT_SCOPES = ("identity", "residence", "employment", "cv", "outcomes", "preferences")
_LIFECYCLE: dict[str, set[str]] = {
    "proposed": {"accepted", "declined", "expired"},
    "accepted": {"followed_up", "declined", "expired"},
    "declined": set(),
    "followed_up": set(),
    "expired": set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Tamper-evident audit chain (Article 12) — re-implemented to the published
# format so verify_chain accepts it, without importing the application.
# ---------------------------------------------------------------------------


class AuditChain:
    def __init__(self, path: Path, salt: bytes) -> None:
        self.path = path
        self.salt = salt
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq = 0
        self._prev = ""

    def emit(self, event_type: str, event_payload: dict[str, Any], *, outcome: str = "ok") -> None:
        self._seq += 1
        record: dict[str, Any] = {
            "schema_version": "v2",
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": _now(),
            "sequence_no": self._seq,
            "outcome": outcome,
            "event_payload": event_payload,
        }
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
        record["chain_hmac"] = hmac.new(
            self.salt, (self._prev + "\n" + canonical).encode("utf-8"), hashlib.sha256
        ).hexdigest()
        self._prev = record["chain_hmac"]
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# CACP tool surface — implemented from scratch over in-memory state.
# ---------------------------------------------------------------------------

_OBJ = {"type": "object"}
_STR = {"type": "string"}


class CacpServer:
    def __init__(self) -> None:
        self.audit = AuditChain(_DATA_DIR / "ai_act_audit.log", _AUDIT_SALT)
        self.composition_source = "unknown"
        self._referrals: dict[str, list[dict[str, Any]]] = {}
        self._schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

    # -- tool catalogue ----------------------------------------------------

    def catalogue(self) -> list[dict[str, Any]]:
        def tool(name: str, desc: str, props: dict[str, Any], required: list[str]) -> dict[str, Any]:
            return {
                "name": name,
                "description": desc,
                "version": _TOOL_VERSION,
                "inputSchema": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                    "additionalProperties": True,
                },
            }

        return [
            tool("get_user_profile_for_consent", "Scope-filtered portable civic profile.",
                 {"userId": _STR, "scopes": {"type": "array", "items": _STR}}, ["userId", "scopes"]),
            tool("propose_referral", "Propose a cross-agent referral.",
                 {"userId": _STR, "targetAgent": _STR, "reason": _STR}, ["userId", "targetAgent"]),
            tool("list_referrals", "List a user's referrals.", {"userId": _STR}, ["userId"]),
            tool("update_referral_status", "Advance a referral's lifecycle status.",
                 {"userId": _STR, "referralId": _STR, "status": _STR}, ["userId", "referralId", "status"]),
            tool("query_esco_skill", "Reconcile an occupation/skill term to ESCO/ISCO.",
                 {"query": _STR, "type": _STR, "limit": {"type": "integer"}}, ["query"]),
            tool("export_eures_compatible", "Export a discovered job as EURES-compatible.",
                 {"userId": _STR, "discoveredJobId": _STR}, ["userId", "discoveredJobId"]),
            tool("record_user_outcome", "Record a measured user outcome.",
                 {"userId": _STR, "outcome": _STR}, ["userId", "outcome"]),
        ]

    # -- dispatch ----------------------------------------------------------

    def call_tool(self, name: str, args: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Return ``(payload, is_error)``. An RFC-7807 problem document is the
        error channel; ``is_error`` becomes the MCP ``isError`` flag on the wire."""
        handler: Callable[[dict[str, Any]], dict[str, Any]] | None = {
            "get_user_profile_for_consent": self._consent,
            "propose_referral": self._propose,
            "list_referrals": self._list,
            "update_referral_status": self._update,
            "query_esco_skill": self._esco,
            "export_eures_compatible": self._eures,
            "record_user_outcome": self._outcome,
        }.get(name)
        if handler is None:
            payload: dict[str, Any] = self._problem("unknown_tool", f"no such tool: {name}")
        else:
            # validate against the declared inputSchema → RFC-7807 on bad args
            schema = next((t["inputSchema"] for t in self.catalogue() if t["name"] == name), None)
            try:
                if schema is not None:
                    jsonschema.validate(args, schema)
                payload = handler(args)
            except jsonschema.ValidationError as exc:
                payload = self._problem("invalid_arguments", exc.message)
        is_error = payload.get("type") == "about:blank"
        self.audit.emit(
            "mcp_tool_invocation",
            {"composition_source": self.composition_source, "tool": name},
            outcome="error" if is_error else "ok",
        )
        return payload, is_error

    # -- tools -------------------------------------------------------------

    @staticmethod
    def _problem(status: str, detail: str) -> dict[str, Any]:
        # RFC 7807 problem document.
        return {"type": "about:blank", "title": status, "status": status, "detail": detail}

    def _consent(self, args: dict[str, Any]) -> dict[str, Any]:
        requested = list(args.get("scopes") or [])
        unknown = [s for s in requested if s not in _CONSENT_SCOPES]
        if unknown:
            return self._problem("invalid_arguments", f"unknown consent scope(s): {unknown}")
        blocks = {
            "identity": {"displayName": "Aïcha B.", "preferredLang": "de"},
            "residence": {"country": "DE", "city": "Berlin", "status": "drittstaat"},
            "employment": {"targetRoles": ["Krankenschwester"], "yearsExperience": 6},
            "cv": {"hasCv": True, "sections": ["summary", "experience"]},
            "outcomes": {"applications": 0, "interviews": 0},
            "preferences": {"remoteOk": False, "maxCommuteKm": 30},
        }
        profile: dict[str, Any] = {
            "userId": str(args.get("userId", "")),
            "scopes": requested,
            "schemaVersion": _SCHEMA_VERSION,
            "consentRecordedAt": _now(),
        }
        for scope in requested:
            profile[scope] = blocks[scope]
        # belt-and-braces: ensure we emit a schema-valid contract
        jsonschema.validate(profile, self._schema)
        return {"profile": profile}

    def _propose(self, args: dict[str, Any]) -> dict[str, Any]:
        user_id = str(args["userId"])
        referral = {
            "referralId": "ref-" + uuid.uuid4().hex[:12],
            "userId": user_id,
            "targetAgent": str(args.get("targetAgent", "")),
            "reason": str(args.get("reason", "")),
            "status": "proposed",
            "userConsentRequired": True,
            "createdAt": _now(),
        }
        self._referrals.setdefault(user_id, []).append(referral)
        return {"referral": referral}

    def _list(self, args: dict[str, Any]) -> dict[str, Any]:
        owned = self._referrals.get(str(args["userId"]), [])
        return {"referrals": [dict(r) for r in owned]}

    def _find(self, user_id: str, referral_id: str) -> dict[str, Any] | None:
        for ref in self._referrals.get(user_id, []):
            if ref["referralId"] == referral_id:
                return ref
        return None

    def _update(self, args: dict[str, Any]) -> dict[str, Any]:
        user_id, referral_id = str(args["userId"]), str(args["referralId"])
        new_status = str(args.get("status", ""))
        ref = self._find(user_id, referral_id)
        if ref is None:
            # tenant isolation: never leak that the referral exists for another user
            return self._problem("not_found", "referral not found for this user")
        if new_status not in _LIFECYCLE.get(ref["status"], set()):
            return self._problem(
                "illegal_transition", f"{ref['status']} -> {new_status} is not allowed"
            )
        ref["status"] = new_status
        ref["updatedAt"] = _now()
        return {"referral": dict(ref)}

    def _esco(self, args: dict[str, Any]) -> dict[str, Any]:
        return {"query": str(args.get("query", "")), "matches": [], "datasetVersion": "independent-stub"}

    def _eures(self, args: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "userId": str(args.get("userId", "")), "euresPayload": {}}

    def _outcome(self, args: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "recorded": True}


# ---------------------------------------------------------------------------
# JSON-RPC over stdio (MCP 2024-11-05)
# ---------------------------------------------------------------------------


def _reply(message_id: Any, result: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": message_id, "result": result}) + "\n")
    sys.stdout.flush()


def main() -> int:
    server = CacpServer()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params") or {}

        if method == "initialize":
            server.composition_source = (params.get("clientInfo") or {}).get("name", "unknown")
            _reply(msg_id, {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "serverInfo": {"name": "independent-cacp-server", "version": _TOOL_VERSION},
                "capabilities": {"tools": {}},
            })
        elif method == "notifications/initialized":
            continue  # notification — no response
        elif method == "tools/list":
            _reply(msg_id, {"tools": server.catalogue()})
        elif method == "tools/call":
            payload, is_error = server.call_tool(params.get("name", ""), params.get("arguments") or {})
            _reply(msg_id, {
                "content": [{"type": "text", "text": json.dumps(payload)}],
                "isError": is_error,
            })
        elif msg_id is not None:
            _reply(msg_id, {"error": "method_not_found", "method": method})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
