# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Phase 9a — 2FA (TOTP) for accounts."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.auth import AuthStore, _totp_at, verify_totp

SECRET = "X" * 64  # >= 32 chars per AuthStore guard


class TotpPrimitivesTests(unittest.TestCase):
    def test_verify_totp_accepts_current_window(self) -> None:
        secret = "JBSWY3DPEHPK3PXP"  # canonical RFC 6238 sample
        when = datetime.now(timezone.utc)
        code = _totp_at(secret, when=when)
        self.assertTrue(verify_totp(secret, code, when=when))

    def test_verify_totp_rejects_wrong_code(self) -> None:
        self.assertFalse(verify_totp("JBSWY3DPEHPK3PXP", "000000"))

    def test_verify_totp_handles_drift_one_window(self) -> None:
        secret = "JBSWY3DPEHPK3PXP"
        now = datetime.now(timezone.utc)
        prev = now - timedelta(seconds=30)
        code_prev = _totp_at(secret, when=prev)
        # Generated 30s ago, verified now: should still pass with drift=1.
        self.assertTrue(verify_totp(secret, code_prev, when=now))


class AuthStoreTotpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.store = AuthStore(Path(self.tmp.name) / "auth.sqlite3", secret_key=SECRET)
        self.user = self.store.create_user("alice@example.test", "supersecret-12345")

    def tearDown(self) -> None:
        self.store.close()
        self.tmp.cleanup()

    def test_enroll_then_confirm_returns_recovery_codes(self) -> None:
        enrollment = self.store.start_totp_enrollment(self.user.id)
        self.assertIn("secret", enrollment)
        self.assertTrue(enrollment["otpauthUrl"].startswith("otpauth://"))
        # Compute a valid code and confirm.
        code = _totp_at(enrollment["secret"], when=datetime.now(timezone.utc))
        recovery = self.store.confirm_totp_enrollment(self.user.id, code)
        self.assertEqual(len(recovery), 8)
        self.assertTrue(self.store.has_totp_enabled(self.user.id))

    def test_confirm_rejects_wrong_code(self) -> None:
        self.store.start_totp_enrollment(self.user.id)
        with self.assertRaises(ValueError):
            self.store.confirm_totp_enrollment(self.user.id, "000000")
        self.assertFalse(self.store.has_totp_enabled(self.user.id))

    def test_recovery_code_consumed_once(self) -> None:
        enrollment = self.store.start_totp_enrollment(self.user.id)
        code = _totp_at(enrollment["secret"], when=datetime.now(timezone.utc))
        recovery = self.store.confirm_totp_enrollment(self.user.id, code)
        first = recovery[0]
        self.assertTrue(self.store.consume_recovery_code(self.user.id, first))
        # Second use: rejected.
        self.assertFalse(self.store.consume_recovery_code(self.user.id, first))

    def test_disable_requires_password(self) -> None:
        enrollment = self.store.start_totp_enrollment(self.user.id)
        code = _totp_at(enrollment["secret"], when=datetime.now(timezone.utc))
        self.store.confirm_totp_enrollment(self.user.id, code)
        with self.assertRaises(ValueError):
            self.store.disable_totp(self.user.id, "wrong-password")
        self.store.disable_totp(self.user.id, "supersecret-12345")
        self.assertFalse(self.store.has_totp_enabled(self.user.id))

    def test_2fa_challenge_consumed_once(self) -> None:
        token = self.store.issue_2fa_challenge(self.user.id)
        self.assertEqual(self.store.consume_2fa_challenge(token), self.user.id)
        # Second consume: gone.
        self.assertIsNone(self.store.consume_2fa_challenge(token))

    def test_2fa_challenge_expires(self) -> None:
        # ttl=0 means the row is born expired.
        token = self.store.issue_2fa_challenge(self.user.id, ttl_seconds=0)
        self.assertIsNone(self.store.consume_2fa_challenge(token))


if __name__ == "__main__":
    unittest.main()
