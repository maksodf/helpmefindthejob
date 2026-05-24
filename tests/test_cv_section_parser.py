# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""CV section parser contract (phase2-backlog #3 — sectional
parsing portion).

PDF / DOCX / TXT extraction already exists at
``company_discovery/cv_extract.py``. The remaining gap from the
original 40-item list was "structured CV parsing" — extracting
the raw text isn't enough; the SPA wants to render the CV as
discrete sections (summary / experience / education / skills /
languages / certifications / projects) AND downstream features
(persona auto-routing, fit-score keyword extraction, tailored-
CV generation) want to know which bullets are which.

LinkedIn auto-import remains operator-blocked (requires LinkedIn
Developer Program OAuth credentials).

Tests pin:
1. Header recognition (EN + DE for every supported section)
2. Mixed-language CV handling (DACH-common: DE headers + EN body)
3. Preamble fallback (name + contact lines before any header)
4. Robustness: empty / None / very-long-line / no-header inputs
5. Detected-headers passthrough (UI shows the user how the CV was
   read)
6. Cv-upload endpoint includes parsedCv in response (source-level)
7. GET /api/profile/cv/structured returns the parsed view
"""

from __future__ import annotations

import unittest
from pathlib import Path

from company_discovery.cv_section_parser import (
    ALL_SECTIONS,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_LANGUAGES,
    SECTION_PREAMBLE,
    SECTION_PROJECTS,
    SECTION_SKILLS,
    SECTION_SUMMARY,
    ParsedCv,
    parse_sections,
)

# ---------------------------------------------------------------------------
# Header recognition — English headers
# ---------------------------------------------------------------------------


class EnglishHeaderRecognition(unittest.TestCase):
    def test_professional_summary(self):
        cv = "PROFESSIONAL SUMMARY\nExperienced engineer."
        parsed = parse_sections(cv)
        self.assertIn(SECTION_SUMMARY, parsed.sections)
        self.assertIn("Experienced engineer.", parsed.sections[SECTION_SUMMARY])

    def test_experience_variants(self):
        for header in (
            "Experience",
            "Work Experience",
            "Professional Experience",
            "Employment",
            "Employment History",
            "Career History",
        ):
            with self.subTest(header=header):
                cv = f"{header}\n2020-2024 Acme Corp"
                parsed = parse_sections(cv)
                self.assertIn(SECTION_EXPERIENCE, parsed.sections)

    def test_education_variants(self):
        for header in (
            "Education",
            "Academic Background",
            "Qualifications",
        ):
            with self.subTest(header=header):
                cv = f"{header}\nMSc Computer Science"
                parsed = parse_sections(cv)
                self.assertIn(SECTION_EDUCATION, parsed.sections)

    def test_skills_variants(self):
        for header in (
            "Skills",
            "Skills & Tools",
            "Technical Skills",
            "Core Competencies",
            "Expertise",
        ):
            with self.subTest(header=header):
                cv = f"{header}\nPython, SQL, Docker"
                parsed = parse_sections(cv)
                self.assertIn(SECTION_SKILLS, parsed.sections)

    def test_languages_recognized(self):
        cv = "Languages\nEnglish (native), German (B2)"
        parsed = parse_sections(cv)
        self.assertIn(SECTION_LANGUAGES, parsed.sections)

    def test_certifications_recognized(self):
        cv = "Certifications\nAWS Solutions Architect (2024)"
        parsed = parse_sections(cv)
        self.assertIn(SECTION_CERTIFICATIONS, parsed.sections)

    def test_projects_recognized(self):
        cv = "Projects\nOpen-source CLI tool with 500 stars"
        parsed = parse_sections(cv)
        self.assertIn(SECTION_PROJECTS, parsed.sections)


# ---------------------------------------------------------------------------
# Header recognition — German headers
# ---------------------------------------------------------------------------


class GermanHeaderRecognition(unittest.TestCase):
    def test_zusammenfassung_summary(self):
        cv = "Zusammenfassung\nErfahrene Software-Ingenieurin."
        parsed = parse_sections(cv)
        self.assertIn(SECTION_SUMMARY, parsed.sections)

    def test_berufserfahrung_experience(self):
        cv = "Berufserfahrung\n2020-2024 Acme GmbH"
        parsed = parse_sections(cv)
        self.assertIn(SECTION_EXPERIENCE, parsed.sections)

    def test_beruflicher_werdegang_experience(self):
        cv = "Beruflicher Werdegang\nAcme GmbH 2020-2024"
        parsed = parse_sections(cv)
        self.assertIn(SECTION_EXPERIENCE, parsed.sections)

    def test_ausbildung_education(self):
        cv = "Ausbildung\nM.Sc. Informatik, TU Berlin"
        parsed = parse_sections(cv)
        self.assertIn(SECTION_EDUCATION, parsed.sections)

    def test_kompetenzen_skills(self):
        cv = "Kompetenzen\nPython, SQL, Docker"
        parsed = parse_sections(cv)
        self.assertIn(SECTION_SKILLS, parsed.sections)

    def test_sprachen_languages(self):
        cv = "Sprachen\nDeutsch (Muttersprache), Englisch (C1)"
        parsed = parse_sections(cv)
        self.assertIn(SECTION_LANGUAGES, parsed.sections)

    def test_zertifikate_certifications(self):
        cv = "Zertifikate\nScrum Master (2023)"
        parsed = parse_sections(cv)
        self.assertIn(SECTION_CERTIFICATIONS, parsed.sections)

    def test_projekte_projects(self):
        cv = "Projekte\nOpen-Source CLI-Tool"
        parsed = parse_sections(cv)
        self.assertIn(SECTION_PROJECTS, parsed.sections)


# ---------------------------------------------------------------------------
# DACH-common: mixed-language CVs
# ---------------------------------------------------------------------------


class MixedLanguageCv(unittest.TestCase):
    """Common DACH pattern: German section headers + English body
    (or vice versa). Parser must recognise BOTH languages'
    headers in the same document."""

    def test_german_headers_english_body(self):
        cv = (
            "Berufserfahrung\n"
            "2020-2024 Senior Engineer at Acme Corp\n"
            "Led a team of 5 backend engineers.\n"
            "\n"
            "Ausbildung\n"
            "B.Sc. Computer Science, MIT (2015-2019)\n"
        )
        parsed = parse_sections(cv)
        self.assertIn(SECTION_EXPERIENCE, parsed.sections)
        self.assertIn(SECTION_EDUCATION, parsed.sections)

    def test_english_headers_german_body(self):
        cv = (
            "Experience\n"
            "2020-2024 Senior-Ingenieur bei Acme GmbH\n"
            "\n"
            "Education\n"
            "M.Sc. Informatik, TU Berlin (2018)\n"
        )
        parsed = parse_sections(cv)
        self.assertIn(SECTION_EXPERIENCE, parsed.sections)
        self.assertIn(SECTION_EDUCATION, parsed.sections)


# ---------------------------------------------------------------------------
# Preamble + structure preservation
# ---------------------------------------------------------------------------


class PreambleAndStructure(unittest.TestCase):
    def test_preamble_lines_before_first_header(self):
        cv = "Jane Doe\njane@example.com\n+49 30 12345678\n\nExperience\n2020-2024 Acme Corp\n"
        parsed = parse_sections(cv)
        self.assertIn(SECTION_PREAMBLE, parsed.sections)
        preamble = "\n".join(parsed.sections[SECTION_PREAMBLE])
        self.assertIn("Jane Doe", preamble)
        self.assertIn("jane@example.com", preamble)

    def test_empty_lines_separate_blocks(self):
        cv = "Experience\nAcme Corp\n2020-2024\n\nBigco Inc\n2015-2020\n"
        parsed = parse_sections(cv)
        # Two blocks in experience: Acme + Bigco
        self.assertEqual(len(parsed.sections[SECTION_EXPERIENCE]), 2)

    def test_detected_headers_preserved(self):
        cv = "PROFESSIONAL SUMMARY:\nExperienced engineer."
        parsed = parse_sections(cv)
        self.assertEqual(parsed.detected_headers[SECTION_SUMMARY], "PROFESSIONAL SUMMARY:")


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------


class RobustnessEdgeCases(unittest.TestCase):
    def test_empty_input_returns_empty(self):
        parsed = parse_sections("")
        self.assertTrue(parsed.is_empty())

    def test_none_input_returns_empty(self):
        parsed = parse_sections(None)
        self.assertTrue(parsed.is_empty())

    def test_whitespace_only_input_returns_empty(self):
        parsed = parse_sections("   \n\n  \t  ")
        self.assertTrue(parsed.is_empty())

    def test_no_recognised_headers_all_goes_to_preamble(self):
        """A CV with no detectable headers (e.g., just plain
        unformatted text) lands entirely in preamble — never
        loses content."""

        cv = (
            "I have been working in software since 2010, mostly in "
            "Python and Rust. I've shipped several open-source "
            "libraries with combined 5000 stars on GitHub."
        )
        parsed = parse_sections(cv)
        self.assertIn(SECTION_PREAMBLE, parsed.sections)
        self.assertEqual(len(parsed.sections), 1)

    def test_long_line_not_classified_as_header(self):
        """A 60+-char line shouldn't be classified as a header
        even if it contains a header keyword."""

        long_line = (
            "Languages I have worked with include Python, Rust, "
            "Go, Java, and TypeScript over many years of experience"
        )
        cv = f"{long_line}\nmore text"
        parsed = parse_sections(cv)
        # Should NOT have triggered the Languages section
        self.assertNotIn(SECTION_LANGUAGES, parsed.sections)

    def test_header_with_trailing_colon(self):
        cv = "Skills:\nPython, SQL"
        parsed = parse_sections(cv)
        self.assertIn(SECTION_SKILLS, parsed.sections)

    def test_header_with_trailing_period(self):
        cv = "Education.\nMSc CS"
        parsed = parse_sections(cv)
        self.assertIn(SECTION_EDUCATION, parsed.sections)

    def test_case_insensitive_header(self):
        for variant in ("EXPERIENCE", "experience", "Experience", "ExPeRiEnCe"):
            with self.subTest(variant=variant):
                cv = f"{variant}\n2020-2024 Acme"
                parsed = parse_sections(cv)
                self.assertIn(SECTION_EXPERIENCE, parsed.sections)


# ---------------------------------------------------------------------------
# Realistic full-CV smoke test
# ---------------------------------------------------------------------------


class FullCvRoundtrip(unittest.TestCase):
    """End-to-end: a realistic DACH-area CV parses into all
    expected sections."""

    SAMPLE_CV = """\
Aïcha Ben Ali
aicha@example.com
+49 30 1234567
Berlin

Zusammenfassung
Pflegekraft mit 6 Jahren Erfahrung in Tunesien.
Aktuell in §16d AufenthG-Verfahren zur Anerkennung als
Krankenpflegerin in Deutschland.

Berufserfahrung
2018-2024 Hôpital La Rabta, Tunis — Krankenpflegerin (registriert)
- Intensivpflege Erwachsene
- Schichtdienst

2015-2018 Clinique Saint-Augustin, Tunis — Pflegehelferin

Ausbildung
2012-2015 Krankenpflegeschule Tunis, Diplôme d'État infirmier

Sprachen
Französisch (Muttersprache), Arabisch (Muttersprache),
Deutsch (B1, im Anerkennungsverfahren), Englisch (B2)

Zertifikate
Anerkennungsbescheid Bundesland Berlin (im Verfahren)
"""

    def test_all_expected_sections_detected(self):
        parsed = parse_sections(self.SAMPLE_CV)
        for section_id in (
            SECTION_PREAMBLE,
            SECTION_SUMMARY,
            SECTION_EXPERIENCE,
            SECTION_EDUCATION,
            SECTION_LANGUAGES,
            SECTION_CERTIFICATIONS,
        ):
            with self.subTest(section=section_id):
                self.assertIn(section_id, parsed.sections)

    def test_preamble_carries_contact(self):
        parsed = parse_sections(self.SAMPLE_CV)
        preamble = "\n".join(parsed.sections[SECTION_PREAMBLE])
        self.assertIn("Aïcha Ben Ali", preamble)
        self.assertIn("aicha@example.com", preamble)

    def test_experience_has_two_blocks(self):
        """The sample has two roles (Hôpital + Clinique) separated
        by an empty line — should be two blocks."""

        parsed = parse_sections(self.SAMPLE_CV)
        self.assertEqual(len(parsed.sections[SECTION_EXPERIENCE]), 2)

    def test_to_dict_serialises_cleanly(self):
        parsed = parse_sections(self.SAMPLE_CV)
        d = parsed.to_dict()
        # JSON-serialisable
        import json

        json.dumps(d)
        self.assertIn("sections", d)
        self.assertIn("detectedHeaders", d)


# ---------------------------------------------------------------------------
# Integration with /api/profile/cv-upload + /api/profile/cv/structured
# ---------------------------------------------------------------------------


class AppPyWiring(unittest.TestCase):
    """Source-level check that the new endpoints + upload-response
    extension are wired in app.py."""

    def setUp(self):
        self.src = Path(str(Path(__file__).resolve().parent.parent / "app.py")).read_text(
            encoding="utf-8"
        )

    def test_cv_upload_returns_parsed_cv(self):
        self.assertIn("from company_discovery.cv_section_parser import", self.src)
        self.assertIn("parsedCv", self.src)

    def test_structured_endpoint_registered(self):
        self.assertIn('parsed.path == "/api/profile/cv/structured"', self.src)


# ---------------------------------------------------------------------------
# Drift guards
# ---------------------------------------------------------------------------


class DriftGuards(unittest.TestCase):
    def test_all_sections_catalogue_size(self):
        # 8 named + 1 preamble + 1 other = 9
        # Pin so a future agent adding a section also updates the
        # frontend / API contract assertions downstream.
        self.assertEqual(len(ALL_SECTIONS), 9)

    def test_parsedcv_is_dataclass(self):
        from dataclasses import is_dataclass

        self.assertTrue(is_dataclass(ParsedCv))

    def test_parsedcv_get_returns_empty_for_missing(self):
        empty = ParsedCv()
        self.assertEqual(empty.get(SECTION_SKILLS), [])

    def test_parsedcv_is_empty_predicate(self):
        empty = ParsedCv()
        self.assertTrue(empty.is_empty())
        nonempty = ParsedCv(sections={SECTION_PREAMBLE: ["x"]})
        self.assertFalse(nonempty.is_empty())


if __name__ == "__main__":
    unittest.main()
