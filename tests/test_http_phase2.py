"""HTTP-level coverage for Phase 2/3 endpoints.

Boots the app on a free port, mirrors the helper pattern used by
``test_http_invitations.py``, and exercises:

- saved searches CRUD
- discover-companies (curated provider only — offline)
- application status update on imported jobs
- watchlist-template apply
- exports endpoints (CSV + Markdown)
- digest preview + send (ConsoleTransport)
- billing GET + admin update
- support submit
- analytics event submission
- last_login_at populated by login
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
                content_type = response.headers.get("Content-Type", "")
                set_cookie = response.headers.get("Set-Cookie", "")
        except HTTPError as error:
            payload = error.read().decode("utf-8") if error.fp else ""
            code = error.code
            content_type = error.headers.get_content_type() if error.headers else ""
            set_cookie = error.headers.get("Set-Cookie", "") if error.headers else ""
        try:
            parsed = json.loads(payload) if payload and content_type.startswith("application/json") else payload
        except json.JSONDecodeError:
            parsed = payload
        return code, parsed, set_cookie, content_type

    def login(self, email: str, password: str):
        code, payload, set_cookie, _ = self.request(
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


class HttpPhase2Tests(unittest.TestCase):
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
        code, payload, set_cookie, _ = cls.admin.request(
            "/api/auth/register",
            method="POST",
            body={"email": "admin@example.com", "password": "very-secure-admin-pass-9"},
            send_csrf=False,
        )
        assert code == 201, payload
        cls.admin.csrf = payload["user"]["csrfToken"]
        if set_cookie:
            cls.admin.cookie = set_cookie.split(";", 1)[0]
        cls.bootstrap = payload["bootstrap"]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        try:
            cls.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            cls.process.kill()
        cls.tmp.cleanup()

    def test_bootstrap_includes_phase2_fields(self) -> None:
        code, payload, _, _ = self.admin.request("/api/bootstrap")
        self.assertEqual(code, 200)
        self.assertIn("savedSearches", payload)
        self.assertIn("watchlistTemplates", payload)
        self.assertIn("billingPlans", payload)
        self.assertIn("onboarding", payload)
        self.assertIn("applicationStatuses", payload)
        self.assertIn("saved", payload["applicationStatuses"])

    def test_saved_searches_crud(self) -> None:
        code, payload, _, _ = self.admin.request(
            "/api/saved-searches",
            method="POST",
            body={"name": "Berlin DH", "targetRoles": ["Digital Health"], "industry": "Healthcare", "location": "Berlin"},
        )
        self.assertEqual(code, 200)
        search_id = payload["savedSearch"]["id"]
        code, payload, _, _ = self.admin.request("/api/saved-searches")
        self.assertEqual(code, 200)
        self.assertTrue(any(s["id"] == search_id for s in payload["savedSearches"]))
        # Update it
        code, payload, _, _ = self.admin.request(
            "/api/saved-searches",
            method="POST",
            body={"id": search_id, "name": "Berlin DH (junior)", "targetRoles": ["Digital Health"]},
        )
        self.assertEqual(code, 200)
        self.assertEqual(payload["savedSearch"]["name"], "Berlin DH (junior)")
        # Delete
        code, payload, _, _ = self.admin.request(f"/api/saved-searches/{search_id}", method="DELETE")
        self.assertEqual(code, 200)

    def test_discover_companies_returns_curated(self) -> None:
        code, payload, _, _ = self.admin.request(
            "/api/discover-companies",
            method="POST",
            body={"targetRoles": ["Digital Health"], "industry": "Healthcare", "location": "Berlin"},
        )
        self.assertEqual(code, 200)
        self.assertIsInstance(payload["results"], list)
        if payload["results"]:
            self.assertIn("relevanceScore", payload["results"][0])

    def test_apply_watchlist_template_adds_companies(self) -> None:
        # Pick the digital health template — small list, deterministic
        code, payload, _, _ = self.admin.request(
            "/api/watchlist-templates/digital_health_de/apply",
            method="POST",
        )
        self.assertEqual(code, 200)
        self.assertGreater(len(payload["result"]["added"]), 0)
        # Re-apply must mark all as already_in_watchlist
        code, payload, _, _ = self.admin.request(
            "/api/watchlist-templates/digital_health_de/apply",
            method="POST",
        )
        self.assertEqual(code, 200)
        skipped_reasons = {item["reason"] for item in payload["result"]["skipped"]}
        self.assertIn("already_in_watchlist", skipped_reasons)

    def test_application_status_update_flow(self) -> None:
        # Seed the demo job + import it
        code, demo_payload, _, _ = self.admin.request("/api/demo/seed", method="POST")
        self.assertEqual(code, 201)
        discovered_id = demo_payload["demo"]["job"]["id"]
        code, imp_payload, _, _ = self.admin.request(
            f"/api/discovered-jobs/{discovered_id}/import",
            method="POST",
        )
        self.assertEqual(code, 200)
        imported_id = imp_payload["job"]["id"]
        code, payload, _, _ = self.admin.request(
            f"/api/imported-jobs/{imported_id}/application",
            method="POST",
            body={
                "applicationStatus": "applied",
                "applicationNotes": "Submitted CV",
                "coverLetterDraft": "Dear hiring team",
                "documentsChecklist": [{"label": "CV", "complete": True}, {"label": "Transcript", "complete": False}],
                "nextAction": "Follow up on Friday",
            },
        )
        self.assertEqual(code, 200)
        self.assertEqual(payload["job"]["application_status"], "applied")
        self.assertEqual(payload["job"]["next_action"], "Follow up on Friday")
        self.assertEqual(len(payload["job"]["documents_checklist"]), 2)

        # Invalid status returns 400
        code, payload, _, _ = self.admin.request(
            f"/api/imported-jobs/{imported_id}/application",
            method="POST",
            body={"applicationStatus": "totally_made_up"},
        )
        self.assertEqual(code, 400)

    def test_exports_csv_and_markdown(self) -> None:
        code, body, _, content_type = self.admin.request("/api/exports/imported.csv")
        self.assertEqual(code, 200)
        self.assertIn("text/csv", content_type)
        self.assertIn("Title", body if isinstance(body, str) else "")
        code, md_body, _, content_type = self.admin.request("/api/exports/imported.md")
        self.assertEqual(code, 200)
        self.assertIn("text/markdown", content_type)
        self.assertIn("# Imported jobs", md_body if isinstance(md_body, str) else "")
        code, csv_body, _, _ = self.admin.request("/api/exports/discovered.csv")
        self.assertEqual(code, 200)
        self.assertIn("Source URL", csv_body if isinstance(csv_body, str) else "")

    def test_digest_preview_and_send(self) -> None:
        code, payload, _, _ = self.admin.request("/api/digest/preview")
        self.assertEqual(code, 200)
        self.assertIn("digest", payload)
        code, payload, _, _ = self.admin.request("/api/digest/send", method="POST")
        self.assertEqual(code, 200)
        self.assertEqual(payload["status"], "sent")
        outbox = Path(self.tmp.name) / "email_outbox.log"
        self.assertTrue(outbox.exists())
        entries = [json.loads(line) for line in outbox.read_text().splitlines() if line.strip()]
        self.assertTrue(any("digest" in entry["subject"].casefold() for entry in entries))

    def test_billing_admin_only(self) -> None:
        code, payload, _, _ = self.admin.request("/api/billing")
        self.assertEqual(code, 200)
        self.assertEqual(payload["subscription"]["plan_id"], "pilot")
        self.assertEqual(len(payload["plans"]), 3)
        # Admin updates to team
        code, payload, _, _ = self.admin.request(
            "/api/admin/billing",
            method="POST",
            body={"planId": "team", "status": "active", "seats": 10, "customerEmail": "ops@example.com"},
        )
        self.assertEqual(code, 200)
        self.assertEqual(payload["subscription"]["plan_id"], "team")
        self.assertEqual(payload["subscription"]["seats"], 10)

        # Member is forbidden
        code, _, _, _ = self.admin.request(
            "/api/admin/users",
            method="POST",
            body={"email": "tester@example.com", "password": "very-secure-tester-pass-9"},
        )
        member = _Client(self.base)
        member.login("tester@example.com", "very-secure-tester-pass-9")
        code, _, _, _ = member.request(
            "/api/admin/billing",
            method="POST",
            body={"planId": "team"},
        )
        self.assertEqual(code, 403)

    def test_support_ticket_submission(self) -> None:
        code, payload, _, _ = self.admin.request(
            "/api/support",
            method="POST",
            body={"subject": "Need help with scan", "body": "It returned blocked_or_captcha", "contactEmail": "alex@example.com"},
        )
        self.assertEqual(code, 201)
        self.assertEqual(payload["ticket"]["subject"], "Need help with scan")
        # Admin can see it
        code, payload, _, _ = self.admin.request("/api/admin/support")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(len(payload["tickets"]), 1)

    def test_analytics_event_submit(self) -> None:
        code, payload, _, _ = self.admin.request(
            "/api/analytics/event",
            method="POST",
            body={"kind": "ui_nav", "payload": {"to": "companies"}},
        )
        self.assertEqual(code, 201)
        # Admin metrics panel surfaces the event
        code, payload, _, _ = self.admin.request("/api/admin/analytics")
        self.assertEqual(code, 200)
        kinds = {event["kind"] for event in payload["events"]}
        self.assertIn("ui_nav", kinds)

    def test_last_login_populated(self) -> None:
        code, payload, _, _ = self.admin.request("/api/admin/users")
        self.assertEqual(code, 200)
        admin_row = next(u for u in payload["users"] if u["email"] == "admin@example.com")
        self.assertIsNotNone(admin_row.get("lastLoginAt"))

    def test_export_imports_round_trip(self) -> None:
        code, payload, _, _ = self.admin.request("/api/data/export")
        self.assertEqual(code, 200)
        self.assertEqual(payload["schemaVersion"], 1)
        # Re-import into a different user via admin-bypass: create another admin, import same payload
        code, _, _, _ = self.admin.request(
            "/api/admin/users",
            method="POST",
            body={"email": "alt-admin@example.com", "password": "very-secure-other-9", "role": "admin"},
        )
        alt = _Client(self.base)
        alt.login("alt-admin@example.com", "very-secure-other-9")
        code, response, _, _ = alt.request(
            "/api/data/import",
            method="POST",
            body=payload,
        )
        self.assertEqual(code, 200)
        self.assertGreaterEqual(response["result"]["counts"]["companies"], 1)


if __name__ == "__main__":
    unittest.main()
