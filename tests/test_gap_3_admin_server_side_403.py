# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""GAP-3 (post-self-audit, 2026-05-23): /admin must not leak the
SPA shell to signed-in non-admin users.

Pre-fix behaviour:
  * Logged-out  → /admin → 200, full SPA shell (~108 KB) — fine; SPA
    sets state.view="admin" so post-login an admin lands on the
    admin view (AUDIT-27 wiring).
  * Logged-in admin → /admin → 200, full SPA shell — fine.
  * Logged-in non-admin → /admin → 200, full SPA shell loads, then
    JS evaluates isAdmin() and bounces to /jobs. The non-admin
    user briefly downloads the entire SPA chrome.

Post-fix behaviour:
  * Logged-out  → /admin → 200, SPA shell (unchanged).
  * Logged-in admin → /admin → 200, SPA shell (unchanged).
  * Logged-in non-admin → /admin → 403, small bilingual HTML
    "Admin access required" page with a link back to the app and
    Cache-Control: no-store.
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


class AdminServerSideForbidden(unittest.TestCase):
    """Live end-to-end probe of the /admin guard."""

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
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        try:
            return resp.status, dict(resp.getheaders()), resp.read()
        finally:
            conn.close()

    def _register(self, email: str, password: str) -> tuple[int, str | None, dict | None]:
        """Register a user. Returns (status, session_cookie, payload)."""
        status, headers, body = self._request(
            "POST",
            "/api/auth/register",
            body=json.dumps({"email": email, "password": password}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        if status not in (200, 201):
            return status, None, None
        # Find the Set-Cookie that carries the session
        # http.client lowercases headers but preserves the first occurrence
        # of any given header name. Multiple Set-Cookies are joined by ", "
        # which is hostile to parsing. We re-open the headers via the raw
        # message API to find each Set-Cookie individually.
        cookies: list[str] = []
        for k, v in headers.items():
            if k.lower() == "set-cookie":
                # comma-join hack: split on ", " safely is hard if Expires
                # contains a comma. Instead just take the first chunk per
                # cookie (name=value pair before semicolon).
                for part in v.split(", "):
                    if "=" in part:
                        first_pair = part.split(";", 1)[0]
                        cookies.append(first_pair)
        session_cookie = next(
            (c for c in cookies if c.startswith("helpmefindthejob_session=")),
            None,
        )
        payload = json.loads(body.decode("utf-8"))
        return status, session_cookie, payload

    def test_logged_out_admin_serves_spa_shell(self) -> None:
        # Baseline: no session → SPA shell loads (so the user can sign
        # in and AUDIT-27's state.view="admin" wiring takes over post-
        # login if they happen to be an admin).
        status, _headers, body = self._request("GET", "/admin")
        self.assertEqual(status, 200, "logged-out /admin should serve SPA shell")
        self.assertGreater(len(body), 50_000, "expected ~108 KB SPA shell")
        self.assertIn(b'<template id="appShellTemplate"', body)

    def _bootstrap_admin_then_create_member(self, member_email: str, member_password: str) -> str:
        """Helper: register a bootstrap admin, then use the admin's
        session to create a non-admin member, then log in as the
        member and return the member's session cookie."""
        # Step 1: bootstrap admin (first registered user)
        status_admin, admin_cookie, admin_payload = self._register(
            "admin@example.invalid", "very-strong-password-1234"
        )
        if status_admin not in (200, 201):
            # If a previous test in this class already bootstrapped,
            # try logging in as the existing admin.
            status_login, headers, login_body = self._request(
                "POST",
                "/api/auth/login",
                body=json.dumps(
                    {
                        "email": "admin@example.invalid",
                        "password": "very-strong-password-1234",
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            if status_login != 200:
                self.skipTest(f"could not bootstrap admin (status {status_admin}/{status_login})")
            # extract session
            for k, v in headers.items():
                if k.lower() == "set-cookie":
                    for part in v.split(", "):
                        if part.startswith("helpmefindthejob_session="):
                            admin_cookie = part.split(";", 1)[0]
                            break
            admin_payload = json.loads(login_body.decode("utf-8"))
        admin_csrf = admin_payload["user"]["csrfToken"]

        # Step 2: as admin, POST /api/admin/users to create a member.
        status_create, _h, _b = self._request(
            "POST",
            "/api/admin/users",
            body=json.dumps(
                {
                    "email": member_email,
                    "password": member_password,
                    "role": "member",
                }
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Cookie": admin_cookie,
                "X-CSRF-Token": admin_csrf,
            },
        )
        if status_create not in (200, 201):
            self.skipTest(f"admin/users POST failed (status {status_create})")

        # Step 3: log in as the new member, return their session cookie
        status_login, login_headers, login_body = self._request(
            "POST",
            "/api/auth/login",
            body=json.dumps(
                {
                    "email": member_email,
                    "password": member_password,
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        if status_login != 200:
            self.skipTest(f"member login failed (status {status_login})")
        # Confirm not admin
        member_payload = json.loads(login_body.decode("utf-8"))
        self.assertFalse(
            member_payload["user"]["isAdmin"],
            "GAP-3 setup invariant: created member must NOT be admin",
        )
        # Extract member session cookie
        member_cookie = None
        for k, v in login_headers.items():
            if k.lower() == "set-cookie":
                for part in v.split(", "):
                    if part.startswith("helpmefindthejob_session="):
                        member_cookie = part.split(";", 1)[0]
                        break
        self.assertIsNotNone(member_cookie, "member login must return a session cookie")
        return member_cookie

    def test_logged_in_non_admin_gets_403_html(self) -> None:
        nonadmin_cookie = self._bootstrap_admin_then_create_member(
            "user@example.invalid", "very-strong-password-5678"
        )

        # Hit /admin with the non-admin's session.
        status, headers, body = self._request("GET", "/admin", headers={"Cookie": nonadmin_cookie})
        self.assertEqual(
            status,
            403,
            f"GAP-3: logged-in non-admin /admin should be 403, got {status}. "
            "Pre-GAP-3 this would have leaked the ~108 KB SPA shell.",
        )
        # Body should be the small HTML page, NOT the SPA shell
        self.assertLess(
            len(body),
            15_000,
            f"GAP-3: 403 body is {len(body)} bytes — should be a small "
            "page, not the SPA shell. Pre-GAP-3 the SPA shell leaked through.",
        )
        # Page must carry the expected markers
        self.assertIn(b"Admin access required", body)
        self.assertIn(b"Back to the app", body)
        # SPA-shell markers must be ABSENT
        self.assertNotIn(b'<template id="appShellTemplate"', body)
        self.assertNotIn(b'id="loginForm"', body)
        # Cache-Control: no-store so browsers/Caddy don't cache the 403
        self.assertEqual(
            headers.get("Cache-Control"),
            "no-store",
            "GAP-3: 403 must be Cache-Control: no-store to keep the role decision per-request.",
        )

    def test_logged_in_non_admin_gets_german_403_when_accept_language_de(self) -> None:
        nonadmin_cookie = self._bootstrap_admin_then_create_member(
            "user-de@example.invalid", "very-strong-password-5678"
        )

        # Request /admin with German Accept-Language
        status, _headers, body = self._request(
            "GET",
            "/admin",
            headers={
                "Cookie": nonadmin_cookie,
                "Accept-Language": "de-DE,de;q=0.9,en;q=0.5",
            },
        )
        self.assertEqual(status, 403)
        # German strings must appear (HTML-entity encoded form);
        # English must NOT.
        self.assertIn(b"Adminzugriff erforderlich", body)
        self.assertIn(b"Zur&uuml;ck zur App", body)
        self.assertNotIn(b"Admin access required", body)
        self.assertIn(b'<html lang="de">', body)


if __name__ == "__main__":
    unittest.main()
