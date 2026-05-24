# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
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


# Phase 2 #11 (2026-05-22): full referral lifecycle persistence.
# The MCP `propose_referral` tool previously returned a stub
# object with no persistence — the calling agent had to track
# state itself. This dataclass + repo wiring give the user a
# durable view of referrals issued FOR them so they can come
# back later, see outstanding items, mark which ones they acted
# on, and provide outcome data for the cost-saving doctrine.
#
# Status state machine:
#   proposed → accepted   (user said yes; handoff is now active)
#   proposed → declined   (user said no; record + drop)
#   accepted → followed_up (user actually visited the target agent)
#   * → expired           (no action within retention window; lifecycle close)
REFERRAL_STATUSES = (
    "proposed",
    "accepted",
    "declined",
    "followed_up",
    "expired",
)


@dataclass
class Referral:
    """One civic-agent referral, persisted per-user.

    Mirrors the in-tool shape from `propose_referral` (HL7 FHIR
    ServiceRequest subset) but adds the lifecycle status field so
    the user can see + update each referral over time. The
    ``supporting_info`` blob is opaque — the issuing agent puts
    whatever JSON-serialisable structured context it wants there
    (e.g., the originating user message that triggered the
    referral).
    """

    user_id: str
    target_agent: str
    reason_code: str
    source_agent: str = "helpmefindthejob"
    intent: str = "proposed"  # FHIR ServiceRequest.intent
    priority: str = "routine"  # FHIR ServiceRequest.priority
    supporting_info: dict[str, Any] = field(default_factory=dict)
    status: str = "proposed"  # one of REFERRAL_STATUSES
    user_consent_required: bool = True
    outcome_note: str = ""  # user-supplied free text on followup/decline
    id: str = field(default_factory=lambda: new_id("ref"))
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)


# Phase 2 #56 (2026-05-21): default fallback set of locales the
# app guarantees support for. Real runtime support is broader —
# :func:`available_locales` discovers any ``<code>.json`` bundle
# under ``static/i18n/`` so dropping in ``ar.json`` activates
# Arabic without a code change. This tuple is the FALLBACK for
# environments where the i18n directory isn't readable (build-time
# imports, tests with no static tree, etc.).
SUPPORTED_LOCALES = ("en", "de")


def available_locales(
    i18n_dir: Path | None = None,
) -> tuple[str, ...]:
    """Return the locale codes the runtime actually has bundles
    for. Reads ``static/i18n/<code>.json`` filenames; falls back
    to :data:`SUPPORTED_LOCALES` when the directory isn't
    accessible.

    Locale codes are validated to match a strict ISO 639-1
    pattern (2-3 lowercase letters, optional ``_REGION`` or
    ``-REGION``) before being trusted — defends against a
    malicious bundle filename being treated as a locale.

    Cached per-process per-directory: i18n bundles don't change
    at runtime, so re-scanning the directory on every locale
    validation is wasteful. Tests that need to exercise
    different bundle sets pass an explicit ``i18n_dir`` (each
    distinct path is cached separately).
    """

    from pathlib import Path

    if i18n_dir is None:
        # Default: <repo_root>/static/i18n. The repo_root is the
        # parent of this module's parent.
        i18n_dir = Path(__file__).resolve().parent.parent / "static" / "i18n"
    # Stringify for cache-key stability (Path objects with the
    # same target compare equal but lru_cache hashes by identity
    # for some Path implementations, so we normalise).
    return _discover_locales_cached(str(i18n_dir.resolve()))


def _discover_locales_cached(i18n_dir_str: str) -> tuple[str, ...]:
    """Module-level functools.lru_cache wrapper. Separate from
    :func:`_discover_locales` so tests can call the inner function
    directly without hitting the cache."""

    from functools import lru_cache
    from pathlib import Path

    # First call sets up the cache. Subsequent calls hit it.
    global _DISCOVER_LOCALES_LRU
    if "_DISCOVER_LOCALES_LRU" not in globals() or _DISCOVER_LOCALES_LRU is None:

        @lru_cache(maxsize=32)
        def _cached(path_str: str) -> tuple[str, ...]:
            return _discover_locales(Path(path_str))

        _DISCOVER_LOCALES_LRU = _cached
    return _DISCOVER_LOCALES_LRU(i18n_dir_str)


# Lazily-initialised cache wrapper. See _discover_locales_cached.
_DISCOVER_LOCALES_LRU = None


def _discover_locales(i18n_dir: Path) -> tuple[str, ...]:
    """Internal: scan i18n_dir for ``<code>.json`` files,
    validate the code shape, return sorted tuple. Falls back to
    SUPPORTED_LOCALES on any I/O error.

    Tests should call this directly to bypass the per-process
    cache (each test wants a fresh scan of its TemporaryDirectory).
    Production code goes through :func:`available_locales` which
    wraps this with the lru_cache.
    """

    import re

    valid_pattern = re.compile(r"^[a-z]{2,3}(?:[_-][a-z]{2,4})?$", re.IGNORECASE)
    try:
        codes: set[str] = set()
        for path in i18n_dir.iterdir():
            if path.suffix.lower() != ".json":
                continue
            stem = path.stem
            if not valid_pattern.match(stem):
                continue
            codes.add(stem.lower())
        if not codes:
            return SUPPORTED_LOCALES
        return tuple(sorted(codes))
    except OSError:
        return SUPPORTED_LOCALES


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
    # Bug F Option B (Loop 10.2, 2026-05-20): friction-class
    # classification derived by friction_classifier.classify() from
    # the user's pasted CV. One of the seven fixture slugs (aicha /
    # yusuf / olga / mahmoud / maria / kaethe / tobias) or "" when
    # the classifier couldn't resolve confidently. Drives Bug C
    # piece-3 + piece-4 persona-aware widening order +
    # Ausländerbehörde caveat AND analysis.py's AI-prompt friction
    # context (residency_status, friction_notes, scenarios). Default
    # "" preserves backward compatibility with existing UserProfile
    # entries serialized before this field existed. The fixture
    # slugs are intentionally a different namespace from the
    # ``persona_id`` registry (15 industry IDs) -- two fields, two
    # concerns: persona_id drives industry-segment ranking +
    # templates; friction_class drives friction-class-aware UX.
    friction_class: str = ""
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
    # Phase 2 #32 (2026-05-21): GDPR Article 7 demonstrable-consent
    # timestamp for the cv_photo. Set when the user uploads a photo;
    # cleared on removal. Article 7 requires the controller to be
    # able to demonstrate WHEN consent was given, not just that it
    # was given — this timestamp is that demonstration.
    cv_photo_consent_at: datetime | None = None
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
    # Phase 2 #46 (2026-05-21): per-user BYO-AI monthly spend cap in
    # EUR. When the user runs in API mode (their own OpenAI / Gemini
    # / Anthropic / DeepSeek key), every invocation is cost-estimated
    # and the cap-enforcer at company_discovery.cost_caps refuses any
    # call that would push the calendar-month total over this cap.
    # Local providers (ollama / manual / claude_code) never trigger
    # the cap regardless of value. Default 5.0 EUR — modest enough
    # that normal workflows don't hit it but a runaway loop is
    # caught before €100 is gone.
    monthly_spend_cap_eur: float = 5.0
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
