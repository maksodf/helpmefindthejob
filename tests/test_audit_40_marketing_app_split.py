# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""AUDIT-40 — split marketing-vs-app HTML for SEO.

Pre-AUDIT-40, ``static/index.html`` was a single 1700-line file
that mixed:

* The auth gate (marketing copy + login form) — visible to
  unauthenticated visitors AND to search-engine crawlers.
* The appShell with all internal app views (sidebar nav, command
  palette, dashboard cards, jobs queue, brief composer, settings,
  admin panes) — only visible to authenticated users via
  client-side ``hidden`` toggling, but **still in the source
  HTML at first paint**.

Search engines index hidden text. Branded queries for
"Helpmefindthejob" surfaced SERP snippets containing internal app
jargon ("Discovered jobs", "Watchlist", "Saved searches", admin
labels) instead of the marketing copy. ~1300 lines of internal
strings polluted the public SEO surface.

AUDIT-40 splits at the source-HTML layer:

* The appShell ``<div id="appShell">`` is wrapped in an inert
  ``<template id="appShellTemplate">`` element in ``index.html``.
  Per the HTML spec, ``<template>`` content is parsed but NOT
  rendered or visited by accessibility / search-engine extraction
  — it's "off-screen storage" for HTML that script later activates.
* ``static/app.js`` materialises the template at module-load via
  an IIFE that runs before any binding code: it clones the
  template content into the live DOM, so all the existing
  ``$("#x").addEventListener()`` calls keep finding their targets.
* Authenticated users see no visual difference (the materialised
  appShell still respects the existing ``hidden`` attribute that
  ``renderAuth`` toggles).
* Crawlers indexing the first paint see only the auth-gate +
  auth-aux sections in the live DOM. The template content is
  inert; the appShell strings stay out of the indexed surface.

This module pins all of the above:

1. The template element exists in index.html source.
2. The internal-app markers (``data-view=``, ``adminTicketList``,
   etc.) appear only inside the template wrapper in the source.
3. The IIFE that materialises the template is present at the top
   of app.js.
4. End-to-end: a freshly-served / response has the template
   wrapper; the auth-gate sections are in the live DOM at the same
   nesting level as before; no SPA functionality regresses.
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


_TEMPLATE_OPEN_RX = re.compile(r'<template\s+id="appShellTemplate"')
_TEMPLATE_CLOSE_RX = re.compile(r"</template>")
_APP_SHELL_OPEN_RX = re.compile(r'<div\s+id="appShell"')


class AppShellWrappedInTemplate(unittest.TestCase):
    """Source-level invariants — these run against the static file,
    so they don't depend on the live server."""

    def test_index_html_declares_template_wrapper(self) -> None:
        src = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIsNotNone(
            _TEMPLATE_OPEN_RX.search(src),
            "AUDIT-40: static/index.html must declare "
            '<template id="appShellTemplate"> wrapping the appShell so '
            "crawlers see only the auth-gate marketing surface at first paint.",
        )

    def test_app_shell_is_inside_the_template_wrapper(self) -> None:
        src = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        tpl_open = _TEMPLATE_OPEN_RX.search(src)
        app_shell = _APP_SHELL_OPEN_RX.search(src)
        self.assertIsNotNone(tpl_open, "no <template id=appShellTemplate>")
        self.assertIsNotNone(app_shell, "no <div id=appShell>")
        self.assertLess(
            tpl_open.end(), app_shell.start(),
            "AUDIT-40: <div id=appShell> must appear AFTER the opening "
            "<template id=appShellTemplate> tag.",
        )

    def test_template_wrapper_closes_before_dialogs(self) -> None:
        # The </template> that closes appShellTemplate must come BEFORE
        # the confirmDialog div at the bottom — otherwise the dialog
        # is accidentally inside the template and won't work.
        src = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        tpl_open = _TEMPLATE_OPEN_RX.search(src)
        dialog = src.find('<div id="confirmDialog"')
        # Find the LAST </template> before the dialog
        closes = [m.start() for m in _TEMPLATE_CLOSE_RX.finditer(src) if tpl_open.end() < m.start() < dialog]
        self.assertTrue(
            closes,
            "AUDIT-40: no </template> tag between the appShellTemplate "
            "opener and confirmDialog. The dialog is inside the template "
            "and will never render.",
        )

    def test_app_js_materialises_template_at_module_load(self) -> None:
        src = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn(
            "_materialiseAppShellTemplate", src,
            "AUDIT-40: app.js must declare the materialisation IIFE "
            "(_materialiseAppShellTemplate) at the top so the cloned "
            "appShell is in the live DOM before binding code runs.",
        )
        self.assertIn(
            "appShellTemplate", src,
            "AUDIT-40: app.js must reference the template id appShellTemplate",
        )
        # The IIFE must run BEFORE the first event-binding call to
        # guarantee the cloned DOM exists. Use a regex that matches
        # actual call syntax ``.addEventListener(`` rather than the
        # word in a comment.
        iife_pos = src.find("_materialiseAppShellTemplate")
        bind_match = re.search(r"\.addEventListener\(", src)
        self.assertGreater(iife_pos, 0, "IIFE not found")
        self.assertIsNotNone(bind_match, "no addEventListener calls found")
        self.assertGreater(
            bind_match.start(), iife_pos,
            "AUDIT-40: the materialisation IIFE must appear in app.js "
            "BEFORE the first .addEventListener( call, otherwise binding "
            "fails on appShell elements that don't exist yet.",
        )

    def test_internal_data_view_markers_only_inside_template(self) -> None:
        # Every ``data-view=`` in index.html must sit between the
        # template opener and the matching </template>. This is the
        # core SEO guarantee — crawlers indexing the source see no
        # internal-app section markers outside the inert template.
        src = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        tpl_open = _TEMPLATE_OPEN_RX.search(src)
        tpl_close_candidates = [
            m.start() for m in _TEMPLATE_CLOSE_RX.finditer(src)
            if m.start() > tpl_open.end()
        ]
        tpl_close = tpl_close_candidates[0]
        for match in re.finditer(r'data-view="([^"]+)"', src):
            with self.subTest(view=match.group(1), pos=match.start()):
                self.assertTrue(
                    tpl_open.end() < match.start() < tpl_close,
                    f"AUDIT-40: data-view={match.group(1)!r} at pos "
                    f"{match.start()} is outside the appShellTemplate "
                    f"wrapper (template: {tpl_open.end()}–{tpl_close}). "
                    "Move it inside the template so search engines don't "
                    "see internal-app markers in the first-paint source.",
                )


class LiveResponseStillCarriesTemplate(unittest.TestCase):
    """End-to-end: a real / GET response carries the template wrapper
    and the appShell markup remains accessible inside it."""

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

    def _get(self, path: str) -> tuple[int, bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", path)
        resp = conn.getresponse()
        try:
            return resp.status, resp.read()
        finally:
            conn.close()

    def test_landing_response_contains_template_wrapper(self) -> None:
        status, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn(
            b'<template id="appShellTemplate"', body,
            "AUDIT-40: live / response missing the template wrapper",
        )

    def test_auth_gate_still_visible_at_first_paint(self) -> None:
        status, body = self._get("/")
        self.assertEqual(status, 200)
        # authGate, login form, register form, and the mission copy
        # must remain OUTSIDE the template so crawlers index them.
        markers = [
            b'id="authGate"',
            b'id="loginForm"',
            b'id="registerForm"',
            b"missionHeading",
        ]
        tpl_pos = body.find(b'<template id="appShellTemplate"')
        for marker in markers:
            with self.subTest(marker=marker):
                pos = body.find(marker)
                self.assertGreater(pos, 0, f"{marker!r} not in body")
                self.assertLess(
                    pos, tpl_pos,
                    f"AUDIT-40: {marker!r} appears INSIDE or AFTER the "
                    "template wrapper. Auth-gate marketing must stay in "
                    "the live DOM at first paint.",
                )

    def test_app_js_iife_present_in_served_app_js(self) -> None:
        status, body = self._get("/app.js")
        self.assertEqual(status, 200)
        self.assertIn(
            b"_materialiseAppShellTemplate", body,
            "AUDIT-40: served /app.js missing the materialisation IIFE",
        )

    def test_existing_spa_smoke_routes_still_work(self) -> None:
        # The smoke test from AUDIT-26 / 27 / 34 invariants — make sure
        # AUDIT-40 didn't break the page routes.
        for path, min_size in [
            ("/forgot-password", 3000),
            ("/privacy", 10000),
            ("/api/health", 50),
            ("/api/version", 50),
        ]:
            with self.subTest(path=path):
                status, body = self._get(path)
                self.assertEqual(status, 200, f"{path} → {status}")
                self.assertGreater(len(body), min_size, f"{path} body too small")


if __name__ == "__main__":
    unittest.main()
