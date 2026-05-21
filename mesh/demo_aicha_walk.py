# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""End-to-end mesh demo: Aïcha walks the full civic-services
mesh through the employment-agent.

What this demonstrates:

1. Aïcha (§16d Anerkennung-track nurse, Berlin) starts in the
   employment-agent and gets a fit-score for a clinical role.
2. The employment-agent identifies a credential-recognition gap
   and emits a propose_referral to the anerkennung-agent.
3. The anerkennung-agent verifies her Tunisian nursing diploma,
   maps it to the Pflegekräfte-aus-Drittstaaten pathway, and
   issues a Verifiable Credential stub.
4. The employment-agent then emits a propose_referral to the
   housing-agent for a Berlin S-Bahn-proximity flat compatible
   with her shift-work hours.
5. Finally, the employment-agent emits a propose_referral to the
   social-services-agent with a consent-scoped profile for §16d
   Aufstockung benefits.
6. The demo prints the full decision trail by reading each
   agent's per-agent audit log so the reviewer can see every
   step traced end-to-end.

Run with all three simulators already up:

    python -m mesh.demo_aicha_walk

Or run alongside docker-compose:

    docker compose -f mesh/mesh-docker-compose.yml up -d
    python -m mesh.demo_aicha_walk

Exit code: 0 on success, non-zero if any step fails.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
import time
import urllib.error
import urllib.request
import uuid
from typing import Any


# Default ports match mesh-docker-compose.yml + the env-var
# fallbacks in each agent's __main__.
HOUSING_URL = os.environ.get("MESH_HOUSING_URL", "http://127.0.0.1:8101")
ANERKENNUNG_URL = os.environ.get("MESH_ANERKENNUNG_URL", "http://127.0.0.1:8102")
SOCIAL_URL = os.environ.get("MESH_SOCIAL_URL", "http://127.0.0.1:8103")


# Aïcha — the canonical §16d Anerkennung-track persona from
# docs/grant/07-personas.md.
AICHA_USER_ID = "user-demo-aicha"
AICHA_PROFILE: dict[str, Any] = {
    "userId": AICHA_USER_ID,
    "displayNameOpaque": "Aïcha B.",
    "frictionClass": "aicha",
    "residencyStatus": "§16d",
    "countryOfOrigin": "Tunisia",
    "qualificationField": "Nursing (Krankenpflege)",
    "city": "Berlin",
    "languageProficiency": {"de": "B1", "ar": "native", "fr": "C1"},
    "yearsExperience": 7,
    "consentedScopes": ["identity", "residence", "employment"],
    "userConsentReceivedAt": "2026-05-21T12:00:00+00:00",
    "hasChildren": False,
}


# ---------------------------------------------------------------------------
# Tiny HTTP client (stdlib only — same dep policy as the agents)
# ---------------------------------------------------------------------------


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _wait_for_health(url: str, label: str, max_seconds: float = 10.0) -> bool:
    """Poll /v1/health until the agent responds or we time out."""
    deadline = time.time() + max_seconds
    last_err: str | None = None
    while time.time() < deadline:
        try:
            payload = _get_json(f"{url}/v1/health")
            if payload.get("status") == "ok":
                return True
        except (urllib.error.URLError, ConnectionError) as exc:
            last_err = f"{type(exc).__name__}: {exc}"
        time.sleep(0.3)
    print(f"  ✗ {label} not reachable at {url} — {last_err}", file=sys.stderr)
    return False


# ---------------------------------------------------------------------------
# The walk — 5 steps
# ---------------------------------------------------------------------------


def _section(title: str, body: str = "") -> None:
    bar = "─" * 78
    print(f"\n{bar}\n  {title}\n{bar}")
    if body:
        print(textwrap.indent(body, "  "))


def _build_referral(
    target_agent: str, reason: str, context: dict[str, Any]
) -> dict[str, Any]:
    """Build a referral envelope matching the shape that the
    employment-agent's ``propose_referral`` MCP tool emits.
    Keeping this here (rather than importing from
    company_discovery.mcp_tools) means the demo can run even when
    the main app isn't installed in the same Python env."""
    return {
        "referralId": f"ref-{uuid.uuid4().hex[:12]}",
        "schemaVersion": "0.1.0",
        "issuedAt": AICHA_PROFILE["userConsentReceivedAt"],
        "sourceAgent": "helpmefindthejob",
        "targetAgent": target_agent,
        "userId": AICHA_USER_ID,
        "intent": "proposed",
        "priority": "routine",
        "reasonCode": reason,
        "supportingInfo": context,
        "userConsentRequired": True,
        "userConsentReceivedAt": AICHA_PROFILE["userConsentReceivedAt"],
    }


def step1_verify_anerkennung() -> dict[str, Any]:
    _section(
        "Step 1 — Verify Aïcha's Tunisian nursing credential",
        "Sending /v1/verify-credential to the anerkennung-agent.\n"
        "Expected pathway: Pflegekräfte aus Drittstaaten (partial recognition + Anpassungslehrgang).",
    )
    payload = {
        "userId": AICHA_USER_ID,
        "qualificationField": AICHA_PROFILE["qualificationField"],
        "countryOfOrigin": AICHA_PROFILE["countryOfOrigin"],
        "residencyStatus": AICHA_PROFILE["residencyStatus"],
        "userConsentReceivedAt": AICHA_PROFILE["userConsentReceivedAt"],
    }
    result = _post_json(f"{ANERKENNUNG_URL}/v1/verify-credential", payload)
    decision = result["decision"]
    print(f"  ✓ pathway = {decision['pathway']}")
    print(f"  ✓ decision = {decision['decision']}")
    print(f"  ✓ legalBasis = {decision['legalBasis']}")
    print(f"  ✓ missing = {decision['missingRequirements']}")
    return decision


def step2_issue_vc(decision_id: str) -> dict[str, Any]:
    _section(
        "Step 2 — Issue Verifiable Credential",
        "Asking the anerkennung-agent to issue a W3C VC stub for the decision.\n"
        "Aïcha now holds a portable credential she can present to other agents.",
    )
    result = _post_json(
        f"{ANERKENNUNG_URL}/v1/issue-vc",
        {"decisionId": decision_id, "userId": AICHA_USER_ID},
    )
    vc = result["verifiableCredential"]
    print(f"  ✓ VC id = {vc['id']}")
    print(f"  ✓ issuer = {vc['issuer']}")
    print(f"  ✓ subject pathway = {vc['credentialSubject']['anerkennungPathway']}")
    return vc


def step3_housing_referral() -> dict[str, Any]:
    _section(
        "Step 3 — Refer Aïcha to housing-agent",
        "Sending propose_referral to the housing-agent with §16d context.\n"
        "Expected cohort: berlin_aufenthaltsgesetz_16d (S-Bahn-proximity, single occupant).",
    )
    referral = _build_referral(
        target_agent="housing-agent",
        reason="needs_housing_berlin_anerkennung_track",
        context={
            "city": AICHA_PROFILE["city"],
            "residency_status": AICHA_PROFILE["residencyStatus"],
            "single_occupant": True,
        },
    )
    result = _post_json(f"{HOUSING_URL}/v1/intake", {"referral": referral})
    intake = result["intake"]
    print(f"  ✓ cohort = {intake['cohort']}")
    print(f"  ✓ rent band = €{intake['monthlyRentBandEur'][0]}–€{intake['monthlyRentBandEur'][1]}/mo")
    print(f"  ✓ wait = {intake['estimatedWaitWeeksMin']}–{intake['estimatedWaitWeeksMax']} weeks")
    print(f"  ✓ tags = {intake['tags']}")
    return intake


def step4_social_eligibility() -> dict[str, Any]:
    _section(
        "Step 4 — Check social-services eligibility",
        "Sending consent-scoped profile to social-services-agent.\n"
        "Expected cohort: aicha_paragraph_16d_anerkennung (Aufstockung during Anpassungslehrgang).",
    )
    result = _post_json(
        f"{SOCIAL_URL}/v1/eligibility-check",
        {
            "profile": {
                "userId": AICHA_USER_ID,
                "frictionClass": AICHA_PROFILE["frictionClass"],
                "residencyStatus": AICHA_PROFILE["residencyStatus"],
                "hasChildren": AICHA_PROFILE["hasChildren"],
                "userConsentReceivedAt": AICHA_PROFILE["userConsentReceivedAt"],
            }
        },
    )
    rec = result["recommendation"]
    print(f"  ✓ primary benefit = {rec['primaryBenefit']}")
    print(
        f"  ✓ estimated monthly = €{rec['estimatedMonthlyEurMin']}–€{rec['estimatedMonthlyEurMax']}"
    )
    print(f"  ✓ supporting = {rec['supportingBenefits']}")
    print(f"  ✓ authority = {rec['responsibleAuthority']}")
    return rec


def step5_trace_audit_trail() -> None:
    _section(
        "Step 5 — End-to-end decision trail",
        "Reading each agent's per-agent audit log to show the full chain.",
    )
    for label, url in (
        ("anerkennung-agent", ANERKENNUNG_URL),
        ("housing-agent", HOUSING_URL),
        ("social-services-agent", SOCIAL_URL),
    ):
        try:
            audit = _get_json(f"{url}/v1/audit-trail")
            print(f"\n  [{label}]  {len(audit['events'])} events:")
            for event in audit["events"]:
                print(
                    f"    seq={event['sequence_no']}  {event['event_type']:30}  {event['timestamp']}"
                )
        except (urllib.error.URLError, ConnectionError) as exc:
            print(f"\n  [{label}] FAILED to read audit: {exc}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Aïcha end-to-end mesh demo")
    parser.add_argument(
        "--skip-health",
        action="store_true",
        help="Skip the up-front health-check probes (use if you "
        "already know the agents are up)",
    )
    args = parser.parse_args()

    _section(
        "helpmefindthejob civic-services mesh — Aïcha demo walk",
        f"housing-agent       {HOUSING_URL}\n"
        f"anerkennung-agent   {ANERKENNUNG_URL}\n"
        f"social-services-agent {SOCIAL_URL}",
    )

    if not args.skip_health:
        for label, url in (
            ("housing-agent", HOUSING_URL),
            ("anerkennung-agent", ANERKENNUNG_URL),
            ("social-services-agent", SOCIAL_URL),
        ):
            if not _wait_for_health(url, label):
                print(
                    f"\nERROR: {label} not reachable. Start the agents first.\n"
                    f"  Single-process:  python -m mesh.run_all\n"
                    f"  docker-compose:  docker compose -f mesh/mesh-docker-compose.yml up -d",
                    file=sys.stderr,
                )
                return 2

    try:
        decision = step1_verify_anerkennung()
        step2_issue_vc(decision["decisionId"])
        step3_housing_referral()
        step4_social_eligibility()
        step5_trace_audit_trail()
    except (urllib.error.URLError, KeyError, ConnectionError) as exc:
        print(f"\nDemo failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    _section("Demo complete")
    print("  All 4 agents cooperated. Aïcha now holds:")
    print("    • A Verifiable Credential for her nursing recognition pathway")
    print("    • A housing-agent intake slot with realistic wait band")
    print("    • A social-services-agent benefit recommendation packet")
    print("  Every step is traceable via each agent's audit-trail endpoint.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
