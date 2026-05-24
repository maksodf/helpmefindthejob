# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""AUDIT-23 + AUDIT-24 + 2026-05-23 /admin/* extension.

Three related fallback handlers all hardened in the same surface
sweep:

* **AUDIT-23 — OPTIONS preflight**: pre-fix, every OPTIONS request
  returned ``501 Not Implemented`` from ``BaseHTTPRequestHandler``,
  breaking cross-origin POSTs with custom headers (Content-Type:
  application/json, X-CSRF-Token). Post-fix: 204 with explicit
  CORS headers for allow-listed origins; bare 204 for unknown.

* **AUDIT-24 — branded 404 HTML**: pre-fix, visitors who mistyped a
  URL got either the Python default error page or a JSON 404 body.
  Both unacceptable on a public-facing civic-commons project.
  Post-fix: bilingual HTML page mirroring the legal-page chrome,
  Cache-Control: no-store, Vary: Accept-Language, Cookie.

* **/admin/* subpath 403**: pre-extension, only the literal /admin
  path got the GAP-3 server-side 403 for non-admin signed-in
  users. /admin/users (and any other subpath) fell through to
  serve_static and returned a plain 404, leaking that /admin is a
  real route while only the exact match was protected.
"""

from __future__ import annotations

import http.client
import json
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


class FallbackHandlers(unittest.TestCase):
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
    ) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request(method, path, headers=headers or {})
        resp = conn.getresponse()
        try:
            return resp.status, dict(resp.getheaders()), resp.read()
        finally:
            conn.close()

    # ---------- AUDIT-23 — OPTIONS preflight ----------

    def test_options_with_allowed_origin_returns_204_with_cors_headers(self) -> None:
        status, headers, body = self._request(
            "OPTIONS",
            "/api/auth/forgot-password",
            headers={"Origin": "https://helpmefindthejob.org"},
        )
        self.assertEqual(status, 204, "AUDIT-23: OPTIONS should be 204, not 501")
        self.assertEqual(body, b"")
        self.assertEqual(
            headers.get("Access-Control-Allow-Origin"),
            "https://helpmefindthejob.org",
        )
        self.assertEqual(headers.get("Access-Control-Allow-Credentials"), "true")
        self.assertIn("GET", headers.get("Access-Control-Allow-Methods", ""))
        self.assertIn("POST", headers.get("Access-Control-Allow-Methods", ""))
        self.assertIn("OPTIONS", headers.get("Access-Control-Allow-Methods", ""))
        self.assertIn("X-CSRF-Token", headers.get("Access-Control-Allow-Headers", ""))
        self.assertEqual(headers.get("Access-Control-Max-Age"), "86400")

    def test_options_with_disallowed_origin_returns_bare_204(self) -> None:
        status, headers, body = self._request(
            "OPTIONS",
            "/api/auth/forgot-password",
            headers={"Origin": "https://attacker.example"},
        )
        self.assertEqual(status, 204)
        self.assertEqual(body, b"")
        # No CORS allow-origin echo for the attacker — browser will reject
        self.assertNotIn(
            "Access-Control-Allow-Origin",
            headers,
            "AUDIT-23: must NOT echo back an unrecognised Origin",
        )

    def test_options_with_no_origin_still_204(self) -> None:
        status, _h, _body = self._request("OPTIONS", "/api/health")
        self.assertEqual(status, 204)

    # ---------- AUDIT-24 — branded 404 HTML ----------

    def test_unknown_url_returns_branded_html_404(self) -> None:
        status, headers, body = self._request("GET", "/this-does-not-exist-deliberately")
        self.assertEqual(status, 404)
        self.assertIn(
            "text/html",
            headers.get("Content-Type", ""),
            "AUDIT-24: 404 should be HTML, not JSON or plain text",
        )
        self.assertEqual(headers.get("Cache-Control"), "no-store")
        self.assertIn("Accept-Language", headers.get("Vary", ""))
        self.assertIn(b"This page doesn", body)
        # Site footer must be injected on the 404 too
        self.assertIn(b'class="site-footer"', body)
        # No-index meta so Google doesn't index error pages
        self.assertIn(b'name="robots" content="noindex,nofollow"', body)

    def test_unknown_url_with_accept_language_de_returns_german_404(self) -> None:
        status, _h, body = self._request(
            "GET",
            "/this-does-not-exist-deliberately",
            headers={"Accept-Language": "de-DE,de;q=0.9"},
        )
        self.assertEqual(status, 404)
        self.assertIn(b"Diese Seite gibt es nicht", body)
        self.assertIn(b'<html lang="de">', body)
        # English heading must NOT bleed into DE 404
        self.assertNotIn(b"This page doesn", body)

    def test_api_endpoints_still_return_json_404(self) -> None:
        # /api/* paths don't go through serve_static; their JSON 404
        # behaviour must be preserved for machine consumers.
        status, headers, _body = self._request("GET", "/api/totally-bogus-endpoint")
        # Either 404 (route handler) or 401 (auth-required) — both are
        # API behaviours, NOT the HTML 404 page.
        self.assertIn(status, (401, 404))
        self.assertIn("json", headers.get("Content-Type", "").lower())

    # ---------- /admin/* subpath 403 ----------

    def test_admin_subpath_serves_spa_when_logged_out(self) -> None:
        # /admin/users when logged out — falls through to serve_static
        # which 404s today (no such file). Logged-out users see the
        # branded HTML 404, not the bare server default.
        status, _h, body = self._request("GET", "/admin/users")
        # 404 because /admin/* doesn't exist as a file
        self.assertEqual(status, 404)
        # But it IS the branded 404 (AUDIT-24), not the default
        self.assertIn(b"site-footer", body)

    def test_admin_subpath_serves_403_for_signed_in_non_admin(self) -> None:
        # Bootstrap admin
        status, headers, body = self._request(
            "POST",
            "/api/auth/register",
        )
        # Re-do via proper register flow
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request(
            "POST",
            "/api/auth/register",
            body=json.dumps(
                {"email": "subpath-admin@example.invalid", "password": "very-strong-password-1234"}
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        if resp.status not in (200, 201):
            resp.read()
            conn.close()
            self.skipTest(f"bootstrap registration disabled (status {resp.status})")
        payload = json.loads(resp.read().decode("utf-8"))
        admin_cookie = None
        for k, v in resp.getheaders():
            if k.lower() == "set-cookie":
                for part in v.split(", "):
                    if part.startswith("helpmefindthejob_session="):
                        admin_cookie = part.split(";", 1)[0]
                        break
        admin_csrf = payload["user"]["csrfToken"]
        conn.close()

        # Create a non-admin member
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request(
            "POST",
            "/api/admin/users",
            body=json.dumps(
                {
                    "email": "subpath-member@example.invalid",
                    "password": "very-strong-password-5678",
                    "role": "member",
                }
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Cookie": admin_cookie,
                "X-CSRF-Token": admin_csrf,
            },
        )
        create_resp = conn.getresponse()
        if create_resp.status not in (200, 201):
            create_resp.read()
            conn.close()
            self.skipTest("admin/users create failed")
        create_resp.read()
        conn.close()

        # Login as member
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request(
            "POST",
            "/api/auth/login",
            body=json.dumps(
                {
                    "email": "subpath-member@example.invalid",
                    "password": "very-strong-password-5678",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        login_resp = conn.getresponse()
        login_resp.read()
        member_cookie = None
        for k, v in login_resp.getheaders():
            if k.lower() == "set-cookie":
                for part in v.split(", "):
                    if part.startswith("helpmefindthejob_session="):
                        member_cookie = part.split(";", 1)[0]
                        break
        conn.close()

        # Hit /admin/users with member session → expect 403
        status, _h, body = self._request(
            "GET",
            "/admin/users",
            headers={"Cookie": member_cookie},
        )
        self.assertEqual(
            status,
            403,
            "/admin/* subpath must 403 for non-admin (was 404 pre-extension)",
        )
        self.assertIn(b"Admin access required", body)

        # And /admin (exact) — same behaviour
        status, _h, body = self._request(
            "GET",
            "/admin",
            headers={"Cookie": member_cookie},
        )
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
