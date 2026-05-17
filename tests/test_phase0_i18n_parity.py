# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Phase 0 — i18n parity gate.

Two invariants:

1. en.json and de.json must have **the same key set**. Drift means a DE
   user will see an English fallback (or worse, a missing key) for any
   string that was added/renamed without translation.

2. Every ``data-i18n="…"`` reference in ``static/index.html`` must point
   to a key that exists in BOTH bundles.

Run as part of the regular test suite. Failures block deploy.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


I18N_DIR = REPO_ROOT / "static" / "i18n"
INDEX_HTML = REPO_ROOT / "static" / "index.html"


class I18nParityTests(unittest.TestCase):
    def test_en_and_de_have_identical_key_sets(self) -> None:
        en = set(json.loads((I18N_DIR / "en.json").read_text()))
        de = set(json.loads((I18N_DIR / "de.json").read_text()))
        only_in_en = en - de
        only_in_de = de - en
        self.assertEqual(
            only_in_en, set(),
            f"keys present in en.json but missing from de.json: {sorted(only_in_en)}",
        )
        self.assertEqual(
            only_in_de, set(),
            f"keys present in de.json but missing from en.json: {sorted(only_in_de)}",
        )

    def test_every_html_reference_resolves_in_both_bundles(self) -> None:
        en = set(json.loads((I18N_DIR / "en.json").read_text()))
        de = set(json.loads((I18N_DIR / "de.json").read_text()))
        html = INDEX_HTML.read_text()
        keys_in_html = set(re.findall(r'data-i18n="([^"]+)"', html))
        missing_en = sorted(k for k in keys_in_html if k not in en)
        missing_de = sorted(k for k in keys_in_html if k not in de)
        self.assertEqual(
            missing_en, [],
            f"data-i18n keys referenced in HTML but absent from en.json: {missing_en}",
        )
        self.assertEqual(
            missing_de, [],
            f"data-i18n keys referenced in HTML but absent from de.json: {missing_de}",
        )

    def test_no_blank_translations(self) -> None:
        for bundle in ("en.json", "de.json"):
            data = json.loads((I18N_DIR / bundle).read_text())
            blanks = [k for k, v in data.items() if not isinstance(v, str) or not v.strip()]
            self.assertEqual(
                blanks, [],
                f"{bundle} has blank or non-string values for: {blanks}",
            )


if __name__ == "__main__":
    unittest.main()
