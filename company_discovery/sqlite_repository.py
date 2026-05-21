# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from .crypto_kit import EncryptionAtRest, is_aead_blob
from .db_errors import retry_on_lock
from .models import (
    AnalyticsEvent,
    CareerPageScan,
    Company,
    CompanyDiscoveryRun,
    DiscoveredJob,
    ImportedJob,
    PushSubscription,
    SavedSearch,
    SupportTicket,
    UserProfile,
    WorkspaceMembership,
)
from .repository import InMemoryCompanyDiscoveryRepository


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _drop_none(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


class SqliteCompanyDiscoveryRepository(InMemoryCompanyDiscoveryRepository):
    def __init__(
        self,
        path: str | Path,
        *,
        crypto: EncryptionAtRest | None = None,
    ) -> None:
        super().__init__()
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        # Encryption-at-rest for ``profile.cv_text``. When ``crypto`` is
        # None (e.g. tests, in-memory dev) the plain JSON path is used.
        # When set, new writes are AEAD-encrypted with the user_id as
        # AAD and existing legacy plain values are migrated lazily on
        # next save.
        self._crypto = crypto
        self._create_schema()
        self._load()

    @retry_on_lock()
    def save_company(self, company: Company) -> Company:
        # Phase 2 #78 Layer 3: @retry_on_lock — Case A (concurrency
        # lock) retries inside the helper before propagating; if the
        # underlying sqlite still raises after 3 attempts the policy
        # classifier at the HTTP boundary maps it to db_lock_busy
        # + friendly user message.
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
            for table in (
                "companies",
                "discovery_runs",
                "scans",
                "discovered_jobs",
                "imported_jobs",
            ):
                if table == "companies":
                    self._connection.execute(
                        "DELETE FROM companies WHERE id = ? AND user_id = ?", (company_id, user_id)
                    )
                else:
                    self._connection.execute(
                        "DELETE FROM " + table + " WHERE company_id = ? AND user_id = ?",
                        (company_id, user_id),
                    )
            self._connection.commit()

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
            self._upsert("discovered_jobs", job.id, job.user_id, job.company_id, asdict(job))
            return result

    @retry_on_lock()
    def save_imported_job(self, job: ImportedJob) -> ImportedJob:
        with self._lock:
            result = super().save_imported_job(job)
            self._upsert("imported_jobs", job.id, job.user_id, job.company_id, asdict(job))
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
            self._connection.execute(
                "DELETE FROM saved_searches WHERE id = ? AND user_id = ?",
                (search_id, user_id),
            )
            self._connection.commit()

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

    @retry_on_lock()
    def save_user_profile(self, profile: UserProfile) -> UserProfile:
        with self._lock:
            result = super().save_user_profile(profile)
            payload = asdict(profile)
            cv = payload.get("cv_text")
            if self._crypto and cv and not is_aead_blob(cv):
                # Encrypt before persisting; in-memory ``profile.cv_text``
                # stays plaintext so the rest of the app sees no change.
                payload["cv_text"] = self._crypto.encrypt(
                    cv,
                    aad=profile.user_id.encode("utf-8"),
                )
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
            self._connection.execute(
                "DELETE FROM user_profiles WHERE user_id = ?",
                (user_id,),
            )
            self._connection.commit()

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
            self._connection.execute(
                "DELETE FROM push_subscriptions WHERE id = ?",
                (subscription_id,),
            )
            self._connection.commit()

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
            self._connection.execute(
                "DELETE FROM workspace_memberships WHERE id = ?",
                (membership_id,),
            )
            self._connection.commit()

    def list_companies(self, user_id: str) -> list[Company]:
        with self._lock:
            return list(super().list_companies(user_id))

    def list_discovered_jobs(
        self, user_id: str, company_id: str | None = None
    ) -> list[DiscoveredJob]:
        with self._lock:
            return list(super().list_discovered_jobs(user_id, company_id))

    def list_discovery_runs(self, user_id: str) -> list[CompanyDiscoveryRun]:
        with self._lock:
            return list(super().list_discovery_runs(user_id))

    def list_scans(self, user_id: str) -> list[CareerPageScan]:
        with self._lock:
            return list(super().list_scans(user_id))

    def list_imported_jobs(self, user_id: str) -> list[ImportedJob]:
        with self._lock:
            return list(super().list_imported_jobs(user_id))

    def watchlist_summary(self, user_id: str) -> dict[str, object]:
        with self._lock:
            return super().watchlist_summary(user_id)

    def find_duplicate_discovered_job(self, candidate: DiscoveredJob) -> DiscoveredJob | None:
        with self._lock:
            return super().find_duplicate_discovered_job(candidate)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _create_schema(self) -> None:
        for table in (
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
        ):
            self._connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    company_id TEXT,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{table}_user ON {table}(user_id)"
            )
            self._connection.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{table}_company ON {table}(company_id)"
            )
        self._connection.commit()

    def _upsert(
        self,
        table: str,
        item_id: str,
        user_id: str,
        company_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        self._connection.execute(
            f"""
            INSERT INTO {table}(id, user_id, company_id, payload, updated_at)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                user_id = excluded.user_id,
                company_id = excluded.company_id,
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (
                item_id,
                user_id,
                company_id,
                json.dumps(payload, default=_json_default),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._connection.commit()

    def _load(self) -> None:
        for payload in self._load_payloads("companies"):
            item = Company(
                **_drop_none(
                    {
                        **payload,
                        "created_at": _parse_datetime(payload.get("created_at")),
                        "updated_at": _parse_datetime(payload.get("updated_at")),
                    }
                )
            )
            self.companies[item.id] = item

        for payload in self._load_payloads("discovery_runs"):
            item = CompanyDiscoveryRun(
                **_drop_none(
                    {
                        **payload,
                        "started_at": _parse_datetime(payload.get("started_at")),
                        "finished_at": _parse_datetime(payload.get("finished_at")),
                        "created_at": _parse_datetime(payload.get("created_at")),
                    }
                )
            )
            self.discovery_runs[item.id] = item

        for payload in self._load_payloads("scans"):
            item = CareerPageScan(
                **_drop_none(
                    {
                        **payload,
                        "last_checked_at": _parse_datetime(payload.get("last_checked_at")),
                        "created_at": _parse_datetime(payload.get("created_at")),
                    }
                )
            )
            self.scans[item.id] = item

        for payload in self._load_payloads("discovered_jobs"):
            item = DiscoveredJob(
                **_drop_none(
                    {
                        **payload,
                        "discovered_at": _parse_datetime(payload.get("discovered_at")),
                        "auto_fit_at": _parse_datetime(payload.get("auto_fit_at")),
                        "created_at": _parse_datetime(payload.get("created_at")),
                        "updated_at": _parse_datetime(payload.get("updated_at")),
                    }
                )
            )
            self.discovered_jobs[item.id] = item

        for payload in self._load_payloads("imported_jobs"):
            item = ImportedJob(
                **_drop_none(
                    {
                        **payload,
                        "analyzed_at": _parse_datetime(payload.get("analyzed_at")),
                        "reminder_at": _parse_datetime(payload.get("reminder_at")),
                        "created_at": _parse_datetime(payload.get("created_at")),
                        "updated_at": _parse_datetime(payload.get("updated_at")),
                    }
                )
            )
            self.imported_jobs[item.id] = item

        for payload in self._load_payloads("saved_searches"):
            item = SavedSearch(
                **_drop_none(
                    {
                        **payload,
                        "created_at": _parse_datetime(payload.get("created_at")),
                        "updated_at": _parse_datetime(payload.get("updated_at")),
                        "last_seen_at": _parse_datetime(payload.get("last_seen_at")),
                    }
                )
            )
            self.saved_searches[item.id] = item

        for payload in self._load_payloads("analytics_events"):
            item = AnalyticsEvent(
                **_drop_none(
                    {
                        **payload,
                        "created_at": _parse_datetime(payload.get("created_at")),
                    }
                )
            )
            self.analytics_events[item.id] = item

        for payload in self._load_payloads("support_tickets"):
            item = SupportTicket(
                **_drop_none(
                    {
                        **payload,
                        "created_at": _parse_datetime(payload.get("created_at")),
                    }
                )
            )
            self.support_tickets[item.id] = item

        for payload in self._load_payloads("user_profiles"):
            cv = payload.get("cv_text")
            if cv and is_aead_blob(cv):
                # Encrypted blob → decrypt back to plaintext for the
                # in-memory model. If the master key has rotated and
                # the blob no longer decrypts, drop the value rather
                # than crash the load — the user can re-paste their CV.
                if self._crypto is None:
                    payload["cv_text"] = None
                else:
                    try:
                        payload["cv_text"] = self._crypto.decrypt(
                            cv,
                            aad=payload["user_id"].encode("utf-8"),
                        )
                    except ValueError:
                        payload["cv_text"] = None
            profile = UserProfile(
                **_drop_none(
                    {
                        **payload,
                        "created_at": _parse_datetime(payload.get("created_at")),
                        "updated_at": _parse_datetime(payload.get("updated_at")),
                        "last_push_notified_at": _parse_datetime(
                            payload.get("last_push_notified_at")
                        ),
                    }
                )
            )
            self.user_profiles[profile.user_id] = profile

        for payload in self._load_payloads("workspace_memberships"):
            membership = WorkspaceMembership(
                **_drop_none(
                    {
                        **payload,
                        "created_at": _parse_datetime(payload.get("created_at")),
                    }
                )
            )
            self.workspace_memberships[membership.id] = membership

        for payload in self._load_payloads("push_subscriptions"):
            sub = PushSubscription(
                **_drop_none(
                    {
                        **payload,
                        "created_at": _parse_datetime(payload.get("created_at")),
                        "updated_at": _parse_datetime(payload.get("updated_at")),
                    }
                )
            )
            self.push_subscriptions[sub.id] = sub

    def _load_payloads(self, table: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(f"SELECT payload FROM {table}").fetchall()
        return [json.loads(row[0]) for row in rows]
