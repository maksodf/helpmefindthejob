# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""UX-R11 (2026-05-23, task #118): the Bookmarklet card must NOT
live under the "Notifications" settings tab — it's an import flow,
not a notification. It now lives under "Workspace" alongside
Workspace backup / Exports / Subscription.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BookmarkletTabPlacement(unittest.TestCase):
    def setUp(self) -> None:
        self.index_html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")

    def test_bookmarklet_card_exists(self) -> None:
        self.assertIn(
            'aria-label="Bookmarklet"',
            self.index_html,
            "Bookmarklet card disappeared from the SPA shell.",
        )

    def test_bookmarklet_card_not_under_notifications_tab(self) -> None:
        """The Bookmarklet card must not carry data-tab='notifications'.
        It's an import-flow feature, not a notifications one."""

        rx = re.compile(
            r'<section class="card" aria-label="Bookmarklet"[^>]*data-tab="notifications"'
        )
        self.assertIsNone(
            rx.search(self.index_html),
            "UX-R11 regression: Bookmarklet card is back under "
            "data-tab='notifications'. It's an import/onboarding "
            "feature, not a notification — keep it under workspace.",
        )

    def test_bookmarklet_card_under_workspace_tab(self) -> None:
        rx = re.compile(r'<section class="card" aria-label="Bookmarklet"[^>]*data-tab="workspace"')
        self.assertIsNotNone(
            rx.search(self.index_html),
            "Bookmarklet card must carry data-tab='workspace'. "
            "Per UX-R11 it moved out of Notifications and into "
            "Workspace alongside Backup / Exports / Subscription.",
        )


if __name__ == "__main__":
    unittest.main()
