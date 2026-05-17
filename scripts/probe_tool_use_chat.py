"""Live runtime probe for the R22 LLM tool-use chat path.

Starts the HTTP server on localhost, monkey-patches the Anthropic
adapter with a scripted LLMTurn sequence (so no real API key is
needed), registers a user, sends two chat messages, and prints the
JSON the client would receive. Exits non-zero if the LLM path
didn't fire or the response shape isn't what the frontend expects.

Usage:
    python scripts/probe_tool_use_chat.py
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# BUG-FIX (R23.9): the app reads ``COMPANY_DISCOVERY_DATA_DIR``, NOT
# ``DIRECTJOB_DB_PATH``. The old code set the wrong env var and the
# probe silently wrote to the repo's data/ directory, polluting the
# dev DB across runs. Use a per-run tempdir for full isolation.
import tempfile
PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_chat_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)
os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-ant-test-stub"
os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "anthropic"
os.environ["DIRECTJOB_MANAGED_AI_MODEL"] = "claude-test"
os.environ["DIRECTJOB_REGISTER_LIMIT"] = "999"
os.environ["DIRECTJOB_ALLOW_REGISTRATION"] = "true"

import app  # noqa: E402
from company_discovery import tool_use_router as TUR  # noqa: E402
from company_discovery.tool_use_router import LLMTurn, ToolCall  # noqa: E402


SCRIPTED_TURNS = iter([])


def _fake_anthropic(api_key, model, system, messages, tools, **_kw):
    """Pull the next scripted LLMTurn so the probe is deterministic."""
    try:
        return next(SCRIPTED_TURNS)
    except StopIteration:
        return LLMTurn(text="(probe ran out of script)",
                        stop_reason="end_turn",
                        raw_provider="anthropic")


def _start_server() -> int:
    """Launch the HTTP server on a random localhost port. Returns port."""
    import http.server
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0),
                                              app.Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.4)
    return port


def _post(port: int, path: str, payload: dict,
           cookie: str | None = None,
           csrf: str | None = None) -> tuple[int, dict, str]:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    if csrf:
        headers["X-CSRF-Token"] = csrf
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=body, method="POST", headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            set_cookie = resp.headers.get("Set-Cookie") or ""
            try:
                return resp.status, json.loads(raw), set_cookie
            except json.JSONDecodeError:
                return resp.status, {"raw": raw}, set_cookie
    except urllib.error.HTTPError as e:  # noqa: F821
        return e.code, {"err": e.read().decode("utf-8", errors="replace")}, ""


def main() -> int:
    TUR._call_anthropic = _fake_anthropic  # type: ignore[assignment]

    port = _start_server()
    print(f"[probe] server up on http://127.0.0.1:{port}", flush=True)

    email = f"probe-{secrets.token_hex(3)}@example.com"
    status, body, set_cookie = _post(port, "/api/auth/register", {
        "email": email, "password": "probe-pass-9X",
        "tosAccepted": True, "privacyAccepted": True,
    })
    if status not in (200, 201):
        print(f"[probe] register failed: {status} {body}")
        return 1
    print(f"[probe] registered {email} status={status}", flush=True)
    csrf = (body.get("user") or {}).get("csrfToken") or body.get("csrfToken") or ""
    cookie = set_cookie.split(";")[0] if set_cookie else ""
    if not cookie or not csrf:
        status, body, set_cookie = _post(port, "/api/auth/login", {
            "email": email, "password": "probe-pass-9X",
        })
        cookie = set_cookie.split(";")[0] if set_cookie else cookie
        csrf = (body.get("user") or {}).get("csrfToken") or body.get("csrfToken") or csrf
    print(f"[probe] auth cookie acquired: {cookie[:40]}…", flush=True)
    print(f"[probe] csrf token: {csrf[:16]}…", flush=True)
    assert cookie, "no auth cookie set"
    assert csrf, "no CSRF token returned"

    # ── PROBE 1: text-only LLM reply. No tools called.
    global SCRIPTED_TURNS
    SCRIPTED_TURNS = iter([
        LLMTurn(text="Hello — I'm DirectJob Scout. What kind of role "
                       "are you after?",
                 stop_reason="end_turn", raw_provider="anthropic"),
    ])
    status, body, _ = _post(port, "/api/chat/message",
                              {"message": "hi"}, cookie=cookie, csrf=csrf)
    print(f"\n[probe-1] hi → status={status}")
    print(f"          reply: {body.get('reply', '')[:120]!r}")
    print(f"          executed: {body.get('executed')}")
    assert status == 200, f"hi probe failed: {body}"
    assert "DirectJob Scout" in body.get("reply", ""), \
        f"LLM reply text not returned: {body}"
    assert body.get("executed") == [], \
        f"expected no tool calls for 'hi', got: {body.get('executed')}"

    # ── PROBE 2: LLM picks find_jobs tool, gets result, replies.
    SCRIPTED_TURNS = iter([
        LLMTurn(text="",
                 tool_calls=[ToolCall(id="t1", name="find_jobs",
                                        args={"query": "bartender",
                                              "location": "Berlin"})],
                 stop_reason="tool_use", raw_provider="anthropic"),
        LLMTurn(text="I've searched bartender roles in Berlin — "
                       "results are on the dashboard.",
                 stop_reason="end_turn", raw_provider="anthropic"),
    ])
    status, body, _ = _post(port, "/api/chat/message",
                              {"message": "find me a bartender job in Berlin"},
                              cookie=cookie, csrf=csrf)
    print(f"\n[probe-2] find bartender → status={status}")
    print(f"          reply: {body.get('reply', '')[:120]!r}")
    print(f"          executed: {body.get('executed')}")
    print(f"          totalJobs: {body.get('totalJobs')}")
    print(f"          navigateTo: {body.get('navigateTo')}")
    assert status == 200, f"find probe failed: {body}"
    assert "find_jobs" in (body.get("executed") or []), \
        f"expected find_jobs in executed, got: {body.get('executed')}"

    # ── PROBE 3: destructive tool MUST be refused server-side.
    SCRIPTED_TURNS = iter([
        LLMTurn(text="",
                 tool_calls=[ToolCall(id="d1", name="add_company",
                                        args={"name": "AcmeCorp",
                                              "url": "https://acme.example"})],
                 stop_reason="tool_use", raw_provider="anthropic"),
        LLMTurn(text="Want me to add AcmeCorp to your watchlist? yes/no",
                 stop_reason="end_turn", raw_provider="anthropic"),
    ])
    status, body, _ = _post(port, "/api/chat/message",
                              {"message": "track acme"},
                              cookie=cookie, csrf=csrf)
    print(f"\n[probe-3] track acme → status={status}")
    print(f"          reply: {body.get('reply', '')[:120]!r}")
    print(f"          executed: {body.get('executed')}")
    print(f"          refused: {body.get('refused')}")
    assert status == 200, f"track probe failed: {body}"
    assert body.get("executed") == [], \
        f"destructive tool should NOT have executed: {body}"
    assert "add_company" in (body.get("refused") or []), \
        f"add_company should be in refused: {body.get('refused')}"

    print("\n[probe] ALL 3 PROBES OK — R22 LLM tool-use path is live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
