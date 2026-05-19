# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Email verification flow (Phase 3 tracker item #31).

On public sign-up the server mints a verification token, mails the
confirm link, and stamps ``users.email_verified_at`` when the user
clicks. ``DIRECTJOB_REQUIRE_EMAIL_VERIFICATION=true`` blocks login on
unverified accounts. Bootstrap admin path auto-verifies (the operator
owns the mailbox already).

POST /api/auth/verify-email/resend mints a fresh token. Always
returns 202 to avoid revealing which emails already have an account.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from company_discovery.auth import AuthStore

ROOT = Path(__file__).resolve().parents[1]


class AuthStoreVerificationTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        with TemporaryDirectory() as tmp:
            store = AuthStore(Path(tmp) / "auth.sqlite3", secret_key="x" * 64)
            user = store.create_user("alice@example.com", "very-secret-pass-1234")
            self.assertFalse(store.is_email_verified(user.id))

            token = store.start_email_verification(user.id)
            self.assertGreater(len(token), 30)
            self.assertFalse(store.is_email_verified(user.id))

            verified_id = store.confirm_email_verification(token)
            self.assertEqual(verified_id, user.id)
            self.assertTrue(store.is_email_verified(user.id))

            # Replay should fail (token burned on confirm).
            with self.assertRaises(ValueError):
                store.confirm_email_verification(token)
            store.close()

    def test_mark_email_verified_short_circuit(self) -> None:
        with TemporaryDirectory() as tmp:
            store = AuthStore(Path(tmp) / "auth.sqlite3", secret_key="x" * 64)
            user = store.create_user("operator@example.com", "very-secret-pass-1234")
            self.assertFalse(store.is_email_verified(user.id))
            store.mark_email_verified(user.id)
            self.assertTrue(store.is_email_verified(user.id))
            store.close()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", 0))
        except PermissionError as error:
            raise unittest.SkipTest("local port binding blocked") from error
        return int(sock.getsockname()[1])


class HttpEmailVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.port = _free_port()
        env = {
            **os.environ,
            "COMPANY_DISCOVERY_DATA_DIR": self.tmp.name,
            "COMPANY_DISCOVERY_ENV": "development",
            "DIRECTJOB_ALLOW_REGISTRATION": "true",
            "DIRECTJOB_REQUIRE_EMAIL_VERIFICATION": "true",
            "DIRECTJOB_PUBLIC_URL": f"http://127.0.0.1:{self.port}",
        }
        self.proc = subprocess.Popen(
            [sys.executable, str(ROOT / "app.py"), "--port", str(self.port)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(self._terminate)
        self.base = f"http://127.0.0.1:{self.port}"
        for _ in range(40):
            try:
                with urlopen(f"{self.base}/api/health", timeout=0.5) as response:
                    if response.getcode() == 200:
                        break
            except OSError:
                time.sleep(0.1)
        else:
            self.fail("server did not start")

    def _terminate(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()

    def _post(self, path: str, body: dict) -> tuple[int, dict]:
        req = Request(
            f"{self.base}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=2) as response:
                return response.getcode(), json.loads(response.read().decode("utf-8") or "{}")
        except HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8") or "{}")

    def _get_status(self, path: str) -> int:
        try:
            with urlopen(f"{self.base}{path}", timeout=2) as response:
                return response.getcode()
        except HTTPError as error:
            return error.code

    def _outbox_url_for(self, marker: str) -> str | None:
        import re

        log = Path(self.tmp.name) / "email_outbox.log"
        if not log.exists():
            return None
        pattern = re.compile(r"https?://[^\s\"\\]+")
        for line in log.read_text(encoding="utf-8").splitlines():
            if marker in line:
                # The outbox writes JSON-encoded text where literal
                # newlines appear as ``\n``. Extract the URL up to the
                # first whitespace / quote / backslash.
                match = pattern.search(line[line.index(marker) :])
                if match:
                    return match.group(0)
        return None

    def test_public_signup_sends_verification_and_blocks_login(self) -> None:
        # Bootstrap admin first (auto-verified).
        self._post(
            "/api/auth/register",
            {"email": "operator@example.com", "password": "very-secret-pass-1234"},
        )
        # Public sign-up.
        code, payload = self._post(
            "/api/auth/register",
            {
                "email": "alice@example.com",
                "password": "very-secret-pass-1234",
                "tosAccepted": True,
                "privacyAccepted": True,
            },
        )
        self.assertEqual(code, 201, payload)
        # Cookie comes back, but a fresh login should be refused on
        # the env-gate because the email isn't verified yet.
        code, payload = self._post(
            "/api/auth/login",
            {"email": "alice@example.com", "password": "very-secret-pass-1234"},
        )
        self.assertEqual(code, 403)
        self.assertEqual(payload["error"]["code"], "email_unverified")

    def test_verify_link_unblocks_login(self) -> None:
        self._post(
            "/api/auth/register",
            {"email": "operator@example.com", "password": "very-secret-pass-1234"},
        )
        self._post(
            "/api/auth/register",
            {
                "email": "bob@example.com",
                "password": "very-secret-pass-1234",
                "tosAccepted": True,
                "privacyAccepted": True,
            },
        )
        verify_url = self._outbox_url_for("Verify your email")
        self.assertIsNotNone(verify_url, "verify-email URL not found in outbox")
        # The URL is absolute (DIRECTJOB_PUBLIC_URL); strip the host so
        # we hit the test server on the assigned port.
        path_with_query = verify_url[len(self.base) :]
        code = self._get_status(path_with_query)
        self.assertEqual(code, 200)
        # Now login succeeds.
        code, payload = self._post(
            "/api/auth/login",
            {"email": "bob@example.com", "password": "very-secret-pass-1234"},
        )
        self.assertEqual(code, 200, payload)

    def test_resend_endpoint_returns_202_for_unknown_email(self) -> None:
        # Status 202 even for a nonexistent address — avoids leaking
        # which emails are registered.
        code, payload = self._post(
            "/api/auth/verify-email/resend",
            {"email": "ghost@example.com"},
        )
        self.assertEqual(code, 202)
        self.assertEqual(payload["status"], "sent_if_known")


if __name__ == "__main__":
    unittest.main()
