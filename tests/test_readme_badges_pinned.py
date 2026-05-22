# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guard for README CI badge URLs.

Backlog item #62 (phase2-backlog-2026-05-19.md): the README CI
badges previously hardcoded ``?branch=claude/project-analysis-
bpHCo`` (the working branch name). Once that branch merges to
main, the badges should reflect main's CI state — not a feature
branch that may no longer exist.

This test pins the invariant: every GitHub workflow badge in the
README must point at ``?branch=main`` (the canonical default
branch), and must NOT reference any ``claude/`` working-branch
name. If a future agent edits the README and drifts the URLs,
this fires.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


README = Path("/Users/fouad./Desktop/NasserMCPserver/README.md")


class ReadmeBadgeBranchPins(unittest.TestCase):
    def setUp(self):
        self.src = README.read_text(encoding="utf-8")

    def test_no_feature_branch_in_badge_urls(self):
        """No `claude/*` working-branch reference may appear in the
        README. Other places (commits, history) are fine; the README
        is the public face of the project."""

        self.assertNotIn(
            "branch=claude/",
            self.src,
            "README badge still references a working branch — "
            "should be branch=main for the canonical state",
        )

    def test_every_actions_workflow_badge_pinned_to_main(self):
        """For every GitHub Actions workflow badge in the README,
        verify it carries ``?branch=main`` (or is unbranched, which
        falls back to default branch). Catches the case where one
        badge was forgotten in a future edit."""

        # Match badge URLs of the form:
        #   github.com/<owner>/<repo>/actions/workflows/<file>/badge.svg?<query>
        pattern = re.compile(
            r"https://github\.com/[^/]+/[^/]+/actions/workflows/[^/]+/badge\.svg([^)\s]*)"
        )
        matches = pattern.findall(self.src)
        self.assertGreater(
            len(matches),
            0,
            "no GitHub Actions badges found in README — "
            "either the README structure changed or all badges "
            "were removed; this test needs review either way",
        )
        for query in matches:
            with self.subTest(query=query):
                if "branch=" in query:
                    self.assertIn(
                        "branch=main",
                        query,
                        f"badge query {query!r} pins to non-main branch",
                    )

    def test_no_other_hardcoded_branch_names_in_readme(self):
        """Defense in depth: catch any other working-branch
        reference patterns that aren't the badge URL specifically."""

        # Allow the literal in fenced code blocks that document
        # branch convention; only fail on actionable URLs.
        forbidden_patterns = [
            "branch=claude/project-analysis",
            "tree/claude/project-analysis",
            "blob/claude/project-analysis",
        ]
        for pat in forbidden_patterns:
            with self.subTest(pattern=pat):
                self.assertNotIn(
                    pat,
                    self.src,
                    f"README still references {pat!r} — should be replaced "
                    "with main/<file> form for the canonical state",
                )


if __name__ == "__main__":
    unittest.main()
