"""create_saved_search — create a daily-watched query.

Tier I (idempotent write): reversible by deleting the search row.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class CreateSavedSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description=(
            "Short label for the saved search, e.g. 'Senior Backend "
            "Berlin'."
        ),
        min_length=1, max_length=120,
    )
    targetRoles: list[str] = Field(
        description=(
            "One or more roles to watch for, e.g. ['backend "
            "engineer', 'platform engineer']. Single role is fine."
        ),
        min_length=1, max_length=50,
    )
    location: str | None = Field(
        default=None,
        description=(
            "City, 'remote', or blank for anywhere. Defaults to the "
            "user's profile location if omitted."
        ),
        max_length=120,
    )


def _create_saved_search_capture_inverse_after(
    inp: "CreateSavedSearchInput", ctx: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Capture the new saved search's ID AFTER the handler creates
    it. ``delete_saved_search`` is the inverse."""
    search_id = result.get("id") or result.get("searchId")
    if not search_id:
        return {}
    return {"searchId": search_id}


def create_saved_search_handler(
    inp: CreateSavedSearchInput, ctx: dict[str, Any]
) -> ToolResult:
    out = ctx["state"].chat_handler_create_saved_search(
        ctx["user_id"], inp.model_dump(exclude_none=True),
    )
    if not out.get("ok", True):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="create_saved_search_failed",
                message=out.get("message", "Could not create the search."),
            ),
        )
    return ToolResult(ok=True, data={k: v for k, v in out.items() if k != "ok"})


register_tool(Tool(
    name="create_saved_search",
    label="Create a saved search",
    description=(
        "Create a daily-watched query for a role + location. Stored "
        "saved searches run on a schedule; new matches appear in the "
        "user's Jobs view and trigger optional digest notifications."
    ),
    tier="I",
    input_schema=CreateSavedSearchInput,
    output_schema=BaseModel,
    handler=create_saved_search_handler,
    capture_inverse_after=_create_saved_search_capture_inverse_after,
    inverse_tool="delete_saved_search",
    keywords=[
        r"\b(?:create|new|add) (?:a )?(?:saved )?search\b",
        r"\bwatch\b.*\b(?:role|position|job)\b",
    ],
    slash_aliases=["/new-search", "/search"],
    confirmation_template=(
        "Saved search **{name}**: roles={targetRoles}, "
        "location={location}. Confirm?"
    ),
))
