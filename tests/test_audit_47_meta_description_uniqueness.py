# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""AUDIT-47 — per-page meta descriptions are distinct.

When the audit was originally raised the project shipped an
identical ``<meta name="description">`` on every URL — a copy of the
landing-page tagline. Search results then collapsed multiple pages
into one (Google deduplicates by description) and any page-specific
copy was lost.

Prior audits (AUDIT-29 / AUDIT-30 cycles) authored distinct
descriptions per page. AUDIT-47's regression guard pins that state
so future template tweaks can't quietly re-introduce the duplicate.

Per page the description must:

  * Be present and non-empty.
  * Be globally unique across the public surface — no two pages
    share the same string.
  * Stay within Google's ~160-character render window (we allow
    up to 220 to leave room for German translations, which tend to
    run ~25 % longer than English).
  * Carry the project name "Helpmefindthejob" so search results
    always brand correctly.

The bilingual variants (foo.html vs foo.de.html) count as distinct
pages because Google resolves them via the hreflang alternates.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"

# Public HTML surface. ``forgot-password.html`` and its DE variant
# are included even though they're robots-noindexed, because Google
# will still surface the description in SERP if it ever decides to
# index them (typically only via direct sitemap discovery).
_PUBLIC_PAGES = (
    "index.html",
    "privacy.html",
    "privacy.de.html",
    "terms.html",
    "terms.de.html",
    "data-retention.html",
    "data-retention.de.html",
    "impressum.html",
    "impressum.en.html",
    "help.html",
    "status.html",
    "changelog.html",
    "forgot-password.html",
    "forgot-password.de.html",
)

_DESCRIPTION_RX = re.compile(
    r'<meta\s+name="description"\s+content="([^"]*)"\s*/?>',
    re.IGNORECASE,
)

# Per Google's documentation a meta description is rendered up to
# ~160 chars on desktop and ~120 on mobile. We accept up to 220 to
# fit German translations (which tend to run ~25 % longer). Lower
# bound of 30 keeps placeholders out.
_MIN_DESCRIPTION_LEN = 30
# Strict 160-char cap — Google truncates desktop SERP descriptions at
# ~160 chars and mobile at ~120. Self-audit (2026-05-23) discovered
# 5 descriptions exceeded this; the test was loosened to 220 to fit
# German translations, but that allowed silent truncation. Tightened
# to 160 so DE + EN both stay within the rendered window.
_MAX_DESCRIPTION_LEN = 160


def _extract_description(filename: str) -> str:
    html = (STATIC / filename).read_text(encoding="utf-8")
    match = _DESCRIPTION_RX.search(html)
    if match is None:
        raise AssertionError(f"{filename} has no meta description tag")
    return match.group(1)


class MetaDescriptionPerPage(unittest.TestCase):
    """Every public page declares a non-empty, branded, length-bounded
    description."""

    def test_every_public_page_has_a_description(self) -> None:
        for filename in _PUBLIC_PAGES:
            with self.subTest(filename=filename):
                desc = _extract_description(filename)
                self.assertGreaterEqual(
                    len(desc),
                    _MIN_DESCRIPTION_LEN,
                    f"AUDIT-47: {filename} description is too short "
                    f"({len(desc)} chars) — looks like a placeholder.",
                )
                self.assertLessEqual(
                    len(desc),
                    _MAX_DESCRIPTION_LEN,
                    f"AUDIT-47: {filename} description is too long "
                    f"({len(desc)} chars) — Google truncates at ~160.",
                )

    def test_every_description_mentions_the_brand(self) -> None:
        for filename in _PUBLIC_PAGES:
            with self.subTest(filename=filename):
                desc = _extract_description(filename)
                self.assertIn(
                    "Helpmefindthejob",
                    desc,
                    f"AUDIT-47: {filename} description doesn't carry the brand; "
                    "SERP results then collapse into anonymous snippets.",
                )


class MetaDescriptionUniqueness(unittest.TestCase):
    """No two public pages may share the same description.

    Google deduplicates SERP results by description. Two pages with
    identical descriptions get collapsed; the user only sees one.
    This is the regression the original audit caught.
    """

    def test_all_descriptions_are_unique(self) -> None:
        seen: dict[str, str] = {}  # description → first filename that used it
        for filename in _PUBLIC_PAGES:
            desc = _extract_description(filename)
            if desc in seen:
                self.fail(
                    f"AUDIT-47 regression: {filename} shares its meta "
                    f"description with {seen[desc]!r}. Google will collapse "
                    "these into a single SERP result. Author distinct "
                    "descriptions per page so each surface ranks for its "
                    "own intent."
                )
            seen[desc] = filename


if __name__ == "__main__":
    unittest.main()
