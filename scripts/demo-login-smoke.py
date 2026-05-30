#!/usr/bin/env python3
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Demo-login smoke check — one command, clear per-persona pass/fail.

Confirms that every seeded demo persona can actually log in to a running
instance via the real ``POST /api/auth/login`` endpoint. This is the
operator's pre-submission check that the live demo accounts work
(`scripts/seed-personas.py` creates them; this script proves they log in).

What it does
------------
For each of the seven canonical personas (sourced from
``company_discovery.persona_fixtures.PERSONAS`` so the check follows the
panel if it changes), POST the persona's demo email + the demo password to
``<base-url>/api/auth/login`` and classify the result:

  PASS  — HTTP 200 with a ``user`` payload and a session ``Set-Cookie``.
  FAIL  — invalid credentials (401), email-unverified (403), 2FA-required,
          rate-limited (429), unreachable host, or any other response.

Each failure prints an operator-actionable reason. Exit code is 0 only if
ALL personas log in; non-zero otherwise (so it can gate a deploy script).

Usage
-----
    python3 scripts/demo-login-smoke.py \\
        --base-url https://demo.your-deployment.org \\
        --password '<the demo password you seeded with>'

    # options:
    --email-domain DOMAIN   Demo-account email domain (default:
                            demo.helpmefindthejob.org; must match the
                            --email-domain used at seed time).
    --timeout SECONDS       Per-request timeout (default 15).

TLS is always verified (the password is transmitted on login). Use a
properly-issued certificate; for a self-signed staging cert, add its CA to
the trust store rather than disabling verification.

Operator boundary
-----------------
This script must be run by the operator against THEIR deployed instance —
the maintainer/agent cannot reach a private demo URL. Everything up to that
remote call is automated and tested (see tests/test_demo_login_smoke.py).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Make the script importable from a clean checkout (scripts/ -> repo root).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from company_discovery.persona_fixtures import PERSONAS, demo_email
except Exception as exc:  # pragma: no cover - import guard for odd checkouts
    print(f"FATAL: cannot import persona fixtures ({exc}). "
          f"Run this from the repository root.", file=sys.stderr)
    sys.exit(2)

GREEN, RED, YELLOW, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"


def _post_login(base_url: str, email: str, password: str, *, timeout: float) -> tuple[str, str]:
    """POST one login. Returns (status, detail) where status is
    'pass' / 'fail' / 'warn'. TLS is always verified (default context)."""
    url = base_url.rstrip("/") + "/api/auth/login"
    body = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            set_cookie = resp.headers.get("Set-Cookie")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                return "fail", f"HTTP 200 but non-JSON body ({raw[:60]!r})"
            if data.get("requires2fa"):
                return "warn", "credentials valid but 2FA is enabled — demo account cannot be smoke-logged-in non-interactively (disable TOTP on demo accounts)"
            if "user" in data and set_cookie:
                return "pass", "session established"
            if "user" in data and not set_cookie:
                return "fail", "HTTP 200 with user but no Set-Cookie (session not established)"
            return "fail", f"HTTP 200 but unexpected body (keys: {sorted(data)[:6]})"
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            err = json.loads(raw).get("error") or json.loads(raw).get("detail") or ""
        except json.JSONDecodeError:
            err = raw[:80]
        if e.code == 401:
            return "fail", "401 invalid_login — account not seeded, or wrong --password / --email-domain"
        if e.code == 403 and "unverified" in raw:
            return "fail", "403 email_unverified — verify the demo accounts, or set HELPMEFINDTHEJOB_REQUIRE_EMAIL_VERIFICATION=false for the demo deployment"
        if e.code == 429:
            return "fail", "429 rate_limited — per-IP failed-login cap hit; wait and retry, or whitelist your IP"
        return "fail", f"HTTP {e.code} {err}".strip()
    except urllib.error.URLError as e:
        return "fail", f"cannot reach {url} ({e.reason})"
    except Exception as e:  # pragma: no cover - defensive
        return "fail", f"unexpected error: {e}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Demo-login smoke check (per-persona pass/fail).")
    ap.add_argument("--base-url", required=True, help="Base URL of the running instance, e.g. https://demo.example.org")
    ap.add_argument("--password", required=True, help="The demo password the personas were seeded with")
    ap.add_argument("--email-domain", default="demo.helpmefindthejob.org",
                    help="Demo-account email domain (must match seed-personas --email-domain)")
    ap.add_argument("--timeout", type=float, default=15.0, help="Per-request timeout in seconds")
    args = ap.parse_args()

    print(f"Demo-login smoke → {args.base_url}  ({len(PERSONAS)} personas, domain @{args.email_domain})\n")
    results: list[tuple[str, str, str]] = []
    for persona in PERSONAS:
        email = demo_email(persona.slug, args.email_domain)
        status, detail = _post_login(args.base_url, email, args.password,
                                     timeout=args.timeout)
        mark = {"pass": f"{GREEN}✓ PASS{RESET}", "fail": f"{RED}✗ FAIL{RESET}",
                "warn": f"{YELLOW}⚠ WARN{RESET}"}[status]
        print(f"  {mark}  {persona.slug:9} {email:42} {detail}")
        results.append((persona.slug, status, detail))

    passed = sum(1 for _, s, _ in results if s == "pass")
    total = len(results)
    print()
    if passed == total:
        print(f"{GREEN}{passed}/{total} demo personas logged in successfully.{RESET}")
        return 0
    failed = [slug for slug, s, _ in results if s != "pass"]
    print(f"{RED}{passed}/{total} logged in — {len(failed)} did NOT: {', '.join(failed)}{RESET}")
    print("Demo logins must all pass before the submission demo is reviewer-ready.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
