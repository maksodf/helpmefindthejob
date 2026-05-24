# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""UX-F1 (2026-05-23, task #88): light theme — the single biggest
remaining visible gap in the audit.

Pre-fix: the project shipped dark-only. Users on a bright office
monitor / public-sector reviewers visiting in a daylit room got an
eye-straining dark-on-dark UI with no way to switch.

Post-fix: full light palette with three layered selection mechanisms:
1. Default: dark (existing behaviour preserved — no surprise).
2. `@media (prefers-color-scheme: light)`: auto-apply light if the
   user's OS reports light AND they haven't explicitly chosen dark.
3. `[data-theme="light"]` / `[data-theme="dark"]`: explicit override
   set by the toggle button. Persisted via cookie (SSR) + localStorage
   (client fallback).

Server-side:
* `_resolve_user_theme()` reads ?theme= or `theme` cookie.
* `_inject_html_theme_attr()` adds `data-theme="…"` to `<html>` when
  the user has an explicit choice — no FOUC.

Client-side:
* `/theme-toggle.js` (3.7 KB) handles the toggle button click, cycles
  between dark and light, writes the cookie + localStorage.
* The button itself (#siteHeaderThemeToggle) lives in the global
  header and shows a sun icon in light mode, moon in dark.

This file is the regression guard for the whole architecture.
"""

from __future__ import annotations

import http.client
import os
import re
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
    except OSError as error:
        raise unittest.SkipTest("local port binding is blocked by the sandbox") from error
    port = int(sock.getsockname()[1])
    sock.close()
    return port


class LightThemeStaticContract(unittest.TestCase):
    """Static checks on CSS + JS + i18n — no server boot."""

    def setUp(self) -> None:
        self.styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")
        self.styles_min = (ROOT / "static" / "styles.min.css").read_text(encoding="utf-8")
        self.theme_js = (ROOT / "static" / "theme-toggle.js").read_text(encoding="utf-8")
        self.sw_js = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")

    def test_light_palette_via_data_theme_attribute(self) -> None:
        self.assertIn(
            ':root[data-theme="light"]',
            self.styles,
            "UX-F1 regression: explicit [data-theme='light'] selector "
            "missing. Manual theme toggle relies on this.",
        )

    def test_light_palette_via_prefers_color_scheme_media_query(self) -> None:
        # We require BOTH the @media query and the :root selector
        # excluding [data-theme="dark"] so explicit-dark wins.
        self.assertIn(
            "@media (prefers-color-scheme: light)",
            self.styles,
            "UX-F1 regression: prefers-color-scheme: light media query "
            "removed. Users with light OS settings need automatic light "
            "theme without having to click the toggle.",
        )
        rx = re.compile(
            r"@media\s*\(prefers-color-scheme:\s*light\)\s*\{\s*"
            r':root:not\(\[data-theme="dark"\]\)\s*\{',
            re.MULTILINE,
        )
        self.assertIsNotNone(
            rx.search(self.styles),
            "UX-F1 regression: the prefers-color-scheme light block "
            "no longer excludes [data-theme='dark']. Explicit dark must "
            "win over OS preference.",
        )

    def test_color_scheme_advertises_both_themes(self) -> None:
        # color-scheme: light dark; lets native form controls /
        # scrollbars adapt.
        self.assertIn(
            "color-scheme: light dark",
            self.styles,
            "UX-F1 regression: :root color-scheme must advertise both light and dark.",
        )

    def test_theme_toggle_script_exists_and_is_csp_safe(self) -> None:
        # Must not assign to .innerHTML (CSP / XSS).
        innerhtml_rx = re.compile(r"\.innerHTML\s*=")
        self.assertIsNone(
            innerhtml_rx.search(self.theme_js),
            "UX-F1: theme-toggle.js must not assign to .innerHTML.",
        )
        # Must wire to the header toggle button.
        self.assertIn(
            "siteHeaderThemeToggle",
            self.theme_js,
            "theme-toggle.js must target #siteHeaderThemeToggle.",
        )
        # Must persist via cookie + localStorage.
        self.assertIn("theme=", self.theme_js)
        self.assertIn("dj_theme", self.theme_js)

    def test_service_worker_caches_theme_toggle_script(self) -> None:
        self.assertIn(
            '"/theme-toggle.js"',
            self.sw_js,
            "UX-F1: theme-toggle.js missing from SW SHELL_PATHS. "
            "Public pages need it cached for offline-first.",
        )

    def test_uptime_bar_empty_state_visible_in_light_mode(self) -> None:
        # The earlier rgba(255,255,255,0.06) empty cells vanished
        # against the white surface. Fix uses the design-token
        # --surface-3 (light gray) + a border so cells stay visible
        # in both themes.
        self.assertNotIn(
            ".uptime-cell--empty { background: rgba(255, 255, 255, 0.06); }",
            self.styles,
            "UX-F1 regression: uptime empty cells back to white-overlay "
            "background, which is invisible in light mode.",
        )


class LightThemeRuntimeContract(unittest.TestCase):
    """End-to-end: boot the server, confirm the theme cookie/query
    roundtrip injects data-theme on <html>."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TemporaryDirectory()
        cls.port = _free_port()
        env = {
            **os.environ,
            "HELPMEFINDTHEJOB_DATA_DIR": cls._tmp.name,
            "HELPMEFINDTHEJOB_AUDIT_SALT": "A" * 43 + "=",
        }
        cls._process = subprocess.Popen(
            [sys.executable, str(ROOT / "app.py"), "--port", str(cls.port)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        cls._wait_for_health()

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._process.poll() is None:
            cls._process.terminate()
            try:
                cls._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls._process.kill()
                cls._process.wait()
        for stream in (cls._process.stdout, cls._process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except Exception:  # noqa: BLE001
                    pass
        cls._tmp.cleanup()

    @classmethod
    def _wait_for_health(cls) -> None:
        for _ in range(60):
            try:
                conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=0.5)
                conn.request("GET", "/api/health")
                resp = conn.getresponse()
                ok = resp.status == 200
                resp.read()
                conn.close()
                if ok:
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError(f"server did not become healthy on port {cls.port}")

    def _get(self, path: str, *, cookie: str | None = None) -> tuple[int, str]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        try:
            return resp.status, resp.read().decode("utf-8")
        finally:
            conn.close()

    def test_no_theme_cookie_no_data_theme_attr(self) -> None:
        _status, body = self._get("/help")
        # The default state lets the @media block decide.
        # Therefore <html> must NOT carry data-theme.
        self.assertNotIn(
            "data-theme=",
            body[:300],  # match in the <html> open tag
            "UX-F1 regression: data-theme attribute injected even "
            "without explicit theme choice. This breaks the system-"
            "preference auto-detection — the @media block can no "
            "longer light up.",
        )

    def test_theme_light_cookie_sets_data_theme_on_html(self) -> None:
        _status, body = self._get("/help", cookie="theme=light")
        self.assertIn(
            'data-theme="light"',
            body[:400],
            "UX-F1 regression: theme=light cookie not honoured. "
            "Server must inject data-theme on <html> via "
            "_inject_html_theme_attr.",
        )

    def test_theme_dark_query_sets_data_theme_on_html(self) -> None:
        _status, body = self._get("/help?theme=dark")
        self.assertIn(
            'data-theme="dark"',
            body[:400],
            "UX-F1 regression: ?theme=dark query param not honoured.",
        )

    def test_theme_query_beats_cookie(self) -> None:
        # Cookie says light, query says dark — query wins.
        _status, body = self._get("/help?theme=dark", cookie="theme=light")
        self.assertIn('data-theme="dark"', body[:400])
        self.assertNotIn('data-theme="light"', body[:400])

    def test_invalid_theme_value_is_ignored(self) -> None:
        _status, body = self._get("/help?theme=hotpink")
        self.assertNotIn("data-theme=", body[:300])

    def test_theme_toggle_button_in_global_header(self) -> None:
        _status, body = self._get("/help")
        self.assertIn(
            'id="siteHeaderThemeToggle"',
            body,
            "UX-F1 regression: theme toggle button missing from the global header.",
        )
        # Must have both icon variants — CSS flips visibility.
        self.assertIn("icon-moon", body)
        self.assertIn("icon-sun", body)

    def test_theme_toggle_script_loaded_by_header(self) -> None:
        _status, body = self._get("/help")
        self.assertIn(
            'src="/theme-toggle.js"',
            body,
            "UX-F1 regression: theme-toggle.js not loaded by the "
            "global header. Without the script, the toggle button "
            "does nothing.",
        )

    def test_theme_toggle_script_serves_200(self) -> None:
        status, body = self._get("/theme-toggle.js")
        self.assertEqual(status, 200)
        self.assertIn("siteHeaderThemeToggle", body)

    def test_404_page_gets_theme_attr_with_cookie(self) -> None:
        status, body = self._get("/this-does-not-exist", cookie="theme=light")
        self.assertEqual(status, 404)
        self.assertIn(
            'data-theme="light"',
            body[:400],
            "UX-F1 regression: 404 page misses the theme attribute "
            "injection — _send_html_404 must call "
            "_inject_html_theme_attr.",
        )

    def test_spa_shell_honours_theme_query_for_first_paint(self) -> None:
        """The SPA shell ALSO gets the data-theme injection so the
        first paint matches the user's cookie/query choice — no
        FOUC. The SPA's applyTheme() later reconciles with the
        user's profile preference if they differ. Pre-fix the SPA
        always painted in dark first, then flashed to the user's
        actual preference."""

        _status, body = self._get("/?theme=light")
        self.assertIn(
            'data-theme="light"',
            body[:400],
            "UX-F1 regression: SPA shell first-paint no longer "
            "honours the theme cookie/query. The user would see "
            "a flash of dark before applyTheme() runs.",
        )


if __name__ == "__main__":
    unittest.main()
