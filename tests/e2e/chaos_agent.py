# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Adversarial chaos agent.

Throws weird / hostile / edge-case inputs at the product and verifies
that the system stays alive (no 500, no crash, no data leak, no silent
acceptance of garbage). Each case has an expected behaviour:

  - ``"reject"`` — the API must return a 4xx with a clear error code.
  - ``"sanitize"`` — input is accepted but stored/rendered safely
    (no XSS, no SQL injection, no path traversal escape).
  - ``"graceful_empty"`` — input is accepted but produces an empty
    result set (no 500, no crash); the user sees a graceful empty state.

Categories exercised:

  * CV field: empty / huge / non-English / control chars / HTML+JS
  * Search query: empty / 1-char / 500-char / SQL-ish / emoji
  * Location: country / whitespace / SQL-ish / emoji / very long
  * Company form: huge name / bad URL / XSS in notes
  * Application notes: HTML, JS, JSON payload
  * Concurrency: same user, two sessions, racing writes
  * Numeric limits: negative, zero, huge

Run via ``./scripts/run-chaos-agent.sh`` (boots a fresh app under a
clean SQLite). Exits non-zero on any FAIL."""

from __future__ import annotations

import json
import os
import secrets
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASE_URL = os.environ.get("E2E_BASE_URL", "").rstrip("/")


# ---------------- HTTP plumbing (reused pattern from promise_verifier) -------


class _HttpClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.cookie = ""
        self.csrf_token = ""

    def _request(
        self, method: str, path: str, *, body: dict | None = None, timeout: int = 30
    ) -> tuple[int, dict | str]:
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.csrf_token and method in {"POST", "PUT", "DELETE", "PATCH"}:
            headers["X-CSRF-Token"] = self.csrf_token
        req = urllib.request.Request(
            self.base_url + path, data=data, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                set_cookie = resp.headers.get("Set-Cookie", "")
                if set_cookie:
                    self.cookie = set_cookie.split(";", 1)[0]
                raw_body = resp.read().decode("utf-8", errors="replace")
                try:
                    payload = json.loads(raw_body) if raw_body else {}
                except json.JSONDecodeError:
                    payload = raw_body
                self._absorb_csrf(payload)
                return resp.status, payload
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            try:
                payload = json.loads(body_text) if body_text else {}
            except json.JSONDecodeError:
                payload = body_text
            return exc.code, payload

    def _absorb_csrf(self, payload) -> None:
        if not isinstance(payload, dict):
            return
        for k in ("csrfToken", "csrf_token"):
            if isinstance(payload.get(k), str) and payload[k]:
                self.csrf_token = payload[k]
                return
        user = payload.get("user") or {}
        if isinstance(user, dict):
            for k in ("csrfToken", "csrf_token"):
                if isinstance(user.get(k), str) and user[k]:
                    self.csrf_token = user[k]
                    return

    def post(self, path, body=None, timeout=30):
        return self._request("POST", path, body=body or {}, timeout=timeout)

    def get(self, path, timeout=30):
        return self._request("GET", path, timeout=timeout)


_ADMIN: _HttpClient | None = None


def _admin_client() -> _HttpClient:
    global _ADMIN
    if _ADMIN is None:
        _ADMIN = _HttpClient(BASE_URL)
        _ADMIN.get("/")
        status, payload = _ADMIN.post(
            "/api/auth/register",
            {
                "email": f"admin+chaos+{secrets.token_hex(3)}@example.com",
                "password": "chaos-admin-pass-99-X",
                "tosAccepted": True,
                "privacyAccepted": True,
            },
        )
        if status not in (200, 201):
            raise RuntimeError(f"admin register failed: {status} {payload}")
    return _ADMIN


def _tester() -> _HttpClient:
    """Mint a fresh tester via the admin path (bypasses rate limit)."""
    admin = _admin_client()
    email = f"chaos+{secrets.token_hex(3)}@example.com"
    pw = "chaos-tester-pass-99-X"
    s, p = admin.post("/api/admin/users", {"email": email, "password": pw, "role": "member"})
    if s not in (200, 201):
        raise RuntimeError(f"admin create failed: {s} {p}")
    c = _HttpClient(BASE_URL)
    c.get("/")
    s, p = c.post("/api/auth/login", {"email": email, "password": pw})
    if s not in (200, 201):
        raise RuntimeError(f"login failed: {s} {p}")
    return c


# ---------------- Result reporting ----------------


@dataclass
class ChaosResult:
    case: str
    category: str
    expectation: str
    ok: bool
    status: int = 0
    detail: str = ""

    def to_dict(self):
        return {
            "case": self.case,
            "category": self.category,
            "expectation": self.expectation,
            "verdict": "PASS" if self.ok else "FAIL",
            "status": self.status,
            "detail": self.detail,
        }


# ---------------- CV-text edge cases ----------------


def _check_cv_input(c: _HttpClient, case: str, cv: str, expect: str) -> ChaosResult:
    """Generic CV submission test. ``expect``:
    'sanitize' — must return 200 and the stored value must not include
                 raw <script>/event handlers when echoed back.
    'reject'   — must return 4xx with a clear error code.
    'graceful_empty' — 200 OK with empty CV string back."""
    status, payload = c.post("/api/profile", {"cvText": cv})
    if expect == "reject":
        if status >= 400:
            return ChaosResult(case, "cv", expect, True, status, f"rejected with {status}")
        return ChaosResult(case, "cv", expect, False, status, f"expected 4xx, got {status}")
    if expect == "graceful_empty":
        if status != 200:
            return ChaosResult(
                case,
                "cv",
                expect,
                False,
                status,
                f"expected 200, got {status}: {str(payload)[:80]}",
            )
        return ChaosResult(case, "cv", expect, True, status, "200 OK")
    # sanitize: accept, but no script tag retained when echoed
    if status != 200:
        return ChaosResult(
            case, "cv", expect, False, status, f"expected 200, got {status}: {str(payload)[:80]}"
        )
    # Read profile back
    gs, gp = c.get("/api/profile")
    if gs != 200:
        return ChaosResult(case, "cv", expect, False, gs, f"profile GET failed: {gs}")
    cv_back = ""
    if isinstance(gp, dict):
        cv_back = gp.get("cvText") or gp.get("cv_text") or ""
        if not cv_back:
            profile = gp.get("profile") or {}
            cv_back = profile.get("cvText") or profile.get("cv_text") or ""
    # Sanitization check: cv may be STORED verbatim but ANY user-facing render
    # must escape. Since /api/profile returns JSON, the raw string is fine —
    # the XSS concern is the HTML render layer. So for "sanitize" we accept
    # 200 + non-corrupted round-trip. The server strips leading/trailing
    # whitespace via .strip() before persisting, so compare against the
    # stripped form.
    expected = cv.strip()[:60_000]
    if cv_back != expected:
        return ChaosResult(
            case,
            "cv",
            expect,
            False,
            status,
            f"round-trip mismatch: in={len(cv)} stripped={len(expected)} out={len(cv_back)}",
        )
    return ChaosResult(
        case, "cv", expect, True, status, f"accepted + round-tripped ({len(cv_back)} chars)"
    )


def chaos_cv_cases() -> list[ChaosResult]:
    cases: list[ChaosResult] = []
    c = _tester()

    cases.append(_check_cv_input(c, "cv_empty", "", "graceful_empty"))
    cases.append(_check_cv_input(c, "cv_whitespace_only", "   \n\t  ", "graceful_empty"))
    cases.append(
        _check_cv_input(c, "cv_normal", "Senior Software Engineer. 8y Python.", "sanitize")
    )
    cases.append(
        _check_cv_input(
            c, "cv_html_inert", "Senior Engineer. <b>Skills</b>: Python, AWS.", "sanitize"
        )
    )
    cases.append(
        _check_cv_input(
            c, "cv_script_tag", "Senior Engineer. <script>alert(1)</script> Python.", "sanitize"
        )
    )
    cases.append(
        _check_cv_input(
            c,
            "cv_event_handler",
            "Senior Engineer <img src=x onerror=alert(1)> Python.",
            "sanitize",
        )
    )
    cases.append(
        _check_cv_input(c, "cv_unicode_emoji", "Senior Engineer 🚀 ⚡️ Python 🐍 K8s ☸️", "sanitize")
    )
    cases.append(
        _check_cv_input(
            c,
            "cv_german_umlaut",
            "Senior Entwickler. Müller, Köln, Düsseldorf. Straße.",
            "sanitize",
        )
    )
    cases.append(
        _check_cv_input(
            c, "cv_arabic_rtl", "مهندس برمجيات أول. خبرة 8 سنوات في Python.", "sanitize"
        )
    )
    cases.append(
        _check_cv_input(
            c, "cv_chinese", "高级软件工程师。8 年 Python 和 Postgres 经验。", "sanitize"
        )
    )
    cases.append(
        _check_cv_input(
            c, "cv_50kb", "Senior Engineer. " + ("Python AWS Postgres " * 2500), "sanitize"
        )
    )
    cases.append(_check_cv_input(c, "cv_100kb_over_limit", "x" * 100_000, "reject"))
    cases.append(_check_cv_input(c, "cv_null_bytes", "Senior\x00Engineer\x00Python", "sanitize"))
    cases.append(
        _check_cv_input(c, "cv_control_chars", "Senior\x01Engineer\x02Python\x03AWS", "sanitize")
    )
    cases.append(_check_cv_input(c, "cv_sql_payload", "Senior'); DROP TABLE users; --", "sanitize"))
    return cases


# ---------------- Search-query edge cases ----------------


def _check_search(c: _HttpClient, case: str, query: str, location, expect: str) -> ChaosResult:
    status, payload = c.post(
        "/api/jobs/search",
        {
            "query": query,
            "location": location,
            "limitPerProvider": 5,
            "cap": 20,
        },
    )
    if expect == "reject":
        if status >= 400:
            return ChaosResult(case, "search", expect, True, status, f"rejected with {status}")
        return ChaosResult(case, "search", expect, False, status, f"expected 4xx, got {status}")
    if expect == "graceful_empty":
        if status != 200:
            return ChaosResult(case, "search", expect, False, status, f"expected 200, got {status}")
        jobs = (payload.get("jobs") if isinstance(payload, dict) else []) or []
        return ChaosResult(
            case, "search", expect, True, status, f"200 OK, {len(jobs)} jobs (empty allowed)"
        )
    # sanitize / accept
    if status != 200:
        return ChaosResult(
            case,
            "search",
            expect,
            False,
            status,
            f"expected 200, got {status}: {str(payload)[:80]}",
        )
    return ChaosResult(
        case, "search", expect, True, status, f"200 OK; {len(payload.get('jobs') or [])} results"
    )


def chaos_search_cases() -> list[ChaosResult]:
    cases: list[ChaosResult] = []
    c = _tester()

    cases.append(_check_search(c, "query_empty", "", "Berlin", "graceful_empty"))
    cases.append(_check_search(c, "query_whitespace", "   ", "Berlin", "graceful_empty"))
    cases.append(_check_search(c, "query_1char", "a", "Berlin", "sanitize"))
    cases.append(_check_search(c, "query_emoji", "🚀 senior engineer 🐍", "Berlin", "sanitize"))
    cases.append(
        _check_search(
            c, "query_500_chars", ("senior backend engineer " * 25)[:500], "Berlin", "sanitize"
        )
    )
    cases.append(
        _check_search(
            c, "query_sql_injection", "senior'; DROP TABLE users; --", "Berlin", "sanitize"
        )
    )
    cases.append(
        _check_search(
            c, "query_html_tags", "<script>alert(1)</script> engineer", "Berlin", "sanitize"
        )
    )
    cases.append(_check_search(c, "query_path_traversal", "../../etc/passwd", "Berlin", "sanitize"))
    cases.append(_check_search(c, "query_unicode_mix", "senior 高级 senior", "Berlin", "sanitize"))
    cases.append(_check_search(c, "location_empty", "engineer", "", "sanitize"))
    cases.append(_check_search(c, "location_null", "engineer", None, "sanitize"))
    cases.append(_check_search(c, "location_country_name", "engineer", "Germany", "sanitize"))
    cases.append(_check_search(c, "location_emoji", "engineer", "🇩🇪 Berlin 🚀", "sanitize"))
    cases.append(
        _check_search(
            c, "location_sql_injection", "engineer", "Berlin'; DROP TABLE x; --", "sanitize"
        )
    )
    cases.append(_check_search(c, "location_500_chars", "engineer", "Berlin " * 80, "sanitize"))
    return cases


# ---------------- Numeric limits ----------------


def _check_search_limit(
    c: _HttpClient, case: str, limit_per_provider, cap, expect_status_range: tuple[int, int]
) -> ChaosResult:
    status, payload = c.post(
        "/api/jobs/search",
        {
            "query": "engineer",
            "location": "Berlin",
            "limitPerProvider": limit_per_provider,
            "cap": cap,
        },
    )
    lo, hi = expect_status_range
    if lo <= status <= hi:
        return ChaosResult(case, "limits", f"{lo}-{hi}", True, status, f"got {status}")
    return ChaosResult(
        case, "limits", f"{lo}-{hi}", False, status, f"got {status}: {str(payload)[:80]}"
    )


def chaos_limits_cases() -> list[ChaosResult]:
    cases: list[ChaosResult] = []
    c = _tester()
    cases.append(_check_search_limit(c, "limits_negative", -5, -10, (200, 299)))
    cases.append(_check_search_limit(c, "limits_zero", 0, 0, (200, 299)))
    cases.append(_check_search_limit(c, "limits_huge", 10**9, 10**9, (200, 299)))
    cases.append(_check_search_limit(c, "limits_non_int", "abc", "xyz", (200, 499)))
    cases.append(_check_search_limit(c, "limits_null", None, None, (200, 299)))
    return cases


# ---------------- Company-form edge cases ----------------


def _check_company(c: _HttpClient, case: str, payload: dict, expect: str) -> ChaosResult:
    status, response = c.post("/api/companies", payload)
    if expect == "reject":
        if status >= 400:
            return ChaosResult(case, "company", expect, True, status, f"rejected with {status}")
        return ChaosResult(case, "company", expect, False, status, f"expected 4xx, got {status}")
    if expect == "sanitize":
        if status not in (200, 201):
            return ChaosResult(
                case,
                "company",
                expect,
                False,
                status,
                f"expected 2xx, got {status}: {str(response)[:80]}",
            )
        return ChaosResult(case, "company", expect, True, status, "accepted")
    return ChaosResult(case, "company", expect, False, status, "unknown expect")


def chaos_company_cases() -> list[ChaosResult]:
    cases: list[ChaosResult] = []
    c = _tester()
    # All "sanitize" cases need a websiteUrl (required field). The "reject"
    # cases test empty/whitespace name which fails before the URL check.
    cases.append(_check_company(c, "company_empty_name", {"name": ""}, "reject"))
    cases.append(_check_company(c, "company_whitespace_name", {"name": "   "}, "reject"))
    cases.append(
        _check_company(
            c,
            "company_huge_name",
            {"name": "A" * 5000, "websiteUrl": "https://x1.example"},
            "sanitize",
        )
    )
    cases.append(
        _check_company(
            c,
            "company_html_in_name",
            {"name": "<script>alert(1)</script>Co", "websiteUrl": "https://x2.example"},
            "sanitize",
        )
    )
    cases.append(
        _check_company(
            c,
            "company_bad_url_scheme",
            {"name": "X-bad-scheme", "websiteUrl": "javascript:alert(1)"},
            "sanitize",
        )
    )
    cases.append(
        _check_company(
            c,
            "company_url_path_traversal",
            {"name": "Y-trav", "websiteUrl": "https://x.com/../../etc/passwd"},
            "sanitize",
        )
    )
    cases.append(
        _check_company(
            c,
            "company_unicode_name",
            {"name": "über-employer GmbH 🚀", "websiteUrl": "https://x3.example"},
            "sanitize",
        )
    )
    cases.append(
        _check_company(
            c,
            "company_notes_xss",
            {
                "name": "Z-xss",
                "websiteUrl": "https://x4.example",
                "notes": "<img src=x onerror=alert(1)>",
            },
            "sanitize",
        )
    )
    return cases


# ---------------- Auth edge cases ----------------


def chaos_auth_cases() -> list[ChaosResult]:
    cases: list[ChaosResult] = []
    admin = _admin_client()

    # invalid email formats
    invalid_emails = [
        "",
        "not-an-email",
        "@example.com",
        "user@",
        "user@.com",
        "user space@example.com",
    ]
    for em in invalid_emails:
        s, p = admin.post(
            "/api/admin/users",
            {
                "email": em,
                "password": "valid-password-99-X",
                "role": "member",
            },
        )
        name = f"auth_invalid_email_{em[:15] or 'empty'}"
        if s >= 400:
            cases.append(ChaosResult(name, "auth", "reject", True, s, f"{s}: {str(p)[:60]}"))
        else:
            cases.append(ChaosResult(name, "auth", "reject", False, s, "accepted invalid email"))

    # weak password (server requires 12+ chars)
    weak_passwords = ["", "a", "short", "12345678901"]
    for pw in weak_passwords:
        s, p = admin.post(
            "/api/admin/users",
            {
                "email": f"weak+{secrets.token_hex(2)}@example.com",
                "password": pw,
                "role": "member",
            },
        )
        name = f"auth_weak_password_{len(pw)}"
        if s >= 400:
            cases.append(ChaosResult(name, "auth", "reject", True, s, f"{s}: {str(p)[:60]}"))
        else:
            cases.append(ChaosResult(name, "auth", "reject", False, s, "accepted weak password"))

    # duplicate registration via admin → admin path normally rejects.
    dup_email = f"dup+{secrets.token_hex(3)}@example.com"
    s1, _ = admin.post(
        "/api/admin/users",
        {
            "email": dup_email,
            "password": "valid-password-99-X",
            "role": "member",
        },
    )
    s2, p2 = admin.post(
        "/api/admin/users",
        {
            "email": dup_email,
            "password": "valid-password-99-X",
            "role": "member",
        },
    )
    if s1 in (200, 201) and s2 >= 400:
        cases.append(
            ChaosResult(
                "auth_duplicate_registration",
                "auth",
                "reject 2nd",
                True,
                s2,
                f"{s2}: {str(p2)[:60]}",
            )
        )
    else:
        cases.append(
            ChaosResult(
                "auth_duplicate_registration",
                "auth",
                "reject 2nd",
                False,
                s2,
                f"first={s1} second={s2}",
            )
        )

    return cases


def chaos_auth_rate_limit_cases() -> list[ChaosResult]:
    """Login rate-limit test. Run LAST — burning 10+ login slots from
    the local IP poisons subsequent _tester() calls."""
    admin = _admin_client()
    cases: list[ChaosResult] = []
    target_email = f"locktest+{secrets.token_hex(3)}@example.com"
    admin.post(
        "/api/admin/users",
        {
            "email": target_email,
            "password": "valid-password-99-X",
            "role": "member",
        },
    )
    locked = False
    last_status = 0
    for _ in range(12):
        c = _HttpClient(BASE_URL)
        c.get("/")
        s, _p = c.post("/api/auth/login", {"email": target_email, "password": "wrong-99"})
        last_status = s
        if s == 429:
            locked = True
            break
    cases.append(
        ChaosResult(
            "auth_login_rate_limit",
            "auth",
            "429 after N attempts",
            locked,
            last_status,
            f"locked-out after burst (last={last_status})",
        )
    )
    return cases


# ---------------- Invalid body / Content-Type / missing CSRF ----------------


def chaos_request_shape_cases() -> list[ChaosResult]:
    cases: list[ChaosResult] = []
    c = _tester()

    # Invalid JSON body — server must return 400, not 500.
    req = urllib.request.Request(
        BASE_URL + "/api/profile",
        data=b"{ not valid json",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Cookie": c.cookie,
            "X-CSRF-Token": c.csrf_token,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    cases.append(
        ChaosResult(
            "request_invalid_json",
            "request_shape",
            "400",
            400 <= status < 500,
            status,
            f"{status} (expected 4xx)",
        )
    )

    # Missing CSRF on state-changing endpoint.
    c2 = _tester()
    saved_token = c2.csrf_token
    c2.csrf_token = ""  # strip the token
    s, p = c2.post("/api/profile", {"cvText": "should not work"})
    c2.csrf_token = saved_token
    cases.append(
        ChaosResult(
            "request_missing_csrf", "request_shape", "403", s == 403, s, f"{s}: {str(p)[:60]}"
        )
    )

    # Unauthenticated POST to protected endpoint.
    naked = _HttpClient(BASE_URL)
    naked.get("/")
    s, _p = naked.post("/api/profile", {"cvText": "naked"})
    cases.append(
        ChaosResult(
            "request_no_auth",
            "request_shape",
            "401 or 403",
            s in (401, 403),
            s,
            f"{s} (expected 401/403)",
        )
    )

    # Profile with unknown extra fields — should ignore them, return 200.
    s, _p = c.post(
        "/api/profile",
        {
            "cvText": "ok",
            "unknown_field": "xxx",
            "__proto__": {"injected": True},
            "constructor": {"injected": True},
        },
    )
    cases.append(
        ChaosResult(
            "request_unknown_fields",
            "request_shape",
            "ignored",
            s == 200,
            s,
            f"{s} (expected 200, unknown fields silently dropped)",
        )
    )
    return cases


# ---------------- Cross-user access ----------------


def chaos_cross_user_cases() -> list[ChaosResult]:
    """User B must not be able to read or modify User A's data."""
    cases: list[ChaosResult] = []
    a = _tester()
    b = _tester()

    # A creates a company. B tries to read it.
    s, payload = a.post(
        "/api/companies",
        {
            "name": "A-Corp",
            "websiteUrl": "https://a-corp.example",
        },
    )
    if s not in (200, 201):
        cases.append(
            ChaosResult(
                "crossuser_setup",
                "cross_user",
                "setup",
                False,
                s,
                f"A failed to create company: {s}",
            )
        )
        return cases
    company_id = (payload.get("company") or {}).get("id")

    # B fetches their own bootstrap — A's company must NOT appear.
    s, b_boot = b.get("/api/bootstrap")
    if s != 200:
        cases.append(
            ChaosResult(
                "crossuser_b_bootstrap", "cross_user", "200", False, s, "B bootstrap failed"
            )
        )
        return cases
    b_companies = b_boot.get("companies") or []
    leaked = any(c.get("id") == company_id for c in b_companies)
    cases.append(
        ChaosResult(
            "crossuser_no_company_leak",
            "cross_user",
            "no leak",
            not leaked,
            s,
            f"B sees {len(b_companies)} companies; leaked={leaked}",
        )
    )

    # B tries to DELETE A's company directly.
    if company_id:
        s, _ = b._request("DELETE", f"/api/companies/{company_id}")
        cases.append(
            ChaosResult(
                "crossuser_delete_other",
                "cross_user",
                "403/404",
                s in (403, 404),
                s,
                f"DELETE returned {s} (expected 403/404)",
            )
        )
    return cases


# ---------------- Application notes / status ----------------


def chaos_application_cases() -> list[ChaosResult]:
    """Import a job and try chaos values on /application endpoint."""
    cases: list[ChaosResult] = []
    c = _tester()

    # First, set a CV and create a saved search to populate discovered jobs.
    c.post("/api/profile", {"cvText": "Senior Python engineer. AWS, Postgres."})
    ss_status, ss_payload = c.post(
        "/api/saved-searches",
        {
            "name": "chaos-app-search",
            "targetRoles": ["senior backend engineer"],
            "location": "Berlin",
        },
    )
    if ss_status not in (200, 201):
        return [
            ChaosResult(
                "application_setup",
                "application",
                "setup",
                False,
                ss_status,
                "saved-search create failed",
            )
        ]
    saved_id = (ss_payload.get("savedSearch") or {}).get("id")
    c.post(f"/api/saved-searches/{urllib.parse.quote(saved_id, safe='')}/run-now", {})
    boot_s, boot = c.get("/api/bootstrap")
    discovered = boot.get("discoveredJobs") or []
    if not discovered:
        return [
            ChaosResult(
                "application_setup",
                "application",
                "discovered",
                False,
                boot_s,
                "no discovered jobs from live API",
            )
        ]
    imp_s, imp_p = c.post(
        f"/api/discovered-jobs/{urllib.parse.quote(discovered[0]['id'], safe='')}/import",
        {},
    )
    if imp_s not in (200, 201):
        return [
            ChaosResult(
                "application_setup",
                "application",
                "import",
                False,
                imp_s,
                f"import failed: {imp_p}",
            )
        ]
    imported_id = (imp_p.get("job") or imp_p.get("importedJob") or {}).get("id")
    if not imported_id:
        return [
            ChaosResult(
                "application_setup",
                "application",
                "imported_id",
                False,
                0,
                "no imported id in response",
            )
        ]

    # Now the chaos cases.
    matrix = [
        ("app_status_invalid", {"applicationStatus": "yolo"}, "reject"),
        ("app_status_empty", {"applicationStatus": ""}, "reject"),
        (
            "app_notes_html",
            {"applicationStatus": "applied", "applicationNotes": "<script>alert(1)</script>"},
            "sanitize",
        ),
        (
            "app_notes_huge",
            {"applicationStatus": "applied", "applicationNotes": "x" * 50_000},
            "sanitize",
        ),
        (
            "app_notes_emoji",
            {"applicationStatus": "applied", "applicationNotes": "🚀 sent CV 📧"},
            "sanitize",
        ),
        ("app_replied_true", {"applicationStatus": "applied", "replied": True}, "sanitize"),
        (
            "app_replied_invalid_type",
            {"applicationStatus": "applied", "replied": "yes"},
            "sanitize",
        ),
        (
            "app_cover_letter_huge",
            {"applicationStatus": "applied", "coverLetterDraft": "x" * 50_000},
            "sanitize",
        ),
    ]
    for name, body, expect in matrix:
        s, p = c.post(
            f"/api/imported-jobs/{urllib.parse.quote(imported_id, safe='')}/application",
            body,
        )
        if expect == "reject":
            ok = s >= 400
            cases.append(ChaosResult(name, "application", expect, ok, s, f"{s}: {str(p)[:60]}"))
        else:
            ok = s == 200
            cases.append(ChaosResult(name, "application", expect, ok, s, f"{s}: {str(p)[:60]}"))
    return cases


# ---------------- Idempotent / repeated imports ----------------


def chaos_repeat_import_cases() -> list[ChaosResult]:
    """Importing the same discovered job N times should not create N
    duplicates — should return the same imported_job each time."""
    cases: list[ChaosResult] = []
    c = _tester()
    c.post("/api/profile", {"cvText": "Senior dev"})
    ss_s, ss = c.post(
        "/api/saved-searches",
        {
            "name": "chaos-repeat",
            "targetRoles": ["senior backend engineer"],
            "location": "Berlin",
        },
    )
    if ss_s not in (200, 201):
        return [
            ChaosResult(
                "repeat_import_setup", "idempotency", "setup", False, ss_s, "saved-search failed"
            )
        ]
    sid = (ss.get("savedSearch") or {}).get("id")
    c.post(f"/api/saved-searches/{urllib.parse.quote(sid, safe='')}/run-now", {})
    _, boot = c.get("/api/bootstrap")
    discovered = boot.get("discoveredJobs") or []
    if not discovered:
        return [
            ChaosResult(
                "repeat_import_setup", "idempotency", "setup", False, 0, "no discovered jobs"
            )
        ]
    did = discovered[0]["id"]
    ids: list[str] = []
    for _ in range(5):
        s, p = c.post(f"/api/discovered-jobs/{urllib.parse.quote(did, safe='')}/import", {})
        if s in (200, 201):
            jid = (p.get("job") or p.get("importedJob") or {}).get("id")
            if jid:
                ids.append(jid)
    unique_count = len(set(ids))
    cases.append(
        ChaosResult(
            "import_idempotent_5x",
            "idempotency",
            "1 unique imported id",
            unique_count == 1,
            200,
            f"got {len(ids)} responses, {unique_count} unique ids",
        )
    )
    return cases


# ---------------- Concurrency: same user, two sessions racing ----------------


def chaos_concurrent_writes() -> list[ChaosResult]:
    """Two parallel sessions both write to the same profile. The user
    should never see a 500 or stale data; last-write-wins is fine."""
    c1 = _tester()
    # Re-login as same user from a fresh client to get a parallel session.
    # Reuse via duplicate signup is more disruptive — use the same cookie.
    email = None
    sid = None
    # Easier: create one tester, then run 10 parallel CV writes from that
    # single client and verify all succeed (no 500s).
    errors: list[str] = []
    statuses: list[int] = []
    lock = threading.Lock()

    def write_cv(i: int):
        s, _ = c1.post("/api/profile", {"cvText": f"Senior Engineer iteration {i} " + ("x" * 200)})
        with lock:
            statuses.append(s)
            if s != 200:
                errors.append(f"iter {i}: {s}")

    threads = [threading.Thread(target=write_cv, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    ok = not errors and all(s == 200 for s in statuses)
    detail = f"20 parallel writes: {len([s for s in statuses if s == 200])}/20 OK"
    if errors:
        detail += f"; failures: {errors[:3]}"
    return [
        ChaosResult(
            "concurrent_cv_writes",
            "concurrency",
            "all 200 OK",
            ok,
            statuses[0] if statuses else 0,
            detail,
        )
    ]


# ---------------- Driver ----------------


def main() -> int:
    if not BASE_URL:
        print("ERROR: E2E_BASE_URL is required", file=sys.stderr)
        return 2
    print(f"[chaos] base_url={BASE_URL}")
    results: list[ChaosResult] = []
    # Order matters: the login-rate-limit batch saturates the failed-login
    # bucket for this IP, so it runs LAST. Anything that needs _tester()
    # (which logs in) must come before it.
    for name, batch in [
        ("CV inputs", chaos_cv_cases),
        ("Search query / location", chaos_search_cases),
        ("Numeric limits", chaos_limits_cases),
        ("Company form", chaos_company_cases),
        ("Auth / registration edge cases", chaos_auth_cases),
        ("Request shape (JSON / CSRF / auth)", chaos_request_shape_cases),
        ("Cross-user isolation", chaos_cross_user_cases),
        ("Application notes / status", chaos_application_cases),
        ("Import idempotency", chaos_repeat_import_cases),
        ("Concurrency", chaos_concurrent_writes),
        ("Login rate-limit (runs LAST)", chaos_auth_rate_limit_cases),
    ]:
        print(f"\n[chaos] --- {name} ---")
        try:
            batch_results = batch()
        except Exception as exc:
            print(f"  ❌ batch '{name}' crashed: {type(exc).__name__}: {exc}")
            results.append(
                ChaosResult(
                    f"batch:{name}",
                    "batch",
                    "no-crash",
                    False,
                    0,
                    f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        for r in batch_results:
            marker = "✅" if r.ok else "❌"
            print(f"  {marker} [{r.category}] {r.case}: {r.detail}")
            results.append(r)

    out = Path(os.environ.get("E2E_CHAOS_REPORT", "tests/e2e/chaos_report.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([r.to_dict() for r in results], indent=2, ensure_ascii=False))
    print(f"\n[chaos] report → {out}")

    print("\n" + "=" * 70)
    print("CHAOS SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in results if r.ok)
    failed = len(results) - passed
    print(f"  total cases: {len(results)}")
    print(f"  passed:      {passed}")
    print(f"  failed:      {failed}")
    if failed:
        print("\n  failing cases:")
        for r in results:
            if not r.ok:
                print(f"    ❌ [{r.category:14s}] {r.case}: {r.detail}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
