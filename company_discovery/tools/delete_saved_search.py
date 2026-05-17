"""delete_saved_search — remove a saved search.

Tier N (non-idempotent). Deletion is irreversible in the data
layer; the user's safety net is the legacy ``requires_confirmation``
pre-confirm gate (already enforced because ``delete_saved_search``
will be added to ``_DESTRUCTIVE_COMMANDS`` for backwards-compat
with the keyword router until Step 4b flips Tier N tools to the
pending_actions preview/commit flow).

Phase 1 Step 7 — closes the CRUD-parity gap. ``add_company`` and
``create_saved_search`` can now pair their inverse with the
corresponding delete via ``capture_inverse_after``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class DeleteSavedSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    searchId: str = Field(
        description=(
            "The ID of the saved search to delete. The user should "
            "confirm; deletion is irreversible."
        ),
        min_length=1, max_length=120,
    )


def _handler(
    inp: DeleteSavedSearchInput, ctx: dict[str, Any]
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
                message=f"Saved search {inp.searchId!r} not found.",
            ),
        )
    name = existing.name
    repo.delete_saved_search(user_id, inp.searchId)
    state.log_analytics(
        user_id, "chat_cmd",
        {"name": "delete_saved_search", "id": inp.searchId},
    )
    return ToolResult(
        ok=True,
        data={
            "message": f"Deleted saved search **{name}**.",
            "id": inp.searchId,
        },
    )


register_tool(Tool(
    name="delete_saved_search",
    label="Delete a saved search",
    description=(
        "Permanently delete a saved search. Irreversible — the "
        "search row is gone after this call. Use only when the "
        "user explicitly asks to delete a specific saved search; "
        "always confirm first."
    ),
    tier="N",
    input_schema=DeleteSavedSearchInput,
    output_schema=BaseModel,
    handler=_handler,
    keywords=[
        r"\bdelete (?:my )?(?:saved )?search\b",
        r"\bremove (?:my )?(?:saved )?search\b",
        r"\bunsave (?:my )?(?:saved )?search\b",
    ],
    slash_aliases=["/delete-search", "/remove-search"],
    confirmation_template=(
        "**Deleting** saved search **{searchId}**. This is "
        "irreversible. Confirm?"
    ),
))
