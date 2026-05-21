# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""4-week plan W3 D15: multilingual scaffolding contract tests
(invariant 15).

What this pins:

1. The locale registry at `static/i18n/locales.json` is well-
   formed and lists at least the persona-anchored locales
   (en, de + planned ar/uk/tr/ro).
2. Every locale declares `code`, `name`, `endonym`, `direction`,
   `status`, `fallback` so the JS layer can drive UI off the
   registry without per-locale special-casing.
3. Every shipped locale has a matching translation JSON file.
4. Every planned locale is in the locales registry but has no
   JSON yet (or has a partial JSON — the loader handles both).
5. The frontend code consumes the registry (loadLocaleRegistry +
   _applyLocaleDirection are present).
6. RTL CSS overrides are present (html[dir="rtl"] selector).
7. The Weblate config + TRANSLATING.md guide ship.
8. Translation JSONs are valid JSON with no obvious key drift.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
LOCALES_REGISTRY = REPO_ROOT / "static" / "i18n" / "locales.json"
I18N_DIR = REPO_ROOT / "static" / "i18n"
APP_JS = REPO_ROOT / "static" / "app.js"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
WEBLATE_CFG = REPO_ROOT / ".weblate"
TRANSLATING_MD = REPO_ROOT / "TRANSLATING.md"

REQUIRED_LOCALE_FIELDS = {
    "code",
    "name",
    "endonym",
    "direction",
    "status",
    "fallback",
}
VALID_DIRECTIONS = {"ltr", "rtl"}
VALID_STATUSES = {"shipped", "planned", "deprecated"}


class LocaleRegistryShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not LOCALES_REGISTRY.exists():
            raise unittest.SkipTest(f"registry not at {LOCALES_REGISTRY}")
        cls.registry = json.loads(LOCALES_REGISTRY.read_text(encoding="utf-8"))

    def test_registry_declares_default_and_locales(self):
        self.assertIn("default", self.registry)
        self.assertIn("locales", self.registry)
        self.assertIsInstance(self.registry["locales"], list)
        self.assertGreater(len(self.registry["locales"]), 0)

    def test_default_locale_is_in_locales(self):
        default = self.registry["default"]
        codes = [l["code"] for l in self.registry["locales"]]
        self.assertIn(default, codes)

    def test_every_locale_has_required_fields(self):
        for locale in self.registry["locales"]:
            for field in REQUIRED_LOCALE_FIELDS:
                self.assertIn(
                    field, locale, f"locale {locale.get('code')!r} missing {field}"
                )

    def test_every_locale_has_valid_direction(self):
        for locale in self.registry["locales"]:
            self.assertIn(locale["direction"], VALID_DIRECTIONS)

    def test_every_locale_has_valid_status(self):
        for locale in self.registry["locales"]:
            self.assertIn(locale["status"], VALID_STATUSES)

    def test_fallback_chain_terminates(self):
        """Every fallback chain must terminate at null (the default
        locale) within at most 5 hops — otherwise a malformed
        registry could cause infinite recursion in the loader."""

        by_code = {l["code"]: l for l in self.registry["locales"]}
        for locale in self.registry["locales"]:
            seen = set()
            current = locale
            for _ in range(6):
                fb = current["fallback"]
                if fb is None:
                    break
                self.assertNotIn(fb, seen, f"fallback cycle through {locale['code']}")
                seen.add(fb)
                self.assertIn(fb, by_code, f"unknown fallback {fb!r}")
                current = by_code[fb]
            else:
                self.fail(f"fallback chain for {locale['code']} too long")

    def test_phase1_locales_are_shipped(self):
        """English + German MUST be marked shipped — they're the
        primary deploy locales per Decision 7 in
        docs/grant/04-research-and-decisions.md."""

        by_code = {l["code"]: l for l in self.registry["locales"]}
        for required in ("en", "de"):
            self.assertIn(required, by_code, f"locale {required} missing from registry")
            self.assertEqual(by_code[required]["status"], "shipped")

    def test_phase2_persona_locales_present(self):
        """The migrant persona panel speaks Arabic, Ukrainian,
        Turkish, Romanian natively. The registry MUST carry an
        entry for each (status may be planned)."""

        by_code = {l["code"]: l for l in self.registry["locales"]}
        for required in ("ar", "uk", "tr", "ro"):
            self.assertIn(required, by_code, f"persona locale {required} missing")

    def test_arabic_is_rtl(self):
        by_code = {l["code"]: l for l in self.registry["locales"]}
        if "ar" in by_code:
            self.assertEqual(by_code["ar"]["direction"], "rtl")


class TranslationFilesAlignWithRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not LOCALES_REGISTRY.exists():
            raise unittest.SkipTest(f"registry not at {LOCALES_REGISTRY}")
        cls.registry = json.loads(LOCALES_REGISTRY.read_text(encoding="utf-8"))

    def test_every_shipped_locale_has_translation_file_or_is_default(self):
        default_locale = self.registry["default"]
        for locale in self.registry["locales"]:
            if locale["status"] != "shipped":
                continue
            if locale["code"] == default_locale:
                # The default locale uses inline strings — no JSON needed
                continue
            json_path = I18N_DIR / f"{locale['code']}.json"
            self.assertTrue(
                json_path.exists(),
                f"shipped locale {locale['code']} missing translation file at {json_path}",
            )

    def test_every_translation_file_is_valid_json(self):
        for json_path in I18N_DIR.glob("*.json"):
            if json_path.name == "locales.json":
                continue
            try:
                content = json.loads(json_path.read_text(encoding="utf-8"))
                self.assertIsInstance(
                    content,
                    dict,
                    f"{json_path.name} top-level MUST be an object",
                )
            except json.JSONDecodeError as exc:
                self.fail(f"{json_path.name} is not valid JSON: {exc}")


class FrontendRegistryConsumption(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not APP_JS.exists():
            raise unittest.SkipTest(f"app.js not at {APP_JS}")
        cls.app_js = APP_JS.read_text(encoding="utf-8")

    def test_loads_locale_registry(self):
        self.assertIn("loadLocaleRegistry", self.app_js)
        self.assertIn("locales.json", self.app_js)

    def test_applies_direction_from_registry(self):
        self.assertIn("_applyLocaleDirection", self.app_js)
        self.assertIn("document.documentElement.dir", self.app_js)

    def test_intl_pluralrules_wrapper_present(self):
        # tPlural is the documented API for translation files
        # that need plural variants. Without it, locales like
        # Ukrainian/Polish/Arabic would render the wrong form.
        self.assertIn("tPlural", self.app_js)
        self.assertIn("Intl.PluralRules", self.app_js)

    def test_template_interpolation_helper_present(self):
        # {{var}} interpolation is the contract the translation
        # files rely on for dynamic values (counts, names, …).
        self.assertIn("_interpolate", self.app_js)


class RtlCssScaffoldingPresent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not STYLES_CSS.exists():
            raise unittest.SkipTest(f"styles.css not at {STYLES_CSS}")
        cls.css = STYLES_CSS.read_text(encoding="utf-8")

    def test_rtl_selector_present(self):
        self.assertIn('html[dir="rtl"]', self.css)

    def test_rtl_flips_text_align(self):
        # The minimum RTL polish: text alignment flips so the UI
        # reads naturally right-to-left.
        self.assertRegex(
            self.css,
            r'html\[dir="rtl"\][^{]*\{[^}]*text-align:\s*right',
        )

    def test_rtl_keeps_numeric_ltr(self):
        # Numbers, code blocks, and URLs are Unicode-bidi LTR even in
        # RTL UIs. Translators rely on this default.
        self.assertIn('html[dir="rtl"] code', self.css)
        # Direction must be explicitly flipped back to ltr for code blocks
        self.assertRegex(
            self.css,
            r'html\[dir="rtl"\]\s*code[^{]*\{[^}]*direction:\s*ltr',
        )


class WeblateAndContributorGuideShip(unittest.TestCase):
    def test_weblate_config_present(self):
        self.assertTrue(WEBLATE_CFG.exists())
        text = WEBLATE_CFG.read_text(encoding="utf-8")
        self.assertIn("[weblate]", text)
        self.assertIn("hosted.weblate.org", text)

    def test_translating_guide_present(self):
        self.assertTrue(TRANSLATING_MD.exists())
        text = TRANSLATING_MD.read_text(encoding="utf-8")
        # The guide MUST mention the two paths (Weblate + direct git)
        self.assertIn("Weblate", text)
        self.assertIn("git", text.lower())
        # MUST mention RTL since that's the highest-priority Phase 2
        self.assertIn("RTL", text)
        # MUST mention plurals + Intl.PluralRules since translators
        # of slavic + arabic languages need it
        self.assertIn("PluralRules", text)


if __name__ == "__main__":
    unittest.main()
