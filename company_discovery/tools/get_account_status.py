"""get_account_status — composite read of the user's account state.

Tier R (read-only). Returns email-verification state, 2FA state,
plan, daily LLM usage vs. cap, account-deletion state, and account
age. Useful when the user asks 'what's my plan' / 'is my email
verified' / 'do I have 2FA' / 'when did I sign up'.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class GetAccountStatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _handler(
    inp: GetAccountStatusInput, ctx: dict[str, Any]
) -> ToolResult:
    state = ctx["state"]
    user_id = ctx["user_id"]
    try:
        user = state.auth_store.get_user(user_id)
    except KeyError:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="user_not_found",
                message="Account record not available.",
            ),
        )

    email_verified = bool(state.auth_store.is_email_verified(user_id))
    totp_enabled = bool(state.auth_store.has_totp_enabled(user_id))
    deletion = state.get_account_deletion_state(user) or {}

    eff_uid = state.effective_user_id(user_id)
    cap = state.llm_daily_cap_for_user(eff_uid)
    used = state.llm_tool_use_count_today(eff_uid)
    import sys as _sys
    daily_cap = None if cap >= _sys.maxsize else cap

    sub = state.get_subscription()
    plan_id = getattr(sub, "plan_id", "free")

    summary = (
        f"**Plan:** {plan_id} · "
        f"**Email verified:** {'yes' if email_verified else 'no'} · "
        f"**2FA:** {'on' if totp_enabled else 'off'} · "
        f"**LLM today:** {used}"
        f"{'/' + str(daily_cap) if daily_cap is not None else ''}"
    )
    return ToolResult(
        ok=True,
        data={
            "message": summary,
            "email": user.email,
            "plan": plan_id,
            "emailVerified": email_verified,
            "twoFactorEnabled": totp_enabled,
            "deletionRequested": bool(deletion.get("deletionRequestedAt")),
            "deletion": deletion,
            "llmUsage": {"today": used, "dailyCap": daily_cap},
            "memberSince": (user.created_at.isoformat()
                              if user.created_at else None),
        },
    )


register_tool(Tool(
    name="get_account_status",
    label="Show account status",
    description=(
        "Return a snapshot of the user's account: plan, email "
        "verification, 2FA state, today's LLM usage vs. cap, and "
        "account-deletion state. Use when the user asks about their "
        "plan, verification, 2FA, or daily usage."
    ),
    tier="R",
    input_schema=GetAccountStatusInput,
    output_schema=BaseModel,
    handler=_handler,
    keywords=[
        r"\b(?:my )?account (?:status|state|info)\b",
        r"\b(?:my )?plan\b",
        r"\bam i verified\b",
        r"\b(?:do i have )?2fa\b",
    ],
    slash_aliases=["/account", "/account-status"],
    confirmation_template="Loading your account status.",
))
