# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""AI Act Article 12 audit-log emitter.

This module implements the structured JSON Lines audit log that records every
AI invocation, MCP tool invocation, persistence confirmation, consent event,
export event, override event, and system event. The schema is documented in
``compliance/audit-log-schema.md``.

The default-emitter pattern uses a module-level singleton initialised from
environment variables. Tests inject a custom emitter via
:func:`set_default_emitter`.

A ContextVar-based caller-context pattern lets entry points (HTTP request
handlers, MCP server stdio loop) set the user / session / caller fields once
per request and have nested call sites read them implicitly. This avoids
threading user_opaque_id and session_opaque_id through every function
signature in the analysis pipeline.

Logging failures never propagate. Article 12 requires the system to record
events automatically; it does not require the system to fail if the record
cannot be written. Failures emit a stderr warning and the original event
continues.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import base64
import contextvars
import hashlib
import json
import secrets
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from company_discovery.env_compat import get_env

SCHEMA_VERSION = "v1"

# ContextVar default is None (not an empty dict) so concurrent contexts
# cannot accidentally share the same mutable default instance — see
# ruff B039 and the underlying CPython documentation. All call sites
# below normalise None to an empty dict on read.
_caller_ctx: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "audit_caller_ctx",
    default=None,
)


class AuditLogEmitter:
    """Emits AI-Act Article 12 audit-log records to a rotating JSONL file."""

    def __init__(
        self,
        log_path: Path | str,
        salt: bytes,
        *,
        plaintext_pii: bool = False,
        rotate_bytes: int = 64 * 1024 * 1024,
    ) -> None:
        self.log_path = Path(log_path)
        self.salt = salt
        self.plaintext_pii = plaintext_pii
        self.rotate_bytes = int(rotate_bytes)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ utils

    def hash_id(self, value: str | None) -> str | None:
        """Return SHA-256(salt || value) hex digest, or the plaintext value
        when plaintext_pii is on, or None when value is None."""
        if value is None:
            return None
        if self.plaintext_pii:
            return value
        digest = hashlib.sha256()
        digest.update(self.salt)
        digest.update(value.encode("utf-8"))
        return digest.hexdigest()

    def short_hash(self, value: str | None) -> str | None:
        """Return the first 16 hex chars of SHA-256(value). Used for
        prompt-template IDs and content-derived fingerprints that do not
        require the per-deployment salt."""
        if value is None:
            return None
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return digest[:16]

    # ------------------------------------------------------------------ emit

    def emit(
        self,
        event_type: str,
        *,
        outcome: str = "ok",
        duration_ms: int = 0,
        event_payload: dict[str, Any] | None = None,
        user_opaque_id: str | None = None,
        session_opaque_id: str | None = None,
        caller: str | None = None,
        journey_phase: str | None = None,
        prompt_template_id: str | None = None,
        ai_provider: str | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        error_class: str | None = None,
    ) -> None:
        """Emit a single audit-log record.

        Caller-context fields (user_opaque_id, session_opaque_id, caller,
        journey_phase) default to whatever has been set via
        :func:`set_caller_context`. Explicit kwargs override the context.
        """
        ctx = _caller_ctx.get() or {}
        record: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": _now_iso(),
            "user_opaque_id": self.hash_id(user_opaque_id or ctx.get("user_id")),
            "session_opaque_id": self.hash_id(session_opaque_id or ctx.get("session_id")),
            "caller": caller or ctx.get("caller") or "system",
            "duration_ms": int(duration_ms),
            "outcome": outcome,
        }
        phase = journey_phase if journey_phase is not None else ctx.get("journey_phase")
        if phase is not None:
            record["journey_phase"] = phase
        if prompt_template_id is not None:
            record["prompt_template_id"] = prompt_template_id
        if ai_provider is not None:
            record["ai_provider"] = ai_provider
        if tokens_in is not None:
            record["tokens_in"] = int(tokens_in)
        if tokens_out is not None:
            record["tokens_out"] = int(tokens_out)
        if error_class is not None:
            record["error_class"] = error_class
        if event_payload:
            record["event_payload"] = event_payload
        self._write(record)

    # -------------------------------------------------------------- internals

    def _write(self, record: dict[str, Any]) -> None:
        try:
            with self._lock:
                self._rotate_if_needed()
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with self.log_path.open("a", encoding="utf-8") as handle:
                    json.dump(record, handle, ensure_ascii=False, sort_keys=True)
                    handle.write("\n")
        except OSError as exc:
            print(f"[audit_log] failed to write record: {exc!r}", file=sys.stderr)

    def _rotate_if_needed(self) -> None:
        if not self.log_path.exists():
            return
        try:
            size = self.log_path.stat().st_size
        except OSError:
            return
        if size < self.rotate_bytes:
            return
        # Microsecond-resolution timestamp plus a short nonce to avoid
        # collision when many rotations happen in the same second
        # (e.g. tight-threshold tests, log-storm conditions).
        now = datetime.now(timezone.utc)
        suffix = now.strftime("%Y%m%d-%H%M%S-%f")
        nonce = secrets.token_hex(2)
        rotated = self.log_path.with_name(f"{self.log_path.name}.{suffix}-{nonce}")
        try:
            self.log_path.rename(rotated)
        except OSError as exc:
            print(f"[audit_log] failed to rotate: {exc!r}", file=sys.stderr)


# --------------------------------------------------------------- caller context


def set_caller_context(
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    caller: str = "system",
    journey_phase: str | None = None,
) -> contextvars.Token:
    """Push the caller context for the current execution scope. Returns a
    token that can be passed to :func:`reset_caller_context` to restore the
    prior context."""
    return _caller_ctx.set(
        {
            "user_id": user_id,
            "session_id": session_id,
            "caller": caller,
            "journey_phase": journey_phase,
        }
    )


def reset_caller_context(token: contextvars.Token) -> None:
    """Restore the caller context to its prior value."""
    _caller_ctx.reset(token)


def current_caller_context() -> dict[str, Any]:
    """Return a shallow copy of the current caller context (for diagnostics
    and tests)."""
    return dict(_caller_ctx.get() or {})


# --------------------------------------------------------- default-emitter singleton


_default_emitter: AuditLogEmitter | None = None
_default_emitter_lock = threading.Lock()


def default_emitter() -> AuditLogEmitter:
    """Return the process-wide default emitter, lazily initialised from
    environment variables.

    Environment variables consulted:

    * ``HELPMEFINDTHEJOB_DATA_ROOT`` (legacy ``DIRECTJOB_DATA_ROOT``) —
      base directory; the audit log is at ``${DATA_ROOT}/ai_act_audit.log``.
    * ``HELPMEFINDTHEJOB_AUDIT_SALT`` (legacy ``DIRECTJOB_AUDIT_SALT``) —
      32 random bytes, base64 or raw. In production mode, missing salt
      is fatal (see :func:`_resolve_salt`). In dev mode, a per-process
      random salt is generated and an ERROR-level stderr warning fires.
    * ``HELPMEFINDTHEJOB_AUDIT_PLAINTEXT_PII`` (legacy
      ``DIRECTJOB_AUDIT_PLAINTEXT_PII``) — ``true`` to disable hashing.
      Default ``false``.
    * ``HELPMEFINDTHEJOB_AUDIT_ROTATE_BYTES`` (legacy
      ``DIRECTJOB_AUDIT_ROTATE_BYTES``) — rotation threshold. Default
      64 MiB.
    """
    global _default_emitter
    if _default_emitter is not None:
        return _default_emitter
    with _default_emitter_lock:
        if _default_emitter is not None:
            return _default_emitter
        data_root = Path(get_env("HELPMEFINDTHEJOB_DATA_ROOT", "DIRECTJOB_DATA_ROOT", "data"))
        log_path = data_root / "ai_act_audit.log"
        salt = _resolve_salt(get_env("HELPMEFINDTHEJOB_AUDIT_SALT", "DIRECTJOB_AUDIT_SALT", ""))
        plaintext_pii = get_env(
            "HELPMEFINDTHEJOB_AUDIT_PLAINTEXT_PII", "DIRECTJOB_AUDIT_PLAINTEXT_PII", "false"
        ).lower() in {
            "true",
            "1",
            "yes",
            "on",
        }
        rotate_bytes = int(
            get_env(
                "HELPMEFINDTHEJOB_AUDIT_ROTATE_BYTES",
                "DIRECTJOB_AUDIT_ROTATE_BYTES",
                str(64 * 1024 * 1024),
            )
        )
        _default_emitter = AuditLogEmitter(
            log_path=log_path,
            salt=salt,
            plaintext_pii=plaintext_pii,
            rotate_bytes=rotate_bytes,
        )
        return _default_emitter


def set_default_emitter(emitter: AuditLogEmitter | None) -> None:
    """Inject a custom emitter (tests) or reset to ``None`` so the next call
    to :func:`default_emitter` re-reads environment variables."""
    global _default_emitter
    with _default_emitter_lock:
        _default_emitter = emitter


def reset_default_emitter() -> None:
    """Reset the singleton. The next call to :func:`default_emitter` will
    reinitialise from environment variables."""
    set_default_emitter(None)


# ------------------------------------------------------------------ helpers


_DEV_ENV_TOKENS = frozenset({"", "development", "dev", "test", "testing"})


def _resolve_app_env() -> str:
    """Read the application environment label, accepting both the
    Helpmefindthejob-era prefix and the legacy company-discovery prefix.

    Returns the casefolded value; empty string when neither is set.
    """
    raw = get_env("HELPMEFINDTHEJOB_ENV", "COMPANY_DISCOVERY_ENV", "")
    return (raw or "").strip().casefold()


def _resolve_salt(raw: str) -> bytes:
    """Resolve the audit-log salt from the configured value.

    Production-mode semantics (Helpmefindthejob 2026-05-19, see
    [docs/grant/04-research-and-decisions.md] PART 1.1 of the
    pre-submission scope-tightening slice):

    * If a salt is configured (``raw`` is non-empty), decode it
      (base64 if it parses, raw bytes otherwise) and return.
    * If no salt is configured **and** the application environment
      is not ``development`` / ``dev`` / ``test`` / ``testing``,
      print a fatal error to stderr and ``sys.exit(1)``. The audit
      log's integrity guarantees can't be honoured without a stable
      cross-restart salt; refusing to start is safer than running
      with degraded auditability.
    * If no salt is configured and the environment **is** dev/test,
      generate a per-process salt and print an ERROR-level warning.
      This keeps the developer's loop frictionless while the
      production path stays fail-fast.

    Tests that need the development-fallback behaviour can rely on
    the default empty ``HELPMEFINDTHEJOB_ENV`` / ``COMPANY_DISCOVERY_ENV``,
    which classifies as ``development``.
    """
    if raw:
        try:
            decoded = base64.b64decode(raw, validate=False)
            if len(decoded) >= 16:
                return decoded
        except Exception:
            pass
        return raw.encode("utf-8")
    env = _resolve_app_env()
    if env not in _DEV_ENV_TOKENS:
        print(
            "[audit_log] FATAL: env=" + env + " requires HELPMEFINDTHEJOB_AUDIT_SALT (or legacy "
            "DIRECTJOB_AUDIT_SALT) to be set to 32 random bytes "
            "(base64). Refusing to start because audit-log integrity "
            "cannot be guaranteed across process restarts without a "
            "stable salt.\n"
            "    Generate one with:\n"
            "        python3 -c 'import secrets, base64; "
            "print(base64.b64encode(secrets.token_bytes(32)).decode())'\n"
            "    Then export it as HELPMEFINDTHEJOB_AUDIT_SALT before "
            "starting the server.",
            file=sys.stderr,
        )
        sys.exit(1)
    salt = secrets.token_bytes(32)
    # Dev-mode warning uses warnings.warn (UserWarning) instead of a
    # raw print to stderr — test runners filter UserWarning by default
    # so the message stays out of the suite's console while remaining
    # visible to a developer running the app directly (default Python
    # warning filter still surfaces it). The category is UserWarning,
    # not DeprecationWarning, because the fallback is *supported*
    # development behaviour, not a deprecation.
    import warnings as _warnings

    _warnings.warn(
        "[audit_log] HELPMEFINDTHEJOB_AUDIT_SALT not set; generated a "
        "per-process salt. Audit-log entries will not be linkable "
        "across process restarts. This fallback is permitted in "
        "development (env=" + (env or "development") + ") only. "
        "Production deployments MUST set HELPMEFINDTHEJOB_AUDIT_SALT "
        "(legacy DIRECTJOB_AUDIT_SALT still accepted with a "
        "DeprecationWarning) to 32 random bytes (base64) for stable "
        "hashing.",
        category=UserWarning,
        stacklevel=2,
    )
    return salt


def _now_iso() -> str:
    """ISO 8601 UTC timestamp with microsecond precision and trailing Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# ------------------------------------------------------------------ convenience wrappers
#
# These short helpers exist so call sites can write
# ``audit_log.emit_ai_invocation(...)`` rather than the full ``emit`` call
# with the event_type spelled out. They are syntactic sugar; the underlying
# emit() is the same.


def emit_ai_invocation(
    *,
    purpose: str,
    ai_provider: str,
    prompt_template_id: str | None = None,
    duration_ms: int = 0,
    outcome: str = "ok",
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    prompt_hash: str | None = None,
    response_hash: str | None = None,
    job_opaque_id: str | None = None,
    cv_section_opaque_ids: list[str] | None = None,
    score_adjustment_factor: float | None = None,
    error_class: str | None = None,
    emitter: AuditLogEmitter | None = None,
) -> None:
    """Convenience: emit an ``ai_invocation`` event."""
    emitter = emitter or default_emitter()
    payload: dict[str, Any] = {"purpose": purpose}
    if prompt_hash is not None:
        payload["prompt_hash"] = prompt_hash
    if response_hash is not None:
        payload["response_hash"] = response_hash
    if job_opaque_id is not None:
        payload["job_opaque_id"] = emitter.hash_id(job_opaque_id)
    if cv_section_opaque_ids:
        payload["cv_section_opaque_ids"] = [
            emitter.hash_id(value) for value in cv_section_opaque_ids
        ]
    if score_adjustment_factor is not None:
        payload["score_adjustment_factor"] = float(score_adjustment_factor)
    emitter.emit(
        "ai_invocation",
        outcome=outcome,
        duration_ms=duration_ms,
        event_payload=payload,
        ai_provider=ai_provider,
        prompt_template_id=prompt_template_id,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        error_class=error_class,
    )


def emit_mcp_tool_invocation(
    *,
    tool_name: str,
    arguments_hash: str | None = None,
    response_size_bytes: int | None = None,
    composition_source: str | None = None,
    duration_ms: int = 0,
    outcome: str = "ok",
    error_class: str | None = None,
    emitter: AuditLogEmitter | None = None,
) -> None:
    """Convenience: emit an ``mcp_tool_invocation`` event."""
    emitter = emitter or default_emitter()
    payload: dict[str, Any] = {"tool_name": tool_name}
    if arguments_hash is not None:
        payload["arguments_hash"] = arguments_hash
    if response_size_bytes is not None:
        payload["response_size_bytes"] = int(response_size_bytes)
    if composition_source is not None:
        payload["composition_source"] = composition_source
    emitter.emit(
        "mcp_tool_invocation",
        outcome=outcome,
        duration_ms=duration_ms,
        event_payload=payload,
        caller="mcp",
        error_class=error_class,
    )


def emit_system_event(
    *,
    system_event_kind: str,
    details: dict[str, Any] | None = None,
    outcome: str = "ok",
    duration_ms: int = 0,
    emitter: AuditLogEmitter | None = None,
) -> None:
    """Convenience: emit a ``system_event`` event."""
    emitter = emitter or default_emitter()
    payload: dict[str, Any] = {"system_event_kind": system_event_kind}
    if details:
        payload["details"] = details
    emitter.emit(
        "system_event",
        outcome=outcome,
        duration_ms=duration_ms,
        event_payload=payload,
        caller="system",
    )
