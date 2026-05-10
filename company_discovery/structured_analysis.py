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
_FIT_RE = re.compile(r"fit\s*score\s*[:=]\s*(\d+(?:\.\d+)?)", re.I)
_RECOMMEND_RE = re.compile(r"recommend(?:ation)?\s*[:=]\s*(apply|consider|skip)", re.I)
_LIST_FIELDS = ("tools", "risks")


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
                parsed.get("fitScore") or parsed.get("fit_score") or parsed.get("score")
            )
            recommendation = parsed.get("recommendation") or parsed.get("decision")
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
