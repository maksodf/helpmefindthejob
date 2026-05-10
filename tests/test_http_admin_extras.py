"""HTTP-level coverage for the readiness / email / account-deletion / Stripe endpoints."""

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

    def request(self, path, *, method="GET", body=None, send_csrf=True):
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

    def login(self, email, password):
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


class HttpAdminExtrasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = TemporaryDirectory()
        cls.port = free_port()
        env = {
            **os.environ,
            "COMPANY_DISCOVERY_DATA_DIR": cls.tmp.name,
            "COMPANY_DISCOVERY_ENV": "development",
            "DIRECTJOB_EMAIL_BACKEND": "console",
            "DIRECTJOB_PUBLIC_URL": f"http://127.0.0.1:{cls.port}",
        }
        cls.process = subprocess.Popen(
            [sys.executable, str(ROOT / "app.py"), "--port", str(cls.port)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        cls.base = f"http://127.0.0.1:{cls.port}"
        for _ in range(40):
            try:
                with urlopen(f"{cls.base}/api/health", timeout=0.5) as response:
                    if response.getcode() == 200:
                        break
            except OSError:
                time.sleep(0.1)
        else:
            cls.process.terminate()
            raise RuntimeError("server did not start")

        cls.admin = _Client(cls.base)
        code, payload, set_cookie = cls.admin.request(
            "/api/auth/register",
            method="POST",
            body={"email": "admin@example.com", "password": "very-secure-admin-pass-9"},
            send_csrf=False,
        )
        assert code == 201
        cls.admin.csrf = payload["user"]["csrfToken"]
        if set_cookie:
            cls.admin.cookie = set_cookie.split(";", 1)[0]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        try:
            cls.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            cls.process.kill()
        cls.tmp.cleanup()

    def test_readiness_admin_only_and_includes_signals(self) -> None:
        code, payload, _ = self.admin.request("/api/admin/readiness")
        self.assertEqual(code, 200)
        self.assertIn("signals", payload)
        signal_ids = {signal["id"] for signal in payload["signals"]}
        for required in ("deployment", "public_url", "email", "backups", "monitoring", "billing", "legal", "scheduler", "quotas", "admin_audit"):
            self.assertIn(required, signal_ids)
        self.assertIn(payload["overallStatus"], {"ok", "partial", "missing"})
        # Member is forbidden
        code, _, _ = self.admin.request(
            "/api/admin/users",
            method="POST",
            body={"email": "member@example.com", "password": "very-secure-member-pass-9"},
        )
        member = _Client(self.base)
        member.login("member@example.com", "very-secure-member-pass-9")
        code, _, _ = member.request("/api/admin/readiness")
        self.assertEqual(code, 403)

    def test_email_status_and_test_send(self) -> None:
        code, payload, _ = self.admin.request("/api/admin/email/status")
        self.assertEqual(code, 200)
        self.assertEqual(payload["backend"], "console")
        # Status response must not expose any SMTP secret keys
        flat_payload = json.dumps(payload)
        for forbidden in ("password", "Password", "DIRECTJOB_SMTP_PASSWORD", "secret"):
            self.assertNotIn(forbidden, flat_payload)
        code, payload, _ = self.admin.request(
            "/api/admin/email/test",
            method="POST",
            body={"target": "ops@example.com"},
        )
        self.assertEqual(code, 200)
        self.assertEqual(payload["status"], "sent")
        # Verify outbox got the entry
        outbox = Path(self.tmp.name) / "email_outbox.log"
        entries = [json.loads(line) for line in outbox.read_text().splitlines() if line.strip()]
        self.assertTrue(any(entry["to"] == "ops@example.com" for entry in entries))
        # Body of the test email must not leak DIRECTJOB_SMTP_PASSWORD or admin password
        for entry in entries:
            self.assertNotIn("password", entry["text"].lower())

    def test_email_test_invalid_target(self) -> None:
        code, payload, _ = self.admin.request(
            "/api/admin/email/test",
            method="POST",
            body={"target": "not-an-email"},
        )
        self.assertEqual(code, 400)
        self.assertEqual(payload["error"]["code"], "invalid_email")

    def test_billing_checkout_blocked_without_stripe(self) -> None:
        code, payload, _ = self.admin.request(
            "/api/admin/billing/checkout",
            method="POST",
            body={"planId": "team"},
        )
        self.assertEqual(code, 400)
        self.assertEqual(payload["error"]["code"], "stripe_disabled")

    def test_account_deletion_request_creates_ticket(self) -> None:
        # Tester requests deletion
        code, _, _ = self.admin.request(
            "/api/admin/users",
            method="POST",
            body={"email": "tester2@example.com", "password": "very-secure-tester2-pass-9"},
        )
        member = _Client(self.base)
        member.login("tester2@example.com", "very-secure-tester2-pass-9")
        code, payload, _ = member.request(
            "/api/account/deletion-request",
            method="POST",
            body={"reason": "Done with the pilot"},
        )
        self.assertEqual(code, 201)
        self.assertEqual(payload["ticket"]["status"], "account_deletion_pending")

    def test_admin_can_delete_user_but_not_self(self) -> None:
        # Create + delete a member
        code, payload, _ = self.admin.request(
            "/api/admin/users",
            method="POST",
            body={"email": "deletetarget@example.com", "password": "very-secure-pass-9"},
        )
        self.assertEqual(code, 201)
        target_id = payload["user"]["id"]
        code, payload, _ = self.admin.request(f"/api/admin/users/{target_id}", method="DELETE")
        self.assertEqual(code, 200)
        self.assertEqual(payload["status"], "deleted")
        # The user can no longer log in
        fresh = _Client(self.base)
        login_code, _ = fresh.login("deletetarget@example.com", "very-secure-pass-9")
        self.assertEqual(login_code, 401)
        # Admin cannot delete self
        admin_id = next(
            user["id"]
            for user in self.admin.request("/api/admin/users")[1]["users"]
            if user["email"] == "admin@example.com"
        )
        code, payload, _ = self.admin.request(f"/api/admin/users/{admin_id}", method="DELETE")
        self.assertEqual(code, 403)

    def test_admin_can_export_target_user_before_delete(self) -> None:
        # Create a tester, give them a company, export their data, delete them.
        code, payload, _ = self.admin.request(
            "/api/admin/users",
            method="POST",
            body={"email": "exporttarget@example.com", "password": "very-secure-pass-9"},
        )
        self.assertEqual(code, 201)
        target_id = payload["user"]["id"]
        target = _Client(self.base)
        target.login("exporttarget@example.com", "very-secure-pass-9")
        target.request(
            "/api/companies",
            method="POST",
            body={"name": "ExportCo", "websiteUrl": "https://export.example"},
        )
        # Admin exports the target's data
        code, payload, _ = self.admin.request(f"/api/admin/users/{target_id}/export")
        self.assertEqual(code, 200)
        self.assertEqual(payload["targetUser"]["email"], "exporttarget@example.com")
        self.assertGreaterEqual(len(payload["companies"]), 1)
        # Member is forbidden
        code, _, _ = target.request(f"/api/admin/users/{target_id}/export")
        self.assertEqual(code, 403)
        # Cleanup
        self.admin.request(f"/api/admin/users/{target_id}", method="DELETE")

    def test_last_admin_cannot_be_deleted(self) -> None:
        # Promote a fresh admin, log in as them, demote ourselves, verify they can't delete the only admin
        code, _, _ = self.admin.request(
            "/api/admin/users",
            method="POST",
            body={"email": "second-admin@example.com", "password": "very-secure-pass-9", "role": "admin"},
        )
        admin_users = self.admin.request("/api/admin/users")[1]["users"]
        original_id = next(u["id"] for u in admin_users if u["email"] == "admin@example.com")
        second_id = next(u["id"] for u in admin_users if u["email"] == "second-admin@example.com")
        second = _Client(self.base)
        second.login("second-admin@example.com", "very-secure-pass-9")
        # Second admin demotes original
        code, _, _ = second.request(f"/api/admin/users/{original_id}", method="PATCH", body={"role": "member"})
        self.assertEqual(code, 200)
        # Now second admin is the last admin and cannot be deleted by themselves (self-modify forbidden)
        code, _, _ = second.request(f"/api/admin/users/{second_id}", method="DELETE")
        self.assertEqual(code, 403)
        # Promote original back so other tests still have the original admin available
        code, _, _ = second.request(
            f"/api/admin/users/{original_id}",
            method="PATCH",
            body={"role": "admin"},
        )
        self.assertEqual(code, 200)


if __name__ == "__main__":
    unittest.main()
