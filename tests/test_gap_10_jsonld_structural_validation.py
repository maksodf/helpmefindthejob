# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""GAP-10 (post-self-audit, 2026-05-23): JSON-LD structural validation.

Google's Rich Results Test (https://search.google.com/test/rich-results)
is the authoritative validator, but we can't run it from this test
environment. This file enforces the structural invariants Google
checks for — schema.org-shape correctness, cross-page ``@id``
references resolving, ISO-8601 dates, absolute HTTPS URLs, valid
email formats in contactPoint — so we catch shape regressions before
they ship to prod.

Run the actual Google validator post-deploy at:
https://search.google.com/test/rich-results?url=https://helpmefindthejob.org/
to confirm Google accepts what we ship.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"

_CANONICAL_ORG_ID = "https://helpmefindthejob.org/#organization"
_CANONICAL_WEB_ID = "https://helpmefindthejob.org/#website"
_HTTPS_URL_RX = re.compile(r"^https://[a-zA-Z0-9._/-]+/?$")
_EMAIL_RX = re.compile(r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
_ISO_DATE_RX = re.compile(r"^\d{4}(-\d{2}(-\d{2}([T ]\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:\d{2})?)?)?)?$")

_LEGAL_PAGES = (
    "privacy.html", "privacy.de.html",
    "terms.html", "terms.de.html",
    "data-retention.html", "data-retention.de.html",
    "impressum.html", "impressum.en.html",
)


def _extract_jsonld(filename: str) -> dict:
    html = (STATIC / filename).read_text(encoding="utf-8")
    m = re.search(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        html,
        re.DOTALL,
    )
    if not m:
        raise AssertionError(f"{filename} has no application/ld+json block")
    return json.loads(m.group(1))


class IndexJsonLdGraph(unittest.TestCase):
    """Validate the canonical @graph on /."""

    def setUp(self) -> None:
        self.data = _extract_jsonld("index.html")

    def test_has_context(self) -> None:
        self.assertEqual(self.data.get("@context"), "https://schema.org")

    def test_graph_is_a_list(self) -> None:
        self.assertIsInstance(self.data.get("@graph"), list)
        self.assertGreater(len(self.data["@graph"]), 0)

    def test_organization_entity_complete(self) -> None:
        org = next(
            (item for item in self.data["@graph"]
             if item.get("@id") == _CANONICAL_ORG_ID),
            None,
        )
        self.assertIsNotNone(org, "canonical Organization @id missing from @graph")
        # Required for NGO claim
        self.assertIn("name", org)
        self.assertIn("url", org)
        self.assertTrue(_HTTPS_URL_RX.match(org["url"]),
                        f"Organization.url must be HTTPS, got {org['url']!r}")
        # Address required for Impressum-equivalent
        address = org.get("address")
        self.assertIsInstance(address, dict)
        self.assertEqual(address.get("@type"), "PostalAddress")
        for field in ("streetAddress", "postalCode", "addressLocality", "addressCountry"):
            self.assertIn(field, address, f"address missing {field}")
        # ContactPoint must include at least one entry
        contacts = org.get("contactPoint")
        self.assertIsInstance(contacts, list)
        self.assertGreater(len(contacts), 0)
        for cp in contacts:
            self.assertEqual(cp.get("@type"), "ContactPoint")
            self.assertIn("contactType", cp)
            # Either email OR url is required
            self.assertTrue(
                cp.get("email") or cp.get("url"),
                f"contactPoint must have email or url, got {cp!r}",
            )
            if "email" in cp:
                self.assertRegex(cp["email"], _EMAIL_RX,
                                 f"invalid email: {cp['email']!r}")
        # foundingDate is ISO-8601
        if "foundingDate" in org:
            self.assertRegex(str(org["foundingDate"]), _ISO_DATE_RX)
        # parentOrganization → The Commons Conservancy
        parent = org.get("parentOrganization")
        if parent:
            self.assertEqual(parent.get("@type"), "Organization")
            self.assertIn("Commons Conservancy", parent.get("name", ""))

    def test_website_entity_complete(self) -> None:
        web = next(
            (item for item in self.data["@graph"]
             if item.get("@id") == _CANONICAL_WEB_ID),
            None,
        )
        self.assertIsNotNone(web, "canonical WebSite @id missing")
        self.assertEqual(web.get("@type"), "WebSite")
        self.assertTrue(_HTTPS_URL_RX.match(web.get("url", "")))
        # Publisher must point at the canonical Organization @id
        publisher = web.get("publisher", {})
        self.assertEqual(publisher.get("@id"), _CANONICAL_ORG_ID,
                         "WebSite.publisher must @id-reference the canonical Organization")

    def test_software_application_consistent(self) -> None:
        sw = next(
            (item for item in self.data["@graph"]
             if item.get("@type") == "SoftwareApplication"),
            None,
        )
        if sw is None:
            self.skipTest("no SoftwareApplication entity")
        self.assertIn("license", sw)
        self.assertIn("apache", sw["license"].lower(),
                      f"license should reference Apache 2.0, got {sw['license']!r}")
        # softwareVersion must match APP_VERSION from app.py — see
        # tests/test_changelog_currency.py for the version-drift guard
        self.assertIn("softwareVersion", sw)


class LegalPageJsonLdReferences(unittest.TestCase):
    """Each legal page's JSON-LD must reference the canonical @ids and
    omit any inline duplicates."""

    def test_every_legal_page_publisher_refs_canonical_org(self) -> None:
        for filename in _LEGAL_PAGES:
            with self.subTest(filename=filename):
                data = _extract_jsonld(filename)
                self.assertEqual(
                    data.get("publisher", {}).get("@id"), _CANONICAL_ORG_ID,
                    f"{filename}: publisher must reference canonical Organization @id",
                )

    def test_every_legal_page_ispartof_refs_canonical_website(self) -> None:
        for filename in _LEGAL_PAGES:
            with self.subTest(filename=filename):
                data = _extract_jsonld(filename)
                self.assertEqual(
                    data.get("isPartOf", {}).get("@id"), _CANONICAL_WEB_ID,
                    f"{filename}: isPartOf must reference canonical WebSite @id",
                )

    def test_every_legal_page_declares_webpage_type(self) -> None:
        for filename in _LEGAL_PAGES:
            with self.subTest(filename=filename):
                data = _extract_jsonld(filename)
                self.assertEqual(data.get("@type"), "WebPage",
                                 f"{filename} must declare @type WebPage")

    def test_every_legal_page_url_is_absolute_https(self) -> None:
        for filename in _LEGAL_PAGES:
            with self.subTest(filename=filename):
                data = _extract_jsonld(filename)
                url = data.get("url", "")
                self.assertTrue(_HTTPS_URL_RX.match(url),
                                f"{filename} url must be absolute HTTPS, got {url!r}")
                self.assertIn("helpmefindthejob.org", url,
                              f"{filename} url must point at the canonical host")

    def test_every_legal_page_declares_in_language(self) -> None:
        for filename in _LEGAL_PAGES:
            with self.subTest(filename=filename):
                data = _extract_jsonld(filename)
                lang = data.get("inLanguage")
                self.assertIsInstance(lang, list,
                                      f"{filename} inLanguage must be a list")
                for code in lang:
                    self.assertIn(code, ("en", "de"))


class CrossReferenceIntegrity(unittest.TestCase):
    """Every @id referenced by a legal page must EXIST in some entity
    graph. The canonical @ids live in index.html; legal pages point at
    them. If anyone deletes or renames an @id in the source graph,
    the legal pages become orphan references — invalid JSON-LD."""

    def test_every_legal_page_reference_resolves_to_an_index_entity(self) -> None:
        index_graph = _extract_jsonld("index.html").get("@graph", [])
        declared_ids = {item.get("@id") for item in index_graph if item.get("@id")}
        for filename in _LEGAL_PAGES:
            data = _extract_jsonld(filename)
            for ref_path in ("publisher", "isPartOf"):
                referenced_id = data.get(ref_path, {}).get("@id")
                with self.subTest(filename=filename, ref=ref_path):
                    self.assertIn(
                        referenced_id, declared_ids,
                        f"GAP-10: {filename}.{ref_path} references @id "
                        f"{referenced_id!r} which is NOT declared in "
                        f"index.html @graph. Orphan reference.",
                    )


if __name__ == "__main__":
    unittest.main()
