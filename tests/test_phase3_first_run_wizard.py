# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""First-run wizard edge cases (Phase 3 tracker item #33).

Wizard state is computed by ``needs_first_run_wizard`` from the live
profile + repository, not stored as a snapshot — so every check
re-derives from current state. The tests cover:

- skip path: dismissing sets ``profile.onboarding_dismissed=True`` and
  the wizard never reappears
- abort: same as skip — the dismissed flag latches once it flips
- resume on next session: an undismissed empty user keeps seeing the
  wizard until they take meaningful action

The wizard hide on activity is implicit: any of saved_searches,
companies, discovered_jobs, imported_jobs being non-empty hides it
without needing the dismissed flag.
"""

from __future__ import annotations

import unittest

from company_discovery.models import (
    Company,
    DiscoveredJob,
    ImportedJob,
    SavedSearch,
    UserProfile,
)
from company_discovery.onboarding import needs_first_run_wizard


def _profile(dismissed: bool = False, *, user_id: str = "u1") -> UserProfile:
    return UserProfile(user_id=user_id, onboarding_dismissed=dismissed)


def _saved_search(user_id: str = "u1") -> SavedSearch:
    return SavedSearch(user_id=user_id, name="My role")


def _company(user_id: str = "u1") -> Company:
    return Company(user_id=user_id, name="Acme", website_url="https://acme.example.com")


def _discovered(user_id: str = "u1") -> DiscoveredJob:
    return DiscoveredJob(
        user_id=user_id,
        source_url="https://example.com/job",
        title="Engineer",
    )


def _imported(user_id: str = "u1") -> ImportedJob:
    return ImportedJob(
        user_id=user_id,
        company_id="c1",
        discovered_job_id="d1",
        source_url="https://example.com/job",
        title="Engineer",
        company_name="Acme",
    )


class FirstRunWizardTests(unittest.TestCase):
    def test_brand_new_user_sees_wizard(self) -> None:
        self.assertTrue(
            needs_first_run_wizard(
                saved_searches=(),
                companies=(),
                profile=_profile(dismissed=False),
                discovered_jobs=(),
                imported_jobs=(),
                dismissed=False,
            )
        )

    def test_dismissed_flag_hides_wizard_even_with_no_data(self) -> None:
        self.assertFalse(
            needs_first_run_wizard(
                saved_searches=(),
                companies=(),
                profile=_profile(dismissed=True),
                discovered_jobs=(),
                imported_jobs=(),
                dismissed=True,
            )
        )

    def test_any_saved_search_hides_wizard(self) -> None:
        self.assertFalse(
            needs_first_run_wizard(
                saved_searches=(_saved_search(),),
                companies=(),
                profile=_profile(dismissed=False),
                discovered_jobs=(),
                imported_jobs=(),
                dismissed=False,
            )
        )

    def test_any_company_hides_wizard(self) -> None:
        self.assertFalse(
            needs_first_run_wizard(
                saved_searches=(),
                companies=(_company(),),
                profile=_profile(dismissed=False),
                discovered_jobs=(),
                imported_jobs=(),
                dismissed=False,
            )
        )

    def test_any_discovered_or_imported_hides_wizard(self) -> None:
        self.assertFalse(
            needs_first_run_wizard(
                saved_searches=(),
                companies=(),
                profile=_profile(dismissed=False),
                discovered_jobs=(_discovered(),),
                imported_jobs=(),
                dismissed=False,
            )
        )
        self.assertFalse(
            needs_first_run_wizard(
                saved_searches=(),
                companies=(),
                profile=_profile(dismissed=False),
                discovered_jobs=(),
                imported_jobs=(_imported(),),
                dismissed=False,
            )
        )

    def test_resume_undismissed_empty_user_still_sees_wizard(self) -> None:
        # The "resume on next session" path: a user who closed the
        # browser without dismissing comes back empty-handed and the
        # wizard is still there for them.
        first_call = needs_first_run_wizard(
            saved_searches=(),
            companies=(),
            profile=_profile(dismissed=False),
            discovered_jobs=(),
            imported_jobs=(),
            dismissed=False,
        )
        self.assertTrue(first_call)
        # Next "session" — same inputs reproduce the same answer
        # because the function is pure.
        second_call = needs_first_run_wizard(
            saved_searches=(),
            companies=(),
            profile=_profile(dismissed=False),
            discovered_jobs=(),
            imported_jobs=(),
            dismissed=False,
        )
        self.assertEqual(first_call, second_call)


if __name__ == "__main__":
    unittest.main()
