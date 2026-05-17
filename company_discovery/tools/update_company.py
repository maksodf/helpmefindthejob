"""update_company — edit a watchlist company's metadata.

Tier I (idempotent write): reversible by restoring the previous
field values, captured pre-execution.

Phase 1 Step 7 — closes the CRUD-parity gap. Fields supported:
name, careerPageUrl, notes, sector, watchEnabled (the on/off
toggle that pauses or resumes scanning).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class UpdateCompanyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    companyId: str = Field(
        description="The ID of the company to edit.",
        min_length=1, max_length=120,
    )
    name: str | None = Field(
        default=None,
        description="New display name. Omit to leave unchanged.",
        max_length=160,
    )
    careerPageUrl: str | None = Field(
        default=None,
        description=(
            "New career-page URL. Omit to leave unchanged. Pass an "
            "empty string to clear it (the next scan will try to "
            "rediscover)."
        ),
        max_length=500,
    )
    notes: str | None = Field(
        default=None,
        description="New free-form notes. Omit to leave unchanged.",
        max_length=2000,
    )
    sector: str | None = Field(
        default=None,
        description="New sector label. Omit to leave unchanged.",
        max_length=80,
    )
    watchEnabled: bool | None = Field(
        default=None,
        description=(
            "Set to true to resume scanning, false to pause. "
            "Omit to leave unchanged. Use this to pause monitoring "
            "without losing the company from the watchlist."
        ),
    )


def _capture_inverse(
    inp: "UpdateCompanyInput", ctx: dict[str, Any]
) -> dict[str, Any]:
    state = ctx["state"]
    repo = state.repository
    existing = repo.companies.get(inp.companyId)
    if existing is None or existing.user_id != ctx["user_id"]:
        return {}
    inverse: dict[str, Any] = {"companyId": inp.companyId}
    if inp.name is not None:
        inverse["name"] = existing.name
    if inp.careerPageUrl is not None:
        inverse["careerPageUrl"] = existing.career_page_url or ""
    if inp.notes is not None:
        inverse["notes"] = existing.notes or ""
    if inp.sector is not None:
        inverse["sector"] = existing.sector or ""
    if inp.watchEnabled is not None:
        inverse["watchEnabled"] = bool(existing.watch_enabled)
    return inverse


def _handler(
    inp: UpdateCompanyInput, ctx: dict[str, Any]
) -> ToolResult:
    state = ctx["state"]
    user_id = ctx["user_id"]
    repo = state.repository
    existing = repo.companies.get(inp.companyId)
    if existing is None or existing.user_id != user_id:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="company_not_found",
                message=f"Company {inp.companyId!r} not found.",
            ),
        )
    if inp.name is not None:
        existing.name = inp.name
    if inp.careerPageUrl is not None:
        existing.career_page_url = inp.careerPageUrl or None
    if inp.notes is not None:
        existing.notes = inp.notes or None
    if inp.sector is not None:
        existing.sector = inp.sector or None
    if inp.watchEnabled is not None:
        existing.watch_enabled = bool(inp.watchEnabled)
    existing.updated_at = datetime.now(timezone.utc)
    repo.save_company(existing)
    state.log_analytics(
        user_id, "chat_cmd",
        {"name": "update_company", "id": inp.companyId},
    )
    return ToolResult(
        ok=True,
        data={
            "message": f"Updated **{existing.name}**.",
            "id": existing.id,
            "watchEnabled": existing.watch_enabled,
        },
    )


register_tool(Tool(
    name="update_company",
    label="Edit a watchlist company",
    description=(
        "Edit a company on the watchlist: rename it, update its "
        "career-page URL, change notes or sector, or pause / "
        "resume scanning via watchEnabled. Pass only the fields "
        "you want to change. Use watchEnabled=false to pause "
        "monitoring without removing the company. Reversible via "
        "undo_last_action."
    ),
    tier="I",
    input_schema=UpdateCompanyInput,
    output_schema=BaseModel,
    handler=_handler,
    capture_inverse=_capture_inverse,
    inverse_tool="update_company",
    keywords=[
        r"\bedit (?:a )?(?:company|employer)\b",
        r"\brename (?:a )?(?:company|employer)\b",
        r"\bupdate (?:a )?(?:company|employer)\b",
        r"\bpause (?:scanning|watching|monitoring)\b",
        r"\bresume (?:scanning|watching|monitoring)\b",
    ],
    slash_aliases=["/edit-company", "/update-company"],
    confirmation_template="Updating company **{companyId}**.",
))
