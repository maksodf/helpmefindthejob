"""LLM call cost tracker (R23.6).

Persists every LLM API call with the model, the provider, the task,
the token counts, and the estimated USD cost so the operator can see
who is burning their budget. Per-user daily caps already exist
(R22.9); this tracker is the SPEND-side dashboard.

Schema
======

  CREATE TABLE llm_calls(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id        TEXT NOT NULL,
      provider       TEXT NOT NULL,   -- 'anthropic' | 'openai' | …
      model          TEXT NOT NULL,
      task           TEXT NOT NULL DEFAULT '',
      input_tokens   INTEGER NOT NULL,
      output_tokens  INTEGER NOT NULL,
      cost_usd       REAL NOT NULL,
      created_at     TEXT NOT NULL    -- UTC ISO timestamp
  )

Per-day rows for any single user stay bounded by the R22.9 daily cap,
so the table grows ~linearly with active-user-count × days. A retention
job (future) can trim rows older than 90 days.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from company_discovery.llm_pricing import estimate_cost_usd

# R24.1 — retention policy. Rows older than this are auto-purged on
# read access. 90 days covers monthly invoicing cycles + a quarter
# of trend data; the operator can extend via env.
RETENTION_DAYS = max(1, int(
    os.environ.get("DIRECTJOB_LLM_COSTS_RETENTION_DAYS") or "90"))

# Throttle: only run the purge once per hour at most so a busy
# dashboard doesn't pay the DELETE cost on every request.
PURGE_THROTTLE_S = 3600


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _cutoff_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


class LLMCostTracker:
    """Thread-safe SQLite-backed call ledger."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self._lock = threading.RLock()
        self._last_purge_at: float = 0.0
        self._create_schema()

    def _create_schema(self) -> None:
        with self._lock:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_calls(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id        TEXT NOT NULL,
                    provider       TEXT NOT NULL,
                    model          TEXT NOT NULL,
                    task           TEXT NOT NULL DEFAULT '',
                    input_tokens   INTEGER NOT NULL,
                    output_tokens  INTEGER NOT NULL,
                    cost_usd       REAL NOT NULL,
                    created_at     TEXT NOT NULL
                )
                """
            )
            # Range queries (today, last 7 days) hit created_at; user
            # totals hit user_id; provider/task breakdowns hit those.
            for stmt in (
                "CREATE INDEX IF NOT EXISTS idx_llm_calls_created "
                "ON llm_calls(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_llm_calls_user "
                "ON llm_calls(user_id, created_at)",
            ):
                self.connection.execute(stmt)
            self.connection.commit()

    def record(self, *, user_id: str, provider: str, model: str,
                task: str, input_tokens: int, output_tokens: int,
                cost_usd: float | None = None) -> float:
        """Insert one call record. Returns the USD cost (computed if
        not supplied). Never raises — accounting MUST not break the
        user's chat."""
        if cost_usd is None:
            cost_usd = estimate_cost_usd(model, input_tokens,
                                           output_tokens)
        try:
            with self._lock:
                self.connection.execute(
                    "INSERT INTO llm_calls(user_id, provider, model, "
                    "task, input_tokens, output_tokens, cost_usd, "
                    "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_id or "", provider or "", model or "",
                      task or "", int(input_tokens or 0),
                      int(output_tokens or 0), float(cost_usd),
                      _now_iso()),
                )
                self.connection.commit()
        except sqlite3.Error:
            pass
        return float(cost_usd)

    # ---------------- Aggregation queries ----------------

    def today_total_usd(self) -> float:
        self._maybe_purge()
        prefix = _today_key()
        with self._lock:
            row = self.connection.execute(
                "SELECT COALESCE(SUM(cost_usd),0) FROM llm_calls "
                "WHERE created_at LIKE ?",
                (prefix + "%",),
            ).fetchone()
        return float(row[0] or 0.0)

    def today_total_for_user_usd(self, user_id: str) -> float:
        prefix = _today_key()
        with self._lock:
            row = self.connection.execute(
                "SELECT COALESCE(SUM(cost_usd),0) FROM llm_calls "
                "WHERE user_id = ? AND created_at LIKE ?",
                (user_id, prefix + "%"),
            ).fetchone()
        return float(row[0] or 0.0)

    def usage_last_n_days(self, n: int = 7) -> list[dict[str, float | str]]:
        """Daily totals for the last N days, oldest first. Each entry:
        ``{"date": "2026-05-13", "cost_usd": 1.23, "calls": 42}``."""
        self._maybe_purge()
        n = max(1, min(int(n), 90))
        with self._lock:
            rows = self.connection.execute(
                "SELECT substr(created_at,1,10) AS d, "
                "COALESCE(SUM(cost_usd),0), COUNT(*) "
                "FROM llm_calls "
                "WHERE date(created_at) >= date('now', ?) "
                "GROUP BY d ORDER BY d",
                (f"-{n - 1} days",),
            ).fetchall()
        return [
            {"date": r[0], "cost_usd": float(r[1]), "calls": int(r[2])}
            for r in rows
        ]

    def by_provider_today(self) -> list[dict[str, float | str]]:
        prefix = _today_key()
        with self._lock:
            rows = self.connection.execute(
                "SELECT provider, COALESCE(SUM(cost_usd),0), COUNT(*) "
                "FROM llm_calls WHERE created_at LIKE ? "
                "GROUP BY provider ORDER BY SUM(cost_usd) DESC",
                (prefix + "%",),
            ).fetchall()
        return [
            {"provider": r[0], "cost_usd": float(r[1]),
              "calls": int(r[2])}
            for r in rows
        ]

    def by_task_today(self) -> list[dict[str, float | str | int]]:
        prefix = _today_key()
        with self._lock:
            rows = self.connection.execute(
                "SELECT task, COALESCE(SUM(cost_usd),0), COUNT(*) "
                "FROM llm_calls WHERE created_at LIKE ? "
                "GROUP BY task ORDER BY SUM(cost_usd) DESC",
                (prefix + "%",),
            ).fetchall()
        return [
            {"task": r[0] or "unknown", "cost_usd": float(r[1]),
              "calls": int(r[2])}
            for r in rows
        ]

    def by_model_today(self) -> list[dict[str, float | str | int]]:
        prefix = _today_key()
        with self._lock:
            rows = self.connection.execute(
                "SELECT model, COALESCE(SUM(cost_usd),0), COUNT(*) "
                "FROM llm_calls WHERE created_at LIKE ? "
                "GROUP BY model ORDER BY SUM(cost_usd) DESC",
                (prefix + "%",),
            ).fetchall()
        return [
            {"model": r[0], "cost_usd": float(r[1]),
              "calls": int(r[2])}
            for r in rows
        ]

    def top_users_today(self, limit: int = 10) -> list[dict[str, float | str | int]]:
        prefix = _today_key()
        limit = max(1, min(int(limit), 100))
        with self._lock:
            rows = self.connection.execute(
                "SELECT user_id, COALESCE(SUM(cost_usd),0), COUNT(*) "
                "FROM llm_calls WHERE created_at LIKE ? "
                "GROUP BY user_id ORDER BY SUM(cost_usd) DESC LIMIT ?",
                (prefix + "%", limit),
            ).fetchall()
        return [
            {"user_id": r[0], "cost_usd": float(r[1]),
              "calls": int(r[2])}
            for r in rows
        ]

    def purge_older_than(self, days: int = RETENTION_DAYS) -> int:
        """R24.1 — delete rows older than ``days``. Returns row count
        deleted. Safe to call from any thread."""
        days = max(1, int(days))
        cutoff = _cutoff_iso(days)
        try:
            with self._lock:
                cur = self.connection.execute(
                    "DELETE FROM llm_calls WHERE created_at < ?",
                    (cutoff,),
                )
                self.connection.commit()
                return cur.rowcount or 0
        except sqlite3.Error:
            return 0

    def _maybe_purge(self) -> None:
        """Lazy retention sweep — runs at most once every
        PURGE_THROTTLE_S seconds. Called from read-side methods so
        the dashboard always sees a freshly-pruned dataset without
        paying the DELETE cost on every record() call."""
        now = time.time()
        if now - self._last_purge_at < PURGE_THROTTLE_S:
            return
        self._last_purge_at = now
        self.purge_older_than(RETENTION_DAYS)

    def close(self) -> None:
        try:
            self.connection.close()
        except sqlite3.Error:
            pass
