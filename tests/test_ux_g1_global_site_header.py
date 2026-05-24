# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""UX-G1 + G2 (2026-05-23, tasks #89/#90): the global site header.

Pre-fix: every public content page had only a per-page
"← Back to Helpmefindthejob" link as the way back, and the
language switcher lived footer-only — users high on a page never
saw it.

Post-fix: a slim sticky header on every public content surface
(legal, /help, /status, /changelog, /api/docs, /forgot-password,
404). Brand mark + wordmark on the left, primary nav in the
middle (Help / Status / API / Changelog), language switcher
on the right.

NOT injected on the SPA shell (`/`, `/admin`, etc.) because the
SPA has its own in-app `.topbar` with cmdK + view-title — a
second header above it would clutter the canvas.

This file is the regression guard.
"""

from __future__ import annotations

import http.client
import os
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


class GlobalSiteHeader(unittest.TestCase):
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

    def _get(self, path: str, *, lang: str | None = None) -> tuple[int, str]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        headers = {}
        if lang:
            headers["Accept-Language"] = lang
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        try:
            return resp.status, resp.read().decode("utf-8")
        finally:
            conn.close()

    PUBLIC_PAGES_WITH_HEADER = [
        "/help",
        "/status",
        "/changelog",
        "/api/docs",
        "/privacy",
        "/terms",
        "/impressum",
        "/data-retention",
        "/forgot-password",
    ]

    def test_every_public_content_page_has_global_header(self) -> None:
        for path in self.PUBLIC_PAGES_WITH_HEADER:
            with self.subTest(path=path):
                _status, body = self._get(path)
                self.assertIn(
                    'class="site-header"',
                    body,
                    f"UX-G1 regression: {path} is missing the global "
                    "site-header. _inject_html_header wasn't called or "
                    "the path-based exclusion is too broad.",
                )

    def test_404_page_has_global_header(self) -> None:
        status, body = self._get("/this-url-definitely-does-not-exist")
        self.assertEqual(status, 404)
        self.assertIn(
            'class="site-header"',
            body,
            "UX-G1 regression: 404 page missing global header. "
            "_send_html_404 must call _inject_html_header.",
        )

    def test_spa_root_does_not_get_global_header(self) -> None:
        """The SPA shell has its own in-app topbar. The global
        header would stack on top of it — clutter."""

        _status, body = self._get("/")
        self.assertNotIn(
            'class="site-header"',
            body,
            "UX-G1 regression: SPA shell (/) is now getting the global "
            "header injected. The SPA has its own .topbar; this would "
            "create a duplicate nav. The serve_static path-based check "
            "(candidate.name != 'index.html') is broken.",
        )

    def test_spa_admin_route_does_not_get_global_header(self) -> None:
        _status, body = self._get("/admin")
        self.assertNotIn(
            'class="site-header"',
            body,
            "UX-G1 regression: /admin (SPA route) is now getting the global header injected.",
        )

    def test_header_carries_primary_nav_in_english(self) -> None:
        _status, body = self._get("/help")
        for label in ("Help", "Status", "API", "Changelog"):
            with self.subTest(label=label):
                self.assertIn(
                    f">{label}<",
                    body,
                    f"UX-G1 regression: EN nav label '{label}' missing from the header on /help.",
                )

    def test_header_translates_nav_in_de(self) -> None:
        """The header is built per-language; /help?lang=de must
        render the DE nav labels."""

        _status, body = self._get("/help?lang=de")
        # Hilfe and Änderungen are the DE-specific labels — Status
        # and API stay the same string in both bundles.
        self.assertIn(
            ">Hilfe<",
            body,
            "UX-G1 regression: DE nav label 'Hilfe' missing on "
            "/help?lang=de. _build_site_header(lang='de') broken.",
        )
        self.assertIn(
            ">Änderungen<",
            body,
            "UX-G1 regression: DE nav label 'Änderungen' missing on /help?lang=de.",
        )

    def test_g2_language_switcher_in_header_not_only_footer(self) -> None:
        _status, body = self._get("/help")
        # UX-G2: language switcher must live in the header too, not
        # only in the footer. Probe by class name.
        self.assertIn(
            'class="site-header-langswitch"',
            body,
            "UX-G2 regression: site-header-langswitch missing — the "
            "language switcher only lives in the footer again.",
        )

    def test_brand_mark_is_link_to_home(self) -> None:
        _status, body = self._get("/help")
        self.assertIn(
            'class="site-header-brand" href="/"',
            body,
            "UX-G1 regression: brand mark missing or doesn't link "
            "to /. Brand must be the canonical home affordance.",
        )

    def test_header_is_idempotent_no_double_injection(self) -> None:
        _status, body = self._get("/help")
        # Two occurrences would mean double-injection. We expect
        # exactly one site-header.
        self.assertEqual(
            body.count('class="site-header"'),
            1,
            "UX-G1 regression: site-header injected more than once. "
            "_inject_html_header idempotency check broken.",
        )


if __name__ == "__main__":
    unittest.main()
