# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Application-draft numerical-claim drift guard — closes phase2-
backlog #59.

Three numerical claims in the NLnet application body were reworded
in 2026-05-19 pass 2 because their primary sources didn't yield
specific headline figures. The 2026-05-22 re-verification pass 3
re-attempted all 3 via 8 fresh WebFetch routes — all routes
returned 404 / 403 / navigation-only. Reword retained.

If a future maintainer (or future agent) accidentally re-introduces
the precise figures into the application body without primary-source
verification, the application's honesty discipline (Rule 2 of
`13-lessons-learned.md`) is violated. This test catches that.

The test scope is BODY TEXT in the application package files. The
verification table in `application-draft-2026-05-19.md` is the
audit trail and SHOULD still mention the prior numbers (in
historical context) — so the test excludes that file.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APPLICATION_PACKAGE = REPO_ROOT / "docs" / "grant" / "12-application-package.md"
APPLICATION_DRAFT = REPO_ROOT / "docs" / "grant" / "application-draft-2026-05-19.md"


class ApplicationBodyHasNoUnverifiedPreciseNumbers(unittest.TestCase):
    """The reworded claims must stay reworded in the application
    body until / unless a primary-source URL surfaces."""

    def setUp(self):
        self.body = APPLICATION_PACKAGE.read_text(encoding="utf-8")

    def test_healthcare_claim_not_reverted_to_precise_46000(self):
        """The "~46,000 unfilled healthcare positions" claim was
        reworded to "tens of thousands". If someone reverts to a
        precise figure, this fires."""

        # Tolerate the audit-trail phrasing "(was: ...)" — only
        # body assertions count.
        body_lines = [
            ln for ln in self.body.splitlines() if "(was:" not in ln and "was: " not in ln
        ]
        body_text = "\n".join(body_lines)

        forbidden_patterns = [
            r"46[,.]000\s+unfilled",
            r"46[,.]000\s+vacant",
            r"~46[,.]000",
            r"about 46[,.]000",
        ]
        for pat in forbidden_patterns:
            with self.subTest(pattern=pat):
                self.assertIsNone(
                    re.search(pat, body_text),
                    f"application body reverted to precise '46,000' "
                    f"figure (pattern: {pat!r}) — re-verify primary "
                    f"source first or keep the 'tens of thousands' "
                    f"rewording",
                )

    def test_mbe_claim_not_reverted_to_precise_700(self):
        """The MBE "~700 service points" claim was reworded to drop
        the count entirely + name the operational architecture."""

        body_lines = [
            ln for ln in self.body.splitlines() if "(was:" not in ln and "was: " not in ln
        ]
        body_text = "\n".join(body_lines)

        forbidden_patterns = [
            r"~700\s+(?:MBE|Migrationsberatung|service points|Beratungsstellen)",
            r"700\s+Migrationsberatungsstellen",
            r"about 700\s+(?:MBE|Migrationsberatung)",
        ]
        for pat in forbidden_patterns:
            with self.subTest(pattern=pat):
                self.assertIsNone(
                    re.search(pat, body_text),
                    f"application body reverted to precise '700' MBE "
                    f"count (pattern: {pat!r}) — re-verify primary "
                    f"source or keep the operational-architecture phrasing",
                )

    def test_optionskommunen_claim_carries_cap_phrasing(self):
        """The Optionskommunen claim was reworded to cap-vs-current
        distinction. The body must still reference either the
        §6a SGB II cap or note that the BMAS list is the source of
        truth. If neither phrasing is present, someone has stripped
        the qualifier."""

        body_text = self.body

        # At least one of these qualifiers must be present
        qualifiers = [
            "§6a SGB II",
            "25%",
            "BMAS-published list",
            "BMAS list is the source",
        ]
        has_qualifier = any(q in body_text for q in qualifiers)
        self.assertTrue(
            has_qualifier,
            "application body no longer carries the Optionskommunen "
            "cap-vs-current-count qualifier — at least one of "
            "§6a SGB II / 25% / BMAS-published-list phrasing must "
            "appear if the figure is asserted at all",
        )


class VerificationTableDocumentsRequiredAuditTrail(unittest.TestCase):
    """The application-draft verification table is the audit trail.
    It MUST carry the pass-2 + pass-3 documentation so a reader can
    reconstruct the verification history."""

    def setUp(self):
        self.draft = APPLICATION_DRAFT.read_text(encoding="utf-8")

    def test_pass_3_audit_trail_present(self):
        """Pass 3 (2026-05-22) must be documented after pass 2."""

        self.assertIn(
            "Re-verification pass 3 — 2026-05-22",
            self.draft,
            "application draft missing pass-3 audit trail",
        )

    def test_pass_3_documents_all_three_claims(self):
        """Each reworded claim must be documented in the pass-3
        table so the verification history is complete."""

        # Find the pass-3 section
        start = self.draft.find("Re-verification pass 3 — 2026-05-22")
        self.assertGreater(start, 0)
        section = self.draft[start:]

        for required in (
            "Healthcare unfilled positions",
            "Migrationsberatungsstellen",
            "Optionskommunen",
        ):
            with self.subTest(claim=required):
                self.assertIn(
                    required,
                    section,
                    f"pass-3 audit trail missing {required}",
                )

    def test_pass_3_documents_route_count(self):
        """The pass-3 narrative must state how many routes were
        attempted — this is the evidence the re-attempt was
        thorough, not perfunctory."""

        start = self.draft.find("Re-verification pass 3 — 2026-05-22")
        section = self.draft[start:]
        self.assertIn(
            "8 distinct WebFetch routes",
            section,
            "pass-3 must document the number of fetch routes tried",
        )


if __name__ == "__main__":
    unittest.main()
