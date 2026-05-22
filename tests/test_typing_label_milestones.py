# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""PART 9 Loop 28 — milestone-shape contract for TYPING_LABELS.

PART 6 Loop 14.1 introduced a flat string label per long-op category;
PART 9 Loop 28 reshaped each value to a milestone array
``[{after: <ms>, text: "..."}, ...]`` so the typing bubble can rotate
during the wait.

This test asserts the contract in `static/app.js`:

- TYPING_LABELS is a JS object with one key per long-op category
- Each value is an array of >= 1 milestone object
- Each milestone has integer ``after`` (ms) and non-empty ``text``
- ``after`` values are monotonically non-decreasing within an array
- First milestone has ``after: 0`` (initial label, displayed immediately)
- Browser-level rotation verification is performed by the Playwright
  smoke (tests/e2e/typing_label_smoke.py); this file is the fast,
  no-browser contract layer that catches refactor regressions.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

APP_JS = Path(__file__).resolve().parent.parent / "static" / "app.js"


def _extract_typing_labels() -> dict[str, list[dict[str, object]]]:
    """Pull the TYPING_LABELS_SCHEDULE literal out of static/app.js
    and return the parsed value. Uses a regex anchor + brace-balance
    walk so the parser stays robust against unrelated edits elsewhere
    in the file.

    The schedule was renamed from ``TYPING_LABELS`` to
    ``TYPING_LABELS_SCHEDULE`` in phase2-backlog #75 wiring (the
    runtime ``TYPING_LABELS`` is now a Proxy that resolves keys via
    the i18n bundle). The new entry shape carries ``key`` +
    ``fallback`` instead of ``text``; this extractor normalises
    ``fallback`` back to ``text`` so the downstream assertions
    don't need to change."""

    text = APP_JS.read_text(encoding="utf-8")
    anchor = re.search(r"const TYPING_LABELS_SCHEDULE\s*=\s*\{", text)
    assert anchor is not None, "TYPING_LABELS_SCHEDULE literal not found in app.js"
    start = anchor.end() - 1  # the opening "{"
    depth = 0
    end = None
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    assert end is not None, "TYPING_LABELS literal is not brace-balanced"
    literal = text[start:end]
    # Convert JS-ish object literal -> JSON. Bare keys appear after
    # "{", ",", or at the start of a line. Quote any bare key that
    # is followed by ":" (but not "::" or "://" — those are values
    # like URLs).
    json_text = re.sub(
        r"(^|[\{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*):(?!/)",
        r'\1"\2"\3:',
        literal,
        flags=re.MULTILINE,
    )
    # Strip trailing commas before } or ] (legal JS, illegal JSON).
    json_text = re.sub(r",(\s*[\]}])", r"\1", json_text)
    parsed = json.loads(json_text)
    # Normalise the new entry shape: rename `fallback` → `text` so
    # downstream assertions can stay shape-agnostic. The substantive
    # contract (first stage after=0, monotonic, ≥2 stages for long-
    # ops) is independent of which key holds the EN string.
    for category, stages in parsed.items():
        if not isinstance(stages, list):
            continue
        for stage in stages:
            if isinstance(stage, dict) and "fallback" in stage and "text" not in stage:
                stage["text"] = stage["fallback"]
    return parsed


class TypingLabelMilestoneContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.labels = _extract_typing_labels()

    def test_has_default_plus_known_categories(self) -> None:
        # default is the catch-all; the others are PART 6 Loop 14.1
        # long-op surfaces (search/tailor/letter/consult/inspire).
        for required in ("default", "search", "tailor", "letter", "consult", "inspire"):
            self.assertIn(required, self.labels, msg=f"missing label category: {required}")

    def test_every_value_is_milestone_array(self) -> None:
        for name, milestones in self.labels.items():
            with self.subTest(label=name):
                self.assertIsInstance(milestones, list, msg=f"{name}: not an array")
                self.assertGreater(len(milestones), 0, msg=f"{name}: empty array")
                for stage in milestones:
                    self.assertIsInstance(stage, dict, msg=f"{name}: stage not a dict")
                    self.assertIn("after", stage, msg=f"{name}: stage missing 'after'")
                    self.assertIn("text", stage, msg=f"{name}: stage missing 'text'")
                    self.assertIsInstance(stage["after"], int, msg=f"{name}: 'after' not int")
                    self.assertIsInstance(stage["text"], str, msg=f"{name}: 'text' not str")
                    self.assertGreater(len(stage["text"].strip()), 0, msg=f"{name}: empty text")

    def test_first_milestone_after_is_zero(self) -> None:
        # The initial label must display immediately; later milestones
        # rotate via setTimeout in chatAppendBubble.
        for name, milestones in self.labels.items():
            with self.subTest(label=name):
                self.assertEqual(
                    milestones[0]["after"],
                    0,
                    msg=f"{name}: first milestone must have after=0, got {milestones[0]['after']}",
                )

    def test_after_values_monotonically_increase(self) -> None:
        for name, milestones in self.labels.items():
            with self.subTest(label=name):
                previous = -1
                for i, stage in enumerate(milestones):
                    self.assertGreater(
                        stage["after"],
                        previous,
                        msg=(
                            f"{name}: stage {i} after={stage['after']} must be "
                            f"strictly greater than previous {previous}"
                        ),
                    )
                    previous = stage["after"]

    def test_long_op_categories_have_at_least_two_milestones(self) -> None:
        # search / tailor / letter / consult are >=2s ops (PART 6 Loop
        # 14 audit). Their milestone array MUST rotate at least once
        # so the bubble doesn't appear frozen for the full wait.
        for required in ("search", "tailor", "letter", "consult", "inspire"):
            with self.subTest(label=required):
                self.assertGreaterEqual(
                    len(self.labels[required]),
                    2,
                    msg=(
                        f"{required}: long-op category must have >=2 milestones; "
                        f"a single stage defeats the point of the rotation refactor"
                    ),
                )

    def test_text_contains_no_xss_payload(self) -> None:
        # Defence in depth: textContent is XSS-safe regardless, but
        # the label strings should never contain HTML tags or script
        # constructs that might accidentally render via innerHTML in
        # a future refactor.
        for name, milestones in self.labels.items():
            with self.subTest(label=name):
                for stage in milestones:
                    text = stage["text"]
                    self.assertNotIn("<script", text.lower(), msg=name)
                    self.assertNotIn("javascript:", text.lower(), msg=name)
                    self.assertNotIn("<img", text.lower(), msg=name)


if __name__ == "__main__":
    unittest.main()
