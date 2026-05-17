"""R23.8 — end-to-end probe for the LLM response cache.

Verifies that:
  1. The same chat question asked twice triggers exactly ONE HTTP
     call to the (stubbed) provider.
  2. The /api/admin/llm-costs endpoint reports hits >= 1.
  3. The second-turn reply matches the first (cache served the
     same payload).

Per the vision: "Cost engineering is server-side and invisible —
prompt caching, response caching keyed on context hash."
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_cache_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)
os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-ant-stub"
os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "anthropic"
os.environ["DIRECTJOB_REGISTER_LIMIT"] = "999"
os.environ["DIRECTJOB_ALLOW_REGISTRATION"] = "true"
os.environ.pop("DIRECTJOB_LLM_DAILY_CAP", None)

import app  # noqa: E402
from company_discovery import tool_use_router as TUR  # noqa: E402
from company_discovery.tool_use_router import LLMTurn  # noqa: E402


# Count how many times the HTTP layer is hit.
HTTP_HITS = {"n": 0}


def _counting_http(url, headers, body, timeout=None):
    HTTP_HITS["n"] += 1
    return 200, {
        "content": [{"type": "text",
                      "text": "Hello — I'm DirectJob Scout."}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 120, "output_tokens": 45},
    }


def _start_server() -> int:
    import http.server
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.4)
    return port


def _post(port, path, payload, cookie=None, csrf=None):
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    if csrf:
        headers["X-CSRF-Token"] = csrf
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=body, method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return (resp.status,
                json.loads(resp.read().decode("utf-8")),
                resp.headers.get("Set-Cookie") or "")


def _get(port, path, cookie, csrf):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        headers={"Cookie": cookie, "X-CSRF-Token": csrf})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def main() -> int:
    # Patch the lowest-level HTTP call. The router's adapter checks
    # the cache BEFORE calling _http_post_json — so cache hits will
    # bypass this counter entirely.
    TUR._http_post_json = _counting_http  # type: ignore[assignment]
    port = _start_server()
    print(f"[probe] server up on http://127.0.0.1:{port}")
    findings: list[str] = []

    # Two FRESH users sending the same first message. Empty history
    # + same defaults → same system prompt + same messages → same
    # cache key → second user's call should be cache-served.
    def _register(email):
        s, b, c = _post(port, "/api/auth/register", {
            "email": email, "password": "cache-pass-9X",
            "tosAccepted": True, "privacyAccepted": True,
        })
        return (b.get("user") or {}).get("csrfToken") or "", c.split(";")[0]

    csrf_a, cookie_a = _register(f"a+{secrets.token_hex(2)}@example.com")
    csrf_b, cookie_b = _register(f"b+{secrets.token_hex(2)}@example.com")

    HTTP_HITS["n"] = 0

    msg = "hi"
    s1, body1, _ = _post(port, "/api/chat/message",
                            {"message": msg},
                            cookie=cookie_a, csrf=csrf_a)
    print(f"[probe] user A {msg!r} → status={s1} "
          f"reply={(body1.get('reply') or '')[:60]!r}")
    s2, body2, _ = _post(port, "/api/chat/message",
                            {"message": msg},
                            cookie=cookie_b, csrf=csrf_b)
    print(f"[probe] user B {msg!r} → status={s2} "
          f"reply={(body2.get('reply') or '')[:60]!r}")
    cookie, csrf = cookie_a, csrf_a  # for the admin GET below

    if s1 != 200 or s2 != 200:
        findings.append(f"chat returned {s1}/{s2}")
    # Both replies must be identical (cache returned same payload).
    if (body1.get("reply") or "").strip() != (body2.get("reply") or "").strip():
        findings.append(
            f"replies differed: {body1.get('reply')!r} vs {body2.get('reply')!r}")
    # CRITICAL: only 1 HTTP hit despite 2 chats — the cache worked.
    if HTTP_HITS["n"] != 1:
        findings.append(
            f"expected 1 HTTP hit (cache should serve the 2nd), "
            f"got {HTTP_HITS['n']}")
    else:
        print(f"[probe] 2 chats produced 1 HTTP hit — cache served the 2nd ✓")

    # Admin dashboard must report cache stats.
    s, dash = _get(port, "/api/admin/llm-costs", cookie, csrf)
    cache_stats = dash.get("responseCache") or {}
    print(f"[probe] /api/admin/llm-costs responseCache: {cache_stats}")
    if (cache_stats.get("hits") or 0) < 1:
        findings.append(
            f"dashboard hit count {cache_stats.get('hits')}, expected >=1")
    if (cache_stats.get("hit_rate") or 0) < 0.4:
        # 1 hit / 2 lookups should be ≥ 0.5 (and at most 1.0).
        findings.append(
            f"hit_rate={cache_stats.get('hit_rate')}, expected ~0.5")

    print()
    print("=" * 60)
    if findings:
        print(f"RESPONSE CACHE PROBE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("RESPONSE CACHE PROBE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
