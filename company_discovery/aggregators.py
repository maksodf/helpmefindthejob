# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Job-aggregator scaffolding.

Aggregators are the **second rail** of Helpmefindthejob's source pipeline
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
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Iterable, Iterator, Protocol

# ---------- locale-tolerant location matching ----------------------------

# Common DE/EU/EN city aliases — substring-folded for matching. Each tuple
# is treated symmetrically: querying any alias matches any job whose
# location text contains any other alias from the same group. Keep this
# list short and city-level — country-name aliases are too noisy.
_CITY_ALIASES: tuple[tuple[str, ...], ...] = (
    ("munich", "münchen", "muenchen"),
    ("cologne", "köln", "koeln"),
    ("nuremberg", "nürnberg", "nuernberg"),
    ("vienna", "wien"),
    ("zurich", "zürich", "zuerich"),
    ("geneva", "genève", "genf"),
    ("warsaw", "warszawa"),
    ("prague", "praha"),
    ("copenhagen", "københavn", "kopenhagen"),
    ("brussels", "bruxelles", "brüssel"),
    ("dusseldorf", "düsseldorf", "duesseldorf"),
)


def _fold_diacritics(text: str) -> str:
    """Strip combining marks so 'München' compares equal to 'Munchen'.

    Decomposes via NFKD and drops the combining-mark codepoints. This
    catches ä→a, ö→o, ü→u, ß→ss (after explicit replacement). Does NOT
    transliterate ä→ae — that's covered by the alias table for the
    cities where it actually matters."""

    if not text:
        return ""
    # Explicit ß→ss replacement — NFKD doesn't decompose it.
    text = text.replace("ß", "ss").replace("ẞ", "SS")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


# DE/EU cities that also exist as small US towns. When the user types
# one of these (without a country qualifier), we reject jobs whose
# location text looks like a US listing — i.e. ends in a US state code
# pattern or contains ", USA" / ", US".
_DE_EU_AMBIGUOUS_CITIES: frozenset[str] = frozenset(
    {
        "berlin",
        "hamburg",
        "frankfurt",
        "munich",
        "munchen",
        "vienna",
        "wien",
        "paris",
        "athens",
        "bremen",
        "cologne",
        "koln",
        "koeln",
        "dresden",
        "essen",
    }
)

# US-state-code pattern: ", XX" where XX is a 2-letter postal code, or
# ", USA" / ", US" / ", United States" anywhere in the text.
#
# Deliberate exclusions:
# - DE (Delaware) collides with the ISO country code for Germany.
# - IN (Indiana) collides with "in" — too noisy. Indiana jobs are rare.
# - OR (Oregon) collides with the English conjunction.
# - CO (Colorado) and CA (California) collide with too many companies.
# - WA (Washington) is fine in EU job text since "Wa" rarely appears
#   after a comma in DE/EU listings; keeping it.
# In practice the missed states (CO, CA, IN, OR, DE) are very unlikely
# to host a DE/EU-namesake city in our feeds, so the loss is tiny.
_US_HINT_RE = re.compile(
    r",\s*"
    r"(?:al|ak|az|ar|ct|fl|ga|hi|id|il|ia|ks|ky|la|me|md|"
    r"ma|mi|mn|ms|mo|mt|ne|nv|nh|nj|nm|ny|nc|nd|oh|ok|pa|ri|sc|sd|"
    r"tn|tx|ut|vt|va|wa|wv|wi|wy)"
    r"\b(?:,\s*(?:usa?|united states))?",
    re.IGNORECASE,
)
_US_COUNTRY_RE = re.compile(r"\b(?:usa|united states)\b", re.IGNORECASE)


def _looks_like_us_listing(job_location: str) -> bool:
    """Does the job's location text look like a US listing? Heuristic:
    matches a ', XX' US state postal-code pattern OR explicit US country
    marker. Used only when the user typed a DE/EU-ambiguous city without
    a country qualifier."""

    if not job_location:
        return False
    return bool(_US_HINT_RE.search(job_location) or _US_COUNTRY_RE.search(job_location))


def location_matches(user_location: str | None, job_location: str | None) -> bool:
    """True when the user's location text matches the job's location.

    Defense in depth on top of plain casefold-substring matching:
    1. Strip diacritics so 'munchen' matches 'München'.
    2. Expand DE/EU city aliases so 'Munich' matches 'München' and vice
       versa.
    3. Reject same-name US namesakes when the user typed an ambiguous
       DE/EU city without a country qualifier (e.g. 'Berlin' alone
       should not match 'Berlin, GA, USA'; but 'Berlin, US' still does).

    Empty user_location matches anything (caller's job to skip the
    filter)."""

    if not user_location:
        return True
    user_raw = user_location.casefold().strip()
    user_norm = _fold_diacritics(user_raw)
    job_raw = (job_location or "").casefold()
    job_norm = _fold_diacritics(job_raw)
    if not user_norm:
        return True

    user_has_country_hint = bool(
        _US_HINT_RE.search(user_location)
        or _US_COUNTRY_RE.search(user_location)
        or any(
            hint in user_raw
            for hint in (
                "germany",
                "deutschland",
                "austria",
                "österreich",
                "osterreich",
                "switzerland",
                "schweiz",
                "france",
                "italy",
                "spain",
                "netherlands",
                "belgium",
                "denmark",
                "poland",
                "czech",
            )
        )
    )
    is_ambiguous_de_city = not user_has_country_hint and user_norm in _DE_EU_AMBIGUOUS_CITIES

    if user_norm in job_norm:
        if is_ambiguous_de_city and _looks_like_us_listing(job_raw):
            return False
        return True
    # Alias expansion: if the user's text contains any alias from a
    # group, the job qualifies if its location contains any other alias
    # from the same group.
    for group in _CITY_ALIASES:
        folded_group = [_fold_diacritics(alias) for alias in group]
        if any(alias in user_norm for alias in folded_group):
            if any(alias in job_norm for alias in folded_group):
                if is_ambiguous_de_city and _looks_like_us_listing(job_raw):
                    return False
                return True
    return False


# ---------- seniority-band intelligence -----------------------------------

# Words that, when present in the user's query, signal an explicit
# seniority band. The values are the conflicting bands — if a job
# title contains any of those, we treat it as a seniority mismatch.
_SENIORITY_CONFLICTS: dict[str, tuple[str, ...]] = {
    "senior": (
        "junior",
        "intern",
        "internship",
        "trainee",
        "praktikant",
        "working student",
        "werkstudent",
        "apprentice",
        "azubi",
    ),
    "lead": (
        "junior",
        "intern",
        "internship",
        "trainee",
        "praktikant",
        "working student",
        "werkstudent",
        "apprentice",
        "azubi",
    ),
    "staff": (
        "junior",
        "intern",
        "internship",
        "trainee",
        "praktikant",
        "working student",
        "werkstudent",
        "apprentice",
        "azubi",
    ),
    "principal": (
        "junior",
        "intern",
        "internship",
        "trainee",
        "praktikant",
        "working student",
        "werkstudent",
        "apprentice",
        "azubi",
    ),
    "head of": (
        "junior",
        "intern",
        "internship",
        "trainee",
        "praktikant",
        "working student",
        "werkstudent",
        "apprentice",
        "azubi",
    ),
    "junior": (
        "senior",
        "lead",
        "staff",
        "principal",
        "head of",
        "director",
        "vp ",
        "chief",
        "cto",
        "cfo",
        "cmo",
        "ceo",
    ),
    "intern": (
        "senior",
        "lead",
        "staff",
        "principal",
        "head of",
        "director",
        "vp ",
        "chief",
        "cto",
        "cfo",
        "cmo",
        "ceo",
    ),
    "trainee": (
        "senior",
        "lead",
        "staff",
        "principal",
        "head of",
        "director",
        "vp ",
        "chief",
        "cto",
        "cfo",
        "cmo",
        "ceo",
    ),
}


# Strong "this is a trainee role" markers. When the user's query
# contains a professional-role keyword (manager, engineer, etc.) but no
# explicit junior-band signal, treat trainee-marker titles as a
# mismatch — the user typed "marketing manager", not "marketing
# internship", so Praktikum/Werkstudent rows are wrong by default.
_TRAINEE_MARKERS: tuple[str, ...] = (
    "praktikant",
    "praktikum",
    "werkstudent",
    "azubi",
    "auszubildende",
    "auszubildender",
    "trainee",
    "internship",
)
_PROFESSIONAL_ROLE_TRIGGERS: tuple[str, ...] = (
    "manager",
    "director",
    "specialist",
    "engineer",
    "developer",
    "scientist",
    "analyst",
    "consultant",
    "architect",
    "designer",
    "lead",
    "head",
    "principal",
    "staff",
)
_JUNIOR_BAND_OPT_INS: tuple[str, ...] = (
    "intern",
    "internship",
    "trainee",
    "praktikant",
    "praktikum",
    "werkstudent",
    "azubi",
    "auszubild",
    "apprentice",
    "graduate",
    "junior",
    "entry-level",
    "entry level",
)


def seniority_conflicts(query: str | None, job_title: str | None) -> bool:
    """True iff the user's query explicitly asks for one seniority band
    and the job title clearly belongs to a conflicting one.

    Examples:
    - query='senior backend engineer', title='Junior Backend Engineer' → True
    - query='senior backend',          title='Senior Backend Engineer' → False
    - query='marketing manager',       title='Praktikant Marketing'    → True (professional-role implies mid+)
    - query='marketing internship',    title='Praktikant Marketing'    → False (user opted into junior band)
    - query='internship marketing',    title='Head of Marketing'       → True
    """

    if not query or not job_title:
        return False
    q = _fold_diacritics(query.casefold())
    t = _fold_diacritics(job_title.casefold())
    for trigger, conflicts in _SENIORITY_CONFLICTS.items():
        if trigger in q:
            for bad in conflicts:
                if bad in t:
                    return True
    # Implicit mid+ band: query contains a professional-role keyword
    # AND no junior-band opt-in → reject trainee markers in title.
    if any(trigger in q for trigger in _PROFESSIONAL_ROLE_TRIGGERS):
        if not any(opt_in in q for opt_in in _JUNIOR_BAND_OPT_INS):
            for marker in _TRAINEE_MARKERS:
                if marker in t:
                    return True
    return False


# ---------- role-family discriminator ------------------------------------

# Words too generic to be discriminators. A 'marketing manager' search
# must not pass jobs titled merely 'HR Manager' or 'Property Manager'
# just because they share the word 'manager'. The same trap caught a
# 'data scientist' search returning 'Freelance Writer' because both
# titles satisfied OR-token matching on common stop-y role words.
_GENERIC_ROLE_WORDS: frozenset[str] = frozenset(
    {
        "manager",
        "specialist",
        "engineer",
        "developer",
        "lead",
        "analyst",
        "coordinator",
        "consultant",
        "assistant",
        "associate",
        "officer",
        "executive",
        "professional",
        "expert",
        "scientist",
        "leader",
        "head",
        "director",
        "vp",
        "supervisor",
        "owner",
        "operator",
        "representative",
        "agent",
    }
)
_QUERY_STOPWORDS: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "of",
        "for",
        "in",
        "at",
        "to",
        "and",
        "or",
        "with",
        "without",
        "on",
        "by",
        "as",
    }
)
_SENIORITY_WORDS: frozenset[str] = frozenset(
    {
        "senior",
        "sr",
        "junior",
        "jr",
        "lead",
        "staff",
        "principal",
        "head",
        "mid",
        "mid-level",
        "intermediate",
        "entry",
        "entry-level",
        "intern",
        "internship",
        "trainee",
        "praktikant",
        "werkstudent",
        "apprentice",
        "azubi",
        "graduate",
    }
)


def query_distinctive_tokens(query: str | None) -> list[str]:
    """Return the distinctive (non-generic, non-stopword, non-seniority)
    tokens from a query. Used to require at least one of these in the
    job's title — catches the OR-token leak (e.g. 'marketing manager'
    passing 'HR Manager' because both share 'manager').

    Empty when every token is generic — caller should fall back to
    OR-match in that case (don't over-filter when the user typed a
    purely-generic query)."""

    if not query:
        return []
    folded = _fold_diacritics(query.casefold())
    tokens = re.findall(r"\w+", folded)
    return [
        tok
        for tok in tokens
        if tok
        and len(tok) > 2
        and tok not in _GENERIC_ROLE_WORDS
        and tok not in _QUERY_STOPWORDS
        and tok not in _SENIORITY_WORDS
    ]


def title_matches_query_family(query: str | None, job_title: str | None) -> bool:
    """True when the job title contains at least one distinctive token
    from the user's query. Falls back to True if the query has no
    distinctive tokens (purely-generic query — let OR-match decide).

    This is the post-filter for the role-family leak documented in
    ``_matches()``. Apply AFTER ``_matches()`` (which is too lenient by
    design for description-only matches) but BEFORE other quality
    checks."""

    if not job_title:
        return True  # don't reject blank titles — let the rest of the row decide
    distinctive = query_distinctive_tokens(query)
    if not distinctive:
        return True  # purely-generic query; OR-match already decided
    t = _fold_diacritics(job_title.casefold())
    return any(tok in t for tok in distinctive)


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
    ) -> list[AggregatedJob]: ...


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
                "DELETE FROM aggregator_cache WHERE expires_at < ?",
                (now,),
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
    haystack = " ".join(
        part.casefold()
        for part in (
            job.title,
            job.company_name,
            job.description or "",
            job.location or "",
        )
        if part
    )
    if keyword_tokens:
        hits = sum(1 for tok in keyword_tokens if tok and tok.casefold() in haystack)
        score += min(0.50, 0.10 * hits)
    if location:
        # Use the same locale-tolerant matcher the providers use, so a
        # search for 'Munich' boosts a 'München, Deutschland' job
        # equivalently. 'remote' as a fallback keeps remote-friendly
        # roles competitive when the provider passed them through.
        job_loc = (job.location or "").casefold()
        if location_matches(location, job.location) or "remote" in job_loc:
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
    scored = [
        (
            job,
            score_job(
                job, keyword_tokens=tokens, location=location, now=now, dismissed_terms=dismissed
            ),
        )
        for job in jobs
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[: max(1, cap)]


class JobAggregationEngine:
    """Fan-out + cache for many ``JobAggregatorProvider`` instances.

    Phase 2 #71: optional ``index`` parameter wires a persistent
    :class:`JobIndex` for write-through at search-fan-out time.
    Cache (existing) is per-(provider, query) for 1h to dedupe
    provider-quota burn; index (new) is per-source_url for 14d to
    power DiagnosticEngine facet analytics. Both can coexist.
    """

    def __init__(
        self,
        providers: Iterable[JobAggregatorProvider] | None = None,
        cache: AggregatorResultCache | None = None,
        index: object | None = None,
    ) -> None:
        self.providers: list[JobAggregatorProvider] = list(providers or [])
        self.cache = cache
        # Typed as ``object`` here to avoid a circular import with
        # company_discovery.job_index (which imports AggregatedJob
        # from this module). The runtime contract is "any object with
        # upsert_jobs(jobs, role_bucket=...) → int". JobIndex
        # satisfies it; mocks for tests can too.
        self.index = index

    def search(
        self,
        *,
        query: str,
        location: str | None,
        limit_per_provider: int = 25,
        persona_id: str | None = None,
        role_bucket: str | None = None,
    ) -> tuple[list[AggregatedJob], list[AggregationOutcome]]:
        """Synchronous façade — drains :meth:`search_streaming` and
        returns the merged (jobs, outcomes) tuple. Existing callers
        keep their existing semantics + get the parallel-fan-out
        speedup automatically.

        Callers that want per-provider progress events as they arrive
        (SSE streaming endpoint, Phase 2 #77) should call
        :meth:`search_streaming` directly and consume the event
        sequence.

        ``role_bucket`` (Phase 2 #71): when set + the engine has an
        ``index`` configured, the dedup'd job list is written through
        to the persistent job-index with this bucket tag. Optional —
        omitting it skips the write-through.
        """
        final_jobs: list[AggregatedJob] = []
        final_outcomes: list[AggregationOutcome] = []
        for event in self.search_streaming(
            query=query,
            location=location,
            limit_per_provider=limit_per_provider,
            persona_id=persona_id,
            role_bucket=role_bucket,
        ):
            if event[0] == "done":
                final_jobs = event[1]["jobs"]
                final_outcomes = event[1]["outcomes"]
        return final_jobs, final_outcomes

    def search_streaming(
        self,
        *,
        query: str,
        location: str | None,
        limit_per_provider: int = 25,
        persona_id: str | None = None,
        max_workers: int | None = None,
        role_bucket: str | None = None,
    ) -> Iterator[tuple[str, dict]]:
        """Yield events as providers complete + a final ``done`` event
        carrying the merged dedup'd jobs + outcomes.

        Event sequence:

        - ``("started", {"providers": [...], "skipped": [...]})`` —
          fired once at the start. ``providers`` is the list of
          provider names that will be queried; ``skipped`` is the
          list of skipped (provider, reason) pairs (e.g. remote-only
          feed skipped on a city-search).
        - ``("provider_ok", {"provider": name, "job_count": N,
          "cached": bool})`` — fired as each provider's search
          completes successfully.
        - ``("provider_error", {"provider": name, "error": "..."})``
          — fired when a provider's search raises.
        - ``("done", {"jobs": [...], "outcomes": [...]})`` — fired
          last with the merged + dedup'd result. ``outcomes`` carries
          the per-provider :class:`AggregationOutcome` list in input
          (non-skipped) order, followed by the skipped outcomes.

        Concurrency: uses a :class:`ThreadPoolExecutor` to fan out
        the per-provider ``provider.search(...)`` calls. Providers are
        expected to be thread-safe (stateless after __init__ + stateless
        HTTP fetches; the project's :class:`AggregatorResultCache` is
        RLock-protected). ``max_workers`` defaults to one worker per
        provider, capped at 16.
        """
        query_hash = canonical_query(query, location)
        accepts_remote = _user_wants_remote(location)

        # First pass: split providers into "to query" vs "skip" buckets,
        # emit the started event so downstream consumers know what to
        # expect.
        to_query: list[JobAggregatorProvider] = []
        skipped_outcomes: list[AggregationOutcome] = []
        skipped_pairs: list[tuple[str, str]] = []
        for provider in self.providers:
            if not accepts_remote and getattr(provider, "remote_only", False):
                # Skip remote-only feeds (Remotive / WeWorkRemotely)
                # when the user's saved search names a specific city/
                # region. A "Berlin" search should not return remote-
                # anywhere jobs — those bleed into the queue and break
                # reply-rate + skill-gap analytics. The user opts into
                # remote feeds by leaving location empty or putting
                # "remote" in it.
                skipped_outcomes.append(
                    AggregationOutcome(
                        provider=provider.name,
                        job_count=0,
                        cached=False,
                        error="skipped_remote_only_for_location_search",
                    )
                )
                skipped_pairs.append((provider.name, "skipped_remote_only_for_location_search"))
            else:
                to_query.append(provider)

        yield (
            "started",
            {
                "providers": [p.name for p in to_query],
                "skipped": [{"provider": n, "reason": r} for (n, r) in skipped_pairs],
            },
        )

        # Inline the cache-hit + provider.search() unit so the
        # ThreadPoolExecutor can fan out cleanly. Each task returns
        # (provider_name, AggregationOutcome, [AggregatedJob...]).
        def _one_provider(
            provider: JobAggregatorProvider,
        ) -> tuple[str, AggregationOutcome, list[AggregatedJob]]:
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
                    jobs = list(
                        provider.search(
                            query=query,
                            location=location,
                            limit=limit_per_provider,
                            persona_id=persona_id,
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - best-effort; failure must not break the caller
                    error = f"{type(exc).__name__}: {exc}"[:200]
                    jobs = []
                if self.cache is not None and jobs:
                    self.cache.put(provider.name, query_hash, jobs)
            outcome = AggregationOutcome(
                provider=provider.name,
                job_count=len(jobs),
                cached=cached,
                error=error,
            )
            return (provider.name, outcome, jobs)

        # Streaming fan-out. Results arrive in completion-time order
        # (fastest provider first), which is what the SSE consumer
        # wants. We accumulate jobs + outcomes for the final ``done``
        # event in the same map.
        accumulated_jobs: list[AggregatedJob] = []
        provider_outcomes: dict[str, AggregationOutcome] = {}
        if to_query:
            worker_count = max_workers if max_workers is not None else min(len(to_query), 16)
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                future_to_provider = {
                    executor.submit(_one_provider, provider): provider.name for provider in to_query
                }
                for future in as_completed(future_to_provider):
                    name = future_to_provider[future]
                    try:
                        _, outcome, jobs = future.result()
                    except BaseException as exc:  # noqa: BLE001 - executor errors shouldn't tear down the stream
                        outcome = AggregationOutcome(
                            provider=name,
                            job_count=0,
                            cached=False,
                            error=f"{type(exc).__name__}: {exc}"[:200],
                        )
                        jobs = []
                    provider_outcomes[name] = outcome
                    accumulated_jobs.extend(jobs)
                    if outcome.error and outcome.error != "skipped_remote_only_for_location_search":
                        yield (
                            "provider_error",
                            {"provider": name, "error": outcome.error},
                        )
                    else:
                        yield (
                            "provider_ok",
                            {
                                "provider": name,
                                "job_count": outcome.job_count,
                                "cached": outcome.cached,
                            },
                        )

        # Cross-provider host-priority dedup: collapse identical
        # canonical source URLs, prefer the provider with the longest
        # description. Canonicalization strips: scheme, www. prefix,
        # query/fragment, and trailing slash — so a job at
        #   https://acme.example/jobs/42
        #   https://www.acme.example/jobs/42/
        #   https://acme.example/jobs/42?utm_source=indeed
        # all dedupe to the same canonical key.
        seen: dict[str, AggregatedJob] = {}
        host_pattern = re.compile(r"^https?://([^/]+)/(.+?)(?:\?|#|$)")
        nourl_counter = 0
        for job in accumulated_jobs:
            url = getattr(job, "source_url", None)
            if not isinstance(url, str):
                # A misbehaving provider returned a non-AggregatedJob or a
                # None/non-string source_url. The isolation boundary must extend
                # past provider.search() into the merge — skip it, never crash
                # the whole fan-out (the module's core contract).
                continue
            match = host_pattern.match(url)
            if match:
                host = match.group(1).lower().removeprefix("www.")
                path = match.group(2).lower().rstrip("/")
                host_path = f"{host}/{path}"
            elif url:
                host_path = url
            else:
                # Empty URL: give each URL-less job a unique key so distinct
                # postings don't all collapse into one under the "" key.
                host_path = f"\x00nourl-{nourl_counter}"
                nourl_counter += 1
            existing = seen.get(host_path)
            if existing is None or len(job.description or "") > len(existing.description or ""):
                seen[host_path] = job

        # Final outcomes list: preserve the legacy ordering shape
        # callers depend on (queried providers in input order, then
        # skipped ones at the tail).
        ordered_outcomes: list[AggregationOutcome] = [
            provider_outcomes[provider.name]
            for provider in to_query
            if provider.name in provider_outcomes
        ]
        ordered_outcomes.extend(skipped_outcomes)
        dedup_jobs = list(seen.values())

        # Phase 2 #71 write-through: persist the dedup'd jobs to the
        # job-index when one is configured. Tagged with role_bucket
        # when the caller supplied one (e.g. from
        # ``identify_bucket(query)`` in chat_handler_find_jobs).
        # Best-effort: failures here must not abort the streaming
        # response. Seniority + language facets land in Phase B.
        index = getattr(self, "index", None)
        if index is not None and dedup_jobs:
            try:
                index.upsert_jobs(dedup_jobs, role_bucket=role_bucket)
            except Exception:  # noqa: BLE001 - write-through is best-effort; never break the search
                pass

        yield (
            "done",
            {"jobs": dedup_jobs, "outcomes": ordered_outcomes},
        )

    def attributions(self) -> list[ProviderAttribution]:
        out: list[ProviderAttribution] = []
        for p in self.providers:
            attribution = getattr(p, "attribution", None)
            if isinstance(attribution, ProviderAttribution):
                out.append(attribution)
        return out
