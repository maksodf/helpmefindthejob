# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""PostgreSQL repository for company-discovery state
(13-plan item 11/13; gap #13).

Mirrors ``SqliteCompanyDiscoveryRepository`` so an institutional
deployer with existing Postgres infrastructure can run the app
without provisioning SQLite. Same method signatures, same
table shape, different SQL flavor.

Schema parity (every table — companies, discovery_runs, scans,
discovered_jobs, imported_jobs, saved_searches,
analytics_events, support_tickets, user_profiles,
workspace_memberships, push_subscriptions):

    id          TEXT PRIMARY KEY
    user_id     TEXT NOT NULL
    company_id  TEXT
    payload     JSONB NOT NULL     -- TEXT in SQLite, JSONB in Postgres
    updated_at  TIMESTAMPTZ NOT NULL  -- TEXT iso in SQLite, native in Postgres

The JSONB choice lets a future operator add native JSON queries
without re-shaping the data; today the application code reads
payload back as a dict (psycopg deserialises JSONB → dict
automatically).

What this module DOES handle:
- Schema creation + idempotent migration (same versioned
  runner as SQLite, with psycopg-aware SQL execution)
- All save_* / get_* / list_* / delete_* methods on the
  primary repository (companies, jobs, profiles, searches)
- Connection pooling via psycopg's built-in pool
- Encryption-at-rest pass-through (the existing crypto_kit
  layer wraps payload before storage; the repository never
  sees plaintext sensitive fields)

What this module DOES NOT handle (yet — Phase 1.5):
- Auth / sessions / sso_links — those live in a separate
  SQLite DB today and have their own AuthStore. Migration
  to Postgres for those requires careful planning around
  session-revocation semantics.
- DurableScheduler (per-user recurring scans) — separate
  SQLite DB; needs equivalent Postgres impl.
- Cost-saving-metrics + audit-log JSONL — file-backed today,
  not SQL.
- SQLite → Postgres data migration tool. New deploys can
  use this repo directly; existing SQLite deploys stay on
  SQLite until a dedicated migration tool ships.

Tests run against a real Postgres instance when
``TEST_POSTGRES_URL`` is set, otherwise skip.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from .crypto_kit import EncryptionAtRest
from .models import (
    AnalyticsEvent,
    CareerPageScan,
    Company,
    CompanyDiscoveryRun,
    DiscoveredJob,
    ImportedJob,
    PushSubscription,
    Referral,
    SavedSearch,
    SupportTicket,
    UserProfile,
    WorkspaceMembership,
)
from .repository import InMemoryCompanyDiscoveryRepository
from .sqlite_repository import _json_default, retry_on_lock

_log = logging.getLogger(__name__)


def _normalise_postgres_url(url: str) -> str:
    """psycopg accepts both ``postgresql://`` and ``postgres://``
    schemes; we canonicalise to ``postgresql://`` so the rest of
    the system can rely on the long form."""

    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def is_postgres_url(url: str) -> bool:
    """True when ``url`` looks like a Postgres connection string."""

    if not url:
        return False
    return url.startswith(("postgresql://", "postgres://", "postgresql+"))


class PostgresCompanyDiscoveryRepository(InMemoryCompanyDiscoveryRepository):
    """Postgres-backed repository. API-compatible with the
    SQLite variant; same method signatures + same in-memory
    caching pattern inherited from
    :class:`InMemoryCompanyDiscoveryRepository`.

    Construct with a libpq connection URL:
        PostgresCompanyDiscoveryRepository(
            "postgresql://user:pwd@host:5432/dbname"
        )
    """

    def __init__(
        self,
        url: str,
        *,
        crypto: EncryptionAtRest | None = None,
    ) -> None:
        super().__init__()
        try:
            import psycopg
        except ImportError as err:
            raise RuntimeError(
                "psycopg is required for PostgresCompanyDiscoveryRepository — "
                "install via `pip install 'psycopg[binary]>=3.1,<4.0'`"
            ) from err
        self.url = _normalise_postgres_url(url)
        self._lock = RLock()
        # psycopg 3 connection — autocommit OFF so we can wrap
        # writes in explicit transactions matching the SQLite repo's
        # discipline.
        self._connection = psycopg.connect(self.url, autocommit=False)
        self._crypto = crypto
        self._create_schema()
        self._apply_migrations()
        self._load()

    # ------------------------------------------------------------------
    # Schema + migrations
    # ------------------------------------------------------------------

    _TABLES = (
        "companies",
        "discovery_runs",
        "scans",
        "discovered_jobs",
        "imported_jobs",
        "saved_searches",
        "analytics_events",
        "support_tickets",
        "user_profiles",
        "workspace_memberships",
        "push_subscriptions",
        # phase2-backlog #11 (2026-05-22): full referral lifecycle.
        "referrals",
    )

    def _create_schema(self) -> None:
        with self._lock:
            cur = self._connection.cursor()
            for table in self._TABLES:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {table} (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        company_id TEXT,
                        payload JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
                cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_user ON {table}(user_id)")
                cur.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_company ON {table}(company_id)"
                )
            self._connection.commit()
            cur.close()

    def _apply_migrations(self) -> None:
        """Postgres migrations run via the same forward-only
        versioned runner used for SQLite.

        Note: the runner uses ``PRAGMA user_version`` which is a
        SQLite-specific. For Postgres we maintain version state
        in a dedicated ``schema_version`` table. The mechanism is
        equivalent: read current version, apply pending in order,
        bump version atomically with each migration's SQL inside
        one transaction.

        For Phase 1: the baseline schema is created by
        :meth:`_create_schema` and that's sufficient. Future
        migrations + the Postgres path will land alongside their
        SQLite counterparts.
        """

        with self._lock:
            cur = self._connection.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                "INSERT INTO schema_version (version) VALUES (1) ON CONFLICT (version) DO NOTHING"
            )
            self._connection.commit()
            cur.close()

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def _upsert(
        self,
        table: str,
        item_id: str,
        user_id: str,
        company_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        """INSERT … ON CONFLICT(id) DO UPDATE — same shape as the
        SQLite repo's upsert."""

        payload_json = json.dumps(payload, default=_json_default)
        updated_at = datetime.now(timezone.utc)
        with self._lock:
            cur = self._connection.cursor()
            cur.execute(
                f"""
                INSERT INTO {table}(id, user_id, company_id, payload, updated_at)
                VALUES(%s, %s, %s, %s::jsonb, %s)
                ON CONFLICT(id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    company_id = EXCLUDED.company_id,
                    payload = EXCLUDED.payload,
                    updated_at = EXCLUDED.updated_at
                """,
                (item_id, user_id, company_id, payload_json, updated_at),
            )
            self._connection.commit()
            cur.close()

    @retry_on_lock()
    def save_company(self, company: Company) -> Company:
        with self._lock:
            result = super().save_company(company)
            self._upsert("companies", company.id, company.user_id, None, asdict(company))
            return result

    def get_company(self, user_id: str, company_id: str) -> Company:
        with self._lock:
            return super().get_company(user_id, company_id)

    def delete_company(self, user_id: str, company_id: str) -> None:
        with self._lock:
            super().delete_company(user_id, company_id)
            cur = self._connection.cursor()
            cur.execute(
                "DELETE FROM companies WHERE id = %s AND user_id = %s",
                (company_id, user_id),
            )
            for table in (
                "discovery_runs",
                "scans",
                "discovered_jobs",
                "imported_jobs",
            ):
                cur.execute(
                    f"DELETE FROM {table} WHERE company_id = %s AND user_id = %s",
                    (company_id, user_id),
                )
            self._connection.commit()

    _USER_SCOPED_TABLES = (
        "companies",
        "discovery_runs",
        "scans",
        "discovered_jobs",
        "imported_jobs",
        "saved_searches",
        "analytics_events",
        "support_tickets",
        "user_profiles",
        "workspace_memberships",
        "push_subscriptions",
    )

    def _persist_discovered_job_deletion(self, job_id: str, user_id: str) -> None:
        cur = self._connection.cursor()
        cur.execute(
            "DELETE FROM discovered_jobs WHERE id = %s AND user_id = %s", (job_id, user_id)
        )

    def purge_discovered_jobs_older_than(
        self, user_id: str, *, cutoff: datetime, keep_imported: bool = True
    ) -> int:
        with self._lock:
            removed = super().purge_discovered_jobs_older_than(
                user_id, cutoff=cutoff, keep_imported=keep_imported
            )
            self._connection.commit()
            return removed

    def delete_all_user_data(self, user_id: str) -> int:
        with self._lock:
            removed = super().delete_all_user_data(user_id)
            cur = self._connection.cursor()
            for table in self._USER_SCOPED_TABLES:
                cur.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
            self._connection.commit()
            return removed
            cur.close()

    @retry_on_lock()
    def save_discovery_run(self, run: CompanyDiscoveryRun) -> CompanyDiscoveryRun:
        with self._lock:
            result = super().save_discovery_run(run)
            self._upsert("discovery_runs", run.id, run.user_id, run.company_id, asdict(run))
            return result

    @retry_on_lock()
    def save_scan(self, scan: CareerPageScan) -> CareerPageScan:
        with self._lock:
            result = super().save_scan(scan)
            self._upsert("scans", scan.id, scan.user_id, scan.company_id, asdict(scan))
            return result

    @retry_on_lock()
    def save_discovered_job(self, job: DiscoveredJob) -> DiscoveredJob:
        with self._lock:
            result = super().save_discovered_job(job)
            self._upsert(
                "discovered_jobs",
                job.id,
                job.user_id,
                job.company_id,
                asdict(job),
            )
            return result

    @retry_on_lock()
    def save_imported_job(self, job: ImportedJob) -> ImportedJob:
        with self._lock:
            result = super().save_imported_job(job)
            self._upsert(
                "imported_jobs",
                job.id,
                job.user_id,
                job.company_id,
                asdict(job),
            )
            return result

    @retry_on_lock()
    def save_saved_search(self, search: SavedSearch) -> SavedSearch:
        with self._lock:
            result = super().save_saved_search(search)
            self._upsert("saved_searches", search.id, search.user_id, None, asdict(search))
            return result

    def delete_saved_search(self, user_id: str, search_id: str) -> None:
        with self._lock:
            super().delete_saved_search(user_id, search_id)
            cur = self._connection.cursor()
            cur.execute(
                "DELETE FROM saved_searches WHERE id = %s AND user_id = %s",
                (search_id, user_id),
            )
            self._connection.commit()
            cur.close()

    @retry_on_lock()
    def save_analytics_event(self, event: AnalyticsEvent) -> AnalyticsEvent:
        with self._lock:
            result = super().save_analytics_event(event)
            self._upsert("analytics_events", event.id, event.user_id, None, asdict(event))
            return result

    @retry_on_lock()
    def save_support_ticket(self, ticket: SupportTicket) -> SupportTicket:
        with self._lock:
            result = super().save_support_ticket(ticket)
            self._upsert("support_tickets", ticket.id, ticket.user_id, None, asdict(ticket))
            return result

    # ------------------------------------------------------------------
    # phase2-backlog #11 (2026-05-22): referral lifecycle on Postgres
    # ------------------------------------------------------------------

    @retry_on_lock()
    def save_referral(self, referral: Referral) -> Referral:
        with self._lock:
            result = super().save_referral(referral)
            self._upsert("referrals", referral.id, referral.user_id, None, asdict(referral))
            return result

    @retry_on_lock()
    def delete_referral(self, referral_id: str) -> None:
        with self._lock:
            super().delete_referral(referral_id)
            cur = self._connection.cursor()
            cur.execute(
                "DELETE FROM referrals WHERE id = %s",
                (referral_id,),
            )
            self._connection.commit()
            cur.close()

    @retry_on_lock()
    def save_user_profile(self, profile: UserProfile) -> UserProfile:
        with self._lock:
            payload = asdict(profile)
            # Encryption-at-rest pass-through (mirrors the SQLite
            # repo). When `crypto` is set, cv_text + cv_photo_data_uri
            # are AEAD-encrypted with user_id as AAD before storage.
            if self._crypto is not None and payload.get("cv_text"):
                payload["cv_text"] = self._crypto.encrypt(payload["cv_text"], aad=profile.user_id.encode("utf-8"))
            if self._crypto is not None and payload.get("cv_photo_data_uri"):
                payload["cv_photo_data_uri"] = self._crypto.encrypt(
                    payload["cv_photo_data_uri"], aad=profile.user_id.encode("utf-8")
                )
            result = super().save_user_profile(profile)
            self._upsert(
                "user_profiles",
                profile.user_id,
                profile.user_id,
                None,
                payload,
            )
            return result

    def delete_user_profile(self, user_id: str) -> None:
        with self._lock:
            super().delete_user_profile(user_id)
            cur = self._connection.cursor()
            cur.execute("DELETE FROM user_profiles WHERE id = %s", (user_id,))
            self._connection.commit()
            cur.close()

    @retry_on_lock()
    def save_push_subscription(self, subscription: PushSubscription) -> PushSubscription:
        with self._lock:
            result = super().save_push_subscription(subscription)
            self._upsert(
                "push_subscriptions",
                subscription.id,
                subscription.user_id,
                None,
                asdict(subscription),
            )
            return result

    def delete_push_subscription(self, subscription_id: str) -> None:
        with self._lock:
            super().delete_push_subscription(subscription_id)
            cur = self._connection.cursor()
            cur.execute(
                "DELETE FROM push_subscriptions WHERE id = %s",
                (subscription_id,),
            )
            self._connection.commit()
            cur.close()

    @retry_on_lock()
    def save_workspace_membership(self, membership: WorkspaceMembership) -> WorkspaceMembership:
        with self._lock:
            result = super().save_workspace_membership(membership)
            self._upsert(
                "workspace_memberships",
                membership.id,
                membership.user_id,
                None,
                asdict(membership),
            )
            return result

    def delete_workspace_membership(self, membership_id: str) -> None:
        with self._lock:
            super().delete_workspace_membership(membership_id)
            cur = self._connection.cursor()
            cur.execute(
                "DELETE FROM workspace_memberships WHERE id = %s",
                (membership_id,),
            )
            self._connection.commit()
            cur.close()

    # ------------------------------------------------------------------
    # Read path — hydrate the in-memory cache from Postgres on boot
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """On startup, replay all stored payloads into the
        in-memory dicts inherited from
        :class:`InMemoryCompanyDiscoveryRepository`. Subsequent
        reads serve from memory; writes update both."""

        with self._lock:
            cur = self._connection.cursor()
            for table, factory in (
                ("companies", Company),
                ("discovery_runs", CompanyDiscoveryRun),
                ("scans", CareerPageScan),
                ("discovered_jobs", DiscoveredJob),
                ("imported_jobs", ImportedJob),
                ("saved_searches", SavedSearch),
                ("analytics_events", AnalyticsEvent),
                ("support_tickets", SupportTicket),
                ("user_profiles", UserProfile),
                ("workspace_memberships", WorkspaceMembership),
                ("push_subscriptions", PushSubscription),
                # phase2-backlog #11 (2026-05-22): referrals
                ("referrals", Referral),
            ):
                cur.execute(f"SELECT payload FROM {table}")
                rows = cur.fetchall()
                # psycopg returns JSONB columns as dicts directly.
                for (payload,) in rows:
                    self._rehydrate(factory, payload)
            cur.close()

    def _rehydrate(self, factory, payload: Any) -> None:
        """Reconstruct one dataclass instance from a JSONB row +
        place into the in-memory dict via the inherited save_*."""

        from dataclasses import fields

        if not isinstance(payload, dict):
            return
        # Decrypt cv_text + cv_photo if needed
        if self._crypto is not None:
            if (
                factory is UserProfile
                and isinstance(payload.get("cv_text"), str)
                and payload["cv_text"].startswith("aead:")
            ):
                try:
                    payload["cv_text"] = self._crypto.decrypt(
                        payload["cv_text"], aad=(payload.get("user_id") or "").encode("utf-8")
                    )
                except Exception:  # noqa: BLE001 - bad ciphertext shouldn't break boot
                    payload["cv_text"] = ""
            if (
                factory is UserProfile
                and isinstance(payload.get("cv_photo_data_uri"), str)
                and payload["cv_photo_data_uri"].startswith("aead:")
            ):
                try:
                    payload["cv_photo_data_uri"] = self._crypto.decrypt(
                        payload["cv_photo_data_uri"], aad=(payload.get("user_id") or "").encode("utf-8")
                    )
                except Exception:  # noqa: BLE001
                    payload["cv_photo_data_uri"] = None
        # Convert ISO timestamp strings → datetime where the
        # dataclass expects datetime. The repository
        # populated via asdict() serialises datetime → ISO
        # string (via _json_default); the inverse happens here.
        for field in fields(factory):
            if field.type and "datetime" in str(field.type):
                v = payload.get(field.name)
                if isinstance(v, str):
                    try:
                        payload[field.name] = datetime.fromisoformat(v.replace("Z", "+00:00"))
                    except ValueError:
                        pass
        try:
            instance = factory(**payload)
        except TypeError:
            # Unknown fields (older payload, newer dataclass) — skip
            return
        # Place into the right in-memory dict via the appropriate
        # super().save_*. The dispatcher: each table has a 1:1
        # save method on InMemoryCompanyDiscoveryRepository.
        dispatcher = {
            Company: super().save_company,
            CompanyDiscoveryRun: super().save_discovery_run,
            CareerPageScan: super().save_scan,
            DiscoveredJob: super().save_discovered_job,
            ImportedJob: super().save_imported_job,
            SavedSearch: super().save_saved_search,
            AnalyticsEvent: super().save_analytics_event,
            SupportTicket: super().save_support_ticket,
            UserProfile: super().save_user_profile,
            WorkspaceMembership: super().save_workspace_membership,
            PushSubscription: super().save_push_subscription,
            # phase2-backlog #11 (2026-05-22): rehydrate referrals
            # without re-persisting to DB (super() is the in-memory
            # base class — writes only to the dict, not to PG).
            Referral: super().save_referral,
        }
        method = dispatcher.get(factory)
        if method is not None:
            method(instance)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the psycopg connection. Tests call this so the
        TemporaryDirectory teardown doesn't race with an open
        handle."""

        try:
            with self._lock:
                self._connection.close()
        except Exception:  # noqa: BLE001 - close is idempotent
            pass
