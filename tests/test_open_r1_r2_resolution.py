# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Open R1 + R2 resolution audit trail (phase2-backlog #36).

The two Open R-questions critical to the NLnet submission window
were verified live on 2026-05-22 via WebFetch against the NLnet
site. This contract test pins the audit-trail entries in
``04-research-and-decisions.md`` so a future agent can't silently
remove them.

Why a test: the R1 deadline + R2 differentiation answer both feed
directly into the application draft + submission scheduling.
Losing the audit trail would force a re-verification under
deadline pressure.
"""

from __future__ import annotations

import unittest
from pathlib import Path


RESEARCH_DOC = Path(
    "/Users/fouad./Desktop/NasserMCPserver/docs/grant/04-research-and-decisions.md"
)


class R1DeadlineAuditTrail(unittest.TestCase):
    def setUp(self):
        self.src = RESEARCH_DOC.read_text(encoding="utf-8")

    def test_r1_marked_answered_2026_05_22(self):
        self.assertIn("Open R1:", self.src)
        # Find the R1 section
        start = self.src.find("Open R1:")
        # Find the next R-question heading or end
        next_r = self.src.find("Open R2:", start)
        section = self.src[start:next_r]
        self.assertIn("ANSWERED", section)
        self.assertIn("2026-05-22", section)

    def test_r1_records_exact_deadline_with_time(self):
        start = self.src.find("Open R1:")
        next_r = self.src.find("Open R2:", start)
        section = self.src[start:next_r]
        # Exact phrasing from the NLnet call page
        self.assertIn("1 June 2026", section)
        self.assertIn("noon CEST", section)

    def test_r1_records_source_url(self):
        start = self.src.find("Open R1:")
        next_r = self.src.find("Open R2:", start)
        section = self.src[start:next_r]
        # Source URL must be present for traceability
        self.assertIn("nlnet.nl/news/2026/20260401-call.html", section)

    def test_r1_documents_schedule_paths(self):
        """Maintainer needs to know the trade-off (submit by 1 June
        vs wait for call 14)."""

        start = self.src.find("Open R1:")
        next_r = self.src.find("Open R2:", start)
        section = self.src[start:next_r]
        self.assertIn("Compress", section)
        self.assertIn("Wait for call 14", section)


class R2DifferentiationAuditTrail(unittest.TestCase):
    def setUp(self):
        self.src = RESEARCH_DOC.read_text(encoding="utf-8")

    def test_r2_marked_answered_2026_05_22(self):
        start = self.src.find("Open R2:")
        next_r = self.src.find("Open R3:", start)
        section = self.src[start:next_r]
        self.assertIn("ANSWERED", section)
        self.assertIn("2026-05-22", section)

    def test_r2_states_no_prior_funded_projects(self):
        """The R2 answer is decisively NO — pinning the wording so
        the maintainer can copy it verbatim into the application
        draft if needed."""

        start = self.src.find("Open R2:")
        next_r = self.src.find("Open R3:", start)
        section = self.src[start:next_r]
        self.assertIn("NO", section)  # explicit
        self.assertIn("employment", section)
        self.assertIn("migration", section)

    def test_r2_records_source_url(self):
        start = self.src.find("Open R2:")
        next_r = self.src.find("Open R3:", start)
        section = self.src[start:next_r]
        self.assertIn("nlnet.nl/project", section)

    def test_r2_describes_positioning_impact(self):
        """The differentiation finding feeds §10 of the application
        draft. Pinning the recommended-language anchor so it can be
        retrieved by the maintainer or a future agent prepping the
        submission."""

        start = self.src.find("Open R2:")
        next_r = self.src.find("Open R3:", start)
        section = self.src[start:next_r]
        self.assertIn("differentiation", section.lower())
        self.assertIn("§10", section)


if __name__ == "__main__":
    unittest.main()
