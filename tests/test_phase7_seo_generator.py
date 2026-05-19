# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""SEO content cadence (Phase 7 tracker item #62).

The generator script ``scripts/generate-seo-pages.py`` fans out a
small operator-edited config (cities + roles) into a 200-entry
``seo-pages.json``. Re-running with the same input is a no-op
(de-dupe by slug). Engineering side of the page-render is already
tested by ``tests/test_phase1_seo_pages.py`` (#17).
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_seo_pages",
        REPO_ROOT / "scripts" / "generate-seo-pages.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FanOutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load_generator()

    def test_full_cross_product(self) -> None:
        payload = {
            "cities": [
                {"slug": "berlin", "label": "Berlin"},
                {"slug": "munich", "label": "Munich"},
            ],
            "roles": [
                {"slug": "data-engineer", "label": "Data engineer"},
                {"slug": "pm", "label": "PM"},
            ],
        }
        pages = self.module.fan_out(payload)
        self.assertEqual(len(pages), 4)  # 2 cities × 2 roles
        slugs = {p["slug"] for p in pages}
        self.assertEqual(
            slugs,
            {"data-engineer-berlin", "data-engineer-munich", "pm-berlin", "pm-munich"},
        )

    def test_intro_template_substitution(self) -> None:
        payload = {
            "cities": [{"slug": "berlin", "label": "Berlin"}],
            "roles": [{"slug": "de", "label": "Data engineer"}],
            "intro_template": "Hi {role} in {city}.",
        }
        pages = self.module.fan_out(payload)
        self.assertEqual(pages[0]["intro"], "Hi Data engineer in Berlin.")

    def test_dedup_on_slug(self) -> None:
        payload = {
            "cities": [
                {"slug": "berlin", "label": "Berlin"},
                {"slug": "berlin", "label": "Berlin"},  # duplicate
            ],
            "roles": [{"slug": "de", "label": "Data engineer"}],
        }
        pages = self.module.fan_out(payload)
        self.assertEqual(len(pages), 1)

    def test_invalid_entries_skipped(self) -> None:
        payload = {
            "cities": [
                {"slug": "berlin", "label": "Berlin"},
                {"slug": "", "label": "no slug"},  # filtered
                {"slug": "munich"},  # filtered (no label)
                "not a dict",  # filtered
            ],
            "roles": [{"slug": "de", "label": "Data engineer"}],
        }
        pages = self.module.fan_out(payload)
        self.assertEqual([p["slug"] for p in pages], ["de-berlin"])

    def test_default_template_used_when_missing(self) -> None:
        payload = {
            "cities": [{"slug": "berlin", "label": "Berlin"}],
            "roles": [{"slug": "de", "label": "Data engineer"}],
        }
        pages = self.module.fan_out(payload)
        # Default template references the role and city.
        self.assertIn("Data engineer", pages[0]["intro"])
        self.assertIn("Berlin", pages[0]["intro"])

    def test_shipped_input_yields_200_pages(self) -> None:
        # Spec target: 10 cities × 20 roles = 200 pages. The shipped
        # input JSON is sized to exactly that target.
        import json

        path = REPO_ROOT / "deploy" / "seo-pages-input.json.example"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(self.module.fan_out(payload)), 200)


if __name__ == "__main__":
    unittest.main()
