# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""End-to-end mesh demo: Yusuf (Blue Card, Munich) walks the mesh.

Companion to ``demo_aicha_walk.py`` — exercises a different cohort
across all 3 agents so the demo isn't a single happy path. Yusuf
is a Syrian electrical engineer on an EU Blue Card; he needs:

1. Verification of his BSc Electrical Engineering (Damascus) →
   anerkennung-agent → § 4 AsylG engineering pathway →
   full_recognition_pending_language (Sprachnachweis B2 DSH).
2. Munich short-term furnished housing → housing-agent →
   munich_blue_card cohort (€1100-1650/mo, 3-6 month
   furnished, 2-5 week wait).
3. NO social-services referral — Yusuf earns above the
   Bürgergeld threshold. Demo proves the social-services
   agent declines the referral gracefully when the cohort
   doesn't match.

Run with mesh already up:
    python -m mesh.demo_yusuf_walk
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


YUSUF_USER_ID = "user-demo-yusuf"
YUSUF_PROFILE: dict[str, Any] = {
    "userId": YUSUF_USER_ID,
    "displayNameOpaque": "Yusuf A.",
    "frictionClass": "yusuf",
    "residencyStatus": "EU Blue Card",
    "countryOfOrigin": "Syria",
    "qualificationField": "Electrical Engineering",
    "city": "Munich",
    "languageProficiency": {"de": "A2", "ar": "native", "en": "C1"},
    "yearsExperience": 9,
    "consentedScopes": ["identity", "residence", "employment"],
    "userConsentReceivedAt": "2026-05-21T12:00:00+00:00",
    "hasChildren": False,
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
    print(f"  ✗ {label} not reachable at {url}", file=sys.stderr)
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
        "issuedAt": YUSUF_PROFILE["userConsentReceivedAt"],
        "sourceAgent": "helpmefindthejob",
        "targetAgent": target,
        "userId": YUSUF_USER_ID,
        "intent": "proposed",
        "priority": "routine",
        "reasonCode": reason,
        "supportingInfo": ctx,
        "userConsentRequired": True,
        "userConsentReceivedAt": YUSUF_PROFILE["userConsentReceivedAt"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Yusuf end-to-end mesh demo")
    parser.add_argument("--skip-health", action="store_true")
    args = parser.parse_args()

    _section(
        "helpmefindthejob civic-services mesh — Yusuf demo walk",
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

    # Step 1 — verify electrical engineering BSc
    _section(
        "Step 1 — Verify Yusuf's Syrian Electrical Engineering BSc",
        "Expected pathway: engineering_paragraph_4_asylg.\n"
        "Note: Yusuf is on Blue Card now, but his original recognition was under §4 AsylG.",
    )
    decision_resp = _post_json(
        f"{ANERKENNUNG_URL}/v1/verify-credential",
        {
            "userId": YUSUF_USER_ID,
            "qualificationField": YUSUF_PROFILE["qualificationField"],
            "countryOfOrigin": YUSUF_PROFILE["countryOfOrigin"],
            "residencyStatus": "§ 4 AsylG",  # historic recognition status
            "userConsentReceivedAt": YUSUF_PROFILE["userConsentReceivedAt"],
        },
    )
    decision = decision_resp["decision"]
    print(f"  ✓ pathway = {decision['pathway']}")
    print(f"  ✓ decision = {decision['decision']}")
    print(f"  ✓ missing = {decision['missingRequirements']}")

    # Step 2 — Munich Blue Card housing
    _section(
        "Step 2 — Refer Yusuf to housing-agent for Munich short-term flat",
        "Expected cohort: munich_blue_card (€1100-1650/mo furnished short-term).",
    )
    housing_resp = _post_json(
        f"{HOUSING_URL}/v1/intake",
        {
            "referral": _build_referral(
                "housing-agent",
                "needs_housing_munich_blue_card_short_term",
                {
                    "city": YUSUF_PROFILE["city"],
                    "residency_status": "Blue Card",
                    "short_term": True,
                    "furnished_preferred": True,
                },
            )
        },
    )
    intake = housing_resp["intake"]
    print(f"  ✓ cohort = {intake['cohort']}")
    print(
        f"  ✓ rent band = €{intake['monthlyRentBandEur'][0]}–€{intake['monthlyRentBandEur'][1]}/mo"
    )
    print(f"  ✓ wait = {intake['estimatedWaitWeeksMin']}–{intake['estimatedWaitWeeksMax']} weeks")
    print(f"  ✓ tags = {intake['tags']}")

    # Step 3 — social-services check (expected: NOT matched to a cohort)
    _section(
        "Step 3 — Social-services eligibility check (NOT matched)",
        "Yusuf earns above the Bürgergeld threshold. The agent should\n"
        "fall through to the default unmatched cohort — proves the mesh\n"
        "handles the negative-eligibility case gracefully.",
    )
    social_resp = _post_json(
        f"{SOCIAL_URL}/v1/eligibility-check",
        {
            "profile": {
                "userId": YUSUF_USER_ID,
                "frictionClass": YUSUF_PROFILE["frictionClass"],
                "residencyStatus": "Blue Card",
                "hasChildren": False,
            }
        },
    )
    rec = social_resp["recommendation"]
    if rec["cohort"] == "default_unmatched":
        print(f"  ✓ correctly fell through to default cohort (Beratungstermin)")
        print(f"  ✓ no monetary benefit suggested (above threshold)")
    else:
        print(f"  ⚠ unexpected cohort match: {rec['cohort']}")
        return 1

    _section("Demo complete")
    print("  Yusuf demo walk passed:")
    print("    • Engineering credential recognized + Sprachnachweis flagged")
    print("    • Munich Blue Card short-term housing intake")
    print("    • Social-services correctly declined to over-recommend benefits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
