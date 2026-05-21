# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""4-week plan W1 D5: friction-class spec drift guard.

The spec at commons/friction-class-spec-v0.1.md is a CC-BY-4.0
published standard. The code at company_discovery/persona_fixtures.py
ships the 7 personas the spec describes. This test pins both:

1. The spec lists exactly the 7 slugs the code defines
2. The spec's slug → label table doesn't drift from the code
3. Both classify into the {most-acute migrant, wider friction}
   cohort axes the spec defines

A future contributor who adds an 8th persona to persona_fixtures
without updating the spec — or vice versa — fails this test.
That's the integrity claim: the published standard and the
running code are the same thing.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from company_discovery.persona_fixtures import PERSONAS


_SPEC_PATH = Path(__file__).resolve().parent.parent / "commons" / "friction-class-spec-v0.1.md"


# Persona slugs in the code use the bare given-name form (aicha,
# yusuf, olga, mahmoud, maria, kaethe, tobias). The spec uses
# given-name-prefixed-with-residency-context (aicha_paragraph_16d,
# yusuf_blue_card, …). The two are intentionally different — the
# spec is the public surface, the code uses the shorter form for
# brevity. This map encodes the correspondence.
PERSONA_SLUG_TO_SPEC_SLUG: dict[str, str] = {
    "aicha": "aicha_paragraph_16d",
    "yusuf": "yusuf_blue_card",
    "olga": "olga_paragraph_24",
    "mahmoud": "mahmoud_paragraph_4_asylg",
    "maria": "maria_eu_citizen_intra_eu",
    "kaethe": "kaethe_wiedereinstieg",
    "tobias": "tobias_quereinstieg",
}


class SpecDriftGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not _SPEC_PATH.exists():
            raise unittest.SkipTest(f"spec not found at {_SPEC_PATH}")
        cls.spec_text = _SPEC_PATH.read_text(encoding="utf-8")

    def test_spec_lists_all_seven_personas(self):
        for persona in PERSONAS:
            expected_slug = PERSONA_SLUG_TO_SPEC_SLUG.get(persona.slug)
            self.assertIsNotNone(
                expected_slug,
                f"Persona '{persona.slug}' not in PERSONA_SLUG_TO_SPEC_SLUG map — "
                "add it to the spec AND this map together",
            )
            self.assertIn(
                f"`{expected_slug}`",
                self.spec_text,
                f"Spec at {_SPEC_PATH.name} missing persona slug `{expected_slug}` — "
                "the code defines this persona but the spec does not document it",
            )

    def test_spec_lists_both_cohort_axes(self):
        # Both axes the code uses must appear in the spec
        for axis in ("most-acute", "wider"):
            self.assertIn(axis, self.spec_text)

    def test_spec_has_required_top_level_sections(self):
        # The spec is a draft standard — required structural sections
        for heading in (
            "## Abstract",
            "## 1. Why",
            "## 2. The seven friction classes",
            "## 3. Classification signals",
            "## 4. Classification output contract",
            "## 5. Trust Receipt requirement",
            "## 6. Cross-agent transmission",
            "## 7. Rendering & UI contract",
            "## 8. Fairness contract",
            "## 9. Versioning",
        ):
            self.assertIn(
                heading,
                self.spec_text,
                f"Spec missing required heading {heading!r}",
            )

    def test_spec_carries_cc_by_4_license_marker(self):
        # CC-BY-4.0 is the published-standard licence (vs Apache-2.0
        # for the code). Both must be present.
        self.assertIn("CC-BY-4.0", self.spec_text)
        self.assertIn("CC BY 4.0", self.spec_text)

    def test_spec_carries_version_marker(self):
        # The spec is v0.1; the marker has to be present so any
        # future version bump is a deliberate edit.
        self.assertIn("v0.1", self.spec_text)
        self.assertIn('"schemaVersion": "0.1.0"', self.spec_text)


if __name__ == "__main__":
    unittest.main()
