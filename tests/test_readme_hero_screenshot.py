# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guard for the README hero screenshot.

The README
opens with a single screenshot of the product showing the
language switcher and the headline value prop. The screenshot lives
at `docs/screenshots/hero-landing.png` and is captured from the
public marketing landing of a running instance.

This test pins three invariants so a future agent that edits the
README cannot silently drop the hero, rename the file, or commit
an empty PNG:

1. The image file exists.
2. The image is non-trivial in size (>=100 KiB rules out a 1x1
   placeholder).
3. The README references the image at its canonical path.

A 4th invariant — that the image actually shows the current
branding — is enforced by the human reviewer at commit time, not
this test. PNG content cannot be cheaply inspected here.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HERO = REPO_ROOT / "docs" / "screenshots" / "hero-landing.png"
README = REPO_ROOT / "README.md"


class ReadmeHeroScreenshot(unittest.TestCase):
    def test_hero_file_exists(self) -> None:
        self.assertTrue(
            HERO.is_file(),
            f"hero screenshot missing at {HERO} — recapture via "
            "/tmp/capture_hero.py against a running app instance",
        )

    def test_hero_file_is_substantive(self) -> None:
        size = HERO.stat().st_size
        self.assertGreaterEqual(
            size,
            100 * 1024,
            f"hero screenshot at {HERO} is only {size} bytes — "
            "smaller than 100 KiB suggests a placeholder; recapture",
        )

    def test_readme_embeds_hero(self) -> None:
        src = README.read_text(encoding="utf-8")
        canonical = "docs/screenshots/hero-landing.png"
        self.assertIn(
            canonical,
            src,
            f"README no longer embeds {canonical} — Ceiling-1 box 1.3.1 "
            "requires the hero screenshot to be visible in the README",
        )

    def test_readme_hero_has_alt_text(self) -> None:
        """Markdown image embeds for the hero must include alt text
        (the bracketed portion of `![alt](path)`). Hero is the most
        important image in the README and must remain accessible to
        screen readers + degraded-network surfaces."""

        src = README.read_text(encoding="utf-8")
        # Find every Markdown image embed that points at the hero.
        # Pattern: ![<alt>](docs/screenshots/hero-landing.png ...)
        # We allow optional title (`"..."`) after the path.
        import re

        pattern = re.compile(r"!\[([^\]]*)\]\(docs/screenshots/hero-landing\.png[^)]*\)")
        matches = pattern.findall(src)
        self.assertGreater(
            len(matches),
            0,
            "README references the hero path but not via a Markdown "
            "image embed — bare-path references defeat assistive tech",
        )
        for alt in matches:
            with self.subTest(alt=alt):
                # Empty alt is allowed only for decorative images;
                # the hero is content-bearing, so require a description
                # of at least 30 chars (covers "civic-commons headline ..."
                # without forcing verbosity).
                self.assertGreaterEqual(
                    len(alt.strip()),
                    30,
                    f"hero image alt text {alt!r} is too short — should "
                    "describe the headline, value props, and the EN/DE "
                    "language switcher visible in the shot",
                )


if __name__ == "__main__":
    unittest.main()
