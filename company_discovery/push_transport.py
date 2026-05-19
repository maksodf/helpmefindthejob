# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Web Push transport — VAPID-signed payload to the user's push service.

Wraps :mod:`pywebpush` (added in 0.12.0) so the app code is a one-liner
and tests can stub the send path without touching the network.

Why pywebpush:
- Real-world VAPID signing + AES-128-GCM payload encryption is fiddly
  and easy to get wrong. pywebpush ships the protocol implementation
  battle-tested across Mozilla / FCM / Apple endpoints.
- It's the smallest reasonable dep for this; alternatives (rolling our
  own with `cryptography` directly) are 200+ lines of risky code.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .models import PushSubscription


class PushUnavailableError(RuntimeError):
    """VAPID env vars are not set — push is intentionally disabled."""


def _vapid_keys() -> tuple[str, str, str] | None:
    public = os.environ.get("DIRECTJOB_VAPID_PUBLIC_KEY", "").strip()
    private = os.environ.get("DIRECTJOB_VAPID_PRIVATE_KEY", "").strip()
    contact = os.environ.get("DIRECTJOB_VAPID_CONTACT", "mailto:operator@example.com").strip()
    if not public or not private:
        return None
    return public, private, contact


def is_push_configured() -> bool:
    return _vapid_keys() is not None


def vapid_public_key() -> str | None:
    keys = _vapid_keys()
    return keys[0] if keys else None


@dataclass
class PushPayload:
    title: str
    body: str
    url: str | None = None
    icon: str | None = "/icons/icon.svg"

    def to_json(self) -> str:
        return json.dumps(
            {
                k: v
                for k, v in {
                    "title": self.title,
                    "body": self.body,
                    "url": self.url,
                    "icon": self.icon,
                }.items()
                if v is not None
            }
        )


def send_push(subscription: PushSubscription, payload: PushPayload) -> None:
    """Send ``payload`` to the user agent identified by ``subscription``.

    Raises :class:`PushUnavailableError` when VAPID keys aren't set.
    Other failures (404 gone, 410 expired) propagate as ``WebPushException``
    so the caller can decide whether to delete the stale subscription.
    """

    keys = _vapid_keys()
    if keys is None:
        raise PushUnavailableError("vapid_keys_not_configured")
    public, private, contact = keys
    try:
        from pywebpush import webpush  # type: ignore[import-not-found]
    except ImportError as error:  # pragma: no cover - dep guard
        raise PushUnavailableError("pywebpush_not_installed") from error

    sub_dict = {
        "endpoint": subscription.endpoint,
        "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
    }
    webpush(
        subscription_info=sub_dict,
        data=payload.to_json(),
        vapid_private_key=private,
        vapid_claims={"sub": contact},
    )
