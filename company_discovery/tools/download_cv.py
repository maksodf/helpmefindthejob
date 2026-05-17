"""download_cv — open the print-styled CV page for browser PDF save.

Tier R (read-only). Returns an ``openUrl`` to the print view; needs
an existing CV on the user's profile.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class DownloadCvInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # No parameters — operates on the user's profile.


def download_cv_handler(
    inp: DownloadCvInput, ctx: dict[str, Any]
) -> ToolResult:
    out = ctx["state"].chat_handler_download_cv(ctx["user_id"], {})
    if not out.get("ok", True):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="download_cv_failed",
                message=out.get(
                    "message",
                    "No CV on file. Ask the user to build one first.",
                ),
            ),
        )
    return ToolResult(ok=True, data={k: v for k, v in out.items() if k != "ok"})


register_tool(Tool(
    name="download_cv",
    label="Download your CV as a PDF",
    description=(
        "Open the print-styled CV page so the user can save it as "
        "PDF from their browser. Needs an existing CV on the "
        "profile."
    ),
    tier="R",
    input_schema=DownloadCvInput,
    output_schema=BaseModel,
    handler=download_cv_handler,
    keywords=[
        r"\bdownload (?:my )?(?:cv|resume|lebenslauf)\b",
        r"\bsave (?:my )?(?:cv|resume|lebenslauf) (?:as )?pdf\b",
        r"\bget (?:my )?(?:cv|resume|lebenslauf) (?:as )?pdf\b",
        r"\b(?:lebenslauf|cv) (?:als )?pdf herunterladen\b",
        r"\b(?:herunterladen|drucken|speichern)\b.*\b(?:lebenslauf|cv)\b",
    ],
    slash_aliases=["/download-cv", "/cv-pdf", "/print-cv"],
    confirmation_template="Opening your CV in print view.",
))
