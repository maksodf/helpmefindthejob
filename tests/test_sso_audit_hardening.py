# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guards for two security-hardening fixes from the bug hunt:

- verify_chain returned ok=True for an empty / wiped / zero-record log (vacuous
  pass) — an auditor pointing it at a deleted log got a false green. It now
  returns ok=False with reason "no_records".
- find_or_create_sso_user auto-linked any IdP identity to an existing local
  account on a bare email match, ignoring whether the IdP verified the email — an
  account-takeover vector with a non-verifying OIDC provider. It now refuses to
  auto-link an existing account unless email_verified is true (new-account
  creation is unaffected; SAML asserts the email cryptographically).
"""

from __future__ import annotations

import os
import tempfile
import unittest

from company_discovery.audit_log import verify_chain
from company_discovery.auth import AuthStore


class VerifyChainEmptyTests(unittest.TestCase):
    def test_empty_log_list_does_not_vacuously_pass(self) -> None:
        result = verify_chain([], b"s" * 32)
        self.assertFalse(result.ok)
        self.assertEqual(result.first_break_reason, "no_records")

    def test_blank_only_file_does_not_vacuously_pass(self) -> None:
        from pathlib import Path

        p = Path(tempfile.mkdtemp()) / "ai_act_audit.log"
        p.write_text("\n\n   \n", encoding="utf-8")
        result = verify_chain([p], b"s" * 32)
        self.assertFalse(result.ok)


class SsoEmailVerifiedTests(unittest.TestCase):
    def _store(self) -> AuthStore:
        return AuthStore(os.path.join(tempfile.mkdtemp(), "a.db"), secret_key=b"x" * 32)

    def test_unverified_email_cannot_autolink_existing_account(self) -> None:
        store = self._store()
        store.create_user("victim@x.test", "VictimPass123456")
        with self.assertRaises(ValueError) as cm:
            store.find_or_create_sso_user(
                provider_id="evil-idp", subject="attacker",
                email="victim@x.test", email_verified=False,
            )
        self.assertEqual(str(cm.exception), "sso_email_unverified")
        # the victim's local login is untouched
        self.assertIsNotNone(store.authenticate("victim@x.test", "VictimPass123456"))

    def test_verified_email_links_existing_account(self) -> None:
        store = self._store()
        store.create_user("user@x.test", "UserPass12345678")
        linked = store.find_or_create_sso_user(
            provider_id="good-idp", subject="s", email="user@x.test", email_verified=True
        )
        self.assertEqual(linked.email, "user@x.test")

    def test_new_account_with_unverified_email_still_created(self) -> None:
        store = self._store()
        created = store.find_or_create_sso_user(
            provider_id="idp", subject="s2", email="brandnew@x.test", email_verified=False
        )
        self.assertEqual(created.email, "brandnew@x.test")


if __name__ == "__main__":
    unittest.main()
