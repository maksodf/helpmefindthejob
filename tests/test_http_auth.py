# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""HTTP-level auth/admin coverage.

These tests boot the real `app.py` server on a free localhost port and
exercise the admin/auth endpoints over real HTTP. They rely on the
first-account-is-admin behavior that occurs when the data directory is
empty at startup.
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

ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", 0))
        except PermissionError as error:
            raise unittest.SkipTest("local port binding is blocked by the sandbox") from error
        return int(sock.getsockname()[1])


class _Client:
    """Tiny urllib helper that tracks one cookie + CSRF pair per role."""

    def __init__(self, base: str) -> None:
        self.base = base
        self.cookie: str | None = None
        self.csrf: str | None = None

    def _headers(self, json_body: bool = True, send_csrf: bool = True) -> dict[str, str]:
        headers = {}
        if json_body:
            headers["Content-Type"] = "application/json"
        if self.cookie:
            headers["Cookie"] = self.cookie
        if send_csrf and self.csrf:
            headers["X-CSRF-Token"] = self.csrf
        return headers

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        body: dict | None = None,
        json_body: bool = True,
        send_csrf: bool = True,
        capture_set_cookie: bool = False,
    ) -> tuple[int, dict, str]:
        data = json.dumps(body or {}).encode("utf-8") if method != "GET" else None
        request = Request(
            f"{self.base}{path}",
            data=data,
            headers=self._headers(json_body=json_body and method != "GET", send_csrf=send_csrf),
            method=method,
        )
        try:
            with urlopen(request, timeout=2) as response:
                payload = response.read().decode("utf-8")
                code = response.getcode()
                set_cookie = response.headers.get("Set-Cookie", "")
        except HTTPError as error:
            payload = error.read().decode("utf-8") if error.fp else ""
            code = error.code
            set_cookie = error.headers.get("Set-Cookie", "") if error.headers else ""
        try:
            parsed = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            parsed = {}
        if capture_set_cookie and set_cookie:
            self.cookie = set_cookie.split(";", 1)[0]
            if self.cookie.endswith("=") or self.cookie.endswith('="'):
                # logout sends an empty session cookie
                self.cookie = None
        return code, parsed, set_cookie

    def login(self, email: str, password: str) -> tuple[int, dict]:
        code, payload, set_cookie = self.request(
            "/api/auth/login",
            method="POST",
            body={"email": email, "password": password},
            capture_set_cookie=True,
            send_csrf=False,
        )
        if code == 200:
            self.csrf = payload.get("user", {}).get("csrfToken")
            if not self.cookie and set_cookie:
                self.cookie = set_cookie.split(";", 1)[0]
        return code, payload


class HttpAuthAdminTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.port = free_port()
        env = {
            **os.environ,
            "HELPMEFINDTHEJOB_AUDIT_SALT": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",  # deterministic test salt; silences audit-log dev warning in spawned subprocess
            "HELPMEFINDTHEJOB_DATA_DIR": self.tmp.name,
            "HELPMEFINDTHEJOB_ENV": "development",
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

    def _create_admin_and_member(self) -> tuple[_Client, _Client, dict]:
        """Returns (admin_client, member_client, member_user_payload)."""
        admin = _Client(self.base)
        # First registration becomes admin via has_users()=False
        code, payload, set_cookie = admin.request(
            "/api/auth/register",
            method="POST",
            body={"email": "admin@example.com", "password": "very-secure-password-123"},
            capture_set_cookie=True,
            send_csrf=False,
        )
        self.assertEqual(code, 201)
        admin.csrf = payload["user"]["csrfToken"]
        if not admin.cookie and set_cookie:
            admin.cookie = set_cookie.split(";", 1)[0]
        self.assertTrue(payload["user"]["isAdmin"])

        # Admin creates a member account
        code, payload, _ = admin.request(
            "/api/admin/users",
            method="POST",
            body={
                "email": "member@example.com",
                "password": "very-secure-member-pass",
                "role": "member",
            },
        )
        self.assertEqual(code, 201)
        member_user = payload["user"]
        self.assertEqual(member_user["role"], "member")

        member = _Client(self.base)
        code, _ = member.login("member@example.com", "very-secure-member-pass")
        self.assertEqual(code, 200)
        return admin, member, member_user

    # --- tests ---

    def test_member_forbidden_from_admin_apis(self) -> None:
        admin, member, member_user = self._create_admin_and_member()
        # GET admin users
        code, payload, _ = member.request("/api/admin/users")
        self.assertEqual(code, 403)
        self.assertEqual(payload.get("error", {}).get("code"), "admin_required")
        # POST admin users
        code, payload, _ = member.request(
            "/api/admin/users",
            method="POST",
            body={"email": "x@example.com", "password": "very-secure-x-pass-1"},
        )
        self.assertEqual(code, 403)
        self.assertEqual(payload.get("error", {}).get("code"), "admin_required")
        # PATCH a user
        code, payload, _ = member.request(
            f"/api/admin/users/{member_user['id']}",
            method="PATCH",
            body={"active": False},
        )
        self.assertEqual(code, 403)
        self.assertEqual(payload.get("error", {}).get("code"), "admin_required")

    def test_csrf_required_for_mutating_calls(self) -> None:
        admin, _, _ = self._create_admin_and_member()
        saved_csrf = admin.csrf
        admin.csrf = None
        code, payload, _ = admin.request(
            "/api/companies",
            method="POST",
            body={"name": "X", "websiteUrl": "https://example.org"},
            send_csrf=False,
        )
        self.assertEqual(code, 403)
        self.assertEqual(payload.get("error", {}).get("code"), "csrf_failed")
        admin.csrf = saved_csrf

    def test_deactivated_user_cannot_login(self) -> None:
        admin, member, member_user = self._create_admin_and_member()
        # Deactivate the member
        code, _, _ = admin.request(
            f"/api/admin/users/{member_user['id']}",
            method="PATCH",
            body={"active": False},
        )
        self.assertEqual(code, 200)
        # The existing member session should be invalidated
        code, _, _ = member.request("/api/bootstrap")
        self.assertEqual(code, 401)
        # New login should fail
        fresh = _Client(self.base)
        code, payload = fresh.login("member@example.com", "very-secure-member-pass")
        self.assertEqual(code, 401)
        self.assertEqual(payload.get("error", {}).get("code"), "invalid_login")

    def test_last_admin_cannot_be_demoted_or_deactivated(self) -> None:
        admin, _, _ = self._create_admin_and_member()
        admin_user_id = None
        code, payload, _ = admin.request("/api/admin/users")
        self.assertEqual(code, 200)
        for user in payload["users"]:
            if user["role"] == "admin":
                admin_user_id = user["id"]
                break
        self.assertIsNotNone(admin_user_id)
        # Demote attempt is blocked at the HTTP layer because admin would
        # be modifying themselves; backend rejects self-modify of role.
        code, payload, _ = admin.request(
            f"/api/admin/users/{admin_user_id}",
            method="PATCH",
            body={"role": "member"},
        )
        self.assertIn(code, (400, 403))
        # Even if we try to demote a *different* admin who is the only
        # active admin, the auth_store-level last-admin guard kicks in.
        # Build that scenario: create a second admin, demote ourselves,
        # then have the second admin try to demote the only remaining admin.
        code, payload, _ = admin.request(
            "/api/admin/users",
            method="POST",
            body={
                "email": "admin2@example.com",
                "password": "very-secure-admin2-pass",
                "role": "admin",
            },
        )
        self.assertEqual(code, 201)
        admin2_id = payload["user"]["id"]
        admin2 = _Client(self.base)
        code, _ = admin2.login("admin2@example.com", "very-secure-admin2-pass")
        self.assertEqual(code, 200)
        # admin2 demotes the original admin -> succeeds
        code, payload, _ = admin2.request(
            f"/api/admin/users/{admin_user_id}",
            method="PATCH",
            body={"role": "member"},
        )
        self.assertEqual(code, 200)
        # admin2 is now the only admin. They cannot demote themselves.
        code, payload, _ = admin2.request(
            f"/api/admin/users/{admin2_id}",
            method="PATCH",
            body={"role": "member"},
        )
        self.assertIn(code, (400, 403))
        # Re-promote original admin so cleanup is sane
        code, _, _ = admin2.request(
            f"/api/admin/users/{admin_user_id}",
            method="PATCH",
            body={"role": "admin"},
        )
        self.assertEqual(code, 200)

    def test_self_modify_role_or_active_forbidden(self) -> None:
        admin, _, _ = self._create_admin_and_member()
        code, payload, _ = admin.request("/api/admin/users")
        self.assertEqual(code, 200)
        admin_id = next(u["id"] for u in payload["users"] if u["role"] == "admin")
        code, payload, _ = admin.request(
            f"/api/admin/users/{admin_id}",
            method="PATCH",
            body={"active": False},
        )
        self.assertEqual(code, 403)
        self.assertEqual(payload.get("error", {}).get("code"), "self_modify_forbidden")

    def test_password_change_invalidates_session(self) -> None:
        admin, member, _ = self._create_admin_and_member()
        # Member changes their password
        code, payload, set_cookie = member.request(
            "/api/auth/change-password",
            method="POST",
            body={
                "currentPassword": "very-secure-member-pass",
                "newPassword": "much-newer-member-pass",
            },
        )
        self.assertEqual(code, 200)
        # Endpoint clears session cookie
        self.assertIn("Max-Age=0", set_cookie)
        # Old session is invalid now
        code, _, _ = member.request("/api/bootstrap")
        self.assertEqual(code, 401)
        # Login with old password fails
        fresh = _Client(self.base)
        code, _ = fresh.login("member@example.com", "very-secure-member-pass")
        self.assertEqual(code, 401)
        # Login with new password works
        code, _ = fresh.login("member@example.com", "much-newer-member-pass")
        self.assertEqual(code, 200)

    def test_admin_password_reset_signs_target_out(self) -> None:
        admin, member, member_user = self._create_admin_and_member()
        # Member is signed in
        code, _, _ = member.request("/api/bootstrap")
        self.assertEqual(code, 200)
        # Admin resets the password
        code, _, _ = admin.request(
            f"/api/admin/users/{member_user['id']}",
            method="PATCH",
            body={"password": "totally-new-member-pass-9"},
        )
        self.assertEqual(code, 200)
        # Old session invalid
        code, _, _ = member.request("/api/bootstrap")
        self.assertEqual(code, 401)
        # New password works
        fresh = _Client(self.base)
        code, _ = fresh.login("member@example.com", "totally-new-member-pass-9")
        self.assertEqual(code, 200)

    def test_admin_audit_log_records_actions(self) -> None:
        admin, _, member_user = self._create_admin_and_member()
        # Trigger one of each action kind
        code, _, _ = admin.request(
            f"/api/admin/users/{member_user['id']}",
            method="PATCH",
            body={"active": False},
        )
        self.assertEqual(code, 200)
        code, _, _ = admin.request(
            f"/api/admin/users/{member_user['id']}",
            method="PATCH",
            body={"active": True, "password": "another-secure-pass-9"},
        )
        self.assertEqual(code, 200)

        log_path = Path(self.tmp.name) / "admin_audit.log"
        # Allow a brief moment for the daemon to flush, then read
        for _ in range(10):
            if log_path.exists() and log_path.stat().st_size:
                break
            time.sleep(0.1)
        self.assertTrue(log_path.exists())
        entries = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        actions = [entry["action"] for entry in entries]
        self.assertIn("create_user", actions)
        self.assertIn("update_active", actions)
        self.assertIn("reset_password", actions)
        for entry in entries:
            self.assertIn("actorEmail", entry)
            self.assertIn("at", entry)


if __name__ == "__main__":
    unittest.main()
