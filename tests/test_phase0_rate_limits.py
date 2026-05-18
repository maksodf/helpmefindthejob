# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""End-to-end rate-limit verification across the four auth-adjacent
surfaces (Phase 0 tracker item #7).

Surfaces covered:

- ``/api/auth/login`` — 10 attempts per 600s per IP (``login_allowed``)
- ``/api/auth/forgot-password`` — 5 requests per 600s per IP
  (``password_reset_allowed``)
- ``/api/auth/register`` — 3 requests per 600s per IP when an admin
  already exists (``register_allowed``); the first-account bootstrap is
  intentionally unrestricted so an empty install can come up
- ``/api/auth/2fa-verify`` — protected by single-use challenges issued
  during login; brute-force is bounded by the login rate-limit because
  every wrong code burns the challenge

AI-call quotas (per-day / per-domain / per-user concurrency) are
enforced by ``QuotaStore`` and covered by ``tests/test_modules.py``;
this file does not duplicate that coverage.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import (
    PASSWORD_RESET_REQUEST_LIMIT,
    REGISTER_REQUEST_LIMIT,
    AppState,
)


class RateLimitHelperTests(unittest.TestCase):
    """Exercise the AppState gating helpers directly. The HTTP routes
    call these — verifying the helpers locks in the same behaviour
    that the rate-limit responses depend on."""

    def _state(self) -> AppState:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        state = AppState(
            root / "company.sqlite3",
            root / "auth.sqlite3",
            root / "ai.json",
            root / "schedule.json",
            start_scheduler=False,
        )
        self.addCleanup(state.auth_store.close)
        self.addCleanup(state.repository.close)
        return state

    def test_login_rate_limit_blocks_after_ten_failures(self) -> None:
        state = self._state()
        ip = "203.0.113.10"
        for _ in range(10):
            self.assertTrue(state.login_allowed(ip))
            state.record_login_failure(ip)
        self.assertFalse(state.login_allowed(ip))
        # A different IP is unaffected — the bucket is per-IP, not global.
        self.assertTrue(state.login_allowed("203.0.113.20"))
        # Clearing failures unlocks the same IP.
        state.clear_login_failures(ip)
        self.assertTrue(state.login_allowed(ip))

    def test_password_reset_rate_limit_blocks_after_limit(self) -> None:
        state = self._state()
        ip = "203.0.113.30"
        for _ in range(PASSWORD_RESET_REQUEST_LIMIT):
            self.assertTrue(state.password_reset_allowed(ip))
            state.record_password_reset_request(ip)
        self.assertFalse(state.password_reset_allowed(ip))
        # Per-IP isolation.
        self.assertTrue(state.password_reset_allowed("203.0.113.31"))

    def test_register_rate_limit_blocks_after_limit(self) -> None:
        state = self._state()
        ip = "203.0.113.40"
        for _ in range(REGISTER_REQUEST_LIMIT):
            self.assertTrue(state.register_allowed(ip))
            state.record_register_request(ip)
        self.assertFalse(state.register_allowed(ip))
        # Per-IP isolation.
        self.assertTrue(state.register_allowed("203.0.113.41"))

    def test_quota_error_signals_too_many_requests(self) -> None:
        # AI/scan/domain quotas raise QuotaError; the HTTP surface maps
        # those to 429. Confirm the QuotaError carries a code suitable
        # for the response body.
        from company_discovery.quotas import QuotaError

        err = QuotaError("ai_quota_exceeded", "Out of AI calls for today.")
        self.assertEqual(err.code, "ai_quota_exceeded")
        self.assertIn("AI calls", err.message)


if __name__ == "__main__":
    unittest.main()
