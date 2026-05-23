# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""UX-P0 (2026-05-23, task #108): public sign-up must be open by default.

Origin bug: ``ALLOW_REGISTRATION`` defaulted to ``False``. After the
first admin user existed the SPA hid ``#registerForm`` because the
server reported ``registrationOpen: false``. The "Sign up — it's
free" CTAs on /help and /changelog therefore led the user to the
sign-in form with no way to create an account — a hard dead end
for a civic-commons product whose mission is to serve anyone in
the EU labour market facing structural friction.

Root cause fix: ``ALLOW_REGISTRATION`` default flipped to ``True``.
Operators who deliberately want a closed deployment still set
``HELPMEFINDTHEJOB_ALLOW_REGISTRATION=0`` explicitly.

This file is the regression guard. Three checks:

1. ``/api/auth/status`` returns ``registrationOpen: true`` with
   ZERO users (fresh install).
2. ``/api/auth/status`` returns ``registrationOpen: true`` AFTER a
   user has registered (the original bug — was false here).
3. The SPA shell's static register-form copy is the public-signup
   copy ("Create your account" / "Free to start. No tracker…"),
   not the bootstrap-only copy ("This screen only appears on a
   new install"). The JS still hot-swaps to bootstrap copy when
   the DB is empty, but the on-disk default must match the common
   case.
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


class PublicSignupOpenByDefault(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TemporaryDirectory()
        cls.port = _free_port()
        env = {
            **os.environ,
            "HELPMEFINDTHEJOB_DATA_DIR": cls._tmp.name,
            "HELPMEFINDTHEJOB_AUDIT_SALT": "A" * 43 + "=",
        }
        # Drop any inherited HELPMEFINDTHEJOB_ALLOW_REGISTRATION so
        # we test the DEFAULT — that's the whole point.
        env.pop("HELPMEFINDTHEJOB_ALLOW_REGISTRATION", None)
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
            return resp.status, dict(resp.getheaders()), resp.read()
        finally:
            conn.close()

    def _post_json(self, path: str, payload: dict) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=4)
        body = json.dumps(payload).encode("utf-8")
        conn.request("POST", path, body=body, headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        })
        resp = conn.getresponse()
        try:
            return resp.status, dict(resp.getheaders()), resp.read()
        finally:
            conn.close()

    def test_registration_open_on_fresh_install(self) -> None:
        status, _h, body = self._get("/api/auth/status")
        self.assertEqual(status, 200)
        payload = json.loads(body.decode("utf-8"))
        self.assertTrue(
            payload.get("registrationOpen"),
            f"Fresh install must report registrationOpen=true; got: {payload!r}",
        )

    def test_registration_stays_open_after_first_user_registers(self) -> None:
        """The original bug: registrationOpen flipped to false once
        any user existed. Locks in the civic-commons doctrine of
        open-by-default public signup."""

        # Register a first user.
        status, _h, body = self._post_json("/api/auth/register", {
            "email": "first-user@example.org",
            "password": "test-password-1234",
        })
        # 200 (or 201/202 — any 2xx) means the user was created.
        self.assertIn(
            status, (200, 201, 202),
            f"first user registration failed: {status} / {body!r}",
        )

        # Now check that registrationOpen is STILL true.
        status, _h, body = self._get("/api/auth/status")
        self.assertEqual(status, 200)
        payload = json.loads(body.decode("utf-8"))
        self.assertTrue(
            payload.get("registrationOpen"),
            "UX-P0 regression: registrationOpen became false after first "
            "user registered. Public sign-up must stay open by default — "
            f"got: {payload!r}",
        )
        self.assertTrue(
            payload.get("hasUsers"),
            f"hasUsers should be true after a registration; got: {payload!r}",
        )

    def test_register_form_default_copy_matches_public_signup_branch(self) -> None:
        """The static HTML defaults must reflect the common case —
        public signup — not the bootstrap (first-user-only) case.
        Otherwise the user sees a flash of "This screen only appears
        on a new install" before the JS hydrates."""

        status, _h, body = self._get("/")
        self.assertEqual(status, 200)
        text = body.decode("utf-8")

        self.assertIn(
            'id="registerHeading"', text,
            "registerForm heading element missing from SPA shell",
        )
        self.assertIn(
            'data-i18n="auth.createPublicHeading"', text,
            "registerHeading must use auth.createPublicHeading i18n key",
        )
        self.assertIn(
            'data-i18n="auth.createPublicLead"', text,
            "registerLead must use auth.createPublicLead i18n key",
        )
        self.assertNotIn(
            "This screen only appears on a new install",
            text,
            "Stale bootstrap-only copy is back in the SPA shell. "
            "Default must be public-signup copy; JS swaps to bootstrap "
            "copy only when the DB has zero users.",
        )


if __name__ == "__main__":
    unittest.main()
