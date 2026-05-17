# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Round-7 tests: items 13–17 closeout."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.billing import (
    Subscription,
    apply_stripe_event,
    verify_stripe_webhook_signature,
)


class StripeWebhookSignatureTests(unittest.TestCase):
    def _sign(self, payload: bytes, secret: str, ts: int | None = None) -> str:
        ts = ts if ts is not None else int(time.time())
        signed = f"{ts}.".encode() + payload
        sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        return f"t={ts},v1={sig}"

    def test_valid_signature(self) -> None:
        payload = b'{"id":"evt_123","type":"checkout.session.completed"}'
        secret = "whsec_test"
        header = self._sign(payload, secret)
        self.assertTrue(verify_stripe_webhook_signature(payload, header, secret))

    def test_tampered_payload_rejected(self) -> None:
        secret = "whsec_test"
        header = self._sign(b"original", secret)
        self.assertFalse(verify_stripe_webhook_signature(b"different", header, secret))

    def test_wrong_secret_rejected(self) -> None:
        payload = b"{}"
        header = self._sign(payload, "whsec_real")
        self.assertFalse(verify_stripe_webhook_signature(payload, header, "whsec_attacker"))

    def test_replay_outside_tolerance_rejected(self) -> None:
        payload = b"{}"
        secret = "whsec_test"
        header = self._sign(payload, secret, ts=int(time.time()) - 600)
        self.assertFalse(verify_stripe_webhook_signature(payload, header, secret, tolerance_seconds=300))


class StripeEventApplyTests(unittest.TestCase):
    def test_checkout_session_completed_activates(self) -> None:
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer_email": "buyer@example.com",
                    "line_items": [{"price": {"id": "price_team_xyz"}}],
                }
            },
        }
        current = Subscription(plan_id="pilot", status="pending")
        next_state = apply_stripe_event(event, current, plan_resolver=lambda p: "team" if "team" in p else "")
        self.assertEqual(next_state.status, "active")
        self.assertEqual(next_state.plan_id, "team")
        self.assertEqual(next_state.customer_email, "buyer@example.com")
        self.assertEqual(next_state.last_event, "checkout.session.completed")

    def test_subscription_deleted_cancels(self) -> None:
        event = {"type": "customer.subscription.deleted", "data": {"object": {"id": "sub_x"}}}
        current = Subscription(plan_id="team", status="active")
        next_state = apply_stripe_event(event, current)
        self.assertEqual(next_state.status, "cancelled")
        self.assertIsNotNone(next_state.cancelled_at)

    def test_invoice_payment_failed_marks_past_due(self) -> None:
        event = {"type": "invoice.payment_failed", "data": {"object": {"id": "in_x"}}}
        current = Subscription(plan_id="team", status="active")
        next_state = apply_stripe_event(event, current)
        self.assertEqual(next_state.status, "past_due")

    def test_unknown_event_type_returns_current_unchanged(self) -> None:
        event = {"type": "ping", "data": {"object": {}}}
        current = Subscription(plan_id="team", status="active")
        next_state = apply_stripe_event(event, current)
        self.assertIs(next_state, current)


class AutoPushHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="round7-push-"))
        os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(cls.tmpdir)
        os.environ["DIRECTJOB_VAPID_PUBLIC_KEY"] = "synthetic"
        os.environ["DIRECTJOB_VAPID_PRIVATE_KEY"] = "synthetic"
        for name in list(sys.modules):
            if name == "app" or name.startswith("company_discovery.push_transport"):
                del sys.modules[name]
        import app  # noqa: E402
        from company_discovery import push_transport

        cls.app = app
        cls.state = app.STATE
        cls.push_transport = push_transport
        cls.original_send = push_transport.send_push

    @classmethod
    def tearDownClass(cls) -> None:
        cls.push_transport.send_push = cls.original_send
        for key in ("DIRECTJOB_VAPID_PUBLIC_KEY", "DIRECTJOB_VAPID_PRIVATE_KEY"):
            os.environ.pop(key, None)
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_no_subscription_returns_no_subscriptions(self) -> None:
        out = self.state.notify_new_matches("user_no_subs")
        self.assertEqual(out["status"], "no_subscriptions")
        self.assertEqual(out["sent"], 0)


if __name__ == "__main__":
    unittest.main()
