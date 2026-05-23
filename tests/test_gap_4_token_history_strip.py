# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""GAP-4 (post-self-audit, 2026-05-23): SPA strips one-time-use tokens
from window.location after consuming them.

Pre-fix: ``initAcceptInvite()`` and ``initResetPassword()`` read the
``?token=<token>`` query parameter and stored it in form.dataset, but
left the URL untouched. The token then sat in browser history, in any
screen-share recording, and got included in the Referer header of
every subresource loaded by the page.

This problem was made worse by AUDIT-27 introducing a second
URL form (``/reset-password/<token>``) that 303-redirected to the
canonical ``?token=<token>``: the token now appeared in BOTH history
entries.

Post-fix: both ``init*`` functions call
``history.replaceState({}, "", window.location.pathname)``
*before* the API call, so the token never sits in window.location.
``form.dataset.token`` keeps the value for the subsequent
form-submission API call. replaceState (not pushState) so the user
can't navigate back to the token-carrying URL.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TokenStrippedFromUrlAfterConsumption(unittest.TestCase):
    """Source-level invariants. The SPA runs in a browser; we don't
    spin one up here, but we assert the source carries the right
    instructions."""

    def setUp(self) -> None:
        self.src = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

    def _extract_function(self, name: str) -> str:
        match = re.search(
            rf'(async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{',
            self.src,
        )
        self.assertIsNotNone(match, f"function {name} not found in app.js")
        # Track brace depth from the opening brace to find the matching close
        start = match.end() - 1  # position of opening {
        depth = 0
        for i in range(start, len(self.src)):
            ch = self.src[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return self.src[start:i + 1]
        raise AssertionError(f"unbalanced braces extracting {name}")

    def test_init_reset_password_strips_token_from_url(self) -> None:
        body = self._extract_function("initResetPassword")
        self.assertIn(
            "history.replaceState", body,
            "GAP-4 regression: initResetPassword() must call "
            "history.replaceState to remove ?token=X from window.location "
            "after capturing the token. Otherwise the secret persists in "
            "browser history / screen-share recordings / Referer headers.",
        )
        # Must use replaceState (not pushState) so back-button doesn't
        # bring the token-carrying URL back
        self.assertNotIn(
            "history.pushState", body,
            "GAP-4: use replaceState (not pushState) — pushState leaves "
            "the token-carrying URL one back-button click away.",
        )

    def test_init_accept_invite_strips_token_from_url(self) -> None:
        body = self._extract_function("initAcceptInvite")
        self.assertIn(
            "history.replaceState", body,
            "GAP-4 regression: initAcceptInvite() must call "
            "history.replaceState to remove ?token=X from window.location.",
        )
        self.assertNotIn("history.pushState", body)

    def test_replace_state_runs_before_api_call(self) -> None:
        # If the API call runs first and a subresource fetch fires
        # before replaceState completes, the token leaks in Referer.
        # Assert: replaceState appears BEFORE the api(...) call inside
        # each function body.
        for name in ("initResetPassword", "initAcceptInvite"):
            with self.subTest(function=name):
                body = self._extract_function(name)
                replace_pos = body.find("history.replaceState")
                api_pos = body.find("api(")
                self.assertGreater(replace_pos, 0, f"no replaceState in {name}")
                self.assertGreater(api_pos, 0, f"no api( call in {name}")
                self.assertLess(
                    replace_pos, api_pos,
                    f"GAP-4: in {name}, history.replaceState must run BEFORE "
                    f"the api(...) call so the token is scrubbed from the URL "
                    "before any network activity could carry it in Referer.",
                )

    def test_token_still_captured_in_form_dataset(self) -> None:
        # The token must still be captured locally — form.dataset.token —
        # otherwise the subsequent form submission has nothing to send.
        for name in ("initResetPassword", "initAcceptInvite"):
            with self.subTest(function=name):
                body = self._extract_function(name)
                self.assertIn(
                    "form.dataset.token = token", body,
                    f"GAP-4: {name} must still capture the token into "
                    "form.dataset.token; we only want to scrub it from the "
                    "URL, not lose it entirely.",
                )


if __name__ == "__main__":
    unittest.main()
