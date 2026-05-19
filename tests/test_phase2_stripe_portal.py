# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Stripe Customer Portal redirect (Phase 2 tracker item #22).

Adds ``StripeBillingBackend.create_portal_session`` so the in-app
"Manage subscription" link can redirect the user to Stripe's hosted
portal — they self-serve invoices / card updates / cancellations
without an operator support ticket.

The webhook event handler now propagates ``customer`` from each
``checkout.session.completed`` / ``customer.subscription.*`` event
into ``Subscription.customer_id`` so the portal call has something to
target. Carries forward across no-op events.
"""

from __future__ import annotations

import unittest

from company_discovery.billing import (
    StripeBillingBackend,
    Subscription,
    apply_stripe_event,
)


class FakeStripeTransport:
    def __init__(self, response: dict[str, object]) -> None:
        self.calls: list[tuple[str, str, dict[str, str]]] = []
        self.response = response

    def __call__(self, method: str, url: str, form: dict[str, str]) -> dict[str, object]:
        self.calls.append((method, url, dict(form)))
        return self.response


class StripePortalSessionTests(unittest.TestCase):
    def test_portal_session_posts_to_stripe(self) -> None:
        transport = FakeStripeTransport(
            {"id": "bps_test_123", "url": "https://billing.stripe.example/p/bps_test_123"},
        )
        # construct the backend directly + patch in the env-derived api_key
        backend = StripeBillingBackend(transport=transport)
        backend.api_key = "sk_test_dummy"

        result = backend.create_portal_session(
            customer_id="cus_test_123",
            return_url="https://app.helpmefindthejob.com/?billing=portal-return",
        )

        self.assertEqual(result["id"], "bps_test_123")
        self.assertEqual(result["url"], "https://billing.stripe.example/p/bps_test_123")
        self.assertEqual(
            result["returnUrl"], "https://app.helpmefindthejob.com/?billing=portal-return"
        )
        # Verify the form fields posted upstream.
        method, url, form = transport.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://api.stripe.com/v1/billing_portal/sessions")
        self.assertEqual(form["customer"], "cus_test_123")
        self.assertEqual(
            form["return_url"], "https://app.helpmefindthejob.com/?billing=portal-return"
        )

    def test_missing_api_key_raises(self) -> None:
        backend = StripeBillingBackend(transport=FakeStripeTransport({}))
        backend.api_key = ""
        with self.assertRaises(RuntimeError):
            backend.create_portal_session(customer_id="cus_x", return_url="https://x")

    def test_missing_customer_id_raises(self) -> None:
        backend = StripeBillingBackend(transport=FakeStripeTransport({}))
        backend.api_key = "sk_test_dummy"
        with self.assertRaises(ValueError):
            backend.create_portal_session(customer_id="", return_url="https://x")

    def test_missing_return_url_raises(self) -> None:
        backend = StripeBillingBackend(transport=FakeStripeTransport({}))
        backend.api_key = "sk_test_dummy"
        with self.assertRaises(ValueError):
            backend.create_portal_session(customer_id="cus_x", return_url="")


class CustomerIdPropagationTests(unittest.TestCase):
    def test_checkout_completed_records_customer_id(self) -> None:
        before = Subscription()
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer": "cus_alice",
                    "customer_email": "alice@example.com",
                    "line_items": [{"price": {"id": "price_team"}}],
                }
            },
        }
        after = apply_stripe_event(
            event, before, plan_resolver=lambda p: "team" if p == "price_team" else ""
        )
        self.assertEqual(after.customer_id, "cus_alice")
        self.assertEqual(after.customer_email, "alice@example.com")
        self.assertEqual(after.plan_id, "team")

    def test_subscription_updated_carries_customer_id(self) -> None:
        before = Subscription(customer_id="cus_existing", plan_id="team")
        event = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "customer": "cus_existing",
                    "status": "active",
                    "items": {"data": [{"price": {"id": "price_team"}}]},
                }
            },
        }
        after = apply_stripe_event(event, before, plan_resolver=lambda p: "team")
        self.assertEqual(after.customer_id, "cus_existing")

    def test_unknown_event_keeps_customer_id(self) -> None:
        before = Subscription(customer_id="cus_keep_me")
        event = {"type": "ping", "data": {"object": {}}}
        after = apply_stripe_event(event, before)
        # apply_stripe_event returns ``current`` unchanged on unknown
        # event types; customer_id must therefore be intact.
        self.assertEqual(after.customer_id, "cus_keep_me")


if __name__ == "__main__":
    unittest.main()
