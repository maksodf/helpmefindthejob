"""Phase 1 / Step 7 Batch 1 — saved-search + company CRUD parity.

Verifies the four new tools and the two newly-paired inverses:

  1. update_saved_search: rename, then undo restores the old name.
  2. delete_saved_search: removes the row.
  3. update_company: rename + pause (watchEnabled=false), then undo.
  4. add_company → reversal pairs with delete_company (capture_inverse_after).
  5. create_saved_search → reversal pairs with delete_saved_search.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_batch1_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)

import app  # noqa: E402
from company_discovery.tool_registry import try_dispatch  # noqa: E402


def _ctx(user_id, call_id):
    return {
        "state": app.STATE,
        "user_id": user_id,
        "tool_actions_store": app.STATE.tool_actions_store,
        "tool_call_id": call_id,
    }


def main() -> int:
    findings: list[str] = []
    state = app.STATE

    # ----- 1+5. create_saved_search → undo → row gone -----
    user1 = "probe-batch1-1"
    state.update_profile(user1, {})
    ctx1 = _ctx(user1, "create-1")
    out = try_dispatch("create_saved_search", {
        "name": "Senior Backend Berlin",
        "targetRoles": ["backend engineer"],
    }, ctx1)
    if not out or not out.get("ok"):
        findings.append(f"create_saved_search failed: {out}")
        return _report(findings)
    if not out.get("reversalToken"):
        findings.append(
            "create_saved_search did not issue reversalToken "
            "(capture_inverse_after broken?)")
    search_id = out.get("id")
    if not search_id:
        findings.append("create_saved_search no id in result")
        return _report(findings)
    print(f"[probe] create_saved_search -> id={search_id[:12]}..., token issued")

    # Undo should call delete_saved_search.
    undo = try_dispatch("undo_last_action", {}, ctx1)
    if not undo or not undo.get("ok"):
        findings.append(f"undo create_saved_search failed: {undo}")
    if any(s.id == search_id
           for s in state.repository.list_saved_searches(user1)):
        findings.append(
            "create_saved_search undo did not delete the row")
    else:
        print("[probe] undo create_saved_search -> row deleted ✓")

    # ----- 2. update_saved_search → rename → undo restores -----
    create2 = try_dispatch("create_saved_search", {
        "name": "Original Name",
        "targetRoles": ["data engineer"],
    }, _ctx(user1, "create-2"))
    sid2 = create2.get("id")
    upd = try_dispatch("update_saved_search", {
        "searchId": sid2, "name": "New Name",
    }, _ctx(user1, "update-1"))
    if not upd or not upd.get("ok"):
        findings.append(f"update_saved_search failed: {upd}")
    saved = next(
        (s for s in state.repository.list_saved_searches(user1)
         if s.id == sid2), None)
    if saved is None or saved.name != "New Name":
        findings.append(
            f"update_saved_search did not rename: {saved.name if saved else 'gone'!r}")
    else:
        print(f"[probe] update_saved_search renamed to 'New Name'")
    # Undo restores.
    try_dispatch("undo_last_action", {}, _ctx(user1, "update-1-undo"))
    saved = next(
        (s for s in state.repository.list_saved_searches(user1)
         if s.id == sid2), None)
    if saved is None or saved.name != "Original Name":
        findings.append(
            f"undo update_saved_search did not restore name: "
            f"{saved.name if saved else 'gone'!r}")
    else:
        print(f"[probe] undo update_saved_search restored 'Original Name' ✓")

    # ----- 3. delete_saved_search removes -----
    deld = try_dispatch("delete_saved_search", {
        "searchId": sid2,
    }, _ctx(user1, "del-1"))
    if not deld or not deld.get("ok"):
        findings.append(f"delete_saved_search failed: {deld}")
    elif any(s.id == sid2
             for s in state.repository.list_saved_searches(user1)):
        findings.append("delete_saved_search did not remove the row")
    else:
        print("[probe] delete_saved_search removed the row ✓")

    # ----- 4+5. add_company → undo via delete_company -----
    user2 = "probe-batch1-2"
    state.update_profile(user2, {})
    add_out = try_dispatch("add_company", {
        "name": "Charité Berlin", "websiteUrl": "https://charite.de",
    }, _ctx(user2, "add-1"))
    if not add_out or not add_out.get("ok"):
        findings.append(f"add_company failed: {add_out}")
        return _report(findings)
    if not add_out.get("reversalToken"):
        findings.append(
            "add_company did not issue reversalToken "
            "(capture_inverse_after broken?)")
    cid = add_out.get("id")
    if not cid:
        findings.append("add_company no id in result")
        return _report(findings)
    if not any(c.id == cid for c in state.repository.list_companies(user2)):
        findings.append("add_company did not actually persist")
    else:
        print(f"[probe] add_company -> id={cid[:12]}..., token issued")
    # Undo -> delete_company
    try_dispatch("undo_last_action", {}, _ctx(user2, "add-1-undo"))
    if any(c.id == cid for c in state.repository.list_companies(user2)):
        findings.append(
            "undo add_company did not delete the company")
    else:
        print("[probe] undo add_company -> company deleted ✓")

    # ----- 6. update_company: name + pause -----
    add_out2 = try_dispatch("add_company", {
        "name": "ACME", "websiteUrl": "https://acme.test",
    }, _ctx(user2, "add-2"))
    cid2 = add_out2.get("id")
    upd_out = try_dispatch("update_company", {
        "companyId": cid2, "name": "ACME GmbH",
        "watchEnabled": False,
    }, _ctx(user2, "upd-co-1"))
    if not upd_out or not upd_out.get("ok"):
        findings.append(f"update_company failed: {upd_out}")
    company = next(
        (c for c in state.repository.list_companies(user2)
         if c.id == cid2), None)
    if company is None or company.name != "ACME GmbH":
        findings.append(
            f"update_company did not rename: "
            f"{company.name if company else 'gone'!r}")
    if company and company.watch_enabled:
        findings.append(
            "update_company watchEnabled=false did not pause scanning")
    else:
        print("[probe] update_company renamed + paused scanning ✓")
    # Undo restores name + watch_enabled.
    try_dispatch("undo_last_action", {}, _ctx(user2, "upd-co-1-undo"))
    company = next(
        (c for c in state.repository.list_companies(user2)
         if c.id == cid2), None)
    if company is None:
        findings.append("undo update_company lost the company")
    elif company.name != "ACME" or not company.watch_enabled:
        findings.append(
            f"undo update_company did not restore: "
            f"name={company.name!r}, watch_enabled={company.watch_enabled}")
    else:
        print("[probe] undo update_company restored name + scanning ✓")

    return _report(findings)


def _report(findings: list[str]) -> int:
    print()
    print("=" * 60)
    if findings:
        print(f"PHASE 1 BATCH 1 PROBE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("PHASE 1 BATCH 1 PROBE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
