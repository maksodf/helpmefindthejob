# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Slack-webhook outbound notifier for high-fit discovered jobs.

The user pastes an Incoming Webhook URL into Settings → Notifications.
We POST a small JSON payload when a discovered job's ``auto_fit_score``
crosses their threshold. Stdlib only — no slack-sdk dependency.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

LOG = logging.getLogger(__name__)


def _looks_like_slack_webhook(url: str) -> bool:
    if not url:
        return False
    return url.startswith("https://hooks.slack.com/") or url.startswith("https://hooks.")


def post_high_fit_notification(
    *,
    webhook_url: str,
    job_title: str,
    company_name: str,
    location: str | None,
    fit_score: float,
    fit_reason: str | None,
    job_url: str | None,
    public_url: str | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """POST a compact Slack message. Returns ``{"status": ..., "code": ...}``.

    Never raises — the caller (an endpoint handler) shouldn't break a
    user-facing action because Slack is down."""

    if not _looks_like_slack_webhook(webhook_url):
        return {"status": "skipped", "reason": "invalid_webhook_url"}
    fit_pct = int(round(fit_score * 100))
    title_line = f"*{job_title}*" if job_title else "*A new role*"
    company_line = f" at *{company_name}*" if company_name else ""
    location_line = f" — {location}" if location else ""
    reason = (fit_reason or "").strip()
    reason_block = f"\n> {reason}" if reason else ""
    link_block = f"\n<{job_url}|View job>" if job_url else ""
    cta_block = f"\n<{public_url}|Open DirectJob Scout>" if public_url else ""
    text = (
        f":briefcase: *{fit_pct}% fit* — {title_line}{company_line}{location_line}"
        f"{reason_block}{link_block}{cta_block}"
    )
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"status": "ok", "code": resp.status}
    except urllib.error.HTTPError as error:
        LOG.warning("slack_notify HTTP %s: %s", error.code, error.reason)
        return {"status": "error", "code": error.code, "reason": error.reason}
    except urllib.error.URLError as error:
        LOG.warning("slack_notify URLError: %s", error.reason)
        return {"status": "error", "reason": str(error.reason)}
    except Exception as error:  # noqa: BLE001 — last-resort safety net
        LOG.warning("slack_notify exception: %s", error)
        return {"status": "error", "reason": str(error)}
