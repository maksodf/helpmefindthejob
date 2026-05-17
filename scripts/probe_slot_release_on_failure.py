"""Phase 1 / Step 5 — atomic-reservation release on failure.

The daily LLM call cap (Free=5, Pro=50, Power=200) is claimed BEFORE
the LLM call runs. If the LLM call itself fails (network, provider
5xx, timeout, etc.) the slot should be released so the user doesn't
lose a call to a failure that produced no value.

This probe verifies:
  1. ``claim_llm_tool_use_slot`` increments the per-user counter.
  2. ``release_llm_tool_use_slot`` decrements it.
  3. The decrement is bounded at zero (no negative counts).
  4. End-to-end via the chat HTTP path: when the LLM returns an
     error, the slot is released so a second message can still run.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_slot_release_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)
os.environ["DIRECTJOB_REGISTER_LIMIT"] = "999"
os.environ["DIRECTJOB_ALLOW_REGISTRATION"] = "true"
# Force a real daily cap so claim returns True; a real managed
# provider stub returns "llm_error" so the release path fires.
os.environ["DIRECTJOB_LLM_DAILY_CAP"] = "5"
os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-ant-stub"
os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "anthropic"

import app  # noqa: E402
from company_discovery import tool_use_router as TUR  # noqa: E402
from company_discovery.tool_use_router import (  # noqa: E402
    LLMTurn, ToolUseResult,
)


def main() -> int:
    findings: list[str] = []
    state = app.STATE

    # --- Part 1: direct claim / release unit-style ---
    user_id = "probe-slot-user"
    if not state.claim_llm_tool_use_slot(user_id):
        findings.append("claim_llm_tool_use_slot returned False unexpectedly")
        return _report(findings)
    if state.llm_tool_use_count_today(user_id) != 1:
        findings.append(
            f"after claim, count = {state.llm_tool_use_count_today(user_id)}"
            " (want 1)")
    state.release_llm_tool_use_slot(user_id)
    if state.llm_tool_use_count_today(user_id) != 0:
        findings.append(
            f"after release, count = {state.llm_tool_use_count_today(user_id)}"
            " (want 0)")
    # Release-below-zero is a no-op.
    state.release_llm_tool_use_slot(user_id)
    if state.llm_tool_use_count_today(user_id) != 0:
        findings.append(
            f"release below zero went negative: "
            f"{state.llm_tool_use_count_today(user_id)}")
    print(f"[probe] direct claim/release/floor-at-zero OK")

    # --- Part 2: end-to-end via HTTP chat ---
    # Monkey-patch run_tool_use to force an "llm_error" so the
    # release path fires.
    def _fake_run_tool_use(*args, **kwargs):
        return ToolUseResult(reply="", error="llm_error", turns_used=1)

    TUR.run_tool_use = _fake_run_tool_use  # type: ignore[assignment]
    # Re-import in app.py's lazy-import path: app.py re-imports
    # ``run_tool_use`` from the module each request, so patching the
    # attribute on the module is sufficient.

    import http.server  # noqa: E402
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.4)

    # Register an HTTP user.
    body = json.dumps({
        "email": "slot-release+probe@example.com",
        "password": "slot-release-pass-9X",
        "tosAccepted": True,
        "privacyAccepted": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/auth/register",
        data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        reg_body = json.loads(resp.read().decode("utf-8"))
        cookie = resp.headers.get("Set-Cookie").split(";")[0]
    csrf = (reg_body.get("user") or {}).get("csrfToken") or ""
    eff_uid = state.effective_user_id(reg_body["user"]["id"])

    # Count starts at 0.
    if state.llm_tool_use_count_today(eff_uid) != 0:
        findings.append(
            f"post-register count = "
            f"{state.llm_tool_use_count_today(eff_uid)} (want 0)")

    # Send a chat message that should hit the LLM path. The stub
    # forces error="llm_error" → slot should be released.
    msg_body = json.dumps({"message": "hi"}).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/chat/message",
        data=msg_body, method="POST",
        headers={
            "Content-Type": "application/json",
            "Cookie": cookie,
            "X-CSRF-Token": csrf,
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        chat_status = resp.status
        chat_body = json.loads(resp.read().decode("utf-8"))

    if chat_status != 200:
        findings.append(f"chat/message returned {chat_status}: {chat_body}")
    end_count = state.llm_tool_use_count_today(eff_uid)
    if end_count != 0:
        findings.append(
            f"slot NOT released on LLM error: count = {end_count} (want 0). "
            f"chat reply: {chat_body.get('reply', '')[:80]}")
    else:
        print("[probe] LLM error releases the slot via HTTP path "
              "(count stays at 0)")

    httpd.shutdown()
    return _report(findings)


def _report(findings: list[str]) -> int:
    print()
    print("=" * 60)
    if findings:
        print(f"SLOT RELEASE PROBE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("SLOT RELEASE PROBE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
