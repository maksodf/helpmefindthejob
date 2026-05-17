"""get_billing_status — read the user's subscription + usage.

Tier R. Maps to ``GET /api/billing``. Returns the current plan,
available plans the user could upgrade to, and today's LLM usage vs.
cap.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from company_discovery.tool_registry import (
    Tool, ToolResult, register_tool,
)


class GetBillingStatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _handler(
    inp: GetBillingStatusInput, ctx: dict[str, Any]
) -> ToolResult:
    from company_discovery.billing import plans_payload
    state = ctx["state"]
    user_id = ctx["user_id"]
    eff_uid = state.effective_user_id(user_id)
    cap = state.llm_daily_cap_for_user(eff_uid)
    used = state.llm_tool_use_count_today(eff_uid)
    import sys as _sys
    daily_cap = None if cap >= _sys.maxsize else cap
    sub = state.get_subscription().to_dict()
    plans = plans_payload()
    plan_id = sub.get("planId") or "free"
    cap_blurb = (
        "unlimited" if daily_cap is None
        else f"{used}/{daily_cap}"
    )
    return ToolResult(
        ok=True,
        data={
            "message": (
                f"You're on **{plan_id}**. AI usage today: {cap_blurb}."
            ),
            "subscription": sub,
            "plans": plans,
            "aiUsage": {"today": used, "dailyCap": daily_cap},
        },
    )


register_tool(Tool(
    name="get_billing_status",
    label="Show billing + usage",
    description=(
        "Return the user's current subscription, all available plans "
        "(for upgrade conversations), and today's AI usage vs. cap. "
        "Use when the user asks 'what's my plan', 'am I near my "
        "limit', 'can I upgrade', or similar."
    ),
    tier="R",
    input_schema=GetBillingStatusInput,
    output_schema=BaseModel,
    handler=_handler,
    keywords=[
        r"\b(?:my )?(?:plan|subscription|billing)\b",
        r"\b(?:my )?usage\b",
        r"\bnear (?:my )?limit\b",
        r"\b(?:can i )?upgrade\b",
    ],
    slash_aliases=["/billing", "/plan"],
    confirmation_template="Loading your billing + usage.",
))
