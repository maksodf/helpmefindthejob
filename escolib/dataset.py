# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Curated ESCO/ISCO reference dataset — loading + normalisation.

Loads occupations + skills from ``<base>/{occupations,skills}.json`` (the
packaged ``escolib/data/esco/`` by default) and normalises each entry into a
flat match record. Falls back to a small embedded mini-dataset when the JSON
files are unavailable (e.g. a packaging configuration that strips data files).

Dependencies: Python standard library only. No application coupling.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Version string reported when the embedded mini-dataset is used.
FALLBACK_VERSION = "v0-mini-fallback"

#: Version reported if a loaded dataset file omits its own ``datasetVersion``.
DATASET_VERSION_DEFAULT = "v1-curated-2026-05-18"

#: Directory of the data files shipped inside the package.
PACKAGED_DATA_DIR = Path(__file__).resolve().parent / "data" / "esco"

#: Optional metadata keys copied onto a record when present on the source entry.
_OPTIONAL_KEYS = (
    "isco",
    "category",
    "cefr",
    "personas",
    "shortageDE2024",
    "esco_uri",
    "altLabels_en",
    "altLabels_de",
)

#: Embedded 12-entry mini-dataset. Used only when the JSON files are absent.
#: Kept shape-compatible with the legacy loader so callers branching on the
#: ``label`` key continue to work.
FALLBACK_DATASET: list[dict[str, Any]] = [
    {"code": "2221.1", "label": "Registered nurse (general)", "type": "occupation", "isco": "2221"},
    {
        "code": "2221.2",
        "label": "Specialist nurse (clinical / Pflege)",
        "type": "occupation",
        "isco": "2221",
    },
    {
        "code": "5321.1",
        "label": "Healthcare assistant / Pflegehelfer",
        "type": "occupation",
        "isco": "5321",
    },
    {"code": "2144.1", "label": "Mechanical engineer", "type": "occupation", "isco": "2144"},
    {"code": "2512.1", "label": "Software developer", "type": "occupation", "isco": "2512"},
    {
        "code": "2513.1",
        "label": "Frontend developer / Web developer",
        "type": "occupation",
        "isco": "2513",
    },
    {
        "code": "7126.1",
        "label": "Plumbing trade apprentice / Anlagenmechaniker SHK",
        "type": "occupation",
        "isco": "7126",
    },
    {
        "code": "5322.1",
        "label": "Home-based personal-care worker / Häusliche Pflegehilfe",
        "type": "occupation",
        "isco": "5322",
    },
    {"code": "S1.0.1", "label": "Clinical-German communication", "type": "skill"},
    {"code": "S1.0.2", "label": "Patient documentation", "type": "skill"},
    {"code": "S5.0.1", "label": "TypeScript / React frontend development", "type": "skill"},
    {"code": "S2.0.1", "label": "Mechanical CAD (Solidworks / CATIA)", "type": "skill"},
]


@dataclass(frozen=True)
class EscoDataset:
    """A loaded, normalised ESCO/ISCO reference dataset.

    ``records`` is the flat list of match records; ``version`` is the dataset
    provenance string; ``is_fallback`` is True when the embedded mini-dataset
    was used because the JSON files were unavailable.
    """

    records: list[dict[str, Any]]
    version: str
    is_fallback: bool

    def __len__(self) -> int:
        return len(self.records)


def _normalise(entry: dict[str, Any], kind: str) -> dict[str, Any]:
    """Flatten a source JSON entry into a match record.

    ``label`` defaults to the EN label (legacy-compatible); both EN and DE
    labels remain available for locale-aware display.
    """
    record: dict[str, Any] = {
        "code": entry["code"],
        "label": entry.get("label_en") or entry.get("label") or "",
        "label_en": entry.get("label_en") or entry.get("label") or "",
        "label_de": entry.get("label_de") or "",
        "type": kind,
    }
    for key in _OPTIONAL_KEYS:
        if key in entry:
            record[key] = entry[key]
    return record


def load_dataset(base: Path | str | None = None) -> EscoDataset:
    """Load the curated ESCO dataset from ``<base>/{occupations,skills}.json``.

    ``base`` defaults to the packaged :data:`PACKAGED_DATA_DIR`. Returns the
    embedded :data:`FALLBACK_DATASET` (``is_fallback=True``) when either file
    is missing.
    """
    base_path = Path(base) if base is not None else PACKAGED_DATA_DIR
    occupations_path = base_path / "occupations.json"
    skills_path = base_path / "skills.json"
    if not occupations_path.exists() or not skills_path.exists():
        return EscoDataset(
            records=[dict(entry) for entry in FALLBACK_DATASET],
            version=FALLBACK_VERSION,
            is_fallback=True,
        )

    combined: list[dict[str, Any]] = []
    version = DATASET_VERSION_DEFAULT
    for path, kind in ((occupations_path, "occupation"), (skills_path, "skill")):
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if kind == "occupation":
            version = data.get("datasetVersion") or DATASET_VERSION_DEFAULT
        for entry in data.get("entries", []):
            combined.append(_normalise(entry, kind))

    return EscoDataset(records=combined, version=version, is_fallback=False)
