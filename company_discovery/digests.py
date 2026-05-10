"""Plain-text digest builder shared by manual + email-driven digests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from .dedup import effective_freshness_at
from .models import Company, DiscoveredJob


def build_digest(
    *,
    user_email: str,
    companies: Iterable[Company],
    discovered_jobs: Iterable[DiscoveredJob],
    since: datetime | None = None,
    cap: int = 10,
) -> str:
    since = since or (datetime.now(timezone.utc) - timedelta(days=7))
    company_index = {company.id: company for company in companies}
    new_jobs = [
        job
        for job in discovered_jobs
        if (effective_freshness_at(job) or job.discovered_at) >= since
        and not job.imported_job_id
    ]
    new_jobs.sort(
        key=lambda job: effective_freshness_at(job) or job.discovered_at,
        reverse=True,
    )

    if not new_jobs:
        return (
            f"Hi {user_email.split('@', 1)[0] or 'there'},\n\n"
            f"No new direct-company roles in your watchlist since {since.date()}. "
            "Add more companies or run a manual scan from the Companies view.\n"
        )

    lines = [
        f"Hi {user_email.split('@', 1)[0] or 'there'},",
        "",
        f"Here are the latest {min(cap, len(new_jobs))} direct-company roles since {since.date()}:",
        "",
    ]
    for job in new_jobs[:cap]:
        company_name = company_index.get(job.company_id).name if company_index.get(job.company_id) else "Unknown company"
        lines.append(f"- {job.title} — {company_name}{(' · ' + job.location) if job.location else ''}")
        if job.source_url:
            lines.append(f"  {job.source_url}")
    lines += ["", "Open DirectJob Scout to review and import."]
    return "\n".join(lines) + "\n"
