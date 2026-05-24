# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""AUDIT-27 — wire /admin, /reset-password/<token>, /accept-invite/<token>.

Pre-AUDIT-27 the three paths below all returned 404:

* ``/admin`` — the SPA understands an "admin" view internally but had
  no path-to-view dispatch, so a bookmark or external link to /admin
  was a dead end.
* ``/reset-password/<token>`` — the SPA only reads tokens from the
  ``?token=`` query string. Anyone hand-editing or generating a
  path-token form (e.g. a third-party email template that didn't get
  the contract memo) hit a 404 instead of the reset flow.
* ``/accept-invite/<token>`` — same as reset, for invitations.

After AUDIT-27:

* ``/admin`` serves the SPA shell, and ``static/app.js`` carries an
  ``init()`` branch that sets ``state.view = "admin"`` for that path so
  a freshly-loaded /admin lands on the admin view (existing
  ``isAdmin()`` guard still redirects non-admin users to /jobs).
* ``/reset-password/<token>`` returns 303 to
  ``/reset-password?token=<token>``. Empty token (trailing slash only)
  redirects to ``/reset-password`` (canonical form). Malformed tokens
  (chars outside URL-safe base64 alphabet, length < 8 or > 256) return
  404.
* ``/accept-invite/<token>`` mirrors the reset behaviour.

Token shape is whitelisted to the ``secrets.token_urlsafe`` alphabet
(``[A-Za-z0-9_-]``) with length bounds [8, 256] to keep arbitrary
garbage paths from generating redirects.
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
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]

_VALID_TOKEN_43 = "A" * 43  # token_urlsafe(32) shape
_MIN_VALID_TOKEN = "abcd_-09"  # exactly 8 chars, all alphabet members

_MALFORMED_TOKENS = (
    "short",  # too short (<8)
    "a" * 257,  # too long (>256)
    "has space",  # space not in alphabet
    "has.dot",  # dot not in alphabet
    "has/slash",  # slash splits the path before us
    "has+plus",  # + (non-URL-safe base64) not in alphabet
    "has=equals",  # padding not in token_urlsafe output
)


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
    except OSError as error:
        raise unittest.SkipTest("local port binding is blocked by the sandbox") from error
    port = int(sock.getsockname()[1])
    sock.close()
    return port


class SpaTokenRoutesLive(unittest.TestCase):
    """End-to-end probe of the AUDIT-27 routes against a live handler."""

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

    def _get(self, path: str) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", path)
        resp = conn.getresponse()
        try:
            body = resp.read()
            return resp.status, dict(resp.getheaders()), body
        finally:
            conn.close()

    def test_admin_serves_spa_shell(self) -> None:
        status, _headers, body = self._get("/admin")
        self.assertEqual(
            status,
            200,
            f"AUDIT-27: /admin should serve the SPA shell, got {status}",
        )
        self.assertGreater(
            len(body),
            50_000,
            f"AUDIT-27: /admin response is only {len(body)} bytes; expected the ~103 KB SPA shell.",
        )
        self.assertIn(b"<title>Helpmefindthejob", body)
        # SPA chrome markers — confirms it really is the shell, not
        # a tiny error page that happens to be 200.
        self.assertIn(b"appShell", body)

    def test_reset_password_path_token_redirects_to_query_form(self) -> None:
        status, headers, _body = self._get(f"/reset-password/{_VALID_TOKEN_43}")
        self.assertEqual(status, 303, f"expected 303 SEE_OTHER, got {status}")
        self.assertEqual(
            headers.get("Location"),
            f"/reset-password?token={_VALID_TOKEN_43}",
            "AUDIT-27: /reset-password/<token> should redirect to canonical query form",
        )

    def test_accept_invite_path_token_redirects_to_query_form(self) -> None:
        status, headers, _body = self._get(f"/accept-invite/{_VALID_TOKEN_43}")
        self.assertEqual(status, 303)
        self.assertEqual(
            headers.get("Location"),
            f"/accept-invite?token={_VALID_TOKEN_43}",
        )

    def test_minimum_length_token_is_accepted(self) -> None:
        status, headers, _body = self._get(f"/reset-password/{_MIN_VALID_TOKEN}")
        self.assertEqual(status, 303)
        self.assertEqual(
            headers.get("Location"),
            f"/reset-password?token={_MIN_VALID_TOKEN}",
        )

    def test_reset_password_empty_token_redirects_to_canonical(self) -> None:
        # /reset-password/ (trailing slash, no token) is a typo we
        # forgive — drop the slash and show the SPA shell.
        status, headers, _body = self._get("/reset-password/")
        self.assertEqual(status, 303)
        self.assertEqual(headers.get("Location"), "/reset-password")

    def test_accept_invite_empty_token_redirects_to_canonical(self) -> None:
        status, headers, _body = self._get("/accept-invite/")
        self.assertEqual(status, 303)
        self.assertEqual(headers.get("Location"), "/accept-invite")

    def test_reset_password_malformed_token_returns_404(self) -> None:
        for bad_token in _MALFORMED_TOKENS:
            # URL-encode the bad chars so http.client will send them at
            # all; the server then sees the percent-encoded form and
            # rejects it via the alphabet whitelist.
            encoded = quote(bad_token, safe="")
            with self.subTest(token=bad_token):
                status, _headers, _body = self._get(f"/reset-password/{encoded}")
                self.assertEqual(
                    status,
                    404,
                    f"AUDIT-27: /reset-password/{bad_token!r} should 404; got {status}",
                )

    def test_accept_invite_malformed_token_returns_404(self) -> None:
        for bad_token in _MALFORMED_TOKENS:
            encoded = quote(bad_token, safe="")
            with self.subTest(token=bad_token):
                status, _headers, _body = self._get(f"/accept-invite/{encoded}")
                self.assertEqual(status, 404)

    def test_canonical_reset_password_unchanged(self) -> None:
        # The existing query-form must keep serving the SPA shell.
        status, _headers, body = self._get("/reset-password")
        self.assertEqual(status, 200)
        self.assertGreater(len(body), 50_000)

    def test_canonical_accept_invite_unchanged(self) -> None:
        status, _headers, body = self._get("/accept-invite")
        self.assertEqual(status, 200)
        self.assertGreater(len(body), 50_000)


class SpaInitHandlesAdminPath(unittest.TestCase):
    """The SPA's init() must recognise /admin so a freshly-loaded
    /admin lands on the admin view (subject to isAdmin() guard)."""

    def test_app_js_sets_admin_view_for_admin_path(self) -> None:
        src = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        # Look for the literal AUDIT-27 wiring. We accept either the
        # `state.view = "admin"` pattern or a direct `navigate("admin")`
        # call inside the /admin branch.
        # The branch identifier is the path string "/admin" near the
        # SPA's other path-routing branches.
        self.assertIn(
            'path === "/admin"',
            src,
            'AUDIT-27: static/app.js init() must branch on path === "/admin" '
            "so a freshly-loaded /admin lands on the admin view.",
        )


if __name__ == "__main__":
    unittest.main()
