"""set_slack_webhook — save (or clear) the user's Slack webhook URL.

Tier I. Inverse restores the previous URL (or empty if it was unset).
Pair with ``test_slack_webhook`` to verify after save.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from company_discovery.tool_registry import (
    Tool, ToolError, ToolResult, register_tool,
)


class SetSlackWebhookInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    webhookUrl: str = Field(
        description=(
            "The Slack incoming-webhook URL "
            "(``https://hooks.slack.com/services/...``). Pass an "
            "empty string to clear the saved webhook."
        ),
        max_length=500,
    )


def _capture_inverse(
    inp: "SetSlackWebhookInput", ctx: dict[str, Any]
) -> dict[str, Any]:
    profile = ctx["state"].profile_for(ctx["user_id"])
    return {"webhookUrl": getattr(profile, "slack_webhook_url", "") or ""}


def _handler(
    inp: SetSlackWebhookInput, ctx: dict[str, Any]
) -> ToolResult:
    state = ctx["state"]
    user_id = ctx["user_id"]
    url = (inp.webhookUrl or "").strip()
    # Light validation: non-empty must look like a Slack hook URL.
    if url and not url.startswith("https://hooks.slack.com/"):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="bad_webhook_url",
                message=(
                    "Slack webhook URLs start with "
                    "'https://hooks.slack.com/'. Ask the user to "
                    "paste a fresh one from the Slack app."
                ),
            ),
        )
    state.update_profile(user_id, {"slackWebhookUrl": url})
    state.log_analytics(
        user_id, "chat_cmd",
        {"name": "set_slack_webhook", "cleared": url == ""},
    )
    msg = (
        "Cleared your Slack webhook." if not url
        else "Saved your Slack webhook. Run test_slack_webhook to verify."
    )
    return ToolResult(ok=True, data={"message": msg, "cleared": url == ""})


register_tool(Tool(
    name="set_slack_webhook",
    label="Save your Slack webhook URL",
    description=(
        "Save (or clear) the user's Slack incoming-webhook URL so "
        "high-fit job matches can post to their channel. Pass an "
        "empty string to clear. Use ``test_slack_webhook`` after "
        "save to verify the URL works."
    ),
    tier="I",
    input_schema=SetSlackWebhookInput,
    output_schema=BaseModel,
    handler=_handler,
    capture_inverse=_capture_inverse,
    inverse_tool="set_slack_webhook",
    keywords=[
        r"\b(?:set|save|update) (?:my )?slack (?:webhook|hook)\b",
        r"\bclear (?:my )?slack (?:webhook|hook)\b",
    ],
    slash_aliases=["/slack", "/set-slack"],
    confirmation_template="Saving Slack webhook URL.",
))
