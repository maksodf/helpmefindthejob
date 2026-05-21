# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Simulator: civic Anerkennung-agent.

Receives credential-verification requests + ESCO-skill lookups
from the employment-agent and produces a recognition decision
that mirrors how a real BIBB / Anabin / KMK integration would
respond. Issues a Verifiable Credential stub the user can carry
to other agents (Wohnungsamt, Sozialamt, Jobcenter).

This is a SIMULATOR. It does not connect to any real BIBB,
Anabin, or Zentralstelle für ausländisches Bildungswesen
endpoint. It encodes realistic-enough decision logic for three
pathway scenarios:

1. Aïcha — Tunisian nursing diploma (Pflegekräfte aus
   Drittstaaten Anerkennung pathway). Output: partial
   recognition + 6-month Anpassungslehrgang requirement.
2. Mahmoud — Syrian electrical engineering BSc under §4 AsylG.
   Output: full recognition pending Sprachnachweis (B2 DSH).
3. Olga — Ukrainian general medicine MD under §24 Ukraine
   protection. Output: expedited recognition + 12-month
   supervised practice (Approbation) pathway.

Endpoints:

- POST /v1/verify-credential — verify a foreign credential, return decision
- POST /v1/issue-vc — issue a Verifiable Credential for a recognised credential
- GET  /v1/health
- GET  /v1/audit-trail
"""

from __future__ import annotations

import argparse
import hashlib
import os
import uuid
from http import HTTPStatus
from pathlib import Path
from typing import Any

from mesh.common import (
    AgentAuditLog,
    JsonRequestHandler,
    now_iso,
    serve_until_stopped,
)


AGENT_NAME = "anerkennung-agent"
AGENT_VERSION = "0.1.0"


# Three demo recognition pathways. Each maps a (country_of_origin,
# qualification_field) pattern to a decision template.
PATHWAYS: list[dict[str, Any]] = [
    {
        "pathway_id": "pflege_drittstaaten",
        "label": "Pflegekräfte aus Drittstaaten (nursing, third countries)",
        "matches": {
            "qualification_field_in": ["nursing", "krankenpflege", "pflege"],
            "country_origin_in": [
                "tunisia", "tn", "morocco", "ma", "egypt", "eg",
                "jordan", "jo", "lebanon", "lb", "philippines", "ph",
            ],
        },
        "decision": "partial_recognition",
        "missing": ["Anpassungslehrgang (6 months supervised practice)"],
        "estimated_completion_months": 6,
        "issuing_authority": "Bezirksregierung Berlin (Pflege-Anerkennungsstelle)",
        "legal_basis": "§ 25 KrPflG i.V.m. § 2 PflBRefG",
    },
    {
        "pathway_id": "engineering_paragraph_4_asylg",
        "label": "Engineering BSc/MSc under § 4 AsylG",
        "matches": {
            "qualification_field_in": [
                "electrical engineering", "elektrotechnik",
                "mechanical engineering", "maschinenbau",
                "civil engineering", "bauingenieurwesen",
            ],
            "residency_status_in": ["§ 4 asylg", "§4 asylg", "4 asylg", "asylg"],
        },
        "decision": "full_recognition_pending_language",
        "missing": ["Sprachnachweis B2 DSH (German for academic context)"],
        "estimated_completion_months": 12,
        "issuing_authority": "Zentralstelle für ausländisches Bildungswesen (ZAB)",
        "legal_basis": "§ 9 BQFG",
    },
    {
        "pathway_id": "medicine_paragraph_24_ukraine",
        "label": "Approbation (medicine) under § 24 Ukraine protection",
        "matches": {
            "qualification_field_in": [
                "general medicine", "internal medicine", "medizin", "humanmedizin",
            ],
            "country_origin_in": ["ukraine", "ua"],
        },
        "decision": "expedited_recognition_supervised_practice",
        "missing": ["12-month supervised clinical practice (Approbation)"],
        "estimated_completion_months": 12,
        "issuing_authority": "Landesprüfungsamt für Gesundheitsberufe",
        "legal_basis": "§ 10 BÄO + EU/UA bilateral agreement 2026",
    },
]

DEFAULT_PATHWAY = {
    "pathway_id": "default_unmatched",
    "label": "Unmatched — generic BQFG pathway",
    "decision": "review_pending",
    "missing": [
        "Document translation (apostille required)",
        "Equivalence assessment per BQFG § 9",
    ],
    "estimated_completion_months": 9,
    "issuing_authority": "Zentralstelle für ausländisches Bildungswesen (ZAB)",
    "legal_basis": "§ 9 BQFG",
}


def _match_pathway(payload: dict[str, Any]) -> dict[str, Any]:
    field = str(payload.get("qualificationField", "")).strip().lower()
    country = str(payload.get("countryOfOrigin", "")).strip().lower()
    residency = str(payload.get("residencyStatus", "")).strip().lower()
    for pathway in PATHWAYS:
        m = pathway.get("matches", {})
        field_ok = "qualification_field_in" not in m or any(
            f in field for f in m["qualification_field_in"]
        )
        country_ok = "country_origin_in" not in m or country in [
            c.lower() for c in m["country_origin_in"]
        ]
        residency_ok = "residency_status_in" not in m or any(
            r in residency for r in m["residency_status_in"]
        )
        if field_ok and country_ok and residency_ok:
            return pathway
    return DEFAULT_PATHWAY


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _make_verification_decision(payload: dict[str, Any]) -> dict[str, Any]:
    pathway = _match_pathway(payload)
    decision_id = f"anerkennung-{uuid.uuid4().hex[:12]}"
    return {
        "decisionId": decision_id,
        "schemaVersion": "0.1.0",
        "agent": AGENT_NAME,
        "decidedAt": now_iso(),
        "pathway": pathway["pathway_id"],
        "pathwayLabel": pathway["label"],
        "decision": pathway["decision"],
        "qualificationFieldOpaque": _short_hash(payload.get("qualificationField", "")),
        "countryOfOriginOpaque": _short_hash(payload.get("countryOfOrigin", "")),
        "missingRequirements": list(pathway.get("missing", [])),
        "estimatedCompletionMonths": pathway.get("estimated_completion_months"),
        "issuingAuthority": pathway.get("issuing_authority"),
        "legalBasis": pathway.get("legal_basis"),
        "userConsentReceivedAt": payload.get("userConsentReceivedAt") or now_iso(),
    }


def _make_verifiable_credential_stub(
    decision: dict[str, Any], user_id: str
) -> dict[str, Any]:
    """W3C Verifiable Credentials Data Model 2.0 stub. The full
    signing pipeline lands in week 2's verifiable-credentials
    integration; this stub establishes the shape so downstream
    agents can already consume it.
    """
    return {
        "@context": [
            "https://www.w3.org/ns/credentials/v2",
            "https://helpmefindthejob.com/vc/anerkennung/v1",
        ],
        "id": f"urn:uuid:{uuid.uuid4()}",
        "type": ["VerifiableCredential", "AnerkennungCredential"],
        "issuer": f"did:web:anerkennung-agent.helpmefindthejob.com",
        "validFrom": now_iso(),
        "credentialSubject": {
            "id": f"did:web:user.helpmefindthejob.com:{_short_hash(user_id)}",
            "anerkennungPathway": decision["pathway"],
            "decision": decision["decision"],
            "issuingAuthority": decision["issuingAuthority"],
            "legalBasis": decision["legalBasis"],
            "missingRequirements": decision["missingRequirements"],
            "estimatedCompletionMonths": decision["estimatedCompletionMonths"],
        },
        # Signature placeholder — replaced by real Sigstore-style
        # signature in week 2 of the 4-week plan.
        "proof": {
            "type": "PendingSignaturePlaceholder",
            "created": now_iso(),
            "note": (
                "Real W3C VC signature lands in week 2 — this stub "
                "ships the data shape so downstream agents can be "
                "wired today and only the signature step needs to "
                "be added later."
            ),
        },
    }


def make_handler(audit: AgentAuditLog) -> type[JsonRequestHandler]:
    decisions: dict[str, dict[str, Any]] = {}

    def health(_handler, _payload):
        return {
            "status": "ok",
            "agent": AGENT_NAME,
            "version": AGENT_VERSION,
            "checkedAt": now_iso(),
        }

    def verify_credential(_handler, payload):
        for required in ("userId", "qualificationField", "countryOfOrigin"):
            if not payload.get(required):
                return {
                    "_http_status": HTTPStatus.BAD_REQUEST,
                    "status": "error",
                    "code": "missing_field",
                    "field": required,
                }
        decision = _make_verification_decision(payload)
        decisions[decision["decisionId"]] = decision
        audit.emit(
            "credential_verified",
            {
                "decisionId": decision["decisionId"],
                "pathway": decision["pathway"],
                "userId": payload["userId"],
            },
        )
        return {"status": "ok", "decision": decision}

    def issue_vc(_handler, payload):
        decision_id = str(payload.get("decisionId") or "").strip()
        user_id = str(payload.get("userId") or "").strip()
        if not decision_id or not user_id:
            return {
                "_http_status": HTTPStatus.BAD_REQUEST,
                "status": "error",
                "code": "missing_field",
            }
        decision = decisions.get(decision_id)
        if decision is None:
            return {
                "_http_status": HTTPStatus.NOT_FOUND,
                "status": "not_found",
                "decisionId": decision_id,
            }
        vc = _make_verifiable_credential_stub(decision, user_id)
        audit.emit(
            "verifiable_credential_issued",
            {
                "vcId": vc["id"],
                "decisionId": decision_id,
                "userId": user_id,
            },
        )
        return {"status": "ok", "verifiableCredential": vc}

    def audit_trail(_handler, _payload):
        return {"status": "ok", "agent": AGENT_NAME, "events": audit.replay()}

    class Handler(JsonRequestHandler):
        routes = {
            ("GET", "/v1/health"): health,
            ("POST", "/v1/verify-credential"): verify_credential,
            ("POST", "/v1/issue-vc"): issue_vc,
            ("GET", "/v1/audit-trail"): audit_trail,
        }

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="anerkennung-agent simulator")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MESH_ANERKENNUNG_PORT", "8102")),
    )
    parser.add_argument(
        "--audit-path",
        default=os.environ.get(
            "MESH_ANERKENNUNG_AUDIT", "data/mesh/anerkennung-agent-audit.log"
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
