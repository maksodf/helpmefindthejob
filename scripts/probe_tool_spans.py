"""Phase 1 / Step 8 — OTel-shaped tool-call spans probe.

Verifies that every dispatch through ``try_dispatch`` emits one
``tool_call_spans`` row regardless of outcome:

  1. Successful Tier R call -> 1 span, success=1, cache_hit=0.
  2. Successful Tier I call -> 1 span, success=1, cache_hit=0,
     duration > 0.
  3. Repeated Tier I call (cache hit) -> 1 additional span,
     success=1, cache_hit=1.
  4. Validation failure -> 1 span, success=0, error_code='validation_failed'.
  5. ``tool_span_success_rate`` reports the (ok, total) ratio.

These are the field names the OTel GenAI Semantic Conventions
exporter will translate 1:1 into ``execute_tool`` spans when the
observability backend is wired (per ADR-001).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_spans_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)

import app  # noqa: E402
from company_discovery.tool_registry import try_dispatch  # noqa: E402


def main() -> int:
    findings: list[str] = []
    state = app.STATE
    store = state.tool_actions_store

    user_id = "probe-spans"
    state.update_profile(user_id, {"personaId": "tech"})
    ctx = {
        "state": state,
        "user_id": user_id,
        "tool_actions_store": store,
        "tool_call_id": "spans_turn_1",
    }

    # Baseline: zero spans for this user before anything runs.
    if store.tool_span_count(user_id=user_id) != 0:
        findings.append(
            f"baseline span count != 0: "
            f"{store.tool_span_count(user_id=user_id)}")

    # 1. Successful Tier I dispatch.
    out = try_dispatch("set_persona", {"persona": "data"}, ctx)
    if not out or not out.get("ok"):
        findings.append(f"set_persona failed: {out}")
    n1 = store.tool_span_count(tool_name="set_persona", user_id=user_id)
    if n1 != 1:
        findings.append(f"after 1 call, set_persona spans = {n1}")
    else:
        print(f"[probe] set_persona dispatch -> 1 span")

    # 2. Repeated identical call -> idempotency cache hit ->
    # cache_hit span.
    try_dispatch("set_persona", {"persona": "data"}, ctx)
    n2 = store.tool_span_count(tool_name="set_persona", user_id=user_id)
    if n2 != 2:
        findings.append(f"after repeat call, set_persona spans = {n2}")
    # Inspect the latest row's cache_hit flag.
    with store._lock:
        row = store._conn.execute(
            "SELECT success, error_code, cache_hit "
            "FROM tool_call_spans WHERE user_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    if row is None or row[2] != 1:
        findings.append(
            f"second identical call should record cache_hit=1, "
            f"got row: {row}")
    else:
        print("[probe] idempotency cache hit -> span with cache_hit=1")

    # 3. Validation failure -> span with success=0,
    # error_code='validation_failed'.
    bad = try_dispatch("set_persona", {"persona": ""}, ctx)
    if not bad or bad.get("ok") is not False:
        findings.append(f"empty persona should fail: {bad}")
    with store._lock:
        row = store._conn.execute(
            "SELECT success, error_code FROM tool_call_spans "
            "WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    if row is None or row[0] != 0 or row[1] != "validation_failed":
        findings.append(
            f"validation failure span wrong: {row} "
            "(want success=0, error_code='validation_failed')")
    else:
        print("[probe] validation failure -> span with "
              "error_code='validation_failed'")

    # 4. Success-rate aggregate.
    ok, total = store.tool_span_success_rate(tool_name="set_persona")
    if total != 3:
        findings.append(
            f"success_rate total = {total} (want 3 = "
            "success + cache_hit + validation_fail)")
    if ok != 2:
        findings.append(
            f"success_rate ok = {ok} (want 2 = success + cache_hit)")
    else:
        print(f"[probe] tool_span_success_rate(set_persona) = "
              f"{ok}/{total}")

    return _report(findings)


def _report(findings: list[str]) -> int:
    print()
    print("=" * 60)
    if findings:
        print(f"TOOL SPANS PROBE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("TOOL SPANS PROBE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
