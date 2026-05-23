# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""AUDIT-22 — TTDSG §25 referral-cookie regression guard.

The ``/r/<code>`` referral landing endpoint redirects the visitor to the
home page with a ``?ref=<code>`` query parameter. Historically it ALSO
set a ``helpmefindthejob_ref`` HTTP cookie. That cookie is consent-required
tracking under German TTDSG §25 (and would also fail the EU ePrivacy
Directive Article 5(3) test): it identifies the inbound referrer across
the session before any consent banner is shown.

The cookie is also functionally redundant: ``/api/auth/register`` reads
the referral code from the ``referrerCode`` JSON body field, which the
SPA fills from the ``?ref=`` query parameter the redirect target carries.
Nothing in the server reads the cookie back.

This module is the regression guard. Two layers:

1. **Source tripwire** — the literal ``helpmefindthejob_ref`` token must
   not appear anywhere in ``app.py``. If it reappears (Set-Cookie OR any
   incoming-Cookie parsing), the test fails.
2. **End-to-end behaviour probe** — boot the real app on a free port,
   hit ``/r/abc123``, verify the response is a 303 to ``/?ref=abc123``
   and contains zero ``Set-Cookie`` headers carrying the cookie name.
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

_FORBIDDEN_COOKIE_NAME = "helpmefindthejob_ref"


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
    except OSError as error:
        raise unittest.SkipTest("local port binding is blocked by the sandbox") from error
    port = int(sock.getsockname()[1])
    sock.close()
    return port


class RefCookieAbsentFromSourceTests(unittest.TestCase):
    """Cheap, deterministic tripwire: the literal cookie name must not
    appear in ``app.py``. Any reintroduction — Set-Cookie emission,
    Cookie-header parsing, comment reference — fails this test."""

    def test_app_py_contains_no_helpmefindthejob_ref_token(self) -> None:
        src = (ROOT / "app.py").read_text(encoding="utf-8")
        hits: list[int] = []
        for lineno, line in enumerate(src.splitlines(), start=1):
            if _FORBIDDEN_COOKIE_NAME in line:
                hits.append(lineno)
        if hits:
            # Use self.fail rather than assertNotIn so the failure
            # message stays compact instead of dumping the entire
            # ~10k-line app.py source into the diff.
            self.fail(
                "AUDIT-22 regression: the helpmefindthejob_ref cookie "
                f"name reappeared in app.py at line(s) {hits}. This cookie "
                "is consent-required tracking under TTDSG §25 and must not "
                "be emitted by the /r/<code> referral redirect or read from "
                "incoming Cookie headers. The referral code is forwarded "
                "via the referrerCode JSON body field on /api/auth/register; "
                "no server-side cookie is required."
            )


class RefRedirectEmitsNoConsentCookieTests(unittest.TestCase):
    """End-to-end probe: boot the real handler on a free port, request
    ``/r/<code>``, and verify the response is a 303 redirect with no
    ``helpmefindthejob_ref`` cookie."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.port = _free_port()
        env = {
            **os.environ,
            "HELPMEFINDTHEJOB_DATA_DIR": self._tmp.name,
            "HELPMEFINDTHEJOB_AUDIT_SALT": "A" * 43 + "=",
        }
        self._process = subprocess.Popen(
            [sys.executable, str(ROOT / "app.py"), "--port", str(self.port)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(self._terminate)
        self._wait_for_health()

    def _terminate(self) -> None:
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
        # Close the stdout/stderr pipes the subprocess opened; otherwise
        # Python emits ResourceWarning when the test suite tears down.
        for stream in (self._process.stdout, self._process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except Exception:  # noqa: BLE001 — best-effort cleanup
                    pass

    def _wait_for_health(self) -> None:
        for _ in range(60):
            try:
                conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=0.5)
                conn.request("GET", "/api/health")
                resp = conn.getresponse()
                ok = resp.status == 200
                resp.read()
                conn.close()
                if ok:
                    return
            except OSError:
                time.sleep(0.1)
        self.fail("server did not become healthy on port {}".format(self.port))

    def test_referral_redirect_does_not_emit_helpmefindthejob_ref_cookie(self) -> None:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", "/r/abc123")
        resp = conn.getresponse()
        try:
            self.assertEqual(
                resp.status, 303, "expected 303 SEE_OTHER redirect from /r/<code>"
            )
            self.assertEqual(resp.getheader("Location"), "/?ref=abc123")
            set_cookies = resp.headers.get_all("Set-Cookie") or []
            for cookie in set_cookies:
                self.assertNotIn(
                    _FORBIDDEN_COOKIE_NAME,
                    cookie,
                    msg=(
                        "AUDIT-22 regression: /r/<code> emitted a "
                        f"{_FORBIDDEN_COOKIE_NAME} cookie. This is "
                        "consent-required tracking under TTDSG §25 and is "
                        "forbidden. Drop the Set-Cookie header from the "
                        "referral redirect; the SPA already carries the "
                        "code via ?ref=<code> in the redirect target."
                    ),
                )
        finally:
            resp.read()
            conn.close()


if __name__ == "__main__":
    unittest.main()
