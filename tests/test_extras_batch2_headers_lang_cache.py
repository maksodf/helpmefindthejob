# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Extras batch 2 (2026-05-23): Permissions-Policy hardening + lang
cookie persistence + Cache-Control on static assets.

Three small but visible hardening sweeps, all in the response-header
layer:

* **Permissions-Policy** — extended from the original three locks
  (geolocation / microphone / camera) to also lock interest-cohort
  (Federated Learning of Cohorts), browsing-topics (Topics-API
  successor), fullscreen-by-default, accelerometer, gyroscope,
  magnetometer, usb, serial, midi, payment. A civic-commons project
  must explicitly opt out of ad-tracking signals.

* **Lang cookie persistence** — clicking the lang switcher's
  ``?lang=de`` used to work for the current request only; the next
  page fell back to Accept-Language because no cookie was set. Now
  ``?lang=de`` triggers ``Set-Cookie: lang=de; Path=/; Max-Age=1y``
  so the choice survives navigation. The cookie is preferred over
  Accept-Language by the existing _resolve_user_language() chain.

* **Cache-Control on static assets** — pre-fix, every page load
  re-downloaded /styles.css, /app.js, /forgot-password.js, and the
  /icons/* set because no Cache-Control was sent. Now tiered:
  HTML stays no-cache (per-request rendered), CSS/JS get 5-min
  revalidation, icons/fonts get 1-day cache.
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


class HeadersLangCacheExtras(unittest.TestCase):

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

    def _get(self, path: str, headers: dict | None = None) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", path, headers=headers or {})
        resp = conn.getresponse()
        try:
            return resp.status, dict(resp.getheaders()), resp.read()
        finally:
            conn.close()

    def _get_all_setcookies(self, path: str, headers: dict | None = None) -> list[str]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", path, headers=headers or {})
        resp = conn.getresponse()
        try:
            cookies: list[str] = []
            for k, v in resp.getheaders():
                if k.lower() == "set-cookie":
                    cookies.extend(v.split(", "))
            resp.read()
            return cookies
        finally:
            conn.close()

    # ---------- Permissions-Policy ----------

    def test_permissions_policy_opts_out_of_floc_and_topics(self) -> None:
        _status, headers, _body = self._get("/api/health")
        perms = headers.get("Permissions-Policy", "")
        for required in (
            "interest-cohort=()",
            "browsing-topics=()",
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "fullscreen=(self)",
            "accelerometer=()",
            "usb=()",
            "payment=()",
        ):
            with self.subTest(directive=required):
                self.assertIn(
                    required, perms,
                    f"Permissions-Policy missing {required!r}",
                )

    # ---------- Lang cookie persistence ----------

    def test_lang_query_de_sets_persistent_cookie(self) -> None:
        cookies = self._get_all_setcookies("/privacy?lang=de")
        lang_cookies = [c for c in cookies if c.startswith("lang=")]
        self.assertTrue(
            lang_cookies,
            "?lang=de must Set-Cookie: lang=de",
        )
        cookie = lang_cookies[0]
        self.assertIn("lang=de", cookie)
        self.assertIn("Path=/", cookie)
        self.assertIn("Max-Age=", cookie)
        # 1-year cookie — extract the Max-Age value and assert ≥ 30 days
        ma_match = [tok for tok in cookie.split(";") if "Max-Age=" in tok]
        self.assertTrue(ma_match)
        ma = int(ma_match[0].split("=", 1)[1].strip())
        self.assertGreaterEqual(
            ma, 30 * 86400,
            "lang cookie Max-Age should be ≥ 30 days for stickiness",
        )
        self.assertIn("SameSite=Lax", cookie)

    def test_lang_query_en_sets_lang_en_cookie(self) -> None:
        cookies = self._get_all_setcookies("/privacy?lang=en")
        lang_cookies = [c for c in cookies if c.startswith("lang=")]
        self.assertTrue(lang_cookies)
        self.assertIn("lang=en", lang_cookies[0])

    def test_no_lang_query_no_cookie_set(self) -> None:
        # Bare /privacy without ?lang= must NOT issue a lang cookie
        # (otherwise we'd lock a user into whatever their first
        # Accept-Language match was, defeating future switches).
        cookies = self._get_all_setcookies("/privacy")
        lang_cookies = [c for c in cookies if c.startswith("lang=")]
        self.assertFalse(
            lang_cookies,
            f"no ?lang= → no Set-Cookie lang; got {lang_cookies}",
        )

    def test_invalid_lang_query_no_cookie(self) -> None:
        # ?lang=fr is not a supported language; must not set a cookie
        cookies = self._get_all_setcookies("/privacy?lang=fr")
        lang_cookies = [c for c in cookies if c.startswith("lang=")]
        self.assertFalse(lang_cookies)

    # ---------- Cache-Control on static assets ----------

    def test_html_response_is_no_cache(self) -> None:
        _status, headers, _body = self._get("/privacy")
        cc = headers.get("Cache-Control", "")
        self.assertIn(
            "no-cache", cc.lower(),
            f"HTML must be no-cache (per-request rendered), got {cc!r}",
        )

    def test_css_response_has_short_max_age(self) -> None:
        _status, headers, _body = self._get("/styles.css")
        cc = headers.get("Cache-Control", "")
        self.assertIn("public", cc)
        self.assertIn("max-age=", cc)
        # Extract max-age and assert in [60, 3600] window
        for tok in cc.split(","):
            tok = tok.strip()
            if tok.startswith("max-age="):
                ma = int(tok.split("=", 1)[1])
                self.assertGreaterEqual(ma, 60, "CSS max-age too short")
                self.assertLessEqual(ma, 3600, "CSS max-age too long for active iteration")

    def test_js_response_has_short_max_age(self) -> None:
        _status, headers, _body = self._get("/forgot-password.js")
        cc = headers.get("Cache-Control", "")
        self.assertIn("max-age=", cc)

    def test_icon_response_has_day_max_age(self) -> None:
        _status, headers, _body = self._get("/favicon.ico")
        cc = headers.get("Cache-Control", "")
        self.assertIn("max-age=", cc)
        for tok in cc.split(","):
            tok = tok.strip()
            if tok.startswith("max-age="):
                ma = int(tok.split("=", 1)[1])
                self.assertGreaterEqual(ma, 3600, "icon max-age should be ≥ 1 hour")


if __name__ == "__main__":
    unittest.main()
