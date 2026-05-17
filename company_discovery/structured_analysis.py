# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Parse free-form AI analysis output into structured fit fields.

The system prompt asks the model to emit a JSON block. When the model
complies we use it directly; when it doesn't we fall back to a series
of regex extractors that pull the most common labelled fields out of
the freeform text. The output shape is deliberately small and stable.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


_VALID_RECOMMENDATIONS = {"apply", "consider", "skip"}


@dataclass
class StructuredFit:
    fit_score: float | None = None
    recommendation: str | None = None
    healthcare_relevance: str | None = None
    junior_suitability: str | None = None
    required_experience: str | None = None
    language_requirements: str | None = None
    tools: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "fitScore": self.fit_score,
            "recommendation": self.recommendation,
            "healthcareRelevance": self.healthcare_relevance,
            "juniorSuitability": self.junior_suitability,
            "requiredExperience": self.required_experience,
            "languageRequirements": self.language_requirements,
            "tools": list(self.tools),
            "risks": list(self.risks),
            "notes": self.notes,
        }


_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}")
# Score regex must accept many shapes:
#   "Fit score: 0.72"      "fit_score = 0.4"      "Fit Score is 0.91"
#   "Score: 0.55"          "fitScore: 0.7"        "fitScore":0.7
#   The non-digit gap is capped at 12 chars so we don't match the wrong
#   number ("Score for X = 5 years; 0.72") and avoid runaway scans.
_FIT_RE = re.compile(
    r"(?:fit[\s_]*)?score[^\d]{0,12}(\d+(?:\.\d+)?)",
    re.I,
)
# Recommendation regex must accept many natural-language shapes:
#   "Recommendation: apply"     "recommend: apply"
#   "I'd recommend you APPLY"   "Recommending apply"
#   "recommendation = consider"
# The separator gap allows up to 30 chars including small connector
# words ("you", "to", "that"). We require a word-boundary around the
# verdict so "applyer"/"applying" don't accidentally match.
_RECOMMEND_RE = re.compile(
    r"recommend\w*[\s\w:=\-,.'\"]{0,30}?\b(apply|consider|skip)\b",
    re.I,
)
_LIST_FIELDS = ("tools", "risks")


def _first_present(parsed: dict, *keys: str):
    """Return parsed[k] for the first k that EXISTS — even when the
    value is falsy (e.g. ``0``). Replaces the ``a or b or c`` pattern
    which silently drops a legitimate ``0`` score."""
    for k in keys:
        if k in parsed:
            return parsed[k]
    return None


def parse_freeform(output: str) -> StructuredFit:
    if not output:
        return StructuredFit()
    structured = StructuredFit(notes=output.strip())

    block = _JSON_BLOCK_RE.search(output)
    if block:
        try:
            parsed = json.loads(block.group(0))
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            structured.fit_score = _coerce_float(
                _first_present(parsed, "fitScore", "fit_score", "score")
            )
            recommendation = (_first_present(parsed, "recommendation", "decision"))
            if isinstance(recommendation, str) and recommendation.casefold() in _VALID_RECOMMENDATIONS:
                structured.recommendation = recommendation.casefold()
            for src, dst in (
                ("healthcareRelevance", "healthcare_relevance"),
                ("healthcare_relevance", "healthcare_relevance"),
                ("juniorSuitability", "junior_suitability"),
                ("junior_suitability", "junior_suitability"),
                ("requiredExperience", "required_experience"),
                ("required_experience", "required_experience"),
                ("languageRequirements", "language_requirements"),
                ("language_requirements", "language_requirements"),
            ):
                value = parsed.get(src)
                if isinstance(value, str) and value.strip():
                    setattr(structured, dst, value.strip())
            for field_name in _LIST_FIELDS:
                items = parsed.get(field_name) or parsed.get(field_name.title()) or []
                if isinstance(items, list):
                    setattr(structured, field_name, [str(item) for item in items if item])
                elif isinstance(items, str):
                    setattr(structured, field_name, [item.strip() for item in items.split(",") if item.strip()])

    if structured.fit_score is None:
        match = _FIT_RE.search(output)
        if match:
            structured.fit_score = _coerce_float(match.group(1))
    if not structured.recommendation:
        match = _RECOMMEND_RE.search(output)
        if match:
            structured.recommendation = match.group(1).casefold()
    if structured.fit_score is not None and structured.fit_score > 1:
        structured.fit_score = round(structured.fit_score / 100.0, 3) if structured.fit_score <= 100 else 1.0

    return structured


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def system_prompt_addendum() -> str:
    return (
        "If you can, return the structured fields as a single JSON object on a line by itself, "
        "with keys: fitScore (0-1), recommendation (apply|consider|skip), healthcareRelevance, "
        "juniorSuitability, requiredExperience, languageRequirements, tools (array), risks (array)."
    )
