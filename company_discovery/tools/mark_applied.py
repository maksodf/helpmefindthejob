"""mark_applied — update application status on an imported job.

Tier I (idempotent write): reversible by re-setting the previous
status. Status is constrained to a fixed enum via ``Literal`` so the
LLM cannot emit an invalid value (the legacy ``_validate_application_status``
callable is replaced by Pydantic's type system).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


ApplicationStatus = Literal[
    "saved", "interested", "applied", "interview", "rejected", "archived",
]


class MarkAppliedInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    importedJobId: str = Field(
        description=(
            "The ID of an imported job in the user's queue. Paste it "
            "from the Jobs view."
        ),
        min_length=1, max_length=120,
    )
    status: ApplicationStatus = Field(
        description=(
            "New status. Must be one of: saved, interested, applied, "
            "interview, rejected, archived."
        ),
    )
    replied: bool | None = Field(
        default=None,
        description=(
            "Whether the company has replied. Omit if unknown."
        ),
    )


def _mark_applied_capture_inverse(
    inp: "MarkAppliedInput", ctx: dict[str, Any]
) -> dict[str, Any]:
    """Look up the imported job and capture its current status (and
    replied flag) so ``undo_last_action`` can restore them.

    The legacy ``chat_handler_mark_applied`` uses the in-memory dict
    ``repository.imported_jobs.get(...)`` directly and verifies
    ``user_id`` matches. We follow the same pattern here — there is
    no dedicated ``find_imported_job`` method on the repository.

    If the job can't be found, return a no-op inverse rather than
    raising; the registry layer treats a missing match as "no undo
    available."
    """
    state = ctx["state"]
    user_id = ctx["user_id"]
    job = state.repository.imported_jobs.get(inp.importedJobId)
    if job is None or getattr(job, "user_id", None) != user_id:
        return {
            "importedJobId": inp.importedJobId,
            "status": inp.status,
        }
    prev_status = getattr(job, "application_status", None) or "saved"
    inverse: dict[str, Any] = {
        "importedJobId": inp.importedJobId,
        "status": prev_status,
    }
    # Capture the replied flag only if it was previously set; if
    # unknown leave it absent (the handler treats it as no-op).
    if getattr(job, "replied_at", None) is not None:
        inverse["replied"] = True
    return inverse


def mark_applied_handler(
    inp: MarkAppliedInput, ctx: dict[str, Any]
) -> ToolResult:
    out = ctx["state"].chat_handler_mark_applied(
        ctx["user_id"], inp.model_dump(exclude_none=True),
    )
    if not out.get("ok", True):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="mark_applied_failed",
                message=out.get("message", "Could not update the job."),
            ),
        )
    return ToolResult(ok=True, data={k: v for k, v in out.items() if k != "ok"})


register_tool(Tool(
    name="mark_applied",
    label="Mark an application status",
    description=(
        "Update applicationStatus and/or replied on an imported job. "
        "Use this whenever the user reports they applied, got a "
        "reply, archived a posting, or moved an opportunity to "
        "interview / rejected."
    ),
    tier="I",
    input_schema=MarkAppliedInput,
    output_schema=BaseModel,
    handler=mark_applied_handler,
    capture_inverse=_mark_applied_capture_inverse,
    inverse_tool="mark_applied",
    keywords=[
        r"\bmark (?:as )?applied\b",
        r"\bset (?:application )?status\b",
        r"\bthey replied\b",
        r"\bgot a reply\b",
    ],
    slash_aliases=["/applied", "/mark"],
    confirmation_template=(
        "Marking job **{importedJobId}** as **{status}** "
        "(replied={replied}). Confirm?"
    ),
))
