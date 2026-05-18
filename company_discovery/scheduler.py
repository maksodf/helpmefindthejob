# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Durable, sqlite-backed scheduler for watchlist scans.

Replaces the previous in-process volatile timer. Jobs persist across
process restarts. The scheduler is intentionally minimal — single
sqlite table, single worker thread, no cron expressions, just per-user
"every N minutes" intervals matching the existing watchlist contract.

Design choices
--------------

- One row per user: ``(user_id, enabled, interval_minutes, last_run_at,
  last_run_status, last_run_trigger, next_run_at)``.
- A worker thread wakes every ``poll_seconds`` and claims due jobs by
  marking them ``running``, computing ``next_run_at`` as
  ``now + interval``, and invoking the user-supplied callable. State is
  persisted before and after the call so a crash never leaves a job in
  ``running`` for the next process — startup resets any orphaned
  ``running`` rows to ``idle``.
- Failures increment ``consecutive_failures`` and apply backoff up to
  ``max_backoff_minutes`` so a broken target does not consume the
  entire budget.
- The handler is plain Python; the scheduler does not know what a scan
  is. Tests inject a fake handler.
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


@dataclass
class ScheduleRecord:
    user_id: str
    enabled: bool
    interval_minutes: int
    last_run_at: datetime | None
    last_run_status: str
    last_run_trigger: str | None
    next_run_at: datetime | None
    consecutive_failures: int
    state: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "intervalMinutes": self.interval_minutes,
            "lastRunAt": self.last_run_at.isoformat() if self.last_run_at else None,
            "lastRunStatus": self.last_run_status,
            "lastRunTrigger": self.last_run_trigger,
            "nextRunAt": self.next_run_at.isoformat() if self.next_run_at else None,
            "consecutiveFailures": self.consecutive_failures,
            "state": self.state,
        }


JobHandler = Callable[[str, str], dict[str, Any]]
"""``(user_id, trigger) -> result_dict``. Result must contain ``status``."""


class DurableScheduler:
    def __init__(
        self,
        path: str | Path,
        *,
        handler: JobHandler,
        poll_seconds: int = 30,
        max_backoff_minutes: int = 240,
        min_interval_minutes: int = 15,
        max_interval_minutes: int = 10_080,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handler = handler
        self.poll_seconds = max(1, int(poll_seconds))
        self.max_backoff_minutes = int(max_backoff_minutes)
        self.min_interval_minutes = int(min_interval_minutes)
        self.max_interval_minutes = int(max_interval_minutes)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._create_schema()
        self._reset_orphans()

    # ---- schema ----

    def _create_schema(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schedules (
                user_id TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0,
                interval_minutes INTEGER NOT NULL DEFAULT 360,
                last_run_at TEXT,
                last_run_status TEXT NOT NULL DEFAULT 'disabled',
                last_run_trigger TEXT,
                next_run_at TEXT,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                state TEXT NOT NULL DEFAULT 'idle'
            )
            """
        )
        self._connection.commit()

    def _reset_orphans(self) -> None:
        with self._lock:
            self._connection.execute("UPDATE schedules SET state = 'idle' WHERE state = 'running'")
            self._connection.commit()

    # ---- read/write ----

    def get(self, user_id: str) -> ScheduleRecord:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT user_id, enabled, interval_minutes, last_run_at, last_run_status,
                       last_run_trigger, next_run_at, consecutive_failures, state
                FROM schedules WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return ScheduleRecord(
                user_id=user_id,
                enabled=False,
                interval_minutes=360,
                last_run_at=None,
                last_run_status="disabled",
                last_run_trigger=None,
                next_run_at=None,
                consecutive_failures=0,
                state="idle",
            )
        return ScheduleRecord(
            user_id=row[0],
            enabled=bool(row[1]),
            interval_minutes=int(row[2]),
            last_run_at=_parse_dt(row[3]),
            last_run_status=row[4] or "disabled",
            last_run_trigger=row[5],
            next_run_at=_parse_dt(row[6]),
            consecutive_failures=int(row[7] or 0),
            state=row[8] or "idle",
        )

    def all(self) -> list[ScheduleRecord]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT user_id, enabled, interval_minutes, last_run_at, last_run_status,
                       last_run_trigger, next_run_at, consecutive_failures, state
                FROM schedules ORDER BY user_id
                """
            ).fetchall()
        return [
            ScheduleRecord(
                user_id=row[0],
                enabled=bool(row[1]),
                interval_minutes=int(row[2]),
                last_run_at=_parse_dt(row[3]),
                last_run_status=row[4] or "disabled",
                last_run_trigger=row[5],
                next_run_at=_parse_dt(row[6]),
                consecutive_failures=int(row[7] or 0),
                state=row[8] or "idle",
            )
            for row in rows
        ]

    def upsert(self, user_id: str, *, enabled: bool, interval_minutes: int) -> ScheduleRecord:
        clamped = max(
            self.min_interval_minutes, min(int(interval_minutes), self.max_interval_minutes)
        )
        existing = self.get(user_id)
        if enabled:
            base = existing.last_run_at or _now() - timedelta(minutes=clamped)
            next_run = base + timedelta(minutes=clamped)
            if next_run < _now():
                next_run = _now()
        else:
            next_run = None
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO schedules(user_id, enabled, interval_minutes, last_run_at,
                                      last_run_status, last_run_trigger, next_run_at,
                                      consecutive_failures, state)
                VALUES(?, ?, ?, ?, ?, ?, ?, 0, 'idle')
                ON CONFLICT(user_id) DO UPDATE SET
                    enabled = excluded.enabled,
                    interval_minutes = excluded.interval_minutes,
                    next_run_at = excluded.next_run_at,
                    state = 'idle'
                """,
                (
                    user_id,
                    1 if enabled else 0,
                    clamped,
                    existing.last_run_at.isoformat() if existing.last_run_at else None,
                    existing.last_run_status if enabled else "disabled",
                    existing.last_run_trigger,
                    next_run.isoformat() if next_run else None,
                ),
            )
            self._connection.commit()
        return self.get(user_id)

    def record_run(
        self,
        user_id: str,
        *,
        status: str,
        trigger: str,
        success: bool,
    ) -> ScheduleRecord:
        existing = self.get(user_id)
        if success:
            consecutive = 0
        else:
            consecutive = existing.consecutive_failures + 1
        if existing.enabled:
            interval = existing.interval_minutes
            if not success and consecutive > 1:
                backoff = min(interval * (2 ** (consecutive - 1)), self.max_backoff_minutes)
                interval = max(interval, int(backoff))
            next_run = _now() + timedelta(minutes=interval)
        else:
            next_run = None
        last_run_at = _now()
        with self._lock:
            self._connection.execute(
                """
                UPDATE schedules SET
                    last_run_at = ?, last_run_status = ?, last_run_trigger = ?,
                    next_run_at = ?, consecutive_failures = ?, state = 'idle'
                WHERE user_id = ?
                """,
                (
                    last_run_at.isoformat(),
                    status,
                    trigger,
                    next_run.isoformat() if next_run else None,
                    consecutive,
                    user_id,
                ),
            )
            self._connection.commit()
        return self.get(user_id)

    # ---- worker ----

    def _claim_due(self, now: datetime | None = None) -> ScheduleRecord | None:
        now = now or _now()
        with self._lock:
            row = self._connection.execute(
                """
                SELECT user_id FROM schedules
                WHERE enabled = 1 AND state = 'idle'
                  AND next_run_at IS NOT NULL AND next_run_at <= ?
                ORDER BY next_run_at ASC LIMIT 1
                """,
                (now.isoformat(),),
            ).fetchone()
            if row is None:
                return None
            user_id = row[0]
            self._connection.execute(
                "UPDATE schedules SET state = 'running' WHERE user_id = ? AND state = 'idle'",
                (user_id,),
            )
            self._connection.commit()
        return self.get(user_id)

    def run_due(self) -> list[ScheduleRecord]:
        results: list[ScheduleRecord] = []
        while True:
            record = self._claim_due()
            if record is None:
                break
            try:
                outcome = self.handler(record.user_id, "scheduled")
                status = str(outcome.get("status") or "completed")
                success = status not in {
                    "failed",
                    "blocked_or_unavailable",
                    "blocked_or_captcha",
                    "blocked_by_robots",
                    "restricted_platform",
                    "missing_career_page",
                }
            except Exception as error:  # noqa: BLE001 - resilient worker
                status = f"failed: {error}"
                success = False
            results.append(
                self.record_run(record.user_id, status=status, trigger="scheduled", success=success)
            )
        return results

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="DurableScheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def close(self) -> None:
        self.stop()
        with self._lock:
            self._connection.close()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.run_due()
            except Exception:  # noqa: BLE001 - never let the loop die
                pass
            self._stop.wait(self.poll_seconds)
