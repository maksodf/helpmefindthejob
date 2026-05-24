# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Background job queue (13-plan item 9/13; gap #14).

Stdlib-only persistent queue. Survives process restarts via
SQLite, dispatches to user-registered handlers in worker threads,
retries failed jobs with exponential backoff.

Use cases this unlocks:

1. **Long-running aggregator fan-out** can be enqueued + the
   HTTP request returns immediately with a job_id. The frontend
   polls /api/jobs/<id> for status.
2. **Scheduled scans** that take >30s no longer hang the
   scheduler thread — they run in the background queue.
3. **Failed jobs retry automatically** with exponential backoff
   (1m → 2m → 4m → 8m → … max_backoff_minutes).
4. **Operator visibility**: queue depth + per-job history via
   :meth:`stats`.

Design constraints:

- **Stdlib only** — sqlite3 + threading. No Celery, no RQ, no
  Redis. Multi-process deploys CAN coordinate via SQLite WAL
  but the recommended pattern is one queue per app process.
- **No exactly-once guarantee** — at-least-once. Handlers must
  be idempotent. The retry semantics fire any failed job up to
  ``max_attempts`` times.
- **Per-handler timeout** — a handler that hangs blocks one
  worker thread; with ``worker_count=2`` (default), a single
  hang doesn't stall the whole queue. A hard timeout would
  need subprocess-level kill (out of scope for v1).
- **Crash recovery** — on boot, any job in `running` state from
  a previous process is reset to `pending` (matches the
  DurableScheduler's _reset_orphans pattern).

The existing :class:`DurableScheduler` handles per-user
recurring schedules (e.g., "scan Aïcha's watchlist every 6h").
This queue handles ad-hoc background work. The two compose:
the scheduler tick can enqueue a queue job to do the actual
scan, returning immediately while the worker does the work.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

_log = logging.getLogger(__name__)


# Handler signature: takes the payload dict, returns a JSON-
# serializable result (or raises on failure). All handlers run
# on a worker thread.
JobHandler = Callable[[dict[str, Any]], Any]


JOB_STATUSES: tuple[str, ...] = (
    "pending",
    "running",
    "completed",
    "failed",
    "dead",  # exhausted all retries
)


@dataclass(frozen=True)
class JobRecord:
    """One job's state at a point in time."""

    id: str
    kind: str
    payload: dict[str, Any]
    status: str
    attempt: int
    max_attempts: int
    created_at: str
    started_at: str | None
    completed_at: str | None
    error: str | None
    result: Any | None
    next_attempt_at: str | None


@dataclass(frozen=True)
class QueueStats:
    """Operator-facing snapshot of queue state."""

    pending: int
    running: int
    completed: int
    failed: int
    dead: int
    total: int
    by_kind: dict[str, int]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


class BackgroundJobQueue:
    """Persistent job queue + worker pool.

    Construct one per app process. Register handlers via
    :meth:`register_handler`, then call :meth:`start` to spin
    up worker threads. Enqueue work via :meth:`enqueue`.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        worker_count: int = 2,
        max_attempts: int = 5,
        max_backoff_minutes: int = 30,
        poll_seconds: float = 1.0,
    ) -> None:
        if worker_count < 1:
            raise ValueError("worker_count must be >= 1")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.worker_count = worker_count
        self.max_attempts = max_attempts
        self.max_backoff_minutes = max_backoff_minutes
        self.poll_seconds = poll_seconds
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._workers: list[threading.Thread] = []
        self._handlers: dict[str, JobHandler] = {}
        self._create_schema()
        self._reset_orphans()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _create_schema(self) -> None:
        with self._lock:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS background_jobs (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 5,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    next_attempt_at TEXT,
                    error TEXT,
                    result TEXT
                )
                """
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_status_attempt "
                "ON background_jobs(status, next_attempt_at)"
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_kind ON background_jobs(kind)"
            )
            self._connection.commit()

    def _reset_orphans(self) -> None:
        """On boot, any job stuck in 'running' from a previous
        process gets reset to 'pending' so a new worker picks it
        up. Without this, a crashed worker leaves jobs stranded."""

        with self._lock:
            self._connection.execute(
                "UPDATE background_jobs SET status = 'pending', "
                "started_at = NULL WHERE status = 'running'"
            )
            self._connection.commit()

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def register_handler(self, kind: str, handler: JobHandler) -> None:
        """Register a callable to dispatch jobs of ``kind``."""

        if not kind:
            raise ValueError("kind_must_not_be_empty")
        with self._lock:
            self._handlers[kind] = handler

    def registered_kinds(self) -> list[str]:
        with self._lock:
            return sorted(self._handlers)

    # ------------------------------------------------------------------
    # Enqueue + introspection
    # ------------------------------------------------------------------

    def enqueue(
        self,
        kind: str,
        payload: dict[str, Any] | None = None,
        *,
        max_attempts: int | None = None,
    ) -> str:
        """Add a job to the queue. Returns the job id. The job
        starts in ``pending`` and is picked up by the next free
        worker.

        Unknown kinds are allowed at enqueue time — the worker
        thread surfaces the missing-handler condition at
        dispatch time (marks the job 'dead' with a clear
        error). This lets producers + consumers deploy
        independently."""

        import uuid

        job_id = f"job-{uuid.uuid4().hex[:12]}"
        attempts = int(max_attempts if max_attempts is not None else self.max_attempts)
        attempts = max(1, attempts)
        now = _now_iso()
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO background_jobs
                (id, kind, payload, status, attempt, max_attempts,
                 created_at, next_attempt_at)
                VALUES (?, ?, ?, 'pending', 0, ?, ?, ?)
                """,
                (
                    job_id,
                    kind,
                    json.dumps(payload or {}, default=str),
                    attempts,
                    now,
                    now,
                ),
            )
            self._connection.commit()
        return job_id

    def get_job(self, job_id: str) -> JobRecord | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT id, kind, payload, status, attempt, max_attempts,
                       created_at, started_at, completed_at,
                       next_attempt_at, error, result
                FROM background_jobs WHERE id = ?
                """,
                (job_id,),
            ).fetchone()
        return _row_to_record(row) if row else None

    def stats(self) -> QueueStats:
        """Snapshot of queue depths by status + by kind. Used by
        the operator-facing diagnostic endpoint."""

        with self._lock:
            counts = dict(
                self._connection.execute(
                    "SELECT status, COUNT(*) FROM background_jobs GROUP BY status"
                ).fetchall()
            )
            by_kind = dict(
                self._connection.execute(
                    "SELECT kind, COUNT(*) FROM background_jobs GROUP BY kind"
                ).fetchall()
            )
        return QueueStats(
            pending=int(counts.get("pending", 0)),
            running=int(counts.get("running", 0)),
            completed=int(counts.get("completed", 0)),
            failed=int(counts.get("failed", 0)),
            dead=int(counts.get("dead", 0)),
            total=sum(int(v) for v in counts.values()),
            by_kind=by_kind,
        )

    # ------------------------------------------------------------------
    # Worker loop
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Spin up the worker threads. Idempotent — calling
        twice is a no-op."""

        with self._lock:
            if self._workers:
                return
            for i in range(self.worker_count):
                thread = threading.Thread(
                    target=self._worker_loop,
                    name=f"jobqueue-worker-{i}",
                    daemon=True,
                )
                thread.start()
                self._workers.append(thread)

    def stop(self, *, timeout: float = 5.0) -> None:
        """Signal workers to exit + wait for them. Used in
        tests + on graceful shutdown."""

        self._stop.set()
        for thread in self._workers:
            thread.join(timeout=timeout)
        with self._lock:
            self._workers.clear()
            self._stop.clear()

    def run_once(self) -> bool:
        """Synchronous variant of one worker iteration. Used by
        tests + ad-hoc operator scripts. Returns True if a job
        was processed, False if the queue was empty."""

        return self._claim_and_run_one()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            ran = False
            try:
                ran = self._claim_and_run_one()
            except Exception:  # noqa: BLE001 - log + keep worker alive
                _log.exception("jobqueue worker crashed in claim_and_run")
            if not ran:
                # Idle — sleep briefly to avoid tight-loop
                # against an empty queue
                self._stop.wait(self.poll_seconds)

    def _claim_and_run_one(self) -> bool:
        """Atomically claim one pending job (UPDATE … RETURNING
        is sqlite-3.35+; we fall back to SELECT + UPDATE inside
        a transaction). Returns True if a job ran, False if
        nothing was eligible."""

        now_iso = _now_iso()
        with self._lock:
            row = self._connection.execute(
                """
                SELECT id, kind, payload, status, attempt, max_attempts,
                       created_at, started_at, completed_at,
                       next_attempt_at, error, result
                FROM background_jobs
                WHERE status = 'pending' AND (
                    next_attempt_at IS NULL OR next_attempt_at <= ?
                )
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (now_iso,),
            ).fetchone()
            if not row:
                return False
            job = _row_to_record(row)
            # Atomically claim
            self._connection.execute(
                "UPDATE background_jobs SET status = 'running', "
                "started_at = ?, attempt = attempt + 1 WHERE id = ?",
                (now_iso, job.id),
            )
            self._connection.commit()
        # Reload to get the bumped attempt
        with self._lock:
            updated = self._connection.execute(
                "SELECT attempt FROM background_jobs WHERE id = ?",
                (job.id,),
            ).fetchone()
        current_attempt = int(updated[0]) if updated else (job.attempt + 1)
        self._dispatch(job, current_attempt)
        return True

    def _dispatch(self, job: JobRecord, current_attempt: int) -> None:
        handler = self._handlers.get(job.kind)
        if handler is None:
            self._finalise(
                job.id,
                status="dead",
                error=f"no_handler_for_kind:{job.kind!r}",
                result=None,
            )
            return
        try:
            result = handler(job.payload)
        except Exception as exc:  # noqa: BLE001 - all handler failures route through retry
            self._handle_failure(job, current_attempt, exc)
            return
        self._finalise(
            job.id,
            status="completed",
            error=None,
            result=result,
        )

    def _handle_failure(self, job: JobRecord, current_attempt: int, exc: BaseException) -> None:
        error_msg = f"{type(exc).__name__}: {exc}"[:500]
        if current_attempt >= job.max_attempts:
            self._finalise(
                job.id,
                status="dead",
                error=error_msg,
                result=None,
            )
            return
        # Exponential backoff: 1m, 2m, 4m, 8m, …, capped
        backoff_minutes = min(
            self.max_backoff_minutes,
            2 ** (current_attempt - 1),
        )
        next_at = (_now_dt() + timedelta(minutes=backoff_minutes)).isoformat(timespec="seconds")
        with self._lock:
            self._connection.execute(
                """
                UPDATE background_jobs
                SET status = 'pending',
                    next_attempt_at = ?,
                    error = ?,
                    started_at = NULL
                WHERE id = ?
                """,
                (next_at, error_msg, job.id),
            )
            self._connection.commit()

    def _finalise(
        self,
        job_id: str,
        *,
        status: str,
        error: str | None,
        result: Any | None,
    ) -> None:
        if status not in JOB_STATUSES:
            raise ValueError(f"invalid_status:{status!r}")
        result_json = json.dumps(result, default=str) if result is not None else None
        with self._lock:
            self._connection.execute(
                """
                UPDATE background_jobs
                SET status = ?,
                    completed_at = ?,
                    error = ?,
                    result = ?
                WHERE id = ?
                """,
                (status, _now_iso(), error, result_json, job_id),
            )
            self._connection.commit()

    def close(self) -> None:
        """Close the SQLite connection. Tests call this to free
        the file handle before TemporaryDirectory cleanup."""

        self.stop()
        with self._lock:
            self._connection.close()


def _row_to_record(row: tuple) -> JobRecord:
    return JobRecord(
        id=row[0],
        kind=row[1],
        payload=json.loads(row[2]) if row[2] else {},
        status=row[3],
        attempt=int(row[4]),
        max_attempts=int(row[5]),
        created_at=row[6],
        started_at=row[7],
        completed_at=row[8],
        next_attempt_at=row[9],
        error=row[10],
        result=json.loads(row[11]) if row[11] else None,
    )
