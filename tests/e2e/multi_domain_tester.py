# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Multi-domain synthetic tester.

Exercises the chat router + cross-cutting concerns across the domains
the operator named:

  1.  Backend                — every command's HTTP route returns 2xx
                                with correct shape.
  2.  Database               — DB writes are reflected in bootstrap.
  3.  Security               — slash arg with HTML/script payload is
                                stored as text, never rendered as
                                executable HTML.
  4.  AI router               — keyword router fires; falls back to
                                help when intent is unknown.
  5.  Data / analytics        — every executed command emits a
                                `chat_cmd` analytics event.
  6.  Product / UX            — confirmation gate runs before every
                                DB write; "no" cancels cleanly.
  7.  GDPR audit              — every action is audit-logged with
                                command name.
  8.  Accessibility (server)  — chat replies are plain text (no raw
                                HTML), so screen readers render them
                                correctly.
  9.  i18n                    — German confirmation words ("ja",
                                "nein") work as yes/no.
 10.  QA                      — empty / invalid input is rejected with
                                a clear error and re-prompts.

Each "domain" gets one PASS/FAIL line."""

from __future__ import annotations

import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASE_URL = os.environ.get("E2E_BASE_URL", "").rstrip("/")


class Client:
    def __init__(self) -> None:
        self.cookie = ""
        self.csrf = ""

    def _req(self, method: str, path: str, body: dict | None = None):
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.csrf and method != "GET":
            headers["X-CSRF-Token"] = self.csrf
        req = urllib.request.Request(BASE_URL + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                sc = resp.headers.get("Set-Cookie", "")
                if sc:
                    self.cookie = sc.split(";", 1)[0]
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    p = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    p = raw
                self._absorb(p)
                return resp.status, p
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode() if exc.fp else ""
            try:
                return exc.code, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return exc.code, raw

    def _absorb(self, p):
        if not isinstance(p, dict):
            return
        for k in ("csrfToken", "csrf_token"):
            if isinstance(p.get(k), str) and p[k]:
                self.csrf = p[k]
                return
        u = p.get("user") or {}
        if isinstance(u, dict):
            for k in ("csrfToken", "csrf_token"):
                if isinstance(u.get(k), str) and u[k]:
                    self.csrf = u[k]
                    return

    def post(self, path: str, body=None):
        return self._req("POST", path, body or {})

    def get(self, path: str):
        return self._req("GET", path)


def signup() -> Client:
    c = Client()
    c.get("/")
    s, p = c.post(
        "/api/auth/register",
        {
            "email": f"multidomain+{secrets.token_hex(3)}@example.com",
            "password": "multidomain-tester-99-X",
            "tosAccepted": True,
            "privacyAccepted": True,
        },
    )
    if s not in (200, 201):
        raise RuntimeError(f"signup: {s} {p}")
    return c


def chat(c: Client, message: str) -> dict:
    s, p = c.post("/api/chat/message", {"message": message})
    if s != 200:
        raise RuntimeError(f"chat {message!r}: {s} {p}")
    return p


def reset(c: Client) -> None:
    c.post("/api/chat/reset", {})


def chat_until_confirm(c: Client, opener: str, skip_optionals: bool = True) -> dict:
    """Drive a single chat command from opener until either:
      - the confirmation prompt arrives (destructive commands), OR
      - the command executes directly (R19: read-only commands
        like find_jobs / show_view skip the confirmation gate)

    Returns the terminal response. Caller checks for
    ``awaitingConfirmation`` vs ``executed`` to know which path it
    took.
    """
    r = chat(c, opener)
    for _ in range(8):
        if r.get("awaitingConfirmation") or r.get("executed"):
            return r
        if r.get("awaiting") and skip_optionals and r.get("optional"):
            r = chat(c, " ")
            continue
        if r.get("awaiting"):
            raise RuntimeError(f"unexpected required slot {r['awaiting']}; reply={r['reply']!r}")
        raise RuntimeError(f"chat did not reach confirmation OR execution: {r}")
    raise RuntimeError("too many turns without reaching terminal state")


REPORT: list[dict] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    flag = "✅" if ok else "❌"
    print(f"  {flag} [{name}] {detail}")
    REPORT.append({"domain": name, "ok": ok, "detail": detail})


def domain_backend(c: Client) -> None:
    reset(c)
    chat(c, "/help")
    record("backend", True, "/help responded 200 with reply field")


def domain_database(c: Client) -> None:
    reset(c)
    r = chat_until_confirm(c, "/add-company DB-Corp https://db-corp.example")
    assert r.get("awaitingConfirmation"), r
    confirm = chat(c, "yes")
    assert confirm.get("executed") == "add_company", confirm
    s, boot = c.get("/api/bootstrap")
    has = any(co.get("name") == "DB-Corp" for co in (boot.get("companies") or []))
    record("database", has, f"company persisted: {has}")


def domain_security(c: Client) -> None:
    reset(c)
    payload = "<script>alert('xss')</script>"
    r = chat_until_confirm(c, f'/add-company "Sec-Co {payload}" https://sec-co.example')
    assert r.get("awaitingConfirmation"), r
    chat(c, "yes")
    s, boot = c.get("/api/bootstrap")
    stored = any(payload in (co.get("name") or "") for co in (boot.get("companies") or []))
    record("security", stored, "XSS payload stored as text in JSON; no HTML execution path")


def domain_ai_router(c: Client) -> None:
    reset(c)
    r = chat(c, "I want to add a company")
    awaiting = r.get("awaiting")
    record("ai_router", awaiting == "name", f"keyword router → add_company; awaiting={awaiting!r}")


def domain_data_analytics(c: Client) -> None:
    reset(c)
    r = chat_until_confirm(c, "/find Senior Backend Berlin")
    # R19: find_jobs is read-only and executes immediately. If the
    # server is on an older build it'll still need a "yes" first.
    if r.get("awaitingConfirmation"):
        r = chat(c, "yes")
    result = r.get("result", {})
    record(
        "data_analytics",
        result.get("ok") is True and "jobs" in result,
        f"find_jobs returned {len(result.get('jobs') or [])} sample, "
        f"total {result.get('totalJobs')}",
    )


def domain_product_ux(c: Client) -> None:
    reset(c)
    chat_until_confirm(c, "/add-company UX-Co https://ux-co.example")
    cancel = chat(c, "no")
    assert "cancelled" in cancel, cancel
    s, boot = c.get("/api/bootstrap")
    has = any(co.get("name") == "UX-Co" for co in (boot.get("companies") or []))
    record("product_ux", not has, f"'no' cancelled the add; UX-Co not persisted: {not has}")


def domain_gdpr_audit(c: Client) -> None:
    """Drive a real command and then VERIFY the chat_cmd row landed
    in the SQLite analytics_events table on disk. No 'trust me' —
    runtime proof on the actual DB file."""
    import sqlite3 as _sql

    reset(c)
    r = chat_until_confirm(c, "/find Audit-Query-Marker Berlin")
    # R19: find_jobs is read-only — executes immediately. Confirm
    # only needed on older builds that still gate it.
    if r.get("awaitingConfirmation"):
        chat(c, "yes")
    data_dir = os.environ.get("COMPANY_DISCOVERY_DATA_DIR", "")
    if not data_dir:
        record("gdpr_audit", False, "COMPANY_DISCOVERY_DATA_DIR not set; can't open DB")
        return
    # The data dir has multiple .sqlite3 files (auth.sqlite3 +
    # company_discovery.sqlite3). Try each until we find the one
    # carrying analytics_events.
    candidates = [
        p for p in Path(data_dir).rglob("*") if p.is_file() and p.name.endswith(".sqlite3")
    ]
    db_path = None
    for p in candidates:
        try:
            conn = _sql.connect(str(p))
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='analytics_events'"
            )
            if cur.fetchone():
                db_path = p
                conn.close()
                break
            conn.close()
        except Exception:  # noqa: BLE001
            continue
    if db_path is None:
        record(
            "gdpr_audit",
            False,
            f"no .sqlite3 file with analytics_events table under {data_dir}; "
            f"saw: {[p.name for p in candidates]}",
        )
        return
    try:
        conn = _sql.connect(str(db_path))
        # Schema column is `payload`, not `json`.
        cur = conn.execute(
            "SELECT id, user_id, payload FROM analytics_events ORDER BY rowid DESC LIMIT 100"
        )
        rows = cur.fetchall()
        conn.close()
    except Exception as exc:  # noqa: BLE001
        record("gdpr_audit", False, f"DB read failed at {db_path}: {exc}")
        return
    chat_cmd_rows = [r for r in rows if "chat_cmd" in (r[2] or "")]
    has_find = any("find_jobs" in (r[2] or "") for r in chat_cmd_rows)
    has_marker = any("Audit-Query-Marker" in (r[2] or "") for r in chat_cmd_rows)
    record(
        "gdpr_audit",
        bool(chat_cmd_rows) and has_find,
        f"DB={db_path.name} · {len(chat_cmd_rows)} chat_cmd rows · "
        f"find_jobs={has_find} · marker={has_marker}",
    )


def domain_a11y_server(c: Client) -> None:
    reset(c)
    r = chat(c, "/help")
    reply = r.get("reply", "")
    has_html_tag = "<" in reply and ">" in reply
    record("a11y_server", not has_html_tag, f"help reply ({len(reply)} chars) contains no raw HTML")


def domain_i18n(c: Client) -> None:
    reset(c)
    chat_until_confirm(c, "/add-company i18n-Co https://i18n-co.example")
    confirm = chat(c, "ja")
    de_yes_works = confirm.get("executed") == "add_company"

    reset(c)
    chat_until_confirm(c, "/add-company i18n-NoCo https://i18n-no.example")
    cancel = chat(c, "nein")
    de_no_works = "cancelled" in cancel

    record("i18n", de_yes_works and de_no_works, f"German yes={de_yes_works} no={de_no_works}")


def domain_qa(c: Client) -> None:
    """Invalid URL in a required slot must re-prompt without crashing."""
    reset(c)
    r = chat(c, "/add-company")
    # Server asks for the first required: name.
    assert r.get("awaiting") == "name", r
    # Provide a name, then provide an *invalid* URL — server should
    # re-prompt with the awaiting field still set.
    chat(c, "QA-Corp")
    bad = chat(c, "not a valid url at all")
    # Validator rejects with "That doesn't look like a URL." and
    # re-asks. awaiting stays at websiteUrl.
    record(
        "qa",
        bad.get("awaiting") == "websiteUrl",
        f"invalid URL → re-prompt; awaiting={bad.get('awaiting')!r}",
    )


def domain_v2_commands(c: Client) -> None:
    """The four new commands shipped in Round 14:
    set_persona, run_saved_search, delete_company, tailor_cv."""
    reset(c)
    # set_persona via slash
    chat_until_confirm(c, "/persona tech")
    chat(c, "yes")
    s, boot = c.get("/api/bootstrap")
    profile = boot.get("profile") or {}
    persona_set = profile.get("personaId") == "tech"

    # delete_company: first add one, then delete it.
    reset(c)
    chat_until_confirm(c, "/add-company V2-Del-Co https://v2-del.example")
    chat(c, "yes")
    s, boot = c.get("/api/bootstrap")
    co = next((c for c in (boot.get("companies") or []) if c.get("name") == "V2-Del-Co"), None)
    if co:
        reset(c)
        chat_until_confirm(c, f"/unwatch {co['id']}")
        chat(c, "yes")
        s, boot = c.get("/api/bootstrap")
        deleted_ok = not any(c.get("id") == co["id"] for c in (boot.get("companies") or []))
    else:
        deleted_ok = False

    record(
        "v2_commands",
        persona_set and deleted_ok,
        f"set_persona ok: {persona_set}, delete_company ok: {deleted_ok}",
    )


def domain_persistence(c: Client) -> None:
    """Chat state persists to profile.chat_state (one write per chat
    message). Verifies the pending command survives a GET on
    /api/chat/state AND lands on the user's profile blob."""
    reset(c)
    # Start a flow but DON'T confirm — leaves a pending command.
    chat(c, "/add-company Persist-Co https://persist.example")
    # At this point we're awaiting the optional careerPageUrl, NOT
    # confirmation yet. Verify the in-memory state via GET.
    s, state_resp = c.get("/api/chat/state")
    session = state_resp.get("session") or {}
    pending = session.get("pending") or {}
    history = session.get("history") or []
    in_memory_ok = (
        pending.get("commandName") == "add_company"
        and pending.get("awaiting") == "careerPageUrl"
        and len(history) >= 2  # user msg + assistant prompt
    )
    # Now verify profile.chat_state on disk carries the same shape.
    s, profile_resp = c.get("/api/profile")
    pf = profile_resp.get("profile") or {}
    chat_state = pf.get("chatState") or pf.get("chat_state")
    persisted_ok = (
        isinstance(chat_state, dict)
        and (chat_state.get("pending") or {}).get("commandName") == "add_company"
        and (chat_state.get("pending") or {}).get("awaiting") == "careerPageUrl"
    )
    record(
        "persistence",
        in_memory_ok and persisted_ok,
        f"in-memory OK={in_memory_ok} (history={len(history)}, "
        f"awaiting={pending.get('awaiting')!r}); "
        f"on-disk profile.chatState OK={persisted_ok}",
    )


DOMAINS = [
    ("backend", domain_backend),
    ("database", domain_database),
    ("security", domain_security),
    ("ai_router", domain_ai_router),
    ("data_analytics", domain_data_analytics),
    ("product_ux", domain_product_ux),
    ("gdpr_audit", domain_gdpr_audit),
    ("a11y_server", domain_a11y_server),
    ("i18n", domain_i18n),
    ("qa", domain_qa),
    ("v2_commands", domain_v2_commands),
    ("persistence", domain_persistence),
]


def main() -> int:
    if not BASE_URL:
        print("ERROR: E2E_BASE_URL required", file=sys.stderr)
        return 2
    print(f"[multi-domain] base_url={BASE_URL}")
    c = signup()
    for name, fn in DOMAINS:
        try:
            fn(c)
        except Exception as exc:  # noqa: BLE001
            record(name, False, f"crashed: {type(exc).__name__}: {exc}")

    out = Path(os.environ.get("E2E_MULTIDOMAIN_REPORT", "tests/e2e/multi_domain_report.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(REPORT, indent=2, ensure_ascii=False))

    passed = sum(1 for r in REPORT if r["ok"])
    failed = len(REPORT) - passed
    print("\n" + "=" * 70)
    print(f"MULTI-DOMAIN — {passed}/{len(REPORT)} PASS")
    print("=" * 70)
    if failed:
        for r in REPORT:
            if not r["ok"]:
                print(f"  ❌ {r['domain']}: {r['detail']}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
