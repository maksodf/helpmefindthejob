# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Round-3 tests: regional template expansion + PDF extraction."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.cv_extract import (
    CvExtractError,
    extract_pdf_text,
    extract_text,
)
from company_discovery.watchlist_templates import list_templates


class RegionalExpansionTests(unittest.TestCase):
    EXPECTED = (
        "madrid_tech_es",
        "barcelona_tech_es",
        "stockholm_tech_se",
        "copenhagen_tech_dk",
        "warsaw_tech_pl",
    )

    def test_all_new_templates_present(self) -> None:
        ids = {item["id"] for item in list_templates()}
        for tid in self.EXPECTED:
            self.assertIn(tid, ids)

    def test_madrid_visible_to_finance_persona(self) -> None:
        finance_ids = {item["id"] for item in list_templates("finance")}
        self.assertIn("madrid_tech_es", finance_ids)

    def test_warsaw_visible_to_tech_persona(self) -> None:
        tech_ids = {item["id"] for item in list_templates("tech")}
        self.assertIn("warsaw_tech_pl", tech_ids)


def _build_minimal_pdf(text: str) -> bytes:
    """Build a tiny single-page PDF that ``pypdf`` can read.

    We use ``pypdf``'s own writer so the test doesn't depend on
    hand-rolled byte layouts.
    """

    from pypdf import PdfWriter
    from pypdf.generic import (
        ArrayObject,
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
        NumberObject,
    )

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    # Build a minimal text-showing content stream.
    stream = DecodedStreamObject()
    safe = text.replace("(", r"\(").replace(")", r"\)")
    stream.set_data(f"BT /F1 18 Tf 50 700 Td ({safe}) Tj ET".encode("latin-1"))
    page[NameObject("/Contents")] = stream
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
        }
    )
    page[NameObject("/Resources")] = resources
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


class PdfExtractTests(unittest.TestCase):
    def test_extract_text_from_minimal_pdf(self) -> None:
        try:
            blob = _build_minimal_pdf("HELLO PDF CV TEXT")
        except ImportError:
            self.skipTest("pypdf not installed locally")
        out = extract_pdf_text(blob)
        self.assertIn("HELLO", out.upper())

    def test_extract_text_dispatches_pdf(self) -> None:
        try:
            blob = _build_minimal_pdf("DISPATCH OK")
        except ImportError:
            self.skipTest("pypdf not installed locally")
        out = extract_text("cv.pdf", blob)
        self.assertIn("DISPATCH", out.upper())

    def test_corrupt_pdf_raises(self) -> None:
        with self.assertRaises(CvExtractError):
            extract_pdf_text(b"NOT A PDF")


if __name__ == "__main__":
    unittest.main()
