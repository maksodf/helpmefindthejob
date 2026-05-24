# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guard: every legal page has both EN and DE files + a
language switcher.

AUDIT-6 (2026-05-22): static/privacy.html, terms.html, data-
retention.html, impressum.html had ZERO data-i18n attributes and no
DE translation files. A non-English-reading migrant landing on
/privacy saw English; a non-German-reading lawyer reviewing
/impressum saw German. Both backwards-of-intent.

This test enforces:

* Every legal page has both canonical and translated file present on
  disk (privacy.html + privacy.de.html; impressum.html + impressum.en.html).
* Every legal HTML file (EN or DE) contains a `language-switcher`
  block so users can find the other language.
* The Handler's `_resolve_user_language` + `_bilingual_page_path`
  helpers exist (server-side routing for ?lang= / cookie /
  Accept-Language).
"""

from __future__ import annotations

import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"


LEGAL_PAGE_PAIRS = (
    ("privacy.html", "privacy.de.html"),
    ("terms.html", "terms.de.html"),
    ("data-retention.html", "data-retention.de.html"),
    ("impressum.html", "impressum.en.html"),  # DE-canonical; EN courtesy
)


class LegalPagesAreBilingual(unittest.TestCase):
    def test_every_legal_page_has_both_language_files(self) -> None:
        missing = []
        for a, b in LEGAL_PAGE_PAIRS:
            if not (STATIC / a).exists():
                missing.append(a)
            if not (STATIC / b).exists():
                missing.append(b)
        self.assertEqual(missing, [], f"Missing bilingual legal files: {missing}")

    def test_every_legal_page_has_language_switcher(self) -> None:
        missing = []
        for a, b in LEGAL_PAGE_PAIRS:
            for filename in (a, b):
                src = (STATIC / filename).read_text(encoding="utf-8")
                if 'class="language-switcher"' not in src:
                    missing.append(filename)
        self.assertEqual(
            missing,
            [],
            f"Legal pages missing language-switcher block: {missing}",
        )

    def test_translation_files_have_correct_html_lang(self) -> None:
        # DE translation files: <html lang="de">
        for de_file in (
            "privacy.de.html",
            "terms.de.html",
            "data-retention.de.html",
        ):
            src = (STATIC / de_file).read_text(encoding="utf-8")
            self.assertIn(
                '<html lang="de">',
                src,
                f'{de_file} missing <html lang="de">',
            )
        # EN courtesy translation of Impressum
        en_src = (STATIC / "impressum.en.html").read_text(encoding="utf-8")
        self.assertIn(
            '<html lang="en">',
            en_src,
            'impressum.en.html missing <html lang="en">',
        )

    def test_de_privacy_contains_key_legal_markers(self) -> None:
        """DE Privacy must substantiate the same AI-Act + GDPR claims
        as the EN version (AUDIT-6 must not regress AUDIT-5)."""

        de = (STATIC / "privacy.de.html").read_text(encoding="utf-8")
        for marker in (
            "Artikel 12",
            "Artikel 20",
            "DSGVO",
            "KI-Verordnung",
            "BlnBDI",
            "datenschutz-berlin",
            "Berliner Beauftragte",
            "Datenschutzbeauftragter",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, de, f"DE Privacy missing {marker!r}")


class HandlerHasBilingualRoutingHelpers(unittest.TestCase):
    def test_resolve_user_language_helper_present(self) -> None:
        from app import Handler

        self.assertTrue(
            hasattr(Handler, "_resolve_user_language"),
            "Handler missing _resolve_user_language (AUDIT-6 SSR helper)",
        )
        self.assertTrue(
            hasattr(Handler, "_bilingual_page_path"),
            "Handler missing _bilingual_page_path (AUDIT-6 SSR helper)",
        )

    def test_bilingual_page_path_maps_correctly(self) -> None:
        from app import Handler

        # /impressum is DE-canonical
        self.assertEqual(
            Handler._bilingual_page_path(None, "/impressum", "en"),
            "/impressum.en",
        )
        self.assertEqual(
            Handler._bilingual_page_path(None, "/impressum", "de"),
            "/impressum",
        )
        # Other legal pages are EN-canonical with .de courtesy
        self.assertEqual(
            Handler._bilingual_page_path(None, "/privacy", "de"),
            "/privacy.de",
        )
        self.assertEqual(
            Handler._bilingual_page_path(None, "/privacy", "en"),
            "/privacy",
        )


if __name__ == "__main__":
    unittest.main()
