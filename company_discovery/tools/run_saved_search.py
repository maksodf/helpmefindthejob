"""run_saved_search — trigger one of the user's saved searches now.

Tier R (read-only): executes the saved query and returns matches.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class RunSavedSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    searchId: str = Field(
        description=(
            "The ID of one of the user's saved searches. List them "
            "from the Saved Searches view in Settings."
        ),
        min_length=1, max_length=120,
    )


def run_saved_search_handler(
    inp: RunSavedSearchInput, ctx: dict[str, Any]
) -> ToolResult:
    out = ctx["state"].chat_handler_run_saved_search(
        ctx["user_id"], inp.model_dump(exclude_none=True),
    )
    if not out.get("ok", True):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="run_saved_search_failed",
                message=out.get("message", "Could not run the search."),
            ),
        )
    return ToolResult(ok=True, data={k: v for k, v in out.items() if k != "ok"})


register_tool(Tool(
    name="run_saved_search",
    label="Run a saved search now",
    description=(
        "Trigger one of the user's existing saved searches "
        "immediately, outside its normal daily schedule. Returns the "
        "match set."
    ),
    tier="R",
    input_schema=RunSavedSearchInput,
    output_schema=BaseModel,
    handler=run_saved_search_handler,
    keywords=[
        r"\brun (?:a |my |the )?(?:saved )?search\b",
        r"\bcheck (?:my )?(?:saved )?search (?:now|today)\b",
    ],
    slash_aliases=["/run-search", "/run"],
    confirmation_template="Running saved search **{searchId}** now.",
))
