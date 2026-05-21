# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 #80 — cover-letter section parser contract (JS source).

The JS-side parsers parseCoverLetterSections + parseCitations in
static/app.js are the canonical implementation. This Python file
asserts the JS source carries the expected anchors so the contract
documented in docs/grant/08-cost-saving-doctrine.md (and #80) doesn't
silently drift away from what the AI prompt template at
analysis.py:build_cover_letter_brief_prompt is designed to emit.

Behavior testing of the JS itself happens at the browser/Playwright
level (see tests/e2e/typing_label_smoke.py for the existing
JS-behavior pattern). This file is the source-level pin so refactors
to the parser don't accidentally drop the section markers.
"""

from __future__ import annotations

import pathlib
import re
import unittest

APP_JS = pathlib.Path(__file__).resolve().parent.parent / "static" / "app.js"


class CoverLetterSectionParserContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = APP_JS.read_text(encoding="utf-8")

    def test_parser_function_present(self) -> None:
        self.assertIn("function parseCoverLetterSections(", self.text)
        self.assertIn("function parseCitations(", self.text)
        self.assertIn("function renderCoverLetterSections(", self.text)

    def test_parser_matches_subject_line_marker(self) -> None:
        # Pin the regex anchor: prompt section 1 is "Subject line /
        # opening salutation" — parser must split on it.
        self.assertIn(r"1\.\s*Subject\s*line", self.text)

    def test_parser_matches_letter_body_marker(self) -> None:
        self.assertIn(r"2\.\s*Cover\s*letter\s*body", self.text)

    def test_parser_matches_editing_notes_marker(self) -> None:
        self.assertIn(r"3\.\s*Editing\s*notes", self.text)

    def test_parser_matches_draft_assumptions_marker(self) -> None:
        self.assertIn(r"4\.\s*Draft\s*assumptions", self.text)

    def test_parser_matches_source_citations_marker(self) -> None:
        self.assertIn(r"5\.\s*Source\s*citations", self.text)
        # DE-locale alias
        self.assertIn(r"##\s*Quellen", self.text)

    def test_citations_parser_handles_cv_jd_inference_tags(self) -> None:
        # The 3-tag set must be detected by the citation parser
        self.assertIn(r"\[(CV|JD|Inference)\]", self.text)

    def test_render_function_targets_known_dom_ids(self) -> None:
        # The HTML structure depends on these specific element ids;
        # if any is renamed, the renderer breaks silently in the
        # browser. Pin them.
        for dom_id in (
            "coverLetterSectionSubject",
            "coverLetterSectionBody",
            "coverLetterSectionEditingNotes",
            "coverLetterSectionAssumptions",
            "coverLetterCitationsList",
            "coverLetterCopyBodyBtn",
        ):
            self.assertIn(dom_id, self.text, msg=f"missing dom-id {dom_id}")

    def test_copy_body_handler_uses_clipboard_api(self) -> None:
        # Copy-letter-body should use the modern Clipboard API with
        # a fallback toast for blocked browsers.
        self.assertIn("navigator.clipboard", self.text)

    def test_html_includes_all_section_panels(self) -> None:
        html_path = APP_JS.parent / "index.html"
        html = html_path.read_text(encoding="utf-8")
        for dom_id in (
            "coverLetterSectionsPanel",
            "coverLetterSectionSubject",
            "coverLetterSectionBody",
            "coverLetterSectionEditingNotes",
            "coverLetterSectionAssumptions",
            "coverLetterCitationsList",
            "coverLetterCopyBodyBtn",
        ):
            self.assertIn(dom_id, html, msg=f"missing HTML id {dom_id}")


if __name__ == "__main__":
    unittest.main()
