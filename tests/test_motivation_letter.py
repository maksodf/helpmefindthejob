"""Unit tests for the DACH-norm motivation letter drafter."""

from __future__ import annotations

import unittest

from company_discovery.motivation_letter import (
    build_letter_prompt,
    draft_with_ai,
    templated_fallback,
)


_JOB = {
    "title": "Pflegehelfer/in (m/w/d)",
    "company": "Charité",
    "location": "Berlin",
    "url": "https://example.com/jobs/123",
}

_CV = (
    "Maria Schmidt. Senior Pflegehelferin with 6 years experience in "
    "elderly care across two clinics in Berlin. Worked at Klinikum "
    "Alpha 2018-2022 caring for 12 residents per shift."
)


class BuildPromptTests(unittest.TestCase):
    def test_system_prompt_contains_dach_structure(self):
        system, _ = build_letter_prompt(
            job_title="Bartender", company="Berliner Bar",
            location="Berlin", job_url="", cv_text="",
        )
        for needed in ("Anrede", "Hauptteil", "Schluss", "Sehr geehrte",
                        "TT.MM.JJJJ", "Mit freundlichen Grüßen"):
            self.assertIn(needed, system, msg=f"missing: {needed}")

    def test_user_prompt_carries_job_and_cv(self):
        _, user = build_letter_prompt(
            job_title="Bartender", company="Berliner Bar",
            location="Berlin", job_url="https://x",
            cv_text="some cv",
        )
        self.assertIn("Berliner Bar", user)
        self.assertIn("Bartender", user)
        self.assertIn("some cv", user)
        self.assertIn("https://x", user)


class DraftWithAiTests(unittest.TestCase):
    def test_none_caller_returns_none(self):
        result = draft_with_ai(
            job=_JOB, cv_text=_CV,
            user_name="Maria", user_location="Berlin",
            ai_caller=None,
        )
        self.assertIsNone(result)

    def test_successful_call_returns_letter(self):
        def fake_ai(system, user):
            # Return a complete DACH letter — the AI's responsibility.
            return (
                "Maria Schmidt, Berlin\n\nCharité\nBerlin\n\n"
                "12.05.2026\n\nBetreff: Bewerbung als Pflegehelferin\n\n"
                "Sehr geehrte Damen und Herren,\n\n"
                "hiermit bewerbe ich mich um die Stelle.\n\n"
                "Meine Erfahrung im Klinikum Alpha …\n\n"
                "Mein Engagement und meine Empathie …\n\n"
                "Mit freundlichen Grüßen,\n\nMaria Schmidt"
            )
        result = draft_with_ai(
            job=_JOB, cv_text=_CV,
            user_name="Maria", user_location="Berlin",
            ai_caller=fake_ai,
        )
        self.assertIsNotNone(result)
        self.assertIn("Sehr geehrte Damen und Herren", result)
        self.assertIn("Mit freundlichen Grüßen", result)

    def test_caller_error_returns_none(self):
        def crashing(system, user):
            raise RuntimeError("api down")
        result = draft_with_ai(
            job=_JOB, cv_text=_CV,
            user_name="Maria", user_location="Berlin",
            ai_caller=crashing,
        )
        self.assertIsNone(result)


class TemplatedFallbackTests(unittest.TestCase):
    def test_template_includes_banner_and_structure(self):
        text = templated_fallback(
            job=_JOB, user_name="Maria", user_location="Berlin",
        )
        # The honesty banner.
        self.assertIn("without an AI", text)
        # DACH structure pieces.
        self.assertIn("Charité", text)
        self.assertIn("Berlin", text)
        self.assertIn("Bewerbung als Pflegehelfer", text)
        self.assertIn("Sehr geehrte Damen und Herren", text)
        self.assertIn("Mit freundlichen Grüßen", text)
        # 3-paragraph Hauptteil structure markers (placeholders).
        self.assertIn("2. Absatz", text)
        self.assertIn("3. Absatz", text)
        # User identity in absender + signature.
        self.assertIn("Maria", text)

    def test_template_with_missing_company_falls_to_placeholder(self):
        text = templated_fallback(
            job={"title": "Pflegehelfer", "company": "",
                  "location": "", "url": ""},
            user_name="", user_location="",
        )
        self.assertIn("<Firma>", text)
        self.assertIn("<Ort der Firma>", text)
        self.assertIn("<Ihr Name>", text)
        self.assertIn("<Ihre Stadt>", text)


if __name__ == "__main__":
    unittest.main()
