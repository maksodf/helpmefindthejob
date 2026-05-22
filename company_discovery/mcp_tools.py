# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import timezone
from pathlib import Path
from typing import Any

from .service import CompanyDiscoveryService

# ---------------------------------------------------------------------------
# Reference ESCO dataset.
#
# The query_esco_skill tool returns matches loaded from the curated dataset
# under reference/esco/ (occupations.json + skills.json). The current
# v1-curated-2026-05-18 release carries ~30 occupations + ~50 skills covering
# the seven-persona panel per Decision 21 (Aïcha = nurse, Yusuf = mechanical
# engineer, Olga = frontend developer, Mahmoud = trade apprentice, Maria =
# home-based care worker, Käthe = returning Wiedereinstieg, Tobias = trade
# Quereinstieg) plus Bundesagentur-für-Arbeit 2025 shortage-occupation
# coverage. Entries optionally carry altLabels_de / altLabels_en arrays so
# colloquial synonyms (e.g. "Krankenschwester" -> 2221.1 Krankenpfleger/in)
# resolve to canonical codes; the PART 7 Loop 22 composability flow added
# this enrichment for the nurse entries. Codes derive from ISCO-08 / ESCO
# 1.1 (CC BY 4.0). See docs/esco-integration.md for the upgrade path to the
# full ESCO dataset.
#
# Source-class hierarchy (docs/grant/14-source-class-hierarchy.md): ESCO
# codes are class B (authoritative standardised taxonomy). The shortageDE2024
# flag is class C (BfA 2025 list). The tool surface carries both
# datasetVersion (the project's curated-version pin) and esco_uri (the
# upstream authoritative URI) so external consumers can verify provenance.
#
# The legacy 12-entry inline mini-dataset below is kept as a fallback for
# environments where the reference/ tree is unavailable (e.g. some Python
# packaging configurations). It is also used by tests that want to exercise
# the loader's fallback path.
# ---------------------------------------------------------------------------

_ESCO_REFERENCE_DATASET_FALLBACK: list[dict[str, str]] = [
    {"code": "2221.1", "label": "Registered nurse (general)", "type": "occupation", "isco": "2221"},
    {
        "code": "2221.2",
        "label": "Specialist nurse (clinical / Pflege)",
        "type": "occupation",
        "isco": "2221",
    },
    {
        "code": "5321.1",
        "label": "Healthcare assistant / Pflegehelfer",
        "type": "occupation",
        "isco": "5321",
    },
    {"code": "2144.1", "label": "Mechanical engineer", "type": "occupation", "isco": "2144"},
    {"code": "2512.1", "label": "Software developer", "type": "occupation", "isco": "2512"},
    {
        "code": "2513.1",
        "label": "Frontend developer / Web developer",
        "type": "occupation",
        "isco": "2513",
    },
    {
        "code": "7126.1",
        "label": "Plumbing trade apprentice / Anlagenmechaniker SHK",
        "type": "occupation",
        "isco": "7126",
    },
    {
        "code": "5322.1",
        "label": "Home-based personal-care worker / Häusliche Pflegehilfe",
        "type": "occupation",
        "isco": "5322",
    },
    {"code": "S1.0.1", "label": "Clinical-German communication", "type": "skill"},
    {"code": "S1.0.2", "label": "Patient documentation", "type": "skill"},
    {"code": "S5.0.1", "label": "TypeScript / React frontend development", "type": "skill"},
    {"code": "S2.0.1", "label": "Mechanical CAD (Solidworks / CATIA)", "type": "skill"},
]


# Module-level cache for the loaded dataset. Populated lazily on first call
# to :func:`_load_esco_reference_dataset` and not refreshed during a process
# lifetime — the file is repo-tracked reference data, not user data.
_ESCO_DATASET_CACHE: list[dict[str, Any]] | None = None


def _load_esco_reference_dataset() -> list[dict[str, Any]]:
    """Load the curated ESCO dataset from `reference/esco/*.json`.

    Falls back to :data:`_ESCO_REFERENCE_DATASET_FALLBACK` if the files are
    not present. Cached for the process lifetime.
    """

    global _ESCO_DATASET_CACHE
    if _ESCO_DATASET_CACHE is not None:
        return _ESCO_DATASET_CACHE

    base = Path(__file__).resolve().parent.parent / "reference" / "esco"
    occupations_path = base / "occupations.json"
    skills_path = base / "skills.json"
    if not occupations_path.exists() or not skills_path.exists():
        _ESCO_DATASET_CACHE = list(_ESCO_REFERENCE_DATASET_FALLBACK)
        return _ESCO_DATASET_CACHE

    combined: list[dict[str, Any]] = []
    for path, kind in ((occupations_path, "occupation"), (skills_path, "skill")):
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        for entry in data.get("entries", []):
            # Normalised match record. `label` is the EN label by default
            # (compat with the legacy mini-dataset shape); both EN + DE
            # remain available for callers that want locale-aware display.
            record: dict[str, Any] = {
                "code": entry["code"],
                "label": entry.get("label_en") or entry.get("label") or "",
                "label_en": entry.get("label_en") or entry.get("label") or "",
                "label_de": entry.get("label_de") or "",
                "type": kind,
            }
            for optional_key in (
                "isco",
                "category",
                "cefr",
                "personas",
                "shortageDE2024",
                "esco_uri",
                "altLabels_en",
                "altLabels_de",
            ):
                if optional_key in entry:
                    record[optional_key] = entry[optional_key]
            combined.append(record)

    _ESCO_DATASET_CACHE = combined
    return combined


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
        "description": "Extract jobs from supplied HTML without fetching: tries known ATS adapters first (Greenhouse / Lever / Personio), falls back to JobPosting JSON-LD parsing and visible job-link anchor extraction.",
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
            "Cross-agent shared taxonomy. Backed by the v1-curated "
            "2026-05-18 reference dataset (~80 entries spanning ISCO-08 "
            "occupations + ESCO skills, aligned to the seven-persona "
            "panel and Bundesagentur-für-Arbeit 2025 shortage codes). "
            "Matches against EN + DE labels and altLabels arrays, so "
            "colloquial synonyms (e.g. 'Krankenschwester') resolve to "
            "canonical entries."
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
    # phase2-backlog #11 (2026-05-22): referral lifecycle.
    # propose_referral now persists; list + update tools below
    # let users + agents drive the lifecycle to completion.
    {
        "name": "list_referrals",
        "description": "List referrals issued for a user. Optional status filter (proposed / accepted / declined / followed_up / expired) for the loosen-affordance flow + cost-saving doctrine outcome aggregation. Returns most-recent first.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": [
                        "proposed",
                        "accepted",
                        "declined",
                        "followed_up",
                        "expired",
                    ],
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                },
            },
            "required": ["userId"],
        },
    },
    {
        "name": "update_referral_status",
        "description": "Update an existing referral's lifecycle status. Allowed transitions: proposed→accepted, proposed→declined, accepted→followed_up, *→expired. Optional outcome_note free-text the user supplies. Returns the updated referral.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {"type": "string"},
                "referralId": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": [
                        "accepted",
                        "declined",
                        "followed_up",
                        "expired",
                    ],
                },
                "outcomeNote": {"type": "string"},
            },
            "required": ["userId", "referralId", "status"],
        },
    },
]


class CompanyDiscoveryMCPTools:
    def __init__(self, service: CompanyDiscoveryService) -> None:
        self.service = service

    def suggest_relevant_companies(
        self, targetRoles: list[str], industry: str, location: str | None = None
    ) -> dict[str, Any]:
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

    def scan_company_career_page(
        self, userId: str, companyId: str, careerPageUrl: str | None = None
    ) -> dict[str, Any]:
        scan = self.service.scan_company_career_page(userId, companyId, careerPageUrl)
        return {"status": scan.status, "scan": asdict(scan)}

    def extract_direct_jobs_from_company_site(
        self, userId: str, companyId: str, pageUrl: str, html: str
    ) -> dict[str, Any]:
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

    def get_user_profile_for_consent(self, userId: str, scopes: list[str]) -> dict[str, Any]:
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
        """Emit + persist a structured referral object.

        phase2-backlog #11 (2026-05-22): now persists into the
        repository's referrals table so the user can come back and
        see + act on outstanding referrals. The returned shape
        still mirrors HL7 FHIR ServiceRequest for civic-services
        integrator familiarity; the persisted record adds a
        lifecycle ``status`` field (proposed → accepted / declined
        → followed_up / expired). The full lifecycle is exercised
        via ``list_referrals`` + ``update_referral_status``.

        Falls back to the legacy stub shape (no persistence) if
        the service doesn't expose a repository — keeps the tool
        usable in any agent harness that constructs the service
        without a backing store.
        """

        from company_discovery.models import Referral

        referral_model: Referral | None = None
        # Try to persist via the repository when available
        try:
            repo = self.service.repository  # type: ignore[attr-defined]
        except AttributeError:
            repo = None
        if repo is not None:
            try:
                referral_model = Referral(
                    user_id=userId,
                    target_agent=targetAgent,
                    reason_code=reason,
                    supporting_info=dict(context or {}),
                )
                repo.save_referral(referral_model)
            except Exception:  # noqa: BLE001 - degrade to stub if persistence fails
                referral_model = None

        if referral_model is not None:
            return {
                "status": "ok",
                "referral": {
                    "referralId": referral_model.id,
                    "schemaVersion": "0.1.0",
                    "issuedAt": referral_model.created_at.isoformat(),
                    "sourceAgent": referral_model.source_agent,
                    "targetAgent": referral_model.target_agent,
                    "userId": referral_model.user_id,
                    "intent": referral_model.intent,
                    "priority": referral_model.priority,
                    "reasonCode": referral_model.reason_code,
                    "supportingInfo": referral_model.supporting_info,
                    "userConsentRequired": referral_model.user_consent_required,
                    "status": referral_model.status,
                },
            }

        # Legacy stub path: no repo wired — keep the structured
        # response shape so existing callers don't break.
        return {
            "status": "ok",
            "referral": {
                "referralId": f"ref-{uuid.uuid4().hex[:12]}",
                "schemaVersion": "0.1.0",
                "issuedAt": _now_iso(),
                "sourceAgent": "helpmefindthejob",
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
        type: str | None = None,  # noqa: A002 - param name is part of the public MCP tool JSON schema; cannot rename without breaking external clients
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Substring-match the curated ESCO reference dataset.

        Matches against both the English and German labels so a German-
        language query against a record with an English `label_en` still
        resolves. The output shape is stable across the v0-mini fallback
        and the v1-curated dataset; consumers can switch dataset versions
        without code changes.
        """

        dataset = _load_esco_reference_dataset()
        lowered = (query or "").strip().lower()
        kind = (type or "any").lower()
        candidates = (entry for entry in dataset if kind in ("any", entry["type"]))

        def _matches(entry: dict[str, Any]) -> bool:
            if not lowered:
                return False
            if lowered in entry.get("label_en", entry.get("label", "")).lower():
                return True
            if lowered in entry.get("label_de", "").lower():
                return True
            for alt in entry.get("altLabels_en", []) or []:
                if lowered in str(alt).lower():
                    return True
            for alt in entry.get("altLabels_de", []) or []:
                if lowered in str(alt).lower():
                    return True
            return False

        matches = [entry for entry in candidates if _matches(entry)]
        if limit is not None:
            matches = matches[: max(0, int(limit))]
        return {
            "status": "ok",
            "datasetVersion": (
                "v1-curated-2026-05-18"
                if dataset is not _ESCO_REFERENCE_DATASET_FALLBACK
                else "v0-mini-fallback"
            ),
            "totalCandidates": len(dataset),
            "matches": matches,
        }

    def export_eures_compatible(self, userId: str, discoveredJobId: str) -> dict[str, Any]:
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
        except Exception as error:  # noqa: BLE001 - repository surface differs across backends (sqlite vs in-memory mock); any lookup failure is reported as not_found to the MCP client
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
        # Cost-saving metrics wiring (phase2-backlog #69 follow-up).
        # An "applied" outcome is the user actually shipping a job
        # application — the primary unit of higher_apply_rate. The
        # event also informs fewer_wrong_fit_apps when the note
        # carries a fit_score field >= 75 (high-fit application).
        # Opt-in via HELPMEFINDTHEJOB_COST_METRICS env var; off by
        # default per honesty-doctrine. Best-effort: never raises.
        try:
            from company_discovery.cost_saving_metrics import (
                CostSavingMetricsLog,
                MECHANISM_HIGHER_APPLY_RATE,
                MECHANISM_FEWER_WRONG_FIT_APPS,
                is_collection_enabled,
            )

            if outcomeType == "applied" and is_collection_enabled():
                from company_discovery import audit_log as _audit_log_mod

                metrics_path = outcomes_path.parent / "cost_saving_metrics.jsonl"
                cs_log = CostSavingMetricsLog(
                    metrics_path,
                    salt=_audit_log_mod.default_emitter().salt,
                    enabled=True,
                )
                cs_log.record(
                    MECHANISM_HIGHER_APPLY_RATE,
                    user_id=userId,
                    value=1.0,
                    unit="applications",
                    metadata={"job_id": jobId},
                )
                # If the caller passed fit_score in the note as
                # JSON (some HTTP handlers do this so the funnel
                # can be correlated against the discovered_jobs.
                # confidence_score), parse + emit the second
                # mechanism.
                fit_score = None
                if note:
                    try:
                        as_json = json.loads(note)
                        if isinstance(as_json, dict):
                            fit_score = float(as_json.get("fit_score") or 0.0)
                    except (ValueError, TypeError):
                        fit_score = None
                if fit_score is not None and fit_score >= 75:
                    cs_log.record(
                        MECHANISM_FEWER_WRONG_FIT_APPS,
                        user_id=userId,
                        value=1.0,
                        unit="high_fit_applications",
                        metadata={
                            "job_id": jobId,
                            "fit_score": fit_score,
                        },
                    )
        except Exception:  # noqa: BLE001 - best-effort
            pass
        return {"status": "ok", "event": event}

    # ------------------------------------------------------------------
    # phase2-backlog #11 (2026-05-22): referral lifecycle
    # ------------------------------------------------------------------

    def list_referrals(
        self,
        userId: str,
        status: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Return the user's referrals, optionally filtered by
        status, most-recent first."""

        try:
            repo = self.service.repository  # type: ignore[attr-defined]
        except AttributeError:
            return {
                "status": "unavailable",
                "error": "no repository configured",
                "referrals": [],
            }
        from company_discovery.models import REFERRAL_STATUSES

        if status is not None and status not in REFERRAL_STATUSES:
            return {
                "status": "invalid_arguments",
                "error": f"status must be one of {list(REFERRAL_STATUSES)}",
                "referrals": [],
            }
        if limit < 1 or limit > 200:
            limit = 50
        items = repo.list_referrals(user_id=userId, status=status)[:limit]
        return {
            "status": "ok",
            "referrals": [
                {
                    "referralId": r.id,
                    "userId": r.user_id,
                    "sourceAgent": r.source_agent,
                    "targetAgent": r.target_agent,
                    "intent": r.intent,
                    "priority": r.priority,
                    "reasonCode": r.reason_code,
                    "supportingInfo": r.supporting_info,
                    "status": r.status,
                    "userConsentRequired": r.user_consent_required,
                    "outcomeNote": r.outcome_note,
                    "issuedAt": r.created_at.isoformat(),
                    "updatedAt": r.updated_at.isoformat(),
                }
                for r in items
            ],
        }

    def update_referral_status(
        self,
        userId: str,
        referralId: str,
        status: str,
        outcomeNote: str | None = None,
    ) -> dict[str, Any]:
        """Advance a referral's lifecycle status with validation.

        Allowed transitions (enforced here):
        - proposed → accepted
        - proposed → declined
        - accepted → followed_up
        - any → expired

        Cross-user attack defense: the caller's ``userId`` must
        match the referral's stored ``user_id`` — a malicious
        caller can't update someone else's referral.
        """

        from company_discovery.models import REFERRAL_STATUSES

        # Allowed transitions per source status
        allowed_transitions = {
            "proposed": {"accepted", "declined", "expired"},
            "accepted": {"followed_up", "declined", "expired"},
            "declined": {"expired"},
            "followed_up": {"expired"},
            "expired": set(),
        }

        if status not in REFERRAL_STATUSES:
            return {
                "status": "invalid_arguments",
                "error": f"status must be one of {list(REFERRAL_STATUSES)}",
            }
        try:
            repo = self.service.repository  # type: ignore[attr-defined]
        except AttributeError:
            return {"status": "unavailable", "error": "no repository configured"}

        referral = repo.get_referral(referralId)
        if referral is None:
            return {"status": "not_found", "error": "no such referral"}

        # Cross-tenant defense: only the referral's owner can update
        if referral.user_id != userId:
            return {"status": "not_found", "error": "no such referral"}

        # Transition validation
        if status not in allowed_transitions.get(referral.status, set()):
            return {
                "status": "invalid_transition",
                "error": (
                    f"cannot transition from {referral.status!r} to "
                    f"{status!r}"
                ),
                "currentStatus": referral.status,
            }

        # Apply
        referral.status = status
        # intent mirror — keeps the FHIR-aligned outward shape
        # consistent (intent goes proposed → directive when
        # accepted, completed when followed_up)
        if status == "accepted":
            referral.intent = "directive"
        elif status == "followed_up":
            referral.intent = "completed"
        if outcomeNote:
            referral.outcome_note = outcomeNote[:1000]
        repo.save_referral(referral)
        return {
            "status": "ok",
            "referral": {
                "referralId": referral.id,
                "userId": referral.user_id,
                "status": referral.status,
                "intent": referral.intent,
                "outcomeNote": referral.outcome_note,
                "updatedAt": referral.updated_at.isoformat(),
            },
        }


# ---------------------------------------------------------------------------
# Module-level helpers used by §2.3 tools.
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """ISO-8601 timestamp in UTC, second precision. Stable across calls
    so test fixtures can compare exactly when needed."""

    from datetime import datetime

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


def _read_user_outcomes(service: CompanyDiscoveryService, user_id: str) -> dict[str, Any]:
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
