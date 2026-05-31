# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Reproducible reconciliation benchmark for escolib.

Measures how well the reconciler resolves colloquial **synonym** queries back to
their canonical ESCO/ISCO code. The labelled set combines the committed
dataset's ``altLabels_en`` / ``altLabels_de`` arrays (today concentrated in the
nursing codes — the entries that carry curated altLabels) with a hand-curated
set of cross-persona colloquial queries (``CURATED_CASES``) so coverage spans
all seven personas rather than only the altLabel-enriched entries. It is fully
reproducible and needs no external ground truth: every labelled query must
resolve to the right code.

Metrics:
  * **recall** — fraction of synonym queries whose canonical code appears in
    the returned matches (the synonym is findable at all);
  * **top-1** — fraction whose canonical code is the *first* match (some
    synonyms are intentionally shared across sibling codes, so top-1 < 100%
    is expected and not a defect);
  * **false positives** — a small set of nonsense queries that must return
    zero matches (guards against over-broad substring matching).

Run it::

    python -m escolib.benchmark
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from escolib.dataset import EscoDataset, load_dataset
from escolib.reconcile import EscoReconciler

#: Hand-curated realistic colloquial queries → expected canonical code, one
#: per persona/skill family, complementing the altLabel-derived cases so the
#: benchmark spans all seven personas rather than only the synonym-enriched
#: nursing entries. Expected codes verified against the committed dataset.
CURATED_CASES: tuple[tuple[str, str], ...] = (
    ("Maschinenbauingenieur", "2144.1"),  # Yusuf — mechanical engineer
    ("Anlagenmechaniker", "7126.1"),  # Mahmoud — SHK trade
    ("Pflegehelfer", "5321.1"),  # care assistant
    ("häusliche Pflege", "5322.1"),  # Maria — home-based care
    ("Softwareentwickler", "2512.1"),  # Tobias — software
    ("Frontend", "2513.1"),  # Olga — frontend developer
    ("Schweißen", "S.ENG.WELD"),  # welding skill
    ("Deutsch B1", "S.LANG.DE.B1"),  # CEFR language skill
    ("TypeScript", "S.IT.TYPESCRIPT"),  # IT skill
)

#: Queries that must return zero matches (over-broad-matching guard). Mixes
#: nonsense strings with realistic-but-out-of-dataset occupation terms.
NEGATIVE_QUERIES = (
    "zzzznotareal",
    "qwertyxyz",
    "definitely not an occupation 123",
    "Mechatroniker",
    "Buchhaltung",
    "Lagerarbeit",
)


@dataclass
class BenchmarkResult:
    dataset_version: str
    total_candidates: int
    synonym_cases: int
    recalled: int
    top1: int
    negative_queries: int
    false_positives: int
    failures: list[dict[str, Any]] = field(default_factory=list)

    @property
    def recall_pct(self) -> float:
        return 100.0 * self.recalled / self.synonym_cases if self.synonym_cases else 0.0

    @property
    def top1_pct(self) -> float:
        return 100.0 * self.top1 / self.synonym_cases if self.synonym_cases else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "datasetVersion": self.dataset_version,
            "totalCandidates": self.total_candidates,
            "synonymCases": self.synonym_cases,
            "recalled": self.recalled,
            "recallPct": round(self.recall_pct, 1),
            "top1": self.top1,
            "top1Pct": round(self.top1_pct, 1),
            "negativeQueries": self.negative_queries,
            "falsePositives": self.false_positives,
            "failures": self.failures,
        }


def _synonym_cases(dataset: EscoDataset) -> list[tuple[str, str]]:
    """Yield (synonym_query, expected_code) for every documented altLabel."""
    cases: list[tuple[str, str]] = []
    for record in dataset.records:
        for key in ("altLabels_en", "altLabels_de"):
            for alt in record.get(key, []) or []:
                cases.append((str(alt), record["code"]))
    return cases


def run_benchmark(
    dataset: EscoDataset | None = None, base: Path | str | None = None
) -> BenchmarkResult:
    data = dataset if dataset is not None else load_dataset(base)
    reconciler = EscoReconciler(dataset=data)

    cases = _synonym_cases(data) + list(CURATED_CASES)
    recalled = top1 = 0
    failures: list[dict[str, Any]] = []
    for query, expected_code in cases:
        matches = reconciler.query(query).matches
        codes = [m["code"] for m in matches]
        if expected_code in codes:
            recalled += 1
            if codes and codes[0] == expected_code:
                top1 += 1
        else:
            failures.append({"query": query, "expected": expected_code, "got": codes[:3]})

    false_positives = 0
    for query in NEGATIVE_QUERIES:
        if reconciler.query(query).matches:
            false_positives += 1
            failures.append({"query": query, "expected": "<none>", "got": "non-empty"})

    return BenchmarkResult(
        dataset_version=data.version,
        total_candidates=len(data),
        synonym_cases=len(cases),
        recalled=recalled,
        top1=top1,
        negative_queries=len(NEGATIVE_QUERIES),
        false_positives=false_positives,
        failures=failures,
    )


def main() -> int:
    result = run_benchmark()
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
