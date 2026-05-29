# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""biasprobe — a standalone, replayable comparative bias-evaluation harness for
employment-AI systems.

It measures how different LLM providers score the *same* prompt against the
*same* panel of synthetic job-seeker personas, then surfaces per-persona means
and the cells where providers disagree most. The committed JSONL caches make
every published number reproducible offline — ``python -m biasprobe`` regenerates
the comparative report with no API keys and no network.

The package is import-isolated from the host application (stdlib only), so any
employment-AI project can lift it and supply its own personas + production
prompt via the live runner. The Helpmefindthejob live runner lives at
``scripts/bias_comparative_report.py`` (it adds the provider callers + the
production ``build_auto_fit_prompt`` seam, then delegates replay/metrics/report
back to this package).

Methodology: ``compliance/accuracy-and-bias-testing.md``.
"""

from __future__ import annotations

from pathlib import Path

from biasprobe.metrics import (
    cross_provider_disagreement,
    per_persona_mean,
    summarize,
)
from biasprobe.outcomes import (
    CallOutcome,
    append_outcome,
    cache_path,
    discover_providers,
    load_outcomes,
)
from biasprobe.report import render_markdown

#: Caches bundled with the package, so ``python -m biasprobe`` works with zero
#: configuration. Byte-identical to ``data/bias_comparative_cache/`` (pinned by
#: ``tests/test_biasprobe_standalone.py``).
DEFAULT_CACHE_DIR = Path(__file__).resolve().parent / "data"

__all__ = [
    "CallOutcome",
    "load_outcomes",
    "append_outcome",
    "cache_path",
    "discover_providers",
    "per_persona_mean",
    "cross_provider_disagreement",
    "summarize",
    "render_markdown",
    "DEFAULT_CACHE_DIR",
]
