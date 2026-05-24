# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 backlog #56 — persona localisation contract tests.

Two concerns:

1. Persona content depth must stay normalised across the 7-persona
   panel so the bias methodology compares like-for-like across
   the most-acute and wider-friction cohorts.
2. The locale validator (used by /api/profile updates) must
   discover translation bundles dynamically from static/i18n/
   rather than hardcoding the supported set — dropping in a new
   ``.json`` bundle should activate that locale without a code
   change.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.models import (
    SUPPORTED_LOCALES,
    _discover_locales,
    available_locales,
)
from company_discovery.persona_fixtures import PERSONAS


class PersonaContentDepthNormalisation(unittest.TestCase):
    """Drift guard: every persona must have the same scoring scenario
    count, tailoring scenario count, and cross-industry probe count.
    Without this the methodology comparison is unfair (some personas
    contribute more evidence than others)."""

    def test_panel_size_seven(self) -> None:
        self.assertEqual(len(PERSONAS), 7)

    def test_cohort_split_five_plus_two(self) -> None:
        most_acute = [p for p in PERSONAS if p.cohort == "most-acute"]
        wider_friction = [p for p in PERSONAS if p.cohort == "wider-friction"]
        self.assertEqual(len(most_acute), 5)
        self.assertEqual(len(wider_friction), 2)

    def test_every_persona_has_10_scoring_scenarios(self) -> None:
        for p in PERSONAS:
            self.assertEqual(len(p.scenarios), 10, f"{p.slug}: scoring scenarios")

    def test_every_persona_has_10_cv_tailoring_scenarios(self) -> None:
        for p in PERSONAS:
            self.assertEqual(
                len(p.cv_tailoring_scenarios),
                10,
                f"{p.slug}: cv_tailoring_scenarios",
            )

    def test_every_persona_has_exactly_one_cross_industry_probe(self) -> None:
        for p in PERSONAS:
            self.assertEqual(
                len(p.cross_industry_probes),
                1,
                f"{p.slug}: cross_industry_probes",
            )

    def test_every_persona_has_at_least_three_friction_keywords(self) -> None:
        # 3 is the floor — Yusuf has 3, others have 4-5. Below 3
        # the CV-tailoring semantic check has too little signal.
        for p in PERSONAS:
            self.assertGreaterEqual(
                len(p.friction_keywords),
                3,
                f"{p.slug}: friction_keywords (got {p.friction_keywords})",
            )

    def test_cv_summary_within_normalised_band(self) -> None:
        # 200-400 chars — narrower than that signals depth drift.
        # Outside that range means one persona has notably more or
        # less narrative depth than the others.
        for p in PERSONAS:
            self.assertGreaterEqual(len(p.cv_summary), 200, f"{p.slug}: cv_summary too short")
            self.assertLessEqual(len(p.cv_summary), 400, f"{p.slug}: cv_summary too long")

    def test_locale_field_is_one_of_supported(self) -> None:
        # Personas may use any locale the runtime supports
        for p in PERSONAS:
            self.assertIn(p.locale, available_locales())


class DynamicLocaleDiscovery(unittest.TestCase):
    def test_fallback_to_supported_locales_when_dir_missing(self) -> None:
        # Point at a directory that doesn't exist — should fall back
        with TemporaryDirectory() as tmp:
            bogus = Path(tmp) / "does-not-exist"
            self.assertEqual(_discover_locales(bogus), SUPPORTED_LOCALES)

    def test_discovers_json_bundles_in_directory(self) -> None:
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "en.json").write_text("{}", encoding="utf-8")
            (d / "de.json").write_text("{}", encoding="utf-8")
            (d / "ar.json").write_text("{}", encoding="utf-8")
            self.assertEqual(_discover_locales(d), ("ar", "de", "en"))

    def test_ignores_non_json_files(self) -> None:
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "en.json").write_text("{}", encoding="utf-8")
            (d / "readme.md").write_text("notes", encoding="utf-8")
            self.assertEqual(_discover_locales(d), ("en",))

    def test_rejects_garbage_filenames(self) -> None:
        """A filename like ``../etc/passwd.json`` must not be
        accepted as a locale code."""
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "en.json").write_text("{}", encoding="utf-8")
            # These should NOT be picked up as locales:
            (d / "..etc.json").write_text("{}", encoding="utf-8")
            (d / "with space.json").write_text("{}", encoding="utf-8")
            (d / "with/slash.json").parent.mkdir(parents=True, exist_ok=True)
            # The slash one can't actually exist as a single file —
            # filesystems disallow / in names. Skip.
            codes = _discover_locales(d)
            self.assertIn("en", codes)
            self.assertNotIn("..etc", codes)
            self.assertNotIn("with space", codes)

    def test_available_locales_caches_results(self) -> None:
        """Quality-audit (2026-05-21): the original implementation
        rescanned the directory on every call. available_locales
        now caches results per resolved-directory-path so the
        validator hot path doesn't pay an iterdir cost on every
        request."""
        from company_discovery.models import available_locales

        # Two calls with the default dir should return identical
        # tuples (cached). We can't easily test "did NOT scan"
        # without a side-channel, but we CAN test that the return
        # value is stable across calls (which is the user-facing
        # guarantee).
        first = available_locales()
        second = available_locales()
        self.assertEqual(first, second)
        # And the tuple identity equality is the cache marker —
        # uncached calls would each build a fresh tuple
        self.assertIs(first, second)

    def test_repo_default_includes_at_least_en_and_de(self) -> None:
        # The repo ships en.json + de.json today; available_locales()
        # should return at least these two when called without args.
        codes = available_locales()
        self.assertIn("en", codes)
        self.assertIn("de", codes)


class LocaleProfileValidator(unittest.TestCase):
    """The /api/profile locale-update path uses available_locales()
    (not the hardcoded SUPPORTED_LOCALES) so dropping in ``ar.json``
    activates Arabic without a code change."""

    def test_update_profile_uses_dynamic_locale_set(self) -> None:
        from app import AppState

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = AppState(
                root / "company.sqlite3",
                root / "auth.sqlite3",
                root / "ai.json",
                root / "schedule.json",
                start_scheduler=False,
            )
            try:
                user = state.auth_store.create_user("loc@example.com", "secret-pass-12345")
                # Known-supported locales pass
                profile = state.update_profile(user.id, {"locale": "en"})
                self.assertEqual(profile.locale, "en")
                profile = state.update_profile(user.id, {"locale": "de"})
                self.assertEqual(profile.locale, "de")
                # Unknown locale rejected with the expected ValueError
                with self.assertRaises(ValueError) as cm:
                    state.update_profile(user.id, {"locale": "xx"})
                self.assertIn("unsupported_locale", str(cm.exception))
            finally:
                state.auth_store.close()
                state.repository.close()


if __name__ == "__main__":
    unittest.main()
