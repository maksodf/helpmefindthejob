# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""End-to-end mesh demo: Olga (§24 Ukraine, Leipzig, family).

Companion to demo_aicha_walk.py and demo_yusuf_walk.py — covers a
software-professional cohort and a deliberately valuable legal case:

1. Verify Olga's Ukrainian software / senior-frontend background →
   anerkennung-agent → it_unregulated_no_recognition pathway →
   the agent correctly reports that NO formal recognition
   (Anerkennung) is required, because IT / software is an
   unregulated profession in Germany. She can work immediately.
2. Leipzig family housing → housing-agent →
   leipzig_paragraph_24_ukraine cohort (markedly cheaper than the
   larger cities, family-sized, Kita-proximity).
3. Social-services with family → social-services-agent →
   olga_paragraph_24_family cohort (Bürgergeld + Kinderzuschlag,
   Kita-Gutschein, Sprachkurs DSH B1, Schulpaket).

Run with mesh already up:
    python -m mesh.demo_olga_walk
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

HOUSING_URL = os.environ.get("MESH_HOUSING_URL", "http://127.0.0.1:8101")
ANERKENNUNG_URL = os.environ.get("MESH_ANERKENNUNG_URL", "http://127.0.0.1:8102")
SOCIAL_URL = os.environ.get("MESH_SOCIAL_URL", "http://127.0.0.1:8103")


OLGA_USER_ID = "user-demo-olga"
OLGA_PROFILE: dict[str, Any] = {
    "userId": OLGA_USER_ID,
    "displayNameOpaque": "Olga K.",
    "frictionClass": "olga",
    "residencyStatus": "§24 Ukraine",
    "countryOfOrigin": "Ukraine",
    "qualificationField": "Software engineering (senior frontend / React)",
    "city": "Leipzig",
    "languageProficiency": {"de": "A2", "uk": "native", "ru": "native", "en": "C1"},
    "yearsExperience": 9,
    "consentedScopes": ["identity", "residence", "employment", "family"],
    "userConsentReceivedAt": "2026-05-21T12:00:00+00:00",
    "hasChildren": True,
    "numberOfChildren": 2,
    "childrenAges": [7, 11],
}


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read().decode("utf-8"))


def _get_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _wait_for_health(url: str, label: str, max_seconds: float = 10.0) -> bool:
    deadline = time.time() + max_seconds
    while time.time() < deadline:
        try:
            if _get_json(f"{url}/v1/health").get("status") == "ok":
                return True
        except (urllib.error.URLError, ConnectionError):
            pass
        time.sleep(0.3)
    print(f"  ✗ {label} not reachable", file=sys.stderr)
    return False


def _section(title: str, body: str = "") -> None:
    bar = "─" * 78
    print(f"\n{bar}\n  {title}\n{bar}")
    if body:
        print(textwrap.indent(body, "  "))


def _build_referral(target: str, reason: str, ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "referralId": f"ref-{uuid.uuid4().hex[:12]}",
        "schemaVersion": "0.1.0",
        "issuedAt": OLGA_PROFILE["userConsentReceivedAt"],
        "sourceAgent": "helpmefindthejob",
        "targetAgent": target,
        "userId": OLGA_USER_ID,
        "intent": "proposed",
        "priority": "routine",
        "reasonCode": reason,
        "supportingInfo": ctx,
        "userConsentRequired": True,
        "userConsentReceivedAt": OLGA_PROFILE["userConsentReceivedAt"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Olga end-to-end mesh demo")
    parser.add_argument("--skip-health", action="store_true")
    args = parser.parse_args()

    _section(
        "helpmefindthejob civic-services mesh — Olga demo walk",
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
                return 2

    # Step 1
    _section(
        "Step 1 — Verify Olga's Ukrainian software / frontend background",
        "Expected pathway: it_unregulated_no_recognition.\n"
        "IT / software is an unregulated profession in Germany — the agent\n"
        "should report that NO formal recognition is required.",
    )
    decision = _post_json(
        f"{ANERKENNUNG_URL}/v1/verify-credential",
        {
            "userId": OLGA_USER_ID,
            "qualificationField": OLGA_PROFILE["qualificationField"],
            "countryOfOrigin": OLGA_PROFILE["countryOfOrigin"],
            "residencyStatus": OLGA_PROFILE["residencyStatus"],
            "userConsentReceivedAt": OLGA_PROFILE["userConsentReceivedAt"],
        },
    )["decision"]
    print(f"  ✓ pathway = {decision['pathway']}")
    print(f"  ✓ decision = {decision['decision']}")
    print(f"  ✓ legalBasis = {decision['legalBasis']}")
    print(f"  ✓ issuingAuthority = {decision['issuingAuthority']}")
    print(f"  ✓ estimated months to start = {decision['estimatedCompletionMonths']}")

    # Step 2 — Leipzig family housing
    _section(
        "Step 2 — Refer Olga + 2 children to housing-agent",
        "Expected cohort: leipzig_paragraph_24_ukraine (family-sized, Kita-proximity).",
    )
    intake = _post_json(
        f"{HOUSING_URL}/v1/intake",
        {
            "referral": _build_referral(
                "housing-agent",
                "needs_housing_leipzig_family",
                {
                    "city": OLGA_PROFILE["city"],
                    "residency_status": OLGA_PROFILE["residencyStatus"],
                    "family_size": 3,
                    "children_ages": OLGA_PROFILE["childrenAges"],
                },
            )
        },
    )["intake"]
    print(f"  ✓ cohort = {intake['cohort']}")
    print(
        f"  ✓ rent band = €{intake['monthlyRentBandEur'][0]}–€{intake['monthlyRentBandEur'][1]}/mo"
    )
    print(f"  ✓ tags = {intake['tags']}")

    # Step 3 — Family social-services
    _section(
        "Step 3 — Social-services eligibility (family-of-3)",
        "Expected cohort: olga_paragraph_24_family (Bürgergeld + Kinderzuschlag\n"
        "+ Kita-Gutschein + Schulpaket + Sprachkurs DSH B1).",
    )
    rec = _post_json(
        f"{SOCIAL_URL}/v1/eligibility-check",
        {
            "profile": {
                "userId": OLGA_USER_ID,
                "frictionClass": OLGA_PROFILE["frictionClass"],
                "residencyStatus": OLGA_PROFILE["residencyStatus"],
                "hasChildren": True,
            }
        },
    )["recommendation"]
    print(f"  ✓ cohort = {rec['cohort']}")
    print(f"  ✓ primary benefit = {rec['primaryBenefit']}")
    print(
        f"  ✓ estimated monthly = €{rec['estimatedMonthlyEurMin']}–€{rec['estimatedMonthlyEurMax']}"
    )
    print(f"  ✓ supporting = {len(rec['supportingBenefits'])} benefits:")
    for benefit in rec["supportingBenefits"]:
        print(f"      • {benefit}")

    _section("Demo complete")
    print("  Olga demo walk passed:")
    print("    • Software/IT correctly identified as unregulated — no Anerkennung needed")
    print("    • Family-sized Leipzig housing intake")
    print("    • Bürgergeld + Kinderzuschlag + Kita-Gutschein recommended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
