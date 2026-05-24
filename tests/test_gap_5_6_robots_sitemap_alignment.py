# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""GAPs 5 + 6 (post-self-audit, 2026-05-23): robots.txt and
sitemap.xml must stay aligned with the actual indexable surfaces
after the AUDIT-22 / 26 / 27 / 37 changes.

* GAP-5: ``/csp-report`` must be in ``Disallow:``. POST-only, never
  crawled, but defence in depth.
* GAP-6: the dynamic sitemap.xml must NOT include any surface that
  ``Disallow:`` blocks — ``/forgot-password`` (noindex), ``/admin``
  (admin only), the path-token redirects, ``/csp-report``.

A sitemap that ships a URL while robots.txt blocks it is a SEO
contradiction Google flags in Search Console.
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


class RobotsAndSitemapAlignment(unittest.TestCase):
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

    def test_robots_disallows_csp_report(self) -> None:
        status, body = self._get("/robots.txt")
        self.assertEqual(status, 200)
        text = body.decode("utf-8")
        self.assertIn(
            "Disallow: /csp-report",
            text,
            "GAP-5: /csp-report must be in robots.txt Disallow even "
            "though the endpoint is POST-only.",
        )

    def test_robots_disallows_all_non_indexable_surfaces(self) -> None:
        status, body = self._get("/robots.txt")
        self.assertEqual(status, 200)
        text = body.decode("utf-8")
        for required in (
            "Disallow: /api/",
            "Disallow: /accept-invite/",
            "Disallow: /reset-password/",
            "Disallow: /forgot-password",
            "Disallow: /admin",
            "Disallow: /r/",
            "Disallow: /csp-report",
        ):
            with self.subTest(rule=required):
                self.assertIn(required, text)

    def test_sitemap_excludes_every_disallowed_surface(self) -> None:
        status, body = self._get("/sitemap.xml")
        self.assertEqual(status, 200)
        text = body.decode("utf-8")
        # GAP-6: sitemap must NOT list anything robots.txt blocks.
        # A sitemap entry for a disallowed URL is a SEO contradiction
        # that Google Search Console flags.
        for forbidden in (
            "/forgot-password",
            "/admin",
            "/csp-report",
            "/accept-invite",
            "/reset-password",
            "/r/",
        ):
            with self.subTest(forbidden=forbidden):
                # /reset-password is a prefix of /reset-password-form
                # etc — but we don't have any such page so substring
                # match is safe enough here.
                self.assertNotIn(
                    forbidden,
                    text,
                    f"GAP-6: sitemap.xml lists {forbidden!r}, which is "
                    "robots-Disallowed. Either drop it from the sitemap "
                    "or open it for indexing — never both at once.",
                )

    def test_sitemap_includes_every_indexable_surface(self) -> None:
        status, body = self._get("/sitemap.xml")
        self.assertEqual(status, 200)
        text = body.decode("utf-8")
        for indexable in (
            "<loc>http://127.0.0.1:",  # any URL — sitemap must have entries
            "/help",
            "/changelog",
            "/status",
            "/privacy",
            "/terms",
            "/data-retention",
            "/impressum",
        ):
            with self.subTest(indexable=indexable):
                self.assertIn(
                    indexable,
                    text,
                    f"GAP-6: sitemap.xml missing {indexable!r}.",
                )


if __name__ == "__main__":
    unittest.main()
