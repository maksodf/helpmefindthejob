# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 backlog #48 — Session-invalidation completeness contract.

Auth-sensitive state changes MUST invalidate all of the user's
active sessions. Without this, a compromised cookie keeps working
even after the victim takes defensive action (changing password,
enabling 2FA, demoting from admin, etc.).

Coverage:

1. Password change → all sessions invalidated (existing)
2. Account deactivation → all sessions invalidated (existing)
3. Role change → all sessions invalidated (NEW — was a gap; a
   demoted admin retained admin-scoped sessions until token
   expiry)
4. TOTP enrollment → all sessions invalidated (NEW — without
   this, a compromised cookie survives 2FA enrollment, defeating
   the user's defensive intent)
5. TOTP disable → all sessions invalidated (NEW — disabling 2FA
   is auth-sensitive; old cookies must re-auth)
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import AppState
from company_discovery.auth import AuthUser


def _make_state() -> tuple[AppState, AuthUser]:
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
    user = state.auth_store.create_user("sess@example.com", "secret-pass-12345678")
    return state, user


def _count_sessions_for(state: AppState, user_id: str) -> int:
    rows = state.auth_store.connection.execute(
        "SELECT COUNT(*) FROM sessions WHERE user_id = ?", (user_id,)
    ).fetchone()
    return int(rows[0]) if rows else 0


class SessionCookieHeaderSignature(unittest.TestCase):
    """Regression guard: the TOTP-confirm and TOTP-disable handlers
    call session_cookie_header(token, max_age). The 2-arg signature
    is enforced by Python — if anyone reduces it to 1 arg, this
    test fails immediately rather than at runtime on a real request."""

    def test_signature_takes_two_positional_args(self) -> None:
        from app import session_cookie_header

        # Must accept (token, max_age) — both positional, both required
        result = session_cookie_header("test-token-123", 3600)
        self.assertIn("test-token-123", result)
        self.assertIn("Max-Age=3600", result)
        self.assertIn("HttpOnly", result)
        self.assertIn("SameSite=Lax", result)

    def test_signature_rejects_missing_max_age(self) -> None:
        from app import session_cookie_header

        with self.assertRaises(TypeError):
            session_cookie_header("test-token-123")  # type: ignore[call-arg]


class SessionInvalidationContract(unittest.TestCase):
    def setUp(self) -> None:
        self.state, self.user = _make_state()
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.addCleanup(lambda: self.state._test_tmp.cleanup())  # noqa: SLF001
        # Create 3 distinct sessions for the user — simulating
        # laptop / phone / tablet logins.
        self.s1 = self.state.auth_store.create_session(self.user)
        self.s2 = self.state.auth_store.create_session(self.user)
        self.s3 = self.state.auth_store.create_session(self.user)
        self.assertEqual(_count_sessions_for(self.state, self.user.id), 3)

    def test_password_change_invalidates_all_sessions(self) -> None:
        self.state.auth_store.update_user(self.user.id, password="new-strong-password-12345")
        self.assertEqual(_count_sessions_for(self.state, self.user.id), 0)

    def test_account_deactivation_invalidates_all_sessions(self) -> None:
        self.state.auth_store.update_user(self.user.id, active=False)
        self.assertEqual(_count_sessions_for(self.state, self.user.id), 0)

    def test_role_change_invalidates_all_sessions(self) -> None:
        """Phase 2 #48 NEW: was a gap before this fix."""
        # Promote member → admin (state.create_user defaults to member)
        self.state.auth_store.update_user(self.user.id, role="admin")
        self.assertEqual(
            _count_sessions_for(self.state, self.user.id),
            0,
            "Role change must invalidate all sessions — a demoted admin "
            "must not retain admin-scoped powers via cached cookies",
        )

    def test_no_op_update_does_not_invalidate_sessions(self) -> None:
        """If we update with the SAME role + active state and no
        password, sessions must NOT be invalidated. This is the
        legitimate use case where an admin re-saves a user form
        without changing anything."""
        self.state.auth_store.update_user(self.user.id, role=self.user.role, active=True)
        self.assertEqual(
            _count_sessions_for(self.state, self.user.id),
            3,
            "No-op update must not invalidate sessions",
        )

    def test_totp_enrollment_invalidates_all_sessions(self) -> None:
        """Phase 2 #48 NEW: enabling 2FA must invalidate any
        existing session including the current one. Otherwise a
        compromised cookie keeps working even after the victim's
        defensive 2FA enrollment."""
        # Start enrollment to set totp_secret
        self.state.auth_store.start_totp_enrollment(self.user.id)
        # Confirm with a valid code — we need to compute one from
        # the secret. Use the existing _decrypt_secret + generate_totp.
        import sqlite3

        row = self.state.auth_store.connection.execute(
            "SELECT totp_secret FROM users WHERE id = ?", (self.user.id,)
        ).fetchone()
        secret = self.state.auth_store._decrypt_secret(row[0], self.user.id)
        from datetime import datetime, timezone

        from company_discovery.auth import _totp_at

        code = _totp_at(secret, when=datetime.now(timezone.utc))
        self.state.auth_store.confirm_totp_enrollment(self.user.id, code)
        self.assertEqual(
            _count_sessions_for(self.state, self.user.id),
            0,
            "TOTP enrollment must invalidate all sessions",
        )

    def test_totp_disable_invalidates_all_sessions(self) -> None:
        """Phase 2 #48 NEW: same logic for disable."""
        # First enroll
        self.state.auth_store.start_totp_enrollment(self.user.id)
        row = self.state.auth_store.connection.execute(
            "SELECT totp_secret FROM users WHERE id = ?", (self.user.id,)
        ).fetchone()
        secret = self.state.auth_store._decrypt_secret(row[0], self.user.id)
        from datetime import datetime, timezone

        from company_discovery.auth import _totp_at

        code = _totp_at(secret, when=datetime.now(timezone.utc))
        self.state.auth_store.confirm_totp_enrollment(self.user.id, code)
        # Re-create 3 sessions (enroll wiped them)
        self.state.auth_store.create_session(self.user)
        self.state.auth_store.create_session(self.user)
        self.state.auth_store.create_session(self.user)
        self.assertEqual(_count_sessions_for(self.state, self.user.id), 3)
        # Now disable
        self.state.auth_store.disable_totp(self.user.id, "secret-pass-12345678")
        self.assertEqual(
            _count_sessions_for(self.state, self.user.id),
            0,
            "TOTP disable must invalidate all sessions",
        )

    def test_cross_user_sessions_unaffected(self) -> None:
        """Invalidating user A's sessions must not touch user B's."""
        other = self.state.auth_store.create_user("other-sess@example.com", "secret-pass-12345678")
        s_other = self.state.auth_store.create_session(other)
        self.assertEqual(_count_sessions_for(self.state, other.id), 1)
        # Demote/promote user A
        self.state.auth_store.update_user(self.user.id, role="admin")
        self.assertEqual(
            _count_sessions_for(self.state, other.id),
            1,
            "Other users' sessions must not be affected",
        )


if __name__ == "__main__":
    unittest.main()
