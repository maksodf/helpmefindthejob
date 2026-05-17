"""open_cv_builder — open the CV Builder canvas view.

Tier R (read-only): emits a ``navigateTo`` for the frontend; no DB
writes.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class OpenCvBuilderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # No parameters.


def open_cv_builder_handler(
    inp: OpenCvBuilderInput, ctx: dict[str, Any]
) -> ToolResult:
    out = ctx["state"].chat_handler_open_cv_builder(ctx["user_id"], {})
    if not out.get("ok", True):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="open_cv_builder_failed",
                message=out.get("message", "Could not open the CV builder."),
            ),
        )
    return ToolResult(ok=True, data={k: v for k, v in out.items() if k != "ok"})


register_tool(Tool(
    name="open_cv_builder",
    label="Open the CV Builder",
    description=(
        "Open the guided CV Builder canvas so the user can walk "
        "through DACH-style CV sections (header, summary, "
        "experience, education, skills) with photo + PDF export. "
        "The AI formats; it never invents content."
    ),
    tier="R",
    input_schema=OpenCvBuilderInput,
    output_schema=BaseModel,
    handler=open_cv_builder_handler,
    keywords=[
        r"\b(?:create|generate|build|make|write|start) (?:a |my |me )?(?:new )?(?:cv|resume|lebenslauf)\b",
        r"\bi need (?:you )?(?:to )?(?:generate|create|build|make|write)\b.*\b(?:cv|resume|lebenslauf)\b",
        r"\bhelp (?:me )?(?:write|build|create) (?:my )?(?:cv|resume)\b",
        r"\b(?:open|go to|show me) (?:the )?cv builder\b",
    ],
    slash_aliases=["/cv", "/build-cv", "/create-cv"],
    confirmation_template="Opening the CV Builder for you.",
))
