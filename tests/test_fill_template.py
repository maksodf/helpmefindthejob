# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Phase 7 — the forkable compliance fill tool (scripts/fill_template.py).

The starter kit's promise: a deployer forks the pack, writes a JSON config, and
`fill_template` substitutes EVERY machine-fillable {{...}} slot — whatever its
spacing or case — while surfacing the descriptive [TBD: …] prompts they must
answer by hand. These tests pin that, and specifically guard the regression a
review caught: a slot with spaces / a line wrap (e.g. `{{DEPLOYER NAME}}`) must
NOT be silently skipped, leaving --strict to pass on a half-filled legal doc.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.fill_template import TOKEN_RE, _normalise_key, fill

REPO_ROOT = Path(__file__).resolve().parent.parent
_DPA = REPO_ROOT / "compliance" / "dpa-template.md"
_FRIA = REPO_ROOT / "compliance" / "fundamental-rights-impact-assessment-template.md"
_CONFIG = REPO_ROOT / "compliance" / "starter-kit" / "example-config.json"


class KeyNormalisation(unittest.TestCase):
    def test_spacing_case_and_linewrap_fold_to_one_key(self):
        self.assertEqual(_normalise_key("DEPLOYER NAME"), "DEPLOYER_NAME")
        self.assertEqual(_normalise_key("DEPLOYER\nNAME"), "DEPLOYER_NAME")
        self.assertEqual(_normalise_key("deployer-name"), "DEPLOYER_NAME")
        self.assertEqual(_normalise_key("SUB-PROCESSOR REGISTRY URL"), "SUB_PROCESSOR_REGISTRY_URL")


class FillToolContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(_CONFIG.read_text(encoding="utf-8"))
        cls.dpa = _DPA.read_text(encoding="utf-8")
        cls.slots = {_normalise_key(b) for b in TOKEN_RE.findall(cls.dpa)}

    def test_example_config_is_valid_json_object(self):
        self.assertIsInstance(self.config, dict)

    def test_config_covers_every_dpa_slot(self):
        self.assertTrue(self.slots, "DPA template declares no {{...}} slots")
        config_keys = {k for k in self.config if not k.startswith("_")}
        missing = self.slots - config_keys
        self.assertEqual(missing, set(), f"example config is missing DPA slots: {missing}")

    def test_dpa_fills_completely_with_no_residual_placeholder(self):
        filled, unfilled, _tbd = fill(self.dpa, self.config)
        self.assertEqual(unfilled, [], f"DPA still has unfilled slots: {unfilled}")
        # the regression guard the review asked for: NOT just "no TOKEN_RE match"
        # (the old false-confidence check) but no residual double-brace at all.
        self.assertNotIn("{{", filled, "a {{...}} placeholder survived a full fill")
        self.assertIn(str(self.config["DEPLOYER_NAME"]), filled)

    def test_strict_fails_on_an_incomplete_config(self):
        # the core bug: a half-filled DPA must be REPORTED, not silently passed.
        filled, unfilled, _tbd = fill(self.dpa, {"NAME": "x"})
        self.assertIn("DEPLOYER_NAME", unfilled, "an unfilled body slot was not reported")
        self.assertIn("CONTROLLER_NAME", unfilled)
        self.assertIn("{{", filled, "unfilled slots must remain visible in the output")

    def test_fill_is_idempotent(self):
        once, _, _ = fill(self.dpa, self.config)
        twice, _, _ = fill(once, self.config)
        self.assertEqual(once, twice, "re-filling an already-filled doc changed it")


class TbdPromptsAreManualNotAutofilled(unittest.TestCase):
    def test_fria_tbd_prompts_are_surfaced_and_retained(self):
        filled, _unfilled, tbd = fill(_FRIA.read_text(encoding="utf-8"), {})
        self.assertGreaterEqual(len(tbd), 5, "expected several [TBD] deployer prompts")
        self.assertIn("[TBD:", filled)


if __name__ == "__main__":
    unittest.main()
