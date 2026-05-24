# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""PART 10 Loop 31: provider catalogue vs honesty-matrix consistency.

The doctrine document at ``docs/grant/15-ai-provider-honesty-matrix.md``
is binding on the code: every entry in
``company_discovery.ai_providers.PROVIDER_OPTIONS`` must have a row in
the matrix. This test catches drift — a new provider added to the
catalogue without an accompanying matrix row, or a matrix entry that
references a provider id no longer in the catalogue.

The doctrine doc is the user-facing tradeoff surface; silent drift
defeats the "honest at decision time" promise.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from company_discovery.ai_providers import PROVIDER_OPTIONS

MATRIX_DOC = (
    Path(__file__).resolve().parent.parent / "docs" / "grant" / "15-ai-provider-honesty-matrix.md"
)

# Map from PROVIDER_OPTIONS id -> human-readable label expected to
# appear in the matrix table. The matrix uses prose labels (e.g.
# "Ollama / local") rather than ids because the table is operator/
# evaluator-facing. The match below is "id-fragment appears in a row
# label" so re-wording the label slightly doesn't break the test.
_ID_TO_MATRIX_FRAGMENT: dict[str, str] = {
    "manual": "Manual handoff",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google_gemini": "Google Gemini",
    "deepseek": "DeepSeek",
    "openrouter": "OpenRouter",
    "ollama": "Ollama",
    "codex_cli": "Codex CLI",
    "claude_code": "Claude Code",
    "custom": "Custom",
    "managed": "Managed",
}


class HonestyMatrixConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix_text = MATRIX_DOC.read_text(encoding="utf-8")
        cls.provider_ids = {opt.id for opt in PROVIDER_OPTIONS}

    def test_matrix_doc_exists(self) -> None:
        self.assertTrue(MATRIX_DOC.exists(), msg=f"matrix doc missing: {MATRIX_DOC}")
        self.assertGreater(len(self.matrix_text), 2000, msg="matrix doc suspiciously small")

    def test_every_catalogue_provider_has_matrix_fragment(self) -> None:
        """Each PROVIDER_OPTIONS entry must have a recognised
        matrix-row fragment (per _ID_TO_MATRIX_FRAGMENT) AND that
        fragment must literally appear in the doc."""

        for provider_id in sorted(self.provider_ids):
            with self.subTest(provider_id=provider_id):
                self.assertIn(
                    provider_id,
                    _ID_TO_MATRIX_FRAGMENT,
                    msg=(
                        f"Provider id {provider_id!r} is in PROVIDER_OPTIONS but not "
                        f"mapped in _ID_TO_MATRIX_FRAGMENT — add a mapping AND a "
                        f"matrix-doc row before merging the new provider."
                    ),
                )
                fragment = _ID_TO_MATRIX_FRAGMENT[provider_id]
                self.assertIn(
                    fragment,
                    self.matrix_text,
                    msg=(
                        f"Provider id {provider_id!r} (matrix fragment {fragment!r}) "
                        f"is in PROVIDER_OPTIONS but the honesty-matrix doc does not "
                        f"mention it. Add a row to the matrix before shipping a new "
                        f"provider — the doctrine binds the code."
                    ),
                )

    def test_no_orphan_matrix_fragments(self) -> None:
        """A reverse check: every entry in _ID_TO_MATRIX_FRAGMENT must
        correspond to a current PROVIDER_OPTIONS id. Catches the
        opposite drift — a provider removed from the catalogue but
        still listed in the matrix-mapping test."""

        for provider_id in _ID_TO_MATRIX_FRAGMENT:
            with self.subTest(provider_id=provider_id):
                self.assertIn(
                    provider_id,
                    self.provider_ids,
                    msg=(
                        f"Test mapping references {provider_id!r} but it is no "
                        f"longer in PROVIDER_OPTIONS — either re-add the provider "
                        f"or drop the matrix-mapping entry + matrix row."
                    ),
                )

    def test_matrix_doc_documents_per_use_case(self) -> None:
        """Doctrine compliance check: the matrix must include per-use-
        case guidance (fit-scoring / cover-letter / CV consult / brief).
        Without that, the doc is a feature list, not honest guidance."""

        for use_case in (
            "Fit scoring",
            "Cover-letter",
            "CV consult",
            "Brief",
        ):
            with self.subTest(use_case=use_case):
                self.assertIn(
                    use_case,
                    self.matrix_text,
                    msg=f"matrix doc missing per-use-case section: {use_case}",
                )

    def test_matrix_doc_links_to_ai_act_and_source_class_doctrines(self) -> None:
        """Cross-reference completeness: the honesty matrix must link
        back to the AI Act compliance pack and the source-class
        hierarchy. Catches doctrine-doc-drift where one doctrine evolves
        without updating its peer references."""

        for reference in (
            "10-ai-act-compliance.md",
            "14-source-class-hierarchy.md",
            "08-cost-saving-doctrine.md",
        ):
            with self.subTest(reference=reference):
                self.assertIn(
                    reference,
                    self.matrix_text,
                    msg=f"matrix doc missing cross-reference to {reference}",
                )

    def test_matrix_doc_warns_about_deepseek_jurisdiction(self) -> None:
        """The DeepSeek row must surface the PRC-jurisdiction
        consideration. Specific to the privacy / data-residency
        honesty story; a row that hides this point would fail the
        doctrine's stated honesty bar."""

        # Loosely match because the prose could vary slightly across
        # edits. Both "PRC" mentions and a phrase that signals the
        # consideration (jurisdiction / data-residency) must appear.
        self.assertIn("PRC", self.matrix_text, msg="missing PRC mention for DeepSeek")
        self.assertTrue(
            re.search(r"(data[- ]residency|jurisdiction)", self.matrix_text, re.IGNORECASE)
            is not None,
            msg="DeepSeek row should signal the jurisdictional / data-residency note",
        )


if __name__ == "__main__":
    unittest.main()
