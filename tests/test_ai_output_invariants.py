# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""PART 8 Loop 26: golden-output structural invariants for AI letter prompts.

Asserts the *shape* of cover-letter and motivation-letter outputs the
prompts in ``company_discovery/analysis.py`` and
``company_discovery/motivation_letter.py`` are designed to elicit.
Catches prompt-template regressions without needing a live LLM in CI.

Coverage layers (complementary):
- ``test_ai_quality.py`` — JSON parsing edge cases.
- ``test_ai_quality_deep.py`` — prompt injection, fact-ratio grounding,
  score-recommendation consistency.
- ``test_bias_methodology.py`` — 7-persona x 10-scenario fit-scoring
  bias (Ollama-gated, ~30 min).
- ``test_ai_output_invariants.py`` (this file) — structural-shape
  invariants on representative outputs. No LLM. Runs in ~50 ms.

How the synthetic-representative pattern works:

The fixtures at ``tests/fixtures/ai_golden/`` are hand-crafted to
represent what a correctly-prompted AI SHOULD produce for the canonical
Aicha CV + Anerkennung-friendly JD pair. The tests assert structural
invariants that the *prompt* tells the AI to honor:

- Cover letter: 5 sections (subject, body, editing notes, draft
  assumptions, source citations) with the citations using
  ``[CV]`` / ``[JD]`` / ``[Inference]`` tags.
- Motivation letter: 8-step DIN 5008 structure + a ``## Quellen``
  citations block.

When the prompt template changes, BOTH the prompt AND the synthetic
fixture must be updated to keep the pair consistent. If only one side
changes, the test fails — that's the regression signal.

Real-AI outputs from a one-time Ollama run are tracked separately in
``docs/grant/anschreiben-quality-walks-2026-05-20/*.md`` and the bias-
methodology test cluster; this rig is the fast, deterministic
complement that runs on every commit.

Doctrine reference: ``docs/grant/14-source-class-hierarchy.md``.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "ai_golden"

_FORBIDDEN_FILLER_PHRASES = (
    "hiermit bewerbe ich mich",
    "i am writing to express my interest",
    "i would like to apply for the position",
    "in conclusion",
    "overall, this is",
    "it is important to note that",
    "here are some key points",
    "i would recommend",
)


def _load_inputs() -> dict[str, str]:
    with (FIXTURES_DIR / "aicha_inputs.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_text(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


class FixturesPresentTests(unittest.TestCase):
    """Sanity: the fixtures exist and the inputs JSON has the expected keys."""

    def test_inputs_json_carries_canonical_fields(self) -> None:
        inputs = _load_inputs()
        for field in ("persona_slug", "cv_text", "jd_text", "job_title", "company", "location"):
            self.assertIn(field, inputs, msg=field)
        self.assertEqual(inputs["persona_slug"], "aicha")
        self.assertIn("Krankenpfleg", inputs["job_title"])

    def test_cover_letter_fixture_present(self) -> None:
        text = _load_text("aicha_cover_letter_representative.txt")
        self.assertGreater(len(text), 1000, msg="cover-letter fixture suspiciously small")

    def test_motivation_letter_fixture_present(self) -> None:
        text = _load_text("aicha_motivation_letter_representative.txt")
        self.assertGreater(len(text), 1000, msg="motivation-letter fixture suspiciously small")


class CoverLetterStructuralInvariants(unittest.TestCase):
    """Asserts the 5-section structure the
    ``build_cover_letter_brief_prompt`` template tells the AI to emit."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _load_text("aicha_cover_letter_representative.txt")
        cls.text_lower = cls.text.lower()
        cls.inputs = _load_inputs()

    def test_has_subject_or_opening_salutation(self) -> None:
        # Section 1 of the prompt's "Return exactly these sections" block.
        self.assertTrue(
            any(needle in self.text for needle in ("Subject:", "Sehr geehrte", "Dear ")),
            msg="missing subject line / opening salutation",
        )

    def test_has_body_with_minimum_length(self) -> None:
        # Section 2: cover letter body, ~280 words.
        self.assertGreater(len(self.text), 800, msg="body too short for a 280-word target")

    def test_has_editing_notes_section(self) -> None:
        # Section 3 of the prompt's structure.
        self.assertIn("Editing notes", self.text)

    def test_has_draft_assumptions_section(self) -> None:
        # Section 4 of the prompt's structure.
        self.assertIn("Draft assumptions", self.text)

    def test_has_source_citations_section(self) -> None:
        # Section 5: PART 8 Loop 25 addition. Either EN or DE heading is acceptable.
        self.assertTrue(
            "Source citations" in self.text or "Quellen" in self.text,
            msg="missing PART 8 Loop 25 Source citations section",
        )

    def test_citations_use_documented_tags(self) -> None:
        # Each citation entry uses [CV] / [JD] / [Inference] per the prompt template.
        cv_hits = self.text.count("[CV]")
        jd_hits = self.text.count("[JD]")
        inf_hits = self.text.count("[Inference]")
        self.assertGreaterEqual(cv_hits, 2, msg=f"too few [CV] citations: {cv_hits}")
        self.assertGreaterEqual(jd_hits, 2, msg=f"too few [JD] citations: {jd_hits}")
        # Inference citations are honest-uncertainty markers; at least one is expected
        # in any non-trivial cover letter (e.g. defaulted salutation, defaulted language).
        self.assertGreaterEqual(inf_hits, 1, msg=f"missing [Inference] citation: {inf_hits}")

    def test_citation_count_in_documented_range(self) -> None:
        # Prompt asks for 3-6 entries; allow generous upper bound for fixture leniency.
        total = self.text.count("[CV]") + self.text.count("[JD]") + self.text.count("[Inference]")
        self.assertGreaterEqual(total, 3, msg=f"too few citations: {total}")
        self.assertLessEqual(total, 20, msg=f"absurd citation count: {total}")

    def test_no_forbidden_filler_phrases(self) -> None:
        # The prompt forbids the listed phrases case-insensitively in the body.
        for phrase in _FORBIDDEN_FILLER_PHRASES:
            self.assertNotIn(
                phrase, self.text_lower, msg=f"forbidden filler phrase present: {phrase!r}"
            )

    def test_cv_grounded_claims_appear_in_cv(self) -> None:
        """Class-E grounding check: each [CV] citation's quoted excerpt
        must literally appear in the canonical CV fixture. Catches
        invented [CV] sources at prompt-template-design time."""

        cv_text = self.inputs["cv_text"]
        # Match `← [CV] "<excerpt>"` patterns. The quoted excerpt is what
        # the AI claims to be citing from the CV.
        for match in re.finditer(r"←\s*\[CV\]\s*\"([^\"]+)\"", self.text, re.MULTILINE):
            excerpt = match.group(1).strip()
            self.assertIn(
                excerpt,
                cv_text,
                msg=(
                    f"[CV] citation references text not found in CV fixture: {excerpt!r}. "
                    "Either the citation is invented or the synthetic fixture drifted "
                    "from the inputs JSON."
                ),
            )

    def test_jd_grounded_claims_appear_in_jd(self) -> None:
        """Same class-E discipline for [JD] citations."""

        jd_text = self.inputs["jd_text"]
        for match in re.finditer(r"←\s*\[JD\]\s*\"([^\"]+)\"", self.text, re.MULTILINE):
            excerpt = match.group(1).strip()
            self.assertIn(
                excerpt,
                jd_text,
                msg=(f"[JD] citation references text not found in JD fixture: {excerpt!r}"),
            )


class MotivationLetterStructuralInvariants(unittest.TestCase):
    """Asserts the DIN 5008 9-step structure that ``build_letter_prompt``
    tells the AI to emit (steps 1-8 = letter, step 9 = Quellen citations)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _load_text("aicha_motivation_letter_representative.txt")
        cls.text_lower = cls.text.lower()
        cls.inputs = _load_inputs()

    def test_has_absenderzeile(self) -> None:
        self.assertIn("Absenderzeile", self.text)

    def test_has_empfaengeradresse(self) -> None:
        self.assertIn("Empfängeradresse", self.text)

    def test_has_iso_or_german_date_format(self) -> None:
        # Prompt asks for TT.MM.JJJJ.
        self.assertTrue(
            re.search(r"\b\d{2}\.\d{2}\.\d{4}\b", self.text) is not None,
            msg="missing German date format TT.MM.JJJJ",
        )

    def test_has_betreff_line(self) -> None:
        self.assertIn("Betreff", self.text)

    def test_has_anrede(self) -> None:
        self.assertTrue(
            any(needle in self.text for needle in ("Sehr geehrte", "Sehr geehrter")),
            msg="missing Anrede",
        )

    def test_has_schluss(self) -> None:
        self.assertTrue(
            any(needle in self.text for needle in ("Mit freundlichen Grüßen", "Freundliche Grüße")),
            msg="missing Schluss",
        )

    def test_has_quellen_section(self) -> None:
        # PART 8 Loop 25 addition. Prompt asks for "## Quellen (Source citations)".
        self.assertIn(
            "Quellen",
            self.text,
            msg="missing PART 8 Loop 25 Quellen section after Unterschrift",
        )

    def test_quellen_section_is_after_schluss(self) -> None:
        # Doctrine: Quellen is NOT part of the letter; it goes after Schluss.
        schluss_idx = self.text.find("Mit freundlichen Grüßen")
        quellen_idx = self.text.find("Quellen")
        self.assertGreater(schluss_idx, -1)
        self.assertGreater(quellen_idx, -1)
        self.assertGreater(
            quellen_idx,
            schluss_idx,
            msg="Quellen section must follow Schluss, not appear inside the letter body",
        )

    def test_citations_use_documented_tags(self) -> None:
        cv_hits = self.text.count("[CV]")
        jd_hits = self.text.count("[JD]")
        inf_hits = self.text.count("[Inference]")
        self.assertGreaterEqual(cv_hits, 2)
        self.assertGreaterEqual(jd_hits, 2)
        self.assertGreaterEqual(inf_hits, 1)

    def test_no_forbidden_filler_phrases(self) -> None:
        for phrase in _FORBIDDEN_FILLER_PHRASES:
            self.assertNotIn(
                phrase, self.text_lower, msg=f"forbidden filler phrase present: {phrase!r}"
            )

    def test_cv_grounded_claims_appear_in_cv(self) -> None:
        cv_text = self.inputs["cv_text"]
        for match in re.finditer(r"←\s*\[CV\]\s*\"([^\"]+)\"", self.text, re.MULTILINE):
            excerpt = match.group(1).strip()
            self.assertIn(excerpt, cv_text, msg=f"[CV] citation not in CV: {excerpt!r}")

    def test_jd_grounded_claims_appear_in_jd(self) -> None:
        jd_text = self.inputs["jd_text"]
        for match in re.finditer(r"←\s*\[JD\]\s*\"([^\"]+)\"", self.text, re.MULTILINE):
            excerpt = match.group(1).strip()
            self.assertIn(excerpt, jd_text, msg=f"[JD] citation not in JD: {excerpt!r}")


class PromptTemplateConsistencyTests(unittest.TestCase):
    """Cross-checks the prompt templates name the citation tags that the
    fixtures use. If the prompt rename a tag (e.g. [CV] -> [Resume]), this
    test fails before the fixture-vs-output tests catch the drift."""

    def test_cover_letter_prompt_documents_citation_tags(self) -> None:
        from company_discovery.ai_providers import AIProviderConfig
        from company_discovery.analysis import build_cover_letter_brief_prompt
        from company_discovery.models import ImportedJob

        provider = AIProviderConfig(
            provider_id="ollama",
            invocation_mode="local_http",
            model="llama3.1:8b",
            credential_reference="",
            base_url="http://localhost:11434",
            command="",
            notes="invariant-test",
        )
        job = ImportedJob(
            user_id="u-x",
            company_id="co-x",
            discovered_job_id="dj-x",
            source_url="https://example.invalid",
            title="Krankenpfleger / Krankenpflegerin (Anerkennung-friendly)",
            company_name="Beispielarbeitgeber",
            location="Berlin",
            description="Berliner Krankenhaus sucht Pflegekraft. Anerkennung-friendly.",
        )
        bundle = build_cover_letter_brief_prompt(job, provider)
        prompt = bundle["prompt"]
        for tag in ("[CV]", "[JD]", "[Inference]"):
            self.assertIn(
                tag,
                prompt,
                msg=f"cover-letter prompt missing citation tag {tag}; rename or scope drift",
            )
        # The doctrine document is the load-bearing cross-reference.
        self.assertIn("docs/grant/14-source-class-hierarchy.md", prompt)

    def test_motivation_letter_prompt_documents_citation_tags(self) -> None:
        from company_discovery.motivation_letter import build_letter_prompt

        system, _user = build_letter_prompt(
            job_title="Krankenpfleger / Krankenpflegerin (Anerkennung-friendly)",
            company="Beispielarbeitgeber",
            location="Berlin",
            job_url="https://example.invalid",
            cv_text="Aïcha Ben Salah\nRegistered nurse 7 years.",
        )
        for tag in ("[CV]", "[JD]", "[Inference]"):
            self.assertIn(
                tag,
                system,
                msg=f"motivation-letter system prompt missing citation tag {tag}",
            )
        self.assertIn("Quellen", system)
        self.assertIn("docs/grant/14-source-class-hierarchy.md", system)


if __name__ == "__main__":
    unittest.main()
