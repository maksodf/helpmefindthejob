# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""2026-05-23: /api/auth/status per-IP rate limit.

Pre-fix the endpoint was unprotected. The SPA polls it; an unbounded
poller (or a hostile probe) drowned logs and enabled session-
validity enumeration. Post-fix: 60 requests/minute/IP. Legitimate
single-tab polling is ~1/minute so the cap is 60× generous, while
still tight enough that a hostile script gets cut off fast.
"""

from __future__ import annotations

import unittest


class StatusSlotRateLimit(unittest.TestCase):
    """Direct test of the rate-limit slot — bypasses HTTP layer so
    we can exercise the limit synchronously without needing real
    elapsed time."""

    def test_first_60_pass_then_429_slot_returns_false(self) -> None:
        from app import STATE, STATUS_REQUEST_LIMIT
        client = "192.0.2.42"
        # Ensure the bucket starts empty for this client
        with STATE._status_request_lock:  # noqa: SLF001 — test setup
            STATE._status_requests.pop(client, None)
        for _ in range(STATUS_REQUEST_LIMIT):
            self.assertTrue(STATE.claim_status_slot(client))
        # 61st claim should fail
        self.assertFalse(STATE.claim_status_slot(client))

    def test_different_ips_have_independent_buckets(self) -> None:
        from app import STATE, STATUS_REQUEST_LIMIT
        a, b = "192.0.2.43", "192.0.2.44"
        with STATE._status_request_lock:  # noqa: SLF001
            STATE._status_requests.pop(a, None)
            STATE._status_requests.pop(b, None)
        # Burn through A's budget
        for _ in range(STATUS_REQUEST_LIMIT):
            self.assertTrue(STATE.claim_status_slot(a))
        self.assertFalse(STATE.claim_status_slot(a))
        # B's bucket must be untouched
        self.assertTrue(STATE.claim_status_slot(b))

    def test_window_rolls_when_timestamps_age_out(self) -> None:
        import time
        from app import STATE, STATUS_REQUEST_LIMIT, STATUS_REQUEST_WINDOW
        client = "192.0.2.45"
        with STATE._status_request_lock:  # noqa: SLF001
            # Pre-fill the bucket with old timestamps that should be
            # treated as out-of-window on the next check
            STATE._status_requests[client] = [
                time.time() - (STATUS_REQUEST_WINDOW + 5)
            ] * STATUS_REQUEST_LIMIT
        # New claim succeeds because all stored timestamps are stale
        self.assertTrue(STATE.claim_status_slot(client))


if __name__ == "__main__":
    unittest.main()
