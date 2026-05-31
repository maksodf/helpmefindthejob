# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guards for auth-security bugs found in the bug hunt.

- Invitation acceptance for an EXISTING email used to silently force-reset that
  account's password/role/active (token-leak takeover). It now rejects with
  account_exists and never mutates the existing account.
- authenticate() returned immediately for a missing email (no password hashing),
  leaking account existence via response time. It now runs a decoy hash.
- consume_2fa_challenge crashed (db_schema_drift -> 500) on a fresh instance
  because pending_2fa was created lazily; it's now created eagerly.
- The per-IP login slot caps repeated unrefunded claims — the mechanism the
  2fa-verify metering fix relies on to bound TOTP brute-force.

(The HTTP-level fixes — 2fa-verify metering, the bootstrap-admin race, and the
malformed-cookie 500 — were proven end-to-end against a booted instance; this
file pins the in-process logic that underlies them.)
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import company_discovery.auth as authmod
from app import AppState


def _make_state() -> AppState:
    tmp = TemporaryDirectory()
    root = Path(tmp.name)
    state = AppState(
        root / "company.sqlite3",
        root / "auth.sqlite3",
        root / "ai.json",
        root / "schedule.json",
        start_scheduler=False,
    )
    state._test_tmp = tmp  # noqa: SLF001 - keep tempdir alive for the test
    return state


class InvitationOverwriteTests(unittest.TestCase):
    def test_invitation_for_existing_email_is_rejected_not_overwritten(self) -> None:
        state = _make_state()
        self.addCleanup(state.auth_store.close)
        state.auth_store.create_user("victim@x.test", "VictimPassword123")
        issued = state.token_store.issue(kind="invitation", email="victim@x.test", role="member")
        with self.assertRaises(ValueError) as cm:
            state.accept_invitation(raw_token=issued.raw_token, password="AttackerPassword123")
        self.assertEqual(str(cm.exception), "account_exists")
        # The victim's original credentials must be intact.
        self.assertIsNotNone(state.auth_store.authenticate("victim@x.test", "VictimPassword123"))
        self.assertIsNone(state.auth_store.authenticate("victim@x.test", "AttackerPassword123"))


class EnumerationTimingTests(unittest.TestCase):
    def test_missing_user_runs_decoy_hash(self) -> None:
        state = _make_state()
        self.addCleanup(state.auth_store.close)
        state.auth_store.create_user("real@x.test", "RealPassword12345")
        with patch.object(authmod, "hash_password", wraps=authmod.hash_password) as hp:
            self.assertIsNone(state.auth_store.authenticate("ghost@x.test", "whatever12345"))
            self.assertTrue(
                hp.called, "a decoy hash must run for a missing account (anti-enumeration)"
            )

    def test_wrong_password_still_rejected(self) -> None:
        state = _make_state()
        self.addCleanup(state.auth_store.close)
        state.auth_store.create_user("real@x.test", "RealPassword12345")
        self.assertIsNone(state.auth_store.authenticate("real@x.test", "WrongPassword12345"))
        self.assertIsNotNone(state.auth_store.authenticate("real@x.test", "RealPassword12345"))


class TwoFactorTableTests(unittest.TestCase):
    def test_consume_challenge_on_fresh_instance_returns_none(self) -> None:
        # pending_2fa is created eagerly; a 2fa-verify before any enrollment must
        # return None, not crash with a missing-table error.
        state = _make_state()
        self.addCleanup(state.auth_store.close)
        self.assertIsNone(state.auth_store.consume_2fa_challenge("bogus-token"))


class LoginSlotMeteringTests(unittest.TestCase):
    def test_unrefunded_claims_eventually_capped(self) -> None:
        state = _make_state()
        self.addCleanup(state.auth_store.close)
        results = [state.claim_login_slot("203.0.113.7") for _ in range(15)]
        self.assertIn(False, results, "the per-IP login slot must cap repeated unrefunded claims")


if __name__ == "__main__":
    unittest.main()
