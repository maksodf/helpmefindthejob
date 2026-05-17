"""R23.6 — end-to-end probe for the LLM cost tracker + admin endpoint.

Boots the server with a stubbed Anthropic adapter that reports
realistic token counts, drives an admin user through a chat call
that invokes the LLM, then queries the /api/admin/llm-costs endpoint
and asserts the spend was captured.
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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import shutil
import tempfile
PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_cost_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)
os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-ant-stub"
os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "anthropic"
os.environ["DIRECTJOB_REGISTER_LIMIT"] = "999"
os.environ["DIRECTJOB_ALLOW_REGISTRATION"] = "true"
# Disable per-user cap for the probe so we can verify cost tracking
# end-to-end without being blocked by R22.9's daily limit.
os.environ["DIRECTJOB_LLM_DAILY_CAP"] = "0"

import app  # noqa: E402
from company_discovery import tool_use_router as TUR  # noqa: E402
from company_discovery.tool_use_router import LLMTurn, ToolCall  # noqa: E402


def _fake_anthropic(api_key, model, system, messages, tools, **_kw):
    """Stubbed adapter that fakes a realistic 500-in / 200-out call."""
    last = messages[-1] if messages else {}
    if (isinstance(last.get("content"), list) and last["content"]
            and last["content"][0].get("type") == "tool_result"):
        return LLMTurn(text="Done — top 5 in your dashboard.",
                        stop_reason="end_turn",
                        raw_provider="anthropic",
                        model_used=model,
                        input_tokens=500, output_tokens=180)
    return LLMTurn(
        text="",
        tool_calls=[ToolCall(id="t1", name="find_jobs",
                              args={"persona_id": "bartender"})],
        stop_reason="tool_use",
        raw_provider="anthropic",
        model_used=model,
        input_tokens=420, output_tokens=85,
    )


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
        raw = resp.read().decode("utf-8")
        return resp.status, json.loads(raw), resp.headers.get("Set-Cookie") or ""


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

    # Register the bootstrap user (admin).
    email = f"admin-{secrets.token_hex(2)}@example.com"
    status, body, set_cookie = _post(port, "/api/auth/register", {
        "email": email, "password": "admin-pass-9X",
        "tosAccepted": True, "privacyAccepted": True,
    })
    if status != 201:
        print(f"register failed: {status} {body}")
        return 1
    cookie = set_cookie.split(";")[0]
    csrf = (body.get("user") or {}).get("csrfToken") or ""
    is_admin = (body.get("user") or {}).get("role") == "admin"
    print(f"[probe] registered {email} (admin={is_admin})")

    # Fire two chats — each triggers a tool-use loop (2 LLM calls per
    # chat = 4 calls total, ~1000 in / ~400 out).
    for i in range(2):
        status, _, _ = _post(port, "/api/chat/message",
                                {"message": f"find me a bartender job {i}"},
                                cookie=cookie, csrf=csrf)
        if status != 200:
            print(f"chat {i} failed: {status}")
            return 1
    print("[probe] 2 chats fired — 4 LLM calls total expected")

    # Query the cost dashboard endpoint.
    status, dash = _get(port, "/api/admin/llm-costs", cookie, csrf)
    if status != 200:
        print(f"dashboard query failed: {status} {dash}")
        return 1

    today = dash.get("today") or {}
    total = today.get("total_usd") or 0
    print(f"\n[probe] /api/admin/llm-costs returned:")
    print(f"  total_usd today: ${total:.6f}")
    print(f"  by_provider: {today.get('by_provider')}")
    print(f"  by_task: {today.get('by_task')}")
    print(f"  by_model: {today.get('by_model')}")
    print(f"  top_users: {today.get('top_users')}")
    print(f"  last7Days length: {len(dash.get('last7Days') or [])}")

    findings: list[str] = []
    if total <= 0:
        findings.append(f"total_usd is {total}, expected > 0")
    if not today.get("by_provider"):
        findings.append("by_provider is empty")
    elif today["by_provider"][0]["provider"] != "anthropic":
        findings.append(f"provider mismatch: {today['by_provider']}")
    by_task = {r["task"]: r["calls"]
                for r in (today.get("by_task") or [])}
    if "tool_use_chat" not in by_task:
        findings.append(f"tool_use_chat task missing in {by_task}")
    elif by_task["tool_use_chat"] < 4:
        findings.append(
            f"expected at least 4 tool_use_chat calls, got {by_task['tool_use_chat']}")

    print()
    print("=" * 60)
    if findings:
        print(f"COST DASHBOARD PROBE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("COST DASHBOARD PROBE — PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
