# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Domain-transition timeline audit-trail contract
(phase2-backlog #35).

The project's public-tree domain went through three states:
``khalo.org`` (legacy commercial) → ``directjob-scout.example``
(Decision-12 placeholder) → ``helpmefindthejob.org`` (Decision-22
real acquisition). The Decision-22 narrative previously skipped
the two-step transition, making the git-history "rename then
rename again" pattern look like redundant churn instead of two
distinct decisions made for distinct reasons.

This test pins the timeline narrative in
``04-research-and-decisions.md`` Open R8 so a future agent can't
silently drop the explanation.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from pathlib import Path as _RPath

_REPO_ROOT = _RPath(__file__).resolve().parent.parent


RESEARCH_DOC = Path(str(_REPO_ROOT / "docs/grant/04-research-and-decisions.md"))


class DomainTransitionTimelinePresent(unittest.TestCase):
    def setUp(self):
        self.src = RESEARCH_DOC.read_text(encoding="utf-8")

    def test_timeline_marker_present(self):
        """The full-timeline section was added 2026-05-22 per #35."""

        self.assertIn(
            "Full domain-transition timeline (added 2026-05-22 per phase2-backlog #35)",
            self.src,
        )

    def test_all_three_domain_states_documented(self):
        """The three states (khalo / placeholder / real) must each
        appear in the timeline."""

        # Find the timeline section
        start = self.src.find("Full domain-transition timeline")
        self.assertGreater(start, 0)
        # The section extends to the next paragraph break (blank line
        # followed by non-table content)
        section = self.src[start : start + 3000]

        self.assertIn("khalo.org", section)
        self.assertIn("directjob-scout.example", section)
        self.assertIn("helpmefindthejob.org", section)

    def test_timeline_references_both_decisions(self):
        """The narrative must cite both Decision 12 (sanitisation
        placeholder) and Decision 22 (real-domain acquisition) so a
        reader can trace the rationale for each step."""

        start = self.src.find("Full domain-transition timeline")
        section = self.src[start : start + 3000]
        self.assertIn("Decision 12", section)
        self.assertIn("Decision 22", section)

    def test_timeline_explains_why_two_steps(self):
        """The "why this matters" paragraph distinguishes the two
        renames as decisions-for-distinct-reasons rather than
        redundant churn."""

        start = self.src.find("Full domain-transition timeline")
        section = self.src[start : start + 3000]
        # Either phrasing is acceptable as long as the narrative
        # makes the distinct-decisions case
        self.assertTrue(
            "redundant churn" in section.lower() or "two distinct decisions" in section,
            "timeline must distinguish the two renames as decisions "
            "for distinct reasons (not redundant churn)",
        )

    def test_decision_22_cross_links_to_timeline(self):
        """Decision 22's body should mention the two-step transition
        so a reader who lands there directly is pointed at the
        full timeline in R8."""

        # Find the Decision 22 section
        start = self.src.find("Decision 22: Project rename")
        end = self.src.find("### ", start + 10)  # next ### heading
        section = self.src[start:end]
        self.assertIn("two-step domain transition", section)
        # And references all 3 states
        self.assertIn("khalo.org", section)
        self.assertIn("directjob-scout.example", section)
        self.assertIn("helpmefindthejob.org", section)

    def test_timeline_clarifies_rfc_2606_basis(self):
        """The .example TLD choice in Decision 12 is grounded in
        RFC 2606. Pinning the reference so future readers see why
        the placeholder is .example (not .test / .invalid / a made-
        up TLD)."""

        start = self.src.find("Full domain-transition timeline")
        section = self.src[start : start + 3000]
        self.assertIn("RFC 2606", section)


if __name__ == "__main__":
    unittest.main()
