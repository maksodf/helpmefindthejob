"""delete_account — start the GDPR right-to-erasure flow.

Tier N (non-idempotent write with external side-effect). The legacy
handler emails the user a confirmation link, then a 7-day grace
window begins before any data is erased. The grace window is the
user's safety net; the tier annotation is N because the email is
sent immediately (irreversible external side-effect).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class DeleteAccountInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(
        description=(
            "The user's account email, typed exactly as they signed "
            "up. Used as a confirmation step before the deletion "
            "email is sent."
        ),
    )


def delete_account_handler(
    inp: DeleteAccountInput, ctx: dict[str, Any]
) -> ToolResult:
    out = ctx["state"].chat_handler_delete_account(
        ctx["user_id"], inp.model_dump(),
    )
    if not out.get("ok", True):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="delete_account_failed",
                message=out.get(
                    "message", "Could not start account deletion."
                ),
            ),
        )
    return ToolResult(ok=True, data={k: v for k, v in out.items() if k != "ok"})


register_tool(Tool(
    name="delete_account",
    label="Delete your account (GDPR right-to-erasure)",
    description=(
        "Start the account-deletion flow. Triggers a confirmation "
        "email; after the user clicks the link, a 7-day grace "
        "window begins before any data is erased. The user can "
        "cancel from Settings during the grace window. Use only "
        "when the user explicitly asks to delete their account."
    ),
    tier="N",
    input_schema=DeleteAccountInput,
    output_schema=BaseModel,
    handler=delete_account_handler,
    keywords=[
        r"\bdelete (?:my )?account\b",
        r"\berase (?:my )?account\b",
        r"\bclose (?:my )?account\b",
        r"\bkonto (?:löschen|loeschen)\b",
        r"\b(?:löschen|loeschen) (?:mein|meines)? konto\b",
        r"\bgdpr\b.*(?:delete|erase|right to erasure)",
        r"\bdsgvo\b.*(?:löschen|loeschen|löschung|loeschung)",
    ],
    slash_aliases=["/delete-account", "/delete-my-account", "/erase-account"],
    confirmation_template=(
        "I'll start deletion for **{email}** — you'll get a "
        "confirmation email with a link. Clicking the link starts "
        "a 7-day grace window before any data is erased. Confirm?"
    ),
))
