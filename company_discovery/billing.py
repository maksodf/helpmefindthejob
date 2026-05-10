"""Provider-neutral billing abstraction.

Two backends ship in this module:

- ``ManualBillingBackend`` — the default. Plans are stored in
  ``data/billing.json`` and an admin manually marks a workspace as
  ``active`` / ``cancelled``. No external network call.
- ``StripeBillingBackend`` — uses the Stripe REST API directly via
  stdlib ``urllib`` + an injectable HTTP transport for tests. Reads
  ``DIRECTJOB_STRIPE_API_KEY`` plus ``DIRECTJOB_STRIPE_PRICE_TEAM`` /
  ``DIRECTJOB_STRIPE_PRICE_ORG``. ``load`` and ``save`` continue to
  read/write the local JSON cache so the admin UI stays usable even
  when the Stripe API is unreachable. The Stripe-only entry point is
  ``create_checkout_session``.

The Stripe surface is intentionally minimal: we ship Checkout-session
creation, which is enough to take payment for a chosen plan. Webhooks
and per-subscription introspection are not implemented; operators
that need them can extend ``StripeBillingBackend`` or move to a
dedicated billing platform.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Plan:
    id: str
    label: str
    monthly_price_eur: int
    seats_included: int
    features: tuple[str, ...]
    # Tier limits (#24, #25). ``None`` for an integer limit means
    # "unlimited"; an empty tuple for ``ai_modes_allowed`` means "no AI
    # at all" (we don't ship that today). The operator finalises these
    # numbers when the pricing model decision lands (#21).
    saved_search_limit: int | None = None
    ai_modes_allowed: tuple[str, ...] = ("manual", "byok", "managed")
    retention_days_max: int = 365
    daily_digest_enabled: bool = True


PLANS: tuple[Plan, ...] = (
    Plan(
        id="pilot",
        label="Pilot",
        monthly_price_eur=0,
        seats_included=5,
        features=("Up to 5 testers", "ConsoleTransport email", "Manual restore drill"),
        saved_search_limit=3,
        ai_modes_allowed=("manual",),
        retention_days_max=30,
        daily_digest_enabled=False,
    ),
    Plan(
        id="team",
        label="Team",
        monthly_price_eur=79,
        seats_included=15,
        features=("Up to 15 testers", "SMTP email", "Daily backups + monitoring", "Standard SLA"),
        saved_search_limit=None,
        ai_modes_allowed=("manual", "byok", "managed"),
        retention_days_max=90,
        daily_digest_enabled=True,
    ),
    Plan(
        id="org",
        label="Organization",
        monthly_price_eur=249,
        seats_included=60,
        features=("Up to 60 testers", "Per-domain quotas", "Priority support", "Stripe + invoice"),
        saved_search_limit=None,
        ai_modes_allowed=("manual", "byok", "managed"),
        retention_days_max=180,
        daily_digest_enabled=True,
    ),
)


@dataclass
class Subscription:
    plan_id: str = "pilot"
    status: str = "active"
    seats: int = 1
    started_at: str = field(default_factory=_now_iso)
    cancelled_at: str | None = None
    notes: str | None = None
    customer_email: str | None = None
    customer_id: str | None = None  # Stripe customer id; required for the customer-portal redirect
    last_event: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class BillingBackend(Protocol):
    name: str

    def load(self) -> Subscription:
        ...

    def save(self, subscription: Subscription) -> Subscription:
        ...


def verify_stripe_webhook_signature(
    payload: bytes,
    header_value: str,
    secret: str,
    *,
    tolerance_seconds: int = 300,
    now_ts: int | None = None,
) -> bool:
    """Verify a Stripe webhook signature header against ``secret``.

    Implements the Stripe ``v1`` scheme: HMAC-SHA256 of
    ``f"{timestamp}.{payload}"`` keyed on the webhook secret, compared
    to the ``v1=`` value in the header. ``tolerance_seconds`` rejects
    replays that are more than 5 minutes old by default.
    """

    import hashlib
    import hmac
    import time

    if not header_value or not secret:
        return False
    pairs: dict[str, list[str]] = {}
    for pair in header_value.split(","):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        pairs.setdefault(key.strip(), []).append(value.strip())
    timestamps = pairs.get("t", [])
    candidates = pairs.get("v1", [])
    if not timestamps or not candidates:
        return False
    try:
        ts = int(timestamps[0])
    except ValueError:
        return False
    current = now_ts if now_ts is not None else int(time.time())
    if abs(current - ts) > tolerance_seconds:
        return False
    signed = f"{ts}.".encode("utf-8") + payload
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, c) for c in candidates)


def apply_stripe_event(
    event: dict[str, object],
    current: Subscription,
    *,
    plan_resolver: Callable[[str], str] | None = None,
) -> Subscription:
    """Map a Stripe event onto a new ``Subscription`` state.

    Returns the ``current`` subscription unchanged when the event type
    isn't one we care about. ``plan_resolver`` translates a Stripe price
    id back into our plan id (``team`` / ``org``); pass ``None`` to keep
    the existing ``plan_id``.
    """

    event_type = str(event.get("type") or "")
    obj = (event.get("data") or {}).get("object") or {}  # type: ignore[union-attr]
    if not isinstance(obj, dict):
        return current
    next_state = Subscription(
        plan_id=current.plan_id,
        status=current.status,
        seats=current.seats,
        started_at=current.started_at,
        cancelled_at=current.cancelled_at,
        notes=current.notes,
        customer_email=current.customer_email,
        customer_id=current.customer_id,
        last_event=event_type,
    )
    customer_email = obj.get("customer_email") or obj.get("customer_details", {}).get("email") if isinstance(obj.get("customer_details"), dict) else obj.get("customer_email")
    if customer_email and isinstance(customer_email, str):
        next_state.customer_email = customer_email
    customer_id = obj.get("customer")
    if customer_id and isinstance(customer_id, str):
        next_state.customer_id = customer_id

    if event_type == "checkout.session.completed":
        next_state.status = "active"
        line = (obj.get("display_items") or obj.get("line_items") or [None])[0] if isinstance(obj.get("line_items"), list) else None
        price_id = ""
        if isinstance(line, dict):
            price_id = str((line.get("price") or {}).get("id") or "")
        if plan_resolver and price_id:
            next_state.plan_id = plan_resolver(price_id) or current.plan_id
    elif event_type == "customer.subscription.updated":
        status = str(obj.get("status") or current.status)
        next_state.status = "active" if status in ("active", "trialing") else status
        items = (obj.get("items") or {}).get("data") or []
        if isinstance(items, list) and items:
            price = items[0].get("price") if isinstance(items[0], dict) else {}
            price_id = str((price or {}).get("id") or "")
            if plan_resolver and price_id:
                next_state.plan_id = plan_resolver(price_id) or current.plan_id
    elif event_type == "customer.subscription.deleted":
        next_state.status = "cancelled"
        next_state.cancelled_at = _now_iso()
    elif event_type == "invoice.payment_failed":
        next_state.status = "past_due"
    else:
        return current
    return next_state


@dataclass
class ManualBillingBackend:
    name: str = "manual"
    path: Path = Path("data/billing.json")

    def load(self) -> Subscription:
        if not self.path.exists():
            return Subscription()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return Subscription()
        return Subscription(**{key: payload.get(key) for key in Subscription.__dataclass_fields__ if key in payload})

    def save(self, subscription: Subscription) -> Subscription:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(subscription.to_dict(), indent=2), encoding="utf-8")
        return subscription


StripeTransport = Callable[[str, str, dict[str, str]], dict[str, object]]


def _default_stripe_transport(method: str, url: str, form: dict[str, str]) -> dict[str, object]:
    api_key = os.environ.get("DIRECTJOB_STRIPE_API_KEY", "")
    if not api_key:
        raise RuntimeError("billing_backend_unconfigured: set DIRECTJOB_STRIPE_API_KEY")
    body = urllib.parse.urlencode(form).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body if method != "GET" else None,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Stripe-Version": "2024-06-20",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=15, context=ssl.create_default_context()) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8") if error.fp else ""
        raise RuntimeError(f"stripe_http_error_{error.code}: {detail[:200]}") from None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        raise RuntimeError("stripe_invalid_response") from None


class StripeBillingBackend:
    """Stripe-backed billing.

    ``transport`` defaults to a stdlib HTTPS POST against
    ``https://api.stripe.com/v1`` but tests can inject a fake to keep
    the unit suite offline.

    State persistence still goes through the local JSON file so the
    admin UI never blocks on a Stripe outage.
    """

    name = "stripe"

    def __init__(
        self,
        *,
        path: Path = Path("data/billing.json"),
        transport: StripeTransport | None = None,
    ) -> None:
        self.path = path
        self.api_key = os.environ.get("DIRECTJOB_STRIPE_API_KEY", "")
        self.success_url = os.environ.get("DIRECTJOB_STRIPE_SUCCESS_URL", "")
        self.cancel_url = os.environ.get("DIRECTJOB_STRIPE_CANCEL_URL", "")
        self.price_lookup = {
            "team": os.environ.get("DIRECTJOB_STRIPE_PRICE_TEAM", ""),
            "org": os.environ.get("DIRECTJOB_STRIPE_PRICE_ORG", ""),
        }
        self._transport: StripeTransport = transport or _default_stripe_transport

    @property
    def configured(self) -> bool:
        return bool(self.api_key) and any(self.price_lookup.values())

    def load(self) -> Subscription:
        if not self.path.exists():
            return Subscription()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return Subscription()
        return Subscription(**{key: payload.get(key) for key in Subscription.__dataclass_fields__ if key in payload})

    def save(self, subscription: Subscription) -> Subscription:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(subscription.to_dict(), indent=2), encoding="utf-8")
        return subscription

    def create_checkout_session(self, *, plan_id: str, customer_email: str | None = None) -> dict[str, object]:
        if not self.configured:
            raise RuntimeError("billing_backend_unconfigured: set DIRECTJOB_STRIPE_API_KEY and price IDs")
        price_id = self.price_lookup.get(plan_id)
        if not price_id:
            raise ValueError("unknown_plan")
        if not self.success_url or not self.cancel_url:
            raise RuntimeError("billing_backend_unconfigured: set DIRECTJOB_STRIPE_SUCCESS_URL and DIRECTJOB_STRIPE_CANCEL_URL")
        form: dict[str, str] = {
            "mode": "subscription",
            "success_url": self.success_url,
            "cancel_url": self.cancel_url,
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "allow_promotion_codes": "true",
        }
        if customer_email:
            form["customer_email"] = customer_email
        response = self._transport("POST", "https://api.stripe.com/v1/checkout/sessions", form)
        return {
            "id": response.get("id"),
            "url": response.get("url"),
            "planId": plan_id,
            "priceId": price_id,
            "expiresAt": response.get("expires_at"),
        }

    def create_portal_session(self, *, customer_id: str, return_url: str) -> dict[str, object]:
        """Mint a Stripe Customer Portal session so users can self-manage
        their subscription (see invoices, update card, cancel) without
        the operator having to handle support tickets. The portal is
        the canonical answer to the 24h SLA on billing changes."""

        if not self.api_key:
            raise RuntimeError("billing_backend_unconfigured: set DIRECTJOB_STRIPE_API_KEY")
        if not customer_id:
            raise ValueError("missing_customer_id")
        if not return_url:
            raise ValueError("missing_return_url")
        form = {
            "customer": customer_id,
            "return_url": return_url,
        }
        response = self._transport("POST", "https://api.stripe.com/v1/billing_portal/sessions", form)
        return {
            "id": response.get("id"),
            "url": response.get("url"),
            "returnUrl": return_url,
        }


def build_backend(*, data_dir: Path | None = None) -> BillingBackend:
    backend = (os.environ.get("DIRECTJOB_BILLING_BACKEND") or "manual").strip().casefold()
    base = Path(data_dir) if data_dir else Path("data")
    if backend == "stripe":
        return StripeBillingBackend(path=base / "billing.json")
    return ManualBillingBackend(path=base / "billing.json")


def plans_payload() -> list[dict[str, object]]:
    return [
        {
            "id": plan.id,
            "label": plan.label,
            "monthlyPriceEur": plan.monthly_price_eur,
            "seatsIncluded": plan.seats_included,
            "features": list(plan.features),
            "savedSearchLimit": plan.saved_search_limit,
            "aiModesAllowed": list(plan.ai_modes_allowed),
            "retentionDaysMax": plan.retention_days_max,
            "dailyDigestEnabled": plan.daily_digest_enabled,
        }
        for plan in PLANS
    ]


def find_plan(plan_id: str) -> Plan | None:
    for plan in PLANS:
        if plan.id == plan_id:
            return plan
    return None
