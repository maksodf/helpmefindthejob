# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""HTTP-level coverage for invite + password-reset + admin metrics + quotas.

The harness boots ``app.py`` on a free port like ``test_http_auth.py``.
Email transport defaults to ``ConsoleTransport`` with an outbox at
``data/email_outbox.log``; tests read tokens out of that JSONL file
because there is no live SMTP in the test environment.
"""

from __future__ import annotations

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
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", 0))
        except PermissionError as error:
            raise unittest.SkipTest("local port binding is blocked by the sandbox") from error
        return int(sock.getsockname()[1])


class _Client:
    def __init__(self, base: str) -> None:
        self.base = base
        self.cookie: str | None = None
        self.csrf: str | None = None

    def _headers(self, *, send_csrf: bool = True, body: bool = True) -> dict[str, str]:
        headers: dict[str, str] = {}
        if body:
            headers["Content-Type"] = "application/json"
        if self.cookie:
            headers["Cookie"] = self.cookie
        if send_csrf and self.csrf:
            headers["X-CSRF-Token"] = self.csrf
        return headers

    def request(
        self, path: str, *, method: str = "GET", body: dict | None = None, send_csrf: bool = True
    ) -> tuple[int, dict, str]:
        data = json.dumps(body or {}).encode("utf-8") if method != "GET" else None
        request = Request(
            f"{self.base}{path}",
            data=data,
            headers=self._headers(send_csrf=send_csrf, body=method != "GET"),
            method=method,
        )
        try:
            with urlopen(request, timeout=2) as response:
                code = response.getcode()
                payload = response.read().decode("utf-8")
                set_cookie = response.headers.get("Set-Cookie", "")
        except HTTPError as error:
            payload = error.read().decode("utf-8") if error.fp else ""
            code = error.code
            set_cookie = error.headers.get("Set-Cookie", "") if error.headers else ""
        try:
            parsed = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            parsed = {}
        return code, parsed, set_cookie

    def login(self, email: str, password: str) -> tuple[int, dict]:
        code, payload, set_cookie = self.request(
            "/api/auth/login",
            method="POST",
            body={"email": email, "password": password},
            send_csrf=False,
        )
        if code == 200:
            self.csrf = payload.get("user", {}).get("csrfToken")
            if set_cookie:
                self.cookie = set_cookie.split(";", 1)[0]
        return code, payload


class HttpInvitesAndResetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.port = free_port()
        env = {
            **os.environ,
            "HELPMEFINDTHEJOB_AUDIT_SALT": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",  # deterministic test salt; silences audit-log dev warning in spawned subprocess
            "HELPMEFINDTHEJOB_DATA_DIR": self.tmp.name,
            "HELPMEFINDTHEJOB_ENV": "development",
            "HELPMEFINDTHEJOB_EMAIL_BACKEND": "console",
            "HELPMEFINDTHEJOB_PUBLIC_URL": f"http://127.0.0.1:{self.port}",
            "HELPMEFINDTHEJOB_QUOTA_SCANS_PER_DAY": "5",
            "HELPMEFINDTHEJOB_QUOTA_AI_PER_DAY": "2",
            "HELPMEFINDTHEJOB_QUOTA_DOMAIN_PER_HOUR": "20",
            "HELPMEFINDTHEJOB_QUOTA_ACTIVE_SCANS": "3",
        }
        self.process = subprocess.Popen(
            [sys.executable, str(ROOT / "app.py"), "--port", str(self.port)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(self._terminate)
        self.base = f"http://127.0.0.1:{self.port}"
        self.outbox = Path(self.tmp.name) / "email_outbox.log"
        self._wait_for_health()

    def _terminate(self) -> None:
        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        finally:
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass

    def _wait_for_health(self) -> None:
        for _ in range(40):
            try:
                with urlopen(f"{self.base}/api/health", timeout=0.5) as response:
                    if response.getcode() == 200:
                        return
            except OSError:
                time.sleep(0.1)
        self.fail("server did not start")

    def _read_outbox(self) -> list[dict]:
        if not self.outbox.exists():
            return []
        return [json.loads(line) for line in self.outbox.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _wait_for_email(self, to: str, *, attempts: int = 20) -> dict:
        for _ in range(attempts):
            for entry in reversed(self._read_outbox()):
                if entry["to"].casefold() == to.casefold():
                    return entry
            time.sleep(0.1)
        # self.fail() raises AssertionError so the explicit return
        # below is unreachable in practice; the explicit form satisfies
        # ruff RET503 + mypy's "function must return on all paths".
        self.fail(f"email never arrived for {to}")
        return {}  # unreachable; for type-checker satisfaction

    def _token_from_link(self, body: str) -> str:
        match = re.search(r"https?://[^\s]+\?token=([A-Za-z0-9_\-]+)", body)
        self.assertIsNotNone(match, f"no link in body: {body!r}")
        return match.group(1)

    def _create_admin(self) -> _Client:
        admin = _Client(self.base)
        code, payload, set_cookie = admin.request(
            "/api/auth/register",
            method="POST",
            body={"email": "admin@example.com", "password": "very-secure-admin-pass-12"},
            send_csrf=False,
        )
        self.assertEqual(code, 201)
        admin.csrf = payload["user"]["csrfToken"]
        if set_cookie:
            admin.cookie = set_cookie.split(";", 1)[0]
        return admin

    def test_admin_can_send_invite_and_invitee_accepts(self) -> None:
        admin = self._create_admin()
        code, payload, _ = admin.request(
            "/api/admin/invitations",
            method="POST",
            body={"email": "invited@example.com", "role": "member"},
        )
        self.assertEqual(code, 201)
        email = self._wait_for_email("invited@example.com")
        self.assertIn("accept-invite", email["text"])
        token = self._token_from_link(email["text"])

        # GET reveals the invitation metadata
        code, payload, _ = _Client(self.base).request(f"/api/auth/accept-invite/{token}")
        self.assertEqual(code, 200)
        self.assertEqual(payload["invitation"]["email"], "invited@example.com")
        self.assertEqual(payload["invitation"]["role"], "member")

        # POST consumes the invite + signs in
        code, payload, set_cookie = _Client(self.base).request(
            f"/api/auth/accept-invite/{token}",
            method="POST",
            body={"newPassword": "very-secure-invite-pass-9"},
            send_csrf=False,
        )
        self.assertEqual(code, 201)
        self.assertIn("helpmefindthejob_session=", set_cookie)
        # Re-using the token must fail
        code, _, _ = _Client(self.base).request(
            f"/api/auth/accept-invite/{token}",
            method="POST",
            body={"newPassword": "ignored-replay-pass-1"},
            send_csrf=False,
        )
        self.assertEqual(code, 410)

        # Member can sign in with the password they chose
        member = _Client(self.base)
        code, _ = member.login("invited@example.com", "very-secure-invite-pass-9")
        self.assertEqual(code, 200)

        # Member cannot send invites
        code, payload, _ = member.request(
            "/api/admin/invitations",
            method="POST",
            body={"email": "another@example.com", "role": "member"},
        )
        self.assertEqual(code, 403)

    def test_password_reset_request_sends_link_and_consumes_once(self) -> None:
        admin = self._create_admin()
        # Create a member directly so we have an account with a known password
        code, _, _ = admin.request(
            "/api/admin/users",
            method="POST",
            body={"email": "tester@example.com", "password": "very-secure-tester-pass-9"},
        )
        self.assertEqual(code, 201)

        # Forgot-password is unauthenticated
        client = _Client(self.base)
        code, payload, _ = client.request(
            "/api/auth/forgot-password",
            method="POST",
            body={"email": "tester@example.com"},
            send_csrf=False,
        )
        self.assertEqual(code, 202)
        email = self._wait_for_email("tester@example.com")
        token = self._token_from_link(email["text"])

        # GET reveals masked metadata
        code, payload, _ = _Client(self.base).request(f"/api/auth/reset-password/{token}")
        self.assertEqual(code, 200)
        self.assertEqual(payload["reset"]["email"], "tester@example.com")

        # POST resets the password
        code, payload, _ = _Client(self.base).request(
            f"/api/auth/reset-password/{token}",
            method="POST",
            body={"newPassword": "much-newer-tester-pass-9"},
            send_csrf=False,
        )
        self.assertEqual(code, 200)

        # Old password no longer works
        code, _ = _Client(self.base).login("tester@example.com", "very-secure-tester-pass-9")
        self.assertEqual(code, 401)
        # New password works
        code, _ = _Client(self.base).login("tester@example.com", "much-newer-tester-pass-9")
        self.assertEqual(code, 200)

        # Token cannot be replayed
        code, _, _ = _Client(self.base).request(
            f"/api/auth/reset-password/{token}",
            method="POST",
            body={"newPassword": "newer-still-tester-pass-9"},
            send_csrf=False,
        )
        self.assertEqual(code, 410)

    def test_forgot_password_for_unknown_email_does_not_leak(self) -> None:
        # No accounts yet — forgot still returns 202
        client = _Client(self.base)
        code, _, _ = client.request(
            "/api/auth/forgot-password",
            method="POST",
            body={"email": "ghost@example.com"},
            send_csrf=False,
        )
        self.assertEqual(code, 202)
        # No outbox entry is created for unknown emails
        time.sleep(0.1)
        for entry in self._read_outbox():
            self.assertNotEqual(entry["to"], "ghost@example.com")

    def test_admin_metrics_admin_only_and_includes_counters(self) -> None:
        admin = self._create_admin()
        code, payload, _ = admin.request("/api/admin/metrics")
        self.assertEqual(code, 200)
        self.assertIn("users", payload)
        self.assertIn("quotas", payload)
        self.assertIn("scheduler", payload)

        # Member is forbidden
        code, _, _ = admin.request(
            "/api/admin/users",
            method="POST",
            body={"email": "member@example.com", "password": "very-secure-member-pass-9"},
        )
        member = _Client(self.base)
        code, _ = member.login("member@example.com", "very-secure-member-pass-9")
        self.assertEqual(code, 200)
        code, _, _ = member.request("/api/admin/metrics")
        self.assertEqual(code, 403)

    def test_health_includes_quota_usage_for_authenticated_user(self) -> None:
        admin = self._create_admin()
        code, payload, _ = admin.request("/api/health")
        self.assertEqual(code, 200)
        self.assertIn("quotas", payload)
        self.assertIn("schedulerActiveJobs", payload)


if __name__ == "__main__":
    unittest.main()
