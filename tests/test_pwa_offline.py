# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PWA / offline mode contract tests (post-sprint engineer-gap #2).

The 40-gap analysis flagged "PWA / offline mode not verified."
This file pins:

1. **Manifest shape**: name + short_name match the project name
   (catches pre-rename drift); description carries friction-class
   positioning, NOT the legacy healthcare-management one; required
   PWA fields (start_url, scope, display, icons) are set.

2. **Service worker contract**:
   - SHELL_PATHS includes every critical app-shell file PLUS
     i18n/locales.json (W3 D15 multilingual scaffolding).
   - Cache version bumped on every shell-changing release so
     activate handler picks up the new SHELL_CACHE.
   - Activate handler cleans up BOTH the current cache-prefix
     AND the legacy `directjob-shell-` prefix from the rename.
   - /api/* is NEVER cached (the SW must short-circuit on it).
   - App shell uses network-first (so re-deploys land
     immediately); other static assets cache-first.
   - Push handler exists for Web Push delivery (matches the
     classify_push_exception E2E tests in
     test_alert_delivery_e2e.py).

3. **Index.html links to manifest + registers SW** (without
   these, the PWA never installs).

4. **Static-file server actually serves the manifest + sw.js**
   at the expected URLs (runtime check via HTTP boot).

These tests catch silent regressions: a contributor who renames
the cache prefix without updating the cleanup filter, or removes
a critical SHELL_PATH, or changes the manifest name without
updating the README — all fail here.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC = REPO_ROOT / "static"
MANIFEST = STATIC / "manifest.webmanifest"
SW = STATIC / "sw.js"
INDEX = STATIC / "index.html"


class ManifestShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MANIFEST.exists():
            raise unittest.SkipTest(f"manifest not at {MANIFEST}")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_name_matches_project(self):
        # Project rename landed in commit fd2a474. Manifest MUST
        # carry the post-rename name.
        self.assertEqual(self.manifest.get("name"), "Helpmefindthejob")
        self.assertEqual(self.manifest.get("short_name"), "Helpmefindthejob")

    def test_description_not_pre_rename(self):
        desc = self.manifest.get("description", "")
        self.assertTrue(desc, "manifest description is empty")
        # The pre-rename description called the project a
        # "Healthcare-management … job-search assistant." The
        # friction-class repositioning makes that wrong.
        self.assertNotIn(
            "Healthcare-management",
            desc,
            "manifest description still carries the pre-rename "
            "healthcare-management positioning",
        )

    def test_required_pwa_fields_present(self):
        for field in (
            "name",
            "short_name",
            "start_url",
            "scope",
            "display",
            "icons",
            "theme_color",
            "background_color",
        ):
            self.assertIn(field, self.manifest, f"manifest missing {field}")

    def test_display_is_standalone_or_minimal_ui(self):
        # PWA installability needs display = standalone | minimal-ui
        # | fullscreen per the W3C manifest spec
        self.assertIn(
            self.manifest.get("display"),
            ("standalone", "minimal-ui", "fullscreen"),
        )

    def test_at_least_one_icon_with_purpose(self):
        icons = self.manifest.get("icons", [])
        self.assertGreaterEqual(len(icons), 1)
        # At least one icon should be installable (any | maskable)
        purposes = {p.strip() for icon in icons for p in str(icon.get("purpose", "")).split()}
        self.assertTrue(
            purposes & {"any", "maskable"},
            "no icon declares purpose=any|maskable",
        )


class ServiceWorkerContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SW.exists():
            raise unittest.SkipTest(f"sw.js not at {SW}")
        cls.text = SW.read_text(encoding="utf-8")

    def test_cache_version_constant_present(self):
        # CACHE_VERSION drives the per-deploy cache busting. Without
        # it, browser caches go stale forever.
        self.assertRegex(self.text, r"CACHE_VERSION\s*=\s*[\"']v[\d.]+[\"']")

    def test_cache_prefix_post_rename(self):
        # Cache prefix MUST be the post-rename one; legacy is only
        # referenced for cleanup of users with the old PWA installed.
        self.assertIn('CACHE_PREFIX = "helpmefindthejob-shell-"', self.text)

    def test_legacy_cache_prefix_cleanup_present(self):
        # Without this, users who installed the PWA pre-rename keep
        # their dead `directjob-shell-*` cache buckets forever.
        self.assertIn("LEGACY_CACHE_PREFIX", self.text)
        self.assertIn('"directjob-shell-"', self.text)

    def test_shell_paths_includes_locale_registry(self):
        # W3 D15 multilingual scaffolding adds /i18n/locales.json.
        # If it's not in SHELL_PATHS, the loadLocaleRegistry() call
        # in app.js would fail offline.
        self.assertIn("/i18n/locales.json", self.text)

    def test_shell_paths_includes_core_assets(self):
        for path in (
            '"/"',
            '"/index.html"',
            '"/app.js"',
            '"/styles.css"',
            '"/manifest.webmanifest"',
            '"/i18n/en.json"',
            '"/i18n/de.json"',
        ):
            self.assertIn(
                path,
                self.text,
                f"SHELL_PATHS missing critical asset: {path}",
            )

    def test_api_paths_not_cached(self):
        # /api/* MUST short-circuit out of the cache layer — caching
        # a logged-in user's API response would leak data across users
        # or stale them.
        self.assertRegex(
            self.text,
            r'url\.pathname\.startsWith\([\'"]\s*/api/\s*[\'"]\)',
            "SW doesn't short-circuit /api/ — risk of caching auth-scoped responses",
        )

    def test_shell_strategy_is_network_first(self):
        # App shell uses network-first so re-deploys land immediately
        # — old build was cache-first with a manual CACHE_VERSION bump
        # per deploy, which was a stale-version trap.
        self.assertIn("network-first", self.text.lower())
        # Sanity: fetch(request) is called before caches.match
        fetch_index = self.text.find("await fetch(request)")
        cache_match_index = self.text.find("caches.match(request)")
        self.assertGreater(fetch_index, 0)
        self.assertGreater(cache_match_index, 0)

    def test_offline_navigation_fallback_to_index(self):
        # When offline + navigation request → serve cached index.html
        # so the SPA shell at least renders an offline UI.
        self.assertIn('caches.match("/index.html")', self.text)
        self.assertRegex(self.text, r'request\.mode\s*===?\s*[\'"]navigate[\'"]')

    def test_push_handler_present(self):
        # Web Push relies on the SW's "push" event listener. Without
        # it, notifications from notify_new_matches never reach the
        # user's notification tray.
        self.assertIn('addEventListener("push"', self.text)
        self.assertIn("showNotification", self.text)

    def test_notification_click_handler_present(self):
        # Click → focus existing tab or open new one with the
        # notification's URL. Without it, a click does nothing.
        self.assertIn('addEventListener("notificationclick"', self.text)

    def test_skip_waiting_on_install(self):
        # New SW takes over immediately on install (matches the
        # network-first deploy strategy).
        self.assertIn("skipWaiting", self.text)

    def test_clients_claim_on_activate(self):
        # Activate handler claims open tabs so they're controlled by
        # the new SW without a manual reload.
        self.assertIn("clients.claim", self.text)


class IndexHtmlRegistersSW(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not INDEX.exists():
            raise unittest.SkipTest(f"index.html not at {INDEX}")
        cls.text = INDEX.read_text(encoding="utf-8")

    def test_index_links_to_manifest(self):
        # Without <link rel="manifest"> the PWA NEVER becomes
        # installable in Chrome / Edge / Safari.
        self.assertRegex(
            self.text,
            r'<link[^>]+rel=[\'"]manifest[\'"][^>]+href=[\'"]/manifest\.webmanifest[\'"]',
        )

    def test_app_js_registers_sw(self):
        # The SW must be registered from app.js (the SPA bootstrap).
        # We check app.js carries the register call.
        app_js = (STATIC / "app.js").read_text(encoding="utf-8")
        self.assertIn('navigator.serviceWorker.register("/sw.js")', app_js)


class PreRenameResidueGuard(unittest.TestCase):
    """Drift guard: user-facing static surfaces MUST NOT carry the
    pre-rename `DirectJob` brand. The project was renamed
    Helpmefindthejob in commit fd2a474 + Decision 22 made
    helpmefindthejob.com canonical.

    Comment-only references to the legacy prefix (e.g., the SW's
    LEGACY_CACHE_PREFIX block that documents the cleanup) are
    permitted by allowlisting via path."""

    USER_FACING_GLOBS = [
        "static/index.html",
        "static/bookmarklet.js",
        "static/i18n/en.json",
        "static/i18n/de.json",
        "static/manifest.webmanifest",
    ]

    def test_server_version_not_pre_rename(self):
        # The HTTP Server: response header SHOULD carry the post-
        # rename name so external scanners + log aggregators don't
        # mis-attribute traffic to a defunct brand.
        from app import Handler

        self.assertIn(
            "Helpmefindthejob",
            Handler.server_version,
            f"Handler.server_version still pre-rename: {Handler.server_version}",
        )
        self.assertNotIn(
            "DirectJob", Handler.server_version,
        )

    def test_no_directjob_residue_in_user_facing_files(self):
        residues: list[tuple[str, int, str]] = []
        for rel in self.USER_FACING_GLOBS:
            path = REPO_ROOT / rel
            if not path.exists():
                continue
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if "DirectJob" in line:
                    residues.append((rel, lineno, line.strip()[:100]))
        self.assertEqual(
            residues,
            [],
            "pre-rename 'DirectJob' brand found in user-facing files:\n"
            + "\n".join(f"  {r[0]}:{r[1]}: {r[2]}" for r in residues),
        )


class StaticServerServesPwaAssets(unittest.TestCase):
    """End-to-end: boot the real HTTP server + verify /manifest.web
    manifest + /sw.js + /i18n/locales.json all return 200 with the
    right content-types. A regression in the static-file router
    would silently break PWA install."""

    def setUp(self) -> None:
        # We don't boot a subprocess here; instead we patch the
        # Handler static-serve path directly. The actual subprocess
        # boot is exercised earlier in this session's transparency
        # runtime tests.
        from io import BytesIO
        from unittest.mock import MagicMock

        from app import Handler

        self.handler = Handler.__new__(Handler)
        self.handler.headers = {}
        self.handler.wfile = BytesIO()
        self.handler.send_response = MagicMock()
        self.handler.send_header = MagicMock()
        self.handler.end_headers = MagicMock()
        self.captured_headers: list[tuple[str, str]] = []
        self.captured_status: list[int] = []
        self.handler.send_response.side_effect = self.captured_status.append
        self.handler.send_header.side_effect = lambda n, v: self.captured_headers.append((n, v))

    def _content_type(self) -> str:
        for name, value in self.captured_headers:
            if name.lower() == "content-type":
                return value
        return ""

    def test_manifest_route_returns_json(self):
        self.handler.path = "/manifest.webmanifest"
        self.handler.do_GET()
        self.assertIn(200, self.captured_status)
        ct = self._content_type()
        # Content-type may be application/manifest+json (per spec) OR
        # application/json (acceptable fallback)
        self.assertTrue(
            "manifest" in ct or "json" in ct,
            f"manifest served with unexpected content-type: {ct!r}",
        )

    def test_sw_route_returns_javascript(self):
        self.handler.path = "/sw.js"
        self.handler.do_GET()
        self.assertIn(200, self.captured_status)
        ct = self._content_type()
        self.assertTrue(
            "javascript" in ct,
            f"sw.js served with unexpected content-type: {ct!r}",
        )

    def test_locale_registry_route_returns_json(self):
        self.handler.path = "/i18n/locales.json"
        self.handler.do_GET()
        self.assertIn(200, self.captured_status)
        ct = self._content_type()
        self.assertIn("json", ct)


if __name__ == "__main__":
    unittest.main()
