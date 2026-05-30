# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Per-user and per-domain quotas.

Three counters live in one sqlite DB:

- ``user_scans_per_day`` — number of career-page scans a user starts in
  one rolling UTC day.
- ``user_ai_calls_per_day`` — number of analyze requests a user fires.
- ``domain_scans_per_hour`` — total scans against a single domain in
  one rolling hour, summed across all users. Stops a single popular
  career site from being hammered.

Concurrency is tracked in memory (``MAX_ACTIVE_SCANS_PER_USER``) because
it is process-local; the existing per-company lock in ``app.py``
already prevents the same ``(user, company)`` from running twice.

Limits come from environment variables with safe defaults:

- ``HELPMEFINDTHEJOB_QUOTA_SCANS_PER_DAY`` (default 50)
- ``HELPMEFINDTHEJOB_QUOTA_AI_PER_DAY`` (default 50)
- ``HELPMEFINDTHEJOB_QUOTA_DOMAIN_PER_HOUR`` (default 30)
- ``HELPMEFINDTHEJOB_QUOTA_ACTIVE_SCANS`` (default 3)
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from company_discovery.env_compat import get_env


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today_key() -> str:
    return _now().strftime("%Y-%m-%d")


def _hour_key(when: datetime | None = None) -> str:
    when = when or _now()
    return when.strftime("%Y-%m-%dT%H")


@dataclass(frozen=True)
class QuotaLimits:
    scans_per_day: int = int(get_env("HELPMEFINDTHEJOB_QUOTA_SCANS_PER_DAY", "50"))
    ai_per_day: int = int(get_env("HELPMEFINDTHEJOB_QUOTA_AI_PER_DAY", "50"))
    domain_per_hour: int = int(get_env("HELPMEFINDTHEJOB_QUOTA_DOMAIN_PER_HOUR", "30"))
    active_scans: int = int(get_env("HELPMEFINDTHEJOB_QUOTA_ACTIVE_SCANS", "3"))


class QuotaError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class QuotaStore:
    def __init__(self, path: str | Path, *, limits: QuotaLimits | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.limits = limits or QuotaLimits()
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self._lock = threading.RLock()
        self._active_per_user: dict[str, int] = {}
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_counters (
                user_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                period TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, kind, period)
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS domain_counters (
                domain TEXT NOT NULL,
                period TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (domain, period)
            )
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def _user_count(self, user_id: str, kind: str, period: str) -> int:
        row = self.connection.execute(
            "SELECT count FROM user_counters WHERE user_id = ? AND kind = ? AND period = ?",
            (user_id, kind, period),
        ).fetchone()
        return int(row[0]) if row else 0

    def _domain_count(self, domain: str, period: str) -> int:
        row = self.connection.execute(
            "SELECT count FROM domain_counters WHERE domain = ? AND period = ?",
            (domain, period),
        ).fetchone()
        return int(row[0]) if row else 0

    def _bump_user(self, user_id: str, kind: str, period: str) -> None:
        self.connection.execute(
            """
            INSERT INTO user_counters(user_id, kind, period, count)
            VALUES(?, ?, ?, 1)
            ON CONFLICT(user_id, kind, period) DO UPDATE SET count = count + 1
            """,
            (user_id, kind, period),
        )
        self.connection.commit()

    def _bump_domain(self, domain: str, period: str) -> None:
        self.connection.execute(
            """
            INSERT INTO domain_counters(domain, period, count)
            VALUES(?, ?, 1)
            ON CONFLICT(domain, period) DO UPDATE SET count = count + 1
            """,
            (domain, period),
        )
        self.connection.commit()

    def usage(self, user_id: str) -> dict[str, int]:
        with self._lock:
            day = _today_key()
            scans = self._user_count(user_id, "scans", day)
            ai = self._user_count(user_id, "ai", day)
            return {
                "scansToday": scans,
                "scansLimitPerDay": self.limits.scans_per_day,
                "aiToday": ai,
                "aiLimitPerDay": self.limits.ai_per_day,
                "activeScans": self._active_per_user.get(user_id, 0),
                "activeScanLimit": self.limits.active_scans,
            }

    def can_start_scan(self, user_id: str, *, target_url: str | None = None) -> None:
        with self._lock:
            day = _today_key()
            if self._user_count(user_id, "scans", day) >= self.limits.scans_per_day:
                raise QuotaError(
                    "scan_quota_exhausted", "Daily scan limit reached. Try again tomorrow."
                )
            if self._active_per_user.get(user_id, 0) >= self.limits.active_scans:
                raise QuotaError(
                    "scan_concurrency_limit",
                    f"You can run at most {self.limits.active_scans} scans at once.",
                )
            if target_url:
                domain = (urlparse(target_url).netloc or "").casefold()
                if (
                    domain
                    and self._domain_count(domain, _hour_key()) >= self.limits.domain_per_hour
                ):
                    raise QuotaError(
                        "domain_rate_limited",
                        "This domain is being scanned a lot right now. Try again later.",
                    )

    def record_scan_started(self, user_id: str, *, target_url: str | None = None) -> None:
        with self._lock:
            self._bump_user(user_id, "scans", _today_key())
            self._active_per_user[user_id] = self._active_per_user.get(user_id, 0) + 1
            if target_url:
                domain = (urlparse(target_url).netloc or "").casefold()
                if domain:
                    self._bump_domain(domain, _hour_key())

    def record_scan_finished(self, user_id: str) -> None:
        with self._lock:
            current = self._active_per_user.get(user_id, 0)
            if current > 0:
                self._active_per_user[user_id] = current - 1

    def can_run_ai(self, user_id: str) -> None:
        with self._lock:
            if self._user_count(user_id, "ai", _today_key()) >= self.limits.ai_per_day:
                raise QuotaError(
                    "ai_quota_exhausted", "Daily AI analysis limit reached. Try again tomorrow."
                )

    def record_ai_run(self, user_id: str) -> None:
        with self._lock:
            self._bump_user(user_id, "ai", _today_key())

    def reserve_ai_run(self, user_id: str) -> None:
        """Atomic check-AND-consume of the daily AI limit (raises QuotaError if
        at the limit). Use this on the request path instead of
        can_run_ai()+record_ai_run() — those were two separate locked sections
        with the multi-second AI call between them, so concurrent requests at the
        limit both passed the check before either incremented (TOCTOU)."""
        with self._lock:
            day = _today_key()
            if self._user_count(user_id, "ai", day) >= self.limits.ai_per_day:
                raise QuotaError(
                    "ai_quota_exhausted", "Daily AI analysis limit reached. Try again tomorrow."
                )
            self._bump_user(user_id, "ai", day)

    def reserve_scan(self, user_id: str, *, target_url: str | None = None) -> None:
        """Atomic check-AND-consume of can_start_scan + record_scan_started, so
        concurrent scans can't both pass the limit check before incrementing."""
        with self._lock:
            day = _today_key()
            if self._user_count(user_id, "scans", day) >= self.limits.scans_per_day:
                raise QuotaError(
                    "scan_quota_exhausted", "Daily scan limit reached. Try again tomorrow."
                )
            if self._active_per_user.get(user_id, 0) >= self.limits.active_scans:
                raise QuotaError(
                    "scan_concurrency_limit",
                    f"You can run at most {self.limits.active_scans} scans at once.",
                )
            domain = ""
            if target_url:
                domain = (urlparse(target_url).netloc or "").casefold()
                if domain and self._domain_count(domain, _hour_key()) >= self.limits.domain_per_hour:
                    raise QuotaError(
                        "domain_rate_limited",
                        "This domain is being scanned a lot right now. Try again later.",
                    )
            self._bump_user(user_id, "scans", day)
            self._active_per_user[user_id] = self._active_per_user.get(user_id, 0) + 1
            if domain:
                self._bump_domain(domain, _hour_key())

    def admin_metrics(self) -> dict[str, int]:
        cutoff_day = (_now() - timedelta(days=1)).strftime("%Y-%m-%d")
        with self._lock:
            scan_today = self.connection.execute(
                "SELECT COALESCE(SUM(count),0) FROM user_counters WHERE kind = 'scans' AND period >= ?",
                (cutoff_day,),
            ).fetchone()[0]
            ai_today = self.connection.execute(
                "SELECT COALESCE(SUM(count),0) FROM user_counters WHERE kind = 'ai' AND period >= ?",
                (cutoff_day,),
            ).fetchone()[0]
            distinct_users = self.connection.execute(
                "SELECT COUNT(DISTINCT user_id) FROM user_counters WHERE period >= ?",
                (cutoff_day,),
            ).fetchone()[0]
            domain_top = self.connection.execute(
                "SELECT domain, count FROM domain_counters WHERE period = ? ORDER BY count DESC LIMIT 1",
                (_hour_key(),),
            ).fetchone()
        return {
            "scansLast24h": int(scan_today or 0),
            "aiLast24h": int(ai_today or 0),
            "distinctActiveUsers": int(distinct_users or 0),
            "topDomainThisHour": domain_top[0] if domain_top else None,
            "topDomainThisHourCount": int(domain_top[1]) if domain_top else 0,
        }
