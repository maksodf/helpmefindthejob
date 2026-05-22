# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guard: favicon.ico + apple-touch-icon + og-card present
and properly linked from every public HTML page.

AUDIT-9 incident (2026-05-22): /favicon.ico returned 404 because the
project only shipped /icons/icon.svg (declared in manifest.webmanifest
but NOT linked from HTML <head>). Browsers, bookmarks, Slack/Teams
link unfurls, and search-results favicon probes all hit /favicon.ico
unconditionally and got a generic globe.

AUDIT-10 incident: og-card.png at /icons/og-card.png returned 404
despite every page's <meta property="og:image"> advertising it.
Social shares on X / LinkedIn / Slack / WhatsApp / iMessage /
Discord collapsed to plain text URLs.

This test enforces:
- static/favicon.ico exists (multi-resolution ICO, 16/24/32/48)
- static/apple-touch-icon.png exists (180×180)
- static/icons/og-card.png exists (1200×630)
- Every public HTML page links to all three icons in <head>
"""

from __future__ import annotations

import struct
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC = REPO_ROOT / "static"

FAVICON = STATIC / "favicon.ico"
APPLE_TOUCH = STATIC / "apple-touch-icon.png"
OG_CARD = STATIC / "icons" / "og-card.png"


# Every page that gets indexed by search engines / unfurled in chat /
# bookmarked. SPA index + every legal/marketing page.
PAGES = (
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
)


class FaviconAndIconsExistOnDisk(unittest.TestCase):
    def test_favicon_ico_exists_and_is_multi_res(self) -> None:
        self.assertTrue(FAVICON.exists(), "static/favicon.ico missing")
        # ICO header is 6 bytes: reserved(2) + type(2) + count(2)
        header = FAVICON.read_bytes()[:6]
        reserved, ico_type, count = struct.unpack("<HHH", header)
        self.assertEqual(reserved, 0, "ICO reserved field not 0")
        self.assertEqual(ico_type, 1, "ICO type field not 1 (icon)")
        self.assertGreaterEqual(
            count,
            2,
            f"ICO has only {count} frame(s); expected >= 2 for "
            f"multi-resolution. Regenerate with PIL.save(format='ICO', "
            f"sizes=[...]).",
        )

    def test_apple_touch_icon_exists_and_is_180px(self) -> None:
        self.assertTrue(APPLE_TOUCH.exists(), "static/apple-touch-icon.png missing")
        # PNG header: 8-byte sig + IHDR (4 length + 4 type + 4 width + 4 height)
        data = APPLE_TOUCH.read_bytes()[:24]
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual(width, 180, f"apple-touch-icon width: {width}, expected 180")
        self.assertEqual(height, 180, f"apple-touch-icon height: {height}, expected 180")

    def test_og_card_exists_and_is_1200x630(self) -> None:
        self.assertTrue(OG_CARD.exists(), "static/icons/og-card.png missing")
        data = OG_CARD.read_bytes()[:24]
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual(width, 1200, f"og-card width: {width}, expected 1200 (OG spec)")
        self.assertEqual(height, 630, f"og-card height: {height}, expected 630 (OG spec)")


class EveryPublicPageLinksAllThreeIcons(unittest.TestCase):
    def test_every_page_has_favicon_ico_link(self) -> None:
        missing = []
        for page in PAGES:
            html = (STATIC / page).read_text(encoding="utf-8")
            if '/favicon.ico' not in html:
                missing.append(page)
        self.assertEqual(missing, [], f"Pages missing /favicon.ico <link>: {missing}")

    def test_every_page_has_apple_touch_icon_link(self) -> None:
        missing = []
        for page in PAGES:
            html = (STATIC / page).read_text(encoding="utf-8")
            if '/apple-touch-icon.png' not in html:
                missing.append(page)
        self.assertEqual(
            missing, [], f"Pages missing /apple-touch-icon.png <link>: {missing}"
        )

    def test_every_page_has_og_image_pointing_at_real_file(self) -> None:
        """og:image meta tag must point at an existing PNG so social
        unfurls work."""
        import re

        for page in PAGES:
            html = (STATIC / page).read_text(encoding="utf-8")
            m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
            if m:
                with self.subTest(page=page):
                    url = m.group(1)
                    # Map URL → file on disk
                    # URL form: https://helpmefindthejob.org/icons/og-card.png
                    if url.startswith("https://helpmefindthejob.org/"):
                        rel = url[len("https://helpmefindthejob.org/"):]
                    else:
                        rel = url.lstrip("/")
                    p = STATIC / rel
                    self.assertTrue(
                        p.exists(),
                        f"{page}: og:image {url!r} → {p} doesn't exist on disk",
                    )


if __name__ == "__main__":
    unittest.main()
