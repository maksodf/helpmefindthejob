# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Persona-aware ranking of suggestions / discovery results.

The persona-specific data (sector weights, label, description) lives in
:mod:`company_discovery.personas`. This module turns that data into a
deterministic scoring function so the ranking is predictable,
explainable, and unit-testable.

Score components (all 0–1):

- Sector affinity: how aligned the company sector is with the persona.
- Role focus: how many of the user's target-role keywords appear in
  the company name + sector + reason.
- Industry overlap: ``industry`` keyword present in the haystack.
- Location fit: ``location`` substring in the company location hint.
- Curated boost: items that came from the curated taxonomy get a small
  baseline lift over generic results.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .personas import DEFAULT_PERSONA_ID, get_persona


@dataclass
class RankedItem:
    name: str
    score: float
    breakdown: dict[str, float]
    reason: str


def _normalise(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").casefold().strip())


def _tokens(value: str | None) -> set[str]:
    return {token for token in re.findall(r"\w+", _normalise(value)) if token}


def _sector_score(sector: str | None, weights: Mapping[str, float]) -> float:
    haystack = _normalise(sector)
    if not haystack:
        return 0.45
    best = 0.45
    for keyword, weight in weights.items():
        if keyword in haystack:
            best = max(best, weight)
    return best


def rank_candidates(
    candidates: Iterable[dict[str, object]],
    *,
    target_roles: Sequence[str],
    industry: str | None = None,
    location: str | None = None,
    persona_label: str | None = None,
    persona_id: str | None = None,
) -> list[dict[str, object]]:
    persona = get_persona(persona_id or DEFAULT_PERSONA_ID)
    industry = industry or persona.default_industry
    persona_label = persona_label or persona.label
    role_tokens = set()
    for role in target_roles:
        role_tokens |= _tokens(role)
    industry_token = _normalise(industry)
    location_token = _normalise(location)

    ranked: list[dict[str, object]] = []
    for candidate in candidates:
        name = str(candidate.get("name") or candidate.get("category") or "")
        sector = candidate.get("sector") or candidate.get("category")
        reason = candidate.get("relevance_reason") or candidate.get("relevanceReason") or ""
        location_hint = candidate.get("location_hint") or candidate.get("locationHint") or ""

        haystack = _normalise(f"{name} {sector or ''} {reason}")
        sector_score = _sector_score(
            sector if isinstance(sector, str) else None,
            persona.sector_weights,
        )
        role_overlap = len(role_tokens & _tokens(haystack))
        role_score = min(1.0, 0.4 + role_overlap * 0.15) if role_overlap else 0.3
        industry_score = 0.6 if industry_token and industry_token in haystack else 0.4
        location_score = 0.0
        if location_token and isinstance(location_hint, str) and location_token in _normalise(location_hint):
            location_score = 0.15
        curated_boost = 0.05 if candidate.get("type") == "company" else 0.0

        composite = round(
            min(
                1.0,
                sector_score * 0.45
                + role_score * 0.30
                + industry_score * 0.10
                + location_score
                + curated_boost,
            ),
            3,
        )
        breakdown = {
            "sector": round(sector_score, 3),
            "roleOverlap": round(role_score, 3),
            "industry": round(industry_score, 3),
            "location": round(location_score, 3),
            "curatedBoost": round(curated_boost, 3),
        }
        explanation_parts = [f"persona={persona_label}"]
        if role_overlap:
            explanation_parts.append(f"matches {role_overlap} target-role token(s)")
        if isinstance(sector, str) and sector:
            explanation_parts.append(f"sector={sector}")
        if location_score:
            explanation_parts.append(f"in {location}")
        explanation = "; ".join(explanation_parts)

        new_candidate = dict(candidate)
        new_candidate["relevanceScore"] = composite
        new_candidate["relevanceBreakdown"] = breakdown
        existing_reason = (
            str(candidate.get("relevance_reason") or candidate.get("relevanceReason") or "").strip()
        )
        new_candidate["relevanceReason"] = (
            f"{existing_reason} ({explanation})" if existing_reason else explanation
        )
        ranked.append(new_candidate)
    ranked.sort(key=lambda item: item["relevanceScore"], reverse=True)
    return ranked
