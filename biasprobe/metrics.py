# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Aggregation metrics over ``CallOutcome`` sets.

Two questions a bias review asks of the raw outcomes:

* **per_persona_mean** — does any one persona systematically score lower? A
  large gap between persona means is the first-order disparate-impact signal.
* **cross_provider_disagreement** — on which (persona, scenario) cells do
  providers disagree most? High-spread cells are where a reviewer should look:
  one model may be wrong, or both may be reading different legitimate facets.

Stdlib only (``statistics``); no host-application coupling.
"""

from __future__ import annotations

import statistics
from typing import Any

from biasprobe.outcomes import CallOutcome


def summarize(provider_id: str, outcomes: list[CallOutcome]) -> dict[str, Any]:
    """Build the per-provider summary row ``render_markdown`` expects, by
    tallying outcome statuses + total cost. Used when replaying a cache (the
    live runner builds the same shape as it goes)."""
    return {
        "provider_id": provider_id,
        "total_cells": len(outcomes),
        "ok": sum(1 for o in outcomes if o.status == "ok"),
        "errors": sum(1 for o in outcomes if o.status == "error"),
        "skipped_no_key": sum(1 for o in outcomes if o.status == "skipped_no_key"),
        "over_budget": sum(1 for o in outcomes if o.status == "over_budget"),
        "cache_misses": sum(1 for o in outcomes if o.status == "cache_miss_replay_mode"),
        "total_cost_eur": round(sum(o.cost_eur for o in outcomes), 4),
    }


def per_persona_mean(outcomes: list[CallOutcome]) -> dict[str, float]:
    """Mean ``raw_score`` per persona, over ``ok`` outcomes with a score."""
    by_persona: dict[str, list[int]] = {}
    for o in outcomes:
        if o.status != "ok" or o.raw_score is None:
            continue
        by_persona.setdefault(o.persona_slug, []).append(o.raw_score)
    return {k: round(statistics.fmean(v), 2) for k, v in by_persona.items()}


def cross_provider_disagreement(
    by_provider: dict[str, list[CallOutcome]],
) -> list[dict[str, Any]]:
    """For each (persona, scenario) cell, compute the max-min score
    spread across providers. Returns the top 20 highest-disagreement
    cells — the ones a reviewer should investigate."""
    cell_scores: dict[tuple[str, str], dict[str, int]] = {}
    for provider_id, outs in by_provider.items():
        for o in outs:
            if o.status == "ok" and o.raw_score is not None:
                cell_scores.setdefault((o.persona_slug, o.scenario_label), {})[provider_id] = (
                    o.raw_score
                )
    rows: list[dict[str, Any]] = []
    for (persona, scenario), provider_scores in cell_scores.items():
        if len(provider_scores) < 2:
            continue
        scores = list(provider_scores.values())
        spread = max(scores) - min(scores)
        if spread == 0:
            continue
        rows.append(
            {
                "persona": persona,
                "scenario": scenario,
                "spread": spread,
                "scores": dict(sorted(provider_scores.items())),
            }
        )
    rows.sort(key=lambda r: r["spread"], reverse=True)
    return rows[:20]
