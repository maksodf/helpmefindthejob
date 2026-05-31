# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guard for the quota TOCTOU fix.

can_run_ai()/record_ai_run() (and can_start_scan()/record_scan_started()) were
two separate locked sections with real work — including the multi-second AI call
— between them, so concurrent requests at the daily limit all passed the check
before any of them incremented. The request path now uses atomic reserve_ai_run
/ reserve_scan (check-and-consume under one lock); the old methods are retained
for callers that genuinely want a separate check + record.
"""

from __future__ import annotations

import concurrent.futures
import os
import tempfile
import unittest

from company_discovery.quotas import QuotaError, QuotaLimits, QuotaStore


def _store(*, ai: int = 100, scans: int = 100, active: int = 100, dom: int = 100) -> QuotaStore:
    db = os.path.join(tempfile.mkdtemp(), "q.sqlite3")
    return QuotaStore(
        db,
        limits=QuotaLimits(
            scans_per_day=scans, ai_per_day=ai, active_scans=active, domain_per_hour=dom
        ),
    )


class ReserveAtomicityTests(unittest.TestCase):
    def test_reserve_ai_run_grants_exactly_the_limit_under_concurrency(self) -> None:
        store = _store(ai=2)

        def attempt(_: int) -> bool:
            try:
                store.reserve_ai_run("u1")
                return True
            except QuotaError:
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            results = list(ex.map(attempt, range(12)))
        self.assertEqual(sum(results), 2, "reserve_ai_run must not overshoot the limit (TOCTOU)")

    def test_reserve_scan_grants_exactly_the_limit_under_concurrency(self) -> None:
        store = _store(scans=2, active=100)

        def attempt(_: int) -> bool:
            try:
                store.reserve_scan("u1")
                return True
            except QuotaError:
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            results = list(ex.map(attempt, range(12)))
        self.assertEqual(sum(results), 2)

    def test_reserve_ai_run_raises_at_limit(self) -> None:
        store = _store(ai=1)
        store.reserve_ai_run("u1")
        with self.assertRaises(QuotaError):
            store.reserve_ai_run("u1")


if __name__ == "__main__":
    unittest.main()
