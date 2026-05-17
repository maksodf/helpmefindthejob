"""update_profile — change persona, location, or target roles.

Tier I (idempotent write): reversible by setting the previous values
back.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class UpdateProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona: str | None = Field(
        default=None,
        description=(
            "Which persona to switch to (tech / marketing / data / "
            "healthcare-clinical / legal / finance / sales / design / "
            "hr / operations / education / media / support / "
            "product-management / healthcare-management). Omit to "
            "leave unchanged."
        ),
        max_length=80,
    )
    location: str | None = Field(
        default=None,
        description=(
            "City or 'remote'. Omit to leave unchanged."
        ),
        max_length=120,
    )
    targetRoles: list[str] | None = Field(
        default=None,
        description=(
            "Target roles to override on the profile. Omit to leave "
            "unchanged. Empty list clears the field."
        ),
        max_length=50,
    )


def _update_profile_capture_inverse(
    inp: "UpdateProfileInput", ctx: dict[str, Any]
) -> dict[str, Any]:
    """Capture the previous values of any field the user is about to
    overwrite. Only fields explicitly being set in this call are
    captured — untouched fields don't go in the inverse.
    """
    profile = ctx["state"].profile_for(ctx["user_id"])
    inverse: dict[str, Any] = {}
    if inp.persona is not None:
        inverse["persona"] = getattr(profile, "persona_id", "") or "tech"
    if inp.location is not None:
        inverse["location"] = getattr(profile, "location", "") or ""
    if inp.targetRoles is not None:
        inverse["targetRoles"] = list(
            getattr(profile, "target_roles", None) or []
        )
    return inverse


def update_profile_handler(
    inp: UpdateProfileInput, ctx: dict[str, Any]
) -> ToolResult:
    payload = inp.model_dump(exclude_none=True)
    if not payload:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="nothing_to_update",
                message=(
                    "Nothing to update — at least one of persona, "
                    "location, or targetRoles must be set."
                ),
                user_hint=(
                    "Ask the user which field they want changed, then "
                    "re-issue the tool call."
                ),
            ),
        )
    out = ctx["state"].chat_handler_update_profile(ctx["user_id"], payload)
    if not out.get("ok", True):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="update_profile_failed",
                message=out.get("message", "Could not update profile."),
            ),
        )
    return ToolResult(ok=True, data={k: v for k, v in out.items() if k != "ok"})


register_tool(Tool(
    name="update_profile",
    label="Update your profile",
    description=(
        "Change persona, location, or target roles on the user's "
        "profile. At least one field must be provided."
    ),
    tier="I",
    input_schema=UpdateProfileInput,
    output_schema=BaseModel,
    handler=update_profile_handler,
    capture_inverse=_update_profile_capture_inverse,
    inverse_tool="update_profile",
    keywords=[
        r"\bupdate (?:my )?profile\b",
        r"\bchange (?:my )?(?:location|roles|seniority)\b",
        r"\bset (?:my )?(?:location|roles|seniority)\b",
    ],
    slash_aliases=["/profile", "/update-profile"],
    confirmation_template=(
        "Updating profile — persona={persona}, "
        "location={location}, targetRoles={targetRoles}. Confirm?"
    ),
))
