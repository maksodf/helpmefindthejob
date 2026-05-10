"""Saved-search → discovered-job matcher.

The matcher runs purely in Python over already-fetched lists; it never
re-fetches anything. The product policy is: a saved search shows the
user "new matches since I last looked", where "matches" means a job
whose title/description/location aligns with the search's target roles,
sectors, and location, and "since I last looked" is keyed on
``saved_search.last_seen_at``.

Computing on-read avoids the trap of denormalising matches onto the
DiscoveredJob row — a brand-new saved search retroactively picks up
old jobs without backfill.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, Mapping

from .models import Company, DiscoveredJob, SavedSearch


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokens(value: str | None) -> set[str]:
    return {match.group(0).casefold() for match in _TOKEN_RE.finditer(value or "")}


def _haystack_for_job(job: DiscoveredJob) -> str:
    return " ".join(
        part for part in (job.title, job.location or "", job.raw_description or "") if part
    )


def saved_search_matches_job(
    search: SavedSearch,
    job: DiscoveredJob,
    company_sector: str | None = None,
) -> bool:
    """Return True if ``job`` matches the criteria of ``search``."""

    haystack_tokens = _tokens(_haystack_for_job(job))
    role_tokens: set[str] = set()
    for role in search.target_roles or []:
        role_tokens |= _tokens(role)
    if role_tokens and not (role_tokens & haystack_tokens):
        return False
    if search.location:
        location = (job.location or "").casefold()
        if search.location.casefold() not in location:
            return False
    if search.sectors and company_sector:
        sector_lc = company_sector.casefold()
        if not any(sector.casefold() in sector_lc for sector in search.sectors if sector):
            return False
    return True


def matches_for_search(
    search: SavedSearch,
    jobs: Iterable[DiscoveredJob],
    companies_by_id: Mapping[str, Company],
) -> list[DiscoveredJob]:
    """Return all discovered jobs that match this saved search."""

    matched: list[DiscoveredJob] = []
    for job in jobs:
        company = companies_by_id.get(job.company_id)
        sector = company.sector if company else None
        if saved_search_matches_job(search, job, sector):
            matched.append(job)
    return matched


def unseen_matches_for_search(
    search: SavedSearch,
    jobs: Iterable[DiscoveredJob],
    companies_by_id: Mapping[str, Company],
) -> list[DiscoveredJob]:
    """Subset of matches with any signal after ``search.last_seen_at``.

    "Signal" includes the original ``discovered_at`` *or* any
    ``also_seen_at`` re-sighting timestamp — so a job that was first
    found weeks ago but just re-found via a new aggregator counts as
    unseen until the operator reviews it."""

    from .dedup import effective_freshness_at

    threshold: datetime | None = search.last_seen_at
    matched = matches_for_search(search, jobs, companies_by_id)
    if threshold is None:
        return matched
    return [
        job
        for job in matched
        if (effective_freshness_at(job) or job.discovered_at) > threshold
    ]


def alert_summary_for_search(
    search: SavedSearch,
    jobs: Iterable[DiscoveredJob],
    companies_by_id: Mapping[str, Company],
) -> dict[str, object]:
    """Return a UI-friendly summary block for this saved search."""

    from .dedup import effective_freshness_at

    job_list = list(jobs)
    matches = matches_for_search(search, job_list, companies_by_id)
    unseen = unseen_matches_for_search(search, job_list, companies_by_id)
    latest = max(
        (effective_freshness_at(job) or job.discovered_at for job in matches),
        default=None,
    )
    return {
        "matchCount": len(matches),
        "unseenCount": len(unseen),
        "latestMatchAt": latest.isoformat() if latest else None,
    }
