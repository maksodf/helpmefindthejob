"""add_company — add a company to the user's watchlist.

Tier I (idempotent write): reversible via ``delete_company``. Today
this still goes through the legacy confirmation gate (it appears in
``_DESTRUCTIVE_COMMANDS``); the tier annotation is correct for the
portfolio policy and will be honoured when Step 4 (CRUD-parity
enforcement) wires up undo-by-reversal-token instead of pre-confirm.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class AddCompanyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="The company's full name (e.g. 'Charité Berlin').",
        min_length=1, max_length=160,
    )
    websiteUrl: str = Field(
        description="The company's primary website URL.",
        min_length=4, max_length=500,
    )
    careerPageUrl: str | None = Field(
        default=None,
        description=(
            "Optional career-page URL. Omit if you don't know it — "
            "we'll try to discover it on the first scan."
        ),
        max_length=500,
    )


def _add_company_capture_inverse_after(
    inp: "AddCompanyInput", ctx: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    """Capture the new company's ID AFTER the handler creates it.
    The legacy handler returns it as ``id`` in the result data dict.
    The inverse tool ``delete_company`` removes the row by ID.
    """
    company_id = result.get("id") or result.get("companyId")
    if not company_id:
        return {}
    return {"companyId": company_id}


def add_company_handler(
    inp: AddCompanyInput, ctx: dict[str, Any]
) -> ToolResult:
    out = ctx["state"].chat_handler_add_company(
        ctx["user_id"], inp.model_dump(exclude_none=True),
    )
    if not out.get("ok", True):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="add_company_failed",
                message=out.get("message", "Could not add the company."),
            ),
        )
    return ToolResult(ok=True, data={k: v for k, v in out.items() if k != "ok"})


register_tool(Tool(
    name="add_company",
    label="Add a company to your watchlist",
    description=(
        "Watch a company's career page for new openings. Adds the "
        "company to the user's watchlist; future automated scans will "
        "surface new postings in the user's Companies view."
    ),
    tier="I",
    input_schema=AddCompanyInput,
    output_schema=BaseModel,
    handler=add_company_handler,
    capture_inverse_after=_add_company_capture_inverse_after,
    inverse_tool="delete_company",
    keywords=[
        r"\badd (?:a )?company\b",
        r"\bwatch\b.*\bcompany\b",
        r"\bfollow\b.*\bcompany\b",
    ],
    slash_aliases=["/add-company", "/add", "/watch"],
    confirmation_template=(
        "I'll add **{name}** ({websiteUrl}) to your watchlist. Confirm?"
    ),
))
