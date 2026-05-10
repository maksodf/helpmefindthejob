"""Round-5 tests: A2 i18n bundles + locale persistence."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.models import SUPPORTED_LOCALES


class I18nBundleTests(unittest.TestCase):
    EN_PATH = REPO_ROOT / "static" / "i18n" / "en.json"
    DE_PATH = REPO_ROOT / "static" / "i18n" / "de.json"

    def test_both_bundles_exist(self) -> None:
        self.assertTrue(self.EN_PATH.exists(), "en.json missing")
        self.assertTrue(self.DE_PATH.exists(), "de.json missing")

    def test_bundles_share_same_keys(self) -> None:
        en = json.loads(self.EN_PATH.read_text())
        de = json.loads(self.DE_PATH.read_text())
        self.assertEqual(set(en), set(de), "translation key drift")

    def test_german_strings_actually_german(self) -> None:
        de = json.loads(self.DE_PATH.read_text())
        # A handful of keys we know should look German.
        self.assertIn("Übersicht", de["nav.dashboard"])
        self.assertIn("Einstellungen", de["nav.settings"])
        self.assertEqual(de["common.delete"], "Löschen")
        self.assertEqual(de["common.save"], "Speichern")

    def test_supported_locales_constant(self) -> None:
        self.assertIn("en", SUPPORTED_LOCALES)
        self.assertIn("de", SUPPORTED_LOCALES)


class LocalePersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="round5-locale-"))
        os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(cls.tmpdir)
        for name in list(sys.modules):
            if name == "app":
                del sys.modules[name]
        import app  # noqa: E402

        cls.state = app.STATE

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_locale_round_trip(self) -> None:
        profile = self.state.update_profile("locale-user", {"locale": "de"})
        self.assertEqual(profile.locale, "de")
        again = self.state.profile_for("locale-user")
        self.assertEqual(again.locale, "de")

    def test_unsupported_locale_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.state.update_profile("locale-user-2", {"locale": "klingon"})

    def test_locale_default_en(self) -> None:
        profile = self.state.profile_for("locale-user-3")
        self.assertEqual(profile.locale, "en")


if __name__ == "__main__":
    unittest.main()
