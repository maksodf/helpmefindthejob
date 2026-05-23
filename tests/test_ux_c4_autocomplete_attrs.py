# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""UX-C4 (2026-05-23, task #77): every auth-relevant input must
carry the correct `autocomplete` attribute. This is the contract
password managers rely on; without it Bitwarden / 1Password /
LastPass / browser-builtin managers don't fill the fields cleanly.

The original audit flagged this as P0 thinking the attrs were
missing. Audit was actually wrong — the attrs were already there.
This file locks them in so future refactors can't accidentally
drop them.

Also adds autocomplete="off" to the admin "send test email" input
(the one gap we did find — admin actions shouldn't autofill with
the operator's own credentials).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AutocompleteContract(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.index_html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")

    # ( input id, required autocomplete value )
    AUTH_INPUTS = [
        # Login form
        ("loginEmail", "email"),
        ("loginPassword", "current-password"),
        # Register form
        ("registerEmail", "email"),
        ("registerPassword", "new-password"),
        # Forgot password
        ("forgotEmail", "email"),
        # Reset password (path-token flow)
        ("resetPasswordValue", "new-password"),
        # Accept invite (path-token flow)
        ("acceptInvitePassword", "new-password"),
        # Change password in settings
        ("currentPassword", "current-password"),
        ("newPassword", "new-password"),
        # Settings "support contact email" — operator email, fine to autofill
        ("supportContactEmail", "email"),
    ]

    # Inputs that should explicitly opt OUT of autocomplete because
    # the value belongs to someone else (admin actions) or is a
    # session secret that should never be remembered.
    OFF_INPUTS = [
        # Admin adding/inviting another user
        ("newUserEmail", "off"),
        ("inviteEmail", "off"),
        # Admin "send test email to X"
        ("testEmailTarget", "off"),
        # Brief-view inline "session API key"
        ("providerRuntimeKey", "off"),
        # BYO-AI persistent key in settings
        ("aiByokKey", "off"),
        # Slack webhook URL
        ("slackWebhookUrl", "off"),
        # Command palette search input
        ("cmdkInput", "off"),
        # Chat dock input
        ("dockChatInput", "off"),
    ]

    def _expect_autocomplete(self, input_id: str, value: str) -> None:
        rx = re.compile(
            rf'<input[^>]*id="{re.escape(input_id)}"[^>]*\bautocomplete="([^"]*)"'
        )
        m = rx.search(self.index_html)
        self.assertIsNotNone(
            m,
            f"UX-C4 regression: <input id='{input_id}'> is missing the "
            f"autocomplete attribute entirely. Set autocomplete='{value}'.",
        )
        self.assertEqual(
            m.group(1), value,
            f"UX-C4: <input id='{input_id}'> autocomplete is "
            f"{m.group(1)!r}, expected {value!r}.",
        )

    def test_auth_inputs_have_correct_autocomplete(self) -> None:
        for input_id, value in self.AUTH_INPUTS:
            with self.subTest(input_id=input_id):
                self._expect_autocomplete(input_id, value)

    def test_admin_and_secret_inputs_opt_out_of_autocomplete(self) -> None:
        for input_id, value in self.OFF_INPUTS:
            with self.subTest(input_id=input_id):
                self._expect_autocomplete(input_id, value)


if __name__ == "__main__":
    unittest.main()
