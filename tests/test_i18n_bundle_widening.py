# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Contract tests for the backend i18n bundle helper + the #75 wiring.

Closes phase2-backlog item #75:

1. ``i18n_bundle.translate(key, locale)`` resolves correctly with
   EN fallback when the locale doesn't carry the key.
2. ``widening.widening_label(affordance, locale)`` returns the
   translated label for DE and the EN default otherwise.
3. Every ``backend.*`` key shipped in #75 is present in BOTH
   en.json AND de.json (parity contract — DE users must not see
   accidentally-untranslated strings).
4. The frontend ``static/app.js`` ``TYPING_LABELS`` schedule
   carries the ``backend.typing.*`` keys it expects to find in
   the bundles.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from company_discovery import i18n_bundle
from company_discovery.widening import (
    DROP_SENIORITY,
    TRY_LATERALS,
    WIDEN_LOCATION,
    WIDENING_LABEL,
    widening_label,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
EN_BUNDLE = REPO_ROOT / "static" / "i18n" / "en.json"
DE_BUNDLE = REPO_ROOT / "static" / "i18n" / "de.json"


def _load_bundle(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# i18n_bundle.translate substrate
# ---------------------------------------------------------------------------


class I18nBundleTranslate(unittest.TestCase):
    def setUp(self):
        # Fresh module state for each test so cross-test pollution
        # doesn't hide bugs.
        i18n_bundle._reset_for_test()

    def test_translate_de_returns_de_string(self):
        result = i18n_bundle.translate("backend.widening.widen_location", "de")
        self.assertEqual(result, "Standort erweitert")

    def test_translate_en_returns_en_string(self):
        result = i18n_bundle.translate("backend.widening.widen_location", "en")
        self.assertEqual(result, "Widened location")

    def test_translate_unknown_locale_falls_back_to_en(self):
        result = i18n_bundle.translate("backend.widening.widen_location", "fr")
        self.assertEqual(result, "Widened location")

    def test_translate_unknown_key_falls_back_to_default(self):
        result = i18n_bundle.translate("no.such.key", "de", default="fallback")
        self.assertEqual(result, "fallback")

    def test_translate_unknown_key_with_no_default_returns_key(self):
        result = i18n_bundle.translate("no.such.key", "de")
        self.assertEqual(result, "no.such.key")

    def test_translate_locale_normalisation_lowercases(self):
        result = i18n_bundle.translate("backend.widening.widen_location", "DE")
        self.assertEqual(result, "Standort erweitert")

    def test_translate_strips_region_code(self):
        """en-US / en_US / en should all resolve to the en bundle."""

        for locale in ("en-US", "en_US", "en", "EN"):
            with self.subTest(locale=locale):
                result = i18n_bundle.translate("backend.widening.widen_location", locale)
                self.assertEqual(result, "Widened location")

    def test_translate_none_locale_falls_back_to_en(self):
        result = i18n_bundle.translate("backend.widening.widen_location", None)
        self.assertEqual(result, "Widened location")

    def test_translate_empty_locale_falls_back_to_en(self):
        result = i18n_bundle.translate("backend.widening.widen_location", "")
        self.assertEqual(result, "Widened location")

    def test_available_locales_includes_en_and_de(self):
        locales = i18n_bundle.available_translation_locales()
        self.assertIn("en", locales)
        self.assertIn("de", locales)


# ---------------------------------------------------------------------------
# widening_label accessor
# ---------------------------------------------------------------------------


class WideningLabelAccessor(unittest.TestCase):
    def setUp(self):
        i18n_bundle._reset_for_test()

    def test_widen_location_de(self):
        self.assertEqual(widening_label(WIDEN_LOCATION, "de"), "Standort erweitert")

    def test_widen_location_en(self):
        self.assertEqual(widening_label(WIDEN_LOCATION, "en"), "Widened location")

    def test_drop_seniority_de(self):
        self.assertEqual(widening_label(DROP_SENIORITY, "de"), "Senioritätsangabe entfernt")

    def test_try_laterals_de(self):
        self.assertEqual(widening_label(TRY_LATERALS, "de"), "Seitenrollen ausprobiert")

    def test_unknown_affordance_falls_back_to_slug(self):
        result = widening_label("garbage_affordance", "de")
        self.assertEqual(result, "garbage_affordance")

    def test_no_locale_defaults_to_en(self):
        self.assertEqual(widening_label(WIDEN_LOCATION), "Widened location")


# ---------------------------------------------------------------------------
# Bundle parity — EVERY backend.* key must exist in BOTH bundles
# ---------------------------------------------------------------------------


class BackendKeyParity(unittest.TestCase):
    """If a backend.* key exists in en.json but not de.json (or
    vice versa), users of the missing locale see the key string
    rendered raw — bad UX. This test enforces strict parity."""

    def setUp(self):
        self.en = _load_bundle(EN_BUNDLE)
        self.de = _load_bundle(DE_BUNDLE)

    def test_every_backend_key_in_en_is_in_de(self):
        en_backend = {k for k in self.en if k.startswith("backend.")}
        de_backend = {k for k in self.de if k.startswith("backend.")}
        missing = en_backend - de_backend
        self.assertEqual(
            missing,
            set(),
            f"keys in en.json but missing from de.json: {missing}",
        )

    def test_every_backend_key_in_de_is_in_en(self):
        en_backend = {k for k in self.en if k.startswith("backend.")}
        de_backend = {k for k in self.de if k.startswith("backend.")}
        missing = de_backend - en_backend
        self.assertEqual(
            missing,
            set(),
            f"keys in de.json but missing from en.json: {missing}",
        )

    def test_backend_keys_not_empty_strings(self):
        for bundle, name in ((self.en, "en"), (self.de, "de")):
            for key, value in bundle.items():
                if key.startswith("backend."):
                    with self.subTest(bundle=name, key=key):
                        self.assertTrue(
                            value,
                            f"{name}.json[{key!r}] is empty",
                        )

    def test_de_strings_are_not_equal_to_en_strings(self):
        """If a DE string equals the EN string verbatim, it's
        probably an untranslated placeholder. Allowed for proper
        nouns + acronyms (CV / Anschreiben / Quellen / etc.) but
        we don't expect those in the widening / typing surface."""

        verbatim_allowed = {
            # Proper nouns + technical terms that legitimately
            # stay the same across locales
        }
        for key, en_value in self.en.items():
            if not key.startswith("backend."):
                continue
            de_value = self.de.get(key, "")
            if not de_value:
                continue
            if key in verbatim_allowed:
                continue
            # Allow if the EN value is itself untranslatable (URLs,
            # numbers, or contains only ASCII punctuation).
            if not any(c.isalpha() for c in en_value):
                continue
            with self.subTest(key=key):
                self.assertNotEqual(
                    de_value,
                    en_value,
                    f"de.json[{key!r}] is identical to en.json — looks untranslated",
                )


# ---------------------------------------------------------------------------
# app.js consumes the right keys
# ---------------------------------------------------------------------------


class FrontendTypingLabelsReferenceBundleKeys(unittest.TestCase):
    """Source-level check: the frontend TYPING_LABELS_SCHEDULE
    references backend.typing.* keys. Each referenced key MUST
    exist in the i18n bundle, or DE users see the fallback string
    (English) instead of the translation."""

    def setUp(self):
        self.app_js = (REPO_ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.en = _load_bundle(EN_BUNDLE)
        self.de = _load_bundle(DE_BUNDLE)

    def test_app_js_references_backend_typing_keys(self):
        """The new wiring should reference backend.typing.* keys."""

        self.assertIn("backend.typing.search.0", self.app_js)
        self.assertIn("backend.typing.tailor.0", self.app_js)
        self.assertIn("backend.typing.letter.0", self.app_js)
        self.assertIn("backend.typing.default", self.app_js)

    def test_no_more_hardcoded_typing_strings(self):
        """The pre-wiring code had `text: "Querying job boards..."`
        literals. Post-wiring those become `key: "backend.typing.*"`
        + `fallback: "..."`. Verify the schedule entries use the
        new shape."""

        # The new shape uses key+fallback rather than just text.
        # The schedule object is named TYPING_LABELS_SCHEDULE.
        self.assertIn("TYPING_LABELS_SCHEDULE", self.app_js)
        # Each schedule entry has a `key:` field
        self.assertIn('key: "backend.typing.', self.app_js)

    def test_every_referenced_typing_key_has_en_translation(self):
        """Extract every backend.typing.* key referenced in app.js
        and verify it's in en.json. Catches the drift bug where
        someone references a key without adding it to the bundle."""

        import re

        keys = set(re.findall(r"backend\.typing\.[a-z]+(?:\.\d+)?", self.app_js))
        # Strip "default" which doesn't have an integer suffix
        for key in keys:
            with self.subTest(key=key):
                self.assertIn(
                    key,
                    self.en,
                    f"app.js references {key} but en.json has no entry",
                )

    def test_every_referenced_typing_key_has_de_translation(self):
        import re

        keys = set(re.findall(r"backend\.typing\.[a-z]+(?:\.\d+)?", self.app_js))
        for key in keys:
            with self.subTest(key=key):
                self.assertIn(
                    key,
                    self.de,
                    f"app.js references {key} but de.json has no entry",
                )


# ---------------------------------------------------------------------------
# Drift guards
# ---------------------------------------------------------------------------


class DriftGuards(unittest.TestCase):
    def test_widening_label_dict_still_has_all_three_affordances(self):
        """Drift guard: if WIDEN_LOCATION / DROP_SENIORITY /
        TRY_LATERALS keys change in widening.py, the bundles must
        be updated to match."""

        self.assertIn(WIDEN_LOCATION, WIDENING_LABEL)
        self.assertIn(DROP_SENIORITY, WIDENING_LABEL)
        self.assertIn(TRY_LATERALS, WIDENING_LABEL)

    def test_bundle_keys_match_widening_constants(self):
        """The bundle key naming convention is
        backend.widening.<affordance_slug>. Verify each affordance
        has both 'past tense label' AND 'action label'."""

        en = _load_bundle(EN_BUNDLE)
        for slug in (WIDEN_LOCATION, DROP_SENIORITY, TRY_LATERALS):
            for suffix in ("", "_action"):
                key = f"backend.widening.{slug}{suffix}"
                with self.subTest(key=key):
                    self.assertIn(
                        key,
                        en,
                        f"missing en.json entry for {key}",
                    )


if __name__ == "__main__":
    unittest.main()
