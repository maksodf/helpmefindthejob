"""delete_company — remove a company from the user's watchlist.

Tier N (non-idempotent write): the legacy handler description states
"Irreversible — the watchlist row is gone after confirm." External
visibility is zero (only the user's watchlist), but reversibility is
zero (no soft-delete). This is the textbook case for Tier N's
preview/confirm/commit pattern when Step 4 wires it up. Today it
still flows through the legacy ``_DESTRUCTIVE_COMMANDS`` gate, which
already requires user confirmation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class DeleteCompanyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    companyId: str = Field(
        description=(
            "The ID of the company to remove. Paste from the "
            "Companies view."
        ),
        min_length=1, max_length=120,
    )


def delete_company_handler(
    inp: DeleteCompanyInput, ctx: dict[str, Any]
) -> ToolResult:
    out = ctx["state"].chat_handler_delete_company(
        ctx["user_id"], inp.model_dump(exclude_none=True),
    )
    if not out.get("ok", True):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="delete_company_failed",
                message=out.get("message", "Could not remove the company."),
            ),
        )
    return ToolResult(ok=True, data={k: v for k, v in out.items() if k != "ok"})


register_tool(Tool(
    name="delete_company",
    label="Remove a company from your watchlist",
    description=(
        "Stop watching a company. Irreversible — the watchlist row "
        "is removed after confirm. Use only when the user "
        "explicitly asks to remove or stop watching a specific "
        "company."
    ),
    tier="N",
    input_schema=DeleteCompanyInput,
    output_schema=BaseModel,
    handler=delete_company_handler,
    keywords=[
        r"\bremove (?:a )?(?:company|employer)\b",
        r"\bunwatch\b",
        r"\bstop watching\b",
        r"\bdelete (?:a )?(?:company|employer)\b",
    ],
    slash_aliases=["/delete-company", "/unwatch", "/remove-company"],
    confirmation_template=(
        "**Removing** company **{companyId}** from your watchlist. "
        "This is irreversible. Confirm?"
    ),
))
