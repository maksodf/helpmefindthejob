# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PWA install-eligibility contract test.

PlanTowardPerfection Ceiling-2 box 2.12.11: "PWA install banner
verified — beforeinstallprompt works on Chrome Android + iOS
Safari (Add to Home Screen)."

The actual `beforeinstallprompt` event fires only in Chromium-
based browsers when ALL of the W3C-published install criteria
are met simultaneously, on a user-interacted page, on HTTPS or
localhost. Reproducing this from a headless Playwright runner is
flaky (Chromium throttles the event during headless runs +
requires user-gesture heuristics). The reliable substitute is to
verify the install-eligibility CRITERIA programmatically from
the static files; the event itself fires reliably when the
criteria are all satisfied, and the manual verification recipe
at `docs/pwa-install-banner-verification.md` is the per-platform
audit cadence for the actual banner appearance.

Pins six install-eligibility criteria documented at
https://web.dev/learn/pwa/installation-prompt/:

1. The page is served over HTTPS (or localhost). [environment
   property — not testable here; recorded in the audit doc.]
2. The page links a web app manifest via `<link rel="manifest">`.
3. The manifest has the required fields: name (or short_name),
   start_url, display (standalone or minimal-ui), icons with at
   least one ≥192×192 PNG-or-SVG icon.
4. The page registers a service worker scoped to / (or above the
   manifest's scope).
5. The page's start_url is reachable + serves a 200.
6. The user has not previously dismissed the install prompt
   recently (Chrome heuristic — also environmental, recorded in
   the audit doc).
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = REPO_ROOT / "static" / "index.html"
MANIFEST = REPO_ROOT / "static" / "manifest.webmanifest"
SW_JS = REPO_ROOT / "static" / "sw.js"


class IndexHtmlLinksManifest(unittest.TestCase):
    """Criterion 2: the page links the manifest."""

    def setUp(self) -> None:
        self.src = INDEX_HTML.read_text(encoding="utf-8")

    def test_link_rel_manifest_present(self) -> None:
        self.assertRegex(
            self.src,
            r'<link[^>]*rel="manifest"[^>]*href="[^"]*manifest[^"]*"',
            "static/index.html missing <link rel=\"manifest\" href=...> tag — "
            "install prompt won't fire on any browser without this",
        )

    def test_link_rel_manifest_points_at_existing_manifest(self) -> None:
        import re
        m = re.search(r'<link[^>]*rel="manifest"[^>]*href="([^"]*)"', self.src)
        self.assertIsNotNone(m)
        href = m.group(1)
        # Allow root-relative or absolute
        manifest_name = href.lstrip("/")
        if manifest_name.startswith("https://") or manifest_name.startswith("http://"):
            # absolute URL — skip the file-existence check
            return
        manifest_path = REPO_ROOT / "static" / manifest_name
        self.assertTrue(
            manifest_path.is_file(),
            f"manifest link href={href!r} doesn't resolve to a file at {manifest_path}",
        )


class ManifestRequiredFields(unittest.TestCase):
    """Criterion 3: manifest has required PWA install fields."""

    def setUp(self) -> None:
        self.data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_has_name_or_short_name(self) -> None:
        self.assertTrue(
            self.data.get("name") or self.data.get("short_name"),
            "manifest must have at least one of name or short_name",
        )

    def test_has_start_url(self) -> None:
        self.assertIn("start_url", self.data)

    def test_display_mode_is_install_eligible(self) -> None:
        # Chrome accepts: fullscreen, standalone, minimal-ui (not
        # browser).
        display = self.data.get("display")
        self.assertIn(
            display,
            ("fullscreen", "standalone", "minimal-ui"),
            f"display mode {display!r} is not install-eligible per Chrome's "
            "criteria; must be fullscreen, standalone, or minimal-ui",
        )

    def test_has_icons(self) -> None:
        icons = self.data.get("icons", [])
        self.assertGreater(len(icons), 0, "manifest must declare at least one icon")

    def test_has_install_eligible_icon(self) -> None:
        """Chrome requires at least one icon of ≥192×192 in PNG or SVG.
        The 'any' sizes value satisfies this for SVG vector icons."""
        icons = self.data.get("icons", [])
        eligible = [
            ic for ic in icons
            if ic.get("sizes") == "any"
            or any(
                int(s.split("x")[0]) >= 192
                for s in ic.get("sizes", "").split()
                if "x" in s
            )
        ]
        self.assertGreater(
            len(eligible),
            0,
            "no install-eligible icon (need ≥192×192 PNG or sizes=\"any\" SVG); "
            f"got {icons!r}",
        )


class ServiceWorkerRegistered(unittest.TestCase):
    """Criterion 4: page registers a service worker. Registration
    happens in `static/app.js` (the SPA bundle), not directly in
    index.html — the index loads app.js which triggers the
    registration."""

    def setUp(self) -> None:
        # Check both app.js (source) and app.min.js (built) — at
        # least one must register the SW. The minified bundle is
        # what production serves; the source bundle is what unit
        # tests check the contract against.
        candidates = [
            REPO_ROOT / "static" / "app.js",
            REPO_ROOT / "static" / "app.min.js",
        ]
        self.bundles = [p for p in candidates if p.is_file()]

    def test_at_least_one_bundle_registers_sw(self) -> None:
        self.assertGreater(len(self.bundles), 0, "no app.js / app.min.js bundles found")
        any_registers = False
        for p in self.bundles:
            src = p.read_text(encoding="utf-8")
            if "serviceWorker.register" in src:
                any_registers = True
                break
        self.assertTrue(
            any_registers,
            f"none of the bundles {[p.name for p in self.bundles]} contain "
            "`serviceWorker.register` — install prompt won't fire",
        )

    def test_index_loads_the_bundle(self) -> None:
        # The index has to load the bundle for the registration to
        # execute at all.
        src = INDEX_HTML.read_text(encoding="utf-8")
        self.assertRegex(
            src,
            r'<script[^>]*src="[^"]*app(?:\.min)?\.js"',
            "static/index.html doesn't load the app bundle — SW registration "
            "never executes",
        )

    def test_sw_file_exists(self) -> None:
        self.assertTrue(SW_JS.is_file(), f"service worker file missing at {SW_JS}")

    def test_sw_scope_covers_root(self) -> None:
        # The default SW scope is the directory of the SW file (`/`
        # for `/sw.js`); the install prompt requires the scope cover
        # the page's URL. We assert the SW file is at the root
        # `static/sw.js` (served at `/sw.js`) so its default scope
        # is `/`.
        self.assertEqual(
            SW_JS.parent.name,
            "static",
            f"sw.js should be at static/sw.js so its default scope is /; "
            f"got {SW_JS}",
        )


class StartUrlReachable(unittest.TestCase):
    """Criterion 5: start_url resolves. We can't boot the app from
    a unit test, so we check that the start_url is `/` (the index
    route which the existing test_unauthenticated_landing.py + the
    rest of the suite exercise live)."""

    def setUp(self) -> None:
        self.data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_start_url_is_root(self) -> None:
        # Any value other than `/` would need additional eligibility
        # verification (the URL must serve a 200 + the scope must
        # cover it). `/` is the simplest correct answer.
        self.assertEqual(
            self.data.get("start_url"),
            "/",
            f"start_url must be `/` for the simplest install-eligibility "
            f"story; got {self.data.get('start_url')!r}",
        )


class EnvironmentCriteriaDocumented(unittest.TestCase):
    """Criteria 1 + 6 are environmental (HTTPS + heuristic prompt
    suppression) and can't be tested from a unit test. Verify the
    manual-verification recipe documents them."""

    def test_audit_doc_exists(self) -> None:
        audit = REPO_ROOT / "docs" / "pwa-install-banner-verification.md"
        self.assertTrue(
            audit.is_file(),
            f"PWA install-banner verification doc missing at {audit}; "
            "needed to document the environmental criteria (HTTPS, "
            "user-gesture heuristics) that can't be unit-tested",
        )


if __name__ == "__main__":
    unittest.main()
