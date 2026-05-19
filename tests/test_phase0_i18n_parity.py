# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Phase 0 — i18n parity gate (generalised across all locale bundles).

Invariants enforced by this module:

1. ``en.json`` is the source of truth. Every other locale bundle must
   share its key set exactly — drift means a non-EN user sees an
   English fallback (or a missing-key error) for any string added or
   renamed without translation.

2. Every ``data-i18n="…"`` reference in ``static/index.html`` must
   resolve in EVERY locale bundle.

3. Non-EN locales must not have blank values. ``en.json`` is excluded
   from this check — a few placeholder keys (e.g., test scaffolding)
   may legitimately be empty in the source.

4. The German-bureaucratic-conventions preservation rule
   (``docs/translating.md``) is enforced for any non-EN locale: where
   ``en.json`` references a documented bureaucratic term verbatim, the
   locale bundle must keep the term verbatim in the same key's value.
   Substring + case-insensitive match — the term may have surrounding
   translated text.

5. HTML inline fallback text must match ``en.json`` (subject to
   whitespace + HTML-entity normalisation). Drift here means the
   in-DOM fallback diverges from the source-of-truth bundle and would
   render the wrong English in the (rare) JS-disabled path.

The parity test walks every ``static/i18n/*.json`` automatically — no
EN+DE hard-code. Adding Arabic / Ukrainian / Turkish / Romanian (per
``docs/translating.md``) only requires dropping the bundle file in.

Run as part of the regular test suite. Failures block deploy.
"""

from __future__ import annotations

import html as html_lib
import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


I18N_DIR = REPO_ROOT / "static" / "i18n"
INDEX_HTML = REPO_ROOT / "static" / "index.html"
SOURCE_LOCALE = "en"


# Source-of-truth list mirrors `docs/translating.md`'s
# "German-bureaucratic-conventions preservation rule" section. Terms
# that have legal-specific meaning in the German labour-administration
# context — translating them strips the legal signal. When this list
# grows, update `docs/translating.md` in the same commit.
PRESERVED_TERMS: tuple[str, ...] = (
    # Residency / work-rights
    "Anerkennung",
    "§16d",
    "§24",
    "Blue Card",
    "Blaue Karte",
    "Freizügigkeit",
    "Anmeldung",
    # Qualification recognition
    "Anabin",
    "BIBB",
    "Approbation",
    "Zeugnisbewertung",
    # Career-shift context
    "Wiedereinstieg",
    "Familienpause",
    "Auffrischung",
    # Employment framework
    "TVöD",
    "Ausbildung",
    "Bewerbungsmappe",
    "Lebenslauf",
    "Tarifvertrag",
    "Beamtenstatus",
    # Social-benefit framework
    "Bürgergeld",
    "ALG I",
    "ALG II",
    "Optionskommune",
    # Industry-specific qualifiers
    "Handwerk",
    "Krankenpfleger",
    "Pflegefachkraft",
    "Altenpflegerin",
    "Anlagenmechaniker SHK",
)


def _locale_bundles() -> dict[str, dict[str, str]]:
    """Load every ``static/i18n/*.json`` keyed by locale code."""
    bundles: dict[str, dict[str, str]] = {}
    for path in sorted(I18N_DIR.glob("*.json")):
        bundles[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return bundles


_NESTED_I18N_BLOCK = re.compile(
    r"<(?P<tag>[A-Za-z][\w-]*)\b[^>]*\bdata-i18n=\"[^\"]+\"[^>]*>.*?</(?P=tag)>",
    re.DOTALL,
)


def _strip_tags(html_fragment: str) -> str:
    """Remove inline HTML tags + collapse whitespace + decode entities.

    Used for the HTML-fallback drift check — we compare the rendered
    text content of a ``data-i18n`` element against ``en.json``'s
    value. The fragment may contain inline spans / icons / etc.;
    flattening to bare text is the comparison surface.

    Nested ``data-i18n`` elements are removed BEFORE tag-stripping —
    they carry their own i18n key and shouldn't pollute the outer
    element's fallback comparison. (E.g., a ``<p data-i18n="empty">No
    active search. <a data-i18n="hint">Type ...</a></p>`` has its outer
    fallback compared as ``"No active search."``, not the concatenated
    multi-element text.)
    """
    fragment = _NESTED_I18N_BLOCK.sub("", html_fragment)
    text = re.sub(r"<[^>]+>", "", fragment)
    text = html_lib.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_for_comparison(value: str) -> str:
    """Same whitespace/entity normalisation as ``_strip_tags`` but
    starting from a JSON value (already a plain string, no HTML
    tags). Returned in a form directly comparable to a stripped
    HTML fragment."""
    return re.sub(r"\s+", " ", html_lib.unescape(value)).strip()


def _data_i18n_pairs(html: str) -> list[tuple[str, str]]:
    """Yield ``(key, inner_html)`` pairs for every
    ``<element data-i18n="key">inner</element>`` in the document.

    Multi-attribute element openings are handled (the regex doesn't
    assume ``data-i18n`` is the first attribute). Self-closing tags
    or void elements (e.g., ``<input data-i18n="..." />``) have no
    inner text — they're skipped because the fallback contract only
    applies to elements that render their own text content.
    """
    pattern = re.compile(
        r"<(?P<tag>[A-Za-z][\w-]*)\b(?P<attrs>[^>]*)\bdata-i18n=\"(?P<key>[^\"]+)\""
        r"(?P<rest>[^>]*)>"
        r"(?P<inner>.*?)"
        r"</(?P=tag)>",
        re.DOTALL,
    )
    return [(m.group("key"), m.group("inner")) for m in pattern.finditer(html)]


class I18nParityTests(unittest.TestCase):
    """Generalised parity gate — walks every ``static/i18n/*.json``."""

    def test_all_locales_have_identical_key_sets(self) -> None:
        bundles = _locale_bundles()
        self.assertIn(SOURCE_LOCALE, bundles, "en.json must exist as the source of truth")
        en_keys = set(bundles[SOURCE_LOCALE])
        report: list[str] = []
        for locale, data in bundles.items():
            if locale == SOURCE_LOCALE:
                continue
            locale_keys = set(data)
            missing = sorted(en_keys - locale_keys)
            extra = sorted(locale_keys - en_keys)
            if missing:
                report.append(f"{locale}.json missing keys from en.json: {missing}")
            if extra:
                report.append(f"{locale}.json has keys not in en.json: {extra}")
        self.assertFalse(report, "\n".join(report))

    def test_every_html_reference_resolves_in_all_locales(self) -> None:
        bundles = _locale_bundles()
        html = INDEX_HTML.read_text(encoding="utf-8")
        keys_in_html = set(re.findall(r'data-i18n="([^"]+)"', html))
        report: list[str] = []
        for locale, data in bundles.items():
            missing = sorted(k for k in keys_in_html if k not in data)
            if missing:
                report.append(
                    f"data-i18n keys referenced in HTML but absent from {locale}.json: {missing}"
                )
        self.assertFalse(report, "\n".join(report))

    def test_no_blank_translations_in_non_source_locales(self) -> None:
        bundles = _locale_bundles()
        report: list[str] = []
        for locale, data in bundles.items():
            if locale == SOURCE_LOCALE:
                # en.json may legitimately have placeholder-blank values.
                continue
            blanks = sorted(k for k, v in data.items() if not isinstance(v, str) or not v.strip())
            if blanks:
                report.append(f"{locale}.json has blank or non-string values for: {blanks}")
        self.assertFalse(report, "\n".join(report))

    def test_preserved_german_terms_are_kept_verbatim(self) -> None:
        """German bureaucratic / labour-administration terms (per
        ``docs/translating.md``) must appear verbatim in every non-EN
        locale's value whenever ``en.json`` uses them in the same key.

        Substring + case-insensitive — surrounding text may be
        translated; only the bureaucratic term itself must be
        preserved. Where ``en.json`` doesn't use a term, the test
        skips silently (the list is a superset of "terms that may
        ever appear in en.json")."""
        bundles = _locale_bundles()
        en_bundle = bundles[SOURCE_LOCALE]

        # Pre-compute: for each preserved term, which en.json keys
        # actually contain it. Avoids re-scanning en.json per locale.
        term_keys: dict[str, list[str]] = {}
        for term in PRESERVED_TERMS:
            term_lower = term.lower()
            matches = [
                key
                for key, value in en_bundle.items()
                if isinstance(value, str) and term_lower in value.lower()
            ]
            if matches:
                term_keys[term] = matches

        report: list[str] = []
        for locale, data in bundles.items():
            if locale == SOURCE_LOCALE:
                continue
            for term, keys in term_keys.items():
                term_lower = term.lower()
                for key in keys:
                    value = data.get(key, "")
                    if not isinstance(value, str) or term_lower not in value.lower():
                        report.append(
                            f"{locale}.json: key {key!r} translates the preserved "
                            f"German term {term!r} — keep the term verbatim per "
                            "docs/translating.md German-bureaucratic-conventions "
                            "preservation rule."
                        )
        self.assertFalse(report, "\n".join(report))

    def test_html_inline_fallback_matches_en_json(self) -> None:
        """``<element data-i18n="key">FALLBACK</element>``: FALLBACK
        text content must match ``en.json[key]`` after whitespace +
        HTML-entity normalisation.

        Without this check, an HTML edit could drift the inline
        fallback away from ``en.json`` (e.g., a refactor renames the
        UI label in HTML but forgets ``en.json``) and the test would
        silently pass — the key still exists, the parity test stays
        green, but a JS-disabled user (rare but real) sees the wrong
        text.

        Elements with empty inner text are not enforced — they signal
        "use the bundle, no fallback needed."
        """
        en_bundle = _locale_bundles()[SOURCE_LOCALE]
        html = INDEX_HTML.read_text(encoding="utf-8")
        pairs = _data_i18n_pairs(html)
        report: list[str] = []
        for key, inner in pairs:
            inner_text = _strip_tags(inner)
            if not inner_text:
                # Empty fallback — caller relies entirely on the
                # bundle. Not a drift case.
                continue
            if key not in en_bundle:
                # Already surfaced by `test_every_html_reference_…`.
                continue
            en_value = _normalize_for_comparison(en_bundle[key])
            if inner_text != en_value:
                report.append(
                    f"data-i18n={key!r}: HTML fallback {inner_text!r} "
                    f"differs from en.json value {en_value!r}"
                )
        self.assertFalse(
            report,
            "HTML inline-fallback drift from en.json (first 20 shown):\n"
            + "\n".join(report[:20])
            + ("\n  …" if len(report) > 20 else ""),
        )


if __name__ == "__main__":
    unittest.main()
