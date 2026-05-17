"""set_persona — switch the user's persona.

Tier I (idempotent write): reversible by setting the previous
persona back.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


# The legacy validator was a string check; the supported list is
# documented in the description but not enforced at validation time.
# Using Literal here would make the LLM's choice strictly typed. The
# personas list is large and the legacy doesn't enforce — keep it as
# a constrained string for now to preserve compatibility. A future
# tightening of the persona enum is a separate change.
PersonaId = str


class SetPersonaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona: PersonaId = Field(
        description=(
            "One of: tech, marketing, data, healthcare-clinical, "
            "legal, finance, sales, design, hr, operations, "
            "education, media, support, product-management, "
            "healthcare-management. Must match the user's preferred "
            "spelling — see the persona library for the canonical "
            "list."
        ),
        min_length=1, max_length=60,
    )


def _set_persona_capture_inverse(
    inp: "SetPersonaInput", ctx: dict[str, Any]
) -> dict[str, Any]:
    """Capture the user's current persona BEFORE we switch it so
    ``undo_last_action`` can restore it. Reads the profile directly
    via the AppState in the context dict."""
    profile = ctx["state"].profile_for(ctx["user_id"])
    return {"persona": getattr(profile, "persona_id", "") or "tech"}


def set_persona_handler(
    inp: SetPersonaInput, ctx: dict[str, Any]
) -> ToolResult:
    out = ctx["state"].chat_handler_set_persona(
        ctx["user_id"], inp.model_dump(exclude_none=True),
    )
    if not out.get("ok", True):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="set_persona_failed",
                message=out.get("message", "Could not set the persona."),
            ),
        )
    return ToolResult(ok=True, data={k: v for k, v in out.items() if k != "ok"})


register_tool(Tool(
    name="set_persona",
    label="Set your persona",
    description=(
        "Switch the user's persona, which biases job ranking, "
        "filtering, and language used in chat. Pick the persona that "
        "matches the user's current role family."
    ),
    tier="I",
    input_schema=SetPersonaInput,
    output_schema=BaseModel,
    handler=set_persona_handler,
    capture_inverse=_set_persona_capture_inverse,
    inverse_tool="set_persona",
    keywords=[
        r"\b(?:set|change|switch) (?:my )?persona\b",
        r"\bi (?:work|am) (?:in|as|a)\b.*\b(tech|marketing|data|legal|sales|design)\b",
    ],
    slash_aliases=["/persona", "/set-persona"],
    confirmation_template="Switching persona to **{persona}**. Confirm?",
))
