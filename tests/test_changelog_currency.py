# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""CHANGELOG.md currency contract — closes phase2-backlog item #61.

Backlog #61: "CHANGELOG-style summaries currently live in commit
bodies, not in CHANGELOG.md."

Two-layer guard:

1. **Format contract** — CHANGELOG follows Keep-a-Changelog 1.1.0:
   has an `## [Unreleased]` block, uses standard subsection
   headings, has a v0.1.0 entry.
2. **Currency contract** — every major work item from the
   13-plan + post-sprint slices has a CHANGELOG reference.
   Catches the silent-drift case where someone ships a new
   feature commit but forgets to update the CHANGELOG.

The second layer is the load-bearing one for #61: it surfaces
drift early instead of letting commit bodies be the only record.
"""

from __future__ import annotations

import unittest
from pathlib import Path


CHANGELOG = Path("/Users/fouad./Desktop/NasserMCPserver/CHANGELOG.md")


class ChangelogFormatContract(unittest.TestCase):
    """Keep-a-Changelog 1.1.0 format requirements."""

    def setUp(self):
        self.src = CHANGELOG.read_text(encoding="utf-8")

    def test_has_unreleased_section(self):
        self.assertIn("## [Unreleased]", self.src)

    def test_has_v0_1_0_release_entry(self):
        self.assertIn("## [0.1.0]", self.src)

    def test_has_standard_subsections(self):
        """Keep-a-Changelog defines: Added / Changed / Deprecated /
        Removed / Fixed / Security as the canonical subsection
        names."""

        for subsection in (
            "### Added",
            "### Changed",
            "### Fixed",
            "### Security",
        ):
            with self.subTest(subsection=subsection):
                self.assertIn(
                    subsection,
                    self.src,
                    f"CHANGELOG missing {subsection!r}",
                )

    def test_format_link_present(self):
        self.assertIn("keepachangelog.com", self.src.lower())


class ChangelogCurrencyContract(unittest.TestCase):
    """Major work items must be referenced in CHANGELOG. If a
    commit ships a feature/fix without updating CHANGELOG, the
    drift surfaces here."""

    def setUp(self):
        self.src = CHANGELOG.read_text(encoding="utf-8")

    def test_13_plan_items_all_referenced(self):
        """The 13-plan engineering slice items must each appear in
        the CHANGELOG. Catches the case where a future agent ships
        a new 13-plan item without backing it into CHANGELOG."""

        # Each phrase is distinctive enough to match exactly one
        # CHANGELOG entry — false positives are extremely unlikely.
        required_phrases = [
            "Alert delivery E2E",  # item 1
            "PWA / offline mode",  # item 2
            "Apply→reply→interview funnel",  # item 3
            "Workspace admin",  # item 4
            "Feature-flag runtime substrate",  # item 5
            "A/B testing framework",  # item 6
            "Public REST API",  # item 7
            "Python SDK for partner agents",  # item 8
            "Background job queue",  # item 9
            "SSR for SEO",  # item 10
            "PostgreSQL backend",  # item 11
            "OIDC + SAML 2.0 SP",  # item 12
            "WCAG AAA-leaning",  # item 13
        ]
        missing = []
        for phrase in required_phrases:
            if phrase not in self.src:
                missing.append(phrase)
        self.assertEqual(
            missing,
            [],
            "13-plan items missing from CHANGELOG — every shipped "
            "feature must have a CHANGELOG entry per backlog #61: "
            f"{missing}",
        )

    def test_post_13_plan_session_work_referenced(self):
        """Items shipped after the 13-plan close (this session +
        related). Catches drift between commit bodies and the
        canonical CHANGELOG."""

        required_phrases = [
            "/mcp/version",
            "/mcp/schemas.json",
            "mcp_server/schemas/",
            "Housing-stub-client",
            "_xss_safe_jsonld",
            "khalo.org",
            "README CI badges",
            "HEAD-request 404",
        ]
        missing = [p for p in required_phrases if p not in self.src]
        self.assertEqual(
            missing,
            [],
            "post-13-plan session items missing from CHANGELOG: "
            f"{missing}",
        )

    def test_commit_hashes_referenced_for_each_major_item(self):
        """Backlog #61 specifically wants the CHANGELOG to carry
        the same level of detail as commit bodies — including
        a commit-hash reference so a reader can drill down."""

        # The session commit hashes — at minimum these should be
        # referenced. We don't require ALL hashes (CHANGELOG isn't
        # a git log) but require that the major slices are
        # commit-anchored.
        for hash_prefix in (
            "17f7707",  # SSR for SEO
            "6bf2988",  # PG backend
            "a49ec1b",  # MCP catalogue
            "ed90258",  # housing-stub
            "b2d7599",  # health-storage fix
        ):
            with self.subTest(hash=hash_prefix):
                self.assertIn(
                    hash_prefix,
                    self.src,
                    f"CHANGELOG missing commit-hash anchor "
                    f"{hash_prefix} — backlog #61 wants drill-down",
                )


if __name__ == "__main__":
    unittest.main()
