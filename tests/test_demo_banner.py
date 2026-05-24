# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guards for the demo-deployment banner.

PlanTowardPerfection box 1.6.5 ships a small banner that appears
when a reviewer lands on `demo.helpmefindthejob.org` (or with
`?demo=1` for QA). The banner explains accounts are reset nightly
so reviewers do not worry about mutating shared data.

The implementation is intentionally minimal — three artefacts:

1. The banner `<aside id="demoBanner">` lives in `static/index.html`
   with the `hidden` attribute by default.
2. `static/demo-banner.js` is a tiny IIFE that reveals the banner
   iff the runtime hostname matches the demo subdomain or the URL
   has `?demo=1`.
3. CSS rules in `static/styles.css` style the revealed banner.

This test pins the three invariants so a future agent that edits
any of the three files cannot silently break the demo-banner
appearance contract. The actual runtime appearance is verified by
the operator's pre-demo Playwright smoke test (`scripts/probe-
ai-router.sh` adjacent; scoped for Ceiling-2 §2.5).
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = REPO_ROOT / "static" / "index.html"
DEMO_BANNER_JS = REPO_ROOT / "static" / "demo-banner.js"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
STYLES_MIN_CSS = REPO_ROOT / "static" / "styles.min.css"


class DemoBannerInIndexHtml(unittest.TestCase):
    """The aside element + the script reference both live in
    `static/index.html`. Both must be present for the banner to
    work on the deployed demo subdomain."""

    def setUp(self) -> None:
        self.src = INDEX_HTML.read_text(encoding="utf-8")

    def test_banner_aside_present(self) -> None:
        self.assertIn(
            'id="demoBanner"',
            self.src,
            "demoBanner aside element missing from static/index.html — "
            "the demo-banner.js reveal logic targets this id",
        )

    def test_banner_aside_hidden_by_default(self) -> None:
        # The aside must have the `hidden` attribute so the apex
        # (non-demo) deployment does not show the banner.
        idx = self.src.find('id="demoBanner"')
        self.assertGreater(idx, 0)
        # Find the opening `<aside` for this id; check `hidden` is
        # in the same opening tag.
        start = self.src.rfind("<aside", 0, idx)
        end = self.src.find(">", idx)
        self.assertGreater(end, idx)
        opening_tag = self.src[start:end]
        self.assertIn(
            "hidden",
            opening_tag,
            f"demoBanner aside opening tag {opening_tag!r} missing the "
            "`hidden` attribute — banner would show on apex too",
        )

    def test_banner_script_loaded(self) -> None:
        self.assertIn(
            "/demo-banner.js",
            self.src,
            "demo-banner.js not referenced from static/index.html — "
            "banner would never be revealed on the demo subdomain",
        )

    def test_banner_aria_label_for_screen_readers(self) -> None:
        # The aside must carry an aria-label so screen-reader users
        # hear the banner announcement explicitly.
        idx = self.src.find('id="demoBanner"')
        start = self.src.rfind("<aside", 0, idx)
        end = self.src.find(">", idx)
        opening_tag = self.src[start:end]
        self.assertIn(
            "aria-label=",
            opening_tag,
            f"demoBanner missing aria-label in {opening_tag!r} — "
            "screen-reader users would not get banner context",
        )


class DemoBannerJavaScript(unittest.TestCase):
    """The reveal logic itself: hostname check + ?demo=1 fallback +
    targets the `demoBanner` id."""

    def setUp(self) -> None:
        self.src = DEMO_BANNER_JS.read_text(encoding="utf-8")

    def test_file_exists_and_substantive(self) -> None:
        self.assertTrue(DEMO_BANNER_JS.is_file())
        self.assertGreater(len(self.src), 500, "demo-banner.js suspiciously small")

    def test_hostname_check(self) -> None:
        # The JS must hard-code the public demo subdomain so a
        # malicious page-content edit cannot trick the banner into
        # showing on the apex.
        self.assertIn(
            "demo.helpmefindthejob.org",
            self.src,
            "demo-banner.js must hard-code the demo subdomain — "
            "soft-coded hostnames would be a confusion-deputy bug",
        )

    def test_query_param_fallback(self) -> None:
        # ?demo=1 is the QA-only override so the maintainer can
        # preview the banner on the apex without DNS games. Must
        # exist + must be coded as the literal "1" (not e.g.
        # `.has('demo')` which would let `?demo=0` also reveal).
        self.assertIn(
            "demo",
            self.src,
        )
        self.assertIn(
            '=== "1"',
            self.src,
            "demo-banner.js must check for the literal `1` value of "
            "the `?demo=` query param — looser checks let `?demo=0` "
            "or `?demo` reveal the banner",
        )

    def test_targets_demoBanner_id(self) -> None:
        self.assertIn(
            'getElementById("demoBanner")',
            self.src,
            "demo-banner.js must target the `demoBanner` id — the "
            "aside in static/index.html depends on this exact id",
        )


class DemoBannerStyles(unittest.TestCase):
    """CSS rules: the .demo-banner class must exist in both the
    human-readable source AND the minified bundle (built artefact)."""

    def test_source_css_has_rule(self) -> None:
        css = STYLES_CSS.read_text(encoding="utf-8")
        self.assertIn(
            ".demo-banner",
            css,
            ".demo-banner CSS rule missing from styles.css — "
            "banner would render unstyled (poor contrast risk)",
        )

    def test_minified_css_has_rule(self) -> None:
        if not STYLES_MIN_CSS.is_file():
            self.skipTest("styles.min.css not built yet")
        mini = STYLES_MIN_CSS.read_text(encoding="utf-8")
        if len(mini) < 100:
            self.skipTest(
                "styles.min.css is placeholder-sized — build pipeline "
                "has not run yet; the prod deploy will fail other tests "
                "before this one becomes meaningful"
            )
        self.assertIn(
            ".demo-banner",
            mini,
            ".demo-banner CSS class missing from minified bundle — "
            "rerun `bash scripts/build-static.sh` after editing styles.css",
        )


if __name__ == "__main__":
    unittest.main()
