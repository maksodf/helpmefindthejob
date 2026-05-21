# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 #71 — persistent facet-indexed job-index.

A long-lived sqlite-backed index of every AggregatedJob the
deployment has seen, indexed by location + role-bucket + seniority-
class + language-detected. Powers Bug C piece-2's DiagnosticEngine
with evidence-backed explanations (e.g., "47 Senior frontend postings
in Berlin within commute range of Leipzig") instead of the current
cache-only / cold-cache-fallback pattern.

Architectural seam:
- ``AggregatorResultCache`` (existing) is keyed on (provider,
  canonical_query) with a 1-hour TTL. It exists to deduplicate
  provider-quota burn across users sharing the same query.
- ``JobIndex`` (this module) is keyed on the dedup'd job itself
  (source_url) with a longer TTL (14-day default per GDPR retention
  policy). It exists to power facet-aware analytics, not to dedupe
  provider calls. Both can coexist.

GDPR + retention: the index does NOT carry user_id. It records only
the publicly-visible job posting (title, company, location,
description, source URL). Per-user state (which user saw which job)
lives elsewhere (discovered_jobs / imported_jobs). The index is the
deployment's curated public-data view.

Phase A (this commit): substrate + write-through.
Phase B (follow-up): seniority + language classification heuristics
that populate the seniority_class / language_detected columns at
write-through time.
Phase C: DiagnosticEngine rewiring to read from the index.
Phase D: commute-range adjacency table (relates to #74).
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
import unicodedata
from dataclasses import asdict
from pathlib import Path
from threading import RLock
from typing import Iterable

from .aggregators import AggregatedJob, _decode, _encode


_DEFAULT_TTL_SECONDS = 14 * 24 * 3600  # 14 days


def _norm_location(text: str | None) -> str:
    """Case-folded, accent-stripped, leading/trailing-whitespace-
    trimmed form of a location string for facet matching. Maps e.g.
    "Berlin, Deutschland", "berlin", "Berlin DE" → "berlin"."""

    if not text:
        return ""
    # Strip accents
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    # Lowercase + collapse whitespace
    folded = folded.casefold().strip()
    # Take the first comma-separated segment (drop trailing country /
    # postal-code clutter).
    first = folded.split(",")[0].strip()
    # Collapse internal whitespace
    return re.sub(r"\s+", " ", first)


def _norm_title(text: str | None) -> str:
    """Normalised title for facet matching (case-fold + strip)."""

    if not text:
        return ""
    folded = unicodedata.normalize("NFKD", text).casefold().strip()
    return re.sub(r"\s+", " ", folded)


class JobIndex:
    """Persistent facet-indexed job store. Thread-safe (RLock-
    protected sqlite WAL).

    Schema columns (all denormalised for facet-query simplicity):

    - ``source_url`` (TEXT, primary key): canonicalised job URL.
    - ``title``, ``title_norm``: original + normalised title.
    - ``company_name``, ``location``, ``location_norm``: company + location.
    - ``source``: aggregator name (adzuna / arbeitnow / etc.).
    - ``role_bucket`` (TEXT, nullable): from
      ``job_type_filter.identify_bucket`` when computable, else "".
    - ``seniority_class`` (TEXT, nullable): Phase B heuristic.
    - ``language_detected`` (TEXT, nullable): Phase B heuristic.
    - ``description_excerpt`` (TEXT): first 1000 chars of the
      description. Truncated to keep the index lean.
    - ``posted_at`` (INTEGER, nullable): epoch seconds of the
      job's posting date when known.
    - ``indexed_at`` (INTEGER): epoch seconds of when this row
      was written.
    - ``ttl_at`` (INTEGER): epoch seconds of when this row
      expires (indexed_at + ttl_seconds).
    - ``raw_payload`` (TEXT): JSON-encoded AggregatedJob for
      round-trip retrieval. Optional — facet queries don't
      use it.
    """

    def __init__(
        self,
        path: str | Path,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = int(ttl_seconds)
        self._lock = RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS job_index (
                source_url TEXT NOT NULL PRIMARY KEY,
                title TEXT NOT NULL,
                title_norm TEXT NOT NULL,
                company_name TEXT NOT NULL,
                location TEXT NOT NULL,
                location_norm TEXT NOT NULL,
                source TEXT NOT NULL,
                role_bucket TEXT NOT NULL DEFAULT '',
                seniority_class TEXT NOT NULL DEFAULT '',
                language_detected TEXT NOT NULL DEFAULT '',
                description_excerpt TEXT NOT NULL DEFAULT '',
                posted_at INTEGER,
                indexed_at INTEGER NOT NULL,
                ttl_at INTEGER NOT NULL,
                raw_payload TEXT NOT NULL
            )
            """
        )
        # Facet indexes — speeds up "count by role_bucket + location" lookups.
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_job_index_location ON job_index(location_norm)"
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_job_index_role_bucket ON job_index(role_bucket)"
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_job_index_ttl ON job_index(ttl_at)"
        )
        self._connection.commit()

    def upsert_jobs(
        self,
        jobs: Iterable[AggregatedJob],
        *,
        role_bucket: str | None = None,
        seniority_class: str | None = None,
        language_detected: str | None = None,
    ) -> int:
        """Write-through entry point. Each job is INSERT-or-REPLACEd
        keyed on source_url. The caller passes optional facets that
        apply to ALL jobs in the iterable (typical case: a single
        search hits the index with a known role_bucket + location).

        Returns the number of rows written.
        """
        now = int(time.time())
        ttl_at = now + self.ttl_seconds
        rows: list[tuple] = []
        for job in jobs:
            if not job.source_url:
                continue  # source_url is the primary key — skip unkeyed jobs
            description = job.description or ""
            description_excerpt = description[:1000]
            posted_at: int | None = None
            if job.posted_at:
                try:
                    posted_at = int(job.posted_at.timestamp())
                except Exception:  # noqa: BLE001 - posted_at may be malformed; degrade to None
                    posted_at = None
            rows.append(
                (
                    job.source_url,
                    job.title or "",
                    _norm_title(job.title),
                    job.company_name or "",
                    job.location or "",
                    _norm_location(job.location),
                    job.source or "",
                    role_bucket or "",
                    seniority_class or "",
                    language_detected or "",
                    description_excerpt,
                    posted_at,
                    now,
                    ttl_at,
                    json.dumps(_encode(job), ensure_ascii=False),
                )
            )
        if not rows:
            return 0
        with self._lock:
            self._connection.executemany(
                """
                INSERT INTO job_index(
                    source_url, title, title_norm,
                    company_name, location, location_norm,
                    source, role_bucket, seniority_class,
                    language_detected, description_excerpt,
                    posted_at, indexed_at, ttl_at, raw_payload
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_url) DO UPDATE SET
                    title = excluded.title,
                    title_norm = excluded.title_norm,
                    company_name = excluded.company_name,
                    location = excluded.location,
                    location_norm = excluded.location_norm,
                    source = excluded.source,
                    role_bucket = CASE WHEN excluded.role_bucket = '' THEN job_index.role_bucket ELSE excluded.role_bucket END,
                    seniority_class = CASE WHEN excluded.seniority_class = '' THEN job_index.seniority_class ELSE excluded.seniority_class END,
                    language_detected = CASE WHEN excluded.language_detected = '' THEN job_index.language_detected ELSE excluded.language_detected END,
                    description_excerpt = excluded.description_excerpt,
                    posted_at = COALESCE(excluded.posted_at, job_index.posted_at),
                    indexed_at = excluded.indexed_at,
                    ttl_at = excluded.ttl_at,
                    raw_payload = excluded.raw_payload
                """,
                rows,
            )
            self._connection.commit()
        return len(rows)

    def count_by_facets(
        self,
        *,
        role_bucket: str | None = None,
        location: str | None = None,
        seniority_class: str | None = None,
        language_detected: str | None = None,
        ttl_now: int | None = None,
    ) -> int:
        """Count jobs matching the given facet predicates. Each facet
        is exact-match against the normalised column; empty / None
        means "no filter on that facet". TTL: rows past ttl_at are
        excluded (caller can pass ttl_now=0 to include expired rows)."""

        now = int(time.time()) if ttl_now is None else int(ttl_now)
        clauses: list[str] = ["ttl_at > ?"]
        params: list[object] = [now]
        if role_bucket:
            clauses.append("role_bucket = ?")
            params.append(role_bucket)
        if location:
            clauses.append("location_norm = ?")
            params.append(_norm_location(location))
        if seniority_class:
            clauses.append("seniority_class = ?")
            params.append(seniority_class)
        if language_detected:
            clauses.append("language_detected = ?")
            params.append(language_detected)
        sql = "SELECT COUNT(*) FROM job_index WHERE " + " AND ".join(clauses)
        with self._lock:
            row = self._connection.execute(sql, params).fetchone()
        return int(row[0]) if row else 0

    def jobs_by_facets(
        self,
        *,
        role_bucket: str | None = None,
        location: str | None = None,
        ttl_now: int | None = None,
        limit: int = 100,
    ) -> list[AggregatedJob]:
        """Return up to ``limit`` non-expired jobs matching the facet
        predicates. Useful for DiagnosticEngine evidence rendering
        (e.g. "here's a sample of the 47 postings we found")."""

        now = int(time.time()) if ttl_now is None else int(ttl_now)
        clauses: list[str] = ["ttl_at > ?"]
        params: list[object] = [now]
        if role_bucket:
            clauses.append("role_bucket = ?")
            params.append(role_bucket)
        if location:
            clauses.append("location_norm = ?")
            params.append(_norm_location(location))
        sql = (
            "SELECT raw_payload FROM job_index WHERE "
            + " AND ".join(clauses)
            + " ORDER BY indexed_at DESC LIMIT ?"
        )
        params.append(int(limit))
        with self._lock:
            rows = self._connection.execute(sql, params).fetchall()
        jobs: list[AggregatedJob] = []
        for (payload,) in rows:
            try:
                entry = json.loads(payload)
                if isinstance(entry, dict):
                    jobs.append(_decode(entry))
            except (TypeError, ValueError):
                continue
        return jobs

    def purge_expired(self) -> int:
        """Delete rows past their ttl_at. Returns the number of rows
        purged. Safe to call in a background scheduler."""

        now = int(time.time())
        with self._lock:
            cur = self._connection.execute(
                "DELETE FROM job_index WHERE ttl_at < ?", (now,)
            )
            self._connection.commit()
            return cur.rowcount

    def close(self) -> None:
        with self._lock:
            self._connection.close()
