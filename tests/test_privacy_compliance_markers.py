# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guard: Privacy page must substantively name the AI Act
articles + GDPR articles it claims compliance with.

AUDIT-5 (2026-05-22): the landing-page hero advertises "Article 12
audit log, Article 20 portable export, transparency notice — ready
for 2 August 2026 enforcement" but the Privacy page had ZERO
mentions of any AI Act or GDPR article. A NLnet / Commons
Conservancy reviewer cross-checking the marketing copy against the
legal documentation would catch the unsubstantiated claim and fail
the application.

The test asserts that every article promised in marketing copy is
named on the Privacy page, plus that the standard GDPR rights are
all enumerated by article number, plus that the German supervisory
authority is named (the operator is in Berlin → BlnBDI).

If a future PR removes any of these, the test fails — the marketing
claim cannot drift away from the legal substantiation.
"""

from __future__ import annotations

import unittest
from pathlib import Path

PRIVACY_PATH = Path(__file__).resolve().parent.parent / "static" / "privacy.html"


REQUIRED_AI_ACT_MARKERS = (
    "AI Act",
    "2024/1689",
    "2 August 2026",
    "Article 12",
    "Article 13",
    "Article 14",
    "Article 20",
    "Article 26",
    "Article 50",
    "HMAC chain",
    "audit log",
)

REQUIRED_GDPR_MARKERS = (
    "GDPR",
    "Article 15",
    "Article 16",
    "Article 17",
    "Article 18",
    "Article 20",
    "Article 21",
    "Article 22",
    "Article 77",
    "Article 37",
)

REQUIRED_OPERATOR_MARKERS = (
    "Berliner Beauftragte für Datenschutz und Informationsfreiheit",
    "BlnBDI",
    "datenschutz-berlin",
    "Data Protection Officer",
    "Impressum",
    "compliance/audit-log-schema",
    "compliance/human-oversight-guide",
    "compliance/deployer-operating-manual",
)


class PrivacyPageHasAiActSubstantiation(unittest.TestCase):
    """Every AI Act claim made anywhere on the public site must be
    named on the Privacy page with enough context that a reviewer
    can verify the substrate."""

    def setUp(self):
        self.src = PRIVACY_PATH.read_text(encoding="utf-8")

    def test_required_ai_act_markers_present(self) -> None:
        missing = [m for m in REQUIRED_AI_ACT_MARKERS if m not in self.src]
        self.assertEqual(
            missing,
            [],
            f"Privacy page missing AI Act markers: {missing!r}",
        )

    def test_required_gdpr_markers_present(self) -> None:
        missing = [m for m in REQUIRED_GDPR_MARKERS if m not in self.src]
        self.assertEqual(
            missing,
            [],
            f"Privacy page missing GDPR markers: {missing!r}",
        )

    def test_required_operator_markers_present(self) -> None:
        missing = [m for m in REQUIRED_OPERATOR_MARKERS if m not in self.src]
        self.assertEqual(
            missing,
            [],
            f"Privacy page missing operator markers: {missing!r}",
        )


if __name__ == "__main__":
    unittest.main()
