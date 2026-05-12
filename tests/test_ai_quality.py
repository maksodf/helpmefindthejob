"""AI quality — output parser robustness.

The parser (``structured_analysis.parse_freeform``) must extract a
useful ``StructuredFit`` from *every* shape of AI output we can
realistically expect — well-formed JSON, malformed JSON, JSON nested
in markdown, plain prose with a labelled score, percentages,
recommendations in various casings, missing fields, unicode, very long
outputs, etc. The intelligence of the dashboard depends entirely on
this — a single missed shape means the user sees ``ready: false`` on
the fit card even though the AI gave them a valid analysis.

This module exhaustively tests the parser. When it finds shapes that
fail, we either fix the parser or document the explicit non-goal."""

from __future__ import annotations

import unittest

from company_discovery.structured_analysis import (
    StructuredFit,
    parse_freeform,
)


class WellFormedJsonShapeTests(unittest.TestCase):
    """The happy paths the prompt asks the model to emit."""

    def test_pure_json_camelcase(self):
        out = parse_freeform(
            '{"fitScore": 0.78, "recommendation": "apply", '
            '"healthcareRelevance": "high", "tools": ["Python", "K8s"], '
            '"risks": ["German required"]}'
        )
        self.assertAlmostEqual(out.fit_score, 0.78, places=3)
        self.assertEqual(out.recommendation, "apply")
        self.assertEqual(out.healthcare_relevance, "high")
        self.assertEqual(out.tools, ["Python", "K8s"])
        self.assertEqual(out.risks, ["German required"])

    def test_pure_json_snake_case(self):
        out = parse_freeform(
            '{"fit_score": 0.5, "recommendation": "consider", '
            '"healthcare_relevance": "medium"}'
        )
        self.assertAlmostEqual(out.fit_score, 0.5, places=3)
        self.assertEqual(out.recommendation, "consider")
        self.assertEqual(out.healthcare_relevance, "medium")

    def test_mixed_case_json_keys(self):
        out = parse_freeform(
            '{"fitScore": 0.6, "recommendation": "consider", '
            '"junior_suitability": "fits"}'
        )
        self.assertAlmostEqual(out.fit_score, 0.6, places=3)
        self.assertEqual(out.junior_suitability, "fits")

    def test_score_alias(self):
        """Some models use ``score`` instead of ``fitScore``."""
        out = parse_freeform('{"score": 0.42, "recommendation": "skip"}')
        self.assertAlmostEqual(out.fit_score, 0.42, places=3)
        self.assertEqual(out.recommendation, "skip")


class JsonInProseShapeTests(unittest.TestCase):
    """The realistic case: model returns prose THEN a JSON block."""

    def test_json_after_paragraph(self):
        out = parse_freeform(
            "This role looks like a strong match. The candidate has 8 years "
            "of Python and the JD asks for 5+.\n\n"
            '{"fitScore": 0.82, "recommendation": "apply", '
            '"tools": ["Python", "Postgres", "K8s"]}'
        )
        self.assertAlmostEqual(out.fit_score, 0.82, places=3)
        self.assertEqual(out.recommendation, "apply")
        self.assertEqual(out.tools, ["Python", "Postgres", "K8s"])

    def test_json_in_markdown_fence(self):
        out = parse_freeform(
            "Here's my analysis:\n\n```json\n"
            '{"fitScore": 0.7, "recommendation": "consider"}\n'
            "```\n\nLet me know if you want more detail."
        )
        self.assertAlmostEqual(out.fit_score, 0.7, places=3)
        self.assertEqual(out.recommendation, "consider")

    def test_json_with_explanation_after(self):
        out = parse_freeform(
            '{"fitScore": 0.5, "recommendation": "consider"}\n\n'
            "The 'consider' verdict reflects that you're a strong technical "
            "match but the location requirement is on-site Munich."
        )
        self.assertAlmostEqual(out.fit_score, 0.5, places=3)


class PercentScoreNormalisationTests(unittest.TestCase):
    """Models often emit 78 instead of 0.78. Parser must clamp."""

    def test_percent_score_85(self):
        out = parse_freeform('{"fitScore": 85, "recommendation": "apply"}')
        # 0..100 → 0..1
        self.assertAlmostEqual(out.fit_score, 0.85, places=3)
        self.assertEqual(out.recommendation, "apply")

    def test_percent_score_100(self):
        out = parse_freeform('{"fitScore": 100, "recommendation": "apply"}')
        self.assertEqual(out.fit_score, 1.0)

    def test_percent_score_0(self):
        out = parse_freeform('{"fitScore": 0, "recommendation": "skip"}')
        self.assertEqual(out.fit_score, 0.0)

    def test_score_over_100_clamps_to_1(self):
        out = parse_freeform('{"fitScore": 150}')
        self.assertEqual(out.fit_score, 1.0)


class RegexFallbackTests(unittest.TestCase):
    """When JSON parsing fails, fall back to regex extraction."""

    def test_plain_text_fit_score_decimal(self):
        out = parse_freeform("The fit score is 0.72 — recommendation: apply.")
        self.assertAlmostEqual(out.fit_score, 0.72, places=3)
        self.assertEqual(out.recommendation, "apply")

    def test_plain_text_fit_score_with_colon(self):
        out = parse_freeform("Fit score: 0.55. Recommendation: consider.")
        self.assertAlmostEqual(out.fit_score, 0.55, places=3)
        self.assertEqual(out.recommendation, "consider")

    def test_plain_text_fit_score_with_equals(self):
        out = parse_freeform("fit_score = 0.4")
        self.assertAlmostEqual(out.fit_score, 0.4, places=3)

    def test_plain_text_score_word_capitalised(self):
        """The prompt sometimes says 'Fit Score' with capital S."""
        out = parse_freeform("Fit Score: 0.91")
        self.assertAlmostEqual(out.fit_score, 0.91, places=3)

    def test_recommendation_capital(self):
        """Recommendation token in various casings."""
        out = parse_freeform("RECOMMENDATION: APPLY (fit score: 0.9)")
        self.assertEqual(out.recommendation, "apply")
        self.assertAlmostEqual(out.fit_score, 0.9, places=3)


class MalformedJsonGracefulFallbackTests(unittest.TestCase):
    """Malformed JSON must not crash — parser falls back to regex.
    The TEXT-LEVEL fallback should still extract score / recommendation."""

    def test_trailing_comma_in_json(self):
        # json.loads chokes on trailing commas; we still extract via regex.
        out = parse_freeform(
            '{"fitScore": 0.7, "recommendation": "apply",}'
        )
        self.assertAlmostEqual(out.fit_score, 0.7, places=3)
        self.assertEqual(out.recommendation, "apply")

    def test_missing_closing_brace(self):
        out = parse_freeform(
            '{"fitScore": 0.6, "recommendation": "consider"'
        )
        # The JSON_BLOCK_RE wants {…}; with no closing brace it doesn't
        # match. The text regex fallback should still pick up the score.
        self.assertAlmostEqual(out.fit_score, 0.6, places=3)
        self.assertEqual(out.recommendation, "consider")

    def test_single_quotes_not_json(self):
        out = parse_freeform(
            "Score: 0.45; recommendation: skip"
        )
        self.assertAlmostEqual(out.fit_score, 0.45, places=3)
        self.assertEqual(out.recommendation, "skip")


class EdgeCaseTests(unittest.TestCase):
    """Empty, very long, unicode, etc."""

    def test_empty_output(self):
        out = parse_freeform("")
        self.assertIsNone(out.fit_score)
        self.assertIsNone(out.recommendation)
        self.assertEqual(out.tools, [])

    def test_whitespace_only(self):
        out = parse_freeform("   \n\t  ")
        self.assertIsNone(out.fit_score)
        self.assertIsNone(out.recommendation)

    def test_only_prose_no_signal(self):
        """The AI may decline to give a score (refusal / off-topic)."""
        out = parse_freeform(
            "I can't give a score because the job description was not "
            "provided in full. Please re-share."
        )
        self.assertIsNone(out.fit_score)
        self.assertIsNone(out.recommendation)

    def test_invalid_recommendation_string(self):
        """``maybe`` is not in the whitelist — should NOT be set."""
        out = parse_freeform(
            '{"fitScore": 0.5, "recommendation": "maybe"}'
        )
        self.assertAlmostEqual(out.fit_score, 0.5, places=3)
        self.assertIsNone(out.recommendation)

    def test_unicode_in_fields(self):
        out = parse_freeform(
            '{"fitScore": 0.6, "recommendation": "consider", '
            '"tools": ["Python", "Docker 🐳", "Kubernetes ☸️"], '
            '"healthcareRelevance": "中等"}'
        )
        self.assertAlmostEqual(out.fit_score, 0.6, places=3)
        self.assertIn("Docker 🐳", out.tools)
        self.assertEqual(out.healthcare_relevance, "中等")

    def test_very_long_output(self):
        """Models can ramble — 50KB+ output must still parse the JSON."""
        prose = "The candidate has many strengths. " * 1500  # ~50KB
        text = prose + '\n{"fitScore": 0.65, "recommendation": "consider"}'
        out = parse_freeform(text)
        self.assertAlmostEqual(out.fit_score, 0.65, places=3)
        self.assertEqual(out.recommendation, "consider")

    def test_tools_as_csv_string(self):
        """Some models emit tools as a comma-separated string."""
        out = parse_freeform(
            '{"fitScore": 0.5, "tools": "Python, K8s, Postgres"}'
        )
        self.assertAlmostEqual(out.fit_score, 0.5, places=3)
        self.assertEqual(out.tools, ["Python", "K8s", "Postgres"])

    def test_score_in_json_string_form(self):
        """Model emits ``"0.7"`` as a string, not a number."""
        out = parse_freeform(
            '{"fitScore": "0.7", "recommendation": "consider"}'
        )
        self.assertAlmostEqual(out.fit_score, 0.7, places=3)

    def test_negative_score_handling(self):
        """A negative score is a bug in the AI; parser must not blow up.
        Current contract: store as-is (parser doesn't clamp <0). The
        downstream display layer should treat negative as 0."""
        out = parse_freeform('{"fitScore": -0.2}')
        # Either None or -0.2 is acceptable; key is "didn't crash".
        self.assertIn(out.fit_score, (None, -0.2))

    def test_null_fields(self):
        out = parse_freeform(
            '{"fitScore": null, "recommendation": null, "tools": null}'
        )
        self.assertIsNone(out.fit_score)
        self.assertIsNone(out.recommendation)
        self.assertEqual(out.tools, [])


class RoundTripStructureTests(unittest.TestCase):
    """The to_dict() shape must stay stable so the API contract doesn't
    drift when we add fields."""

    def test_to_dict_keys_are_camelcase(self):
        out = parse_freeform(
            '{"fitScore": 0.7, "recommendation": "apply"}'
        )
        d = out.to_dict()
        expected = {
            "fitScore", "recommendation", "healthcareRelevance",
            "juniorSuitability", "requiredExperience",
            "languageRequirements", "tools", "risks", "notes",
        }
        self.assertEqual(set(d.keys()), expected)

    def test_to_dict_preserves_lists(self):
        out = parse_freeform(
            '{"fitScore": 0.5, "tools": ["a", "b"], "risks": ["x"]}'
        )
        d = out.to_dict()
        self.assertEqual(d["tools"], ["a", "b"])
        self.assertEqual(d["risks"], ["x"])

    def test_notes_falls_back_to_full_output(self):
        """When parser couldn't extract a structured fitScore, the
        ``notes`` field should still carry the AI's full output so the
        user sees something."""
        text = "The role is interesting but I can't quantify the fit."
        out = parse_freeform(text)
        self.assertEqual(out.notes, text)


if __name__ == "__main__":
    unittest.main()
