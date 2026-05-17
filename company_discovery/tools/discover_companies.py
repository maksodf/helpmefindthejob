"""discover_companies — on-demand company-discovery scan.

Tier R (read-only — outputs a list of candidate companies). Maps
to the existing ``POST /api/discover-companies`` route. When fields
are omitted, the user's profile defaults fill them in.

This is the chat equivalent of clicking "Discover Companies" on the
Companies view. Useful when the user pivots persona or location and
wants fresh suggestions immediately.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class DiscoverCompaniesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    targetRoles: list[str] | None = Field(
        default=None,
        description=(
            "Override roles for this scan. Omit to use the user's "
            "profile target_roles."
        ),
        max_length=50,
    )
    industry: str | None = Field(
        default=None,
        description=(
            "Override industry filter. Omit to use the user's "
            "profile industry."
        ),
        max_length=80,
    )
    location: str | None = Field(
        default=None,
        description=(
            "Override location filter (city / region / country). "
            "Omit to use the user's profile location."
        ),
        max_length=120,
    )
    personaId: str | None = Field(
        default=None,
        description=(
            "Override persona for this scan. Omit to use the user's "
            "current persona."
        ),
        max_length=80,
    )
    limit: int = Field(
        default=12,
        description="Max companies to return (1-50).",
        ge=1, le=50,
    )


def _handler(
    inp: DiscoverCompaniesInput, ctx: dict[str, Any]
) -> ToolResult:
    state = ctx["state"]
    user_id = ctx["user_id"]
    profile = state.profile_for(user_id)
    from company_discovery.personas import get_persona, DEFAULT_PERSONA_ID
    persona_id = (
        inp.personaId
        or getattr(profile, "persona_id", None)
        or DEFAULT_PERSONA_ID
    )
    persona = get_persona(persona_id)
    target_roles = (
        inp.targetRoles
        or list(getattr(profile, "target_roles", None)
                 or persona.default_target_roles)
    )
    industry = (
        inp.industry
        or getattr(profile, "industry", None)
        or persona.default_industry
    )
    location = inp.location or getattr(profile, "location", None) or None
    try:
        results = state.discover_companies(
            target_roles=target_roles,
            industry=industry,
            location=location,
            limit=inp.limit,
            persona_id=persona.id,
        )
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            ok=False,
            error=ToolError(
                code="discovery_failed",
                message=f"Discovery scan failed: {exc}",
                retryable=True,
            ),
        )
    summary = (
        f"Found {len(results)} candidate companies for "
        f"**{', '.join(target_roles[:3])}** in "
        f"**{location or 'anywhere'}**."
    )
    return ToolResult(
        ok=True,
        data={
            "message": summary,
            "results": results,
            "personaId": persona.id,
            "count": len(results),
        },
    )


register_tool(Tool(
    name="discover_companies",
    label="Run a company-discovery scan now",
    description=(
        "Trigger an on-demand scan that returns candidate companies "
        "matching the user's persona + role + location. Read-only — "
        "results are not auto-added to the watchlist; the user (or "
        "a follow-up add_company tool call) decides which to keep."
    ),
    tier="R",
    input_schema=DiscoverCompaniesInput,
    output_schema=BaseModel,
    handler=_handler,
    keywords=[
        r"\bdiscover (?:more )?companies\b",
        r"\bsuggest (?:more )?companies\b",
        r"\bfind (?:more )?(?:companies|employers)\b",
    ],
    slash_aliases=["/discover", "/suggest-companies"],
    confirmation_template="Running a company-discovery scan now.",
))
