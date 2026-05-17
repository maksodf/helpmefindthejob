"""draft_motivation_letter — draft a DACH-norm motivation letter.

Tier R (read-only generation). Draft a Bewerbungsschreiben in proper
DACH structure (Anrede, 3-paragraph Hauptteil, Schluss) for a job
the user picked in their journey. AI-backed when available;
otherwise a structured template with placeholders + an honest "no AI
configured" banner.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class DraftMotivationLetterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # No parameters — operates on the user's journey state.


def draft_motivation_letter_handler(
    inp: DraftMotivationLetterInput, ctx: dict[str, Any]
) -> ToolResult:
    out = ctx["state"].chat_handler_draft_motivation_letter(
        ctx["user_id"], {},
    )
    if not out.get("ok", True):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="draft_motivation_letter_failed",
                message=out.get("message", "Could not draft the letter."),
            ),
        )
    return ToolResult(ok=True, data={k: v for k, v in out.items() if k != "ok"})


register_tool(Tool(
    name="draft_motivation_letter",
    label="Draft a DACH-norm motivation letter",
    description=(
        "Draft a Bewerbungsschreiben in proper DACH structure "
        "(Anrede, 3-paragraph Hauptteil, Schluss) for a job the user "
        "picked in their journey. Use after the user has picked a "
        "specific job."
    ),
    tier="R",
    input_schema=DraftMotivationLetterInput,
    output_schema=BaseModel,
    handler=draft_motivation_letter_handler,
    keywords=[
        r"\bdraft\b.*\b(?:motivation|cover|application)\b.*\bletter\b",
        r"\bmotivation(?:s)?(?:schreiben)?\b",
        r"\bbewerbungsschreiben\b",
        r"\banschreiben\b",
    ],
    slash_aliases=["/letter", "/draft-letter", "/motivation"],
    confirmation_template=(
        "Drafting a motivation letter for your picked job."
    ),
))
