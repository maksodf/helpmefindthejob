# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""PART 5 gate 4.2 — generic-prose regression check.

Operator gate (2026-05-20):

    Generic-filler grep over persona-panel outputs returns 0 hits

    Patterns to grep (case-insensitive, language-aware):
        "I would recommend", "Here are some key points",
        "Hiermit bewerbe ich mich", "It is important to note that",
        "In conclusion", "Overall, this is",
        "I am writing to express my interest"

    Add the grep as a regression check alongside bias-methodology.

This module loads the most-recent dated bias-methodology sidecar
JSON from ``docs/grant/`` and asserts that none of the captured
``raw_output_head`` fields contain any of the forbidden filler
patterns.

Skip-policy: if no bias-methodology sidecar is present (test
infrastructure not run yet), the test skips with a clear reason.
The bias-methodology test itself is opt-in (``HELPMEFINDTHEJOB_RUN_BIAS_METHODOLOGY=1``),
so a fast unit-test run on a fresh clone will skip this check too —
that's the intended behaviour. The regression check guards against
prompts that introduce filler into a real run's captured outputs.

The 8-phrase forbidden list mirrors what's in the prompt builders'
"Forbidden filler phrases" guidance (analysis.py and
motivation_letter.py). When the prompt forbids the model from
emitting these phrases, this test verifies the model honoured the
prompt across the cohort.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


# Patterns the operator listed at PART 5 release (2026-05-20).
# Order matches the operator's wording for traceability.
_FORBIDDEN_PATTERNS: tuple[str, ...] = (
    "I would recommend",
    "Here are some key points",
    "Hiermit bewerbe ich mich",
    "It is important to note that",
    "In conclusion",
    "Overall, this is",
    "I am writing to express my interest",
    # Added by PART 5 prompt-builder edits (same scope, additional
    # generic-application markers caught across the four prompts):
    "I would like to apply for the position",
)


def _latest_bias_sidecar() -> Path | None:
    """Locate the most-recent dated bias-methodology sidecar JSON.

    The bias-methodology test writes its sidecar to
    ``docs/grant/bias-testing-<YYYY-MM-DD>-data.json`` (the date is
    local-time at tear-down; see ``tests/test_bias_methodology.py``
    ``tearDownClass``). Earlier dated runs may also be present
    (broadened, polish, pre-wiring suffixes). We pick the most-recent
    plain-date file first; if absent, fall back to any sidecar
    matching the glob.
    """
    grant_dir = Path(__file__).resolve().parent.parent / "docs" / "grant"
    if not grant_dir.is_dir():
        return None
    candidates = sorted(grant_dir.glob("bias-testing-*-data.json"))
    if not candidates:
        return None
    # Prefer the plain bias-testing-YYYY-MM-DD-data.json over the
    # variant-suffixed ones (broadened, polish, pre-wiring).
    plain = [
        p for p in candidates
        if re.fullmatch(r"bias-testing-\d{4}-\d{2}-\d{2}-data\.json", p.name)
    ]
    if plain:
        return plain[-1]
    return candidates[-1]


def _iter_captured_text(sidecar: dict) -> list[tuple[str, str, str]]:
    """Yield ``(persona, scenario, raw_output_head)`` triples from a
    bias-methodology sidecar. Pulls from both scoring_results and
    cv_tailoring_results so the regression check covers both prompt
    paths the sidecar captures."""

    out: list[tuple[str, str, str]] = []
    for r in sidecar.get("scoring_results", []) or []:
        head = r.get("raw_output_head") or ""
        if head:
            out.append(
                (r.get("persona_slug", "?"), r.get("scenario_label", "?"), head)
            )
    for r in sidecar.get("cv_tailoring_results", []) or []:
        head = r.get("raw_output_head") or ""
        if head:
            out.append(
                (r.get("persona_slug", "?"), r.get("scenario_label", "?"), head)
            )
    return out


class GenericProseGuard(unittest.TestCase):
    """PART 5 gate 4.2 regression check."""

    def setUp(self) -> None:
        self.sidecar_path = _latest_bias_sidecar()
        if self.sidecar_path is None:
            self.skipTest(
                "No bias-methodology sidecar JSON present. Run "
                "`HELPMEFINDTHEJOB_RUN_BIAS_METHODOLOGY=1 python -m "
                "unittest tests.test_bias_methodology -v` first."
            )

    def test_no_forbidden_filler_in_captured_outputs(self) -> None:
        """Operator's PART 5 gate 4.2: zero forbidden-filler hits across
        all captured raw_output_head fields in the latest dated
        bias-methodology sidecar.

        Failures list every offending (persona, scenario, pattern,
        snippet) so the failure surface is honest and actionable.
        Tolerance is zero — no widening to make this pass. If
        failures appear, the corresponding prompt's forbidden-filler
        list needs to be tightened or the model's adherence
        investigated.
        """
        with self.sidecar_path.open("r", encoding="utf-8") as h:
            sidecar = json.load(h)
        triples = _iter_captured_text(sidecar)
        if not triples:
            self.skipTest(
                f"Sidecar {self.sidecar_path.name} contains no captured "
                "raw_output_head fields — skip rather than false-pass."
            )

        hits: list[str] = []
        for persona, scenario, head in triples:
            head_lower = head.lower()
            for pattern in _FORBIDDEN_PATTERNS:
                if pattern.lower() in head_lower:
                    # Extract a short snippet around the match for the
                    # failure message — helps the maintainer see WHY
                    # the pattern matched (model output may be ambiguous).
                    idx = head_lower.find(pattern.lower())
                    start = max(0, idx - 20)
                    end = min(len(head), idx + len(pattern) + 40)
                    snippet = head[start:end].replace("\n", "  ")
                    hits.append(
                        f"  {persona}/{scenario}: pattern '{pattern}'"
                        f" -> '...{snippet}...'"
                    )

        if hits:
            self.fail(
                f"PART 5 gate 4.2 failure: {len(hits)} forbidden-filler "
                f"hit(s) in {self.sidecar_path.name}:\n"
                + "\n".join(hits)
                + "\n\nDo NOT widen the forbidden-filler list to make "
                "this pass. Tighten the production prompt's guidance "
                "so the model stops emitting these patterns, OR investigate "
                "why model adherence dropped."
            )


if __name__ == "__main__":
    unittest.main()
