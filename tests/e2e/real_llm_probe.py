"""Real-LLM end-to-end probe for the chat AI router.

Driven by ``scripts/probe-ai-router.sh``. Sends 5 natural-language
probes through ``/api/chat/message`` against a server configured with
a real managed AI key, and reports which command each one routed to.

The probes are written so that a competent LLM (claude-haiku, gpt-4o-
mini, gemini-flash, etc.) should classify them correctly. A model
that routes < 4/5 either has the prompt wrong, is the wrong model, or
the integration is broken — all of which the operator wants to know
BEFORE shipping the router to testers.

This script is NOT run as part of the unit suite. It requires a real
API key + an external network call."""

from __future__ import annotations

import json
import os
import secrets
import sys
import urllib.error
import urllib.request

BASE_URL = os.environ.get("E2E_BASE_URL", "").rstrip("/")

# (probe, expected_command, optional_arg_assert)
PROBES: list[tuple[str, str, dict | None]] = [
    ("I need you to generate a CV for me", "open_cv_builder", None),
    ("Watch Charité, their career page is https://karriere.charite.de",
     "add_company", {"name": "Charité"}),
    ("Find me senior backend roles in Berlin", "find_jobs",
     {"query": "senior backend"}),
    ("Switch my persona to tech", "set_persona", {"persona": "tech"}),
    ("Show me what you can do", "help", None),
]


class _C:
    def __init__(self):
        self.cookie = ""
        self.csrf = ""

    def _req(self, m, p, body=None):
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.csrf and m != "GET":
            headers["X-CSRF-Token"] = self.csrf
        req = urllib.request.Request(BASE_URL + p, data=data, method=m,
                                       headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                sc = resp.headers.get("Set-Cookie", "")
                if sc:
                    self.cookie = sc.split(";", 1)[0]
                raw = resp.read().decode("utf-8", errors="replace")
                try: p = json.loads(raw) if raw else {}
                except json.JSONDecodeError: p = raw
                if isinstance(p, dict):
                    for k in ("csrfToken", "csrf_token"):
                        if isinstance(p.get(k), str) and p[k]:
                            self.csrf = p[k]; break
                    u = p.get("user") or {}
                    if isinstance(u, dict):
                        for k in ("csrfToken", "csrf_token"):
                            if isinstance(u.get(k), str) and u[k]:
                                self.csrf = u[k]; break
                return resp.status, p
        except urllib.error.HTTPError as e:
            raw = e.read().decode() if e.fp else ""
            try: return e.code, json.loads(raw) if raw else {}
            except json.JSONDecodeError: return e.code, raw


def main() -> int:
    if not BASE_URL:
        print("ERROR: E2E_BASE_URL required", file=sys.stderr)
        return 2
    c = _C()
    c._req("GET", "/")
    s, p = c._req("POST", "/api/auth/register", {
        "email": f"llm-probe+{secrets.token_hex(3)}@example.com",
        "password": "llm-probe-pass-99-X",
        "tosAccepted": True, "privacyAccepted": True,
    })
    if s not in (200, 201):
        print(f"ERROR: register {s} {p}", file=sys.stderr)
        return 1

    correct = 0
    print(f"\nProbing real LLM via configured managed provider...\n")
    for i, (probe, expected, arg_check) in enumerate(PROBES, 1):
        # Reset chat state between probes so no cross-talk.
        c._req("POST", "/api/chat/reset", {})
        s, resp = c._req("POST", "/api/chat/message", {"message": probe})
        if s != 200:
            print(f"  ❌ probe #{i}: HTTP {s} — {resp}")
            continue

        # Inspect the session.pending to see what command was queued.
        session = (resp.get("session") or {})
        pending = session.get("pending") or {}
        routed_command = pending.get("commandName")
        routed_args = pending.get("args") or {}

        # The `help` command executes immediately (no params), so the
        # session won't have a pending entry — check `executed` instead.
        if expected == "help":
            routed_command = resp.get("executed") or routed_command

        verdict = "✅" if routed_command == expected else "❌"
        if routed_command == expected:
            correct += 1
        print(f"  {verdict} probe #{i}: {probe!r}")
        print(f"       expected={expected!r}  got={routed_command!r}")
        if arg_check:
            for k, v in arg_check.items():
                got = routed_args.get(k)
                ok = isinstance(got, str) and v.casefold() in got.casefold()
                af = "✅" if ok else "⚠️"
                print(f"       {af} arg {k}={got!r}  (wanted contains {v!r})")

    print(f"\n{correct}/{len(PROBES)} probes routed correctly.")
    return 0 if correct >= 4 else 1


if __name__ == "__main__":
    sys.exit(main())
