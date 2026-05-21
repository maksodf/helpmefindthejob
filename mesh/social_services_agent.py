# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Simulator: civic social-services-agent.

Receives consent-scoped user profiles + eligibility-check
requests from the employment-agent and returns benefit-bracket
+ next-step recommendations that mirror the shape a real
Jobcenter / Sozialamt / Familienkasse integration would expose.

This is a SIMULATOR. It does not connect to any real Jobcenter,
Sozialamt, Bundesagentur für Arbeit, or Familienkasse endpoint.
It carries plausible decision logic for three realistic
scenarios:

1. Aïcha §16d Anerkennung-track — receives §16d follow-on
   benefits scoped to employment-status (Berufseinstieg
   Pflege). Recommends: ALG-II-Aufstockung during the
   Anpassungslehrgang phase, then transition to regular wage.
2. Olga §24 Ukraine protection with 2 children — recommends
   Kita-Gutschein + Bürgergeld + Kinderzuschlag with
   pre-filled application packet.
3. Tobias Quereinstieg (career change into civic-tech) —
   recommends Bildungsgutschein (educational voucher) for
   the 6-month Web Development Bootcamp.

Endpoints:

- POST /v1/eligibility-check — consume a consent-scoped profile, return recommendations
- POST /v1/profile-consume — accept a transmitted user profile, store with consent expiry
- GET  /v1/health
- GET  /v1/audit-trail
"""

from __future__ import annotations

import argparse
import os
import uuid
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Any

from mesh.common import (
    AgentAuditLog,
    JsonRequestHandler,
    now_iso,
    serve_until_stopped,
)


AGENT_NAME = "social-services-agent"
AGENT_VERSION = "0.1.0"


# Three demo benefit-recommendation cohorts. Each maps a profile
# pattern to a recommendation packet. A real Jobcenter would do
# Bedarfsgemeinschaft + Einkommensanrechnung; we encode
# plausible-enough decision logic.
RECOMMENDATION_COHORTS: list[dict[str, Any]] = [
    {
        "cohort_id": "aicha_paragraph_16d_anerkennung",
        "label": "§16d Anerkennung — Aufstockung during Anpassungslehrgang",
        "matches": {
            "friction_class_in": ["aicha"],
            "residency_status_in": ["§16d", "16d", "anerkennung"],
        },
        "primary_benefit": "Bürgergeld-Aufstockung (SGB II)",
        "supporting_benefits": [
            "ÖPNV-Sozialticket Berlin AB",
            "Krankenversicherung über Jobcenter",
        ],
        "estimated_monthly_eur": [380, 620],
        "next_steps": [
            "Antrag Bürgergeld online (jobcenter.digital)",
            "Bring Anerkennungsbescheid + Arbeitsvertrag Pflege-Anpassung",
            "Termin Berufsberatung — wir koordinieren",
        ],
        "duration_months": 6,
        "responsible_authority": "Jobcenter Berlin (BG-Schlüssel §16d)",
    },
    {
        "cohort_id": "olga_paragraph_24_family",
        "label": "§24 Ukraine protection — family with children",
        "matches": {
            "friction_class_in": ["olga"],
            "residency_status_in": ["§24", "24", "ukraine"],
            "has_children": True,
        },
        "primary_benefit": "Bürgergeld (SGB II) + Kinderzuschlag",
        "supporting_benefits": [
            "Kita-Gutschein Hamburg (24/30/45h pro Woche)",
            "Schulpaket (BuT — Bildung und Teilhabe)",
            "Sprachkurs DSH B1 (Volkshochschule, kostenfrei)",
            "Familienkasse — Kindergeld",
        ],
        "estimated_monthly_eur": [1450, 1880],
        "next_steps": [
            "Antrag Bürgergeld + Kinderzuschlag (eine Antragstelle)",
            "Kita-Gutschein-Antrag bei Sozialbehörde Hamburg",
            "Schulanmeldung Bezirksamt — Termin in <14 Tagen",
        ],
        "duration_months": 12,
        "responsible_authority": "Jobcenter Hamburg + Sozialbehörde Hamburg",
    },
    {
        "cohort_id": "tobias_quereinstieg_bildungsgutschein",
        "label": "Quereinstieg career-change — Bildungsgutschein",
        "matches": {
            "friction_class_in": ["tobias"],
            "career_intent_in": ["bootcamp", "quereinstieg", "career change", "umschulung"],
        },
        "primary_benefit": "Bildungsgutschein (AVGS) für 6-Monats-Bootcamp",
        "supporting_benefits": [
            "ALG I weiter während Maßnahme",
            "Erstattung Lehrgangskosten bis €7.500",
        ],
        "estimated_monthly_eur": [1240, 1240],  # ALG I roughly stable
        "next_steps": [
            "Termin Arbeitsvermittler beantragen — wir helfen mit dem Anschreiben",
            "Maßnahme + Träger AZAV-zertifiziert? Wir verifizieren mit der Bildungseinrichtung",
            "Antragstellung Bildungsgutschein — Genehmigung in ~3 Wochen",
        ],
        "duration_months": 6,
        "responsible_authority": "Bundesagentur für Arbeit (Arbeitsvermittlung)",
    },
]

DEFAULT_RECOMMENDATION = {
    "cohort_id": "default_unmatched",
    "label": "Unmatched — general benefit consultation",
    "primary_benefit": "Beratungstermin Sozialamt",
    "supporting_benefits": [],
    "estimated_monthly_eur": [0, 0],
    "next_steps": [
        "Termin Sozialamt vereinbaren — wir senden Vorabunterlagen",
        "Mitbringen: Personalausweis, Mietvertrag, letzte 3 Kontoauszüge",
    ],
    "duration_months": 0,
    "responsible_authority": "Sozialamt (zuständiger Bezirk)",
}


def _match_cohort(profile_packet: dict[str, Any]) -> dict[str, Any]:
    friction_class = str(profile_packet.get("frictionClass", "")).strip().lower()
    residency = str(profile_packet.get("residencyStatus", "")).strip().lower()
    has_children = bool(profile_packet.get("hasChildren", False))
    career_intent = str(profile_packet.get("careerIntent", "")).strip().lower()
    for cohort in RECOMMENDATION_COHORTS:
        m = cohort.get("matches", {})
        if "friction_class_in" in m and friction_class not in [
            f.lower() for f in m["friction_class_in"]
        ]:
            continue
        if "residency_status_in" in m and not any(
            r in residency for r in m["residency_status_in"]
        ):
            continue
        if "has_children" in m and bool(m["has_children"]) != has_children:
            continue
        if "career_intent_in" in m and not any(
            c in career_intent for c in m["career_intent_in"]
        ):
            continue
        return cohort
    return DEFAULT_RECOMMENDATION


def _make_recommendation(profile_packet: dict[str, Any]) -> dict[str, Any]:
    cohort = _match_cohort(profile_packet)
    recommendation_id = f"rec-{uuid.uuid4().hex[:12]}"
    return {
        "recommendationId": recommendation_id,
        "schemaVersion": "0.1.0",
        "agent": AGENT_NAME,
        "decidedAt": now_iso(),
        "cohort": cohort["cohort_id"],
        "cohortLabel": cohort["label"],
        "primaryBenefit": cohort["primary_benefit"],
        "supportingBenefits": list(cohort["supporting_benefits"]),
        "estimatedMonthlyEurMin": cohort["estimated_monthly_eur"][0],
        "estimatedMonthlyEurMax": cohort["estimated_monthly_eur"][1],
        "nextSteps": list(cohort["next_steps"]),
        "durationMonths": cohort["duration_months"],
        "responsibleAuthority": cohort["responsible_authority"],
        "userConsentReceivedAt": profile_packet.get("userConsentReceivedAt")
        or now_iso(),
        "consentExpiresAt": (
            datetime.now(timezone.utc) + timedelta(days=30)
        ).isoformat(timespec="seconds"),
    }


def make_handler(audit: AgentAuditLog) -> type[JsonRequestHandler]:
    stored_profiles: dict[str, dict[str, Any]] = {}

    def health(_handler, _payload):
        return {
            "status": "ok",
            "agent": AGENT_NAME,
            "version": AGENT_VERSION,
            "checkedAt": now_iso(),
        }

    def profile_consume(_handler, payload):
        scopes = payload.get("scopes") or []
        user_id = payload.get("userId")
        if not user_id or not scopes:
            return {
                "_http_status": HTTPStatus.BAD_REQUEST,
                "status": "error",
                "code": "missing_field",
            }
        # Store with explicit consent-expiry. A real agent would
        # persist this to durable storage with an auto-purge.
        slot_id = f"profile-{uuid.uuid4().hex[:12]}"
        expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(timespec="seconds")
        stored_profiles[slot_id] = {
            "userId": user_id,
            "scopes": list(scopes),
            "consumedAt": now_iso(),
            "expiresAt": expiry,
            "profile": payload.get("profile") or {},
        }
        audit.emit(
            "profile_consumed",
            {
                "slotId": slot_id,
                "userId": user_id,
                "scopes": list(scopes),
                "expiresAt": expiry,
            },
        )
        return {
            "status": "ok",
            "slotId": slot_id,
            "consentExpiresAt": expiry,
        }

    def eligibility_check(_handler, payload):
        profile_packet = payload.get("profile") or payload
        if not profile_packet.get("userId"):
            return {
                "_http_status": HTTPStatus.BAD_REQUEST,
                "status": "error",
                "code": "missing_field",
                "field": "userId",
            }
        recommendation = _make_recommendation(profile_packet)
        audit.emit(
            "eligibility_recommended",
            {
                "recommendationId": recommendation["recommendationId"],
                "cohort": recommendation["cohort"],
                "userId": profile_packet["userId"],
            },
        )
        return {"status": "ok", "recommendation": recommendation}

    def audit_trail(_handler, _payload):
        return {"status": "ok", "agent": AGENT_NAME, "events": audit.replay()}

    class Handler(JsonRequestHandler):
        routes = {
            ("GET", "/v1/health"): health,
            ("POST", "/v1/profile-consume"): profile_consume,
            ("POST", "/v1/eligibility-check"): eligibility_check,
            ("GET", "/v1/audit-trail"): audit_trail,
        }

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="social-services-agent simulator")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MESH_SOCIAL_PORT", "8103")),
    )
    parser.add_argument(
        "--audit-path",
        default=os.environ.get(
            "MESH_SOCIAL_AUDIT", "data/mesh/social-services-agent-audit.log"
        ),
    )
    args = parser.parse_args()
    audit = AgentAuditLog(Path(args.audit_path))
    handler = make_handler(audit)
    server = serve_until_stopped(handler, args.host, args.port)
    print(f"[{AGENT_NAME}] listening on http://{args.host}:{args.port}", flush=True)
    print(f"[{AGENT_NAME}] audit log: {args.audit_path}", flush=True)
    try:
        import signal

        signal.pause()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
