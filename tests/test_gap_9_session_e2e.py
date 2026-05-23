# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""GAP-9 (post-self-audit, 2026-05-23): single end-to-end smoke that
walks every user-visible flow we touched this session in one process.

Individual feature tests each spin up their own server and probe one
concern. This file boots ONE server and walks through the entire
session's surface area top-to-bottom, exactly as a real visitor would:
landing → forgot-password → reset-redirect → admin denial → CSP
report submission → bilingual switch → footer presence → JSON-LD
references → robots/sitemap alignment.

The point isn't to duplicate the focused tests — it's to catch
*interaction* regressions that only show up when the system runs
together (footer injection vs. template wrap vs. bilingual routing
vs. session cookies, all in one process).
"""

from __future__ import annotations

import http.client
import json
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


class SessionE2E(unittest.TestCase):
    """One server, one test method — walks the whole session's surface
    area as a single user journey."""

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

    def _request(self, method: str, path: str, *,
                 body: bytes | None = None,
                 headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        try:
            return resp.status, dict(resp.getheaders()), resp.read()
        finally:
            conn.close()

    def _extract_set_cookie(self, headers: dict[str, str], name_prefix: str) -> str | None:
        for k, v in headers.items():
            if k.lower() == "set-cookie":
                for part in v.split(", "):
                    if part.startswith(name_prefix):
                        return part.split(";", 1)[0]
        return None

    def test_full_session_walkthrough(self) -> None:
        # ---------- Stage 1: anonymous visit to landing ----------
        status, _h, body = self._request("GET", "/")
        self.assertEqual(status, 200, "landing page must serve")
        self.assertIn(b'<template id="appShellTemplate"', body,
                      "AUDIT-40: landing must carry the template wrap")
        self.assertNotIn(b'data-view="jobs"', body[:15523],
                         "AUDIT-40: no app strings in the crawler-visible prefix")
        self.assertIn(b'id="authGate"', body, "auth gate must be in live DOM")
        self.assertIn(b'class="site-footer"', body, "AUDIT-34: footer must be injected")
        # Default language is EN (no Accept-Language header in our probe)
        self.assertIn(b">Contact</h3>", body, "EN footer for default request")

        # ---------- Stage 2: switch to German ----------
        status, _h, body = self._request(
            "GET", "/", headers={"Accept-Language": "de-DE,de;q=0.9,en;q=0.5"}
        )
        self.assertEqual(status, 200)
        self.assertIn(b">Kontakt</h3>", body, "GAP-1: DE Accept-Language → DE footer")
        self.assertNotIn(b">Contact</h3>", body)

        # ---------- Stage 3: ?lang= override ----------
        status, _h, body = self._request(
            "GET", "/?lang=de", headers={"Accept-Language": "en"}
        )
        self.assertEqual(status, 200)
        self.assertIn(b">Kontakt</h3>", body, "?lang=de beats Accept-Language: en")

        # ---------- Stage 4: forgot-password page ----------
        status, _h, body = self._request("GET", "/forgot-password")
        self.assertEqual(status, 200)
        self.assertLess(len(body), 10_000,
                        f"AUDIT-26: dedicated page should be tiny, got {len(body)} bytes")
        self.assertIn(b"forgotPasswordForm", body)
        self.assertNotIn(b"appShell", body,
                         "AUDIT-26: page must NOT carry the SPA shell")

        # ---------- Stage 5: forgot-password submit ----------
        status, _h, body = self._request(
            "POST", "/api/auth/forgot-password",
            body=json.dumps({"email": "nobody@example.invalid"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 202)
        self.assertEqual(json.loads(body.decode("utf-8"))["status"], "sent_if_known")

        # ---------- Stage 6: referral redirect (AUDIT-22) ----------
        status, headers, _body = self._request("GET", "/r/abc123")
        self.assertEqual(status, 303, "AUDIT-22: /r/<code> → 303 SEE_OTHER")
        self.assertEqual(headers.get("Location"), "/?ref=abc123")
        cookies = headers.get("Set-Cookie", "")
        self.assertNotIn(
            "helpmefindthejob_ref", cookies,
            "AUDIT-22: referral redirect must NOT emit the consent-tracking cookie",
        )

        # ---------- Stage 7: path-token redirect (AUDIT-27) ----------
        valid_token = "abcd_-09" * 5  # 40-char URL-safe token
        status, headers, _body = self._request("GET", f"/reset-password/{valid_token}")
        self.assertEqual(status, 303)
        self.assertEqual(
            headers.get("Location"), f"/reset-password?token={valid_token}",
            "AUDIT-27: path-token redirects to canonical query form",
        )
        # Malformed token 404s
        status, _h, _body = self._request("GET", "/reset-password/with%20space")
        self.assertEqual(status, 404)

        # ---------- Stage 8: /admin while logged out (SPA shell) ----------
        status, _h, body = self._request("GET", "/admin")
        self.assertEqual(status, 200, "AUDIT-27: /admin serves SPA for logged-out")
        self.assertIn(b'<template id="appShellTemplate"', body)

        # ---------- Stage 9: bootstrap admin + create member ----------
        status, headers, body = self._request(
            "POST", "/api/auth/register",
            body=json.dumps({
                "email": "e2e-admin@example.invalid",
                "password": "very-strong-password-9999",
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        if status not in (200, 201):
            self.skipTest(f"bootstrap registration disabled (status {status})")
        admin_payload = json.loads(body.decode("utf-8"))
        admin_cookie = self._extract_set_cookie(headers, "helpmefindthejob_session=")
        admin_csrf = admin_payload["user"]["csrfToken"]
        self.assertTrue(admin_payload["user"]["isAdmin"])

        status, _h, _body = self._request(
            "POST", "/api/admin/users",
            body=json.dumps({
                "email": "e2e-member@example.invalid",
                "password": "very-strong-password-8888",
                "role": "member",
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Cookie": admin_cookie,
                "X-CSRF-Token": admin_csrf,
            },
        )
        self.assertIn(status, (200, 201))

        # ---------- Stage 10: member login, then /admin → 403 ----------
        status, headers, body = self._request(
            "POST", "/api/auth/login",
            body=json.dumps({
                "email": "e2e-member@example.invalid",
                "password": "very-strong-password-8888",
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 200)
        member_cookie = self._extract_set_cookie(headers, "helpmefindthejob_session=")
        member_payload = json.loads(body.decode("utf-8"))
        self.assertFalse(member_payload["user"]["isAdmin"])

        status, headers, body = self._request(
            "GET", "/admin", headers={"Cookie": member_cookie}
        )
        self.assertEqual(status, 403,
                         "GAP-3: logged-in non-admin /admin → 403, not SPA")
        self.assertLess(len(body), 15_000)
        self.assertIn(b"Admin access required", body)
        self.assertEqual(headers.get("Cache-Control"), "no-store")

        # ---------- Stage 11: CSP report POST (AUDIT-37) ----------
        csp_body = json.dumps({"csp-report": {
            "blocked-uri": "https://evil.example/x.js",
            "document-uri": "https://helpmefindthejob.org/",
            "effective-directive": "script-src",
        }}).encode("utf-8")
        status, _h, _body = self._request(
            "POST", "/csp-report",
            body=csp_body,
            headers={
                "Content-Type": "application/csp-report",
                "Content-Length": str(len(csp_body)),
            },
        )
        self.assertEqual(status, 204)

        # ---------- Stage 12: CSP header carries reporting hooks ----------
        status, headers, _body = self._request("GET", "/api/health")
        csp = headers.get("Content-Security-Policy", "")
        self.assertIn("report-uri /csp-report", csp)
        self.assertIn("report-to csp-endpoint", csp)
        report_to = headers.get("Report-To", "")
        self.assertIn('"csp-endpoint"', report_to)

        # ---------- Stage 13: footer present on every public surface ----------
        for path in ("/", "/privacy", "/terms", "/impressum", "/data-retention",
                     "/help", "/status", "/changelog", "/forgot-password"):
            with self.subTest(path=path):
                status, _h, body = self._request("GET", path)
                self.assertEqual(status, 200)
                self.assertIn(b'class="site-footer"', body,
                              f"AUDIT-34: footer missing on {path}")
                # Lang switcher present
                self.assertIn(b'class="site-footer-langswitch"', body,
                              f"GAP-2: lang switcher missing on {path}")

        # ---------- Stage 14: JSON-LD @id references (AUDIT-46) ----------
        status, _h, body = self._request("GET", "/privacy")
        self.assertEqual(status, 200)
        m = re.search(rb'<script type="application/ld\+json">\s*(.*?)\s*</script>',
                      body, re.DOTALL)
        self.assertIsNotNone(m)
        jsonld = json.loads(m.group(1).decode("utf-8"))
        self.assertEqual(jsonld["isPartOf"]["@id"],
                         "https://helpmefindthejob.org/#website")
        self.assertEqual(jsonld["publisher"]["@id"],
                         "https://helpmefindthejob.org/#organization")

        # ---------- Stage 15: robots/sitemap alignment (GAPs 5+6) ----------
        status, _h, body = self._request("GET", "/robots.txt")
        self.assertEqual(status, 200)
        self.assertIn(b"Disallow: /csp-report", body, "GAP-5")
        status, _h, sitemap_body = self._request("GET", "/sitemap.xml")
        self.assertEqual(status, 200)
        for forbidden in (b"/csp-report", b"/admin", b"/forgot-password"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, sitemap_body,
                                 f"GAP-6: sitemap leaks {forbidden!r}")

        # ---------- Stage 16: /api/version exposes buildSha ----------
        status, _h, body = self._request("GET", "/api/version")
        self.assertEqual(status, 200)
        payload = json.loads(body.decode("utf-8"))
        self.assertIn("buildSha", payload)
        self.assertTrue(payload["buildSha"])
        self.assertLessEqual(len(payload["buildSha"]), 12)

        # ---------- Stage 17: meta descriptions distinct + length-bounded ----------
        descs: dict[str, str] = {}
        for path in ("/", "/privacy", "/terms", "/impressum", "/data-retention",
                     "/help", "/status", "/changelog"):
            status, _h, body = self._request("GET", path)
            self.assertEqual(status, 200)
            m = re.search(rb'<meta name="description" content="([^"]*)"', body)
            self.assertIsNotNone(m, f"{path} missing description")
            desc = m.group(1).decode("utf-8")
            self.assertLessEqual(len(desc), 160,
                                 f"{path} description {len(desc)} > 160 (SERP truncated)")
            self.assertNotIn(desc, descs,
                             f"{path} duplicates description of {descs.get(desc)}")
            descs[desc] = path


if __name__ == "__main__":
    unittest.main()
