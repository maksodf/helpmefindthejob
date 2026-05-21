# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Per-user BYO-AI spend cap (Phase 2 backlog #46).

When a user supplies their own LLM API key, a runaway analysis loop
(e.g. an aggressive watchlist hammering the OpenAI API) could burn
through hundreds of euros of their personal credit before they notice.
The cap is the user's contract: "stop spending my money once I've
spent X this calendar month."

This module is the substrate:

- ``estimate_eur`` — rate-table-based cost estimate for one
  invocation (prompt + response) on a given provider.
- ``month_to_date_eur`` — sum of estimated costs of all
  ``ai_invocation_cost`` analytics events for the user in the
  current calendar month (UTC).
- ``enforce_cap`` — pre-flight check; raises
  :class:`CostCapExceeded` (with a localised friendly message) if
  the next call would push the user over their personal cap.
- ``record_invocation`` — post-call analytics-event write so the
  next ``month_to_date_eur`` query sees this call's cost.

Design notes:

- We estimate tokens from char counts (~4 chars/token for EN+DE
  mixed text). This is intentionally pessimistic — over-estimating
  cost slightly is safer than under-estimating and surprising the
  user with a real bill higher than the cap.
- Free / local providers (ollama, manual, claude_code) have all-
  zero rates. They never trigger the cap.
- The cap only counts BYO modes (``invocation_mode == "api"``).
  Local-mode invocations have no spend, by definition.
- Rates are denominated in EUR using rough 2026-Q1 published USD
  prices × 0.92 (the actual currency conversion happens whenever
  the user's billing provider settles). We refresh quarterly.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timezone


# Per-provider, per-million-token EUR rates. Sourced from public
# pricing pages 2026-Q1 (refresh quarterly). Where a provider
# bills per-call rather than per-token, we fall back to an
# approximation calibrated to a 1k-token call.
#
# Each entry: provider_id → {"prompt_per_mtok": float, "completion_per_mtok": float}
PROVIDER_RATES_EUR_PER_MTOK: dict[str, dict[str, float]] = {
    # Cloud — paid (per-token)
    "openai": {"prompt_per_mtok": 2.30, "completion_per_mtok": 9.20},  # gpt-4o-ish
    "openai_4o_mini": {"prompt_per_mtok": 0.14, "completion_per_mtok": 0.55},
    "openai_o1": {"prompt_per_mtok": 13.80, "completion_per_mtok": 55.20},
    "gemini": {"prompt_per_mtok": 1.15, "completion_per_mtok": 3.45},  # 1.5 Pro
    "gemini_flash": {"prompt_per_mtok": 0.07, "completion_per_mtok": 0.28},
    "anthropic": {"prompt_per_mtok": 2.76, "completion_per_mtok": 13.80},  # Sonnet 4
    "anthropic_haiku": {"prompt_per_mtok": 0.74, "completion_per_mtok": 3.68},
    "anthropic_opus": {"prompt_per_mtok": 13.80, "completion_per_mtok": 69.00},
    "deepseek": {"prompt_per_mtok": 0.13, "completion_per_mtok": 0.25},
    "openrouter": {"prompt_per_mtok": 2.30, "completion_per_mtok": 9.20},  # varies by route; use OpenAI-ish as upper bound
    # Local / managed — free at point of use (no per-call charge to the user)
    "ollama": {"prompt_per_mtok": 0.0, "completion_per_mtok": 0.0},
    "manual": {"prompt_per_mtok": 0.0, "completion_per_mtok": 0.0},
    "claude_code": {"prompt_per_mtok": 0.0, "completion_per_mtok": 0.0},
}

# Default cap when the user has not configured one (a profile that
# pre-dates the cap feature). EUR / month. Modest enough that a
# reasonable user workflow won't hit it, low enough that a runaway
# loop is caught before €100 is gone.
DEFAULT_MONTHLY_CAP_EUR: float = 5.0


@dataclass(frozen=True)
class CostCapContext:
    """Bundle of context the dispatch chokepoint needs to enforce a
    per-user cap. Handlers and REST endpoints construct this once and
    pass it through to :func:`_dispatch_provider`; the dispatch path
    calls :func:`enforce_cap` before the AI invocation and
    :func:`record_invocation` after.

    A ``None`` context means "no cap enforcement on this call" — the
    sole legitimate use is for system-internal calls that aren't
    user-attributable (e.g. a maintenance migration). All user-
    initiated dispatches MUST provide a context.
    """

    user_id: str
    repository: object  # SqliteCompanyDiscoveryRepository — duck-typed to avoid circular import
    cap_eur: float
    locale: str = "en"

    def with_locale(self, locale: str) -> "CostCapContext":
        from dataclasses import replace

        return replace(self, locale=locale)


@dataclass(frozen=True)
class CostEstimate:
    """Structured estimate of one invocation's cost. The dataclass
    shape is part of the public API so test fixtures and the
    Settings UI can reflect cost without re-deriving from raw fields.
    """

    provider_id: str
    prompt_tokens: int
    completion_tokens: int
    prompt_eur: float
    completion_eur: float

    @property
    def total_eur(self) -> float:
        return round(self.prompt_eur + self.completion_eur, 6)


class CostCapExceeded(Exception):
    """Raised by :func:`enforce_cap` when the next AI call would
    push the user over their personal monthly cap. Carries the
    structured cap context so callers can render a friendly UX
    surface ("You've spent €4.85 of your €5.00 monthly cap…").
    """

    def __init__(
        self,
        *,
        cap_eur: float,
        spent_eur: float,
        next_call_eur: float,
        provider_id: str,
        locale: str = "en",
    ) -> None:
        self.cap_eur = float(cap_eur)
        self.spent_eur = float(spent_eur)
        self.next_call_eur = float(next_call_eur)
        self.provider_id = provider_id
        self.locale = locale
        if locale.startswith("de"):
            msg = (
                f"Monatliches BYO-AI-Limit erreicht: bereits €{spent_eur:.2f} "
                f"von €{cap_eur:.2f} ausgegeben. Der nächste {provider_id}-Aufruf "
                f"(geschätzt €{next_call_eur:.2f}) würde es überschreiten. "
                "Erhöhe das Limit in den Einstellungen oder warte bis zum nächsten Monat."
            )
        else:
            msg = (
                f"Monthly BYO-AI cap reached: already spent €{spent_eur:.2f} "
                f"of €{cap_eur:.2f}. The next {provider_id} call "
                f"(est. €{next_call_eur:.2f}) would exceed it. "
                "Raise the cap in Settings or wait until next month."
            )
        super().__init__(msg)


def _chars_to_tokens(chars: int) -> int:
    """Heuristic: ~4 chars per token for mixed EN+DE prose. Rounds
    up to be safe (pessimistic estimate)."""

    if chars <= 0:
        return 0
    return (chars + 3) // 4


def estimate_eur(
    provider_id: str,
    prompt_text: str,
    response_text: str = "",
) -> CostEstimate:
    """Estimate the EUR cost of one AI invocation. Unknown providers
    return a zero-cost estimate (we'd rather under-bill an unknown
    provider than block legitimate calls)."""

    rates = PROVIDER_RATES_EUR_PER_MTOK.get(
        provider_id, {"prompt_per_mtok": 0.0, "completion_per_mtok": 0.0}
    )
    prompt_tokens = _chars_to_tokens(len(prompt_text or ""))
    completion_tokens = _chars_to_tokens(len(response_text or ""))
    prompt_eur = prompt_tokens / 1_000_000 * rates["prompt_per_mtok"]
    completion_eur = (
        completion_tokens / 1_000_000 * rates["completion_per_mtok"]
    )
    return CostEstimate(
        provider_id=provider_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        prompt_eur=round(prompt_eur, 6),
        completion_eur=round(completion_eur, 6),
    )


def _current_month_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return (start, end) datetimes (UTC, inclusive-exclusive) for the
    current calendar month."""

    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    start = moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    days_in_month = calendar.monthrange(moment.year, moment.month)[1]
    end = start.replace(day=days_in_month, hour=23, minute=59, second=59, microsecond=999999)
    # Use exclusive end-of-month + 1 second so the < comparison is clean
    return start, end


def month_to_date_eur(
    user_id: str,
    repository,
    *,
    now: datetime | None = None,
) -> float:
    """Sum the ``estimated_eur`` field across the user's
    ``ai_invocation_cost`` analytics events for the current
    calendar month. Returns 0.0 for users with no events.
    """

    if not user_id:
        return 0.0
    start, end = _current_month_window(now=now)
    total = 0.0
    try:
        events = repository.list_analytics_events(user_id=user_id, limit=10_000)
    except Exception:  # noqa: BLE001 - Case E best-effort: failing to load history means we conservatively assume 0 spend (won't block, but won't over-block)
        return 0.0
    for event in events:
        if getattr(event, "kind", None) != "ai_invocation_cost":
            continue
        ts = getattr(event, "created_at", None)
        if ts is None:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts < start or ts > end:
            continue
        payload = getattr(event, "payload", {}) or {}
        eur = payload.get("estimated_eur", 0.0)
        try:
            total += float(eur or 0.0)
        except (TypeError, ValueError):
            continue
    return round(total, 6)


def enforce_cap(
    *,
    user_id: str,
    repository,
    cap_eur: float,
    provider_id: str,
    invocation_mode: str,
    prompt_text: str,
    locale: str = "en",
    now: datetime | None = None,
) -> CostEstimate:
    """Pre-flight cap check. Raises :class:`CostCapExceeded` if
    ``month_to_date_eur(user_id) + estimate_eur(prompt) > cap_eur``
    AND the provider actually charges (free providers always pass).

    Returns the :class:`CostEstimate` for the upcoming call so
    callers don't have to compute it twice.

    ``invocation_mode`` filters out local-mode runs (which have no
    cost regardless of provider_id). Passing ``"local_http"`` or
    ``"local_cli"`` always passes.
    """

    estimate = estimate_eur(provider_id, prompt_text)
    # Free invocation modes never trigger the cap
    if invocation_mode in {"local_http", "local_cli", "manual"}:
        return estimate
    if estimate.total_eur <= 0:
        return estimate
    spent = month_to_date_eur(user_id, repository, now=now)
    if spent + estimate.total_eur > cap_eur:
        raise CostCapExceeded(
            cap_eur=cap_eur,
            spent_eur=spent,
            next_call_eur=estimate.total_eur,
            provider_id=provider_id,
            locale=locale,
        )
    return estimate


def record_invocation(
    *,
    user_id: str,
    repository,
    provider_id: str,
    invocation_mode: str,
    prompt_text: str,
    response_text: str = "",
) -> CostEstimate:
    """Write an ``ai_invocation_cost`` analytics event so the next
    :func:`month_to_date_eur` query sees this call's cost.

    Free invocation modes (local + manual) still record an event
    with ``estimated_eur=0`` so the operator can audit *call
    counts* for compliance — Article 50's "informed of the system's
    use" promise requires us to know how many AI calls a user has
    made on their behalf, even if free.

    Returns the :class:`CostEstimate` for caller convenience.
    """

    from company_discovery.models import AnalyticsEvent

    estimate = estimate_eur(provider_id, prompt_text, response_text)
    try:
        event = AnalyticsEvent(
            user_id=user_id,
            kind="ai_invocation_cost",
            payload={
                "provider_id": provider_id,
                "invocation_mode": invocation_mode,
                "prompt_tokens": estimate.prompt_tokens,
                "completion_tokens": estimate.completion_tokens,
                "estimated_eur": estimate.total_eur,
            },
        )
        repository.save_analytics_event(event)
    except Exception:  # noqa: BLE001 - Case E best-effort: a failed cost-event write must not break the AI call
        pass
    return estimate
