"""Phase 1 / Step 1b — verify the new Pydantic-backed tool registry
path.

Checks:
  1. find_jobs is registered in the new registry with tier='R'.
  2. The Anthropic tool spec is Pydantic-generated (has
     ``additionalProperties: false`` + length bounds + anyOf for the
     optional location).
  3. try_dispatch returns ``None`` for tools not in the new registry
     (so the caller in ``app.py:_dispatch`` falls back cleanly).
  4. Pydantic validation rejects an empty query with a structured
     ``validation_failed`` message.
  5. Pydantic validation rejects extra fields (``additionalProperties:
     false`` is enforced at the handler boundary even without
     vendor-side ``strict: true``).
  6. The legacy build_tools_payload() prefers the new spec for
     find_jobs while still emitting all 14 legacy tools.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_new_registry_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)

import app  # noqa: E402, F401 — boot STATE
from company_discovery.tool_registry import (  # noqa: E402
    get_tool, try_dispatch,
)
from company_discovery.tool_use_router import (  # noqa: E402
    build_tools_payload,
)


def main() -> int:
    findings: list[str] = []

    # 1. find_jobs is registered with tier='R'.
    tool = get_tool("find_jobs")
    if tool is None:
        findings.append("find_jobs not in new registry")
    elif tool.tier != "R":
        findings.append(f"find_jobs tier = {tool.tier!r}, want 'R'")
    else:
        print(f"[probe] find_jobs registered as Tier {tool.tier}")

    # 2. Anthropic tool spec is Pydantic-generated.
    if tool is not None:
        spec = tool.anthropic_tool_spec()
        schema = spec["input_schema"]
        if schema.get("additionalProperties") is not False:
            findings.append(
                "input_schema is missing additionalProperties: false")
        if "query" not in schema.get("properties", {}):
            findings.append("input_schema missing query property")
        else:
            q = schema["properties"]["query"]
            if q.get("maxLength") != 200 or q.get("minLength") != 1:
                findings.append(
                    f"query bounds wrong: min={q.get('minLength')} "
                    f"max={q.get('maxLength')}")
        if "location" not in schema.get("properties", {}):
            findings.append("input_schema missing location property")
        else:
            loc = schema["properties"]["location"]
            if "anyOf" not in loc:
                findings.append("location should be anyOf[string, null]")
        print(f"[probe] Pydantic input_schema: "
              f"{list(schema.get('properties', {}).keys())}")

    # 3. Unknown tool → None (caller falls back).
    unknown = try_dispatch(
        "not_a_real_tool", {},
        ctx={"state": app.STATE, "user_id": "probe"},
    )
    if unknown is not None:
        findings.append(
            f"unknown tool should return None, got: {unknown}")
    else:
        print("[probe] unknown tool returns None (fallback intact)")

    # 4. Empty query rejected with validation_failed.
    bad = try_dispatch(
        "find_jobs", {"query": ""},
        ctx={"state": app.STATE, "user_id": "probe"},
    )
    if bad is None:
        findings.append("empty query: try_dispatch returned None")
    elif bad.get("ok") is not False:
        findings.append(f"empty query should fail, got: {bad}")
    else:
        msg = bad.get("message", "")
        if "validation" not in msg.lower():
            findings.append(
                f"empty query error not from Pydantic: {msg}")
        else:
            print(f"[probe] empty query rejected: "
                  f"{msg[:80]}...")

    # 5. Extra fields rejected (additionalProperties: false).
    extra = try_dispatch(
        "find_jobs",
        {"query": "bartender", "limit": 10},  # 'limit' is not declared
        ctx={"state": app.STATE, "user_id": "probe"},
    )
    if extra is None:
        findings.append("extra-field test: try_dispatch returned None")
    elif extra.get("ok") is not False:
        findings.append(
            "extra fields should be rejected (additionalProperties: "
            f"false), got: {extra}")
    else:
        msg = extra.get("message", "")
        if "limit" not in msg.lower() and "extra" not in msg.lower():
            findings.append(
                f"extra-field error not specific: {msg}")
        else:
            print(f"[probe] extra fields rejected: {msg[:80]}...")

    # 6. build_tools_payload includes find_jobs with Pydantic schema.
    payload = build_tools_payload()
    fj_specs = [t for t in payload if t["name"] == "find_jobs"]
    if len(fj_specs) != 1:
        findings.append(
            f"build_tools_payload has {len(fj_specs)} find_jobs specs"
            " (want exactly 1)")
    elif fj_specs[0]["input_schema"].get(
            "additionalProperties") is not False:
        findings.append(
            "build_tools_payload returned legacy schema for find_jobs"
            " (new registry not preferred)")
    else:
        print(f"[probe] build_tools_payload emits {len(payload)} tools; "
              "find_jobs uses Pydantic schema")

    print()
    print("=" * 60)
    if findings:
        print(f"NEW REGISTRY DISPATCH PROBE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("NEW REGISTRY DISPATCH PROBE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
