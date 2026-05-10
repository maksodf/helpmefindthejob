"""Referral program (Phase 4 tracker item #46).

Each user gets a short URL-safe ``referral_code`` minted lazily on
first read. ``/r/<code>`` sets a cookie + redirects home; the
registration form forwards the code via ``referrerCode`` and
``record_referral`` validates it. Self-referrals, inactive referrers,
and unknown codes are silent no-ops so a bad URL never blocks
sign-up. ``count_referrals`` underpins the dashboard counter.

The reward grant (1 month Pro for both sides) is deferred until the
Pro plan exists (gated by tracker #21).
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.auth import AuthStore


class ReferralCodeMintingTests(unittest.TestCase):
    def _store(self) -> AuthStore:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = AuthStore(Path(tmp.name) / "auth.sqlite3", secret_key="x" * 64)
        self.addCleanup(store.close)
        return store

    def test_first_call_mints_idempotent(self) -> None:
        store = self._store()
        user = store.create_user("alice@example.com", "very-secret-pass-1234")
        code = store.ensure_referral_code(user.id)
        self.assertEqual(len(code), 10)
        self.assertEqual(store.ensure_referral_code(user.id), code)

    def test_lookup_returns_none_for_unknown(self) -> None:
        store = self._store()
        self.assertIsNone(store.find_user_by_referral_code("nonexistent"))
        self.assertIsNone(store.find_user_by_referral_code(""))

    def test_lookup_finds_minted_user(self) -> None:
        store = self._store()
        user = store.create_user("alice@example.com", "very-secret-pass-1234")
        code = store.ensure_referral_code(user.id)
        found = store.find_user_by_referral_code(code)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, user.id)


class RecordReferralTests(unittest.TestCase):
    def _store_with_referrer(self) -> tuple[AuthStore, str, str]:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = AuthStore(Path(tmp.name) / "auth.sqlite3", secret_key="x" * 64)
        self.addCleanup(store.close)
        referrer = store.create_user("referrer@example.com", "very-secret-pass-1234")
        code = store.ensure_referral_code(referrer.id)
        return store, referrer.id, code

    def test_valid_code_persists(self) -> None:
        store, referrer_id, code = self._store_with_referrer()
        new_user = store.create_user("alice@example.com", "very-secret-pass-1234")
        store.record_referral(new_user.id, code)
        row = store.connection.execute(
            "SELECT referred_by FROM users WHERE id = ?", (new_user.id,),
        ).fetchone()
        self.assertEqual(row[0], code)
        self.assertEqual(store.count_referrals(referrer_id), 1)

    def test_bad_code_is_no_op(self) -> None:
        store, _, _ = self._store_with_referrer()
        new_user = store.create_user("alice@example.com", "very-secret-pass-1234")
        store.record_referral(new_user.id, "totally-bogus-code")
        row = store.connection.execute(
            "SELECT referred_by FROM users WHERE id = ?", (new_user.id,),
        ).fetchone()
        self.assertIsNone(row[0])

    def test_self_referral_rejected(self) -> None:
        store, referrer_id, code = self._store_with_referrer()
        store.record_referral(referrer_id, code)
        row = store.connection.execute(
            "SELECT referred_by FROM users WHERE id = ?", (referrer_id,),
        ).fetchone()
        self.assertIsNone(row[0])

    def test_inactive_referrer_rejected(self) -> None:
        store, referrer_id, code = self._store_with_referrer()
        store.connection.execute(
            "UPDATE users SET active = 0 WHERE id = ?", (referrer_id,),
        )
        store.connection.commit()
        new_user = store.create_user("alice@example.com", "very-secret-pass-1234")
        store.record_referral(new_user.id, code)
        row = store.connection.execute(
            "SELECT referred_by FROM users WHERE id = ?", (new_user.id,),
        ).fetchone()
        self.assertIsNone(row[0])

    def test_count_referrals_excludes_inactive_referees(self) -> None:
        store, referrer_id, code = self._store_with_referrer()
        a = store.create_user("a@example.com", "very-secret-pass-1234")
        b = store.create_user("b@example.com", "very-secret-pass-1234")
        store.record_referral(a.id, code)
        store.record_referral(b.id, code)
        self.assertEqual(store.count_referrals(referrer_id), 2)
        store.connection.execute(
            "UPDATE users SET active = 0 WHERE id = ?", (a.id,),
        )
        store.connection.commit()
        self.assertEqual(store.count_referrals(referrer_id), 1)


if __name__ == "__main__":
    unittest.main()
