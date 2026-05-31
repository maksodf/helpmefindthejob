# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Simulator: civic housing-agent.

Receives ``propose_referral`` envelopes from the employment-agent
and produces an intake decision + waiting-list slot. Mirrors the
shape a real Berlin / München / Hamburg Wohnungsamt integration
would expose.

This is a SIMULATOR. It does not connect to any real housing
authority. It carries realistic-enough fixture data so the
end-to-end demo can walk the three primary scenarios:

1. Aïcha §16d — Berlin, single occupant, modest budget (€650/mo
   cold rent ceiling), needs accessible-friendly nursing-shift-
   compatible (close to S-Bahn).
2. Yusuf Blue Card — Munich, single occupant, Tech salary (€1400
   cold rent ceiling), needs furnished short-term (3-6 mo) while
   he looks for a permanent flat.
3. Olga §24 Ukraine protection — Leipzig, family of 3 (mother +
   2 children under 12), needs family-sized + close to a Kita.

For each scenario the agent returns a structured intake-decision
payload that the employment-agent can surface to the user. Real
Wohnungsämter would issue a queue position + estimated wait time
+ next-step paperwork list; we emit the same shape.

Endpoints:

- POST /v1/intake — receive a referral, return intake decision
- GET  /v1/status/<referralId> — check status of an existing referral
- GET  /v1/health — liveness check
- GET  /v1/audit-trail — read the per-agent audit log (demo / debug)
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Any

from mesh.common import (
    AgentAuditLog,
    JsonRequestHandler,
    new_referral_id,
    now_iso,
    serve_until_stopped,
    validate_referral,
)

AGENT_NAME = "housing-agent"
AGENT_VERSION = "0.1.0"

# Three demo cohorts. Each cohort describes how the agent should
# answer when it sees a referral matching that pattern. Real
# Wohnungsämter use Mietspiegel + Bedarfsgemeinschaft logic; we
# encode plausible-enough heuristics keyed on the residency_status
# + family_size fields the source agent sends.
COHORTS: list[dict[str, Any]] = [
    {
        "cohort_id": "berlin_aufenthaltsgesetz_16d",
        "label": "Berlin §16d Anerkennung-track",
        "matches": {
            "city": ["berlin"],
            "residency_status_in": ["§16d", "16d", "anerkennung"],
        },
        "estimated_wait_weeks": [6, 10],
        "monthly_rent_band_eur": [450, 720],
        "tags": [
            "s-bahn-proximity",
            "shift-work-compatible",
            "single-occupant",
        ],
        "next_steps": [
            "Submit Wohnberechtigungsschein (WBS) application — we will email the form",
            "Bring Anerkennungsbescheid (Bezirksamt §16d certificate)",
            "Confirm employer's confirmation-of-employment letter",
        ],
        "subsidy_eligible": True,
    },
    {
        "cohort_id": "munich_blue_card",
        "label": "Munich EU Blue Card holder, short-term furnished",
        "matches": {
            "city": ["munich", "münchen", "muenchen"],
            "residency_status_in": ["blue card", "blaue karte", "blue-card", "blue_card"],
        },
        "estimated_wait_weeks": [2, 5],
        "monthly_rent_band_eur": [1100, 1650],
        "tags": [
            "furnished",
            "short-term",
            "3-6-months",
        ],
        "next_steps": [
            "Verify Blue Card validity (we accept scanned copy)",
            "Income verification — last 3 payslips or contract",
            "Schufa report",
        ],
        "subsidy_eligible": False,
    },
    {
        "cohort_id": "leipzig_paragraph_24_ukraine",
        "label": "Leipzig §24 Ukraine protection, family",
        "matches": {
            "city": ["leipzig"],
            "residency_status_in": ["§24", "24", "ukraine"],
        },
        "estimated_wait_weeks": [3, 8],
        # Leipzig is markedly cheaper than the larger cities; illustrative
        # family KdU band (cold rent) for a §24 Bedarfsgemeinschaft.
        "monthly_rent_band_eur": [520, 900],
        "tags": [
            "family-sized",
            "kita-proximity",
            "school-district-flexible",
        ],
        "next_steps": [
            "Bring Ankunftsnachweis + Fiktionsbescheinigung",
            "Kita-Gutschein application status — we coordinate with Sozialbehörde",
            "Schulplatzbescheinigung for each school-age child",
        ],
        "subsidy_eligible": True,
    },
]

DEFAULT_COHORT = {
    "cohort_id": "default_unmatched",
    "label": "Unmatched referral — generic intake",
    "estimated_wait_weeks": [8, 16],
    "monthly_rent_band_eur": [500, 1000],
    "tags": ["generic-intake"],
    "next_steps": [
        "Submit personal-circumstances questionnaire",
        "Income + residency-status verification",
        "We will contact you within 5 business days",
    ],
    "subsidy_eligible": False,
}


def _match_cohort(referral: dict[str, Any]) -> dict[str, Any]:
    """Match a referral to one of the demo cohorts. Order
    matters — first match wins."""
    context = referral.get("supportingInfo", {}) or {}
    city = str(context.get("city", "")).strip().lower()
    residency = str(context.get("residency_status", "")).strip().lower()
    reason = str(referral.get("reasonCode", "")).strip().lower()
    for cohort in COHORTS:
        matchers = cohort.get("matches", {})
        ok = True
        if "city" in matchers and city not in [c.lower() for c in matchers["city"]]:
            ok = False
        if ok and "residency_status_in" in matchers:
            if not any(
                token in residency or token in reason for token in matchers["residency_status_in"]
            ):
                ok = False
        if ok:
            return cohort
    return DEFAULT_COHORT


def _make_intake_decision(referral: dict[str, Any]) -> dict[str, Any]:
    cohort = _match_cohort(referral)
    intake_id = new_referral_id().replace("ref-", "intake-")
    wait_band = cohort.get("estimated_wait_weeks", [4, 8])
    eta = datetime.now(timezone.utc) + timedelta(weeks=wait_band[1])
    return {
        "intakeId": intake_id,
        "sourceReferralId": referral.get("referralId"),
        "schemaVersion": "0.1.0",
        "agent": AGENT_NAME,
        "decidedAt": now_iso(),
        "cohort": cohort["cohort_id"],
        "cohortLabel": cohort["label"],
        "decision": "accepted",
        "estimatedWaitWeeksMin": wait_band[0],
        "estimatedWaitWeeksMax": wait_band[1],
        "estimatedEarliestSlotAt": eta.date().isoformat(),
        "monthlyRentBandEur": cohort.get("monthly_rent_band_eur"),
        "tags": list(cohort.get("tags", [])),
        "nextSteps": list(cohort.get("next_steps", [])),
        "subsidyEligible": cohort.get("subsidy_eligible", False),
        "userConsentReceivedAt": referral.get("userConsentReceivedAt") or now_iso(),
    }


def make_handler(audit: AgentAuditLog) -> type[JsonRequestHandler]:
    """Build a handler class bound to the supplied audit log."""

    intakes: dict[str, dict[str, Any]] = {}

    def health(_handler, _payload):
        return {
            "status": "ok",
            "agent": AGENT_NAME,
            "version": AGENT_VERSION,
            "checkedAt": now_iso(),
        }

    def intake(_handler, payload):
        referral = payload.get("referral") or payload
        ok, err = validate_referral(referral)
        if not ok:
            audit.emit(
                "intake_rejected",
                {"reason": err, "referralId": referral.get("referralId")},
            )
            return {
                "_http_status": HTTPStatus.BAD_REQUEST,
                "status": "rejected",
                "code": "invalid_referral",
                "detail": err,
            }
        decision = _make_intake_decision(referral)
        intakes[decision["intakeId"]] = decision
        audit.emit(
            "intake_accepted",
            {
                "intakeId": decision["intakeId"],
                "sourceReferralId": referral.get("referralId"),
                "cohort": decision["cohort"],
                "userId": referral.get("userId"),
            },
        )
        return {"status": "ok", "intake": decision}

    def status_lookup(_handler, _payload, referral_id):
        for intake_record in intakes.values():
            if intake_record.get("sourceReferralId") == referral_id:
                return {"status": "ok", "intake": intake_record}
        return {
            "_http_status": HTTPStatus.NOT_FOUND,
            "status": "not_found",
            "referralId": referral_id,
        }

    def audit_trail(_handler, _payload):
        return {"status": "ok", "agent": AGENT_NAME, "events": audit.replay()}

    class Handler(JsonRequestHandler):
        routes = {
            ("GET", "/v1/health"): health,
            ("POST", "/v1/intake"): intake,
            ("GET", "/v1/status/<referralId>"): status_lookup,
            ("GET", "/v1/audit-trail"): audit_trail,
        }

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="housing-agent simulator")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("MESH_HOUSING_PORT", "8101"))
    )
    parser.add_argument(
        "--audit-path",
        default=os.environ.get("MESH_HOUSING_AUDIT", "data/mesh/housing-agent-audit.log"),
    )
    args = parser.parse_args()
    audit = AgentAuditLog(Path(args.audit_path))
    handler = make_handler(audit)
    server = serve_until_stopped(handler, args.host, args.port)
    print(f"[{AGENT_NAME}] listening on http://{args.host}:{args.port}", flush=True)
    print(f"[{AGENT_NAME}] audit log: {args.audit_path}", flush=True)
    try:
        # Block forever until SIGTERM / Ctrl-C
        import signal

        signal.pause()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
