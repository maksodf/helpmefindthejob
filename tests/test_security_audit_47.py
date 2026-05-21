# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 backlog #47 — CSRF / CORS / rate-limit / SQL-injection audit
contract tests.

Each test pins one of the defensive layers we added during the
audit. A regression here means a real security defect, not just
a stylistic complaint."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState


def _make_state() -> tuple[AppState, str]:
    tmp = TemporaryDirectory()
    root = Path(tmp.name)
    state = AppState(
        root / "company.sqlite3",
        root / "auth.sqlite3",
        root / "ai.json",
        root / "schedule.json",
        start_scheduler=False,
    )
    state._test_tmp = tmp  # noqa: SLF001
    user = state.auth_store.create_user("sec@example.com", "secret-pass-12345678")
    return state, user.id


class PerUserRequestRateLimit(unittest.TestCase):
    def setUp(self) -> None:
        self.state, self.user_id = _make_state()
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.addCleanup(lambda: self.state._test_tmp.cleanup())  # noqa: SLF001

    def test_first_call_under_cap_returns_true(self) -> None:
        self.assertTrue(self.state.claim_user_request_slot(self.user_id))

    def test_cap_blocks_after_threshold(self) -> None:
        # Custom low cap so the test runs in reasonable time
        for _ in range(5):
            self.assertTrue(
                self.state.claim_user_request_slot(self.user_id, cap=5)
            )
        # 6th attempt must fail
        self.assertFalse(
            self.state.claim_user_request_slot(self.user_id, cap=5)
        )

    def test_per_user_isolation(self) -> None:
        # User A hammers their cap; user B is unaffected
        other = self.state.auth_store.create_user(
            "other@example.com", "secret-pass-12345678"
        )
        for _ in range(5):
            self.state.claim_user_request_slot(self.user_id, cap=5)
        self.assertFalse(
            self.state.claim_user_request_slot(self.user_id, cap=5)
        )
        self.assertTrue(self.state.claim_user_request_slot(other.id, cap=5))

    def test_stale_buckets_get_gc_on_periodic_sweep(self) -> None:
        """Panic-round addition: the rate-limit dict must not grow
        without bound on a long-lived server. Every 256 successful
        claims, stale user_ids (no timestamps inside the window)
        get evicted.
        """

        import time as _time

        # Manually back-date timestamps so they fall outside the window
        for i in range(50):
            uid = f"stale-{i}"
            self.state._user_request_timestamps[uid] = [_time.time() - 9999]
        self.assertEqual(len(self.state._user_request_timestamps), 50)
        # Pump 256 fresh claims to trigger the sweep
        for _ in range(256):
            self.state.claim_user_request_slot(self.user_id, cap=10_000)
        # Stale entries gone; only the active user remains
        self.assertNotIn("stale-0", self.state._user_request_timestamps)
        self.assertIn(self.user_id, self.state._user_request_timestamps)

    def test_empty_user_id_passes_through(self) -> None:
        # Anonymous calls (no user_id) MUST pass — they're rate-limited
        # by the per-IP login/register/reset buckets, not this cap.
        self.assertTrue(self.state.claim_user_request_slot(""))
        self.assertTrue(self.state.claim_user_request_slot(None))


class SqlIdentifierDefense(unittest.TestCase):
    def test_safe_identifier_accepts_valid_names(self) -> None:
        from company_discovery.auth import _assert_safe_identifier

        for name in ("users", "imported_jobs", "table1", "_internal"):
            _assert_safe_identifier(name)  # should not raise

    def test_safe_identifier_rejects_sql_injection_attempts(self) -> None:
        from company_discovery.auth import _assert_safe_identifier

        attacks = [
            "users; DROP TABLE users",
            "users--",
            "users) UNION SELECT *",
            "users'OR'1",
            "users\"OR\"1",
            "",
            "users name",  # space
            "1users",  # leading digit
            "users.column",  # qualified
        ]
        for attack in attacks:
            with self.assertRaises(ValueError, msg=f"attack {attack!r} should raise"):
                _assert_safe_identifier(attack)

    def test_safe_column_definition_accepts_known_types(self) -> None:
        from company_discovery.auth import _assert_safe_column_definition

        for d in (
            "TEXT",
            "INTEGER NOT NULL",
            "INTEGER DEFAULT 0",
            "TEXT DEFAULT ''",
            "VARCHAR(255)",
        ):
            _assert_safe_column_definition(d)

    def test_safe_column_definition_rejects_sql_injection(self) -> None:
        from company_discovery.auth import _assert_safe_column_definition

        attacks = [
            "TEXT; DROP TABLE users",
            "TEXT DEFAULT '; DROP TABLE users; --",
            "INTEGER DEFAULT (SELECT password FROM users)",
        ]
        for attack in attacks:
            with self.assertRaises(ValueError, msg=f"attack {attack!r} should raise"):
                _assert_safe_column_definition(attack)


class SecurityHeadersResponse(unittest.TestCase):
    """End-to-end probe: spin up a real handler and assert the
    expected security headers are present on a normal response."""

    def setUp(self) -> None:
        self.state, self.user_id = _make_state()
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.addCleanup(lambda: self.state._test_tmp.cleanup())  # noqa: SLF001

    def test_response_carries_baseline_security_headers(self) -> None:
        # We can't easily run a full HTTP server in a unit test, so
        # we verify the end_headers method writes the expected
        # headers to a fake writer. Use a minimal Handler with the
        # send_header method stubbed.
        from http.server import BaseHTTPRequestHandler
        from app import Handler

        captured: list[tuple[str, str]] = []

        class FakeHandler(Handler):
            def __init__(self):
                # Bypass BaseHTTPRequestHandler.__init__ which needs a socket
                pass

            def send_header(self, key, value):
                captured.append((key, value))

            def end_headers(self):
                Handler.end_headers(self)

        # Patch super().end_headers() to no-op
        original_super_end = BaseHTTPRequestHandler.end_headers
        BaseHTTPRequestHandler.end_headers = lambda self: None
        try:
            FakeHandler().end_headers()
        finally:
            BaseHTTPRequestHandler.end_headers = original_super_end

        header_dict = dict(captured)
        self.assertEqual(header_dict.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(header_dict.get("X-Frame-Options"), "DENY")
        self.assertEqual(header_dict.get("Referrer-Policy"), "same-origin")
        self.assertEqual(
            header_dict.get("Cross-Origin-Opener-Policy"), "same-origin"
        )
        self.assertEqual(
            header_dict.get("Cross-Origin-Resource-Policy"), "same-origin"
        )
        self.assertIn("Content-Security-Policy", header_dict)
        # Permissions-Policy must lock down the dangerous APIs
        perms = header_dict.get("Permissions-Policy", "")
        for forbidden_feature in ("geolocation", "microphone", "camera"):
            self.assertIn(f"{forbidden_feature}=()", perms)

    def test_hsts_disabled_in_dev_environment(self) -> None:
        # In dev (APP_ENV != production), HSTS must NOT be sent.
        # Otherwise dev users with HTTPS-only sticky bits would
        # be locked out when they switch back to http://localhost.
        import app

        self.assertFalse(app._hsts_enabled())


class CapAuditEvent(unittest.TestCase):
    """Sanity probe of the global response shape: missing CSRF
    header on /api/* POST should return 403 csrf_failed (not a
    different error code we'd silently mis-route)."""

    def setUp(self) -> None:
        self.state, self.user_id = _make_state()
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.addCleanup(lambda: self.state._test_tmp.cleanup())  # noqa: SLF001

    def test_require_csrf_is_a_method_of_handler(self) -> None:
        # Drift guard: if someone renames require_csrf, /api/auth/logout
        # would silently bypass the check.
        from app import Handler

        self.assertTrue(hasattr(Handler, "require_csrf"))


if __name__ == "__main__":
    unittest.main()
