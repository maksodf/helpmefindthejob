# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""PART 7 Loop 22: two end-to-end MCP composability flows.

This module defines two scripted MCP-client flows that exercise the
real subprocess transport and the cross-tool composition contracts
documented in docs/grant/09-mcp-composition.md.

Flow 1 -- Aicha discovery + tailoring + referral (7 steps):
    1. query_esco_skill("Pflegehelfer", type=occupation)
    2. suggest_relevant_companies(roles, industry=healthcare)
    3. add_company_to_watchlist(top suggestion)
    4. extract_direct_jobs_from_company_site(companyId, html_fixture)
    5. get_user_profile_for_consent(identity + employment scopes)
    6. propose_referral(target=housing-agent)
    7. record_user_outcome(jobId, applied)

Flow 2 -- Krankenschwester ESCO + EURES (4 steps):
    1. query_esco_skill("Krankenschwester", type=occupation)
    2. query_esco_skill("Krankenpflege", type=skill)
    3. suggest_relevant_companies(roles=[Krankenschwester], industry=krankenpflege)
    4. export_eures_compatible(userId, discoveredJobId) -- empty-state contract

Each step prints a markdown evidence block to ``out`` (a TextIO sink).
When invoked as a script, the module runs both flows back-to-back and
prints the combined markdown evidence to stdout.

The shell wrapper at ``scripts/run-mcp-composability-flows.sh`` runs the
module twice -- once per flow -- piping each output into
``docs/grant/mcp-walks-2026-05-21/composability-flow-<slug>.md``.

The companion unittest at ``tests.e2e.test_composability_flows`` runs
both flows with assertions so they're part of the regular test suite.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, TextIO

from tests.e2e.mcp_client_harness import (
    MCPHarness,
    assert_ok,
    parse_tool_result,
)


def _step(out: TextIO, n: int, title: str) -> None:
    out.write(f"\n### Step {n}. {title}\n\n")


def _call_block(out: TextIO, tool: str, arguments: dict[str, Any]) -> None:
    out.write("```json\n")
    out.write(json.dumps({"tool": tool, "arguments": arguments}, indent=2, ensure_ascii=False))
    out.write("\n```\n\n")


def _response_block(out: TextIO, payload: dict[str, Any], *, is_error: bool) -> None:
    label = "isError=True" if is_error else "ok"
    out.write(f"**Response ({label}):**\n\n```json\n")
    # Truncate large arrays to keep the evidence file readable.
    rendered = _shorten_for_display(payload)
    out.write(json.dumps(rendered, indent=2, ensure_ascii=False))
    out.write("\n```\n\n")


def _shorten_for_display(value: Any, *, max_list: int = 4) -> Any:
    if isinstance(value, dict):
        return {k: _shorten_for_display(v, max_list=max_list) for k, v in value.items()}
    if isinstance(value, list):
        if len(value) > max_list:
            return [_shorten_for_display(item, max_list=max_list) for item in value[:max_list]] + [
                f"... ({len(value) - max_list} more)"
            ]
        return [_shorten_for_display(item, max_list=max_list) for item in value]
    return value


# A minimal JSON-LD JobPosting HTML fixture. Realistic enough that the
# extract_direct_jobs_from_company_site tool's JSON-LD parser will pick
# it up and return one DiscoveredJob.
_AICHA_JOB_FIXTURE_HTML = """\
<!doctype html>
<html lang="de">
<head><title>Karriere -- Pflege Berlin Mitte</title></head>
<body>
<h1>Stellenangebote</h1>
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "JobPosting",
  "title": "Pflegehelfer:in (m/w/d) -- Anerkennungsweg",
  "description": "Wir begleiten internationale Pflegekraefte durch die Anerkennung nach 16d AufenthG. Sprachkurs B1 und supervisierte Praxis vor Ort.",
  "datePosted": "2026-05-15",
  "validThrough": "2026-07-15",
  "employmentType": "FULL_TIME",
  "hiringOrganization": {
    "@type": "Organization",
    "name": "Pflege Berlin Mitte gGmbH"
  },
  "jobLocation": {
    "@type": "Place",
    "address": {
      "@type": "PostalAddress",
      "addressLocality": "Berlin",
      "postalCode": "10115",
      "addressCountry": "DE"
    }
  }
}
</script>
</body>
</html>
"""


def run_aicha_flow(harness: MCPHarness, out: TextIO) -> dict[str, Any]:
    """Drive the Aicha 7-step composability flow. Returns a summary
    dict the test wrapper can assert on."""

    user_id = "u-aicha"
    out.write("# Composability flow 1: Aicha (16d Anerkennungsweg)\n\n")
    out.write(
        "Persona: Aicha -- Tunisian nurse on Germany's 16d Anerkennungsweg. "
        "Friction class: visa-constrained migrant, regulated profession. "
        "Demonstrates: ESCO taxonomy lookup -> curated company suggestions -> "
        "watchlist creation -> direct HTML job extraction -> portable civic "
        "profile -> housing-agent referral -> outcome event recorded.\n\n"
    )
    out.write("All 7 tool calls succeed against a fresh data dir (no prior repository state).\n")

    summary: dict[str, Any] = {"persona": "aicha", "user_id": user_id, "steps": []}

    # 1. ESCO lookup -----------------------------------------------------
    _step(out, 1, "query_esco_skill(query='Pflegehelfer', type='occupation')")
    args1 = {"query": "Pflegehelfer", "type": "occupation"}
    _call_block(out, "query_esco_skill", args1)
    response = harness.call_tool("query_esco_skill", **args1)
    payload1 = assert_ok(response)
    _response_block(out, payload1, is_error=False)
    assert payload1["totalCandidates"] > 0, "ESCO dataset returned no candidates"
    nurse_match = next(
        (m for m in payload1["matches"] if "Pflege" in m.get("label_de", "")),
        None,
    )
    assert nurse_match is not None, (
        f"expected at least one Pflege-shaped match, got {[m.get('label_de') for m in payload1['matches']]}"
    )
    out.write(
        f"**Composability anchor:** ESCO code `{nurse_match['code']}` "
        f"({nurse_match.get('label_de') or nurse_match.get('label')}) "
        f"is a stable cross-border identifier that downstream civic agents "
        f"(housing, recognition, language schools) can reference without "
        f"re-classifying Aicha's profession.\n"
    )
    summary["steps"].append(
        {"n": 1, "tool": "query_esco_skill", "ok": True, "code": nurse_match["code"]}
    )

    # 2. Suggest companies ----------------------------------------------
    _step(out, 2, "suggest_relevant_companies(targetRoles, industry=healthcare)")
    args2 = {
        "targetRoles": ["Pflegehelfer", "Pflegefachkraft"],
        "industry": "healthcare",
        "location": "Berlin",
    }
    _call_block(out, "suggest_relevant_companies", args2)
    response = harness.call_tool("suggest_relevant_companies", **args2)
    payload2 = assert_ok(response)
    _response_block(out, payload2, is_error=False)
    suggestions = payload2.get("suggestions", [])
    assert suggestions, "expected at least one curated suggestion or category"
    top_suggestion = suggestions[0]
    summary["steps"].append(
        {"n": 2, "tool": "suggest_relevant_companies", "ok": True, "count": len(suggestions)}
    )

    # 3. Add to watchlist -----------------------------------------------
    _step(out, 3, "add_company_to_watchlist(userId, name, websiteUrl)")
    company_name = (
        top_suggestion.get("name") or top_suggestion.get("category") or "Pflege Berlin Mitte gGmbH"
    )
    args3 = {
        "userId": user_id,
        "name": company_name,
        "websiteUrl": "https://pflege-berlin-mitte.example.invalid",
        "sector": "healthcare",
        "notes": "Surfaced from ESCO occupation lookup + curated suggestion.",
    }
    _call_block(out, "add_company_to_watchlist", args3)
    response = harness.call_tool("add_company_to_watchlist", **args3)
    payload3 = assert_ok(response)
    _response_block(out, payload3, is_error=False)
    company_id = payload3["company"]["id"]
    out.write(
        f"**Composability anchor:** company id `{company_id}` is now the "
        f"shared key for subsequent extract / scan / consent calls.\n"
    )
    summary["steps"].append(
        {"n": 3, "tool": "add_company_to_watchlist", "ok": True, "company_id": company_id}
    )

    # 4. Extract jobs from supplied HTML --------------------------------
    _step(out, 4, "extract_direct_jobs_from_company_site(html=<fixture>)")
    args4 = {
        "userId": user_id,
        "companyId": company_id,
        "pageUrl": "https://pflege-berlin-mitte.example.invalid/karriere",
        "html": _AICHA_JOB_FIXTURE_HTML,
    }
    # Don't print the full HTML in the JSON block -- replace with a placeholder.
    _call_block(
        out,
        "extract_direct_jobs_from_company_site",
        {**args4, "html": "<HTML fixture: 30 lines with JSON-LD JobPosting>"},
    )
    response = harness.call_tool("extract_direct_jobs_from_company_site", **args4)
    payload4 = assert_ok(response)
    _response_block(out, payload4, is_error=False)
    extracted_jobs = payload4.get("jobs", [])
    assert extracted_jobs, "expected JSON-LD parser to surface the fixture's JobPosting"
    job_title = extracted_jobs[0].get("title", "<no title>")
    summary["steps"].append(
        {
            "n": 4,
            "tool": "extract_direct_jobs_from_company_site",
            "ok": True,
            "jobs": len(extracted_jobs),
        }
    )

    # 5. Portable profile -----------------------------------------------
    _step(out, 5, "get_user_profile_for_consent(userId, scopes)")
    args5 = {
        "userId": user_id,
        "scopes": ["identity", "residence", "employment"],
    }
    _call_block(out, "get_user_profile_for_consent", args5)
    response = harness.call_tool("get_user_profile_for_consent", **args5)
    payload5 = assert_ok(response)
    _response_block(out, payload5, is_error=False)
    profile5 = payload5["profile"]
    for scope in args5["scopes"]:
        assert scope in profile5, (
            f"expected scope {scope!r} in profile dict, got keys={sorted(profile5.keys())}"
        )
    out.write(
        "**Composability anchor:** an external civic agent (housing-agent, "
        "language-school-agent, recognition-agent) can read this profile "
        "with Aicha's explicit consent and compose its own recommendations "
        "without round-tripping through helpmefindthejob's UI.\n"
    )
    summary["steps"].append({"n": 5, "tool": "get_user_profile_for_consent", "ok": True})

    # 6. Referral to housing-agent --------------------------------------
    _step(out, 6, "propose_referral(targetAgent='housing-agent')")
    args6 = {
        "userId": user_id,
        "targetAgent": "housing-agent",
        "reason": (
            "Aicha is searching for a 16d-Anerkennung clinical placement in Berlin "
            "and will need temporary housing close to the partner clinic. The "
            "housing-agent can use the residence + employment scopes from "
            "get_user_profile_for_consent above to filter listings near the "
            "watchlisted clinic."
        ),
        "context": {
            "city": "Berlin",
            "esco_code": nurse_match["code"],
            "watchlist_company_id": company_id,
        },
    }
    _call_block(out, "propose_referral", args6)
    response = harness.call_tool("propose_referral", **args6)
    payload6 = assert_ok(response)
    _response_block(out, payload6, is_error=False)
    referral = payload6["referral"]
    for field in ("referralId", "sourceAgent", "targetAgent", "userId", "userConsentRequired"):
        assert field in referral, f"referral missing {field}; got {referral}"
    assert referral["sourceAgent"] == "helpmefindthejob"
    assert referral["targetAgent"] == "housing-agent"
    assert referral["userConsentRequired"] is True
    summary["steps"].append(
        {"n": 6, "tool": "propose_referral", "ok": True, "referralId": referral["referralId"]}
    )

    # 7. Outcome event --------------------------------------------------
    _step(out, 7, "record_user_outcome(jobId, outcomeType='applied')")
    args7 = {
        "userId": user_id,
        "jobId": f"job-{company_id}",
        "outcomeType": "applied",
        "note": f"Applied to '{job_title}' via direct company portal.",
    }
    _call_block(out, "record_user_outcome", args7)
    response = harness.call_tool("record_user_outcome", **args7)
    payload7 = assert_ok(response)
    _response_block(out, payload7, is_error=False)
    summary["steps"].append({"n": 7, "tool": "record_user_outcome", "ok": True})

    out.write(
        "\n## Result\n\n"
        "Seven distinct MCP tools, composed into a single user-meaningful "
        "outcome: Aicha now has a curated company watchlist, an extracted "
        "job posting, a portable consent-scoped civic profile, a housing-"
        "agent referral, and a recorded application outcome -- all driven "
        "by an external MCP client against a stateless server instance.\n"
        "\n"
        "Cost-saving doctrine measurement (08-cost-saving-doctrine.md "
        "mechanisms 1, 2, 8): the record_user_outcome event in step 7 is "
        "the primary substrate partner-pilot evidence is built from.\n"
    )
    return summary


def run_esco_eures_flow(harness: MCPHarness, out: TextIO) -> dict[str, Any]:
    """Drive the Krankenschwester ESCO + EURES composability flow.
    Demonstrates cross-agent taxonomy interop: the ESCO occupation/skill
    catalogue and the EURES projection contract."""

    user_id = "u-eures-demo"
    out.write("# Composability flow 2: Krankenschwester ESCO + EURES\n\n")
    out.write(
        "Demonstrates cross-agent taxonomy interop. ESCO provides a "
        "stable cross-border occupation + skill code that any European "
        "civic agent can reference; EURES is the European Employment "
        "Services portal projection contract. Together they let an "
        "external MCP client compose helpmefindthejob's discovery output "
        "with EU-wide labour-market infrastructure.\n\n"
    )

    summary: dict[str, Any] = {"flow": "esco_eures", "user_id": user_id, "steps": []}

    # 1. ESCO occupation lookup -----------------------------------------
    _step(out, 1, "query_esco_skill(query='Krankenschwester', type='occupation')")
    args1 = {"query": "Krankenschwester", "type": "occupation"}
    _call_block(out, "query_esco_skill", args1)
    response = harness.call_tool("query_esco_skill", **args1)
    payload1 = assert_ok(response)
    _response_block(out, payload1, is_error=False)
    assert payload1["totalCandidates"] > 0
    match_labels = [m.get("label_de", "") for m in payload1["matches"]]
    assert any("Krankenpfleger" in label for label in match_labels), (
        f"expected nurse match for Krankenschwester query, got {match_labels}"
    )
    summary["steps"].append({"n": 1, "tool": "query_esco_skill", "ok": True, "type": "occupation"})

    # 2. ESCO skill lookup with type filter ------------------------------
    _step(out, 2, "query_esco_skill(query='Pflege', type='skill')")
    args2 = {"query": "Pflege", "type": "skill"}
    _call_block(out, "query_esco_skill", args2)
    response = harness.call_tool("query_esco_skill", **args2)
    payload2 = assert_ok(response)
    _response_block(out, payload2, is_error=False)
    for match in payload2.get("matches", []):
        assert match.get("type") == "skill", (
            f"type=skill filter must exclude occupations; got {match}"
        )
    out.write(
        "**Composability anchor:** the type=skill filter demonstrates the "
        "tool's typed catalogue -- callers can ask for occupations or "
        "skills independently, matching the ESCO 1.1 schema's separation "
        "of concerns.\n"
    )
    summary["steps"].append({"n": 2, "tool": "query_esco_skill", "ok": True, "type": "skill"})

    # 3. Use ESCO context to suggest companies --------------------------
    _step(out, 3, "suggest_relevant_companies(roles=[Krankenschwester], industry=krankenpflege)")
    args3 = {
        "targetRoles": ["Krankenschwester", "Pflegefachkraft"],
        "industry": "krankenpflege",
        "location": "Berlin",
    }
    _call_block(out, "suggest_relevant_companies", args3)
    response = harness.call_tool("suggest_relevant_companies", **args3)
    payload3 = assert_ok(response)
    _response_block(out, payload3, is_error=False)
    assert payload3.get("suggestions"), "expected at least one suggestion for clinical roles"
    summary["steps"].append({"n": 3, "tool": "suggest_relevant_companies", "ok": True})

    # 4. EURES projection contract --------------------------------------
    _step(out, 4, "export_eures_compatible(userId, discoveredJobId='dj-not-found')")
    args4 = {"userId": user_id, "discoveredJobId": "dj-does-not-exist"}
    _call_block(out, "export_eures_compatible", args4)
    response = harness.call_tool("export_eures_compatible", **args4)
    payload4, is_error = parse_tool_result(response)
    _response_block(out, payload4, is_error=is_error)
    assert payload4.get("status") in {"ok", "not_found", "tool_error"}, (
        f"unexpected EURES status {payload4.get('status')!r}"
    )
    out.write(
        "**Composability anchor:** even the empty-state path returns a "
        "structured response with a documented status code rather than "
        "raising. External MCP clients can compose EURES projection "
        "into a multi-step pipeline without special-casing missing-job "
        "errors -- the contract is the same shape either way.\n"
    )
    summary["steps"].append(
        {"n": 4, "tool": "export_eures_compatible", "ok": True, "status": payload4.get("status")}
    )

    out.write(
        "\n## Result\n\n"
        "Four tool calls demonstrate that ESCO (cross-border taxonomy) "
        "and EURES (European Employment Services projection) are first-"
        "class composability primitives in the helpmefindthejob MCP "
        "surface. An external agent can pivot from an ESCO code into "
        "company suggestions and EURES-shaped projections without ever "
        "touching helpmefindthejob's user-facing UI.\n"
    )
    return summary


def _run(flow: str, out: TextIO) -> dict[str, Any]:
    with MCPHarness() as harness:
        harness.initialize()
        if flow == "aicha":
            return run_aicha_flow(harness, out)
        if flow == "esco-eures":
            return run_esco_eures_flow(harness, out)
        raise ValueError(f"unknown flow {flow!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PART 7 MCP composability flows")
    parser.add_argument(
        "flow",
        choices=["aicha", "esco-eures", "both"],
        help="Which composability flow to run",
    )
    args = parser.parse_args(argv)

    if args.flow == "both":
        _run("aicha", sys.stdout)
        sys.stdout.write("\n\n---\n\n")
        _run("esco-eures", sys.stdout)
    else:
        _run(args.flow, sys.stdout)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"\n[composability-flow] FAIL -- {exc}", file=sys.stderr)
        raise SystemExit(1)
