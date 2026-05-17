"""Phase 1 / Step 7 Batch 3 — settings/account wrap-batch.

Four new tools:
  1. get_account_status — composite read (plan, verification, 2FA, usage)
  2. get_billing_status — subscription + plans + usage
  3. request_data_export — GDPR portability blob + summary
  4. set_slack_webhook — Tier I save with full undo round-trip
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_batch3_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)

import app  # noqa: E402
from company_discovery.tool_registry import try_dispatch  # noqa: E402


def _ctx(user_id):
    return {
        "state": app.STATE,
        "user_id": user_id,
        "tool_actions_store": app.STATE.tool_actions_store,
        "tool_call_id": "batch3",
    }


def main() -> int:
    findings: list[str] = []
    state = app.STATE
    user = state.auth_store.create_user(
        email="batch3-probe@example.com",
        password="batch3-probe-pass-9X",
    )
    user_id = user.id
    state.update_profile(user_id, {})

    # 1. get_account_status
    out = try_dispatch("get_account_status", {}, _ctx(user_id))
    if not out or not out.get("ok"):
        findings.append(f"get_account_status failed: {out}")
    else:
        for key in ("email", "plan", "emailVerified",
                     "twoFactorEnabled", "llmUsage", "memberSince"):
            if key not in out:
                findings.append(
                    f"get_account_status missing '{key}': {out}")
                break
        else:
            print(f"[probe] get_account_status -> "
                  f"plan={out.get('plan')}, 2fa={out.get('twoFactorEnabled')}, "
                  f"verified={out.get('emailVerified')}")

    # 2. get_billing_status
    out = try_dispatch("get_billing_status", {}, _ctx(user_id))
    if not out or not out.get("ok"):
        findings.append(f"get_billing_status failed: {out}")
    elif "subscription" not in out or "plans" not in out:
        findings.append(f"get_billing_status missing fields: {out}")
    else:
        print(f"[probe] get_billing_status -> "
              f"plans={len(out['plans'])}, "
              f"usage={out['aiUsage']}")

    # 3. request_data_export
    out = try_dispatch("request_data_export", {}, _ctx(user_id))
    if not out or not out.get("ok"):
        findings.append(f"request_data_export failed: {out}")
    elif out.get("openUrl") != "/api/data/export":
        findings.append(f"export openUrl wrong: {out.get('openUrl')}")
    else:
        print(f"[probe] request_data_export -> "
              f"{sum(out.get('exportSummary', {}).values())} entries, "
              f"openUrl={out.get('openUrl')}")

    # 4. set_slack_webhook + undo round-trip
    out = try_dispatch("set_slack_webhook", {
        "webhookUrl": "https://hooks.slack.com/services/X/Y/Z",
    }, _ctx(user_id))
    if not out or not out.get("ok"):
        findings.append(f"set_slack_webhook failed: {out}")
    elif not out.get("reversalToken"):
        findings.append("set_slack_webhook no reversalToken")
    profile = state.profile_for(user_id)
    if (getattr(profile, "slack_webhook_url", "") or "") != (
            "https://hooks.slack.com/services/X/Y/Z"):
        findings.append(
            f"webhook not saved: {profile.slack_webhook_url!r}")
    else:
        print("[probe] set_slack_webhook -> saved, token issued")

    # Undo restores empty.
    try_dispatch("undo_last_action", {}, _ctx(user_id))
    profile = state.profile_for(user_id)
    if (getattr(profile, "slack_webhook_url", "") or "") != "":
        findings.append(
            f"undo set_slack_webhook did not clear: "
            f"{profile.slack_webhook_url!r}")
    else:
        print("[probe] undo set_slack_webhook -> webhook cleared ✓")

    # 5. Invalid webhook rejected with structured error.
    out = try_dispatch("set_slack_webhook", {
        "webhookUrl": "https://evil.example.com/hook",
    }, _ctx(user_id))
    if not out or out.get("ok") is not False:
        findings.append(f"invalid webhook should fail: {out}")
    elif "hooks.slack.com" not in (out.get("message") or ""):
        findings.append(
            f"webhook validation error not specific: {out.get('message')}")
    else:
        print("[probe] set_slack_webhook rejects non-Slack URL ✓")

    return _report(findings)


def _report(findings: list[str]) -> int:
    print()
    print("=" * 60)
    if findings:
        print(f"PHASE 1 BATCH 3 PROBE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("PHASE 1 BATCH 3 PROBE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
