"""R23.7 — end-to-end probe for plan-aware LLM cap enforcement.

Verifies:
  1. A workspace on the Free plan hits the 5-chat cap at the
     6th chat call (per-user counter, env override disabled).
  2. The blocked chat still 200s — falls back to deterministic
     with the "you've used today's AI chats / upgrade" note.
  3. The /api/billing response surfaces ``aiUsage.today`` so the
     frontend can render the usage indicator.
  4. Upgrading the workspace to Pro lifts the cap.
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

PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_plan_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)
os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-ant-stub"
os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "anthropic"
os.environ["DIRECTJOB_REGISTER_LIMIT"] = "999"
os.environ["DIRECTJOB_ALLOW_REGISTRATION"] = "true"
# CRITICAL: empty so the plan resolves the cap, not the env.
os.environ.pop("DIRECTJOB_LLM_DAILY_CAP", None)

import app  # noqa: E402
from company_discovery import tool_use_router as TUR  # noqa: E402
from company_discovery.tool_use_router import LLMTurn, ToolCall  # noqa: E402


def _fake_anthropic(api_key, model, system, messages, tools, **_kw):
    """Always returns text (no tool call) so each chat = 1 LLM call."""
    return LLMTurn(text="Sure — what role are you after?",
                    stop_reason="end_turn",
                    raw_provider="anthropic",
                    model_used=model,
                    input_tokens=100, output_tokens=40)


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
    TUR._call_anthropic = _fake_anthropic  # type: ignore[assignment]
    port = _start_server()
    print(f"[probe] server up on http://127.0.0.1:{port}")
    findings: list[str] = []

    # 1. Register the admin user (bootstrap path).
    email = f"plan-admin+{secrets.token_hex(2)}@example.com"
    status, body, set_cookie = _post(port, "/api/auth/register", {
        "email": email, "password": "plan-admin-pass-9X",
        "tosAccepted": True, "privacyAccepted": True,
    })
    if status != 201:
        print(f"register failed: {status} {body}")
        return 1
    cookie = set_cookie.split(";")[0]
    csrf = (body.get("user") or {}).get("csrfToken") or ""
    print(f"[probe] registered {email}")

    # 2. Move the workspace onto Free for this test.
    s, _, _ = _post(port, "/api/admin/billing",
                      {"planId": "free", "status": "active",
                        "seats": 1, "customerEmail": email},
                      cookie=cookie, csrf=csrf)
    if s != 200:
        findings.append(f"admin/billing set Free failed: {s}")

    # 3. Verify /api/billing now reports cap=5.
    s, billing = _get(port, "/api/billing", cookie, csrf)
    if s != 200:
        findings.append(f"/api/billing got {s}")
    elif billing.get("aiUsage", {}).get("dailyCap") != 5:
        findings.append(f"expected cap=5 on Free, got "
                         f"{billing.get('aiUsage', {}).get('dailyCap')}")
    else:
        print(f"[probe] /api/billing reports cap=5, today=0 ✓")

    # 4. Burn through 5 chats on Free — all should succeed.
    fail_count = 0
    for i in range(5):
        s, body, _ = _post(port, "/api/chat/message",
                              {"message": f"hi {i}"},
                              cookie=cookie, csrf=csrf)
        if s != 200:
            findings.append(f"chat {i} unexpectedly failed: {s}")
        # Each chat should produce an LLM reply (not fallback note).
        if "running the simple chat" in (body.get("reply") or "").lower():
            fail_count += 1
    if fail_count > 0:
        findings.append(f"{fail_count}/5 free-cap chats already saw "
                         "the upgrade note (cap fired too early)")
    print(f"[probe] 5 chats on Free fired — no premature blocking")

    # 5. The 6th chat must hit the cap → fallback note present.
    s, body, _ = _post(port, "/api/chat/message",
                          {"message": "one more"},
                          cookie=cookie, csrf=csrf)
    reply = body.get("reply") or ""
    print(f"[probe] 6th chat reply: {reply[:100]!r}")
    if s != 200:
        findings.append(f"6th chat returned {s}, expected 200")
    if "today's ai chats" not in reply.lower():
        findings.append(f"6th chat missing quota note. Reply: {reply!r}")
    if "#billing" not in reply.lower() and "upgrade" not in reply.lower():
        findings.append("6th chat missing upgrade nudge")

    # 6. /api/billing usage should now show today=5 (the 6th was
    # rejected and didn't increment).
    s, billing = _get(port, "/api/billing", cookie, csrf)
    used = billing.get("aiUsage", {}).get("today")
    if used != 5:
        findings.append(f"usage.today=={used}, expected 5")
    else:
        print(f"[probe] /api/billing reports today=5 ✓")

    # 7. Upgrade to Pro — quota should lift to 50.
    s, _, _ = _post(port, "/api/admin/billing",
                      {"planId": "pro_monthly", "status": "active",
                        "seats": 1, "customerEmail": email},
                      cookie=cookie, csrf=csrf)
    if s != 200:
        findings.append(f"upgrade to Pro failed: {s}")
    s, billing = _get(port, "/api/billing", cookie, csrf)
    if billing.get("aiUsage", {}).get("dailyCap") != 50:
        findings.append(f"after Pro upgrade, cap={billing.get('aiUsage', {}).get('dailyCap')}, expected 50")
    else:
        print(f"[probe] after upgrade /api/billing reports cap=50 ✓")

    # 8. Pro user can chat again past the old free cap.
    s, body, _ = _post(port, "/api/chat/message",
                          {"message": "now on Pro"},
                          cookie=cookie, csrf=csrf)
    reply = body.get("reply") or ""
    if "today's ai chats" in reply.lower():
        findings.append("Pro user STILL got the cap note — upgrade "
                         "didn't lift the limit")
    else:
        print(f"[probe] Pro chat replied: {reply[:80]!r}")

    print()
    print("=" * 60)
    if findings:
        print(f"PLAN CAP ENFORCEMENT — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("PLAN CAP ENFORCEMENT — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
