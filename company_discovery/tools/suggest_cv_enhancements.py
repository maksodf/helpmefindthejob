"""suggest_cv_enhancements — gap analysis vs. picked job.

Tier R (read-only). For the job the user picked in their journey,
compare the JD against the CV and surface 3-5 gap questions.
AI-backed when configured; otherwise a heuristic keyword diff with
an honest banner.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class SuggestCvEnhancementsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # No parameters — operates on the user's journey state (picked job
    # + CV on profile). Empty model with extra='forbid' produces a
    # clean ``properties: {}`` JSON schema.


def suggest_cv_enhancements_handler(
    inp: SuggestCvEnhancementsInput, ctx: dict[str, Any]
) -> ToolResult:
    out = ctx["state"].chat_handler_suggest_cv_enhancements(
        ctx["user_id"], {},
    )
    if not out.get("ok", True):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="suggest_cv_enhancements_failed",
                message=out.get("message", "Could not generate suggestions."),
            ),
        )
    return ToolResult(ok=True, data={k: v for k, v in out.items() if k != "ok"})


register_tool(Tool(
    name="suggest_cv_enhancements",
    label="Consult on CV enhancements specific to a JD",
    description=(
        "For the job the user picked in their journey, compare the "
        "JD against their CV and surface 3-5 gap questions. Use after "
        "the user has picked a specific job (their journey is in the "
        "drill / tailor phase)."
    ),
    tier="R",
    input_schema=SuggestCvEnhancementsInput,
    output_schema=BaseModel,
    handler=suggest_cv_enhancements_handler,
    keywords=[
        r"\b(?:consult|enhance|improve)\b.*\bcv\b",
        r"\bcv\b.*\b(?:gaps?|enhancements?|improvements?)\b",
    ],
    slash_aliases=["/consult", "/enhance-cv", "/cv-gaps"],
    confirmation_template=(
        "Consulting CV vs. picked JD for enhancement ideas."
    ),
))
