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
import hmac
import json
import secrets
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from company_discovery.env_compat import get_env

# Phase 2 #13 (2026-05-21): schema bumped v1 → v2. The new
# version adds required tamper-evidence fields (sequence_no +
# chain_hmac). v1 readers can still load v2 records (extra
# fields ignored). verify_chain requires v2 — a mixed-version
# log fails verification with a specific error code, prompting
# the operator to archive pre-v2 records separately rather than
# silently accepting an un-chained surface.
SCHEMA_VERSION = "v2"

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
        # Phase 2 #13 (2026-05-21): tamper-evidence via monotonic
        # sequence number + HMAC chain. State is loaded lazily on
        # the first write so cheap construct/destroy in tests
        # doesn't pay an I/O cost. Each record carries
        # sequence_no (1-indexed monotonic) and chain_hmac
        # (HMAC-SHA256(salt, prev_chain_hmac || canonical_record)).
        # The chain runs across rotated files so deletion of a
        # rotated file is detectable (sequence_no gap).
        self._chain_loaded: bool = False
        self._last_sequence_no: int = 0
        self._last_chain_hmac: str = ""

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

    # -------------------------------------------------------- chain helpers

    def _load_chain_state(self) -> None:
        """Phase 2 #13: scan existing log files (current + rotated)
        to recover ``(last_sequence_no, last_chain_hmac)``. Called
        once on the first write of an emitter instance.

        Rotated files share the ``<basename>.<timestamp>-<nonce>``
        pattern from :meth:`_rotate_if_needed`. We sort lexically
        (timestamps in the name sort chronologically) so the
        highest-sequence record across all files anchors the chain.
        """

        last_seq = 0
        last_hmac = ""
        parent = self.log_path.parent
        basename = self.log_path.name
        candidates: list[Path] = []
        if self.log_path.exists():
            candidates.append(self.log_path)
        try:
            for sibling in parent.iterdir():
                if sibling.name.startswith(basename + ".") and sibling != self.log_path:
                    candidates.append(sibling)
        except OSError:
            pass
        for path in candidates:
            try:
                with path.open("r", encoding="utf-8") as handle:
                    for raw in handle:
                        line = raw.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        seq = obj.get("sequence_no")
                        if isinstance(seq, int) and seq > last_seq:
                            last_seq = seq
                            last_hmac = str(obj.get("chain_hmac", "") or "")
            except OSError:
                continue
        self._last_sequence_no = last_seq
        self._last_chain_hmac = last_hmac
        self._chain_loaded = True

    def _compute_chain_hmac(self, prev_hmac: str, canonical_record: str) -> str:
        """HMAC-SHA256 over (prev_hmac || canonical_record) keyed by
        the deployer salt. Returns hex. The first record in a chain
        has prev_hmac == "" (empty string)."""

        msg = (prev_hmac + "\n" + canonical_record).encode("utf-8")
        return hmac.new(self.salt, msg, hashlib.sha256).hexdigest()

    def _write(self, record: dict[str, Any]) -> None:
        # Concurrency contract (2026-05-21 quality audit):
        # The threading.Lock here protects intra-process concurrency.
        # The audit log is single-writer by design — ops deploying
        # the server with multiple worker processes (gunicorn etc.)
        # MUST configure each worker to write to a per-worker log
        # file or use a single-worker config. Cross-process writes
        # to the same file would produce a sequence_no race
        # (both workers stamp the same N+1) and verify_chain would
        # detect that as a chain break — fail-loud, not silent.
        # The Article 12 audit log is not a high-throughput
        # telemetry surface; single-writer is the correct trade.
        #
        # Lock contract: we hold _lock for the ENTIRE write — the
        # chain-state load is included so two concurrent first-
        # writes can't both compute sequence_no=N+1 from a fresh
        # cache. The load is O(records_in_all_files) so on first
        # write after restart of a long-running deployment (>1GB
        # of rotated logs) this can take seconds. That's an
        # acceptable trade for chain integrity — losing the chain
        # would invalidate every regulator audit, while a 5-second
        # blip after restart is recoverable.
        try:
            with self._lock:
                if not self._chain_loaded:
                    self._load_chain_state()
                # Stamp the record with its sequence + chain HMAC
                # BEFORE serialisation. The HMAC is computed over the
                # canonical record EXCLUDING the chain_hmac field
                # itself (chicken-and-egg) but INCLUDING the
                # sequence_no — so reordering records is detectable.
                # Quality-audit (2026-05-21): we MUST bump the in-
                # memory chain state ONLY AFTER the file write
                # succeeds. The previous version bumped first +
                # wrote second — a single OSError between bump
                # and write would silently corrupt the chain for
                # every subsequent record (record N missing on
                # disk; record N+1 chains from N's in-memory HMAC
                # which no auditor can recompute).
                tentative_seq = self._last_sequence_no + 1
                record["sequence_no"] = tentative_seq
                # Canonical form for HMAC: sorted keys, no whitespace,
                # ensure_ascii so the byte stream is stable across
                # platforms / Python versions.
                canonical = json.dumps(
                    {k: v for k, v in record.items() if k != "chain_hmac"},
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                )
                tentative_hmac = self._compute_chain_hmac(
                    self._last_chain_hmac, canonical
                )
                record["chain_hmac"] = tentative_hmac
                self._rotate_if_needed()
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with self.log_path.open("a", encoding="utf-8") as handle:
                    json.dump(record, handle, ensure_ascii=False, sort_keys=True)
                    handle.write("\n")
                # Commit the in-memory state ONLY after the write
                # succeeds. If the open or write raised an OSError,
                # we fall through to the except below WITHOUT
                # advancing the counters — the next write retries
                # with the same sequence_no, no chain gap.
                self._last_sequence_no = tentative_seq
                self._last_chain_hmac = tentative_hmac
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
        except Exception:  # noqa: BLE001, S110 - invalid base64 falls through to raw-bytes path on purpose
            pass
        return raw.encode("utf-8")
    env = _resolve_app_env()
    if env not in _DEV_ENV_TOKENS:
        print(  # noqa: T201 - fatal-fast stderr output before sys.exit(1); warnings.warn is not appropriate for a terminal failure
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


# Phase 2 #13 (2026-05-21): tamper-evidence verification surface.
# Regulators / external auditors run verify_chain to confirm the
# log hasn't been tampered with. Returns a structured report
# rather than raising — auditors want detail, not exceptions.


class ChainVerificationResult:
    """Outcome of :func:`verify_chain`. Fields are simple primitives
    so the report serialises cleanly into JSON for audit tooling.
    """

    __slots__ = (
        "ok",
        "records_checked",
        "first_break_at_sequence",
        "first_break_reason",
        "missing_sequence_numbers",
    )

    def __init__(
        self,
        *,
        ok: bool,
        records_checked: int,
        first_break_at_sequence: int | None = None,
        first_break_reason: str | None = None,
        missing_sequence_numbers: list[int] | None = None,
    ) -> None:
        self.ok = ok
        self.records_checked = records_checked
        self.first_break_at_sequence = first_break_at_sequence
        self.first_break_reason = first_break_reason
        self.missing_sequence_numbers = missing_sequence_numbers or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "recordsChecked": self.records_checked,
            "firstBreakAtSequence": self.first_break_at_sequence,
            "firstBreakReason": self.first_break_reason,
            "missingSequenceNumbers": list(self.missing_sequence_numbers),
        }


def verify_chain(log_paths: list[Path], salt: bytes) -> ChainVerificationResult:
    """Walk one or more audit log files in sequence-number order and
    confirm the HMAC chain is intact.

    Returns ``ChainVerificationResult(ok=True)`` when:
    - Every record has a sequence_no
    - Sequence numbers are dense (1, 2, 3, ... no gaps)
    - Each record's chain_hmac matches the recomputed HMAC

    Returns ``ok=False`` with diagnostic fields when any of the
    above fails. Designed to be called by an external auditor
    over the rotated + current log files of a deployment.
    """

    all_records: list[tuple[int, dict[str, Any]]] = []
    for path in log_paths:
        try:
            with path.open("r", encoding="utf-8") as handle:
                for raw in handle:
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        return ChainVerificationResult(
                            ok=False,
                            records_checked=len(all_records),
                            first_break_reason="malformed_json",
                        )
                    # Phase 2 #13: reject mixed v1+v2 logs at the
                    # verify boundary. Pre-v2 records lack
                    # tamper-evidence and accepting them silently
                    # would defeat the integrity claim.
                    schema_v = obj.get("schema_version")
                    if schema_v != "v2":
                        return ChainVerificationResult(
                            ok=False,
                            records_checked=len(all_records),
                            first_break_reason=(
                                f"unsupported_schema_version:{schema_v!r}"
                            ),
                        )
                    seq = obj.get("sequence_no")
                    if not isinstance(seq, int):
                        return ChainVerificationResult(
                            ok=False,
                            records_checked=len(all_records),
                            first_break_reason="missing_sequence_no",
                        )
                    all_records.append((seq, obj))
        except OSError as exc:
            return ChainVerificationResult(
                ok=False,
                records_checked=len(all_records),
                first_break_reason=f"file_read_error:{exc!r}"[:200],
            )

    all_records.sort(key=lambda pair: pair[0])

    # Check for sequence gaps. The chain MUST start at 1 (no
    # records before the first).
    seq_numbers = [pair[0] for pair in all_records]
    if seq_numbers and seq_numbers[0] != 1:
        return ChainVerificationResult(
            ok=False,
            records_checked=len(all_records),
            first_break_at_sequence=seq_numbers[0],
            first_break_reason="chain_does_not_start_at_1",
        )
    missing: list[int] = []
    for expected in range(1, len(seq_numbers) + 1):
        if expected != seq_numbers[expected - 1]:
            # Find every missing number up to current
            present = set(seq_numbers)
            missing = [n for n in range(1, seq_numbers[-1] + 1) if n not in present]
            return ChainVerificationResult(
                ok=False,
                records_checked=len(all_records),
                first_break_at_sequence=expected,
                first_break_reason="sequence_gap",
                missing_sequence_numbers=missing,
            )

    # Recompute the HMAC chain
    prev_hmac = ""
    for seq, obj in all_records:
        stored_hmac = str(obj.get("chain_hmac", "") or "")
        canonical = json.dumps(
            {k: v for k, v in obj.items() if k != "chain_hmac"},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        recomputed = hmac.new(
            salt, (prev_hmac + "\n" + canonical).encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(stored_hmac, recomputed):
            return ChainVerificationResult(
                ok=False,
                records_checked=len(all_records),
                first_break_at_sequence=seq,
                first_break_reason="hmac_mismatch",
            )
        prev_hmac = stored_hmac

    return ChainVerificationResult(ok=True, records_checked=len(all_records))


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
