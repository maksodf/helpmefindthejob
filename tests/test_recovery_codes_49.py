# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 backlog #49 — 2FA recovery codes contract tests.

Existing #49 surfaces (from test_phase9_2fa.py):
- Enrollment generates 8 codes
- Codes are one-time use

This file pins the NEW surfaces added 2026-05-21:
- regenerate_recovery_codes(password) re-issues 8 fresh codes
  and invalidates the old ones
- count_remaining_recovery_codes(user_id) reports the live
  remaining count without exposing the codes
- make_user_payload surfaces the remaining count so the UI can
  warn the user before they run out
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState
from company_discovery.auth import _totp_at


class RecoveryCodeRegeneration(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        root = Path(self.tmp.name)
        self.state = AppState(
            root / "company.sqlite3",
            root / "auth.sqlite3",
            root / "ai.json",
            root / "schedule.json",
            start_scheduler=False,
        )
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.addCleanup(self.tmp.cleanup)
        self.user = self.state.auth_store.create_user(
            "alice-49@example.com", "strong-pass-12345"
        )

    def _enroll_totp(self) -> None:
        enrollment = self.state.auth_store.start_totp_enrollment(self.user.id)
        code = _totp_at(enrollment["secret"], when=datetime.now(timezone.utc))
        self.state.auth_store.confirm_totp_enrollment(self.user.id, code)

    def test_regenerate_returns_8_fresh_codes(self) -> None:
        self._enroll_totp()
        codes = self.state.auth_store.regenerate_recovery_codes(
            self.user.id, "strong-pass-12345"
        )
        self.assertEqual(len(codes), 8)
        # All codes are unique
        self.assertEqual(len(set(codes)), 8)
        # Codes look like 10-hex-char strings
        for c in codes:
            self.assertEqual(len(c), 10)
            int(c, 16)  # must parse as hex

    def test_regenerate_invalidates_old_codes(self) -> None:
        self._enroll_totp()
        first_batch = self.state.auth_store.regenerate_recovery_codes(
            self.user.id, "strong-pass-12345"
        )
        # Regenerate again — the first batch must no longer work
        self.state.auth_store.regenerate_recovery_codes(
            self.user.id, "strong-pass-12345"
        )
        self.assertFalse(
            self.state.auth_store.consume_recovery_code(
                self.user.id, first_batch[0]
            )
        )

    def test_regenerate_rejects_wrong_password(self) -> None:
        self._enroll_totp()
        with self.assertRaises(ValueError):
            self.state.auth_store.regenerate_recovery_codes(
                self.user.id, "wrong-password"
            )

    def test_regenerate_rejects_when_totp_not_enrolled(self) -> None:
        with self.assertRaises(ValueError) as cm:
            self.state.auth_store.regenerate_recovery_codes(
                self.user.id, "strong-pass-12345"
            )
        self.assertIn("totp_not_enabled", str(cm.exception))


class RemainingCodeCount(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        root = Path(self.tmp.name)
        self.state = AppState(
            root / "company.sqlite3",
            root / "auth.sqlite3",
            root / "ai.json",
            root / "schedule.json",
            start_scheduler=False,
        )
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.addCleanup(self.tmp.cleanup)
        self.user = self.state.auth_store.create_user(
            "alice-49b@example.com", "strong-pass-12345"
        )

    def test_count_zero_before_totp_enrollment(self) -> None:
        self.assertEqual(
            self.state.auth_store.count_remaining_recovery_codes(self.user.id), 0
        )

    def test_count_eight_after_enrollment(self) -> None:
        enrollment = self.state.auth_store.start_totp_enrollment(self.user.id)
        code = _totp_at(enrollment["secret"], when=datetime.now(timezone.utc))
        self.state.auth_store.confirm_totp_enrollment(self.user.id, code)
        self.assertEqual(
            self.state.auth_store.count_remaining_recovery_codes(self.user.id), 8
        )

    def test_count_decreases_as_codes_are_consumed(self) -> None:
        enrollment = self.state.auth_store.start_totp_enrollment(self.user.id)
        code = _totp_at(enrollment["secret"], when=datetime.now(timezone.utc))
        codes = self.state.auth_store.confirm_totp_enrollment(self.user.id, code)
        # Use 3 codes
        for c in codes[:3]:
            self.assertTrue(
                self.state.auth_store.consume_recovery_code(self.user.id, c)
            )
        self.assertEqual(
            self.state.auth_store.count_remaining_recovery_codes(self.user.id), 5
        )

    def test_user_payload_surfaces_remaining_count(self) -> None:
        enrollment = self.state.auth_store.start_totp_enrollment(self.user.id)
        code = _totp_at(enrollment["secret"], when=datetime.now(timezone.utc))
        codes = self.state.auth_store.confirm_totp_enrollment(self.user.id, code)
        # Consume 2 codes
        for c in codes[:2]:
            self.state.auth_store.consume_recovery_code(self.user.id, c)
        # make_user_payload reads the global app.STATE, so we
        # monkey-patch it to point at this test's AppState for the
        # duration of the payload call.
        import app
        from app import make_user_payload

        original_state = app.STATE
        app.STATE = self.state
        try:
            payload = make_user_payload(self.user, "csrf-token-123")
        finally:
            app.STATE = original_state
        self.assertEqual(payload["recoveryCodesRemaining"], 6)
        self.assertTrue(payload["totpEnabled"])

    def test_user_payload_recovery_count_zero_when_no_totp(self) -> None:
        import app
        from app import make_user_payload

        original_state = app.STATE
        app.STATE = self.state
        try:
            payload = make_user_payload(self.user, "csrf-token-123")
        finally:
            app.STATE = original_state
        self.assertEqual(payload["recoveryCodesRemaining"], 0)
        self.assertFalse(payload["totpEnabled"])


if __name__ == "__main__":
    unittest.main()
