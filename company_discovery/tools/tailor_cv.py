"""tailor_cv — re-emphasise the CV for a single imported job's JD.

Tier R (read-only generation): produces a tailored CV variant
without external side-effect. The legacy handler persists the
tailored summary against the imported_job row for later download;
that's treated as a generation artifact rather than a destructive
mutation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class TailorCvInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    importedJobId: str = Field(
        description=(
            "The ID of the imported job to tailor the CV against. "
            "Paste from the Jobs view."
        ),
        min_length=1, max_length=120,
    )


def tailor_cv_handler(
    inp: TailorCvInput, ctx: dict[str, Any]
) -> ToolResult:
    out = ctx["state"].chat_handler_tailor_cv(
        ctx["user_id"], inp.model_dump(exclude_none=True),
    )
    if not out.get("ok", True):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="tailor_cv_failed",
                message=out.get("message", "Could not tailor the CV."),
            ),
        )
    return ToolResult(ok=True, data={k: v for k, v in out.items() if k != "ok"})


register_tool(Tool(
    name="tailor_cv",
    label="Tailor your CV for a specific job",
    description=(
        "Re-emphasise the CV against a single imported job's JD. "
        "Fact-grounded — never invents new experience. Produces a "
        "summary + bullet reorder + download link tailored to that "
        "job's keywords."
    ),
    tier="R",
    input_schema=TailorCvInput,
    output_schema=BaseModel,
    handler=tailor_cv_handler,
    keywords=[
        r"\btailor (?:my )?(?:cv|resume)\b",
        r"\bre[\-_]?write (?:my )?(?:cv|resume)\b",
        r"\bcustomi[sz]e (?:my )?(?:cv|resume)\b",
    ],
    slash_aliases=["/tailor", "/tailor-cv"],
    confirmation_template=(
        "Generating a tailored CV for job **{importedJobId}**."
    ),
))
