# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Phase 7 — the forkable compliance fill tool (scripts/fill_template.py).

The starter kit's promise: a deployer forks the pack, writes a small JSON config,
and `fill_template` substitutes every machine-fillable {{TOKEN}} while surfacing
the descriptive [TBD: …] prompts they must still answer by hand. These tests pin:
- the example config fills the DPA template with NO unfilled {{TOKEN}} left;
- the config covers every {{TOKEN}} the DPA template declares (no silent gap);
- [TBD: …] prompts are reported, never auto-filled (they need human judgement);
- filling is deterministic + idempotent (a filled doc re-fills to itself).
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.fill_template import TOKEN_RE, fill

REPO_ROOT = Path(__file__).resolve().parent.parent
_DPA = REPO_ROOT / "compliance" / "dpa-template.md"
_FRIA = REPO_ROOT / "compliance" / "fundamental-rights-impact-assessment-template.md"
_CONFIG = REPO_ROOT / "compliance" / "starter-kit" / "example-config.json"


class FillToolContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(_CONFIG.read_text(encoding="utf-8"))
        cls.dpa = _DPA.read_text(encoding="utf-8")

    def test_example_config_is_valid_json_object(self):
        self.assertIsInstance(self.config, dict)

    def test_config_covers_every_dpa_token(self):
        tokens = set(TOKEN_RE.findall(self.dpa))
        self.assertTrue(tokens, "DPA template declares no {{TOKEN}} slots")
        missing = tokens - set(self.config)
        self.assertEqual(missing, set(), f"example config is missing DPA tokens: {missing}")

    def test_dpa_fills_with_no_unfilled_tokens(self):
        filled, unfilled, _tbd = fill(self.dpa, self.config)
        self.assertEqual(unfilled, [], f"DPA still has unfilled {{TOKEN}} slots: {unfilled}")
        # the example values actually landed in the output
        self.assertIn(str(self.config["NAME"]), filled)

    def test_fill_is_idempotent(self):
        once, _, _ = fill(self.dpa, self.config)
        twice, _, _ = fill(once, self.config)
        self.assertEqual(once, twice, "re-filling an already-filled doc changed it")


class TbdPromptsAreManualNotAutofilled(unittest.TestCase):
    def test_fria_tbd_prompts_are_surfaced_and_retained(self):
        # the FRIA template uses descriptive [TBD: deployer to fill — …] prompts
        filled, _unfilled, tbd = fill(_FRIA.read_text(encoding="utf-8"), {})
        self.assertGreaterEqual(len(tbd), 5, "expected several [TBD] deployer prompts")
        # they are reported, but left in place (never auto-filled away)
        self.assertIn("[TBD:", filled)


if __name__ == "__main__":
    unittest.main()
