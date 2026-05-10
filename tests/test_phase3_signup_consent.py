"""DSGVO consent capture on public sign-up (Phase 3 tracker item #30).

Public sign-ups (when DIRECTJOB_ALLOW_REGISTRATION=true and at least
one user already exists) must tick both Terms and Privacy boxes.
The first-account bootstrap path is exempt because the operator IS
the one writing those policies.

Server-side, ``AuthStore.record_consent`` stamps
``users.tos_accepted_at`` and ``users.privacy_accepted_at`` so the
operator can prove informed consent later if a complaint comes in.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from company_discovery.auth import AuthStore


ROOT = Path(__file__).resolve().parents[1]


class ConsentColumnTests(unittest.TestCase):
    def test_record_and_retrieve_consent(self) -> None:
        with TemporaryDirectory() as tmp:
            store = AuthStore(Path(tmp) / "auth.sqlite3", secret_key="x" * 64)
            user = store.create_user("alice@example.com", "very-secret-pass-1234")
            self.assertEqual(
                store.get_consent(user.id),
                {"tosAcceptedAt": None, "privacyAcceptedAt": None},
            )
            store.record_consent(user.id, tos=True, privacy=True)
            recorded = store.get_consent(user.id)
            self.assertIsNotNone(recorded["tosAcceptedAt"])
            self.assertIsNotNone(recorded["privacyAcceptedAt"])
            store.close()

    def test_partial_consent_records_only_what_was_passed(self) -> None:
        with TemporaryDirectory() as tmp:
            store = AuthStore(Path(tmp) / "auth.sqlite3", secret_key="x" * 64)
            user = store.create_user("bob@example.com", "very-secret-pass-1234")
            store.record_consent(user.id, tos=True, privacy=False)
            recorded = store.get_consent(user.id)
            self.assertIsNotNone(recorded["tosAcceptedAt"])
            self.assertIsNone(recorded["privacyAcceptedAt"])
            store.close()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", 0))
        except PermissionError as error:
            raise unittest.SkipTest("local port binding blocked") from error
        return int(sock.getsockname()[1])


class HttpRegisterConsentTests(unittest.TestCase):
    """Spin up the real server, walk the bootstrap admin path, then
    flip into public-registration mode and assert the consent gates."""

    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.port = _free_port()
        env = {
            **os.environ,
            "COMPANY_DISCOVERY_DATA_DIR": self.tmp.name,
            "COMPANY_DISCOVERY_ENV": "development",
            "DIRECTJOB_ALLOW_REGISTRATION": "true",
        }
        self.proc = subprocess.Popen(
            [sys.executable, str(ROOT / "app.py"), "--port", str(self.port)],
            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
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
        request = Request(
            f"{self.base}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=2) as response:
                return response.getcode(), json.loads(response.read().decode("utf-8") or "{}")
        except HTTPError as error:
            payload = json.loads(error.read().decode("utf-8") or "{}")
            return error.code, payload

    def test_bootstrap_admin_signup_does_not_require_consent(self) -> None:
        # First user via /api/auth/register becomes admin; no consent
        # boxes (operator wrote the policy).
        code, payload = self._post(
            "/api/auth/register",
            {"email": "operator@example.com", "password": "very-secret-pass-1234"},
        )
        self.assertEqual(code, 201, payload)
        self.assertTrue(payload["user"]["isAdmin"])

    def test_public_signup_without_consent_is_rejected(self) -> None:
        # First create the bootstrap admin (no consent needed).
        self._post(
            "/api/auth/register",
            {"email": "operator@example.com", "password": "very-secret-pass-1234"},
        )
        # Now a public sign-up without consent flags.
        code, payload = self._post(
            "/api/auth/register",
            {"email": "alice@example.com", "password": "very-secret-pass-1234"},
        )
        self.assertEqual(code, 400)
        self.assertEqual(payload["error"]["code"], "consent_required")

    def test_public_signup_with_consent_succeeds_and_records(self) -> None:
        self._post(
            "/api/auth/register",
            {"email": "operator@example.com", "password": "very-secret-pass-1234"},
        )
        code, payload = self._post(
            "/api/auth/register",
            {
                "email": "bob@example.com",
                "password": "very-secret-pass-1234",
                "tosAccepted": True,
                "privacyAccepted": True,
            },
        )
        self.assertEqual(code, 201, payload)
        # Verify consent is persisted on disk via a fresh AuthStore read.
        store = AuthStore(
            Path(self.tmp.name) / "auth.sqlite3",
            secret_key=os.environ.get("DIRECTJOB_SECRET_KEY") or "x" * 64,
        )
        try:
            users = store.list_users()
            bob = next(u for u in users if u.email == "bob@example.com")
            consent = store.get_consent(bob.id)
            self.assertIsNotNone(consent["tosAcceptedAt"])
            self.assertIsNotNone(consent["privacyAcceptedAt"])
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
