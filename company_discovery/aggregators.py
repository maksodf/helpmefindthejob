"""Job-aggregator scaffolding.

Aggregators are the **second rail** of DirectJob Scout's source pipeline
(the first being direct career-page scans of watched companies). Each
aggregator wraps a public job-board API or RSS feed and emits a
normalized :class:`AggregatedJob` per posting it finds.

The pipeline:

    user query (role + location + persona)
        → JobAggregationEngine.search()
        → fan out to every active provider in parallel
        → normalize → AggregatedJob list
        → dedup against existing DiscoveredJob rows
        → return new + merged-sources counts

This module deliberately keeps the schema **separate from**
:class:`DiscoveryResult` (which is company-shaped) and
:class:`DiscoveredJob` (which is a per-user persisted row). The caller
in ``app.py`` is responsible for promoting an :class:`AggregatedJob`
to a persisted :class:`DiscoveredJob` when the user wants to save it.

Each provider must:
- have a unique ``name`` attribute (used in source-priority dedup)
- declare ``attribution`` if the provider's ToS requires it (Adzuna,
  Muse, etc.) — surfaced in the queue footer
- accept an optional ``fetcher`` kwarg in ``__init__`` for testing
  (same pattern as ``DuckDuckGoSearchProvider``)
- return a list of :class:`AggregatedJob`, never raise on network
  errors (return ``[]`` and let the engine continue)
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Iterable, Protocol


@dataclass
class AggregatedJob:
    """Normalized job posting from any third-party aggregator."""

    title: str
    company_name: str
    source: str  # provider name, e.g. "arbeitnow", "adzuna", "muse"
    source_url: str
    location: str | None = None
    description: str | None = None
    posted_at: datetime | None = None
    salary_hint: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderAttribution:
    """Legal/ToS attribution rendered in the queue footer."""

    name: str
    label: str
    url: str


class JobAggregatorProvider(Protocol):
    """Public API every aggregator must implement.

    Returning ``[]`` is preferred over raising on network errors so a
    single misbehaving provider never sinks the rest of the run.

    ``remote_only`` flags providers whose entire feed is remote-only
    (Remotive, We Work Remotely). The engine skips them when the
    user's saved search specifies a non-remote location, so a
    "Berlin" search no longer leaks remote-anywhere jobs into the
    queue. Default False keeps backwards-compatibility for providers
    that already handle location internally.
    """

    name: str
    attribution: ProviderAttribution | None
    remote_only: bool

    def search(
        self,
        *,
        query: str,
        location: str | None,
        limit: int = 25,
        persona_id: str | None = None,
    ) -> list[AggregatedJob]:
        ...


def _user_wants_remote(location: str | None) -> bool:
    """Return True when the user's search would accept remote-only
    feeds — empty location, or location text that explicitly mentions
    remote (e.g. 'Remote', 'Remote — DACH', 'remote (EU)')."""

    if not location:
        return True
    return "remote" in location.casefold()


def canonical_query(query: str, location: str | None) -> str:
    """Stable hash key for caching identical queries across users."""

    base = f"{(query or '').strip().casefold()}|{(location or '').strip().casefold()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]


# ---------- caching ---------------------------------------------------


class AggregatorResultCache:
    """Sqlite-backed result cache shared across users.

    Keyed on ``(provider_name, canonical_query)``. TTL defaults to one
    hour so a daily-digest run hitting Adzuna for ten different users
    with the same query only spends one of Adzuna's 250-call quota
    units, not ten.
    """

    def __init__(self, path: str | Path, ttl_seconds: int = 3600) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self._lock = RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS aggregator_cache (
                provider TEXT NOT NULL,
                query_hash TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (provider, query_hash)
            )
            """
        )
        self._connection.commit()

    def get(self, provider: str, query_hash: str) -> list[AggregatedJob] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload, expires_at FROM aggregator_cache WHERE provider = ? AND query_hash = ?",
                (provider, query_hash),
            ).fetchone()
        if row is None:
            return None
        payload, expires_at = row
        if int(time.time()) >= int(expires_at):
            return None
        try:
            entries = json.loads(payload)
        except (TypeError, ValueError):
            return None
        return [_decode(entry) for entry in entries if isinstance(entry, dict)]

    def put(self, provider: str, query_hash: str, jobs: list[AggregatedJob]) -> None:
        expires_at = int(time.time()) + self.ttl_seconds
        payload = json.dumps([_encode(job) for job in jobs], ensure_ascii=False)
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO aggregator_cache(provider, query_hash, expires_at, payload)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(provider, query_hash) DO UPDATE SET
                    expires_at = excluded.expires_at,
                    payload = excluded.payload
                """,
                (provider, query_hash, expires_at, payload),
            )
            self._connection.commit()

    def purge_expired(self) -> int:
        now = int(time.time())
        with self._lock:
            cur = self._connection.execute(
                "DELETE FROM aggregator_cache WHERE expires_at < ?", (now,),
            )
            self._connection.commit()
            return cur.rowcount

    def close(self) -> None:
        with self._lock:
            self._connection.close()


def _encode(job: AggregatedJob) -> dict:
    payload = asdict(job)
    if isinstance(job.posted_at, datetime):
        payload["posted_at"] = job.posted_at.isoformat()
    return payload


def _decode(payload: dict) -> AggregatedJob:
    posted_at_raw = payload.get("posted_at")
    posted_at = None
    if posted_at_raw:
        try:
            posted_at = datetime.fromisoformat(posted_at_raw)
        except ValueError:
            posted_at = None
    return AggregatedJob(
        title=str(payload.get("title", "")),
        company_name=str(payload.get("company_name", "")),
        source=str(payload.get("source", "unknown")),
        source_url=str(payload.get("source_url", "")),
        location=payload.get("location"),
        description=payload.get("description"),
        posted_at=posted_at,
        salary_hint=payload.get("salary_hint"),
        raw=dict(payload.get("raw") or {}),
    )


# ---------- engine ----------------------------------------------------


@dataclass
class AggregationOutcome:
    """Per-provider result of a single search."""

    provider: str
    job_count: int
    cached: bool
    error: str | None = None


# Source-priority order: direct company sites > ATS feeds > broad aggregators >
# best-effort web. Used to break composite-score ties so the canonical employer
# URL wins over an Indeed mirror when both surface the same job.
_SOURCE_PRIORITY = {
    # ATS adapters (extracted by service.py from a watched company's site)
    "career_page_scan": 100,
    "greenhouse": 95,
    "lever": 95,
    "personio": 95,
    "smartrecruiters": 95,
    "teamtailor": 95,
    # Curated companies + DDG-discovered company pages
    "curated": 80,
    # Niche / specialised aggregators
    "arbeitnow": 60,
    "muse": 55,
    "remotive": 55,
    "weworkremotely": 55,
    "hn_hiring": 50,
    # Broad aggregators (will land here when added)
    "adzuna": 45,
    "eures": 40,
    "bundesagentur": 40,
    # Bookmarklet / email-forward ingestion (Phase 3)
    "bookmarklet:indeed": 35,
    "bookmarklet:linkedin": 35,
    "bookmarklet:stepstone": 35,
    "bookmarklet:xing": 35,
    "duckduckgo": 30,
    "brave_search": 30,
}


def source_priority(source: str) -> int:
    """Higher = better. Defaults to 25 (lower than any known source)."""

    return _SOURCE_PRIORITY.get(source, 25)


def score_job(
    job: AggregatedJob,
    *,
    keyword_tokens: Iterable[str] = (),
    location: str | None = None,
    now: datetime | None = None,
    dismissed_terms: Iterable[str] = (),
) -> float:
    """Composite 0–1 score for ranking aggregated jobs.

    Inputs (all optional):
    - ``keyword_tokens`` — lowercase substrings to match in title +
      description + company. Each hit adds 0.10, capped at 0.50.
    - ``location`` — substring match on ``job.location`` or "remote"
      gets 0.10.
    - ``now`` — used to compute freshness; jobs posted in the last
      24h get the full 0.20 boost, decaying linearly to 0 over 30
      days. Missing ``posted_at`` gets 0.05 (neutral).
    - source priority gives up to 0.20 (normalised 100 → 0.20).
    - ``dismissed_terms`` — strings the user has flagged as "not
      relevant" (titles + company names from prior dismissals). Each
      substring hit deducts 0.20, floored at 0.0. Effectively pushes
      similar future jobs to the bottom of the queue without hard-
      hiding them so the user can still find them via search.
    """

    score = 0.0
    haystack = " ".join(part.casefold() for part in (
        job.title, job.company_name, job.description or "", job.location or "",
    ) if part)
    if keyword_tokens:
        hits = sum(1 for tok in keyword_tokens if tok and tok.casefold() in haystack)
        score += min(0.50, 0.10 * hits)
    if location:
        loc = location.casefold().strip()
        job_loc = (job.location or "").casefold()
        if loc and (loc in job_loc or "remote" in job_loc):
            score += 0.10
    # Freshness
    score += _freshness_score(job.posted_at, now=now)
    # Source priority — normalise 0..100 → 0..0.20
    score += min(0.20, source_priority(job.source) / 500.0)
    # Negative-filter learning
    if dismissed_terms:
        title_company = f"{job.title} {job.company_name}".casefold()
        penalty = 0.0
        for term in dismissed_terms:
            term_lc = (term or "").casefold().strip()
            if term_lc and term_lc in title_company:
                penalty += 0.20
        score -= min(0.40, penalty)
    return round(max(0.0, min(1.0, score)), 4)


def _freshness_score(posted_at: datetime | None, *, now: datetime | None = None) -> float:
    if posted_at is None:
        return 0.05
    current = now or datetime.now(timezone.utc)
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
    delta = (current - posted_at).total_seconds()
    if delta <= 24 * 3600:
        return 0.20
    if delta >= 30 * 24 * 3600:
        return 0.0
    # Linear decay 24h → 30 days
    days = delta / (24 * 3600)
    return round(max(0.0, 0.20 * (1 - (days - 1) / 29)), 4)


def rank_aggregated(
    jobs: list[AggregatedJob],
    *,
    keyword_tokens: Iterable[str] = (),
    location: str | None = None,
    cap: int = 50,
    now: datetime | None = None,
    dismissed_terms: Iterable[str] = (),
) -> list[tuple[AggregatedJob, float]]:
    """Score every job, sort by score DESC, cap to ``cap`` rows.

    Returns ``(job, score)`` tuples so callers can render the score.
    """

    tokens = list(keyword_tokens)
    dismissed = list(dismissed_terms)
    scored = [(job, score_job(job, keyword_tokens=tokens, location=location, now=now, dismissed_terms=dismissed)) for job in jobs]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:max(1, cap)]


class JobAggregationEngine:
    """Fan-out + cache for many ``JobAggregatorProvider`` instances."""

    def __init__(
        self,
        providers: Iterable[JobAggregatorProvider] | None = None,
        cache: AggregatorResultCache | None = None,
    ) -> None:
        self.providers: list[JobAggregatorProvider] = list(providers or [])
        self.cache = cache

    def search(
        self,
        *,
        query: str,
        location: str | None,
        limit_per_provider: int = 25,
        persona_id: str | None = None,
    ) -> tuple[list[AggregatedJob], list[AggregationOutcome]]:
        all_jobs: list[AggregatedJob] = []
        outcomes: list[AggregationOutcome] = []
        query_hash = canonical_query(query, location)
        accepts_remote = _user_wants_remote(location)
        for provider in self.providers:
            # Skip remote-only feeds (Remotive / WeWorkRemotely) when
            # the user's saved search names a specific city/region. A
            # "Berlin" search should not return remote-anywhere jobs —
            # those bleed into the queue and break reply-rate +
            # skill-gap analytics. The user opts into remote feeds by
            # leaving location empty or putting "remote" in it.
            if not accepts_remote and getattr(provider, "remote_only", False):
                outcomes.append(AggregationOutcome(
                    provider=provider.name,
                    job_count=0,
                    cached=False,
                    error="skipped_remote_only_for_location_search",
                ))
                continue
            cached = False
            jobs: list[AggregatedJob] = []
            error: str | None = None
            if self.cache is not None:
                hit = self.cache.get(provider.name, query_hash)
                if hit is not None:
                    jobs = hit
                    cached = True
            if not cached:
                try:
                    jobs = list(provider.search(
                        query=query,
                        location=location,
                        limit=limit_per_provider,
                        persona_id=persona_id,
                    ))
                except Exception as exc:  # noqa: BLE001
                    error = f"{type(exc).__name__}: {exc}"[:200]
                    jobs = []
                if self.cache is not None and jobs:
                    self.cache.put(provider.name, query_hash, jobs)
            outcomes.append(AggregationOutcome(
                provider=provider.name,
                job_count=len(jobs),
                cached=cached,
                error=error,
            ))
            all_jobs.extend(jobs)
        # Cross-provider host-priority dedup: collapse identical canonical
        # source URLs, prefer the provider with the longest description.
        seen: dict[str, AggregatedJob] = {}
        host_pattern = re.compile(r"^https?://([^/]+)/(.+?)(?:\?|#|$)")
        for job in all_jobs:
            match = host_pattern.match(job.source_url)
            host_path = match.group(1).lower() + "/" + match.group(2).lower() if match else job.source_url
            existing = seen.get(host_path)
            if existing is None or len(job.description or "") > len(existing.description or ""):
                seen[host_path] = job
        return list(seen.values()), outcomes

    def attributions(self) -> list[ProviderAttribution]:
        out: list[ProviderAttribution] = []
        for p in self.providers:
            attribution = getattr(p, "attribution", None)
            if isinstance(attribution, ProviderAttribution):
                out.append(attribution)
        return out
