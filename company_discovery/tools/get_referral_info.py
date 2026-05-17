"""get_referral_info — return the user's referral code, link, and
how many sign-ups they've referred.

Tier R (read-only). Idempotent — calling ``ensure_referral_code``
on AuthStore returns the existing code if one exists, generates a
fresh one otherwise.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class GetReferralInfoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _handler(
    inp: GetReferralInfoInput, ctx: dict[str, Any]
) -> ToolResult:
    state = ctx["state"]
    user_id = ctx["user_id"]
    # The auth store key the route uses is the SESSION user id, not
    # the data user id. STATE wraps the effective id; profile_for
    # used elsewhere takes the data id. For referral, the original
    # session id is what the auth-store keyed code lookups expect.
    try:
        code = state.auth_store.ensure_referral_code(user_id)
        count = state.auth_store.count_referrals(user_id)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            ok=False,
            error=ToolError(
                code="referral_lookup_failed",
                message=f"Could not load referral info: {exc}",
                retryable=True,
            ),
        )
    url = state.public_url_for(f"/r/{code}")
    return ToolResult(
        ok=True,
        data={
            "message": (
                f"Your referral code is **{code}**. Share "
                f"{url} — you've referred {count} so far."
            ),
            "code": code,
            "url": url,
            "referredCount": count,
        },
    )


register_tool(Tool(
    name="get_referral_info",
    label="Show your referral code and stats",
    description=(
        "Return the user's referral code, the shareable URL, and "
        "the number of accounts that signed up via their code. "
        "Use when the user asks 'what's my referral code' / 'how "
        "many people have I referred' / 'share my link'."
    ),
    tier="R",
    input_schema=GetReferralInfoInput,
    output_schema=BaseModel,
    handler=_handler,
    keywords=[
        r"\b(?:my )?referral (?:code|link|url)\b",
        r"\binvite (?:friends|others)\b",
        r"\bshare (?:my )?(?:link|invite)\b",
    ],
    slash_aliases=["/referral", "/invite"],
    confirmation_template="Showing your referral info.",
))
