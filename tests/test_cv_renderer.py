"""R24.4 / R24.6 / R24.7 — CV schema + renderer.

The renderer is pure (no LLM) so it can be exhaustively unit-tested.
Verifies:
  * Sanitised CvDocument clamps every field at its max
  * HTML escaping on every user-controlled string (XSS guard)
  * Photo URI allow-list (only data:image/(png|jpeg|webp|gif)
  * Each of the 6 templates renders without crashing for a complete
    document AND for a near-empty document
  * Accent + photo + template values are validated against allow-lists
  * Renderer output references the base CSS stylesheet
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from company_discovery.cv_schema import (
    CvCertification, CvContact, CvDocument, CvEducation, CvExperience,
    CvLanguage, CvPublication, MAX_BULLET, MAX_BULLETS_PER_ROLE,
    MAX_DESCRIPTION, MAX_EXPERIENCE, MAX_NAME, MAX_SKILLS,
    MAX_SUMMARY, VALID_ACCENT_COLORS, VALID_TEMPLATES,
)
from company_discovery.cv_renderer import render_cv


def _full_doc(**overrides) -> CvDocument:
    """A maximally-populated document for happy-path tests."""
    doc = CvDocument(
        full_name="Maria Schmidt",
        headline="Senior care coordinator with 6 years' Berlin experience",
        location="Berlin, Germany",
        photo_data_uri="",
        template_id="modern",
        accent_color="indigo",
        photo_on=True,
        contacts=[
            CvContact(label="Email", value="maria@example.com"),
            CvContact(label="Phone", value="+49 30 1234567"),
        ],
        summary=(
            "Pflegehelferin with hands-on experience across two Berlin "
            "Charité wards. Strong on documentation + first-response."),
        experience=[
            CvExperience(
                title="Pflegehelferin", company="Charité",
                location="Berlin", start="2020-09", end="present",
                description="12 residents per shift, documentation & first response.",
                bullets=[
                    "Coordinated handovers with night-shift team",
                    "Reduced medication-cycle errors by 18%",
                ],
            ),
        ],
        education=[
            CvEducation(degree="Krankenpflegehilfe",
                         institution="Charité Berlin",
                         start="2018", end="2020"),
        ],
        skills=["First aid", "Documentation", "German", "English"],
        languages=[
            CvLanguage(language="German", level="C1"),
            CvLanguage(language="English", level="B2"),
        ],
        certifications=[
            CvCertification(name="First-aid", issuer="DRK", year="2024"),
        ],
        publications=[],
        notes="",
    )
    for k, v in overrides.items():
        setattr(doc, k, v)
    return doc


class SchemaSanitisationTests(unittest.TestCase):
    def test_string_caps_enforced(self):
        long = "A" * 5000
        doc = CvDocument(full_name=long, summary=long).sanitised()
        self.assertLessEqual(len(doc.full_name), MAX_NAME)
        self.assertLessEqual(len(doc.summary), MAX_SUMMARY)

    def test_invalid_template_falls_back_to_modern(self):
        doc = CvDocument(template_id="not-a-template").sanitised()
        self.assertEqual(doc.template_id, "modern")

    def test_invalid_accent_falls_back_to_indigo(self):
        doc = CvDocument(accent_color="hot-pink").sanitised()
        self.assertEqual(doc.accent_color, "indigo")

    def test_list_lengths_capped(self):
        many = [f"skill-{i}" for i in range(200)]
        doc = CvDocument(skills=many).sanitised()
        self.assertLessEqual(len(doc.skills), MAX_SKILLS)

    def test_experience_bullets_capped(self):
        e = CvExperience(
            title="dev", company="X",
            bullets=[f"line {i}" for i in range(50)],
        )
        doc = CvDocument(experience=[e]).sanitised()
        self.assertLessEqual(
            len(doc.experience[0].bullets), MAX_BULLETS_PER_ROLE)

    def test_control_chars_stripped(self):
        doc = CvDocument(full_name="Maria\x00\x01Schmidt").sanitised()
        self.assertNotIn("\x00", doc.full_name)
        self.assertNotIn("\x01", doc.full_name)

    def test_empty_document_renders_round_trip(self):
        """A completely empty CvDocument must still sanitise + render."""
        doc = CvDocument().sanitised()
        self.assertEqual(doc.template_id, "modern")
        html = render_cv(doc)
        self.assertIn("<!doctype html>", html)


class RendererXssGuardTests(unittest.TestCase):
    def test_name_with_html_tags_is_escaped(self):
        doc = _full_doc(full_name="<script>alert('xss')</script>")
        html = render_cv(doc)
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;alert", html)

    def test_summary_with_html_tags_is_escaped(self):
        doc = _full_doc(summary="<img src=x onerror=alert(1)>")
        html = render_cv(doc)
        self.assertNotIn("<img src=x onerror=", html)
        self.assertIn("&lt;img src=x onerror=", html)

    def test_skill_quotes_escaped(self):
        doc = _full_doc(skills=['"onmouseover=alert(1)"'])
        html = render_cv(doc)
        # The raw quote-and-onmouseover sequence must not appear in
        # attribute position. Double quotes get escaped to &quot;.
        self.assertNotIn('"onmouseover=alert(1)"', html)

    def test_javascript_photo_uri_dropped(self):
        doc = _full_doc(photo_data_uri="javascript:alert(1)")
        html = render_cv(doc)
        self.assertNotIn("javascript:", html)
        self.assertNotIn("<img", html)  # photo block hidden

    def test_data_text_html_photo_uri_dropped(self):
        doc = _full_doc(photo_data_uri="data:text/html,<script>x</script>")
        html = render_cv(doc)
        self.assertNotIn("<script>x", html)

    def test_valid_png_photo_uri_kept(self):
        doc = _full_doc(
            photo_data_uri="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
        )
        html = render_cv(doc)
        self.assertIn('class="cv-photo"', html)
        self.assertIn("data:image/png", html)


class TemplateCoverageTests(unittest.TestCase):
    """Every template must render successfully for both a full and
    a near-empty document."""

    def test_all_six_render_for_full_doc(self):
        for tpl in VALID_TEMPLATES:
            doc = _full_doc(template_id=tpl)
            html = render_cv(doc)
            self.assertIn(f'data-template="{tpl}"', html,
                            f"{tpl}: data-template attr missing")
            self.assertIn("Maria Schmidt", html,
                            f"{tpl}: name not rendered")
            self.assertIn("Pflegehelferin", html,
                            f"{tpl}: experience not rendered")

    def test_all_six_render_for_empty_doc(self):
        for tpl in VALID_TEMPLATES:
            doc = CvDocument(template_id=tpl)
            html = render_cv(doc)
            self.assertIn(f'data-template="{tpl}"', html)
            self.assertIn("<!doctype html>", html)

    def test_each_accent_renders(self):
        for accent in VALID_ACCENT_COLORS:
            doc = _full_doc(accent_color=accent)
            html = render_cv(doc)
            self.assertIn(f'data-accent="{accent}"', html)

    def test_photo_off_hides_image_via_data_attr(self):
        doc = _full_doc(
            photo_on=False,
            photo_data_uri="data:image/png;base64,iVBORw0KGgo=",
        )
        html = render_cv(doc)
        # Photo block isn't emitted at all when photo_on=False.
        self.assertNotIn("class=\"cv-photo\"", html)
        # Data attribute also flips so CSS would hide it even if it slipped in.
        self.assertIn('data-photo-off="true"', html)

    def test_academic_renders_publications(self):
        doc = _full_doc(
            template_id="academic",
            publications=[
                CvPublication(
                    title="On task-based AI assistants",
                    venue="JACM", year="2026",
                    co_authors="A. Smith, B. Lee"),
            ],
        )
        html = render_cv(doc)
        self.assertIn("On task-based AI assistants", html)
        self.assertIn("Publications", html)

    def test_tech_has_twocol_layout(self):
        doc = _full_doc(template_id="tech")
        html = render_cv(doc)
        self.assertIn("cv-twocol", html)
        self.assertIn("cv-twocol-main", html)
        self.assertIn("cv-twocol-side", html)


class RendererOutputShapeTests(unittest.TestCase):
    def test_references_base_stylesheet(self):
        html = render_cv(_full_doc())
        self.assertIn("/static/cv_templates/cv_base.css", html)

    def test_inline_css_option_replaces_link(self):
        html = render_cv(_full_doc(), css_inline="body{margin:0}")
        self.assertNotIn("/static/cv_templates/cv_base.css", html)
        self.assertIn("body{margin:0}", html)

    def test_autoprint_emits_print_script(self):
        html = render_cv(_full_doc(), auto_print=True)
        self.assertIn("window.print()", html)

    def test_no_autoprint_by_default(self):
        html = render_cv(_full_doc())
        self.assertNotIn("window.print()", html)


class RoundTripSerialisationTests(unittest.TestCase):
    def test_from_dict_round_trip_keeps_fields(self):
        original = _full_doc()
        as_dict = original.to_dict()
        rebuilt = CvDocument.from_dict(as_dict)
        self.assertEqual(rebuilt.full_name, original.full_name)
        self.assertEqual(len(rebuilt.experience), len(original.experience))
        self.assertEqual(rebuilt.template_id, original.template_id)

    def test_from_dict_rejects_unknown_extra_keys(self):
        doc = CvDocument.from_dict({"full_name": "Maria",
                                      "evil_field": "drop me"})
        self.assertEqual(doc.full_name, "Maria")
        self.assertFalse(hasattr(doc, "evil_field"))

    def test_from_dict_handles_non_dict(self):
        # Defensive — AI extraction might return ``[]`` or ``None``.
        for junk in (None, [], "string", 42):
            doc = CvDocument.from_dict(junk)
            self.assertIsInstance(doc, CvDocument)
            self.assertEqual(doc.full_name, "")


if __name__ == "__main__":
    unittest.main()
