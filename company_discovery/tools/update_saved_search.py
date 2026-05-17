"""update_saved_search — edit an existing saved search.

Tier I (idempotent write): reversible by updating back to the
previous field values, which are captured pre-execution.

Phase 1 Step 7 — closes the CRUD-parity gap where the chat could
create saved searches but never edit them.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class UpdateSavedSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    searchId: str = Field(
        description="The ID of the saved search to edit.",
        min_length=1, max_length=120,
    )
    name: str | None = Field(
        default=None,
        description="New display name. Omit to leave unchanged.",
        max_length=120,
    )
    targetRoles: list[str] | None = Field(
        default=None,
        description=(
            "New role list. Replaces the existing list when set. "
            "Omit to leave unchanged."
        ),
        max_length=50,
    )
    location: str | None = Field(
        default=None,
        description=(
            "New location, or 'remote'. Omit to leave unchanged. "
            "Pass an empty string to clear the location."
        ),
        max_length=120,
    )
    notes: str | None = Field(
        default=None,
        description=(
            "New free-form notes. Omit to leave unchanged."
        ),
        max_length=2000,
    )


def _capture_inverse(
    inp: "UpdateSavedSearchInput", ctx: dict[str, Any]
) -> dict[str, Any]:
    """Snapshot the search's current values so the undo dispatch
    can restore them. Only fields the caller is about to change get
    captured."""
    state = ctx["state"]
    user_id = ctx["user_id"]
    repo = state.repository
    existing = next(
        (s for s in repo.list_saved_searches(user_id)
         if s.id == inp.searchId),
        None,
    )
    if existing is None:
        return {}
    inverse: dict[str, Any] = {"searchId": inp.searchId}
    if inp.name is not None:
        inverse["name"] = existing.name
    if inp.targetRoles is not None:
        inverse["targetRoles"] = list(existing.target_roles or [])
    if inp.location is not None:
        inverse["location"] = existing.location or ""
    if inp.notes is not None:
        inverse["notes"] = existing.notes or ""
    return inverse


def _handler(
    inp: UpdateSavedSearchInput, ctx: dict[str, Any]
) -> ToolResult:
    state = ctx["state"]
    user_id = ctx["user_id"]
    repo = state.repository
    existing = next(
        (s for s in repo.list_saved_searches(user_id)
         if s.id == inp.searchId),
        None,
    )
    if existing is None:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="search_not_found",
                message=(
                    f"Saved search {inp.searchId!r} not found. "
                    "Ask the user to list their saved searches "
                    "first."
                ),
            ),
        )
    if inp.name is not None:
        existing.name = inp.name
    if inp.targetRoles is not None:
        existing.target_roles = list(inp.targetRoles)
    if inp.location is not None:
        existing.location = inp.location or None
    if inp.notes is not None:
        existing.notes = inp.notes or None
    from datetime import datetime, timezone
    existing.updated_at = datetime.now(timezone.utc)
    repo.save_saved_search(existing)
    state.log_analytics(
        user_id, "chat_cmd",
        {"name": "update_saved_search", "id": inp.searchId},
    )
    return ToolResult(
        ok=True,
        data={
            "message": f"Updated saved search **{existing.name}**.",
            "id": existing.id,
        },
    )


register_tool(Tool(
    name="update_saved_search",
    label="Edit a saved search",
    description=(
        "Edit an existing saved search's name, target roles, "
        "location, or notes. Pass only the fields you want to "
        "change; omit fields you want left alone. Reversible via "
        "the next undo_last_action call."
    ),
    tier="I",
    input_schema=UpdateSavedSearchInput,
    output_schema=BaseModel,
    handler=_handler,
    capture_inverse=_capture_inverse,
    inverse_tool="update_saved_search",
    keywords=[
        r"\bedit (?:my )?(?:saved )?search\b",
        r"\bchange (?:my )?(?:saved )?search\b",
        r"\brename (?:my )?(?:saved )?search\b",
        r"\bupdate (?:my )?(?:saved )?search\b",
    ],
    slash_aliases=["/edit-search", "/update-search"],
    confirmation_template=(
        "Updating saved search **{searchId}**."
    ),
))
