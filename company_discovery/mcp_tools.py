# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .service import CompanyDiscoveryService


# ---------------------------------------------------------------------------
# Reference ESCO mini-dataset.
#
# The query_esco_skill tool returns matches from this set today. It is a
# Week 2 stub seeded with the occupations and skills that map to the project's
# five-persona panel (Aïcha = nurse, Yusuf = mechanical engineer,
# Olga = frontend developer, Mahmoud = trade apprentice, Maria = care worker).
# Full ESCO dataset import lands in Week 2 §2.4 (ESCO + EURES integration);
# that work replaces this constant with a loader against the canonical
# dataset under a CC-BY licence and brings the entry count from ~12 to 30+
# per the §2.4 plan.
# ---------------------------------------------------------------------------

_ESCO_REFERENCE_DATASET: list[dict[str, str]] = [
    # Occupations (ISCO 4-digit + ESCO leaf)
    {"code": "2221.1", "label": "Registered nurse (general)", "type": "occupation", "isco": "2221"},
    {"code": "2221.2", "label": "Specialist nurse (clinical / Pflege)", "type": "occupation", "isco": "2221"},
    {"code": "5321.1", "label": "Healthcare assistant / Pflegehelfer", "type": "occupation", "isco": "5321"},
    {"code": "2144.1", "label": "Mechanical engineer", "type": "occupation", "isco": "2144"},
    {"code": "2512.1", "label": "Software developer", "type": "occupation", "isco": "2512"},
    {"code": "2513.1", "label": "Frontend developer / Web developer", "type": "occupation", "isco": "2513"},
    {"code": "7126.1", "label": "Plumbing trade apprentice / Anlagenmechaniker SHK", "type": "occupation", "isco": "7126"},
    {"code": "5322.1", "label": "Home-based personal-care worker / Häusliche Pflegehilfe", "type": "occupation", "isco": "5322"},
    # Skills
    {"code": "S1.0.1", "label": "Clinical-German communication", "type": "skill"},
    {"code": "S1.0.2", "label": "Patient documentation", "type": "skill"},
    {"code": "S5.0.1", "label": "TypeScript / React frontend development", "type": "skill"},
    {"code": "S2.0.1", "label": "Mechanical CAD (Solidworks / CATIA)", "type": "skill"},
]


# ---------------------------------------------------------------------------
# Outcome-event persistence (Week 2 §2.3).
#
# Outcome events (applied / replied / interviewing / offer / rejected /
# withdrawn) are appended as JSON Lines to data/user_outcomes.jsonl. This is
# deliberately file-based rather than schema-bound to a new SQLite table:
# the file format is auditable, append-only, and easy to migrate when the
# event volume justifies a real table. The cost-saving doctrine notes that
# outcome data is the project's primary measurement substrate for partner-
# pilot evidence (08-cost-saving-doctrine.md mechanisms 1, 2, 8); the schema
# stability here matters more than the storage backend.
# ---------------------------------------------------------------------------

_OUTCOME_TYPES = (
    "applied",
    "replied",
    "interviewing",
    "offer",
    "rejected",
    "withdrawn",
)


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "suggest_relevant_companies",
        "description": "Suggest curated healthcare-management companies and fallback categories from role, industry, and location preferences.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "targetRoles": {"type": "array", "items": {"type": "string"}},
                "industry": {"type": "string"},
                "location": {"type": "string"},
            },
            "required": ["targetRoles", "industry"],
        },
    },
    {
        "name": "add_company_to_watchlist",
        "description": "Create a company watchlist entry without scanning external pages.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {"type": "string"},
                "name": {"type": "string"},
                "websiteUrl": {"type": "string"},
                "careerPageUrl": {"type": "string"},
                "sector": {"type": "string"},
                "notes": {"type": "string"},
                "watchEnabled": {"type": "boolean"},
            },
            "required": ["userId", "name", "websiteUrl"],
        },
    },
    {
        "name": "find_company_career_page",
        "description": "Find an obvious public career page from a company homepage, respecting robots.txt.",
        "inputSchema": {
            "type": "object",
            "properties": {"userId": {"type": "string"}, "companyId": {"type": "string"}},
            "required": ["userId", "companyId"],
        },
    },
    {
        "name": "scan_company_career_page",
        "description": "Scan one known public career page with robots.txt and max-page guards.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {"type": "string"},
                "companyId": {"type": "string"},
                "careerPageUrl": {"type": "string"},
            },
            "required": ["userId", "companyId"],
        },
    },
    {
        "name": "extract_direct_jobs_from_company_site",
        "description": "Extract JobPosting JSON-LD and visible job links from supplied HTML without fetching.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {"type": "string"},
                "companyId": {"type": "string"},
                "pageUrl": {"type": "string"},
                "html": {"type": "string"},
            },
            "required": ["userId", "companyId", "pageUrl", "html"],
        },
    },
    {
        "name": "import_discovered_job",
        "description": "Import a reviewed discovered job into the normal job pipeline.",
        "inputSchema": {
            "type": "object",
            "properties": {"userId": {"type": "string"}, "discoveredJobId": {"type": "string"}},
            "required": ["userId", "discoveredJobId"],
        },
    },
    {
        "name": "deduplicate_discovered_jobs",
        "description": "Report likely duplicates among discovered direct-company jobs.",
        "inputSchema": {
            "type": "object",
            "properties": {"userId": {"type": "string"}},
            "required": ["userId"],
        },
    },
    {
        "name": "get_company_watchlist_summary",
        "description": "Return dashboard metrics for company watchlist and direct-company discoveries.",
        "inputSchema": {
            "type": "object",
            "properties": {"userId": {"type": "string"}},
            "required": ["userId"],
        },
    },
    # ----- §2.3 composition-oriented tools (catalogue v0.2.0) -----
    {
        "name": "get_user_profile_for_consent",
        "description": (
            "Return the user's portable civic profile (subset they have "
            "consented to share). Other open civic agents read this with "
            "explicit user consent to compose their own recommendations "
            "with the user's employment + residence + outcomes context."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {"type": "string"},
                "scopes": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "string",
                        "enum": [
                            "identity",
                            "residence",
                            "employment",
                            "cv",
                            "outcomes",
                            "preferences",
                        ],
                    },
                },
            },
            "required": ["userId", "scopes"],
        },
    },
    {
        "name": "propose_referral",
        "description": (
            "Emit a structured referral to another open civic agent. The "
            "calling agent constructs a referral the user can act on; the "
            "user retains the choice to follow up or decline. Composition "
            "pattern 1 (sequential handoff) per 09-mcp-composition.md."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {"type": "string"},
                "targetAgent": {"type": "string"},
                "reason": {"type": "string"},
                "context": {"type": "object"},
            },
            "required": ["userId", "targetAgent", "reason"],
        },
    },
    {
        "name": "query_esco_skill",
        "description": (
            "Look up ESCO skill or occupation codes by free-text query. "
            "Cross-agent shared taxonomy. Today this returns matches from "
            "a ~12-entry persona-panel-aligned mini-dataset; the full "
            "ESCO dataset import lands in Week 2 §2.4."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "type": {"type": "string", "enum": ["occupation", "skill", "any"]},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": ["query"],
        },
    },
    {
        "name": "export_eures_compatible",
        "description": (
            "Export a stored discovered job in EURES-compatible schema "
            "fields. Enables cross-deployment interoperability with the "
            "European Employment Services portal and any agent that reads "
            "EURES-shaped postings."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {"type": "string"},
                "discoveredJobId": {"type": "string"},
            },
            "required": ["userId", "discoveredJobId"],
        },
    },
    {
        "name": "record_user_outcome",
        "description": (
            "Persist an outcome event for a job (applied / replied / "
            "interviewing / offer / rejected / withdrawn). Append-only JSON "
            "Lines to data/user_outcomes.jsonl. The cost-saving doctrine "
            "uses these events as the primary measurement substrate for "
            "partner-pilot evidence (08-cost-saving-doctrine.md §1, §2, §8)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {"type": "string"},
                "jobId": {"type": "string"},
                "outcomeType": {
                    "type": "string",
                    "enum": list(_OUTCOME_TYPES),
                },
                "occurredAt": {
                    "type": "string",
                    "description": "ISO-8601 timestamp. Omit to use server-side now().",
                },
                "note": {"type": "string"},
            },
            "required": ["userId", "jobId", "outcomeType"],
        },
    },
]


class CompanyDiscoveryMCPTools:
    def __init__(self, service: CompanyDiscoveryService) -> None:
        self.service = service

    def suggest_relevant_companies(self, targetRoles: list[str], industry: str, location: str | None = None) -> dict[str, Any]:
        return {
            "status": "ok",
            "suggestions": self.service.suggest_relevant_companies(
                target_roles=targetRoles,
                industry=industry,
                location=location,
            ),
        }

    def add_company_to_watchlist(self, **payload: Any) -> dict[str, Any]:
        company = self.service.create_company(
            user_id=payload["userId"],
            name=payload["name"],
            website_url=payload["websiteUrl"],
            career_page_url=payload.get("careerPageUrl"),
            sector=payload.get("sector"),
            notes=payload.get("notes"),
            watch_enabled=payload.get("watchEnabled", True),
        )
        return {"status": "ok", "company": asdict(company)}

    def find_company_career_page(self, userId: str, companyId: str) -> dict[str, Any]:
        return self.service.find_company_career_page(userId, companyId)

    def scan_company_career_page(self, userId: str, companyId: str, careerPageUrl: str | None = None) -> dict[str, Any]:
        scan = self.service.scan_company_career_page(userId, companyId, careerPageUrl)
        return {"status": scan.status, "scan": asdict(scan)}

    def extract_direct_jobs_from_company_site(self, userId: str, companyId: str, pageUrl: str, html: str) -> dict[str, Any]:
        company = self.service.repository.get_company(userId, companyId)
        jobs = self.service.extract_direct_jobs_from_company_site(company, pageUrl, html)
        return {"status": "ok", "jobs": [asdict(job) for job in jobs]}

    def import_discovered_job(self, userId: str, discoveredJobId: str) -> dict[str, Any]:
        imported = self.service.import_discovered_job(userId, discoveredJobId)
        return {"status": "ok", "job": asdict(imported)}

    def deduplicate_discovered_jobs(self, userId: str) -> dict[str, Any]:
        return {"status": "ok", **self.service.deduplicate_discovered_jobs(userId)}

    def get_company_watchlist_summary(self, userId: str) -> dict[str, Any]:
        return {"status": "ok", "summary": self.service.get_company_watchlist_summary(userId)}

    # ----- §2.3 composition-oriented tools (catalogue v0.2.0) -----

    def get_user_profile_for_consent(
        self, userId: str, scopes: list[str]
    ) -> dict[str, Any]:
        """Return the user's portable civic profile, filtered to ``scopes``.

        The profile shape is deliberately stable across deployments so other
        open civic agents can compose. Each scope returns either a populated
        subset (if the project has that data for the user) or an explicit
        empty placeholder so the caller can detect "user has no employment
        record yet" without inspecting field-by-field.
        """

        summary = self.service.get_company_watchlist_summary(userId)
        profile: dict[str, Any] = {
            "userId": userId,
            "scopes": list(scopes),
            "schemaVersion": "0.1.0",
            "consentRecordedAt": _now_iso(),
        }
        if "identity" in scopes:
            profile["identity"] = {
                "userId": userId,
                "displayName": None,
                "publicHandle": None,
                "preferredLocale": "en",
            }
        if "residence" in scopes:
            profile["residence"] = {
                "country": None,
                "statusType": None,
                "workAuthorisation": None,
            }
        if "employment" in scopes:
            profile["employment"] = {
                "currentStatus": None,
                "targetRoleFamilies": [],
                "languageLevels": {},
                "escoSkillCodes": [],
                "watchedCompanies": summary.get("watched_companies", 0)
                if isinstance(summary, dict)
                else 0,
            }
        if "cv" in scopes:
            profile["cv"] = {
                "present": False,
                "lastUpdatedAt": None,
                "note": (
                    "CV content is not surfaced through this tool; consume "
                    "the user's CV via a separate consent-bound tool when "
                    "the use case requires it."
                ),
            }
        if "outcomes" in scopes:
            profile["outcomes"] = _read_user_outcomes(self.service, userId)
        if "preferences" in scopes:
            profile["preferences"] = {
                "remote": None,
                "salaryRange": None,
                "locationStrings": [],
            }
        return {"status": "ok", "profile": profile}

    def propose_referral(
        self,
        userId: str,
        targetAgent: str,
        reason: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Emit a structured referral object the receiving agent can consume.

        No persistence: the calling agent is responsible for surfacing the
        referral to the user and handing over on consent. The shape mirrors
        a small subset of HL7 FHIR ServiceRequest (referral.intent / .priority /
        .reasonCode / .supportingInfo) so the surface stays familiar to civic-
        services integrators.
        """

        return {
            "status": "ok",
            "referral": {
                "referralId": f"ref-{uuid.uuid4().hex[:12]}",
                "schemaVersion": "0.1.0",
                "issuedAt": _now_iso(),
                "sourceAgent": "directjob-scout",
                "targetAgent": targetAgent,
                "userId": userId,
                "intent": "proposed",
                "priority": "routine",
                "reasonCode": reason,
                "supportingInfo": context or {},
                "userConsentRequired": True,
            },
        }

    def query_esco_skill(
        self,
        query: str,
        type: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Substring-match the persona-panel mini-dataset.

        Replaced by the full ESCO dataset integration in Week 2 §2.4. The
        output shape is deliberately stable so callers do not need to be
        aware of the underlying dataset version.
        """

        lowered = (query or "").strip().lower()
        kind = (type or "any").lower()
        candidates = (
            entry for entry in _ESCO_REFERENCE_DATASET
            if kind in ("any", entry["type"])
        )
        matches = [
            entry for entry in candidates
            if lowered and lowered in entry["label"].lower()
        ]
        if limit is not None:
            matches = matches[: max(0, int(limit))]
        return {
            "status": "ok",
            "datasetVersion": "v0-mini",
            "totalCandidates": len(_ESCO_REFERENCE_DATASET),
            "matches": matches,
        }

    def export_eures_compatible(
        self, userId: str, discoveredJobId: str
    ) -> dict[str, Any]:
        """Project a stored discovered job into EURES-compatible fields.

        The EURES standard defines a JSON-LD-adjacent JobPosting shape that
        overlaps significantly with schema.org JobPosting. We project the
        fields we currently store onto the EURES vocabulary and return a
        ``status: not_found`` problem when the job id does not resolve.
        """

        repository = getattr(self.service, "repository", None)
        if repository is None:
            return {"status": "error", "error": "no_repository"}
        try:
            job = repository.get_discovered_job(userId, discoveredJobId)
        except Exception as error:
            return {"status": "not_found", "error": str(error)}
        if not job:
            return {"status": "not_found"}
        job_dict = asdict(job) if hasattr(job, "__dataclass_fields__") else dict(job)
        return {
            "status": "ok",
            "eures": {
                "id": job_dict.get("id"),
                "title": job_dict.get("title"),
                "datePosted": job_dict.get("posted_at") or job_dict.get("created_at"),
                "validThrough": job_dict.get("valid_until"),
                "hiringOrganization": {
                    "name": job_dict.get("company") or job_dict.get("company_name"),
                    "url": job_dict.get("company_url"),
                },
                "jobLocation": {
                    "addressLocality": job_dict.get("location"),
                    "addressCountry": job_dict.get("country"),
                },
                "description": job_dict.get("description"),
                "url": job_dict.get("url"),
                "employmentType": job_dict.get("employment_type"),
                "sourceProvider": job_dict.get("source") or job_dict.get("provider"),
                "schemaConformance": "EURES-compatible-subset-v0",
            },
        }

    def record_user_outcome(
        self,
        userId: str,
        jobId: str,
        outcomeType: str,
        occurredAt: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """Append an outcome event to ``data/user_outcomes.jsonl``.

        File-based by deliberate choice (see top-of-module rationale). The
        outcome enum is enforced both by the inputSchema and again here so
        a direct call to the tool method outside the MCP server still
        rejects invalid values cleanly.
        """

        if outcomeType not in _OUTCOME_TYPES:
            return {
                "status": "invalid_arguments",
                "error": f"outcomeType must be one of {list(_OUTCOME_TYPES)}",
            }
        event = {
            "outcomeId": f"out-{uuid.uuid4().hex[:12]}",
            "userId": userId,
            "jobId": jobId,
            "outcomeType": outcomeType,
            "occurredAt": occurredAt or _now_iso(),
            "recordedAt": _now_iso(),
            "schemaVersion": "0.1.0",
        }
        if note:
            event["note"] = note
        outcomes_path = _outcomes_path(self.service)
        outcomes_path.parent.mkdir(parents=True, exist_ok=True)
        with outcomes_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        return {"status": "ok", "event": event}


# ---------------------------------------------------------------------------
# Module-level helpers used by §2.3 tools.
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """ISO-8601 timestamp in UTC, second precision. Stable across calls
    so test fixtures can compare exactly when needed."""

    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _outcomes_path(service: CompanyDiscoveryService) -> Path:
    """Resolve the outcome-events JSON Lines file path. Derived from the
    service's repository data directory so tests can use a tmp path."""

    repository = getattr(service, "repository", None)
    base: Path | None = None
    if repository is not None:
        db_path = getattr(repository, "path", None) or getattr(repository, "db_path", None)
        if db_path:
            base = Path(db_path).parent
    if base is None:
        base = Path("data")
    return base / "user_outcomes.jsonl"


def _read_user_outcomes(
    service: CompanyDiscoveryService, user_id: str
) -> dict[str, Any]:
    """Read the outcome-events file and return a per-user summary plus the
    full event list for the user. Designed to be cheap on small files; if
    the file grows beyond a few thousand events we'll move to a SQLite
    table (the file format is then a migration source)."""

    path = _outcomes_path(service)
    if not path.exists():
        return {"events": [], "counts": {}, "total": 0}
    events: list[dict[str, Any]] = []
    counts: dict[str, int] = {kind: 0 for kind in _OUTCOME_TYPES}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("userId") != user_id:
                continue
            events.append(event)
            outcome_type = event.get("outcomeType")
            if outcome_type in counts:
                counts[outcome_type] += 1
    return {"events": events, "counts": counts, "total": len(events)}
