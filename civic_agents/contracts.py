# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Typed specialist-agent contracts (the table in ``docs/agent-architecture.md`` §2).

Each specialist agent owns one civic capability and exposes a typed input →
output contract, validated as JSON Schema. The planner (``civic_agents/planner.py``)
routes sub-goals to specialists and validates every handoff against these
contracts, so a malformed input or a specialist that returns the wrong shape is
a loud, attributable failure rather than silent corruption flowing downstream.

A specialist is a plain callable today (some in-process via ``company_discovery``
helpers, some bound to the federated ``mesh/`` HTTP agents). The contract is
transport-independent: the same schema governs an in-process call and a
cross-agent CACP handoff.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jsonschema

#: Reusable JSON Schema fragments.
_STR = {"type": "string"}
_STR_ARRAY = {"type": "array", "items": {"type": "string"}}
_OBJECT = {"type": "object"}
_OBJECT_ARRAY = {"type": "array", "items": {"type": "object"}}


class ContractViolation(ValueError):
    """Raised when a payload fails its specialist contract. Carries the
    specialist name + direction (input/output) so a planner step failure is
    immediately attributable."""

    def __init__(self, specialist: str, direction: str, detail: str) -> None:
        self.specialist = specialist
        self.direction = direction
        self.detail = detail
        super().__init__(f"{specialist} {direction} violates contract: {detail}")


def _schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    """A closed-envelope object schema: the listed properties are required;
    additionalProperties is permitted for forward-compatible additive fields
    (mirrors the civic-profile schema's versioning posture)."""
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": True,
    }


@dataclass(frozen=True)
class SpecialistContract:
    """The typed boundary for one specialist agent."""

    name: str
    owns: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]

    def validate_input(self, payload: dict[str, Any]) -> None:
        self._validate(payload, self.input_schema, "input")

    def validate_output(self, payload: dict[str, Any]) -> None:
        self._validate(payload, self.output_schema, "output")

    def _validate(self, payload: dict[str, Any], schema: dict[str, Any], direction: str) -> None:
        try:
            jsonschema.validate(payload, schema)
        except jsonschema.ValidationError as exc:
            # exc.message is the human-readable reason; path locates the field.
            where = "/".join(str(p) for p in exc.absolute_path) or "<root>"
            raise ContractViolation(self.name, direction, f"{where}: {exc.message}") from exc


# ---------------------------------------------------------------------------
# The six specialist contracts (docs/agent-architecture.md §2)
# ---------------------------------------------------------------------------

CONTRACTS: dict[str, SpecialistContract] = {
    "cv_agent": SpecialistContract(
        name="cv_agent",
        owns="Sectional CV interview, photo consent, encrypted-at-rest persistence",
        input_schema=_schema(
            {"persona_slug": _STR, "target_lang": _STR, "prior_cv_text": _STR},
            ["persona_slug", "target_lang"],
        ),
        output_schema=_schema(
            {
                "cv_text": _STR,
                "cv_sections": _OBJECT,
                "cv_export_paths": _STR_ARRAY,
                "consent_log": _OBJECT,
            },
            ["cv_text", "cv_sections"],
        ),
    ),
    "search_agent": SpecialistContract(
        name="search_agent",
        owns="Aggregator fan-out, dedup, persona-aware ranking",
        input_schema=_schema(
            {"role": _STR, "location": _STR, "persona": _STR, "friction_class": _STR},
            ["role", "location"],
        ),
        output_schema=_schema(
            {
                "discovered_jobs": _OBJECT_ARRAY,
                "dedup_groups": _OBJECT,
                "source_attribution": _OBJECT,
            },
            ["discovered_jobs"],
        ),
    ),
    "anerkennung_agent": SpecialistContract(
        name="anerkennung_agent",
        owns="Recognition-status tracking, document checklist, Senatsverwaltung routing",
        input_schema=_schema(
            {"persona_slug": _STR, "current_status": _STR, "target_profession": _STR},
            ["persona_slug", "target_profession"],
        ),
        output_schema=_schema(
            {
                "recognition_steps": _OBJECT_ARRAY,
                "missing_documents": _STR_ARRAY,
                "target_deadline": _STR,
                "senatsverwaltung_url": _STR,
            },
            ["recognition_steps", "missing_documents"],
        ),
    ),
    "letter_agent": SpecialistContract(
        name="letter_agent",
        owns="DACH-norm Anschreiben drafting; friction-context proactive framing",
        input_schema=_schema(
            {"job": _OBJECT, "profile": _OBJECT, "friction_context": _STR},
            ["job", "profile"],
        ),
        output_schema=_schema(
            {
                "letter_text": _STR,
                "paragraph_edits": _OBJECT_ARRAY,
                "regenerate_handles": _STR_ARRAY,
            },
            ["letter_text"],
        ),
    ),
    "housing_agent": SpecialistContract(
        name="housing_agent",
        owns="Handoff to partner housing-search civic agent (Option B)",
        input_schema=_schema(
            {"user_consent_scope": _STR_ARRAY, "target_city": _STR, "employment_status": _STR},
            ["user_consent_scope", "target_city"],
        ),
        output_schema=_schema(
            {"referral_payload": _OBJECT, "partner_agent_uri": _STR},
            ["referral_payload"],
        ),
    ),
    "compliance_agent": SpecialistContract(
        name="compliance_agent",
        owns="Article 22 right-to-human-review surface, audit-log emission, consent enforcement",
        input_schema=_schema(
            {"event_class": _STR, "user_opaque_id": _STR, "ai_output_ref": _STR},
            ["event_class"],
        ),
        output_schema=_schema(
            {
                "audit_log_entry_id": {"type": ["string", "integer"]},
                "escalation_path": _STR,
                "retention_clock": _STR,
            },
            ["audit_log_entry_id", "escalation_path"],
        ),
    ),
}


def get_contract(name: str) -> SpecialistContract:
    """Return the contract for ``name`` or raise ``KeyError`` with the known set."""
    try:
        return CONTRACTS[name]
    except KeyError:
        raise KeyError(f"unknown specialist {name!r}; known: {sorted(CONTRACTS)}") from None
