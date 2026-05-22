# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Contract tests for the v0.1.0 release-doc "Since v0.1.0"
addendum (phase2-backlog #33).

Closes phase2-backlog item #33: "docs/releases/v0.1.0.md
'What's not yet shipped' list — items have shipped since
2026-05-18. Either freeze the file as a historical snapshot
with a clear 'as of v0.1.0 release date' note, or add a
'since v0.1.0' addendum mirroring CHANGELOG [Unreleased]."

This contract pins the structure of the addendum so a future
agent extending it preserves the snapshot + addendum split.
"""

from __future__ import annotations

import unittest
from pathlib import Path


RELEASE_DOC = Path(
    "/Users/fouad./Desktop/NasserMCPserver/docs/releases/v0.1.0.md"
)


class ReleaseDocAddendumStructure(unittest.TestCase):
    def setUp(self):
        self.src = RELEASE_DOC.read_text(encoding="utf-8")

    def test_snapshot_disclosure_present(self):
        """The snapshot section must carry the 'as of 2026-05-18'
        disclosure so readers don't mistake it for current state."""

        self.assertIn("as of 2026-05-18", self.src)
        self.assertIn("Snapshot disclosure", self.src)

    def test_addendum_section_present(self):
        self.assertIn("Since v0.1.0 — running addendum", self.src)

    def test_addendum_references_changelog(self):
        """The addendum must point to CHANGELOG.md as the canonical
        drill-down so readers know where to get commit hashes."""

        self.assertIn("CHANGELOG.md", self.src)
        # And clearly says CHANGELOG is canonical
        self.assertIn("canonical", self.src.lower())

    def test_addendum_dated(self):
        """The addendum has a dated entry so future appends can be
        ordered chronologically."""

        self.assertIn("between v0.1.0 and 2026-05-22", self.src)


class ReleaseDocAddendumCoversShippedWork(unittest.TestCase):
    """The addendum should mention the major post-v0.1.0 slices.
    Catches the case where someone appends a new slice but forgets
    to update the addendum."""

    def setUp(self):
        self.src = RELEASE_DOC.read_text(encoding="utf-8")

    def test_mentions_13_plan(self):
        self.assertIn("13-plan", self.src)

    def test_mentions_postgresql_backend(self):
        self.assertIn("PostgreSQL", self.src)

    def test_mentions_sso(self):
        self.assertIn("SSO", self.src)

    def test_mentions_ssr_for_seo(self):
        self.assertIn("SSR for SEO", self.src)

    def test_mentions_mcp_external_surface(self):
        self.assertIn("/mcp/version", self.src)

    def test_mentions_housing_stub(self):
        self.assertIn("housing-stub-client", self.src)

    def test_mentions_cost_saving_wiring(self):
        self.assertIn("8 mechanism", self.src)

    def test_mentions_language_requirement_detector(self):
        self.assertIn("Language-requirement detector", self.src)

    def test_mentions_visa_status_flags(self):
        self.assertIn("Visa-status flag detector", self.src)

    def test_mentions_hypothesis_property_tests(self):
        self.assertIn("Hypothesis property-based", self.src)


class ReleaseDocAddendumDocumentsRemainingOpenItems(unittest.TestCase):
    """The 'still deferred' section keeps the picture honest by
    naming what's STILL not shipped post-v0.1.0."""

    def setUp(self):
        self.src = RELEASE_DOC.read_text(encoding="utf-8")

    def test_mentions_still_deferred(self):
        self.assertIn("Still deferred", self.src)

    def test_lists_public_demo_deployment(self):
        self.assertIn("Public demo deployment", self.src)

    def test_lists_multi_os_ci(self):
        self.assertIn("Multi-OS CI matrix", self.src)

    def test_lists_partner_ngo_pilot(self):
        self.assertIn("partner-NGO pilot", self.src)

    def test_lists_translations_beyond_en_de(self):
        self.assertIn("Translations beyond EN + DE", self.src)


if __name__ == "__main__":
    unittest.main()
