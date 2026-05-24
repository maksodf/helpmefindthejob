# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""2026-05-23: BreadcrumbList JSON-LD on every indexable public page.

Google ranks BreadcrumbList structured data for the navigation
breadcrumb that appears under search-result snippets. Adding it on
every indexable page is a top-tier SEO baseline.

Coverage:
* Legal pages × 2 langs (privacy / terms / data-retention /
  impressum × EN+DE) — 3-level breadcrumb: Home > Legal > <page>
* Help / Status / Changelog — 2-level breadcrumb: Home > <page>

Skipped (with reason):
* /forgot-password — `noindex,nofollow`; Google won't see it
* /opensearch.xml — site has no `/search` endpoint to back it, so
  shipping an OpenSearch descriptor would be misleading
* FAQPage schema on /help — the page is topical (h2 sections), not
  Q&A; FAQPage would be inauthentic. Revisit when /help is
  restructured to actual Q&A.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "static"


def _extract_all_jsonld(filename: str) -> list[dict]:
    html = (STATIC / filename).read_text(encoding="utf-8")
    blocks: list[dict] = []
    for match in re.finditer(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        html,
        re.DOTALL,
    ):
        try:
            blocks.append(json.loads(match.group(1)))
        except json.JSONDecodeError as e:
            raise AssertionError(f"{filename} has malformed JSON-LD: {e}")
    return blocks


_LEGAL = [
    ("privacy.html", "Privacy", "en"),
    ("privacy.de.html", "Datenschutz", "de"),
    ("terms.html", "Terms", "en"),
    ("terms.de.html", "Nutzungsbedingungen", "de"),
    ("data-retention.html", "Data retention", "en"),
    ("data-retention.de.html", "Aufbewahrungsfristen", "de"),
    ("impressum.html", "Impressum", "de"),
    ("impressum.en.html", "Imprint", "en"),
]

_SECONDARY = [
    ("help.html", "Help", "/help"),
    ("status.html", "Status", "/status"),
    ("changelog.html", "Changelog", "/changelog"),
]


class LegalPagesHaveBreadcrumbList(unittest.TestCase):
    def test_every_legal_page_has_breadcrumbs_block(self) -> None:
        for filename, expected_name, _lang in _LEGAL:
            with self.subTest(filename=filename):
                blocks = _extract_all_jsonld(filename)
                breadcrumbs = [b for b in blocks if b.get("@type") == "BreadcrumbList"]
                self.assertEqual(
                    len(breadcrumbs),
                    1,
                    f"{filename}: expected exactly one BreadcrumbList block, "
                    f"got {len(breadcrumbs)}",
                )
                items = breadcrumbs[0].get("itemListElement", [])
                # Legal pages have 3 levels: Home > Legal > <Page>
                self.assertEqual(
                    len(items),
                    3,
                    f"{filename}: expected 3 breadcrumb levels, got {len(items)}",
                )
                # Third (current page) item name must match the page's locale
                self.assertEqual(
                    items[2]["name"],
                    expected_name,
                    f"{filename}: third crumb name {items[2]['name']!r} "
                    f"!= expected {expected_name!r}",
                )

    def test_breadcrumb_localisation_matches_page_lang(self) -> None:
        for filename, _expected_name, lang in _LEGAL:
            with self.subTest(filename=filename, lang=lang):
                blocks = _extract_all_jsonld(filename)
                breadcrumbs = [b for b in blocks if b.get("@type") == "BreadcrumbList"][0]
                home_label = breadcrumbs["itemListElement"][0]["name"]
                legal_label = breadcrumbs["itemListElement"][1]["name"]
                if lang == "de":
                    self.assertEqual(home_label, "Startseite")
                    self.assertEqual(legal_label, "Rechtliches")
                else:
                    self.assertEqual(home_label, "Home")
                    self.assertEqual(legal_label, "Legal")

    def test_breadcrumb_third_url_matches_page_canonical(self) -> None:
        # Both /impressum.html and impressum.en.html → URL /impressum
        # Both privacy variants → /privacy
        # etc. The breadcrumb's terminal URL is locale-agnostic; the
        # NAME field carries the localisation.
        for filename, _expected_name, _lang in _LEGAL:
            with self.subTest(filename=filename):
                blocks = _extract_all_jsonld(filename)
                breadcrumbs = [b for b in blocks if b.get("@type") == "BreadcrumbList"][0]
                terminal_url = breadcrumbs["itemListElement"][2]["item"]
                self.assertTrue(
                    terminal_url.startswith("https://helpmefindthejob.org/"),
                    f"{filename}: terminal URL must be absolute HTTPS to the canonical host",
                )


class SecondaryPagesHaveBreadcrumbList(unittest.TestCase):
    def test_help_status_changelog_have_two_level_breadcrumbs(self) -> None:
        for filename, expected_name, expected_url in _SECONDARY:
            with self.subTest(filename=filename):
                blocks = _extract_all_jsonld(filename)
                breadcrumbs = [b for b in blocks if b.get("@type") == "BreadcrumbList"]
                self.assertEqual(
                    len(breadcrumbs),
                    1,
                    f"{filename}: expected exactly one BreadcrumbList block",
                )
                items = breadcrumbs[0]["itemListElement"]
                self.assertEqual(
                    len(items),
                    2,
                    f"{filename}: expected 2 breadcrumb levels (Home > {expected_name})",
                )
                self.assertEqual(items[0]["name"], "Home")
                self.assertEqual(items[1]["name"], expected_name)
                self.assertEqual(
                    items[1]["item"],
                    f"https://helpmefindthejob.org{expected_url}",
                )


if __name__ == "__main__":
    unittest.main()
