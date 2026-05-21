# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""A/B (and A/B/C/…) testing framework (13-plan item 6/13;
gap #19). Builds on the feature-flag substrate from item 5/13.

The framework has three pieces:

1. **Experiment registry** (:data:`EXPERIMENTS`) — every
   experiment is declared here with its name, variants, primary
   metric, and status. Unregistered names raise KeyError at the
   call site (same typo-guard discipline as the feature-flag
   registry).
2. **Stable variant assignment** — :func:`get_variant` wraps
   :func:`company_discovery.feature_flags.assign_variant` so the
   same user always lands in the same arm.
3. **Outcome recording + aggregation** — outcomes ride on the
   existing analytics-events table (kind=`experiment_outcome`).
   :func:`summarize_experiment` aggregates per-variant counts +
   per-variant unique-user counts, which is enough to compute
   directional results without a separate experiments table.

Honesty:

- This is the MINIMUM viable A/B framework. It does NOT do:
  - statistical significance testing (p-values, CIs)
  - sample-size calculators
  - sequential analysis / early stopping
- It DOES do: stable cohort assignment, outcome tracking,
  per-variant rollup. That's enough to answer "did treatment
  beat control?" directionally.
- A more sophisticated stats layer can be added later by
  consuming :func:`summarize_experiment`'s output and running
  it through scipy (out of stdlib scope right now).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from . import feature_flags

if TYPE_CHECKING:
    from .repository import CompanyDiscoveryRepository


# Event kind used for outcome events on the analytics_events
# table. Picking a stable string is important — the summary
# query filters on it.
OUTCOME_EVENT_KIND = "experiment_outcome"


@dataclass(frozen=True)
class Experiment:
    """One A/B (or A/B/N) experiment.

    - ``name`` is the canonical experiment id (same convention
      as feature-flag names).
    - ``variants`` is the list of arm names. The first is
      conventionally the control. Order matters — variant
      assignment uses the index.
    - ``primary_metric`` is the outcome kind that defines
      success (e.g., ``"completed_first_journey_step"``).
      Secondary metrics CAN be tracked but the summary
      highlights the primary.
    - ``description`` is operator-facing.
    - ``status`` is one of ``active`` / ``paused`` / ``concluded``.
      Paused experiments still assign variants (so users see
      stable UI) but new outcomes won't fire until resumed.
    """

    name: str
    variants: list[str]
    primary_metric: str
    description: str
    status: str = "active"


# Canonical experiment registry. Add new entries here; remove
# concluded ones once their result is acted on (no permanent
# "if variant == 'treatment'" branches lingering in the code).
EXPERIMENTS: dict[str, Experiment] = {
    "example_journey_first_step": Experiment(
        name="example_journey_first_step",
        variants=["control", "treatment"],
        primary_metric="first_step_completed",
        description=(
            "Example experiment used by the framework's E2E tests. "
            "Treatment surfaces a chat-first onboarding prompt; "
            "control uses the existing dashboard tour. Primary "
            "metric: first journey step completed within 24h."
        ),
        status="active",
    ),
}


def get_variant(experiment_name: str, user_id: str) -> str:
    """Return the variant assignment for ``user_id`` in
    ``experiment_name``. Stable across process restarts (uses the
    HMAC-based bucket from :mod:`company_discovery.feature_flags`).

    Raises ``KeyError`` for unregistered experiments — typo guard.
    """

    if experiment_name not in EXPERIMENTS:
        raise KeyError(f"unregistered_experiment:{experiment_name!r}")
    experiment = EXPERIMENTS[experiment_name]
    return feature_flags.assign_variant(
        experiment.name, user_id, experiment.variants
    )


def build_outcome_payload(
    experiment_name: str,
    user_id: str,
    outcome_kind: str,
) -> dict[str, str]:
    """Build the analytics-event payload for an outcome event.

    Keys:
    - ``experimentName``: stable id for join with EXPERIMENTS
    - ``variant``: the arm the user is in (derived via
      :func:`get_variant` — same for the same user every call)
    - ``outcomeKind``: the operator-defined success kind

    Raises ``KeyError`` for unregistered experiments.
    """

    variant = get_variant(experiment_name, user_id)
    return {
        "experimentName": experiment_name,
        "variant": variant,
        "outcomeKind": outcome_kind,
    }


@dataclass(frozen=True)
class VariantStats:
    """Per-variant rollup from :func:`summarize_experiment`."""

    variant: str
    outcomes_total: int
    outcomes_by_kind: dict[str, int]
    unique_users: int


@dataclass(frozen=True)
class ExperimentSummary:
    """Top-level summary returned by :func:`summarize_experiment`.

    Carries the metadata + per-variant stats so a downstream
    stats layer (or the operator) can compute conversion rates
    + winner.
    """

    experiment_name: str
    primary_metric: str
    status: str
    variants: list[VariantStats]


def summarize_experiment(
    experiment_name: str,
    repository: "CompanyDiscoveryRepository",
    *,
    limit: int = 10000,
) -> ExperimentSummary:
    """Aggregate analytics_events into a per-variant rollup for
    one experiment.

    Reads up to ``limit`` recent analytics events (the existing
    repository accessor caps at 200 by default; we widen for
    aggregation). For deployments with millions of events this
    would migrate to a SQL aggregate; for Phase 1 in-memory is
    correct + cheap.

    Raises ``KeyError`` for unregistered experiments.
    """

    if experiment_name not in EXPERIMENTS:
        raise KeyError(f"unregistered_experiment:{experiment_name!r}")
    experiment = EXPERIMENTS[experiment_name]

    # Initialize empty per-variant buckets so the output always
    # carries every declared variant, even if zero outcomes.
    per_variant_outcomes: dict[str, dict[str, int]] = {
        v: {} for v in experiment.variants
    }
    per_variant_users: dict[str, set[str]] = {v: set() for v in experiment.variants}

    events = repository.list_analytics_events(limit=limit)
    for event in events:
        if event.kind != OUTCOME_EVENT_KIND:
            continue
        payload = event.payload or {}
        if payload.get("experimentName") != experiment_name:
            continue
        variant = payload.get("variant")
        outcome_kind = payload.get("outcomeKind")
        if variant not in per_variant_outcomes or not isinstance(outcome_kind, str):
            # Corrupt event (unknown variant / missing outcome) —
            # skip rather than crash. Worst case: the count
            # underreports; the operator sees a stable shape.
            continue
        bucket = per_variant_outcomes[variant]
        bucket[outcome_kind] = bucket.get(outcome_kind, 0) + 1
        per_variant_users[variant].add(event.user_id)

    variants_stats = [
        VariantStats(
            variant=variant,
            outcomes_total=sum(per_variant_outcomes[variant].values()),
            outcomes_by_kind=dict(per_variant_outcomes[variant]),
            unique_users=len(per_variant_users[variant]),
        )
        for variant in experiment.variants
    ]
    return ExperimentSummary(
        experiment_name=experiment_name,
        primary_metric=experiment.primary_metric,
        status=experiment.status,
        variants=variants_stats,
    )


def all_experiments() -> list[dict[str, object]]:
    """Operator introspection: return every registered experiment's
    metadata as plain dicts (for the admin diagnostics endpoint)."""

    return [
        {
            "name": exp.name,
            "variants": list(exp.variants),
            "primaryMetric": exp.primary_metric,
            "description": exp.description,
            "status": exp.status,
        }
        for exp in sorted(EXPERIMENTS.values(), key=lambda e: e.name)
    ]
