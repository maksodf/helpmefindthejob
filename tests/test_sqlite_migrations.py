# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Versioned SQLite migration contract tests (gap #20).

These tests pin the migration runner's contract so the schema
evolution path stays predictable:

1. Discovery: scan a directory, parse NNN_<name>.sql filenames,
   skip junk files with a warning.
2. Version-gap guard: contiguous version numbers required —
   a missing 002 between 001 and 003 is a contributor error
   (lost a file in a rebase) and fails loudly.
3. Forward-only: an already-applied migration is not re-applied.
4. Per-migration transactional safety: a failing migration leaves
   user_version at the pre-migration value, not half-applied.
5. Idempotency: running the runner twice in a row applies nothing
   the second time.
6. Baseline migration is a no-op on a DB that already went through
   the production SqliteCompanyDiscoveryRepository._create_schema.
7. Repository boot wires the runner — a fresh DB ends up at the
   latest available version.
"""

from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.migrations import (
    Migration,
    MigrationResult,
    current_version,
    discover_migrations,
    latest_available_version,
    run_migrations,
    set_version,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_MIGRATIONS = REPO_ROOT / "migrations"


class DiscoverMigrations(unittest.TestCase):
    def test_returns_empty_for_missing_dir(self):
        with TemporaryDirectory() as tmp:
            non_existent = Path(tmp) / "no_such"
            self.assertEqual(discover_migrations(non_existent), [])

    def test_returns_empty_for_empty_dir(self):
        with TemporaryDirectory() as tmp:
            self.assertEqual(discover_migrations(Path(tmp)), [])

    def test_skips_non_sql_files(self):
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "001_baseline.sql").write_text("-- baseline\n", encoding="utf-8")
            (d / "README.md").write_text("# notes\n", encoding="utf-8")
            (d / "002_foo.txt").write_text("not SQL\n", encoding="utf-8")
            migrations = discover_migrations(d)
            self.assertEqual(len(migrations), 1)
            self.assertEqual(migrations[0].version, 1)
            self.assertEqual(migrations[0].name, "baseline")

    def test_skips_misnamed_sql_files(self):
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "001_ok.sql").write_text("-- ok\n", encoding="utf-8")
            (d / "baseline.sql").write_text("-- missing number\n", encoding="utf-8")
            (d / "abc_bad.sql").write_text("-- non-numeric\n", encoding="utf-8")
            migrations = discover_migrations(d)
            self.assertEqual(len(migrations), 1)

    def test_sorts_by_version_number(self):
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "002_second.sql").write_text("-- 2\n", encoding="utf-8")
            (d / "001_first.sql").write_text("-- 1\n", encoding="utf-8")
            (d / "003_third.sql").write_text("-- 3\n", encoding="utf-8")
            migrations = discover_migrations(d)
            self.assertEqual([m.version for m in migrations], [1, 2, 3])

    def test_version_gap_raises(self):
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "001_first.sql").write_text("-- 1\n", encoding="utf-8")
            (d / "003_third.sql").write_text("-- 3\n", encoding="utf-8")  # gap at 2
            with self.assertRaises(ValueError) as cm:
                discover_migrations(d)
            self.assertIn("gap", str(cm.exception).lower())


class CurrentVersionAndSetVersion(unittest.TestCase):
    def test_fresh_connection_is_version_zero(self):
        conn = sqlite3.connect(":memory:")
        self.assertEqual(current_version(conn), 0)

    def test_set_version_roundtrips(self):
        conn = sqlite3.connect(":memory:")
        set_version(conn, 7)
        self.assertEqual(current_version(conn), 7)

    def test_negative_version_rejected(self):
        conn = sqlite3.connect(":memory:")
        with self.assertRaises(ValueError):
            set_version(conn, -1)

    def test_non_int_version_rejected(self):
        conn = sqlite3.connect(":memory:")
        with self.assertRaises(ValueError):
            set_version(conn, "1")  # type: ignore[arg-type]


class RunMigrationsContract(unittest.TestCase):
    def _make_migrations(self, dir_path: Path, n: int = 2) -> None:
        for i in range(1, n + 1):
            (dir_path / f"{i:03d}_step.sql").write_text(f"CREATE TABLE IF NOT EXISTS step_{i} (id INTEGER PRIMARY KEY);\n", encoding="utf-8")

    def test_apply_to_fresh_db_runs_all_migrations(self):
        conn = sqlite3.connect(":memory:")
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._make_migrations(d, n=3)
            result = run_migrations(conn, d)
            self.assertEqual(result.starting_version, 0)
            self.assertEqual(result.final_version, 3)
            self.assertEqual(result.applied, [1, 2, 3])
        # All step tables exist
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [r[0] for r in cur.fetchall()]
        self.assertEqual(tables, ["step_1", "step_2", "step_3"])

    def test_re_running_applies_nothing(self):
        conn = sqlite3.connect(":memory:")
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._make_migrations(d, n=2)
            run_migrations(conn, d)
            result = run_migrations(conn, d)
            self.assertEqual(result.starting_version, 2)
            self.assertEqual(result.final_version, 2)
            self.assertEqual(result.applied, [])

    def test_only_newer_migrations_applied(self):
        conn = sqlite3.connect(":memory:")
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._make_migrations(d, n=3)
            # Manually mark DB at version 1 (skipping the first
            # migration in this test scenario)
            set_version(conn, 1)
            result = run_migrations(conn, d)
            self.assertEqual(result.starting_version, 1)
            self.assertEqual(result.final_version, 3)
            self.assertEqual(result.applied, [2, 3])

    def test_failing_migration_leaves_version_unchanged(self):
        conn = sqlite3.connect(":memory:")
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "001_good.sql").write_text("CREATE TABLE good (id INTEGER PRIMARY KEY);\n", encoding="utf-8")
            (d / "002_broken.sql").write_text("CREATE TABLE bad (id INTEGER PRIMARY KEY);\n"
                "THIS IS NOT VALID SQL;\n", encoding="utf-8")
            with self.assertRaises(sqlite3.Error):
                run_migrations(conn, d)
        # After the failure, user_version is at 1 (the last
        # successfully-applied migration), not 2.
        self.assertEqual(current_version(conn), 1)
        # And the broken migration's first CREATE was rolled back
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bad'"
        )
        self.assertIsNone(cur.fetchone())

    def test_handles_empty_migrations_dir(self):
        conn = sqlite3.connect(":memory:")
        with TemporaryDirectory() as tmp:
            result = run_migrations(conn, Path(tmp))
            self.assertEqual(result.starting_version, 0)
            self.assertEqual(result.final_version, 0)
            self.assertEqual(result.applied, [])


class RepoMigrationsDirectory(unittest.TestCase):
    """The committed migrations/ in the repo MUST satisfy the
    runner's invariants. A future contributor adding a 002_*.sql
    that doesn't parse, or skipping a version, fails here."""

    def test_repo_migrations_dir_exists(self):
        self.assertTrue(
            REPO_MIGRATIONS.exists(),
            f"migrations/ directory missing at {REPO_MIGRATIONS}",
        )

    def test_repo_migrations_discoverable(self):
        migrations = discover_migrations(REPO_MIGRATIONS)
        self.assertGreaterEqual(len(migrations), 1, "no committed migrations")
        # Version 1 must be present (baseline)
        self.assertEqual(migrations[0].version, 1)

    def test_repo_migrations_apply_cleanly_to_blank_db(self):
        conn = sqlite3.connect(":memory:")
        result = run_migrations(conn, REPO_MIGRATIONS)
        self.assertGreaterEqual(result.final_version, 1)
        # Baseline tables must exist after applying
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='companies'"
        )
        self.assertIsNotNone(cur.fetchone(), "baseline didn't create 'companies' table")

    def test_baseline_is_idempotent_with_create_schema(self):
        """A DB that went through SqliteCompanyDiscoveryRepository's
        _create_schema then through migrations MUST end up
        functionally identical to one that went through
        migrations alone. Critical: existing deploys booting after
        this commit MUST NOT lose data or hit a schema-conflict."""

        from company_discovery.sqlite_repository import (
            SqliteCompanyDiscoveryRepository,
        )

        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite3"
            # Boot the real repo — exercises _create_schema +
            # _apply_migrations both
            repo = SqliteCompanyDiscoveryRepository(db_path)
            try:
                conn = repo._connection
                # user_version should be at the latest available
                latest = latest_available_version(REPO_MIGRATIONS)
                self.assertEqual(current_version(conn), latest)
                # Baseline tables exist + are queryable
                cur = conn.execute("SELECT COUNT(*) FROM companies")
                self.assertEqual(cur.fetchone()[0], 0)
            finally:
                repo.close()


class LatestAvailableVersion(unittest.TestCase):
    def test_returns_zero_for_empty_dir(self):
        with TemporaryDirectory() as tmp:
            self.assertEqual(latest_available_version(Path(tmp)), 0)

    def test_returns_highest_version(self):
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "001_a.sql").write_text("-- a\n", encoding="utf-8")
            (d / "002_b.sql").write_text("-- b\n", encoding="utf-8")
            (d / "003_c.sql").write_text("-- c\n", encoding="utf-8")
            self.assertEqual(latest_available_version(d), 3)


if __name__ == "__main__":
    unittest.main()
