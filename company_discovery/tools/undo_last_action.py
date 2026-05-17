"""undo_last_action — consume the user's most recent Tier I reversal
token and dispatch the inverse action.

Tier R (read-only meta-tool). Doesn't produce its own reversal token
— "redo" isn't a first-class operation here. If the user wants to
re-do the original action, they can re-issue it as a fresh tool
call.

Per the portfolio CRUD-parity policy: every successful Tier I tool
captures its inverse before executing and writes a reversal token.
This tool is the consumer end of that pipeline.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool, try_dispatch,
)


class UndoLastActionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # No parameters — operates on the user's most recent unconsumed
    # token. Future enhancement: accept an optional reversalToken to
    # undo a specific older action.


def undo_last_action_handler(
    inp: UndoLastActionInput, ctx: dict[str, Any]
) -> ToolResult:
    store = ctx.get("tool_actions_store")
    user_id = ctx.get("user_id", "")
    if store is None or not user_id:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="undo_unavailable",
                message="Undo storage is not configured.",
            ),
        )

    latest = store.latest_unconsumed(user_id)
    if latest is None:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="nothing_to_undo",
                message=(
                    "No recent action to undo. Reversal tokens "
                    "expire after a short window."
                ),
                user_hint=(
                    "Tell the user there is nothing to undo right "
                    "now."
                ),
            ),
        )

    # Atomic consume — protects against concurrent undo attempts.
    consumed = store.consume(token=latest["token"], user_id=user_id)
    if consumed is None:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="undo_race",
                message=(
                    "Undo lost a race; the action may already have "
                    "been undone."
                ),
                retryable=False,
            ),
        )

    # Bug fix — clear the user's idempotency cache before
    # dispatching the inverse. Otherwise a repeat of the ORIGINAL
    # action within the 60s cache window would return the stale
    # cached result (including the now-consumed reversalToken)
    # without re-running the handler, leaving the actual state
    # out of sync with what the chat claims happened.
    try:
        store.invalidate_user_idempotency(
            user_id=user_id, tool_name=consumed["tool_name"],
        )
        # Also invalidate the inverse tool's cache — undo dispatch
        # below counts as a fresh execution that should not be
        # served from cache either.
        store.invalidate_user_idempotency(
            user_id=user_id, tool_name=consumed["inverse_tool"],
        )
    except Exception:  # noqa: BLE001
        pass

    inverse_result = try_dispatch(
        consumed["inverse_tool"], consumed["inverse_args"], ctx,
    )
    if inverse_result is None:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="inverse_unknown",
                message=(
                    f"Inverse tool '{consumed['inverse_tool']}' is "
                    "not registered."
                ),
            ),
        )
    if not inverse_result.get("ok"):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="inverse_failed",
                message=inverse_result.get(
                    "message", "The inverse action failed.",
                ),
            ),
        )
    return ToolResult(
        ok=True,
        data={
            "message": (
                f"Undone — restored the state before your last "
                f"{consumed['tool_name']} action."
            ),
            "undoneTool": consumed["tool_name"],
            "inverseTool": consumed["inverse_tool"],
        },
    )


register_tool(Tool(
    name="undo_last_action",
    label="Undo the last action",
    description=(
        "Reverse the user's most recent reversible action (Tier I). "
        "Use when the user says 'undo', 'revert', 'cancel that', or "
        "asks to take back something they just did. Idempotent in "
        "the sense that calling it twice on the same action is a "
        "no-op — the second call finds nothing to undo."
    ),
    tier="R",
    input_schema=UndoLastActionInput,
    output_schema=BaseModel,
    handler=undo_last_action_handler,
    keywords=[
        r"\bundo\b",
        r"\brevert\b",
        r"\bcancel that\b",
        r"\btake (?:that |it )?back\b",
        r"\brückgängig\b",
    ],
    slash_aliases=["/undo", "/revert"],
    confirmation_template="Undoing your last action.",
))
