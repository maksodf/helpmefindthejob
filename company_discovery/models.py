# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Company:
    user_id: str
    name: str
    website_url: str
    career_page_url: str | None = None
    sector: str | None = None
    relevance_score: float | None = None
    relevance_reason: str | None = None
    watch_enabled: bool = False
    notes: str | None = None
    id: str = field(default_factory=lambda: new_id("company"))
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)


@dataclass
class CompanyDiscoveryRun:
    user_id: str
    source_type: str
    company_id: str | None = None
    query: str | None = None
    status: str = "pending"
    pages_checked: int = 0
    jobs_found: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("run"))
    started_at: datetime = field(default_factory=now_utc)
    finished_at: datetime | None = None
    created_at: datetime = field(default_factory=now_utc)


@dataclass
class CareerPageScan:
    user_id: str
    company_id: str
    career_page_url: str
    status: str
    checked_robots: bool
    robots_allowed: bool
    pages_checked: int = 0
    jobs_found: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("scan"))
    last_checked_at: datetime = field(default_factory=now_utc)
    created_at: datetime = field(default_factory=now_utc)


@dataclass
class DiscoveredJob:
    user_id: str
    source_url: str
    title: str
    company_id: str | None = None
    location: str | None = None
    raw_snippet: str | None = None
    raw_description: str | None = None
    structured_data: dict[str, Any] | None = None
    confidence_score: float = 0.0
    imported_job_id: str | None = None
    auto_fit_score: float | None = None
    auto_fit_reason: str | None = None
    auto_fit_at: datetime | None = None
    auto_fit_provider_id: str | None = None
    # Cross-source merge: each entry is keyed by source host (e.g. "indeed.com")
    # and carries the most recent URL + timestamp + provider label seen for that
    # source. Replaces the old "drop the duplicate" behaviour with "this job was
    # also seen at these other places."
    also_seen_at: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Skill-gap atlas: 1-3 skills the auto-fit LLM extracted from the JD that
    # are missing from the candidate's CV. Populated by the auto-fit prompt
    # extension; empty when auto-fit hasn't been run or didn't return a GAPS
    # line. Copied through to ImportedJob.gaps on import.
    gaps: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("discovered_job"))
    discovered_at: datetime = field(default_factory=now_utc)
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)


APPLICATION_STATUSES = (
    "saved",
    "interested",
    "applied",
    "interview",
    "rejected",
    "archived",
)


INTERVIEW_STAGES = (
    "screening",
    "phone",
    "take_home",
    "technical",
    "onsite",
    "panel",
    "offer",
)


@dataclass
class ImportedJob:
    user_id: str
    company_id: str
    discovered_job_id: str
    source_url: str
    title: str
    company_name: str
    location: str | None = None
    description: str | None = None
    source_type: str = "direct_company"
    analysis_status: str = "pending"
    analysis_output: str | None = None
    analysis_error: str | None = None
    analysis_provider_id: str | None = None
    analyzed_at: datetime | None = None
    structured_analysis: dict[str, Any] | None = None
    fit_score: float | None = None
    recommendation: str | None = None
    application_status: str = "saved"
    application_notes: str | None = None
    cover_letter_draft: str | None = None
    documents_checklist: list[dict[str, Any]] = field(default_factory=list)
    next_action: str | None = None
    interview_stage: str | None = None
    reminder_at: datetime | None = None
    # Reply-rate analytics: set to ``now()`` the first time the user
    # confirms the company replied to their application. Distinct from
    # ``application_status`` transitions (which can happen on
    # auto-rejection emails); ``replied_at`` is the user-confirmed
    # signal that someone actually wrote back.
    replied_at: datetime | None = None
    # Public share toggle: when True the job is reachable at
    # ``/share/job/<id>`` for SEO + sign-up funnel. Owner can
    # toggle off any time; toggling off makes the share URL
    # immediately return 404. Default is False so nothing is
    # accidentally public.
    share_enabled: bool = False
    # Skill-gap atlas: copied from the discovered job on import. The
    # aggregator on the dashboard surfaces the most common gaps across
    # the imported queue so the user can prioritise what to learn.
    gaps: list[str] = field(default_factory=list)
    # CV-variant attribution (#44). Each entry is one tailor-cv run
    # result: ``{index, createdAt, excerpt, attributedReply}``. When
    # the user later flags ``replied=True`` on the application, the
    # most recent variant on the job is marked as the one that earned
    # the reply. Empty list when the user never tailored.
    cv_variants: list[dict[str, Any]] = field(default_factory=list)
    application_history: list[dict[str, Any]] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("job"))
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)


@dataclass
class SavedSearch:
    user_id: str
    name: str
    target_roles: list[str] = field(default_factory=list)
    industry: str = "Healthcare"
    location: str | None = None
    sectors: list[str] = field(default_factory=list)
    notes: str | None = None
    last_seen_at: datetime | None = None  # for unseen-matches badge
    id: str = field(default_factory=lambda: new_id("search"))
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)


@dataclass
class AnalyticsEvent:
    user_id: str
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("evt"))
    created_at: datetime = field(default_factory=now_utc)


@dataclass
class SupportTicket:
    user_id: str
    subject: str
    body: str
    contact_email: str
    status: str = "open"
    id: str = field(default_factory=lambda: new_id("ticket"))
    created_at: datetime = field(default_factory=now_utc)


SUPPORTED_LOCALES = ("en", "de")

SUPPORTED_THEMES = ("dark", "light", "system")

WORKSPACE_ROLES = ("owner", "admin", "member")


@dataclass
class PushSubscription:
    """A browser-side Web Push subscription stored server-side.

    The endpoint URL + p256dh + auth keys are everything the server
    needs to encrypt and POST a notification payload to the user's
    push service (Mozilla, Google FCM, Apple).
    """

    user_id: str
    endpoint: str
    p256dh: str
    auth: str
    user_agent: str | None = None
    id: str = field(default_factory=lambda: new_id("push"))
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)


@dataclass
class WorkspaceMembership:
    """Maps a user to a workspace + role.

    Each authenticated user automatically owns one workspace
    (``workspace_id == "ws_<short hash of user_id>"``). When User B
    accepts an invite from User A's workspace, a second membership row
    is added with ``user_id=B, workspace_id=ws(A), role='member'``.

    Read-path data routing is keyed on ``workspace_owner_id`` (the
    user-id of whoever owns the workspace), so existing per-user
    queries keep working unchanged when the user is in their own
    workspace.
    """

    user_id: str
    workspace_id: str
    workspace_owner_id: str
    role: str = "member"
    label: str | None = None
    id: str = field(default_factory=lambda: new_id("wsmember"))
    created_at: datetime = field(default_factory=now_utc)


@dataclass
class UserProfile:
    """Per-user candidate profile used to personalize AI briefs and ranking.

    Stored at most once per user (``user_id`` is the primary key here even
    though we also carry an ``id`` for consistency with the other tables).
    """

    user_id: str
    persona_id: str = "healthcare-management"
    target_roles: list[str] = field(default_factory=list)
    industry: str | None = None
    location: str | None = None
    seniority: str | None = None  # e.g. "junior", "senior", "early-career"
    years_experience: int | None = None
    languages: list[str] = field(default_factory=list)
    cv_text: str | None = None
    # CV photo — stored as a self-contained data URI (e.g.
    # ``data:image/jpeg;base64,...``) so the CV markdown renders
    # offline and exports cleanly. Encrypted at rest via the same
    # AEAD path as cv_text; capped at ~512KB raw (~700KB base64) on
    # upload. PNG/JPEG only — SVG and other formats are rejected
    # because they can carry script.
    cv_photo_data_uri: str | None = None
    # Chat-router session state — persisted across server restarts so an
    # in-flight ``/add-company`` flow survives a deploy. Shape matches
    # ChatSession.to_dict() (history + pending). Capped at ~50 turns by
    # the chat surface; old turns get trimmed before save.
    chat_state: dict | None = None
    notes: str | None = None
    locale: str = "en"
    theme: str = "dark"
    active_workspace_id: str | None = None
    last_push_notified_at: datetime | None = None
    hidden_sources: list[str] = field(default_factory=list)
    # Negative-filter learning: titles + companies the user dismissed as
    # "not relevant". Downweights similar future matches in
    # rank_aggregated and hides direct matches from the queue.
    # Capped at 50 entries (FIFO) so the list never grows unbounded.
    dismissed_terms: list[str] = field(default_factory=list)
    # First-run wizard dismissal — once a user finishes (or X's out of)
    # the wizard, this stays True so we don't pop it back up after they
    # delete their saved searches.
    onboarding_dismissed: bool = False
    # Retention window in days. Discovered jobs not imported within this
    # window are auto-deleted by the daily purge. 0 disables retention.
    retention_days: int = 90
    # Outbound Slack webhook for "high-fit job found" notifications.
    # Empty string = disabled. The threshold is the auto_fit_score
    # below which we don't ping Slack (default 0.70).
    slack_webhook_url: str = ""
    slack_fit_threshold: float = 0.70
    # Track which (user_id, discovered_job_id) we've already notified so
    # the same job doesn't ping Slack twice when re-scored.
    slack_notified_job_ids: list[str] = field(default_factory=list)
    # Explicit consent for sending profile/CV text to a configured LLM.
    # We never send to a third-party model unless this is True. The
    # consent banner persists this on first AI invocation.
    ai_consent_at: datetime | None = None
    ai_consent_provider_id: str | None = None
    # Strict job-type filter — set by the chat router when the user runs
    # /find against a known role bucket. Watchlist auto-discovery scans
    # honour this filter so the queue stays focused. Key is one of the
    # taxonomy buckets in company_discovery.job_type_filter.TAXONOMY
    # (e.g. "bartender", "pflegehelfer"). Empty string = no filter.
    job_type_filter: str = ""
    # Companion location filter for the job-type. Empty / "anywhere" =
    # no location filter. Used by both the chat search and the
    # watchlist scan to keep results in one country / city.
    job_type_location_filter: str = ""
    id: str = field(default_factory=lambda: new_id("profile"))
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)
