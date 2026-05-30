# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""CV builder — deterministic conversation flow tests.

The CV builder must NOT hallucinate. Every test here verifies one of
those properties:

  - State machine walks sections in fixed order
  - Repeatable sections (experience, education) accept multiple entries
  - AI-format prompts forbid invention
  - Fact-ratio gate rejects hallucinated AI output
  - Assembled CV markdown contains only user-stated facts
  - Section keys + question schemas are stable (UI contract)"""

from __future__ import annotations

import unittest

from company_discovery.cv_builder import (
    FACT_RATIO_THRESHOLD,
    SECTIONS,
    SECTIONS_BY_ID,
    CvBuilderState,
    assemble_cv_markdown,
    build_format_prompt,
    compute_fact_ratio,
    cv_markdown_to_html,
    get_section,
    next_section_id,
    render_cv_print_html,
    score_recommendation_inconsistent,
    validate_ai_format_output,
)


class StateMachineOrderTests(unittest.TestCase):
    def test_section_order_is_fixed(self):
        ids = [s.section_id for s in SECTIONS]
        self.assertEqual(ids[:4], ["header", "summary", "experience", "education"])
        self.assertIn("skills", ids)
        self.assertIn("certifications", ids)
        self.assertIn("projects", ids)

    def test_next_section_starts_with_header(self):
        self.assertEqual(next_section_id(None), "header")

    def test_next_section_advances(self):
        self.assertEqual(next_section_id("header"), "summary")
        self.assertEqual(next_section_id("summary"), "experience")
        self.assertEqual(next_section_id("experience"), "education")

    def test_next_section_terminates(self):
        # The last section returns None.
        last_id = SECTIONS[-1].section_id
        self.assertIsNone(next_section_id(last_id))

    def test_unknown_section_resets_to_header(self):
        self.assertEqual(next_section_id("nope"), "header")


class SectionSchemaTests(unittest.TestCase):
    def test_header_has_required_fields(self):
        section = get_section("header")
        required = [q.key for q in section.questions if q.required]
        self.assertIn("full_name", required)
        self.assertIn("email", required)
        self.assertIn("location", required)

    def test_experience_is_repeatable(self):
        self.assertTrue(get_section("experience").repeatable)

    def test_education_is_repeatable(self):
        self.assertTrue(get_section("education").repeatable)

    def test_summary_not_repeatable(self):
        self.assertFalse(get_section("summary").repeatable)

    def test_skills_not_repeatable(self):
        self.assertFalse(get_section("skills").repeatable)

    def test_get_section_raises_on_unknown(self):
        with self.assertRaises(KeyError):
            get_section("nope")


class FormatPromptBoundednessTests(unittest.TestCase):
    """The format prompt must contain explicit anti-hallucination
    instructions. We verify the prompt's text rather than the AI's
    output (that's downstream)."""

    def test_prompt_forbids_invention(self):
        prompt = build_format_prompt("experience", "managed a team of 5")
        self.assertIn("Do NOT add facts", prompt)
        self.assertIn("invent", prompt)

    def test_prompt_carries_user_text_verbatim(self):
        user = "led a migration from monolith to microservices over 18 months"
        prompt = build_format_prompt("experience", user)
        self.assertIn(user, prompt)

    def test_prompt_specifies_section_intent(self):
        prompt = build_format_prompt("summary", "x")
        self.assertIn("summary", prompt.lower())

    def test_prompt_preserves_numbers(self):
        prompt = build_format_prompt("experience", "x")
        self.assertIn("NUMBER", prompt)


class FactRatioGateTests(unittest.TestCase):
    def test_threshold_is_60_percent(self):
        self.assertEqual(FACT_RATIO_THRESHOLD, 0.6)

    def test_validate_accepts_well_grounded_output(self):
        user = "managed a team of 5 engineers, deployed AWS infrastructure"
        ai = "Managed a team of 5 engineers; deployed AWS infrastructure."
        accept, ratio = validate_ai_format_output(user, ai)
        self.assertTrue(accept)
        self.assertGreaterEqual(ratio, 0.6)

    def test_validate_rejects_hallucinated_output(self):
        user = "I worked at Acme."
        ai = (
            "Senior Backend Engineer at Acme, leading a team of 12, "
            "shipping Kubernetes infrastructure and reducing latency 40%."
        )
        accept, ratio = validate_ai_format_output(user, ai)
        self.assertFalse(accept)

    def test_empty_output_ratio_one(self):
        ratio = compute_fact_ratio("anything", "")
        self.assertEqual(ratio, 1.0)

    def test_diacritic_folded_match(self):
        # User typed 'München'; AI typed 'Munchen' — must be treated equal.
        ratio = compute_fact_ratio("Senior Engineer in München", "Senior Engineer in Munchen")
        self.assertGreaterEqual(ratio, 0.8)


class StateSerialisationTests(unittest.TestCase):
    def test_round_trip_empty(self):
        state = CvBuilderState()
        d = state.to_dict()
        restored = CvBuilderState.from_dict(d)
        self.assertEqual(restored.current_section_id, None)
        self.assertEqual(restored.sections, {})

    def test_round_trip_populated(self):
        state = CvBuilderState(
            current_section_id="experience",
            sections={
                "header": [
                    {"full_name": "Anna", "email": "anna@example.com", "location": "Berlin"}
                ],
                "experience": [
                    {"company_name": "Acme", "job_title": "Senior Engineer"},
                ],
            },
        )
        restored = CvBuilderState.from_dict(state.to_dict())
        self.assertEqual(restored.current_section_id, "experience")
        self.assertEqual(restored.sections["header"][0]["full_name"], "Anna")

    def test_from_dict_handles_none(self):
        s = CvBuilderState.from_dict(None)
        self.assertEqual(s.current_section_id, None)

    def test_from_dict_handles_garbage(self):
        s = CvBuilderState.from_dict({"sections": "not-a-dict", "currentSectionId": 42})
        # Should not crash; sections becomes empty.
        self.assertEqual(s.sections, {})


class AssemblyTests(unittest.TestCase):
    """The assembled CV must contain only user-stated facts; nothing
    invented even if the AI hallucinated upstream (we'd have rejected
    that output via the fact-ratio gate before storing here)."""

    def test_minimal_cv(self):
        state = CvBuilderState(
            sections={
                "header": [
                    {
                        "full_name": "Anna Müller",
                        "email": "anna@example.com",
                        "location": "Berlin",
                    }
                ],
            }
        )
        md = assemble_cv_markdown(state)
        self.assertIn("# Anna Müller", md)
        self.assertIn("anna@example.com", md)
        self.assertIn("Berlin", md)

    def test_full_cv_round_trip(self):
        state = CvBuilderState(
            sections={
                "header": [
                    {
                        "full_name": "Anna Müller",
                        "email": "anna@example.com",
                        "location": "Berlin",
                        "linkedin": "linkedin.com/in/anna",
                    }
                ],
                "summary": [
                    {
                        "summary_raw": "Senior backend engineer. 8 years Python.",
                        "formatted": "Senior backend engineer with 8 years of Python "
                        "and microservices experience.",
                    }
                ],
                "experience": [
                    {
                        "company_name": "Acme Corp",
                        "job_title": "Senior Backend Engineer",
                        "start_date": "2022-01",
                        "end_date": "present",
                        "location": "Berlin",
                        "achievements_raw": "Led migration to k8s.",
                        "formatted": "- Led migration to Kubernetes.",
                    },
                ],
                "education": [
                    {
                        "school": "TU Berlin",
                        "degree": "MSc",
                        "field": "Computer Science",
                        "start_date": "2016",
                        "end_date": "2019",
                    },
                ],
                "skills": [
                    {
                        "skills_raw": "python, kubernetes, postgres, aws",
                        "formatted": "**Languages:** Python\n"
                        "**Cloud:** AWS, Kubernetes\n"
                        "**Data:** Postgres",
                    }
                ],
            }
        )
        md = assemble_cv_markdown(state)
        # Header
        self.assertIn("Anna Müller", md)
        self.assertIn("linkedin.com/in/anna", md)
        # Summary
        self.assertIn("## Summary", md)
        self.assertIn("Senior backend engineer", md)
        # Experience
        self.assertIn("## Experience", md)
        self.assertIn("Senior Backend Engineer", md)
        self.assertIn("Acme Corp", md)
        self.assertIn("Led migration to Kubernetes", md)
        # Education
        self.assertIn("## Education", md)
        self.assertIn("TU Berlin", md)
        self.assertIn("Computer Science", md)
        # Skills
        self.assertIn("## Skills", md)
        self.assertIn("Python", md)
        self.assertIn("Kubernetes", md)

    def test_assembly_uses_formatted_when_present(self):
        state = CvBuilderState(
            sections={
                "header": [{"full_name": "X"}],
                "summary": [
                    {
                        "summary_raw": "raw text",
                        "formatted": "polished text",
                    }
                ],
            }
        )
        md = assemble_cv_markdown(state)
        self.assertIn("polished text", md)
        self.assertNotIn("raw text", md)

    def test_assembly_falls_back_to_raw_when_no_formatted(self):
        state = CvBuilderState(
            sections={
                "header": [{"full_name": "X"}],
                "summary": [{"summary_raw": "raw fallback text"}],
            }
        )
        md = assemble_cv_markdown(state)
        self.assertIn("raw fallback text", md)

    def test_empty_state_produces_no_crash(self):
        md = assemble_cv_markdown(CvBuilderState())
        # Just an empty string + newline — no exception.
        self.assertIsInstance(md, str)


class PrintHtmlRenderTests(unittest.TestCase):
    """Markdown → HTML conversion for the print view. Handles only the
    constructs the assembler emits — keep the converter audit-tight."""

    def test_h1_h2_render(self):
        html = cv_markdown_to_html("# Anna Müller\n## Summary\nText.")
        self.assertIn("<h1>Anna Müller</h1>", html)
        self.assertIn("<h2>Summary</h2>", html)

    def test_bold_inline(self):
        html = cv_markdown_to_html("**Senior Engineer** — Acme Corp")
        self.assertIn("<strong>Senior Engineer</strong>", html)

    def test_list_render(self):
        html = cv_markdown_to_html("## Skills\n- Python\n- Kubernetes")
        self.assertIn("<ul>", html)
        self.assertIn("<li>Python</li>", html)
        self.assertIn("<li>Kubernetes</li>", html)
        self.assertIn("</ul>", html)

    def test_paragraph_render(self):
        html = cv_markdown_to_html("Senior backend engineer with 8 years.")
        self.assertIn("<p>Senior backend engineer with 8 years.</p>", html)

    def test_html_escape_in_paragraph(self):
        """User CV text MUST be escaped; raw <script> must not survive."""
        html = cv_markdown_to_html("Note: <script>alert(1)</script>")
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_img_passes_through(self):
        """The assembler's data-URI <img …> photo is rendered (rebuilt from a
        safe allow-list — src + escaped alt + the canonical sizing style — so
        user-supplied event handlers can never survive; see _safe_img)."""
        md = '<img src="data:image/png;base64,AAAA" alt="x" />\n# Anna Müller'
        html = cv_markdown_to_html(md)
        self.assertIn('src="data:image/png;base64,AAAA"', html)
        self.assertIn('alt="x"', html)
        self.assertIn("<h1>Anna Müller</h1>", html)

    def test_lists_close_on_blank_line(self):
        html = cv_markdown_to_html("## Skills\n- Python\n- AWS\n\n## Education\n**TU Berlin**")
        # The first <ul> must close before the next section's heading.
        idx_close = html.find("</ul>")
        idx_h2_edu = html.find("Education")
        self.assertGreater(idx_h2_edu, idx_close)


class PrintDocRenderTests(unittest.TestCase):
    """The full print HTML wrapper — headers, CSS, optional auto-print."""

    def test_doc_includes_doctype_and_print_css(self):
        doc = render_cv_print_html("# Anna\nx")
        self.assertTrue(doc.startswith("<!doctype html>"))
        self.assertIn("@page { size: A4;", doc)
        self.assertIn("Download as PDF", doc)
        self.assertIn("<h1>Anna</h1>", doc)

    def test_autoprint_injects_script(self):
        doc = render_cv_print_html("# Anna", auto_print=True)
        self.assertIn("window.print()", doc)
        self.assertIn("setTimeout", doc)

    def test_no_autoprint_omits_script(self):
        doc = render_cv_print_html("# Anna", auto_print=False)
        # The Download button has window.print() inline; the auto-firing
        # setTimeout script must NOT be present.
        self.assertNotIn("setTimeout(function()", doc)

    def test_photo_data_uri_renders(self):
        md = '<img src="data:image/png;base64,iVBORw0KGgo=" alt="" />\n# X'
        doc = render_cv_print_html(md)
        self.assertIn('src="data:image/png;base64,iVBORw0KGgo="', doc)


class ConsistencyHelperTests(unittest.TestCase):
    def test_apply_low_score_flagged(self):
        self.assertTrue(score_recommendation_inconsistent(0.1, "apply"))

    def test_skip_high_score_flagged(self):
        self.assertTrue(score_recommendation_inconsistent(0.95, "skip"))

    def test_consider_extreme_score_flagged(self):
        self.assertTrue(score_recommendation_inconsistent(0.05, "consider"))
        self.assertTrue(score_recommendation_inconsistent(0.95, "consider"))

    def test_consistent_pairs_pass(self):
        self.assertFalse(score_recommendation_inconsistent(0.8, "apply"))
        self.assertFalse(score_recommendation_inconsistent(0.2, "skip"))
        self.assertFalse(score_recommendation_inconsistent(0.5, "consider"))


if __name__ == "__main__":
    unittest.main()
