# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Cost-saving doctrine measured-outcome instrumentation (Phase 2 #69).

The doctrine at ``docs/grant/08-cost-saving-doctrine.md`` lists 8
mechanisms by which the project saves institutional cost. The
"honesty rules" in that doc require every public claim to be tagged
as proven / plausible / aspirational. Most claims start at
aspirational. This module is the substrate that turns aspirational
into measured.

Design principles:

- **Opt-in**: nothing is recorded unless the deployer sets
  ``HELPMEFINDTHEJOB_COST_METRICS=true`` (or the legacy
  ``HELPMEFINDTHEJOB_COST_METRICS`` alias). Off by default. Honesty rule:
  we don't collect data we haven't told the deployer about.
- **No PII**: every user identifier is opaque-hashed via the same
  HMAC chain the audit log uses. The hash is salt-keyed so a
  forensic comparison can confirm a hit without de-anonymising.
- **Append-only JSONL**: same shape as the AI Act Article 12 audit
  log — one event per line, sortable, replayable, never mutated.
- **Aggregation is separate from collection**: the recording side
  writes raw counter events; the aggregation side reads the log
  and produces the 8-mechanism snapshot on demand. Keeps the hot
  path cheap.
- **Deployer-facing report**: ``snapshot()`` returns a dict the
  operator can paste into their funding-renewal PDF. Every metric
  carries a ``confidence`` field (proven / plausible / aspirational)
  derived from event counts so the operator can't accidentally
  claim "proven" with 3 data points.

The 8 mechanisms (mirror of doctrine doc §1–§8):

1. ``shorter_journey``           — advisor-hours saved per user
2. ``self_serve_anerkennung``    — Anerkennung pathway hits without advisor handoff
3. ``higher_apply_rate``         — applications drafted per active week
4. ``fewer_wrong_fit_apps``      — auto-fit refusals (rank-and-drop)
5. ``persistent_index_reuse``    — cache hits vs aggregator calls
6. ``ai_byo_savings``            — local/manual invocations vs paid API
7. ``language_coverage``         — non-EN/DE journeys completed without paid translation
8. ``faster_recognition``        — friction-class transitions per persona

Every event has a fixed schema; new mechanisms get a new event
type rather than reshaping an existing one.
"""

from __future__ import annotations

import hmac
import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# Mechanism IDs — keep these stable; deployers' reports
# reference them by name.
MECHANISM_SHORTER_JOURNEY = "shorter_journey"
MECHANISM_SELF_SERVE_ANERKENNUNG = "self_serve_anerkennung"
MECHANISM_HIGHER_APPLY_RATE = "higher_apply_rate"
MECHANISM_FEWER_WRONG_FIT_APPS = "fewer_wrong_fit_apps"
MECHANISM_PERSISTENT_INDEX_REUSE = "persistent_index_reuse"
MECHANISM_AI_BYO_SAVINGS = "ai_byo_savings"
MECHANISM_LANGUAGE_COVERAGE = "language_coverage"
MECHANISM_FASTER_RECOGNITION = "faster_recognition"

ALL_MECHANISMS: tuple[str, ...] = (
    MECHANISM_SHORTER_JOURNEY,
    MECHANISM_SELF_SERVE_ANERKENNUNG,
    MECHANISM_HIGHER_APPLY_RATE,
    MECHANISM_FEWER_WRONG_FIT_APPS,
    MECHANISM_PERSISTENT_INDEX_REUSE,
    MECHANISM_AI_BYO_SAVINGS,
    MECHANISM_LANGUAGE_COVERAGE,
    MECHANISM_FASTER_RECOGNITION,
)

# Confidence thresholds. Below these counts a metric is
# "aspirational"; between is "plausible"; above is "proven".
# Hand-tuned to be conservative — a deployer with 50 users
# generating 10 events each gets 500 events total, well over
# the proven threshold for any single mechanism.
PROVEN_EVENT_THRESHOLD = 200
PLAUSIBLE_EVENT_THRESHOLD = 30


@dataclass(frozen=True)
class MetricsEvent:
    """One opt-in cost-saving metrics event. The shape is part of
    the public contract: existing event JSONL files in the wild
    must remain readable as the codebase evolves."""

    mechanism: str
    value: float
    unit: str
    user_hash: str
    at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_jsonl(self) -> str:
        payload = {
            "mechanism": self.mechanism,
            "value": self.value,
            "unit": self.unit,
            "user_hash": self.user_hash,
            "at": self.at.isoformat(),
            "metadata": self.metadata,
        }
        return json.dumps(payload, separators=(",", ":"), default=str)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> MetricsEvent:
        at_str = raw.get("at")
        at_dt = datetime.now(timezone.utc)
        if isinstance(at_str, str):
            try:
                at_dt = datetime.fromisoformat(at_str)
            except ValueError:
                at_dt = datetime.now(timezone.utc)
        return cls(
            mechanism=str(raw.get("mechanism", "")),
            value=float(raw.get("value", 0.0) or 0.0),
            unit=str(raw.get("unit", "")),
            user_hash=str(raw.get("user_hash", "")),
            at=at_dt,
            metadata=dict(raw.get("metadata") or {}),
        )


def _env_enabled() -> bool:
    """Two-step env-var lookup (new name preferred, legacy alias
    supported)."""

    for key in ("HELPMEFINDTHEJOB_COST_METRICS", "HELPMEFINDTHEJOB_COST_METRICS"):
        value = os.environ.get(key, "").strip().lower()
        if value in {"1", "true", "yes", "on"}:
            return True
    return False


# Public alias used by the wiring sites (mcp_tools.py,
# diagnostic_engine.py, app.py). Underscore-prefixed names are
# convention-internal; the same predicate exposed at module level
# without the leading underscore is the canonical opt-in check
# external code should use.
def is_collection_enabled() -> bool:
    return _env_enabled()


def _hash_user_id(user_id: str, salt: bytes) -> str:
    """Opaque HMAC-SHA256 of the user id. Matches the audit-log
    pattern in :mod:`company_discovery.audit_log`. Returns a
    16-char hex prefix — collision-resistant for the deployer's
    user count, short enough to not bloat the JSONL."""

    digest = hmac.new(salt, (user_id or "").encode("utf-8"), "sha256").hexdigest()
    return digest[:16]


class CostSavingMetricsLog:
    """File-backed append-only JSONL collector. Thread-safe (one
    lock per instance). Construct one per process; the file path
    defaults to ``<data_dir>/cost_saving_metrics.jsonl``.

    Reading the log (via :meth:`snapshot`) is independent of the
    collector lifecycle — any process can replay the JSONL to
    produce the aggregate report.
    """

    def __init__(
        self,
        path: Path,
        *,
        salt: bytes,
        enabled: bool | None = None,
    ) -> None:
        self.path = path
        self.salt = salt
        self.enabled = _env_enabled() if enabled is None else bool(enabled)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        mechanism: str,
        *,
        value: float,
        unit: str,
        user_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Record one metrics event. Returns True if written,
        False if the collector is disabled (opt-in gate).

        ``mechanism`` MUST be one of the constants in
        :data:`ALL_MECHANISMS`. Passing an unknown mechanism
        raises ``ValueError`` — silent typos here would corrupt
        the deployer's report.
        """

        if mechanism not in ALL_MECHANISMS:
            raise ValueError(f"unknown_mechanism:{mechanism}")
        if not self.enabled:
            return False
        event = MetricsEvent(
            mechanism=mechanism,
            value=float(value),
            unit=unit,
            user_hash=_hash_user_id(user_id, self.salt),
            at=datetime.now(timezone.utc),
            metadata=dict(metadata or {}),
        )
        line = event.to_jsonl() + "\n"
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line)
        return True

    def replay(self) -> Iterable[MetricsEvent]:
        """Yield every event in the log, oldest-first. Used by
        :meth:`snapshot`. Best-effort: malformed lines are
        skipped, never crash the report."""

        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue
                yield MetricsEvent.from_dict(raw)

    def snapshot(self) -> dict[str, Any]:
        """Aggregate the JSONL into a deployer-facing report.

        Shape::

            {
                "windowDays": <int>,  # how many days the log spans
                "uniqueUsers": <int>,  # distinct user_hash values seen
                "mechanisms": {
                    "<mechanism_id>": {
                        "events": <count>,
                        "total": <sum of values>,
                        "unit": <unit string>,
                        "users": <distinct user_hash count>,
                        "confidence": "proven" | "plausible" | "aspirational",
                    },
                    ...
                },
            }

        Confidence is derived from event count: ≥
        :data:`PROVEN_EVENT_THRESHOLD` → proven; ≥
        :data:`PLAUSIBLE_EVENT_THRESHOLD` → plausible; else
        aspirational. Honest by construction — a deployer can't
        accidentally claim "proven" with 3 data points.
        """

        mechanism_stats: dict[str, dict[str, Any]] = {
            m: {"events": 0, "total": 0.0, "unit": "", "users": set()} for m in ALL_MECHANISMS
        }
        all_users: set[str] = set()
        timestamps: list[datetime] = []
        for event in self.replay():
            stats = mechanism_stats.get(event.mechanism)
            if stats is None:
                continue
            stats["events"] += 1
            stats["total"] += event.value
            if not stats["unit"]:
                stats["unit"] = event.unit
            stats["users"].add(event.user_hash)
            all_users.add(event.user_hash)
            timestamps.append(event.at)
        if timestamps:
            window_days = max(
                1,
                int((max(timestamps) - min(timestamps)).total_seconds() // 86400) + 1,
            )
        else:
            window_days = 0
        out_mechanisms: dict[str, dict[str, Any]] = {}
        for mechanism, stats in mechanism_stats.items():
            events = stats["events"]
            if events >= PROVEN_EVENT_THRESHOLD:
                confidence = "proven"
            elif events >= PLAUSIBLE_EVENT_THRESHOLD:
                confidence = "plausible"
            else:
                confidence = "aspirational"
            out_mechanisms[mechanism] = {
                "events": events,
                "total": round(stats["total"], 4),
                "unit": stats["unit"],
                "users": len(stats["users"]),
                "confidence": confidence,
            }
        return {
            "windowDays": window_days,
            "uniqueUsers": len(all_users),
            "mechanisms": out_mechanisms,
        }
