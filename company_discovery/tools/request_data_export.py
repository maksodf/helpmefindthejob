"""request_data_export — GDPR right-to-portability data export.

Tier R. Returns the JSON blob ``STATE.export_data(user_id)``
produces — same payload as the existing ``GET /api/data/export``
HTTP endpoint. No side effects; the user (or the LLM on their
behalf) is expected to download / save the result.

For UX, the chat surface should treat the result as
"here's your export — save the JSON below" rather than spilling
the full blob into a chat bubble. The handler still returns it;
formatting is the chat dock's concern.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class RequestDataExportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _handler(
    inp: RequestDataExportInput, ctx: dict[str, Any]
) -> ToolResult:
    state = ctx["state"]
    user_id = ctx["user_id"]
    try:
        payload = state.export_data(user_id)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            ok=False,
            error=ToolError(
                code="export_failed",
                message=f"Could not produce export: {exc}",
                retryable=True,
            ),
        )
    state.log_analytics(
        user_id, "chat_cmd", {"name": "request_data_export"},
    )
    # Light summary so the LLM has counts to mention without
    # spilling the whole payload into chat history.
    summary_counts = {
        k: (len(v) if isinstance(v, (list, dict)) else 1)
        for k, v in (payload.items() if isinstance(payload, dict) else [])
    }
    return ToolResult(
        ok=True,
        data={
            "message": (
                "Generated your data export "
                f"({sum(summary_counts.values())} top-level entries). "
                "Use the download link the chat surface attaches."
            ),
            "exportSummary": summary_counts,
            "openUrl": "/api/data/export",
        },
    )


register_tool(Tool(
    name="request_data_export",
    label="Export your data (GDPR portability)",
    description=(
        "Generate the user's full data export — companies, jobs, "
        "saved searches, profile, applications, chat history, etc. "
        "Returns a summary + an openUrl the chat surface attaches "
        "as a download link. Read-only; the user retains all data "
        "in the app afterwards. Use when the user asks to download "
        "their data or invokes GDPR data portability rights."
    ),
    tier="R",
    input_schema=RequestDataExportInput,
    output_schema=BaseModel,
    handler=_handler,
    keywords=[
        r"\bexport (?:my )?data\b",
        r"\bdownload (?:my )?data\b",
        r"\b(?:gdpr|dsgvo) (?:data )?(?:portability|export)\b",
    ],
    slash_aliases=["/export", "/export-data"],
    confirmation_template="Generating your data export.",
))
