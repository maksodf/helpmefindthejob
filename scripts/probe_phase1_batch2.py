"""Phase 1 / Step 7 Batch 2 — settings + account read tools.

Verifies the three new wrappable tools:

  1. test_slack_webhook with NO webhook configured -> structured
     ``no_webhook`` error (not a crash, not a silent ok).
  2. get_referral_info returns a code + URL + referredCount=0
     for a fresh user.
  3. discover_companies runs against the user's persona defaults
     and returns a results list (may be empty in the probe env;
     the API contract is what we verify, not the content).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_batch2_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)

import app  # noqa: E402
from company_discovery.tool_registry import try_dispatch  # noqa: E402


def _ctx(user_id):
    return {
        "state": app.STATE,
        "user_id": user_id,
        "tool_actions_store": app.STATE.tool_actions_store,
        "tool_call_id": "batch2",
    }


def main() -> int:
    findings: list[str] = []
    state = app.STATE

    # Register a real auth user so referral lookup has a row to find.
    user = state.auth_store.create_user(
        email="batch2-probe@example.com",
        password="batch2-probe-pass-9X",
    )
    user_id = user.id
    state.update_profile(user_id, {})

    # 1. Slack test with no webhook -> structured error.
    out = try_dispatch("test_slack_webhook", {}, _ctx(user_id))
    if out is None or out.get("ok") is not False:
        findings.append(
            f"test_slack_webhook should fail when no URL: {out}")
    elif "webhook" not in (out.get("message") or "").lower():
        findings.append(
            f"test_slack_webhook error not specific: {out.get('message')}")
    else:
        print(f"[probe] test_slack_webhook (no URL) -> "
              f"structured error: {out.get('message', '')[:60]}...")

    # 2. Referral info — fresh user, count=0, code generated.
    ref = try_dispatch("get_referral_info", {}, _ctx(user_id))
    if not ref or not ref.get("ok"):
        findings.append(f"get_referral_info failed: {ref}")
    elif not ref.get("code"):
        findings.append(f"get_referral_info no code in result: {ref}")
    elif ref.get("referredCount") != 0:
        findings.append(
            f"fresh user referredCount = "
            f"{ref.get('referredCount')} (want 0)")
    else:
        print(f"[probe] get_referral_info -> "
              f"code='{ref.get('code')[:8]}...', "
              f"url={ref.get('url', '')[:50]}, count=0")

    # 3. discover_companies runs with profile defaults.
    disc = try_dispatch("discover_companies", {"limit": 3}, _ctx(user_id))
    if not disc or disc.get("ok") is not True:
        findings.append(
            f"discover_companies failed: "
            f"{disc.get('message') if disc else None}")
    elif "results" not in disc:
        findings.append("discover_companies no 'results' field")
    else:
        print(f"[probe] discover_companies -> "
              f"persona='{disc.get('personaId')}', "
              f"count={disc.get('count')}")

    # 4. discover_companies with overrides.
    disc2 = try_dispatch("discover_companies", {
        "targetRoles": ["bartender"],
        "location": "Berlin",
        "limit": 2,
    }, _ctx(user_id))
    if not disc2 or disc2.get("ok") is not True:
        findings.append(
            f"discover_companies (override) failed: {disc2}")
    else:
        print(f"[probe] discover_companies override -> "
              f"count={disc2.get('count')}")

    return _report(findings)


def _report(findings: list[str]) -> int:
    print()
    print("=" * 60)
    if findings:
        print(f"PHASE 1 BATCH 2 PROBE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("PHASE 1 BATCH 2 PROBE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
