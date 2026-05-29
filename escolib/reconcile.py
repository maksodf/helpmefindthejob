# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Free-text → ESCO/ISCO concept reconciliation.

Case-insensitive substring matching against EN + DE labels and the optional
``altLabels_en`` / ``altLabels_de`` arrays, so a German colloquial query
(e.g. "Krankenschwester") resolves to its canonical code (2221.1). The output
shape is stable across the curated dataset and the embedded fallback.

Dependencies: Python standard library only. No application coupling.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from escolib.dataset import EscoDataset, load_dataset


@dataclass(frozen=True)
class ReconcileResult:
    """The result of a reconciliation query."""

    status: str
    datasetVersion: str
    totalCandidates: int
    matches: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Serialise to the stable wire shape (matches the MCP tool output)."""
        return {
            "status": self.status,
            "datasetVersion": self.datasetVersion,
            "totalCandidates": self.totalCandidates,
            "matches": self.matches,
        }


def _entry_matches(entry: dict[str, Any], lowered: str) -> bool:
    if not lowered:
        return False
    if lowered in entry.get("label_en", entry.get("label", "")).lower():
        return True
    if lowered in entry.get("label_de", "").lower():
        return True
    for alt in entry.get("altLabels_en", []) or []:
        if lowered in str(alt).lower():
            return True
    for alt in entry.get("altLabels_de", []) or []:
        if lowered in str(alt).lower():
            return True
    return False


class EscoReconciler:
    """Reconciles free text against a loaded :class:`EscoDataset`.

    Construct with an explicit ``dataset``, or let it load one (from ``base``,
    defaulting to the packaged data). The loaded dataset is held for the
    instance's lifetime; build a new instance to pick up changed data.
    """

    def __init__(
        self,
        dataset: EscoDataset | None = None,
        *,
        base: Path | str | None = None,
    ) -> None:
        self._dataset = dataset if dataset is not None else load_dataset(base)

    @property
    def dataset(self) -> EscoDataset:
        return self._dataset

    def query(
        self,
        text: str,
        *,
        kind: str | None = None,
        limit: int | None = None,
    ) -> ReconcileResult:
        """Reconcile ``text`` to matching concepts.

        ``kind`` filters to ``"occupation"`` / ``"skill"`` (``None`` / ``"any"``
        searches both). ``limit`` truncates the match list.
        """
        records = self._dataset.records
        lowered = (text or "").strip().lower()
        wanted = (kind or "any").lower()
        candidates = (entry for entry in records if wanted in ("any", entry["type"]))
        matches = [entry for entry in candidates if _entry_matches(entry, lowered)]
        if limit is not None:
            matches = matches[: max(0, int(limit))]
        return ReconcileResult(
            status="ok",
            datasetVersion=self._dataset.version,
            totalCandidates=len(records),
            matches=matches,
        )
