"""Phase 1 / Step 4 — end-to-end probe for the CRUD-parity undo path.

Exercises:
  1. A Tier I tool (set_persona) runs successfully, captures the
     previous persona as the inverse, writes a reversal_tokens row,
     and returns a ``reversalToken`` in the dispatcher output.
  2. The reversal_tokens row is queryable via the store.
  3. ``undo_last_action`` reads the latest unconsumed token, dispatches
     the inverse (set_persona with the previous value), and the
     profile is restored.
  4. Calling ``undo_last_action`` a second time finds nothing to
     undo (the token was atomically consumed on first use).

This is the proof that the portfolio CRUD-parity policy (Tier I →
post-execution undo via reversal token) works end-to-end against a
real AppState + repository + SQLite store.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_undo_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)

import app  # noqa: E402
from company_discovery.tool_registry import try_dispatch  # noqa: E402


def main() -> int:
    findings: list[str] = []
    state = app.STATE

    # Create a probe user; seed their profile with persona='tech'.
    user_id = "probe-undo-user"
    state.update_profile(user_id, {"personaId": "tech"})
    profile = state.profile_for(user_id)
    if profile.persona_id != "tech":
        findings.append(f"seed failed: persona = {profile.persona_id}")
        return _report(findings)
    print(f"[probe] seeded persona = {profile.persona_id}")

    ctx = {
        "state": state,
        "user_id": user_id,
        "tool_actions_store": state.tool_actions_store,
        "tool_call_id": "probe_call_1",
    }

    # 1. Set persona via the new dispatcher.
    out = try_dispatch("set_persona", {"persona": "data"}, ctx)
    if out is None or not out.get("ok"):
        findings.append(f"set_persona failed: {out}")
        return _report(findings)
    token = out.get("reversalToken")
    if not token:
        findings.append("set_persona did not return reversalToken")
        return _report(findings)
    print(f"[probe] set_persona -> persona='data', reversalToken='{token[:12]}...'")

    profile = state.profile_for(user_id)
    if profile.persona_id != "data":
        findings.append(f"persona not changed: {profile.persona_id}")

    # 2. Reversal_tokens row queryable.
    latest = state.tool_actions_store.latest_unconsumed(user_id)
    if latest is None:
        findings.append("latest_unconsumed returned None after set_persona")
        return _report(findings)
    if latest["tool_name"] != "set_persona":
        findings.append(f"reversal row wrong tool: {latest['tool_name']}")
    if latest["inverse_tool"] != "set_persona":
        findings.append(f"inverse_tool wrong: {latest['inverse_tool']}")
    if latest["inverse_args"].get("persona") != "tech":
        findings.append(
            f"inverse_args wrong: {latest['inverse_args']} "
            f"(expected persona='tech')")
    print(f"[probe] reversal row OK: inverse_args = {latest['inverse_args']}")

    # 3. undo_last_action restores the previous persona.
    undo_out = try_dispatch("undo_last_action", {}, ctx)
    if undo_out is None or not undo_out.get("ok"):
        findings.append(f"undo_last_action failed: {undo_out}")
        return _report(findings)
    print(f"[probe] undo_last_action -> {undo_out.get('message', '')[:80]}")
    profile = state.profile_for(user_id)
    if profile.persona_id != "tech":
        findings.append(
            f"persona not restored: {profile.persona_id} (want 'tech')")
    else:
        print(f"[probe] persona restored to 'tech'")

    # 4. Second undo finds nothing (token was consumed atomically).
    # Note: the inverse dispatch (set_persona "tech") itself wrote a
    # NEW reversal token capturing the now-current state ('data', from
    # before the undo). So latest_unconsumed will find that one. The
    # important atomicity guarantee is that the SAME token can't be
    # consumed twice.
    consumed_again = state.tool_actions_store.consume(
        token=latest["token"], user_id=user_id,
    )
    if consumed_again is not None:
        findings.append(
            "consume() returned a payload for an already-consumed token "
            "(should be None)")
    else:
        print("[probe] consumed token cannot be consumed again")

    # 5. update_profile undo end-to-end. Seed location='Berlin',
    # update to 'Munich', undo, verify Berlin restored.
    user2 = "probe-undo-user-2"
    state.update_profile(user2, {"location": "Berlin"})
    ctx2 = {
        "state": state,
        "user_id": user2,
        "tool_actions_store": state.tool_actions_store,
        "tool_call_id": "probe_call_update",
    }
    out2 = try_dispatch("update_profile", {"location": "Munich"}, ctx2)
    if out2 is None or not out2.get("ok"):
        findings.append(f"update_profile failed: {out2}")
    elif not out2.get("reversalToken"):
        findings.append("update_profile did not return reversalToken")
    else:
        print(f"[probe] update_profile -> location='Munich', token written")
    undo2 = try_dispatch("undo_last_action", {}, ctx2)
    if undo2 is None or not undo2.get("ok"):
        findings.append(f"undo update_profile failed: {undo2}")
    p2 = state.profile_for(user2)
    if getattr(p2, "location", None) != "Berlin":
        findings.append(
            f"update_profile undo did not restore location: "
            f"got {getattr(p2, 'location', None)!r}")
    else:
        print(f"[probe] update_profile undo restored location='Berlin'")

    # 6. mark_applied capture path: simulate an imported_job in
    # memory, mark applied, undo, verify previous status restored.
    # This was the silent-bug case (capture called a non-existent
    # method); regression-proof via this test.
    from company_discovery.models import ImportedJob
    user3 = "probe-undo-user-3"
    state.update_profile(user3, {})  # ensure profile exists
    job = ImportedJob(
        user_id=user3,
        company_id="probe-company",
        discovered_job_id="probe-discovered",
        source_url="https://example.com/job/1",
        title="Bartender",
        company_name="Z-Bar",
        location="Berlin",
        application_status="saved",
    )
    state.repository.save_imported_job(job)
    job_id = job.id  # dataclass default factory assigns the uuid
    ctx3 = {
        "state": state,
        "user_id": user3,
        "tool_actions_store": state.tool_actions_store,
        "tool_call_id": "probe_call_mark",
    }
    out3 = try_dispatch(
        "mark_applied",
        {"importedJobId": job_id, "status": "applied"},
        ctx3,
    )
    if out3 is None or not out3.get("ok"):
        findings.append(f"mark_applied failed: {out3}")
    elif not out3.get("reversalToken"):
        findings.append(
            "mark_applied did not return reversalToken (capture bug?)")
    else:
        print(f"[probe] mark_applied -> status='applied', token written")
    undo3 = try_dispatch("undo_last_action", {}, ctx3)
    if undo3 is None or not undo3.get("ok"):
        findings.append(f"undo mark_applied failed: {undo3}")
    job3 = state.repository.imported_jobs.get(job_id)
    if job3 is None or job3.application_status != "saved":
        findings.append(
            f"mark_applied undo did not restore status: "
            f"{job3.application_status if job3 else 'job gone'!r}")
    else:
        print(f"[probe] mark_applied undo restored status='saved'")

    return _report(findings)


def _report(findings: list[str]) -> int:
    print()
    print("=" * 60)
    if findings:
        print(f"UNDO LAST ACTION PROBE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("UNDO LAST ACTION PROBE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
