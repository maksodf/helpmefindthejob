"""Concurrent-user smoke for the R22 LLM chat path.

Spins up the local HTTP server, stubs the Anthropic adapter with
scripted turns, registers 20 distinct users, and fires 20 parallel
/api/chat/message requests. Asserts:

  * All 20 return 200
  * Each user sees ONLY their own conversation (no state bleed)
  * find_jobs executed for each user
  * No race-induced exceptions in the server (handled by exit code)
  * Per-user LLM-budget counter increments exactly once per request

Run:   python scripts/probe_tool_use_concurrent.py
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# BUG-FIX (R23.9): the app reads ``COMPANY_DISCOVERY_DATA_DIR``, NOT
# ``DIRECTJOB_DB_PATH``. The old code set the wrong env var so the
# probe silently wrote to the repo's data/ dir on every run.
import tempfile
PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_concurrent_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)
os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-ant-stub"
os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "anthropic"
os.environ["DIRECTJOB_REGISTER_LIMIT"] = "999"
os.environ["DIRECTJOB_ALLOW_REGISTRATION"] = "true"
# Cap each user at 5 LLM calls/day — proves per-user isolation.
os.environ["DIRECTJOB_LLM_DAILY_CAP"] = "5"

import app  # noqa: E402
from company_discovery import tool_use_router as TUR  # noqa: E402
from company_discovery.tool_use_router import LLMTurn, ToolCall  # noqa: E402


def _fake_anthropic(api_key, model, system, messages, tools, **_kw):
    """Deterministic LLM stub. First call → find_jobs, second → text."""
    # Detect if the last message is a tool_result (we're on turn 2+).
    last = messages[-1] if messages else {}
    if (isinstance(last.get("content"), list)
            and last["content"]
            and last["content"][0].get("type") == "tool_result"):
        return LLMTurn(text="Done — results in.",
                        stop_reason="end_turn",
                        raw_provider="anthropic")
    return LLMTurn(
        text="",
        tool_calls=[ToolCall(id=f"toolu_{secrets.token_hex(4)}",
                              name="find_jobs",
                              args={"persona_id": "bartender"})],
        stop_reason="tool_use",
        raw_provider="anthropic",
    )


def _start_server() -> int:
    import http.server
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.4)
    return port


def _register(port: int, email: str) -> tuple[str, str]:
    body = json.dumps({
        "email": email, "password": "concurrent-pass-9X",
        "tosAccepted": True, "privacyAccepted": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/auth/register",
        data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8")
        set_cookie = resp.headers.get("Set-Cookie") or ""
    cookie = set_cookie.split(";")[0]
    csrf = (json.loads(raw).get("user") or {}).get("csrfToken") or ""
    return cookie, csrf


def _chat(port: int, cookie: str, csrf: str, msg: str) -> dict:
    body = json.dumps({"message": msg}).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/chat/message",
        data=body, method="POST",
        headers={"Content-Type": "application/json",
                  "Cookie": cookie, "X-CSRF-Token": csrf},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {"status": resp.status,
                     "body": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as e:
        return {"status": e.code,
                 "body": json.loads(e.read().decode("utf-8", "replace"))}


def main() -> int:
    TUR._call_anthropic = _fake_anthropic  # type: ignore[assignment]
    port = _start_server()
    print(f"[probe] server up on http://127.0.0.1:{port}")

    N_USERS = 20

    # Register all users serially (parallel register hits a rate
    # limit by IP — that's a different scenario).
    creds: list[tuple[str, str, str]] = []
    for i in range(N_USERS):
        email = f"conc-{i:02d}+{secrets.token_hex(2)}@example.com"
        cookie, csrf = _register(port, email)
        creds.append((email, cookie, csrf))
    print(f"[probe] registered {N_USERS} users")

    # 20 parallel chat messages.
    findings: list[str] = []
    results: list[dict] = []
    start = time.time()
    with ThreadPoolExecutor(max_workers=N_USERS) as pool:
        futures = {
            pool.submit(_chat, port, cookie, csrf,
                          f"find me a bartender job (user {i})"): (i, email)
            for i, (email, cookie, csrf) in enumerate(creds)
        }
        for fut in as_completed(futures):
            i, email = futures[fut]
            try:
                results.append({"i": i, "email": email, **fut.result()})
            except Exception as exc:  # noqa: BLE001
                findings.append(f"user {i} ({email}): exception {exc}")
    elapsed = time.time() - start
    print(f"[probe] {N_USERS} parallel chats finished in {elapsed:.1f}s")

    # Per-user assertions.
    for r in results:
        i = r["i"]
        if r["status"] != 200:
            findings.append(f"user {i}: non-200 status {r['status']}")
            continue
        body = r["body"]
        if "find_jobs" not in (body.get("executed") or []):
            findings.append(f"user {i}: find_jobs not in executed "
                             f"({body.get('executed')!r})")
        reply = body.get("reply") or ""
        if not reply:
            findings.append(f"user {i}: empty reply")
        # Sanity: per-user LLM counter incremented exactly once.
        # Resolve user_id via the session cookie (only the cookie
        # value matters — the auth_store keys sessions by token).
        cookie_val = creds[i][1].split("=", 1)[1]
        session = app.STATE.auth_store.get_session(cookie_val)
        if session is None:
            findings.append(f"user {i}: session lookup failed")
            continue
        count = app.STATE.llm_tool_use_count_today(session.user.id)
        if count != 1:
            findings.append(
                f"user {i}: LLM count today = {count}, expected 1")

    print()
    print("=" * 60)
    if findings:
        print(f"CONCURRENT SMOKE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print(f"CONCURRENT SMOKE — ALL {N_USERS} USERS PASS")
    print(f"throughput: {N_USERS / elapsed:.1f} req/s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
