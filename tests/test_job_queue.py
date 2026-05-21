# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Background job queue contract tests (13-plan item 9/13;
gap #14).

Pins:
1. Enqueue → pending state with stable id.
2. run_once dispatches to the registered handler + marks
   completed.
3. Missing handler → dead with clear error (no silent drop).
4. Handler exception → retried with exponential backoff up to
   max_attempts, then dead.
5. Persistence across "process restart" (close + reopen).
6. Orphaned 'running' jobs from a prior process get reset to
   'pending' on init.
7. Stats roll up correctly by status + by kind.
8. Worker-thread start/stop is idempotent.
"""

from __future__ import annotations

import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.job_queue import (
    JOB_STATUSES,
    BackgroundJobQueue,
)


class EnqueueAndState(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.q = BackgroundJobQueue(Path(self.tmp.name) / "q.sqlite3")
        self.addCleanup(self.q.close)

    def test_enqueue_returns_stable_id(self):
        job_id = self.q.enqueue("test_kind", {"x": 1})
        self.assertTrue(job_id.startswith("job-"))
        self.assertEqual(len(job_id), 16)  # "job-" + 12 hex

    def test_enqueued_job_starts_pending(self):
        job_id = self.q.enqueue("test_kind", {"hello": "world"})
        record = self.q.get_job(job_id)
        self.assertEqual(record.status, "pending")
        self.assertEqual(record.kind, "test_kind")
        self.assertEqual(record.payload, {"hello": "world"})
        self.assertEqual(record.attempt, 0)
        self.assertIsNone(record.completed_at)

    def test_get_nonexistent_returns_none(self):
        self.assertIsNone(self.q.get_job("job-doesnotexist"))


class DispatchAndCompletion(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.q = BackgroundJobQueue(Path(self.tmp.name) / "q.sqlite3")
        self.addCleanup(self.q.close)
        self.calls: list[dict] = []

        def handler(payload):
            self.calls.append(payload)
            return {"echoed": payload}

        self.q.register_handler("echo", handler)

    def test_run_once_dispatches_handler(self):
        job_id = self.q.enqueue("echo", {"msg": "hi"})
        self.assertTrue(self.q.run_once())
        record = self.q.get_job(job_id)
        self.assertEqual(record.status, "completed")
        self.assertEqual(record.attempt, 1)
        self.assertEqual(record.result, {"echoed": {"msg": "hi"}})
        self.assertEqual(self.calls, [{"msg": "hi"}])

    def test_run_once_returns_false_when_empty(self):
        self.assertFalse(self.q.run_once())

    def test_completed_job_not_re_dispatched(self):
        self.q.enqueue("echo", {"once": True})
        self.assertTrue(self.q.run_once())
        # Second run sees no pending jobs
        self.assertFalse(self.q.run_once())
        self.assertEqual(len(self.calls), 1)


class MissingHandlerKillsJob(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.q = BackgroundJobQueue(Path(self.tmp.name) / "q.sqlite3")
        self.addCleanup(self.q.close)

    def test_unknown_kind_marked_dead_with_clear_error(self):
        job_id = self.q.enqueue("phantom_kind", {})
        self.q.run_once()
        record = self.q.get_job(job_id)
        self.assertEqual(record.status, "dead")
        self.assertIn("no_handler_for_kind", record.error)
        self.assertIn("phantom_kind", record.error)


class RetryWithBackoff(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.q = BackgroundJobQueue(
            Path(self.tmp.name) / "q.sqlite3", max_attempts=3
        )
        self.addCleanup(self.q.close)

        def always_fail(payload):
            raise ValueError("boom")

        self.q.register_handler("fail", always_fail)

    def test_failed_job_retries_until_max_attempts_then_dead(self):
        job_id = self.q.enqueue("fail", {}, max_attempts=2)
        # First run: fails, scheduled for retry
        self.assertTrue(self.q.run_once())
        record = self.q.get_job(job_id)
        self.assertEqual(record.status, "pending")
        self.assertEqual(record.attempt, 1)
        self.assertIsNotNone(record.next_attempt_at)
        # Backoff time is in the future, so run_once won't pick it
        # up. For the test we directly bump the next_attempt to
        # the past.
        self.q._connection.execute(
            "UPDATE background_jobs SET next_attempt_at = '2020-01-01T00:00:00+00:00' WHERE id = ?",
            (job_id,),
        )
        self.q._connection.commit()
        # Second run: hits max_attempts=2, marked dead
        self.assertTrue(self.q.run_once())
        record2 = self.q.get_job(job_id)
        self.assertEqual(record2.status, "dead")
        self.assertEqual(record2.attempt, 2)
        self.assertIn("ValueError", record2.error)
        self.assertIn("boom", record2.error)

    def test_backoff_is_exponential(self):
        # Enqueue + run once → next_attempt is ~1 minute out
        from datetime import datetime, timezone

        job_id = self.q.enqueue("fail", {}, max_attempts=10)
        self.q.run_once()
        rec_after_first = self.q.get_job(job_id)
        next_at = datetime.fromisoformat(rec_after_first.next_attempt_at)
        delta = (next_at - datetime.now(timezone.utc)).total_seconds()
        # Allow a bit of slack: backoff after attempt 1 = 2^0 = 1 min
        # so delta should be ~60s ± a few
        self.assertGreater(delta, 30)
        self.assertLess(delta, 90)


class PersistenceAcrossRestart(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "q.sqlite3"

    def test_pending_jobs_survive_restart(self):
        q1 = BackgroundJobQueue(self.path)
        job_id = q1.enqueue("any", {"data": 1})
        q1.close()

        q2 = BackgroundJobQueue(self.path)
        self.addCleanup(q2.close)
        record = q2.get_job(job_id)
        self.assertIsNotNone(record)
        self.assertEqual(record.status, "pending")
        self.assertEqual(record.payload, {"data": 1})

    def test_orphaned_running_jobs_reset_on_init(self):
        q1 = BackgroundJobQueue(self.path)
        job_id = q1.enqueue("any", {})
        # Manually mark as running (simulating a crashed worker)
        q1._connection.execute(
            "UPDATE background_jobs SET status = 'running', "
            "started_at = '2020-01-01T00:00:00+00:00' WHERE id = ?",
            (job_id,),
        )
        q1._connection.commit()
        q1.close()

        # New queue: _reset_orphans runs on init
        q2 = BackgroundJobQueue(self.path)
        self.addCleanup(q2.close)
        record = q2.get_job(job_id)
        self.assertEqual(record.status, "pending")
        self.assertIsNone(record.started_at)


class Stats(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.q = BackgroundJobQueue(Path(self.tmp.name) / "q.sqlite3")
        self.addCleanup(self.q.close)

        def succeed(_):
            return "ok"

        def fail(_):
            raise RuntimeError("nope")

        self.q.register_handler("good", succeed)
        self.q.register_handler("bad", fail)

    def test_stats_aggregate_correctly(self):
        # 3 good, 2 bad
        for _ in range(3):
            self.q.enqueue("good", {})
        for _ in range(2):
            self.q.enqueue("bad", {}, max_attempts=1)
        # Drain
        while self.q.run_once():
            pass
        stats = self.q.stats()
        self.assertEqual(stats.completed, 3)
        self.assertEqual(stats.dead, 2)
        self.assertEqual(stats.pending, 0)
        self.assertEqual(stats.total, 5)
        self.assertEqual(stats.by_kind.get("good"), 3)
        self.assertEqual(stats.by_kind.get("bad"), 2)


class WorkerStartStopIdempotent(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.q = BackgroundJobQueue(
            Path(self.tmp.name) / "q.sqlite3", worker_count=2
        )
        self.addCleanup(self.q.close)

    def test_start_idempotent(self):
        self.q.start()
        worker_count_after_first = len(self.q._workers)
        self.q.start()  # second call is a no-op
        self.assertEqual(len(self.q._workers), worker_count_after_first)
        self.assertEqual(worker_count_after_first, 2)

    def test_start_and_stop_lifecycle(self):
        self.q.start()
        self.assertEqual(len(self.q._workers), 2)
        self.q.stop(timeout=2.0)
        self.assertEqual(len(self.q._workers), 0)

    def test_workers_process_jobs_when_started(self):
        results: list[str] = []

        def handler(payload):
            results.append(payload.get("msg", ""))
            return "done"

        self.q.register_handler("echo", handler)
        for i in range(5):
            self.q.enqueue("echo", {"msg": f"m{i}"})
        self.q.start()
        # Give workers time to drain
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if self.q.stats().pending == 0 and self.q.stats().running == 0:
                break
            time.sleep(0.05)
        self.q.stop(timeout=2.0)
        # All 5 processed
        self.assertEqual(len(results), 5)
        self.assertEqual(self.q.stats().completed, 5)


class ConstructorValidation(unittest.TestCase):
    def test_worker_count_must_be_positive(self):
        with self.assertRaises(ValueError):
            BackgroundJobQueue("/tmp/x.sqlite3", worker_count=0)


class JobStatusesConstant(unittest.TestCase):
    def test_all_known_statuses_documented(self):
        self.assertEqual(
            set(JOB_STATUSES),
            {"pending", "running", "completed", "failed", "dead"},
        )


if __name__ == "__main__":
    unittest.main()
