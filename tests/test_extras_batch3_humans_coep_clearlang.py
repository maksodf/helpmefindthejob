# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Extras batch 3 (2026-05-23): humans.txt, /clear-lang,
forgot-password BreadcrumbList, theme-color media queries, COEP +
Vary: Origin headers.

Six small but visible quality lifts, mostly response-header /
markup additions. Each is independently low-risk and gets a
focused regression check."""

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
STATIC = ROOT / "static"


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
    except OSError as error:
        raise unittest.SkipTest("local port binding is blocked by the sandbox") from error
    port = int(sock.getsockname()[1])
    sock.close()
    return port


class StaticAssetsBatch3(unittest.TestCase):
    def test_humans_txt_exists_and_has_team_section(self) -> None:
        path = STATIC / "humans.txt"
        self.assertTrue(path.is_file(), "humans.txt missing")
        text = path.read_text(encoding="utf-8")
        self.assertIn("/* TEAM */", text)
        self.assertIn("support@helpmefindthejob.org", text)
        self.assertIn("Apache-2.0", text)
        self.assertIn("Commons Conservancy", text)

    def test_forgot_password_pages_have_breadcrumb_jsonld(self) -> None:
        for filename, page_name in (
            ("forgot-password.html", "Forgot password"),
            ("forgot-password.de.html", "Passwort vergessen"),
        ):
            with self.subTest(filename=filename):
                src = (STATIC / filename).read_text(encoding="utf-8")
                self.assertIn('"@type": "BreadcrumbList"', src)
                self.assertIn(page_name, src)

    def test_index_has_theme_color_for_light_and_dark(self) -> None:
        src = (STATIC / "index.html").read_text(encoding="utf-8")
        self.assertIn(
            'media="(prefers-color-scheme: light)"',
            src,
            "index.html must declare light-mode theme-color",
        )
        self.assertIn(
            'media="(prefers-color-scheme: dark)"',
            src,
            "index.html must declare dark-mode theme-color",
        )


class LiveResponseBatch3(unittest.TestCase):
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

    def _request(
        self, method: str, path: str, *, headers: dict | None = None
    ) -> tuple[int, list[tuple[str, str]], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request(method, path, headers=headers or {})
        resp = conn.getresponse()
        try:
            return resp.status, resp.getheaders(), resp.read()
        finally:
            conn.close()

    def test_humans_txt_served_with_text_plain(self) -> None:
        status, headers, body = self._request("GET", "/humans.txt")
        self.assertEqual(status, 200)
        ct = next((v for k, v in headers if k.lower() == "content-type"), "")
        self.assertIn("text/plain", ct)
        self.assertIn(b"TEAM", body)

    def test_clear_lang_redirects_home_and_clears_cookie(self) -> None:
        status, headers, _body = self._request("GET", "/clear-lang")
        self.assertEqual(status, 303)
        loc = next((v for k, v in headers if k.lower() == "location"), "")
        self.assertEqual(loc, "/")
        # Find the Set-Cookie that clears lang
        clear_cookies = [
            v for k, v in headers if k.lower() == "set-cookie" and v.startswith("lang=")
        ]
        self.assertTrue(
            clear_cookies,
            "/clear-lang must emit a Set-Cookie clearing lang",
        )
        self.assertIn("Max-Age=0", clear_cookies[0])

    def test_coep_header_is_require_corp(self) -> None:
        _status, headers, _body = self._request("GET", "/api/health")
        coep = next((v for k, v in headers if k.lower() == "cross-origin-embedder-policy"), "")
        self.assertEqual(
            coep,
            "require-corp",
            "COEP must be require-corp to enable cross-origin isolation",
        )

    def test_vary_origin_present(self) -> None:
        _status, headers, _body = self._request("GET", "/api/health")
        vary_values = [v for k, v in headers if k.lower() == "vary"]
        joined = ", ".join(vary_values)
        self.assertIn(
            "Origin",
            joined,
            "Every response must Vary: Origin so a CDN can't cross-pollinate CORS state",
        )

    def test_forgot_password_renders_with_breadcrumb(self) -> None:
        _status, _headers, body = self._request("GET", "/forgot-password")
        self.assertIn(b"BreadcrumbList", body)


if __name__ == "__main__":
    unittest.main()
