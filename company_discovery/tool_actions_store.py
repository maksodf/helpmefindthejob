"""Phase 1 / Step 4 — CRUD-parity action ledger.

Two SQLite-backed tables that implement the portfolio CRUD-parity
policy from
``~/Desktop/personal Projects/_portfolio-architecture/chat-tool-invocation.md``:

* **reversal_tokens** — post-execution undo for Tier I tools.
  When a Tier I tool runs successfully, ``try_dispatch`` records the
  inverse action here and returns the token in ``ToolResult.reversal_token``.
  The chat surface shows a toast bubble with "Undo"; when the user
  asks the LLM to undo, the new ``undo_last_action`` tool consumes the
  most recent unconsumed token and dispatches the inverse.

* **pending_actions** — preview/confirm/commit for Tier N tools.
  Tier N tools never execute directly. They write a row here with a
  preview payload and return ``pending_action_id`` in the
  ``ToolResult``. The chat surface renders an inline confirmation
  card whose commit button POSTs to ``/api/pending-actions/<id>/commit``
  to actually perform the action.

Both ledgers use opaque, unguessable IDs (``secrets.token_urlsafe``)
so they can be surfaced to the LLM without leaking guessable handles.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
import time
from pathlib import Path
from threading import RLock
from typing import Any


_SCHEMA = """
CREATE TABLE IF NOT EXISTS reversal_tokens (
    token         TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    tool_name     TEXT NOT NULL,
    tool_call_id  TEXT NOT NULL DEFAULT '',
    inverse_tool  TEXT NOT NULL,
    inverse_args  TEXT NOT NULL,
    created_at    REAL NOT NULL,
    consumed_at   REAL DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_rev_user_unconsumed
  ON reversal_tokens(user_id, consumed_at, created_at DESC);

CREATE TABLE IF NOT EXISTS pending_actions (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    tool_name     TEXT NOT NULL,
    tool_call_id  TEXT NOT NULL DEFAULT '',
    preview       TEXT NOT NULL,
    commit_args   TEXT NOT NULL,
    created_at    REAL NOT NULL,
    committed_at  REAL DEFAULT NULL,
    cancelled_at  REAL DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_pending_user_open
  ON pending_actions(user_id, committed_at, cancelled_at, created_at DESC);

CREATE TABLE IF NOT EXISTS idempotency_cache (
    key           TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    tool_name     TEXT NOT NULL,
    result        TEXT NOT NULL,
    created_at    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_idem_user_created
  ON idempotency_cache(user_id, created_at DESC);

-- Phase 1 / Step 8 — OTel-shaped tool-call span records.
-- Field names mirror the OpenTelemetry GenAI semantic conventions
-- so the data is exporter-ready when the observability backend is
-- chosen (ADR-001 ties exporter to the Pydantic AI migration via
-- Logfire). Until then this table is queryable for replay /
-- per-tool success rate / cost attribution.
CREATE TABLE IF NOT EXISTS tool_call_spans (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id        TEXT NOT NULL DEFAULT '',
    user_id        TEXT NOT NULL,
    tool_name      TEXT NOT NULL,
    tier           TEXT NOT NULL,
    success        INTEGER NOT NULL,
    error_code     TEXT NOT NULL DEFAULT '',
    duration_ms    INTEGER NOT NULL,
    cache_hit      INTEGER NOT NULL DEFAULT 0,
    created_at     REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_span_tool_created
  ON tool_call_spans(tool_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_span_user_created
  ON tool_call_spans(user_id, created_at DESC);
"""


# How long an unconsumed reversal token stays usable. After this
# window the token is treated as consumed (the action has effectively
# "settled" from the user's perspective). 10 minutes mirrors the
# typical chat-bubble lifetime.
REVERSAL_TTL_S = 600.0

# How long an uncommitted pending action stays valid. 24 hours so the
# user can come back tomorrow and still find their preview, but old
# items get garbage-collected.
PENDING_TTL_S = 86400.0

# How long a tool's result stays cached under its idempotency key.
# Sized to catch retries (network blip, double-tap, LLM re-emitting
# the same call across iterations) without preventing the user from
# intentionally repeating an action in a normal session — 60 seconds
# is the standard window in the Stripe-shaped idempotency pattern.
IDEMPOTENCY_TTL_S = 60.0


class ToolActionsStore:
    """SQLite-backed ledger for Tier I reversal tokens and Tier N
    pending actions. Thread-safe via an internal RLock; the
    underlying connection is shared (``check_same_thread=False``)
    matching the pattern in ``SqliteCompanyDiscoveryRepository``."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # -------- reversal tokens (Tier I) --------

    def record_reversal(
        self, *, user_id: str, tool_name: str, tool_call_id: str,
        inverse_tool: str, inverse_args: dict[str, Any],
    ) -> str:
        token = secrets.token_urlsafe(18)
        now = time.time()
        with self._lock:
            self._conn.execute(
                "INSERT INTO reversal_tokens "
                "(token, user_id, tool_name, tool_call_id, "
                " inverse_tool, inverse_args, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (token, user_id, tool_name, tool_call_id or "",
                 inverse_tool, json.dumps(inverse_args, default=str), now),
            )
            self._conn.commit()
        return token

    def latest_unconsumed(self, user_id: str) -> dict[str, Any] | None:
        cutoff = time.time() - REVERSAL_TTL_S
        with self._lock:
            row = self._conn.execute(
                "SELECT token, tool_name, tool_call_id, inverse_tool, "
                "       inverse_args, created_at "
                "FROM reversal_tokens "
                "WHERE user_id = ? "
                "  AND consumed_at IS NULL "
                "  AND created_at >= ? "
                "ORDER BY created_at DESC LIMIT 1",
                (user_id, cutoff),
            ).fetchone()
        if row is None:
            return None
        return {
            "token": row[0],
            "tool_name": row[1],
            "tool_call_id": row[2],
            "inverse_tool": row[3],
            "inverse_args": json.loads(row[4]),
            "created_at": row[5],
        }

    def consume(
        self, *, token: str, user_id: str
    ) -> dict[str, Any] | None:
        """Atomically consume a reversal token. Returns the inverse
        action payload on success, ``None`` if the token does not
        exist, is already consumed, or does not belong to this user
        (defense in depth even though the token is opaque)."""
        now = time.time()
        cutoff = now - REVERSAL_TTL_S
        with self._lock:
            row = self._conn.execute(
                "SELECT tool_name, inverse_tool, inverse_args, created_at "
                "FROM reversal_tokens "
                "WHERE token = ? AND user_id = ? "
                "  AND consumed_at IS NULL "
                "  AND created_at >= ?",
                (token, user_id, cutoff),
            ).fetchone()
            if row is None:
                return None
            self._conn.execute(
                "UPDATE reversal_tokens SET consumed_at = ? WHERE token = ?",
                (now, token),
            )
            self._conn.commit()
        return {
            "tool_name": row[0],
            "inverse_tool": row[1],
            "inverse_args": json.loads(row[2]),
            "created_at": row[3],
        }

    # -------- pending actions (Tier N) --------

    def record_pending(
        self, *, user_id: str, tool_name: str, tool_call_id: str,
        preview: dict[str, Any], commit_args: dict[str, Any],
    ) -> str:
        pid = secrets.token_urlsafe(18)
        now = time.time()
        with self._lock:
            self._conn.execute(
                "INSERT INTO pending_actions "
                "(id, user_id, tool_name, tool_call_id, preview, "
                " commit_args, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, user_id, tool_name, tool_call_id or "",
                 json.dumps(preview, default=str),
                 json.dumps(commit_args, default=str), now),
            )
            self._conn.commit()
        return pid

    def get_pending(
        self, *, pending_id: str, user_id: str
    ) -> dict[str, Any] | None:
        cutoff = time.time() - PENDING_TTL_S
        with self._lock:
            row = self._conn.execute(
                "SELECT tool_name, tool_call_id, preview, commit_args, "
                "       created_at, committed_at, cancelled_at "
                "FROM pending_actions "
                "WHERE id = ? AND user_id = ? AND created_at >= ?",
                (pending_id, user_id, cutoff),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": pending_id,
            "tool_name": row[0],
            "tool_call_id": row[1],
            "preview": json.loads(row[2]),
            "commit_args": json.loads(row[3]),
            "created_at": row[4],
            "committed_at": row[5],
            "cancelled_at": row[6],
        }

    def mark_committed(
        self, *, pending_id: str, user_id: str
    ) -> bool:
        """Mark the pending action as committed. Returns False if it
        was already committed/cancelled or doesn't exist."""
        now = time.time()
        with self._lock:
            cur = self._conn.execute(
                "UPDATE pending_actions SET committed_at = ? "
                "WHERE id = ? AND user_id = ? "
                "  AND committed_at IS NULL "
                "  AND cancelled_at IS NULL",
                (now, pending_id, user_id),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def mark_cancelled(
        self, *, pending_id: str, user_id: str
    ) -> bool:
        now = time.time()
        with self._lock:
            cur = self._conn.execute(
                "UPDATE pending_actions SET cancelled_at = ? "
                "WHERE id = ? AND user_id = ? "
                "  AND committed_at IS NULL "
                "  AND cancelled_at IS NULL",
                (now, pending_id, user_id),
            )
            self._conn.commit()
            return cur.rowcount > 0

    # -------- idempotency cache (Tier I / N / B) --------

    def get_idempotent(
        self, *, key: str, user_id: str
    ) -> dict[str, Any] | None:
        """Return the cached result for a previous identical call, or
        ``None`` if no recent record exists for this user. Caller is
        responsible for computing the canonical key from
        ``(user_id, tool_name, validated_args)``."""
        cutoff = time.time() - IDEMPOTENCY_TTL_S
        with self._lock:
            row = self._conn.execute(
                "SELECT result FROM idempotency_cache "
                "WHERE key = ? AND user_id = ? AND created_at >= ?",
                (key, user_id, cutoff),
            ).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return None

    def invalidate_user_idempotency(
        self, *, user_id: str, tool_name: str | None = None,
    ) -> int:
        """Drop the user's cached results so a fresh call re-runs
        the handler. Used after ``undo_last_action`` so a repeat
        call within the 60s cache window can't return a stale
        ``reversalToken`` paired with stale state.

        When ``tool_name`` is None, clears all of the user's
        entries; otherwise scopes to a single tool. Returns the row
        count removed.
        """
        with self._lock:
            if tool_name is None:
                cur = self._conn.execute(
                    "DELETE FROM idempotency_cache WHERE user_id = ?",
                    (user_id,),
                )
            else:
                cur = self._conn.execute(
                    "DELETE FROM idempotency_cache "
                    "WHERE user_id = ? AND tool_name = ?",
                    (user_id, tool_name),
                )
            self._conn.commit()
            return cur.rowcount or 0

    def record_idempotent(
        self, *, key: str, user_id: str, tool_name: str,
        result: dict[str, Any],
    ) -> None:
        """Cache the result under the given key. INSERT OR REPLACE so a
        later record (e.g. an idempotency hash collision across
        ``json`` orderings, defensive only) overwrites the older
        entry — the freshness invariant is "the most recent identical
        call wins."""
        now = time.time()
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO idempotency_cache "
                "(key, user_id, tool_name, result, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (key, user_id, tool_name,
                 json.dumps(result, default=str), now),
            )
            self._conn.commit()

    # -------- tool-call span records (Step 8) --------

    def record_tool_span(
        self, *, turn_id: str, user_id: str, tool_name: str,
        tier: str, success: bool, error_code: str,
        duration_ms: int, cache_hit: bool,
    ) -> None:
        """Append one tool-call observability record. Field names
        mirror OpenTelemetry GenAI semantic conventions so the
        exporter (Phase 2) is a thin row → span translation.

        Defensively swallows storage errors — observability must not
        block product behaviour.
        """
        try:
            with self._lock:
                self._conn.execute(
                    "INSERT INTO tool_call_spans "
                    "(turn_id, user_id, tool_name, tier, success, "
                    " error_code, duration_ms, cache_hit, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (turn_id, user_id, tool_name, tier,
                     1 if success else 0,
                     error_code or "",
                     int(duration_ms),
                     1 if cache_hit else 0,
                     time.time()),
                )
                self._conn.commit()
        except Exception:  # noqa: BLE001
            pass

    def tool_span_count(
        self, *, tool_name: str | None = None,
        user_id: str | None = None,
    ) -> int:
        """Test/probe helper — count spans optionally filtered by
        tool name and/or user."""
        q = "SELECT COUNT(*) FROM tool_call_spans WHERE 1=1"
        params: list[Any] = []
        if tool_name is not None:
            q += " AND tool_name = ?"
            params.append(tool_name)
        if user_id is not None:
            q += " AND user_id = ?"
            params.append(user_id)
        with self._lock:
            row = self._conn.execute(q, params).fetchone()
        return int(row[0]) if row else 0

    def tool_span_success_rate(
        self, *, tool_name: str, window_seconds: float = 3600.0,
    ) -> tuple[int, int]:
        """Return ``(ok_count, total_count)`` for the named tool over
        the last ``window_seconds``. The SLO ratio
        ``ok_count / total_count`` is what's exported as the
        ``tool.<name>.success_rate`` metric when the OTel bridge is
        wired."""
        cutoff = time.time() - window_seconds
        with self._lock:
            row = self._conn.execute(
                "SELECT SUM(success), COUNT(*) "
                "FROM tool_call_spans "
                "WHERE tool_name = ? AND created_at >= ?",
                (tool_name, cutoff),
            ).fetchone()
        ok = int(row[0] or 0) if row else 0
        total = int(row[1] or 0) if row else 0
        return ok, total

    # -------- maintenance --------

    def gc_expired(self) -> int:
        """Delete consumed reversal tokens, committed/cancelled
        pending actions, and expired idempotency entries older than
        their respective TTLs. Returns the row count removed.
        Callable from a periodic task."""
        rev_cutoff = time.time() - REVERSAL_TTL_S
        pen_cutoff = time.time() - PENDING_TTL_S
        idem_cutoff = time.time() - IDEMPOTENCY_TTL_S
        with self._lock:
            r1 = self._conn.execute(
                "DELETE FROM reversal_tokens WHERE created_at < ?",
                (rev_cutoff,),
            )
            r2 = self._conn.execute(
                "DELETE FROM pending_actions WHERE created_at < ?",
                (pen_cutoff,),
            )
            r3 = self._conn.execute(
                "DELETE FROM idempotency_cache WHERE created_at < ?",
                (idem_cutoff,),
            )
            self._conn.commit()
            return ((r1.rowcount or 0)
                    + (r2.rowcount or 0)
                    + (r3.rowcount or 0))
