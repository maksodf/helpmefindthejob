"""test_slack_webhook — fire a test notification to the user's Slack
webhook.

Tier R (read-only in our model — no DB writes; one outbound HTTP call
to Slack with a sample notification body). Maps to the existing
``POST /api/profile/slack-test`` route.

Useful when the user wants to confirm their webhook is configured
correctly without waiting for a real high-fit match to surface.
"""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, ConfigDict

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class TestSlackWebhookInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # No parameters — uses the webhook URL stored on the profile.


def _handler(
    inp: TestSlackWebhookInput, ctx: dict[str, Any]
) -> ToolResult:
    state = ctx["state"]
    user_id = ctx["user_id"]
    profile = state.profile_for(user_id)
    url = (getattr(profile, "slack_webhook_url", "") or "").strip()
    if not url:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="no_webhook",
                message=(
                    "No Slack webhook URL is set on this user's "
                    "profile. Ask them to paste one in Settings → "
                    "Slack first."
                ),
                user_hint=(
                    "Tell the user they need to add their Slack "
                    "webhook URL in Settings before this can run."
                ),
            ),
        )
    from company_discovery.slack_notify import post_high_fit_notification
    public_url = (
        os.environ.get("DIRECTJOB_PUBLIC_URL")
        or "https://app.khalo.org"
    )
    result = post_high_fit_notification(
        webhook_url=url,
        job_title="Test notification",
        company_name="DirectJob Scout",
        location=None,
        fit_score=0.95,
        fit_reason="This is a test from the chat.",
        job_url=None,
        public_url=public_url,
    )
    state.log_analytics(
        user_id, "slack_test", {"status": result.get("status")},
    )
    if (result.get("status") or "") != "ok":
        return ToolResult(
            ok=False,
            error=ToolError(
                code="slack_post_failed",
                message=(
                    "Slack rejected the test webhook: "
                    f"{result.get('error') or result.get('status')!r}"
                ),
                retryable=True,
            ),
        )
    return ToolResult(
        ok=True,
        data={
            "message": (
                "Test notification sent. Check your Slack channel."
            ),
            "status": result.get("status"),
        },
    )


register_tool(Tool(
    name="test_slack_webhook",
    label="Test the Slack webhook",
    description=(
        "Send a test high-fit notification to the user's configured "
        "Slack webhook so they can confirm it works without waiting "
        "for a real match. Requires a webhook URL already saved on "
        "the user's profile."
    ),
    tier="R",
    input_schema=TestSlackWebhookInput,
    output_schema=BaseModel,
    handler=_handler,
    keywords=[
        r"\btest (?:my |the )?slack (?:webhook|integration|notif)\b",
        r"\bslack test\b",
    ],
    slash_aliases=["/test-slack", "/slack-test"],
    confirmation_template="Sending a test notification to Slack.",
))
