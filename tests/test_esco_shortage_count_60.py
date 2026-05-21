# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 backlog #60 — pin the docs claim "25 of 30 occupations
flagged shortageDE2024" against the actual JSON count.

History: the docs originally said "21 of the 30" which was wrong
by 4 (actual count 25). This test exists so the next time a
curator adjusts the occupations dataset, any doc-drift surfaces
immediately rather than getting noticed months later by a
reviewer cross-checking the cost-saving-doctrine claim.

The test reads both the doc and the JSON and asserts the
declared count == the actual count. Updating the curated dataset
without updating the doc claim fails this test.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DOC = _REPO_ROOT / "docs" / "esco-integration.md"
_DATA = _REPO_ROOT / "reference" / "esco" / "occupations.json"


def _actual_shortage_count() -> tuple[int, int]:
    with _DATA.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        raise AssertionError(
            f"occupations.json: expected list at 'entries', got {type(entries).__name__}"
        )
    total = len(entries)
    shortage = sum(1 for o in entries if o.get("shortageDE2024") is True)
    return shortage, total


def _doc_declared_count() -> tuple[int, int] | None:
    """Parse the 'N of the M occupations' fragment from the docs.
    Returns ``(N, M)`` or ``None`` if the fragment isn't found."""

    text = _DOC.read_text(encoding="utf-8")
    # Match "**25 of the 30 occupations**" or similar
    match = re.search(
        r"\*\*(\d+)\s+of\s+the\s+(\d+)\s+occupations\*\*",
        text,
    )
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


class EscoShortageCountDocDriftGuard(unittest.TestCase):
    def test_occupations_json_loads_and_has_entries(self) -> None:
        actual, total = _actual_shortage_count()
        self.assertGreater(total, 0)
        self.assertGreaterEqual(actual, 0)
        self.assertLessEqual(actual, total)

    def test_doc_declares_a_shortage_count(self) -> None:
        declared = _doc_declared_count()
        self.assertIsNotNone(
            declared,
            "docs/esco-integration.md must contain a '**N of the M occupations**' claim — "
            "this is the drift guard's anchor",
        )

    def test_doc_count_matches_actual_json(self) -> None:
        """The integrity claim. Updating occupations.json without
        updating the doc fails here."""
        declared = _doc_declared_count()
        self.assertIsNotNone(declared)
        actual_shortage, actual_total = _actual_shortage_count()
        declared_shortage, declared_total = declared
        self.assertEqual(
            declared_shortage,
            actual_shortage,
            f"docs/esco-integration.md declares {declared_shortage} shortage occupations "
            f"but occupations.json actually has {actual_shortage}",
        )
        self.assertEqual(
            declared_total,
            actual_total,
            f"docs/esco-integration.md declares {declared_total} total occupations "
            f"but occupations.json actually has {actual_total}",
        )


if __name__ == "__main__":
    unittest.main()
