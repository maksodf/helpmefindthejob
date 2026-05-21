# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Versioned SQLite migrations (4-week plan post-sprint polish: gap #20).

The project ships with `CREATE TABLE IF NOT EXISTS` blocks for
backward-compat — that's fine for a fresh deploy but says nothing
about how to evolve the schema. This module is the runner that
applies forward-only versioned migrations from ``migrations/*.sql``
in lexicographic order, tracked via SQLite's ``PRAGMA
user_version``.

Design:

- **Forward-only**: there is no rollback. SQLite doesn't easily
  support reversing ALTER TABLE, and a "rollback that doesn't
  rollback data" is worse than no rollback. If a migration is
  wrong, write a compensating forward migration.
- **Idempotent runner**: re-running on the same DB does nothing.
- **Stdlib-only**: no Alembic dependency. The project's anti-
  framework doctrine extends here.
- **One migration = one .sql file**: format ``NNN_description.sql``
  where NNN is the version number this migration brings the DB
  TO (so 001 brings v0→v1, 002 brings v1→v2, etc.).
- **Per-migration transaction**: each .sql runs inside a BEGIN/
  COMMIT. A failed migration leaves the DB at the pre-migration
  version, never a half-applied state.
- **No mid-statement comments**: SQLite's executescript handles
  ``--`` line comments and ``/* ... */`` block comments, so
  migrations stay readable.

Operator workflow:

1. Add a new file at ``migrations/NNN_<short_name>.sql`` where
   ``NNN`` is the next integer (zero-padded).
2. Run the app — the migrator picks it up at boot.
3. Confirm via ``PRAGMA user_version`` that the new version is
   active.

Contract tests at ``tests/test_sqlite_migrations.py`` pin:
- Migrations apply cleanly to a fresh DB.
- Idempotency (re-running is a no-op).
- Forward-only (an older user_version can't be re-applied).
- Each migration file has valid SQL (the runner parses it).
- The committed `migrations/001_baseline.sql` reflects the
  same shape that :meth:`SqliteCompanyDiscoveryRepository._
  create_schema` produces.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

# Default migrations directory. The repository's __init__.py
# resolves this relative to the repo root; tests pass an explicit
# directory.
_MIGRATIONS_DIRNAME = "migrations"


_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Migration:
    """One forward-only migration. The runner applies migrations
    in ascending version order until the DB reaches the latest."""

    version: int
    name: str
    path: Path
    sql: str


def _split_statements(sql: str) -> list[str]:
    """Split a migration script into individual SQL statements.

    Strips ``-- ...`` line comments and splits on ``;``. This is
    naive — a ``;`` inside a string literal would break it — but
    migrations are author-controlled and schema-focused; string
    literals are rare. If a migration legitimately needs a
    semicolon inside a literal, escape it via SQL standard
    `''` doubling or wrap the literal across multiple statements.

    Empty statements (whitespace + comment lines only) are
    skipped so trailing semicolons + comment blocks don't trip
    the runner.
    """

    # Strip block comments (/* ... */) first — they can span lines
    sql_no_block_comments = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    # Strip -- line comments
    cleaned_lines: list[str] = []
    for line in sql_no_block_comments.splitlines():
        if "--" in line:
            line = line[: line.index("--")]
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines)
    return [stmt.strip() for stmt in cleaned.split(";") if stmt.strip()]


def discover_migrations(migrations_dir: Path) -> list[Migration]:
    """Scan ``migrations_dir`` for ``NNN_<name>.sql`` files and
    return them sorted by version. Files that don't match the
    naming convention are skipped with a logged warning."""

    if not migrations_dir.exists():
        return []
    found: list[Migration] = []
    for path in sorted(migrations_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() != ".sql":
            continue
        m = re.match(r"^(\d{3,})_(.+)\.sql$", path.name)
        if not m:
            _log.warning(
                "migrations: skipping %s (filename doesn't match NNN_<name>.sql)",
                path.name,
            )
            continue
        version = int(m.group(1))
        name = m.group(2)
        sql = path.read_text(encoding="utf-8")
        found.append(Migration(version=version, name=name, path=path, sql=sql))
    # Sort by version (lexicographic sort on zero-padded names is
    # equivalent, but we do an explicit numeric sort for clarity)
    found.sort(key=lambda m: m.version)
    # Drift guard: version numbers must be contiguous from the
    # smallest found. A gap (e.g. 001, 003) likely means a
    # contributor lost a file in a rebase — fail loudly rather
    # than silently skipping migrations.
    if found:
        expected = found[0].version
        for migration in found:
            if migration.version != expected:
                raise ValueError(
                    f"migration version gap: expected {expected:03d}, "
                    f"got {migration.version:03d} ({migration.path.name})"
                )
            expected += 1
    return found


def current_version(connection: sqlite3.Connection) -> int:
    """Read the SQLite ``PRAGMA user_version`` value."""

    cur = connection.execute("PRAGMA user_version")
    row = cur.fetchone()
    return int(row[0]) if row else 0


def set_version(connection: sqlite3.Connection, version: int) -> None:
    """Set ``PRAGMA user_version``. SQLite doesn't allow parameter
    binding on PRAGMA — we validate the int and interpolate
    directly. Safe because ``version`` is always derived from a
    Migration we just verified."""

    if not isinstance(version, int) or version < 0:
        raise ValueError(f"invalid version: {version!r}")
    connection.execute(f"PRAGMA user_version = {int(version)}")


@dataclass(frozen=True)
class MigrationResult:
    """Outcome of a :func:`run_migrations` call. Useful for tests
    + the operator boot-log line."""

    starting_version: int
    final_version: int
    applied: list[int]


def run_migrations(
    connection: sqlite3.Connection,
    migrations_dir: Path,
) -> MigrationResult:
    """Apply every pending migration in ``migrations_dir``.

    A migration is "pending" if its version is strictly greater
    than the DB's current ``user_version``. The runner applies
    them in ascending order, each inside its own BEGIN/COMMIT,
    and bumps ``user_version`` after each successful migration.

    Returns a :class:`MigrationResult` documenting what was done
    so the operator can log it. The runner is idempotent — calling
    it twice in a row applies the second time's pending set
    (which is empty if nothing new shipped).
    """

    migrations = discover_migrations(migrations_dir)
    starting = current_version(connection)
    applied: list[int] = []
    # Python 3.9's sqlite3.executescript commits statement-by-
    # statement, so a mid-script failure leaves partial work
    # behind. To get true atomicity (all statements in a
    # migration apply together, or none do), we split the
    # script into individual statements + run them inside an
    # explicit transaction with isolation_level=None.
    original_isolation = connection.isolation_level
    connection.isolation_level = None  # manual transaction control
    try:
        for migration in migrations:
            if migration.version <= starting:
                continue
            statements = _split_statements(migration.sql)
            try:
                connection.execute("BEGIN")
                for stmt in statements:
                    connection.execute(stmt)
                # Bump user_version inside the same transaction
                # so schema change + version bump are atomic.
                connection.execute(
                    f"PRAGMA user_version = {int(migration.version)}"
                )
                connection.execute("COMMIT")
            except Exception:
                try:
                    connection.execute("ROLLBACK")
                except sqlite3.OperationalError:
                    pass
                raise
            applied.append(migration.version)
            _log.info(
                "migrations: applied %03d_%s (version %d → %d)",
                migration.version,
                migration.name,
                starting if not applied[:-1] else applied[-2],
                migration.version,
            )
    finally:
        connection.isolation_level = original_isolation
    final = current_version(connection)
    return MigrationResult(
        starting_version=starting,
        final_version=final,
        applied=applied,
    )


def latest_available_version(migrations_dir: Path) -> int:
    """Return the highest version number among the .sql files in
    ``migrations_dir``. Useful for the operator boot-log line
    ("schema at v3, latest available v5 — 2 pending")."""

    migrations = discover_migrations(migrations_dir)
    return migrations[-1].version if migrations else 0
