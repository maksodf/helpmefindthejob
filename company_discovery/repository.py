# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from .dedup import DuplicateMatch, find_duplicate
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
    now_utc,
)


class InMemoryCompanyDiscoveryRepository:
    """Small repository used by the reference slice and tests.

    Production code should replace this with the app's ORM/repository layer.
    """

    def __init__(self) -> None:
        self.companies: dict[str, Company] = {}
        self.discovery_runs: dict[str, CompanyDiscoveryRun] = {}
        self.scans: dict[str, CareerPageScan] = {}
        self.discovered_jobs: dict[str, DiscoveredJob] = {}
        self.imported_jobs: dict[str, ImportedJob] = {}
        self.saved_searches: dict[str, SavedSearch] = {}
        self.analytics_events: dict[str, AnalyticsEvent] = {}
        self.support_tickets: dict[str, SupportTicket] = {}
        self.user_profiles: dict[str, UserProfile] = {}  # keyed by user_id
        self.workspace_memberships: dict[str, WorkspaceMembership] = {}  # keyed by membership.id
        self.push_subscriptions: dict[str, PushSubscription] = {}  # keyed by subscription.id

    def save_company(self, company: Company) -> Company:
        company.updated_at = now_utc()
        self.companies[company.id] = company
        return company

    def get_company(self, user_id: str, company_id: str) -> Company:
        company = self.companies[company_id]
        if company.user_id != user_id:
            raise KeyError(company_id)
        return company

    def list_companies(self, user_id: str) -> list[Company]:
        return [company for company in self.companies.values() if company.user_id == user_id]

    def delete_company(self, user_id: str, company_id: str) -> None:
        company = self.get_company(user_id, company_id)
        del self.companies[company.id]
        for run_id, run in list(self.discovery_runs.items()):
            if run.user_id == user_id and run.company_id == company.id:
                del self.discovery_runs[run_id]
        for scan_id, scan in list(self.scans.items()):
            if scan.user_id == user_id and scan.company_id == company.id:
                del self.scans[scan_id]
        for job_id, job in list(self.discovered_jobs.items()):
            if job.user_id == user_id and job.company_id == company.id:
                del self.discovered_jobs[job_id]
        for job_id, job in list(self.imported_jobs.items()):
            if job.user_id == user_id and job.company_id == company.id:
                del self.imported_jobs[job_id]

    def save_discovery_run(self, run: CompanyDiscoveryRun) -> CompanyDiscoveryRun:
        self.discovery_runs[run.id] = run
        return run

    def save_scan(self, scan: CareerPageScan) -> CareerPageScan:
        self.scans[scan.id] = scan
        return scan

    def save_discovered_job(self, job: DiscoveredJob) -> DiscoveredJob:
        job.updated_at = now_utc()
        self.discovered_jobs[job.id] = job
        return job

    def purge_discovered_jobs_older_than(
        self, user_id: str, *, cutoff: datetime, keep_imported: bool = True
    ) -> int:
        """Delete this user's discovered jobs whose effective freshness is
        older than ``cutoff``. Returns the count removed. Imported jobs
        are skipped by default (the user's already engaged with them)."""

        from .dedup import effective_freshness_at

        removed = 0
        for job_id, job in list(self.discovered_jobs.items()):
            if job.user_id != user_id:
                continue
            if keep_imported and job.imported_job_id:
                continue
            freshness = effective_freshness_at(job) or job.discovered_at
            if freshness and freshness < cutoff:
                del self.discovered_jobs[job_id]
                removed += 1
        return removed

    def list_discovered_jobs(
        self, user_id: str, company_id: str | None = None
    ) -> list[DiscoveredJob]:
        jobs = [job for job in self.discovered_jobs.values() if job.user_id == user_id]
        if company_id:
            jobs = [job for job in jobs if job.company_id == company_id]
        from .dedup import effective_freshness_at

        return sorted(
            jobs,
            key=lambda job: effective_freshness_at(job) or job.discovered_at,
            reverse=True,
        )

    def list_discovery_runs(self, user_id: str) -> list[CompanyDiscoveryRun]:
        return sorted(
            [run for run in self.discovery_runs.values() if run.user_id == user_id],
            key=lambda run: run.started_at,
            reverse=True,
        )

    def list_scans(self, user_id: str) -> list[CareerPageScan]:
        return sorted(
            [scan for scan in self.scans.values() if scan.user_id == user_id],
            key=lambda scan: scan.last_checked_at,
            reverse=True,
        )

    def list_imported_jobs(self, user_id: str) -> list[ImportedJob]:
        return sorted(
            [job for job in self.imported_jobs.values() if job.user_id == user_id],
            key=lambda job: job.created_at,
            reverse=True,
        )

    def save_imported_job(self, job: ImportedJob) -> ImportedJob:
        job.updated_at = now_utc()
        self.imported_jobs[job.id] = job
        return job

    def save_saved_search(self, search: SavedSearch) -> SavedSearch:
        search.updated_at = now_utc()
        self.saved_searches[search.id] = search
        return search

    def list_saved_searches(self, user_id: str) -> list[SavedSearch]:
        return sorted(
            [s for s in self.saved_searches.values() if s.user_id == user_id],
            key=lambda item: item.created_at,
            reverse=True,
        )

    def delete_saved_search(self, user_id: str, search_id: str) -> None:
        s = self.saved_searches.get(search_id)
        if s is None or s.user_id != user_id:
            raise KeyError(search_id)
        del self.saved_searches[search_id]

    def save_analytics_event(self, event: AnalyticsEvent) -> AnalyticsEvent:
        self.analytics_events[event.id] = event
        return event

    def list_analytics_events(
        self, user_id: str | None = None, limit: int = 200
    ) -> list[AnalyticsEvent]:
        events = list(self.analytics_events.values())
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        events.sort(key=lambda e: e.created_at, reverse=True)
        return events[:limit]

    def save_support_ticket(self, ticket: SupportTicket) -> SupportTicket:
        self.support_tickets[ticket.id] = ticket
        return ticket

    def list_support_tickets(self, user_id: str | None = None) -> list[SupportTicket]:
        tickets = list(self.support_tickets.values())
        if user_id:
            tickets = [t for t in tickets if t.user_id == user_id]
        tickets.sort(key=lambda t: t.created_at, reverse=True)
        return tickets

    def get_user_profile(self, user_id: str) -> UserProfile | None:
        return self.user_profiles.get(user_id)

    def save_user_profile(self, profile: UserProfile) -> UserProfile:
        profile.updated_at = now_utc()
        self.user_profiles[profile.user_id] = profile
        return profile

    def delete_user_profile(self, user_id: str) -> None:
        self.user_profiles.pop(user_id, None)

    def list_push_subscriptions(self, user_id: str) -> list[PushSubscription]:
        return [s for s in self.push_subscriptions.values() if s.user_id == user_id]

    def find_push_subscription(self, endpoint: str) -> PushSubscription | None:
        for sub in self.push_subscriptions.values():
            if sub.endpoint == endpoint:
                return sub
        return None

    def save_push_subscription(self, subscription: PushSubscription) -> PushSubscription:
        subscription.updated_at = now_utc()
        self.push_subscriptions[subscription.id] = subscription
        return subscription

    def delete_push_subscription(self, subscription_id: str) -> None:
        self.push_subscriptions.pop(subscription_id, None)

    def list_workspace_memberships(self, user_id: str) -> list[WorkspaceMembership]:
        return [m for m in self.workspace_memberships.values() if m.user_id == user_id]

    def list_workspace_members(self, workspace_id: str) -> list[WorkspaceMembership]:
        return [m for m in self.workspace_memberships.values() if m.workspace_id == workspace_id]

    def find_workspace_membership(
        self, user_id: str, workspace_id: str
    ) -> WorkspaceMembership | None:
        for m in self.workspace_memberships.values():
            if m.user_id == user_id and m.workspace_id == workspace_id:
                return m
        return None

    def save_workspace_membership(self, membership: WorkspaceMembership) -> WorkspaceMembership:
        self.workspace_memberships[membership.id] = membership
        return membership

    def delete_workspace_membership(self, membership_id: str) -> None:
        self.workspace_memberships.pop(membership_id, None)

    def find_duplicate_discovered_job(self, candidate: DiscoveredJob) -> DiscoveredJob | None:
        match = self.find_duplicate_match(candidate)
        if match is None:
            return None
        return self.discovered_jobs.get(match.duplicate_id)

    def find_duplicate_match(self, candidate: DiscoveredJob) -> DuplicateMatch | None:
        existing = [
            job
            for job in self.discovered_jobs.values()
            if job.user_id == candidate.user_id and job.id != candidate.id
        ]
        return find_duplicate(candidate, existing)

    def find_duplicate_discovered_job_pair(
        self, existing: DiscoveredJob, candidate: DiscoveredJob
    ) -> bool:
        return find_duplicate(candidate, [existing]) is not None

    def watchlist_summary(self, user_id: str) -> dict[str, object]:
        companies = self.list_companies(user_id)
        watched = [company for company in companies if company.watch_enabled]
        discovered_jobs = self.list_discovered_jobs(user_id)
        setup_needed = [
            company
            for company in companies
            if company.watch_enabled and not company.career_page_url
        ]
        last_scan = max(
            (scan for scan in self.scans.values() if scan.user_id == user_id),
            key=lambda scan: scan.last_checked_at,
            default=None,
        )
        return {
            "companiesWatched": len(watched),
            "newDirectCompanyJobs": len(
                [job for job in discovered_jobs if not job.imported_job_id]
            ),
            "companiesNeedingCareerPageSetup": len(setup_needed),
            "bestDirectCompanyMatches": [
                asdict(job)
                for job in sorted(
                    discovered_jobs, key=lambda item: item.confidence_score, reverse=True
                )[:5]
            ],
            "lastDiscoveryRunStatus": last_scan.status if last_scan else None,
        }
