# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Apply → reply → interview → offer funnel computation (post-
sprint engineer-gap #10).

The 40-gap analysis flagged "no user-facing analytics — users
can't see their own apply→reply→interview funnel." The data
substrate has been there since Phase 2 (ImportedJob.application_
status + .interview_stage + .replied_at + .application_history)
but no surface exposed it. This module is the computation; the
HTTP route at /api/funnel/summary in app.py renders it; the
frontend mounts it on the dashboard.

Computation contract:

- **Funnel counts**: how many jobs are at each `application_status`
  value (saved / interested / applied / interview / rejected /
  archived).
- **Interview-stage breakdown**: for jobs at status=interview,
  how many are at each `interview_stage` (screening / phone /
  take_home / technical / onsite / panel / offer).
- **Conversion rates**:
  - apply rate = applied / (saved + interested + applied + …
    non-archived) — what fraction of saved jobs the user has
    actually applied to
  - reply rate = jobs-with-replied_at / applied
  - interview rate = at-status-interview / applied
  - offer rate = at-interview-stage-offer / at-status-interview
- **Velocity** (best-effort from application_history): median
  hours between consecutive transitions per status pair.

Honesty:
- These metrics are operator-actionable: a low reply-rate signals
  CV or cover-letter weakness; a low interview rate signals
  fit-scoring drift; a low offer rate signals interview-prep gaps.
- The numbers are inherently small per individual user (a typical
  job search has 20-100 applications). We surface raw counts +
  rates, not percentiles, so users aren't misled into thinking
  the data is statistically robust.
- No DP noise applied — this is the user's own data on their own
  dashboard, not an aggregate public surface.
"""

from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Iterable

from .models import APPLICATION_STATUSES, INTERVIEW_STAGES

if TYPE_CHECKING:
    from .models import ImportedJob


# Statuses that count as "actively pursued" (denominator for apply
# rate). Archived + rejected are end-states and don't count.
_ACTIVE_STATUSES: frozenset[str] = frozenset(
    s for s in APPLICATION_STATUSES if s not in {"archived"}
)


@dataclass(frozen=True)
class FunnelSummary:
    """Per-user funnel snapshot. All fields are primitive +
    JSON-serializable so the HTTP layer can ship it directly."""

    total_jobs: int
    by_status: dict[str, int]
    by_interview_stage: dict[str, int]
    apply_rate: float | None
    reply_rate: float | None
    interview_rate: float | None
    offer_rate: float | None
    median_hours_to_apply: float | None
    median_hours_apply_to_reply: float | None
    median_hours_apply_to_interview: float | None
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_rate(numerator: int, denominator: int) -> float | None:
    """Division that returns ``None`` (not 0.0) when the
    denominator is zero — so the UI can render `—` instead of
    a misleading 0%."""

    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _parse_iso(value: object) -> datetime | None:
    """Coerce a value into an aware ``datetime`` or return
    ``None``. Accepts:

    - ``datetime`` instances → pass through (UTC-normalised if
      naive). The repository returns ``datetime`` for
      ``created_at`` / ``updated_at`` columns, so velocity
      computation must accept that shape directly.
    - ISO 8601 strings → parsed via ``fromisoformat``. The
      ``Z`` suffix some legacy JSON serialisations use is
      coerced to ``+00:00`` first.
    - Anything else (None, int, malformed string) → None.
    """

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _median_hours_between(pairs: list[tuple[datetime, datetime]]) -> float | None:
    """Median wall-clock hours across a list of (earlier, later)
    datetime pairs. Negative deltas are dropped (clock skew /
    bad data). Returns ``None`` when there's nothing to average."""

    hours: list[float] = []
    for earlier, later in pairs:
        delta = (later - earlier).total_seconds() / 3600.0
        if delta < 0:
            continue
        hours.append(delta)
    if not hours:
        return None
    return round(statistics.median(hours), 2)


def _find_transition(history: Iterable[Any], target: str) -> datetime | None:
    """Return the timestamp of the first transition INTO
    ``target`` in the application_history list. The history shape
    is ``[{"at": iso, "from": status, "to": status, ...}, ...]``."""

    for entry in history or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("to") == target:
            ts = _parse_iso(entry.get("at"))
            if ts is not None:
                return ts
    return None


def build_funnel_summary(jobs: list["ImportedJob"]) -> FunnelSummary:
    """Aggregate a user's imported jobs into the public funnel
    snapshot. Pure function — no DB access, no side effects."""

    by_status: dict[str, int] = {status: 0 for status in APPLICATION_STATUSES}
    by_interview_stage: dict[str, int] = {stage: 0 for stage in INTERVIEW_STAGES}
    total = 0
    applied_count = 0
    interview_count = 0
    offer_stage_count = 0
    replied_count = 0
    # Velocity buckets — each is a list of (earlier, later)
    # datetime pairs we'll feed into _median_hours_between.
    saved_to_applied: list[tuple[datetime, datetime]] = []
    applied_to_reply: list[tuple[datetime, datetime]] = []
    applied_to_interview: list[tuple[datetime, datetime]] = []

    for job in jobs:
        total += 1
        status = getattr(job, "application_status", "saved") or "saved"
        if status not in by_status:
            # Unknown status (corrupt data) — bucket under "saved"
            # so we don't lose it, but don't add a new key.
            status = "saved"
        by_status[status] += 1
        if status == "interview":
            stage = getattr(job, "interview_stage", None) or "screening"
            # Mirror the unknown-status fallback: bucket unknown
            # stages under "screening" so the invariant
            # `sum(by_interview_stage.values()) == interview_count`
            # holds for every input. Without this, a job with a
            # custom stage label silently disappears from the
            # stage breakdown — UI shows "5 in interview" with
            # stages summing to 4, which the user can't reconcile.
            if stage not in by_interview_stage:
                stage = "screening"
            by_interview_stage[stage] += 1
            if stage == "offer":
                offer_stage_count += 1
            interview_count += 1
        if status == "applied" or status in {"interview", "rejected"}:
            # "applied" plus any state DOWNSTREAM of applied
            # (interview, rejected) counts as "has applied"
            applied_count += 1
        if getattr(job, "replied_at", None):
            replied_count += 1
        # Velocity from application_history transitions
        history = getattr(job, "application_history", []) or []
        applied_at = _find_transition(history, "applied")
        saved_at = _parse_iso(getattr(job, "created_at", None))
        if saved_at and applied_at:
            saved_to_applied.append((saved_at, applied_at))
        if applied_at:
            replied_at = _parse_iso(getattr(job, "replied_at", None))
            if replied_at:
                applied_to_reply.append((applied_at, replied_at))
            interview_at = _find_transition(history, "interview")
            if interview_at:
                applied_to_interview.append((applied_at, interview_at))

    active_total = sum(by_status[s] for s in _ACTIVE_STATUSES)
    return FunnelSummary(
        total_jobs=total,
        by_status=by_status,
        by_interview_stage=by_interview_stage,
        apply_rate=_safe_rate(applied_count, active_total),
        reply_rate=_safe_rate(replied_count, applied_count),
        interview_rate=_safe_rate(interview_count, applied_count),
        offer_rate=_safe_rate(offer_stage_count, interview_count),
        median_hours_to_apply=_median_hours_between(saved_to_applied),
        median_hours_apply_to_reply=_median_hours_between(applied_to_reply),
        median_hours_apply_to_interview=_median_hours_between(
            applied_to_interview
        ),
    )
