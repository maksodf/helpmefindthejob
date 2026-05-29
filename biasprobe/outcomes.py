# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""The ``CallOutcome`` record and its JSONL cache.

A ``CallOutcome`` is one (provider × persona × scenario) measurement: the
fit-score a model returned for a synthetic job-seeker persona under a given
scenario, plus cost/latency/provenance metadata. The cache is an append-only
JSONL file per provider, keyed by ``(persona_slug, scenario_label)`` — replaying
it reproduces a published bias report offline, with no API keys and no network.

Stdlib only — this module (and the rest of ``biasprobe``) never imports the
host application, so the harness can be lifted into any employment-AI project.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CallOutcome:
    provider_id: str
    persona_slug: str
    scenario_label: str
    status: str  # "ok" | "error" | "skipped_no_key" | "over_budget" | "cache_miss_replay_mode"
    raw_score: int | None = None
    raw_reason: str | None = None
    raw_gaps: list[str] = field(default_factory=list)
    cost_eur: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    duration_ms: int = 0
    error_class: str | None = None
    response_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "persona_slug": self.persona_slug,
            "scenario_label": self.scenario_label,
            "status": self.status,
            "raw_score": self.raw_score,
            "raw_reason": self.raw_reason,
            "raw_gaps": list(self.raw_gaps),
            "cost_eur": round(self.cost_eur, 6),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "duration_ms": self.duration_ms,
            "error_class": self.error_class,
            "response_hash": self.response_hash,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CallOutcome:
        return cls(
            provider_id=raw["provider_id"],
            persona_slug=raw["persona_slug"],
            scenario_label=raw["scenario_label"],
            status=raw["status"],
            raw_score=raw.get("raw_score"),
            raw_reason=raw.get("raw_reason"),
            raw_gaps=list(raw.get("raw_gaps") or []),
            cost_eur=float(raw.get("cost_eur", 0.0)),
            prompt_tokens=int(raw.get("prompt_tokens", 0)),
            completion_tokens=int(raw.get("completion_tokens", 0)),
            duration_ms=int(raw.get("duration_ms", 0)),
            error_class=raw.get("error_class"),
            response_hash=raw.get("response_hash"),
        )


def cache_path(cache_dir: Path, provider_id: str) -> Path:
    """Path to a provider's JSONL cache under ``cache_dir`` (created if absent)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{provider_id}.jsonl"


def load_outcomes_from_path(path: Path) -> dict[tuple[str, str], CallOutcome]:
    """Load cached outcomes from a JSONL file, keyed by
    ``(persona_slug, scenario_label)``.

    Returns an empty dict if the file is absent. Malformed lines are skipped,
    so a partially-written cache still loads what it can.
    """
    if not path.exists():
        return {}
    out: dict[tuple[str, str], CallOutcome] = {}
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                outcome = CallOutcome.from_dict(json.loads(line))
            except (json.JSONDecodeError, KeyError):
                continue
            out[(outcome.persona_slug, outcome.scenario_label)] = outcome
    return out


def append_outcome_to_path(path: Path, outcome: CallOutcome) -> None:
    """Append one outcome to a JSONL cache file (stable, sorted keys)."""
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(outcome.to_dict(), sort_keys=True, separators=(",", ":")) + "\n")


def load_outcomes(cache_dir: Path, provider_id: str) -> dict[tuple[str, str], CallOutcome]:
    """Load a provider's cached outcomes from ``cache_dir`` (dir-based wrapper)."""
    return load_outcomes_from_path(cache_path(cache_dir, provider_id))


def append_outcome(cache_dir: Path, outcome: CallOutcome) -> None:
    """Append one outcome to its provider's JSONL cache under ``cache_dir``."""
    append_outcome_to_path(cache_path(cache_dir, outcome.provider_id), outcome)


def discover_providers(cache_dir: Path) -> list[str]:
    """Provider ids with a cache file under ``cache_dir`` (sorted)."""
    if not cache_dir.exists():
        return []
    return sorted(p.stem for p in cache_dir.glob("*.jsonl"))
