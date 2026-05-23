# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""AUDIT-46 — JSON-LD ``Organization`` / ``WebSite`` centralisation.

Pre-AUDIT-46 every legal page (privacy / terms / data-retention /
impressum, EN + DE) inlined a minimal ``WebSite`` definition inside
its ``WebPage.isPartOf`` field:

    "isPartOf": {
        "@type": "WebSite",
        "name": "Helpmefindthejob",
        "url": "https://helpmefindthejob.org/"
    }

Two problems:

1. The canonical ``WebSite`` and ``Organization`` entities live on
   ``/`` (index.html) at ``@id`` ``#website`` and ``#organization``
   with the full address, contact points, NGO/parent-org metadata,
   etc. The legal-page inline ``WebSite`` is a strict subset — it
   drops ``inLanguage``, ``publisher``, ``description``. Search
   engines see two different ``WebSite`` entities for the same site
   and have to pick one.
2. There's no ``publisher`` field on legal-page ``WebPage`` JSON-LD
   at all, so Google can't link the policy to the canonical
   Organization.

After AUDIT-46 every legal page references the canonical entities by
``@id`` instead of inlining a degraded copy:

    "isPartOf": { "@id": "https://helpmefindthejob.org/#website" },
    "publisher": { "@id": "https://helpmefindthejob.org/#organization" }

The @id targets resolve via the canonical ``/`` ``@graph`` block,
so search engines build a single, complete entity graph.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"

_LEGAL_PAGES = (
    "privacy.html",
    "privacy.de.html",
    "terms.html",
    "terms.de.html",
    "data-retention.html",
    "data-retention.de.html",
    "impressum.html",
    "impressum.en.html",
)

_CANONICAL_WEBSITE_ID = "https://helpmefindthejob.org/#website"
_CANONICAL_ORG_ID = "https://helpmefindthejob.org/#organization"


def _extract_first_jsonld(html: str) -> dict:
    """Pull out the first ``<script type="application/ld+json">`` block
    and parse it. Legal pages have a single WebPage block; index.html
    has a multi-entity @graph but we only need to know the @ids it
    declares."""
    match = re.search(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        html,
        re.DOTALL,
    )
    if not match:
        raise AssertionError("no application/ld+json block found")
    return json.loads(match.group(1))


class IndexHtmlDeclaresCanonicalIds(unittest.TestCase):
    """The @id targets that legal pages reference must exist on /."""

    def test_index_declares_organization_id(self) -> None:
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        data = _extract_first_jsonld(html)
        ids = [item.get("@id") for item in data.get("@graph", [])]
        self.assertIn(
            _CANONICAL_ORG_ID, ids,
            f"AUDIT-46: index.html @graph must declare {_CANONICAL_ORG_ID} so "
            "legal-page JSON-LD references resolve to a real entity.",
        )

    def test_index_declares_website_id(self) -> None:
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        data = _extract_first_jsonld(html)
        ids = [item.get("@id") for item in data.get("@graph", [])]
        self.assertIn(
            _CANONICAL_WEBSITE_ID, ids,
            f"AUDIT-46: index.html @graph must declare {_CANONICAL_WEBSITE_ID}.",
        )


class LegalPagesReferenceCanonicalIds(unittest.TestCase):
    """Every legal page must use @id references, not inline duplicates."""

    def test_every_legal_page_references_canonical_website_id(self) -> None:
        for filename in _LEGAL_PAGES:
            with self.subTest(filename=filename):
                html = (STATIC / filename).read_text(encoding="utf-8")
                data = _extract_first_jsonld(html)
                is_part_of = data.get("isPartOf")
                self.assertIsInstance(
                    is_part_of, dict,
                    f"AUDIT-46: {filename} WebPage.isPartOf must be an object",
                )
                self.assertEqual(
                    is_part_of.get("@id"), _CANONICAL_WEBSITE_ID,
                    f"AUDIT-46: {filename} must reference canonical WebSite via @id, "
                    f"got {is_part_of!r}",
                )
                # Inline @type/name/url duplication is the regression we're guarding
                # against. Pure @id reference has neither.
                self.assertNotIn(
                    "@type", is_part_of,
                    f"AUDIT-46: {filename} isPartOf still inlines @type — should be "
                    "a pure @id reference to the canonical entity.",
                )

    def test_every_legal_page_declares_canonical_publisher(self) -> None:
        for filename in _LEGAL_PAGES:
            with self.subTest(filename=filename):
                html = (STATIC / filename).read_text(encoding="utf-8")
                data = _extract_first_jsonld(html)
                publisher = data.get("publisher")
                self.assertIsInstance(
                    publisher, dict,
                    f"AUDIT-46: {filename} WebPage.publisher must be set",
                )
                self.assertEqual(
                    publisher.get("@id"), _CANONICAL_ORG_ID,
                    f"AUDIT-46: {filename} publisher must reference canonical "
                    f"Organization via @id, got {publisher!r}",
                )

    def test_no_legal_page_inlines_a_website_or_organization_definition(self) -> None:
        # Cheap textual tripwire: the inline ``"@type": "WebSite"`` or
        # ``"@type": "Organization"`` patterns must not reappear in any
        # legal page. A reintroduction means someone duplicated a
        # canonical entity instead of using @id reference.
        forbidden_patterns = (
            '"@type": "WebSite"',
            '"@type": "Organization"',
            '"@type":"WebSite"',
            '"@type":"Organization"',
        )
        for filename in _LEGAL_PAGES:
            html = (STATIC / filename).read_text(encoding="utf-8")
            for pat in forbidden_patterns:
                with self.subTest(filename=filename, pattern=pat):
                    self.assertNotIn(
                        pat, html,
                        f"AUDIT-46: {filename} re-inlines a {pat!r} JSON-LD entity — "
                        "use @id reference to the canonical declaration on / instead.",
                    )


if __name__ == "__main__":
    unittest.main()
