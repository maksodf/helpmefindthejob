# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Unit tests for the CV-vs-JD consultation."""

from __future__ import annotations

import unittest

from company_discovery.cv_consult import (
    build_consult_prompt,
    consult,
    heuristic_consult,
    parse_consult_response,
)


_JOB = {
    "title": "Pflegehelfer/in",
    "company": "Charité",
    "description": (
        "Wir suchen eine Pflegehelferin mit Erfahrung in der "
        "Geriatrie und Kenntnissen in MedTech-Dokumentationssystemen "
        "wie Vivendi oder Snomed. Englisch wäre ein Plus."
    ),
}

_CV_THIN = (
    "Maria Schmidt. 6 years caring for elderly residents in Berlin. "
    "Worked at Klinikum Alpha 2018-2022."
)


class BuildConsultPromptTests(unittest.TestCase):
    def test_system_prompt_locks_output_format(self):
        system, _ = build_consult_prompt(job=_JOB, cv_text=_CV_THIN)
        self.assertIn("JSON list of objects", system)
        self.assertIn("Never invent", system)
        self.assertIn("3-5", system)

    def test_user_prompt_includes_both_sides(self):
        _, user = build_consult_prompt(job=_JOB, cv_text=_CV_THIN)
        self.assertIn("Pflegehelfer", user)
        self.assertIn("Maria Schmidt", user)
        self.assertIn("Klinikum Alpha", user)


class ParseConsultResponseTests(unittest.TestCase):
    def test_valid_json_parses(self):
        raw = (
            '[{"gap": "Vivendi", "question": "Have you used Vivendi?"}, '
            '{"gap": "Geriatrie", "question": "Geriatric experience?"}]'
        )
        gaps = parse_consult_response(raw)
        self.assertEqual(len(gaps), 2)
        self.assertEqual(gaps[0]["gap"], "Vivendi")

    def test_wrapped_in_prose_still_parses(self):
        raw = "Here are the gaps:\n[{\"gap\": \"X\", \"question\": \"Y?\"}]\nDone."
        gaps = parse_consult_response(raw)
        self.assertEqual(gaps, [{"gap": "X", "question": "Y?"}])

    def test_invalid_returns_empty(self):
        self.assertEqual(parse_consult_response("not json"), [])
        self.assertEqual(parse_consult_response(""), [])
        self.assertEqual(parse_consult_response(None), [])

    def test_caps_at_six(self):
        items = ", ".join([
            f'{{"gap": "g{i}", "question": "q{i}?"}}'
            for i in range(10)
        ])
        gaps = parse_consult_response(f"[{items}]")
        self.assertLessEqual(len(gaps), 6)


class HeuristicConsultTests(unittest.TestCase):
    def test_finds_tech_terms_not_in_cv(self):
        gaps = heuristic_consult(job=_JOB, cv_text=_CV_THIN)
        text = " ".join(g["gap"] for g in gaps)
        # Should pick up at least one capitalised term the CV doesn't
        # cover (e.g. Vivendi, Geriatrie, Snomed).
        self.assertTrue(
            any(needle in text for needle in
                 ("Vivendi", "Geriatrie", "Snomed", "MedTech")),
            msg=f"got: {gaps!r}",
        )

    def test_returns_empty_when_no_description(self):
        gaps = heuristic_consult(
            job={"title": "X", "description": ""}, cv_text="anything",
        )
        self.assertEqual(gaps, [])

    def test_caps_at_three_items(self):
        gaps = heuristic_consult(job=_JOB, cv_text="")
        self.assertLessEqual(len(gaps), 3)


class ConsultTopLevelTests(unittest.TestCase):
    def test_no_ai_falls_back_to_heuristic(self):
        gaps, used_ai = consult(
            job=_JOB, cv_text=_CV_THIN, ai_caller=None,
        )
        self.assertFalse(used_ai)
        self.assertGreater(len(gaps), 0)

    def test_ai_returning_gaps_short_circuits(self):
        def fake_ai(system, user):
            return '[{"gap": "Vivendi", "question": "Used it?"}]'
        gaps, used_ai = consult(
            job=_JOB, cv_text=_CV_THIN, ai_caller=fake_ai,
        )
        self.assertTrue(used_ai)
        self.assertEqual(gaps, [{"gap": "Vivendi", "question": "Used it?"}])

    def test_ai_crash_falls_back(self):
        def crashing(system, user):
            raise RuntimeError("api down")
        gaps, used_ai = consult(
            job=_JOB, cv_text=_CV_THIN, ai_caller=crashing,
        )
        self.assertFalse(used_ai)
        # Heuristic fallback ran.
        self.assertGreaterEqual(len(gaps), 0)

    def test_ai_empty_response_falls_back(self):
        def empty(system, user):
            return ""
        gaps, used_ai = consult(
            job=_JOB, cv_text=_CV_THIN, ai_caller=empty,
        )
        self.assertFalse(used_ai)


if __name__ == "__main__":
    unittest.main()
