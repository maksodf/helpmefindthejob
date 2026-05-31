# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""escolib — standalone ESCO/ISCO occupation + skill reconciliation.

A small, dependency-free library that reconciles free text to ESCO/ISCO
concepts against a curated, CC-BY-4.0 dataset (ISCO-08 / ESCO v1.1), with
EN/DE label + altLabels matching and dataset-version provenance.

It has **zero dependency on any application code** — any civic-tech project
(housing, training-matching, benefits) can vendor or install it and reuse the
reconciliation without pulling in Helpmefindthejob. Helpmefindthejob's own
``query_esco_skill`` MCP tool is a thin adapter over this library.

    >>> from escolib import EscoReconciler
    >>> EscoReconciler().query("Krankenschwester", limit=1).matches[0]["code"]
    '2221.1'

Or from the command line::

    python -m escolib "Krankenschwester"
    python -m escolib "frontend" --type occupation --limit 3

Dataset provenance: the bundled occupations + skills are a persona-aligned
curated subset of ISCO-08 / ESCO v1.1, redistributed under CC-BY-4.0; see
``escolib/data/esco/*.json`` for the full attribution headers.
"""

from __future__ import annotations

from escolib.dataset import (
    DATASET_VERSION_DEFAULT,
    FALLBACK_DATASET,
    FALLBACK_VERSION,
    EscoDataset,
    load_dataset,
)
from escolib.reconcile import EscoReconciler, ReconcileResult

__all__ = [
    "EscoReconciler",
    "ReconcileResult",
    "EscoDataset",
    "load_dataset",
    "FALLBACK_DATASET",
    "FALLBACK_VERSION",
    "DATASET_VERSION_DEFAULT",
]

__version__ = "0.1.0"
