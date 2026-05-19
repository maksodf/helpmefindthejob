# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Tests for ``scripts/seed-personas.py``.

Coverage:

- All seven personas (per Decision 21) are seeded.
- Each seeded account's profile fields match
  ``company_discovery/persona_fixtures.PERSONAS``.
- Each persona's saved searches are created exactly once.
- Re-running the seed is a no-op (idempotency).
- Partial-state recovery: if only N of 7 personas exist, the next
  run completes the remaining ones without duplicating the first N.
- The seed script does not hardcode any test password (string search).
- No network access required: tests run against a tmpdir-scoped
  ``AppState``.

The tests import the seed module by file path (the script's filename
contains a hyphen, which Python's normal import machinery cannot
resolve). This mirrors how ``scripts/print_mcp_catalogue.py`` is
exercised in the MCP integration test.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "seed-personas.py"


def _load_seed_module():
    """Import ``scripts/seed-personas.py`` via importlib.util.

    The script file is named with a hyphen which is not a valid
    Python module-name token; standard ``import`` cannot reach it.
    ``importlib.util.spec_from_file_location`` is the canonical
    workaround.
    """
    module_name = "seed_personas_script"
    spec = importlib.util.spec_from_file_location(module_name, str(_SCRIPT_PATH))
    assert spec is not None and spec.loader is not None, "seed-personas.py missing"
    module = importlib.util.module_from_spec(spec)
    # Register the module in sys.modules BEFORE exec_module so dataclass
    # field-type resolution on Python 3.9 can find the module namespace.
    # Without this, ``@dataclass`` fails during the script's module-init.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _build_state_in_tmpdir(tmpdir: Path):
    """Build a fresh ``AppState`` rooted in ``tmpdir`` with the
    scheduler disabled.

    Each test gets its own tmpdir; app.py's module-level path
    constants only read the env var once at import time, so we must
    pass ALL paths explicitly to AppState to keep test isolation.
    """
    os.environ["HELPMEFINDTHEJOB_DATA_DIR"] = str(tmpdir)
    from app import AppState

    return AppState(
        data_path=tmpdir / "company_discovery.sqlite3",
        auth_path=tmpdir / "auth.sqlite3",
        ai_config_path=tmpdir / "ai_provider.json",
        schedule_path=tmpdir / "watchlist_schedule.json",
        admin_audit_path=tmpdir / "admin_audit.log",
        token_path=tmpdir / "tokens.sqlite3",
        quota_path=tmpdir / "quotas.sqlite3",
        scheduler_path=tmpdir / "scheduler.sqlite3",
        start_scheduler=False,
    )


class SeedPersonasTests(unittest.TestCase):
    """Fresh tmpdir per test; AppState constructed in setUp."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="seed_personas_"))
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        # Reset env so AppState picks up our tmpdir.
        self._prev_data_dir = os.environ.get("HELPMEFINDTHEJOB_DATA_DIR")
        os.environ["HELPMEFINDTHEJOB_DATA_DIR"] = str(self.tmpdir)
        self.addCleanup(self._restore_env)
        self.seed_module = _load_seed_module()
        self.state = _build_state_in_tmpdir(self.tmpdir)

    def _restore_env(self) -> None:
        if self._prev_data_dir is None:
            os.environ.pop("HELPMEFINDTHEJOB_DATA_DIR", None)
        else:
            os.environ["HELPMEFINDTHEJOB_DATA_DIR"] = self._prev_data_dir

    # ── core: seven personas seeded with profile + saved searches ──────────

    def test_seeds_all_seven_personas_on_first_run(self) -> None:
        from company_discovery.persona_fixtures import PERSONAS

        summary = self.seed_module.seed(
            self.state,
            password="test-password-fixture",
            email_domain="test.example",
        )
        self.assertEqual(len(summary.created), 7)
        self.assertEqual(set(summary.created), {p.slug for p in PERSONAS})
        # Profiles upserted for every persona too.
        self.assertEqual(set(summary.profile_updated), {p.slug for p in PERSONAS})

    def test_persona_profile_fields_match_fixture(self) -> None:
        from company_discovery.persona_fixtures import PERSONAS

        self.seed_module.seed(
            self.state,
            password="test-password-fixture",
            email_domain="test.example",
        )

        for persona in PERSONAS:
            email = f"{persona.slug}@test.example"
            user_id = None
            for user in self.state.auth_store.list_users():
                if user.email.lower() == email.lower():
                    user_id = user.id
                    break
            self.assertIsNotNone(user_id, f"user {persona.slug} missing")
            profile = self.state.repository.get_user_profile(user_id)
            self.assertIsNotNone(profile, f"profile {persona.slug} missing")
            self.assertEqual(profile.persona_id, persona.slug)
            self.assertEqual(profile.industry, persona.industry)
            self.assertEqual(profile.location, persona.location)
            self.assertEqual(profile.years_experience, persona.years_experience)
            self.assertEqual(sorted(profile.target_roles), sorted(persona.target_roles))

    # ── idempotency: re-run = no-op ───────────────────────────────────────

    def test_rerun_is_noop(self) -> None:
        from company_discovery.persona_fixtures import PERSONAS

        self.seed_module.seed(
            self.state,
            password="test-password-fixture",
            email_domain="test.example",
        )
        users_after_first = sorted(u.email for u in self.state.auth_store.list_users())
        searches_after_first = self._all_search_count()

        summary_second = self.seed_module.seed(
            self.state,
            password="test-password-fixture",
            email_domain="test.example",
        )
        users_after_second = sorted(u.email for u in self.state.auth_store.list_users())
        searches_after_second = self._all_search_count()

        self.assertEqual(users_after_first, users_after_second)
        self.assertEqual(searches_after_first, searches_after_second)
        # On re-run, all seven personas are "already present"; no new
        # accounts are created.
        self.assertEqual(summary_second.created, [])
        self.assertEqual(set(summary_second.already_present), {p.slug for p in PERSONAS})

    # ── partial-state recovery ────────────────────────────────────────────

    def test_partial_state_recovery(self) -> None:
        """Simulate a crash mid-seed: create 3 of 7 by hand, then run
        the seed; expect the remaining 4 to land without duplicating
        the first 3 or skipping any."""
        from company_discovery.persona_fixtures import PERSONAS

        # Pre-create the first three personas (mocking a partial seed).
        for persona in PERSONAS[:3]:
            self.state.auth_store.create_user(
                email=f"{persona.slug}@test.example",
                password="pre-existing",
                role="member",
            )

        summary = self.seed_module.seed(
            self.state,
            password="test-password-fixture",
            email_domain="test.example",
        )

        # All seven personas now exist.
        emails = {u.email.lower() for u in self.state.auth_store.list_users()}
        for persona in PERSONAS:
            self.assertIn(f"{persona.slug}@test.example", emails, f"missing {persona.slug}")
        # The first three were detected as already-present.
        self.assertEqual(set(summary.already_present), {p.slug for p in PERSONAS[:3]})
        # The remaining four were created.
        self.assertEqual(set(summary.created), {p.slug for p in PERSONAS[3:]})

    # ── saved searches: no duplicate on re-run ─────────────────────────────

    def test_saved_searches_not_duplicated_on_rerun(self) -> None:
        from company_discovery.persona_fixtures import PERSONAS

        self.seed_module.seed(
            self.state,
            password="test-password-fixture",
            email_domain="test.example",
        )
        first_count = self._all_search_count()
        # Expected: at least one saved search per persona that has one.
        expected_first = sum(len(p.saved_searches) for p in PERSONAS)
        self.assertEqual(first_count, expected_first)

        self.seed_module.seed(
            self.state,
            password="test-password-fixture",
            email_domain="test.example",
        )
        second_count = self._all_search_count()
        self.assertEqual(second_count, first_count)

    # ── dry-run: writes nothing ───────────────────────────────────────────

    def test_dry_run_writes_nothing(self) -> None:
        summary = self.seed_module.seed(
            self.state,
            password="test-password-fixture",
            email_domain="test.example",
            dry_run=True,
        )
        # The summary reports 7 "would-create"; no actual user rows.
        self.assertEqual(len(summary.created), 7)
        self.assertTrue(summary.dry_run)
        users = [u for u in self.state.auth_store.list_users() if u.email.endswith("@test.example")]
        self.assertEqual(users, [])

    # ── no hardcoded test password ───────────────────────────────────────

    def test_no_hardcoded_test_password_in_script(self) -> None:
        """Search the seed script for the password we use in tests.

        If the script ever pins a default password, this test fails and
        the maintainer is alerted before the demo deployment goes out
        with a guessable password.
        """
        source = _SCRIPT_PATH.read_text(encoding="utf-8")
        forbidden = {
            "test-password-fixture",
            "demoaccess",
            "demopassword",
            "password123",
        }
        for token in forbidden:
            self.assertNotIn(
                token,
                source,
                f"seed-personas.py must not hardcode {token!r}; password is "
                "supplied at runtime via --password",
            )

    def test_default_email_domain_is_canonical(self) -> None:
        """Default email domain is the canonical helpmefindthejob.com
        demo subdomain per Decision 22 (project rename + real-domain
        acquisition supersedes the Decision-12 .example placeholder
        convention; see Open R8 reopen in
        docs/grant/04-research-and-decisions.md). Deployers may still
        override at run time via --email-domain for their own
        subdomain."""
        source = _SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertRegex(
            source,
            r'default="demo\.helpmefindthejob\.com"',
            "seed-personas.py default --email-domain must be the canonical "
            "demo.helpmefindthejob.com subdomain (Decision 22); the prior "
            "Decision-12 .example placeholder convention is superseded.",
        )

    # ── persona fixture consistency ───────────────────────────────────────

    def test_fixture_module_has_seven_personas_with_correct_cohorts(self) -> None:
        """Decision 21 contract: exactly seven personas (five most-acute
        migrant + two wider-friction-class). The fixture module asserts
        this at import time; this test mirrors that assertion at the
        public-API surface."""
        from company_discovery.persona_fixtures import PERSONAS

        self.assertEqual(len(PERSONAS), 7)
        most_acute = [p for p in PERSONAS if p.cohort == "most-acute"]
        wider = [p for p in PERSONAS if p.cohort == "wider-friction"]
        self.assertEqual(len(most_acute), 5)
        self.assertEqual(len(wider), 2)
        slugs = {p.slug for p in PERSONAS}
        self.assertEqual(
            slugs,
            {"aicha", "yusuf", "olga", "mahmoud", "maria", "kaethe", "tobias"},
        )

    # ── helpers ───────────────────────────────────────────────────────────

    def _all_search_count(self) -> int:
        total = 0
        for user in self.state.auth_store.list_users():
            total += len(self.state.repository.list_saved_searches(user.id))
        return total


class CLISmokeTests(unittest.TestCase):
    """argparse / entry-point smoke test — does not actually run the
    seed (that's covered above); just exercises the CLI parser and
    confirms ``--password`` is required."""

    def setUp(self) -> None:
        self.seed_module = _load_seed_module()

    def test_password_is_required(self) -> None:
        # argparse prints "the following arguments are required: --password"
        # to stderr before raising SystemExit. Capture the stderr so the
        # test's expected failure-mode doesn't pollute the suite's
        # console output (PART A.2 of the deep audit).
        import io
        from contextlib import redirect_stderr

        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit):
            self.seed_module._parse_args([])
        self.assertIn("--password", stderr.getvalue())

    def test_dry_run_flag_recognised(self) -> None:
        args = self.seed_module._parse_args(["--password", "x", "--dry-run"])
        self.assertTrue(args.dry_run)

    def test_force_password_reset_flag_recognised(self) -> None:
        args = self.seed_module._parse_args(["--password", "x", "--force-password-reset"])
        self.assertTrue(args.force_password_reset)


if __name__ == "__main__":
    unittest.main()
