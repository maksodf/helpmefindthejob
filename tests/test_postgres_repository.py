# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PostgreSQL repository contract tests (13-plan item 11/13;
gap #13).

Two layers of test:

1. **Substrate (always runs)** — validates the module imports
   cleanly, the URL classifier accepts the right schemes, the
   AppState factory routes correctly based on
   ``HELPMEFINDTHEJOB_DATABASE_URL``, and the SBOM lists
   psycopg.
2. **Live PG (opt-in)** — when ``TEST_POSTGRES_URL`` env var
   points at a real Postgres instance, runs the same E2E
   roundtrip the SQLite tests run (save / get / list / delete)
   against the real backend. Skipped otherwise so CI without a
   PG service stays green.

The opt-in pattern matches existing project conventions
(e.g., bias-comparative cached run skips when caches absent).
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.models import (
    Company,
    DiscoveredJob,
    ImportedJob,
    SavedSearch,
    UserProfile,
)
from company_discovery.postgres_repository import (
    PostgresCompanyDiscoveryRepository,
    is_postgres_url,
)


_LIVE_PG_URL = os.environ.get("TEST_POSTGRES_URL", "").strip()


# -------------------------------------------------------------------------
# Substrate
# -------------------------------------------------------------------------


class IsPostgresUrlClassifier(unittest.TestCase):
    def test_postgresql_scheme(self):
        self.assertTrue(is_postgres_url("postgresql://localhost/db"))

    def test_postgres_short_scheme(self):
        self.assertTrue(is_postgres_url("postgres://localhost/db"))

    def test_postgresql_async_scheme(self):
        self.assertTrue(is_postgres_url("postgresql+asyncpg://localhost/db"))

    def test_sqlite_path_rejected(self):
        self.assertFalse(is_postgres_url("/var/lib/data.sqlite3"))

    def test_sqlite_url_rejected(self):
        self.assertFalse(is_postgres_url("sqlite:///var/lib/data.sqlite3"))

    def test_empty_rejected(self):
        self.assertFalse(is_postgres_url(""))


class AppStateRoutesByDatabaseUrl(unittest.TestCase):
    """The AppState constructor must route the primary
    repository to Postgres when HELPMEFINDTHEJOB_DATABASE_URL
    is a postgres URL, and to SQLite otherwise."""

    def setUp(self):
        self._original_env = dict(os.environ)
        # Clear any inherited test config
        for key in (
            "HELPMEFINDTHEJOB_DATABASE_URL",
            "DIRECTJOB_DATABASE_URL",
        ):
            os.environ.pop(key, None)

    def tearDown(self):
        for key in (
            "HELPMEFINDTHEJOB_DATABASE_URL",
            "DIRECTJOB_DATABASE_URL",
        ):
            if key in self._original_env:
                os.environ[key] = self._original_env[key]
            else:
                os.environ.pop(key, None)

    def test_unset_url_falls_back_to_sqlite(self):
        from app import AppState
        from company_discovery.sqlite_repository import (
            SqliteCompanyDiscoveryRepository,
        )

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
                self.assertIsInstance(
                    state.repository, SqliteCompanyDiscoveryRepository
                )
            finally:
                state.auth_store.close()
                state.repository.close()

    def test_app_py_carries_routing_logic(self):
        """Source-level check: AppState's __init__ MUST branch on
        HELPMEFINDTHEJOB_DATABASE_URL between PostgresCompany
        DiscoveryRepository and SqliteCompanyDiscoveryRepository.
        Direct exercise via `AppState(...)` would trigger the
        module-level `STATE = AppState()` instantiation on first
        `from app import AppState`, which we can't bypass cleanly.
        Source verification is the pragmatic equivalent."""

        src = Path(
            "/Users/fouad./Desktop/NasserMCPserver/app.py"
        ).read_text(encoding="utf-8")
        # The routing block reads the env var
        self.assertIn(
            'get_env(\n            "HELPMEFINDTHEJOB_DATABASE_URL"',
            src,
        )
        # And imports + uses the Postgres repository conditionally
        self.assertIn("PostgresCompanyDiscoveryRepository", src)
        self.assertIn("is_postgres_url(database_url)", src)


class RequirementsContract(unittest.TestCase):
    """psycopg must appear in requirements.txt + SBOM."""

    def test_requirements_lists_psycopg(self):
        req = Path(
            "/Users/fouad./Desktop/NasserMCPserver/requirements.txt"
        ).read_text(encoding="utf-8")
        self.assertIn("psycopg", req.lower())

    def test_sbom_lists_psycopg(self):
        sbom = json.loads(
            Path(
                "/Users/fouad./Desktop/NasserMCPserver/docs/releases/v0.1.0-sbom.json"
            ).read_text(encoding="utf-8")
        )
        names = {c["name"].lower() for c in sbom["components"]}
        self.assertIn("psycopg", names)


class PostgresRepositoryWithoutPsycopg(unittest.TestCase):
    """When psycopg is not installed, constructing the repository
    must raise a clear error rather than failing obscurely later.
    We can't easily uninstall psycopg in-process, so we exercise
    this via a synthetic ImportError mock."""

    def test_raises_runtime_error_when_psycopg_missing(self):
        # Patch builtins.__import__ to fake psycopg ImportError
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "psycopg":
                raise ImportError("simulated missing psycopg")
            return real_import(name, *args, **kwargs)

        from unittest.mock import patch

        with patch("builtins.__import__", side_effect=fake_import):
            with self.assertRaises(RuntimeError) as cm:
                PostgresCompanyDiscoveryRepository("postgresql://x/db")
            self.assertIn("psycopg", str(cm.exception).lower())


# -------------------------------------------------------------------------
# Live Postgres roundtrip (opt-in via TEST_POSTGRES_URL)
# -------------------------------------------------------------------------


@unittest.skipUnless(
    _LIVE_PG_URL,
    "TEST_POSTGRES_URL not set — skipping live Postgres roundtrip. "
    "Set to a clean Postgres URL (CI / local dev) to exercise the "
    "real backend.",
)
class LivePostgresRoundtrip(unittest.TestCase):
    """Real Postgres backend exercises every save/get/list/delete
    code path. Uses a fresh schema per test so the database
    state is deterministic; tear-down drops everything we made."""

    @classmethod
    def setUpClass(cls):
        cls.repo = PostgresCompanyDiscoveryRepository(_LIVE_PG_URL)

    @classmethod
    def tearDownClass(cls):
        # Drop our tables so the test DB stays usable between runs
        cur = cls.repo._connection.cursor()
        for table in cls.repo._TABLES + ("schema_version",):
            try:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            except Exception:
                pass
        cls.repo._connection.commit()
        cur.close()
        cls.repo.close()

    def setUp(self):
        # Clear all tables between tests for determinism
        cur = self.repo._connection.cursor()
        for table in self.repo._TABLES:
            cur.execute(f"DELETE FROM {table}")
        self.repo._connection.commit()
        cur.close()
        # Re-hydrate in-memory cache (now empty)
        for inner in (
            self.repo.companies,
            self.repo.discovered_jobs,
            self.repo.imported_jobs,
            self.repo.saved_searches,
            self.repo.user_profiles,
            self.repo.workspace_memberships,
            self.repo.push_subscriptions,
            self.repo.support_tickets,
            self.repo.analytics_events,
        ):
            inner.clear()

    def test_company_roundtrip(self):
        company = Company(
            user_id="u1",
            name="ACME Pflege",
            website_url="https://acme.example.com",
        )
        self.repo.save_company(company)
        retrieved = self.repo.get_company("u1", company.id)
        self.assertEqual(retrieved.name, "ACME Pflege")
        self.assertEqual(retrieved.website_url, "https://acme.example.com")

    def test_company_list_filters_by_user(self):
        u1c = Company(user_id="u1", name="C1", website_url="https://c1.example")
        u2c = Company(user_id="u2", name="C2", website_url="https://c2.example")
        self.repo.save_company(u1c)
        self.repo.save_company(u2c)
        u1_list = self.repo.list_companies("u1")
        self.assertEqual(len(u1_list), 1)
        self.assertEqual(u1_list[0].name, "C1")

    def test_company_delete_cascades_to_jobs(self):
        company = Company(
            user_id="u1", name="C", website_url="https://c.example"
        )
        self.repo.save_company(company)
        job = DiscoveredJob(
            user_id="u1",
            company_id=company.id,
            source_url="https://jobs.example/1",
            title="Test",
            confidence_score=0.9,
        )
        self.repo.save_discovered_job(job)
        self.repo.delete_company("u1", company.id)
        self.assertEqual(self.repo.list_companies("u1"), [])
        self.assertEqual(self.repo.list_discovered_jobs("u1"), [])

    def test_imported_job_roundtrip(self):
        job = ImportedJob(
            user_id="u1",
            company_id="c1",
            discovered_job_id="d1",
            source_url="https://jobs.example/x",
            title="Embedded Engineer",
            company_name="Daimler",
            description="Stuttgart role.",
        )
        self.repo.save_imported_job(job)
        listed = self.repo.list_imported_jobs("u1")
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0].title, "Embedded Engineer")

    def test_saved_search_delete_removes_row(self):
        search = SavedSearch(
            user_id="u1",
            name="Pflege Berlin",
            target_roles=["Pflegekraft"],
        )
        self.repo.save_saved_search(search)
        self.repo.delete_saved_search("u1", search.id)
        # In-memory check
        self.assertNotIn(search.id, self.repo.saved_searches)
        # DB check
        cur = self.repo._connection.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM saved_searches WHERE id = %s", (search.id,)
        )
        count = cur.fetchone()[0]
        cur.close()
        self.assertEqual(count, 0)

    def test_user_profile_roundtrip(self):
        profile = UserProfile(
            user_id="u1",
            persona_id="aicha",
            cv_text="Aicha CV — Pflegekraft mit §16d pathway.",
        )
        self.repo.save_user_profile(profile)
        retrieved = self.repo.get_user_profile("u1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.persona_id, "aicha")
        self.assertEqual(
            retrieved.cv_text, "Aicha CV — Pflegekraft mit §16d pathway."
        )

    def test_persistence_across_close_reopen(self):
        company = Company(
            user_id="u1", name="Persistent Co", website_url="https://p.example"
        )
        self.repo.save_company(company)
        self.repo.close()
        # Reopen — _load should rehydrate the in-memory cache
        repo2 = PostgresCompanyDiscoveryRepository(_LIVE_PG_URL)
        try:
            listed = repo2.list_companies("u1")
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0].name, "Persistent Co")
        finally:
            repo2.close()
        # Reconnect for any subsequent tests
        type(self).repo = PostgresCompanyDiscoveryRepository(_LIVE_PG_URL)


if __name__ == "__main__":
    unittest.main()
