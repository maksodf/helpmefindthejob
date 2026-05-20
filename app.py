# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import secrets
import time
from dataclasses import asdict, fields, is_dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread
from typing import Any, ClassVar
from urllib.parse import unquote, urlparse

from company_discovery.aggregator_providers import default_no_auth_providers
from company_discovery.aggregators import (
    AggregatorResultCache,
    JobAggregationEngine,
    rank_aggregated,
)
from company_discovery.ai_providers import (
    AIProviderConfig,
    provider_options_payload,
    validate_provider_config,
)
from company_discovery.analysis import (
    build_cover_letter_brief_prompt,
    build_job_decision_brief_prompt,
    execute_auto_fit,
    execute_cover_letter_brief,
    execute_cv_tailoring,
    execute_job_decision_brief,
    parse_auto_fit_output,
)
from company_discovery.auth import AuthSession, AuthStore, AuthUser
from company_discovery.billing import (
    Plan,
    StripeBillingBackend,
    Subscription,
    apply_stripe_event,
    find_plan,
    plans_payload,
    verify_stripe_webhook_signature,
)
from company_discovery.billing import (
    build_backend as build_billing_backend,
)
from company_discovery.chat_router import (
    REGISTRY as CHAT_REGISTRY,
)
from company_discovery.chat_router import (
    ChatSession,
    ChatTurn,
    PendingCommand,
    build_ai_router_prompt,
    extract_keyword_args,
    fill_param_from_message,
    is_confirmation_no,
    is_confirmation_yes,
    keyword_route,
    next_missing_param,
    parse_ai_router_extracted_args,
    parse_ai_router_response,
    parse_slash_command,
    parse_slash_inline_args,
    render_help_text,
)
from company_discovery.chat_router import (
    list_commands as list_chat_commands,
)
from company_discovery.cv_builder import (
    SECTIONS,
    CvBuilderState,
    assemble_cv_markdown,
    build_format_prompt,
    get_section,
    next_section_id,
    render_cv_print_html,
    validate_ai_format_output,
)
from company_discovery.cv_extract import CvExtractError
from company_discovery.cv_extract import extract_text as extract_cv_text
from company_discovery.digests import build_digest
from company_discovery.discovery_providers import (
    BraveSearchProvider,
    CuratedSearchProvider,
    DiscoveryEngine,
    DuckDuckGoSearchProvider,
)
from company_discovery.email_transport import (
    Email,
    EmailTransport,
    build_transport,
    email_from_address,
)
from company_discovery.env_compat import get_env, get_env_bool
from company_discovery.exports import (
    discovered_jobs_to_csv,
    discovered_jobs_to_markdown,
    imported_jobs_to_csv,
    imported_jobs_to_markdown,
)
from company_discovery.http_fetcher import HTTPFetcher
from company_discovery.models import (
    APPLICATION_STATUSES,
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
    new_id,
    now_utc,
)
from company_discovery.onboarding import build_checklist, checklist_progress
from company_discovery.persona_ranking import rank_candidates
from company_discovery.personas import (
    DEFAULT_PERSONA_ID,
    PERSONAS,
    get_persona,
    list_personas_summary,
)
from company_discovery.push_transport import (
    PushPayload,
    PushUnavailableError,
    is_push_configured,
    send_push,
    vapid_public_key,
)
from company_discovery.quotas import QuotaError, QuotaStore
from company_discovery.readiness import build_report as build_readiness_report
from company_discovery.saved_search_alerts import (
    alert_summary_for_search,
    matches_for_search,
    saved_search_matches_job,
    unseen_matches_for_search,
)
from company_discovery.scheduler import DurableScheduler
from company_discovery.service import CompanyDiscoveryService, ScanConfig
from company_discovery.slack_notify import post_high_fit_notification
from company_discovery.sqlite_repository import SqliteCompanyDiscoveryRepository
from company_discovery.structured_analysis import parse_freeform
from company_discovery.tokens import TokenStore
from company_discovery.watchlist_templates import get_template, list_templates

ROOT = Path(__file__).parent
STATIC_ROOT = ROOT / "static"
DATA_ROOT = Path(
    get_env("HELPMEFINDTHEJOB_DATA_DIR", "COMPANY_DISCOVERY_DATA_DIR", str(ROOT / "data"))
)
DATA_PATH = DATA_ROOT / "company_discovery.sqlite3"
AUTH_PATH = DATA_ROOT / "auth.sqlite3"
AI_CONFIG_PATH = DATA_ROOT / "ai_provider.json"
WATCHLIST_SCHEDULE_PATH = DATA_ROOT / "watchlist_schedule.json"
ADMIN_AUDIT_PATH = DATA_ROOT / "admin_audit.log"
TOKEN_PATH = DATA_ROOT / "tokens.sqlite3"
QUOTA_PATH = DATA_ROOT / "quotas.sqlite3"
SCHEDULER_PATH = DATA_ROOT / "scheduler.sqlite3"
EMAIL_OUTBOX_PATH = DATA_ROOT / "email_outbox.log"
PASSWORD_RESET_REQUEST_LIMIT = 5  # per-IP per 10 minutes
PASSWORD_RESET_REQUEST_WINDOW = 600
# Per-IP per 10 minutes. Set DIRECTJOB_REGISTER_LIMIT in dev / test
# environments to relax the cap (e.g. red-team agents that need to
# register 7+ throwaway accounts in quick succession). Production
# stays at the default of 3.
try:
    REGISTER_REQUEST_LIMIT = int(
        get_env("HELPMEFINDTHEJOB_REGISTER_LIMIT", "DIRECTJOB_REGISTER_LIMIT") or 3
    )
except ValueError:
    REGISTER_REQUEST_LIMIT = 3
REGISTER_REQUEST_WINDOW = 600
REQUIRE_EMAIL_VERIFICATION = (
    get_env("HELPMEFINDTHEJOB_REQUIRE_EMAIL_VERIFICATION", "DIRECTJOB_REQUIRE_EMAIL_VERIFICATION")
    or ""
).strip().casefold() in ("true", "1", "yes")
APP_PUBLIC_URL = get_env("HELPMEFINDTHEJOB_PUBLIC_URL", "DIRECTJOB_PUBLIC_URL") or ""
LOCAL_USER_ID = "local-user"
MAX_JSON_BODY_BYTES = 5_000_000
DEFAULT_WATCHLIST_SCHEDULE = {
    "enabled": False,
    "intervalMinutes": 360,
    "lastRunAt": None,
    "lastRunStatus": "disabled",
}
APP_VERSION = "0.79.4"
EXPORT_SCHEMA_VERSION = 1
SESSION_COOKIE_NAME = "directjob_session"
APP_ENV = get_env("HELPMEFINDTHEJOB_ENV", "COMPANY_DISCOVERY_ENV", "development").strip().casefold()
# Bool env-var parsing routes through env_compat.get_env_bool, which
# accepts the permissive truthy set {"true", "1", "yes", "on"}
# casefolded. Earlier these two vars used a strict `== "true"`
# check that silently rejected "True", "TRUE", "1", "yes" — a real
# bug that PART 6 surfaced when an operator set
# HELPMEFINDTHEJOB_ALLOW_REGISTRATION=1 and registration stayed
# closed. Root cause fixed; matches env_compat semantics + matches
# the legalReviewed handling below.
COOKIE_SECURE = get_env_bool(
    "HELPMEFINDTHEJOB_COOKIE_SECURE",
    "DIRECTJOB_COOKIE_SECURE",
    default=(APP_ENV == "production"),
)
ALLOW_REGISTRATION = get_env_bool(
    "HELPMEFINDTHEJOB_ALLOW_REGISTRATION",
    "DIRECTJOB_ALLOW_REGISTRATION",
    default=False,
)
SECRET_KEY = get_env("HELPMEFINDTHEJOB_SECRET_KEY", "DIRECTJOB_SECRET_KEY") or (
    "dev-" + secrets.token_urlsafe(48)
)
ADMIN_EMAIL = get_env("HELPMEFINDTHEJOB_ADMIN_EMAIL", "DIRECTJOB_ADMIN_EMAIL")
ADMIN_PASSWORD = get_env("HELPMEFINDTHEJOB_ADMIN_PASSWORD", "DIRECTJOB_ADMIN_PASSWORD")


def jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {key: jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    return value


def to_snake_case_payload(payload: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "websiteUrl": "website_url",
        "careerPageUrl": "career_page_url",
        "relevanceScore": "relevance_score",
        "relevanceReason": "relevance_reason",
        "watchEnabled": "watch_enabled",
    }
    return {mapping.get(key, key): value for key, value in payload.items()}


def dataclass_from_payload(model: type[Any], payload: dict[str, Any]) -> Any:
    data = {field.name: payload[field.name] for field in fields(model) if field.name in payload}
    for key, value in list(data.items()):
        if key.endswith("_at") and isinstance(value, str):
            data[key] = datetime.fromisoformat(value)
    return model(**data)


def _ai_consent_satisfied(profile, provider) -> bool:
    """The user must have granted consent for the *current* provider id
    before we send their CV / structured profile to a third-party LLM.
    Manual mode + Ollama-local don't transmit anything off-host, so they
    bypass the gate."""

    if provider is None or provider.provider_id == "manual":
        return True
    if provider.invocation_mode == "local_http":
        return True  # Ollama runs in the user's own container.
    consent_at = getattr(profile, "ai_consent_at", None)
    consent_pid = getattr(profile, "ai_consent_provider_id", None)
    if not consent_at:
        return False
    # Switching providers requires re-consent (different data processor).
    return not consent_pid or consent_pid == provider.provider_id


def make_user_payload(user: AuthUser, csrf_token: str) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "isAdmin": user.is_admin,
        "csrfToken": csrf_token,
        "totpEnabled": STATE.auth_store.has_totp_enabled(user.id) if STATE else False,
    }


def make_admin_user_payload(user: AuthUser) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "isAdmin": user.is_admin,
        "createdAt": user.created_at,
        "lastLoginAt": user.last_login_at,
        "lastActiveAt": user.last_active_at,
    }


def session_cookie_header(token: str, max_age: int) -> str:
    parts = [
        f"{SESSION_COOKIE_NAME}={token}",
        "Path=/",
        f"Max-Age={max_age}",
        "HttpOnly",
        "SameSite=Lax",
    ]
    if COOKIE_SECURE:
        parts.append("Secure")
    return "; ".join(parts)


def _read_ai_act_audit_tail(
    log_path: Path, limit: int, event_type_filter: str | None
) -> list[dict[str, Any]]:
    """Read the tail of the AI Act Article 12 audit log.

    Returns up to ``limit`` of the most recent entries (most recent first),
    optionally filtered by event_type. Rotated sibling files are included
    so the queue surfaces events that have just been rotated out of the
    primary file.

    The implementation reads the live file plus rotated siblings into
    memory; for the §2.8 minimum-viable oversight UI this is acceptable
    because the queue is reviewed at human-attention rates (hundreds of
    events per review session, not millions). A streaming or
    sqlite-backed variant lands as a Phase 2 enhancement if oversight
    volumes outgrow the in-memory read.
    """
    records: list[dict[str, Any]] = []
    candidates: list[Path] = []
    if log_path.exists():
        candidates.append(log_path)
    candidates.extend(sorted(log_path.parent.glob(log_path.name + ".*")))
    for candidate in candidates:
        try:
            with candidate.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event_type_filter and record.get("event_type") != event_type_filter:
                        continue
                    records.append(record)
        except OSError:
            continue
    # Sort by timestamp descending so the most recent appears first
    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return records[:limit]


def _serialise_cv_section(section) -> dict[str, Any]:
    """JSON payload describing a CV-builder section for the UI."""
    if section is None:
        return None  # type: ignore[return-value]
    return {
        "sectionId": section.section_id,
        "label": section.label,
        "repeatable": section.repeatable,
        "questions": [
            {"key": q.key, "prompt": q.prompt, "required": q.required, "hint": q.hint}
            for q in section.questions
        ],
    }


def validate_production_config(auth_store: AuthStore) -> None:
    if APP_ENV != "production":
        return
    errors = []
    if len(SECRET_KEY) < 32 or SECRET_KEY.startswith("dev-"):
        errors.append(
            "DIRECTJOB_SECRET_KEY must be set to a stable random value with at least 32 characters."
        )
    if not auth_store.has_users() and (not ADMIN_EMAIL or not ADMIN_PASSWORD):
        errors.append(
            "DIRECTJOB_ADMIN_EMAIL and DIRECTJOB_ADMIN_PASSWORD are required for first production startup."
        )
    if not COOKIE_SECURE:
        errors.append("DIRECTJOB_COOKIE_SECURE must stay true in production behind HTTPS.")
    if errors:
        raise RuntimeError("production_config_error: " + " ".join(errors))


class AppState:
    def __init__(
        self,
        data_path: Path = DATA_PATH,
        auth_path: Path = AUTH_PATH,
        ai_config_path: Path = AI_CONFIG_PATH,
        schedule_path: Path = WATCHLIST_SCHEDULE_PATH,
        admin_audit_path: Path = ADMIN_AUDIT_PATH,
        token_path: Path | None = None,
        quota_path: Path | None = None,
        scheduler_path: Path | None = None,
        *,
        start_scheduler: bool = True,
        email_transport: EmailTransport | None = None,
    ) -> None:
        self.data_path = Path(data_path)
        self.auth_path = Path(auth_path)
        self.ai_config_path = Path(ai_config_path)
        self.schedule_path = Path(schedule_path)
        self.admin_audit_path = Path(admin_audit_path)
        self.token_path = Path(token_path or (self.data_path.parent / "tokens.sqlite3"))
        self.quota_path = Path(quota_path or (self.data_path.parent / "quotas.sqlite3"))
        self.scheduler_path = Path(scheduler_path or (self.data_path.parent / "scheduler.sqlite3"))
        self._audit_lock = Lock()
        # Authenticated encryption for at-rest secrets (cv_text, TOTP).
        # Falls back to HKDF(SECRET_KEY) when DIRECTJOB_DATA_KEY is unset
        # — same threat model as the legacy XOR path, with proper AEAD
        # so DB compromise no longer reveals plaintext.
        try:
            from company_discovery.crypto_kit import EncryptionAtRest

            self.encryption_at_rest: EncryptionAtRest | None = EncryptionAtRest.from_secret_key(
                SECRET_KEY
            )
        except Exception:  # noqa: BLE001 - cryptography import / KDF can fail many ways on minimal sandboxes; want plain-storage fallback for ALL of them, not just the predicted set
            # cryptography import failed (e.g. minimal sandbox). Fall
            # back to plain storage — production deploys must have
            # the dep available; this is a tests-only safety net.
            self.encryption_at_rest = None
        self.repository = SqliteCompanyDiscoveryRepository(
            self.data_path,
            crypto=self.encryption_at_rest,
        )
        self.auth_store = AuthStore(self.auth_path, SECRET_KEY)
        self.auth_store.bootstrap_admin_from_env(ADMIN_EMAIL, ADMIN_PASSWORD)
        validate_production_config(self.auth_store)
        self.service = CompanyDiscoveryService(
            self.repository,
            HTTPFetcher(),
            ScanConfig(max_pages_per_scan=5, request_delay_seconds=0.25),
        )
        self._active_lock = Lock()
        self._active_company_scans: set[tuple[str, str]] = set()
        self._login_lock = Lock()
        self._login_attempts: dict[str, list[float]] = {}
        self._reset_request_lock = Lock()
        self._reset_requests: dict[str, list[float]] = {}
        self._register_request_lock = Lock()
        self._register_requests: dict[str, list[float]] = {}
        self._demo_seed_lock = Lock()
        self.ai_providers = self._load_ai_providers()
        self.token_store = TokenStore(self.token_path, SECRET_KEY)
        self.quota_store = QuotaStore(self.quota_path)
        self.email_transport: EmailTransport = email_transport or build_transport(
            outbox_path=self.data_path.parent / "email_outbox.log",
        )
        self.scheduler = DurableScheduler(
            self.scheduler_path,
            handler=lambda user_id, trigger: self.run_user_daily(user_id, trigger=trigger),
        )
        self.billing_backend = build_billing_backend(data_dir=self.data_path.parent)
        providers: list = [CuratedSearchProvider()]
        if get_env(
            "HELPMEFINDTHEJOB_DUCKDUCKGO_DISABLED", "DIRECTJOB_DUCKDUCKGO_DISABLED", ""
        ).strip().lower() not in (
            "1",
            "true",
            "yes",
        ):
            providers.append(DuckDuckGoSearchProvider())
        brave_key = get_env("HELPMEFINDTHEJOB_BRAVE_API_KEY", "DIRECTJOB_BRAVE_API_KEY", "").strip()
        if brave_key:
            providers.append(BraveSearchProvider(api_key=brave_key))
        self.discovery_engine = DiscoveryEngine(providers=providers)
        # Aggregator (job-level) rail — separate engine because it returns
        # AggregatedJob rows rather than DiscoveryResult companies.
        self.aggregator_cache = AggregatorResultCache(
            self.data_path.parent / "aggregator_cache.sqlite3",
            ttl_seconds=int(
                get_env(
                    "HELPMEFINDTHEJOB_AGGREGATOR_TTL_SECONDS",
                    "DIRECTJOB_AGGREGATOR_TTL_SECONDS",
                    "3600",
                )
                or "3600"
            ),
        )
        aggregator_providers = list(default_no_auth_providers())
        # Future: signup providers (Adzuna, EURES, Bundesagentur) plug in here.
        self.aggregator_engine = JobAggregationEngine(
            providers=aggregator_providers,
            cache=self.aggregator_cache,
        )
        # Bug C piece 2 (2026-05-20): cache-only, deterministic
        # diagnostic engine for the empty-state review phase. Reads
        # AggregatorResultCache; never live-probes (operator decision
        # 2026-05-20 — free-tier providers' coverage skew would inject
        # structural bias against the migrant-five personas).
        from company_discovery.diagnostic_engine import DiagnosticEngine

        self.diagnostic_engine = DiagnosticEngine(
            cache=self.aggregator_cache,
            providers=aggregator_providers,
        )
        # one-shot migration: pull legacy JSON schedules into the durable scheduler
        legacy = self._load_watchlist_schedules()
        for user_id, item in legacy.items():
            self.scheduler.upsert(
                user_id,
                enabled=bool(item.get("enabled")),
                interval_minutes=int(item.get("intervalMinutes") or 360),
            )
        if start_scheduler:
            self.scheduler.start()
            # Daily retention purge — fire-and-forget thread, idempotent.
            # Wakes once an hour, only runs if 24h has elapsed since last run.
            import threading

            self._retention_last_run = now_utc()

            def _retention_loop():
                import time as _time

                while True:
                    _time.sleep(3600)
                    try:
                        if (now_utc() - self._retention_last_run).total_seconds() >= 86_400:
                            self.run_retention_purge()
                            self._retention_last_run = now_utc()
                    except Exception:  # noqa: BLE001 - retention loop must survive every error class; next hourly tick retries
                        # Purge failures shouldn't take down the loop; the
                        # next hourly tick will try again.
                        continue

            t = threading.Thread(target=_retention_loop, name="RetentionPurge", daemon=True)
            t.start()

    def bootstrap(self, user_id: str) -> dict[str, Any]:
        # READ data is scoped to the active workspace owner; the session
        # user's own profile (CV, persona, locale) stays per-user.
        data_user_id = self.effective_user_id(user_id)
        companies = self.repository.list_companies(data_user_id)
        discovered_jobs = self.repository.list_discovered_jobs(data_user_id)
        imported_jobs = self.repository.list_imported_jobs(data_user_id)
        ai_provider = self.ai_provider_for(user_id)
        schedule = self.schedule_for(user_id)
        profile = self.profile_for(user_id)
        saved_searches_raw = self.repository.list_saved_searches(data_user_id)
        steps = build_checklist(
            companies=companies,
            discovered_jobs=discovered_jobs,
            imported_jobs=imported_jobs,
            ai_provider=ai_provider,
            schedule_enabled=bool(schedule.get("enabled")),
            saved_searches=saved_searches_raw,
            profile=profile,
        )
        from company_discovery.onboarding import needs_first_run_wizard

        first_run_wizard = needs_first_run_wizard(
            saved_searches=saved_searches_raw,
            companies=companies,
            profile=profile,
            discovered_jobs=discovered_jobs,
            imported_jobs=imported_jobs,
            dismissed=bool(getattr(profile, "onboarding_dismissed", False)),
        )
        active_ws = profile.active_workspace_id or self.workspace_id_for_owner(user_id)
        return {
            "companies": companies,
            "discoveredJobs": discovered_jobs,
            "importedJobs": imported_jobs,
            "scans": self.repository.list_scans(data_user_id),
            "discoveryRuns": self.repository.list_discovery_runs(data_user_id),
            "summary": self.repository.watchlist_summary(data_user_id),
            "aiProvider": ai_provider.public_dict(),
            "aiProviderOptions": provider_options_payload(),
            "watchlistSchedule": schedule,
            "quotas": self.quota_store.usage(user_id),
            "savedSearches": self._saved_searches_with_alerts(data_user_id),
            "watchlistTemplates": list_templates(profile.persona_id),
            "billingPlans": plans_payload(),
            "personas": list_personas_summary(),
            "profile": self._profile_payload(profile),
            "workspaces": self.list_user_workspaces(user_id),
            "activeWorkspaceId": active_ws,
            "onboarding": {
                "steps": [step.__dict__ for step in steps],
                "progress": checklist_progress(steps),
                "firstRunWizard": first_run_wizard,
            },
            "whatsNew": self._whats_new_for(user_id),
            "applicationOutcomes": self.application_outcomes_summary(data_user_id),
            "skillGaps": self.aggregate_skill_gaps(data_user_id),
            "cvVariants": self.cv_variant_outcomes(data_user_id),
            "planLimits": self.plan_limits(),
            "applicationStatuses": list(APPLICATION_STATUSES),
        }

    def _whats_new_for(self, user_id: str, *, threshold_days: int = 7) -> dict[str, Any] | None:
        """Returns a payload for the 'what's new' toast when the user
        has been away long enough to warrant one. None when they've
        been active recently.

        The frontend shows the toast once per page load and links to
        ``/changelog`` so the user can read the actual release notes."""

        try:
            user = self.auth_store.get_user(user_id)
        except Exception:  # noqa: BLE001 - user gone is not a toast condition
            return None
        last = user.last_active_at or user.last_login_at
        if last is None:
            return None
        gap = now_utc() - last
        if gap.total_seconds() < threshold_days * 86_400:
            return None
        return {
            "appVersion": APP_VERSION,
            "daysAway": int(gap.total_seconds() // 86_400),
            "message": "Welcome back. We shipped a few things while you were away.",
            "link": "/changelog",
        }

    def workspace_id_for_owner(self, owner_user_id: str) -> str:
        """Deterministic workspace id derived from the owner's user id.

        Stable across restarts so existing user_id-keyed rows can be
        treated as belonging to ``ws_<owner>`` without backfill.
        """

        suffix = (
            owner_user_id.split("_", 1)[-1] if owner_user_id.startswith("user_") else owner_user_id
        )
        return f"ws_{suffix}"

    def ensure_owner_membership(
        self, user_id: str, label: str | None = None
    ) -> WorkspaceMembership:
        workspace_id = self.workspace_id_for_owner(user_id)
        existing = self.repository.find_workspace_membership(user_id, workspace_id)
        if existing is not None:
            return existing
        if label is None:
            try:
                user = self.auth_store.get_user(user_id)
                label = user.email
            except KeyError:
                label = "Workspace"
        membership = WorkspaceMembership(
            user_id=user_id,
            workspace_id=workspace_id,
            workspace_owner_id=user_id,
            role="owner",
            label=label,
        )
        return self.repository.save_workspace_membership(membership)

    def list_user_workspaces(self, user_id: str) -> list[dict[str, Any]]:
        memberships = self.repository.list_workspace_memberships(user_id)
        if not memberships:
            self.ensure_owner_membership(user_id)
            memberships = self.repository.list_workspace_memberships(user_id)
        results: list[dict[str, Any]] = []
        for m in memberships:
            results.append(
                {
                    "id": m.workspace_id,
                    "ownerUserId": m.workspace_owner_id,
                    "role": m.role,
                    "label": m.label or "Workspace",
                }
            )
        return results

    def effective_user_id(self, session_user_id: str) -> str:
        """Return the user-id whose data we should READ for this session.

        Reads ``UserProfile.active_workspace_id`` and looks up the
        workspace owner. Falls back to ``session_user_id`` when the
        active workspace is not set, points to a workspace the user is
        not a member of, or is the user's own workspace anyway.

        Writes still go to ``session_user_id`` until cross-workspace
        write routing ships in a follow-up.
        """

        profile = self.repository.get_user_profile(session_user_id)
        active = profile.active_workspace_id if profile else None
        if not active:
            return session_user_id
        own_ws = self.workspace_id_for_owner(session_user_id)
        if active == own_ws:
            return session_user_id
        membership = self.repository.find_workspace_membership(session_user_id, active)
        if membership is None:
            return session_user_id
        return membership.workspace_owner_id

    def resolve_workspace_owner(self, session_user_id: str, workspace_id: str | None) -> str:
        """Validate the user is a member of ``workspace_id`` and return the owner user id.

        Falls back to the user's own workspace when ``workspace_id`` is
        falsy. Raises ``ValueError("workspace_forbidden")`` when the
        user is not a member of the requested workspace — caller maps
        that to HTTP 403.
        """

        own_workspace = self.workspace_id_for_owner(session_user_id)
        target = (workspace_id or own_workspace).strip()
        membership = self.repository.find_workspace_membership(session_user_id, target)
        if membership is None:
            if target == own_workspace:
                self.ensure_owner_membership(session_user_id)
                return session_user_id
            raise ValueError("workspace_forbidden")
        return membership.workspace_owner_id

    def profile_for(self, user_id: str) -> UserProfile:
        existing = self.repository.get_user_profile(user_id)
        if existing is not None:
            return existing
        return UserProfile(user_id=user_id, persona_id=DEFAULT_PERSONA_ID)

    def update_profile(self, user_id: str, payload: dict[str, Any]) -> UserProfile:
        existing = self.repository.get_user_profile(user_id) or UserProfile(
            user_id=user_id, persona_id=DEFAULT_PERSONA_ID
        )
        previous_persona = existing.persona_id
        persona_id = str(
            payload.get("personaId")
            or payload.get("persona_id")
            or existing.persona_id
            or DEFAULT_PERSONA_ID
        )
        if persona_id not in PERSONAS:
            raise ValueError("unknown_persona")
        existing.persona_id = persona_id
        # When the user switches personas, the LLM-derived auto_fit_score
        # on existing queue rows was for the old persona — keeping it
        # would mislead. Clear scores on jobs they haven't imported yet
        # so the queue prompts them to re-fit against the new persona.
        if previous_persona and previous_persona != persona_id:
            cleared = 0
            for job in list(self.repository.discovered_jobs.values()):
                if job.user_id != user_id:
                    continue
                if job.imported_job_id:
                    continue
                if job.auto_fit_score is None:
                    continue
                job.auto_fit_score = None
                job.auto_fit_reason = None
                job.auto_fit_at = None
                job.auto_fit_provider_id = None
                self.repository.save_discovered_job(job)
                cleared += 1
            if cleared:
                self.log_analytics(
                    user_id,
                    "persona_changed_rescore",
                    {"from": previous_persona, "to": persona_id, "cleared": cleared},
                )

        target_roles = (
            payload.get("targetRoles") if "targetRoles" in payload else payload.get("target_roles")
        )
        if isinstance(target_roles, str):
            target_roles = [item.strip() for item in target_roles.split(",") if item.strip()]
        if target_roles is not None:
            existing.target_roles = [
                str(item).strip() for item in target_roles if str(item).strip()
            ][:25]

        if "industry" in payload:
            existing.industry = str(payload.get("industry") or "").strip() or None
        if "location" in payload:
            existing.location = str(payload.get("location") or "").strip() or None
        if "seniority" in payload:
            existing.seniority = str(payload.get("seniority") or "").strip() or None
        if "yearsExperience" in payload or "years_experience" in payload:
            raw_years = payload.get("yearsExperience", payload.get("years_experience"))
            if raw_years in (None, ""):
                existing.years_experience = None
            else:
                try:
                    existing.years_experience = max(0, min(60, int(raw_years)))
                except (TypeError, ValueError) as err:
                    raise ValueError("invalid_years_experience") from err
        languages = payload.get("languages")
        if isinstance(languages, str):
            languages = [item.strip() for item in languages.split(",") if item.strip()]
        if languages is not None:
            existing.languages = [str(item).strip() for item in languages if str(item).strip()][:10]
        if "cvText" in payload or "cv_text" in payload:
            cv_text = payload.get("cvText", payload.get("cv_text")) or ""
            cv_text = str(cv_text)
            if len(cv_text) > 60_000:
                raise ValueError("cv_too_long")
            existing.cv_text = cv_text.strip() or None
        if "notes" in payload:
            existing.notes = str(payload.get("notes") or "").strip() or None
        if "locale" in payload:
            from company_discovery.models import SUPPORTED_LOCALES

            raw_locale = str(payload.get("locale") or "en").strip().lower()
            if raw_locale not in SUPPORTED_LOCALES:
                raise ValueError("unsupported_locale")
            existing.locale = raw_locale
        if "theme" in payload:
            from company_discovery.models import SUPPORTED_THEMES

            raw_theme = str(payload.get("theme") or "dark").strip().lower()
            if raw_theme not in SUPPORTED_THEMES:
                raise ValueError("unsupported_theme")
            existing.theme = raw_theme
        if "hiddenSources" in payload or "hidden_sources" in payload:
            raw = payload.get("hiddenSources", payload.get("hidden_sources")) or []
            if not isinstance(raw, list):
                raise ValueError("invalid_hidden_sources")
            existing.hidden_sources = [str(s).strip() for s in raw if str(s).strip()][:50]
        if "dismissedTerms" in payload or "dismissed_terms" in payload:
            raw = payload.get("dismissedTerms", payload.get("dismissed_terms")) or []
            if not isinstance(raw, list):
                raise ValueError("invalid_dismissed_terms")
            cleaned = [str(s).strip() for s in raw if str(s).strip()][-50:]
            existing.dismissed_terms = cleaned
        if "addDismissedTerms" in payload:
            extras = payload.get("addDismissedTerms") or []
            if not isinstance(extras, list):
                raise ValueError("invalid_dismissed_terms")
            current = list(existing.dismissed_terms or [])
            for term in extras:
                term = str(term).strip()
                if term and term.casefold() not in {c.casefold() for c in current}:
                    current.append(term)
            existing.dismissed_terms = current[-50:]
        if "slackWebhookUrl" in payload or "slack_webhook_url" in payload:
            raw = payload.get("slackWebhookUrl", payload.get("slack_webhook_url"))
            url = "" if raw is None else str(raw).strip()
            # Hard length cap; keep a permissive prefix check (Slack /
            # Discord / Mattermost-compatible webhooks all start with
            # https:// and can be quite long).
            if url and (len(url) > 1024 or not url.startswith("https://")):
                raise ValueError("invalid_slack_webhook_url")
            existing.slack_webhook_url = url
        if "slackFitThreshold" in payload or "slack_fit_threshold" in payload:
            raw = payload.get("slackFitThreshold", payload.get("slack_fit_threshold"))
            try:
                t = float(raw) if raw is not None else 0.70
            except (TypeError, ValueError) as err:
                raise ValueError("invalid_slack_fit_threshold") from err
            existing.slack_fit_threshold = max(0.0, min(1.0, t))
        if "retentionDays" in payload or "retention_days" in payload:
            raw = payload.get("retentionDays", payload.get("retention_days"))
            try:
                days = int(raw) if raw is not None else 90
            except (TypeError, ValueError) as err:
                raise ValueError("invalid_retention_days") from err
            existing.retention_days = max(0, min(3650, days))
        if "onboardingDismissed" in payload or "onboarding_dismissed" in payload:
            existing.onboarding_dismissed = bool(
                payload.get("onboardingDismissed", payload.get("onboarding_dismissed"))
            )
        if "aiConsent" in payload:
            # First-AI-call consent. Stores the timestamp + the provider id
            # the user consented to. Switching provider in Settings clears
            # the consent so the modal re-prompts (handled in update_ai_provider).
            consent = payload.get("aiConsent") or {}
            if not isinstance(consent, dict):
                raise ValueError("invalid_ai_consent")
            if consent.get("granted"):
                existing.ai_consent_at = now_utc()
                existing.ai_consent_provider_id = (
                    str(consent.get("providerId") or consent.get("provider_id") or "").strip()
                    or None
                )
                self.log_analytics(
                    user_id, "ai_consent_granted", {"providerId": existing.ai_consent_provider_id}
                )
            else:
                existing.ai_consent_at = None
                existing.ai_consent_provider_id = None
                self.log_analytics(user_id, "ai_consent_revoked", {})

        return self.repository.save_user_profile(existing)

    def _saved_searches_with_alerts(self, user_id: str) -> list[dict[str, Any]]:
        searches = self.repository.list_saved_searches(user_id)
        if not searches:
            return []
        jobs = self.repository.list_discovered_jobs(user_id)
        companies_by_id = {c.id: c for c in self.repository.list_companies(user_id)}
        results: list[dict[str, Any]] = []
        for search in searches:
            payload = asdict(search)
            payload["alerts"] = alert_summary_for_search(search, jobs, companies_by_id)
            results.append(payload)
        return results

    def _profile_payload(self, profile: UserProfile) -> dict[str, Any]:
        return {
            "personaId": profile.persona_id,
            "targetRoles": list(profile.target_roles or []),
            "industry": profile.industry,
            "location": profile.location,
            "seniority": profile.seniority,
            "yearsExperience": profile.years_experience,
            "languages": list(profile.languages or []),
            "cvText": profile.cv_text or "",
            "cvLength": len(profile.cv_text or ""),
            "cvPhotoDataUri": profile.cv_photo_data_uri or None,
            "chatState": getattr(profile, "chat_state", None),
            "notes": profile.notes,
            "locale": profile.locale or "en",
            "theme": profile.theme or "dark",
            "hiddenSources": list(profile.hidden_sources or []),
            "dismissedTerms": list(profile.dismissed_terms or []),
            "activeWorkspaceId": profile.active_workspace_id,
            "onboardingDismissed": bool(getattr(profile, "onboarding_dismissed", False)),
            "retentionDays": int(getattr(profile, "retention_days", 90) or 0),
            "slackWebhookConfigured": bool(getattr(profile, "slack_webhook_url", "") or ""),
            "slackFitThreshold": float(getattr(profile, "slack_fit_threshold", 0.70) or 0.0),
            "aiConsentAt": profile.ai_consent_at.isoformat()
            if getattr(profile, "ai_consent_at", None)
            else None,
            "aiConsentProviderId": getattr(profile, "ai_consent_provider_id", None),
            "updatedAt": profile.updated_at.isoformat() if profile.updated_at else None,
        }

    def ai_provider_for(self, user_id: str) -> AIProviderConfig:
        return self.ai_providers.get(user_id) or AIProviderConfig()

    def update_ai_provider(self, user_id: str, payload: dict[str, Any]) -> AIProviderConfig:
        config = AIProviderConfig(
            provider_id=payload.get("providerId") or payload.get("provider_id") or "manual",
            invocation_mode=payload.get("invocationMode")
            or payload.get("invocation_mode")
            or "manual",
            model=payload.get("model") or "",
            credential_reference=payload.get("credentialReference")
            or payload.get("credential_reference")
            or "",
            base_url=payload.get("baseUrl") or payload.get("base_url") or "",
            command=payload.get("command") or "",
            notes=payload.get("notes") or "",
        )
        errors = validate_provider_config(config)
        if errors:
            raise ValueError(errors[0]["code"])
        # Tier limit (#25): refuse to set an invocation_mode the active
        # plan doesn't include. Manual is always allowed; api / cli /
        # local_http are gated by ``ai_modes_allowed``. Map our
        # invocation modes onto the three tier slugs (manual / byok /
        # managed).
        mode_slug = "manual"
        if config.invocation_mode in ("api", "cli", "local_http"):
            mode_slug = "managed" if config.provider_id == "managed" else "byok"
        try:
            self.assert_ai_mode_allowed(mode_slug)
        except ValueError as err:
            raise ValueError("plan_ai_mode_locked") from err
        self.ai_providers[user_id] = config
        self.ai_config_path.parent.mkdir(parents=True, exist_ok=True)
        self.ai_config_path.write_text(
            json.dumps(
                {"users": {key: value.public_dict() for key, value in self.ai_providers.items()}},
                indent=2,
            ),
            encoding="utf-8",
        )
        return config

    def _load_ai_providers(self) -> dict[str, AIProviderConfig]:
        if not self.ai_config_path.exists():
            return {}
        try:
            payload = json.loads(self.ai_config_path.read_text(encoding="utf-8"))
            if isinstance(payload.get("users"), dict):
                configs = {}
                for user_id, item in payload["users"].items():
                    config = self._provider_from_payload(item)
                    if not validate_provider_config(config):
                        configs[user_id] = config
                return configs
            config = self._provider_from_payload(payload)
            if validate_provider_config(config):
                return {}
            return {LOCAL_USER_ID: config}
        except (OSError, json.JSONDecodeError):
            return {}

    def _provider_from_payload(self, payload: dict[str, Any]) -> AIProviderConfig:
        return AIProviderConfig(
            provider_id=payload.get("provider_id") or payload.get("providerId") or "manual",
            invocation_mode=payload.get("invocation_mode")
            or payload.get("invocationMode")
            or "manual",
            model=payload.get("model") or "",
            credential_reference=payload.get("credential_reference")
            or payload.get("credentialReference")
            or "",
            base_url=payload.get("base_url") or payload.get("baseUrl") or "",
            command=payload.get("command") or "",
            notes=payload.get("notes") or "",
        )

    def update_watchlist_schedule(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        interval = int(payload.get("intervalMinutes") or payload.get("interval_minutes") or 360)
        record = self.scheduler.upsert(
            user_id, enabled=bool(payload.get("enabled")), interval_minutes=interval
        )
        return self._schedule_payload(record)

    def schedule_for(self, user_id: str) -> dict[str, Any]:
        return self._schedule_payload(self.scheduler.get(user_id))

    def _schedule_payload(self, record) -> dict[str, Any]:
        public = record.public_dict()
        return {**DEFAULT_WATCHLIST_SCHEDULE, **public}

    def _load_watchlist_schedules(self) -> dict[str, dict[str, Any]]:
        if not self.schedule_path.exists():
            return {}
        try:
            payload = json.loads(self.schedule_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if isinstance(payload.get("users"), dict):
            return {
                user_id: self._normalize_schedule(item)
                for user_id, item in payload["users"].items()
                if isinstance(item, dict)
            }
        if isinstance(payload, dict) and "intervalMinutes" in payload:
            return {LOCAL_USER_ID: self._normalize_schedule(payload)}
        return {}

    def _normalize_schedule(self, payload: dict[str, Any]) -> dict[str, Any]:
        interval = int(
            payload.get("intervalMinutes") or DEFAULT_WATCHLIST_SCHEDULE["intervalMinutes"]
        )
        return {
            **DEFAULT_WATCHLIST_SCHEDULE,
            **payload,
            "enabled": bool(payload.get("enabled")),
            "intervalMinutes": min(max(interval, 15), 10_080),
        }

    def _save_watchlist_schedules(self) -> None:
        self.schedule_path.parent.mkdir(parents=True, exist_ok=True)
        self.schedule_path.write_text(
            json.dumps({"users": self.watchlist_schedules}, indent=2), encoding="utf-8"
        )

    def record_admin_action(
        self,
        *,
        actor: AuthUser,
        target: AuthUser | None,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        entry = {
            "at": now_utc().isoformat(),
            "action": action,
            "actorId": actor.id,
            "actorEmail": actor.email,
            "targetId": target.id if target else None,
            "targetEmail": target.email if target else None,
            "details": details or {},
        }
        with self._audit_lock:
            self.admin_audit_path.parent.mkdir(parents=True, exist_ok=True)
            with self.admin_audit_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def health(self, user_id: str | None = None, *, detailed: bool = False) -> dict[str, Any]:
        scheduler_due = sum(1 for record in self.scheduler.all() if record.enabled)
        payload: dict[str, Any] = {
            "status": "ok",
            "version": APP_VERSION,
            "environment": APP_ENV,
            "storage": "sqlite",
            "registrationOpen": self.registration_open(),
            "schedulerActiveJobs": scheduler_due,
        }
        if user_id:
            payload["schedulerEnabled"] = bool(self.schedule_for(user_id).get("enabled"))
            payload["counts"] = {
                "companies": len(self.repository.list_companies(user_id)),
                "discoveredJobs": len(self.repository.list_discovered_jobs(user_id)),
                "importedJobs": len(self.repository.list_imported_jobs(user_id)),
                "scans": len(self.repository.list_scans(user_id)),
            }
            payload["quotas"] = self.quota_store.usage(user_id)
        if detailed:
            payload["subsystems"] = self._health_subsystems()
        return payload

    def _health_subsystems(self) -> dict[str, Any]:
        """Subsystem signals for ops monitoring.

        Visible in ``/api/health?detailed=1`` and inside the admin
        readiness panel. Each entry is either ``{"configured": bool,
        "details": "…"}`` or a primitive count, never a secret.
        """

        backup_remote = get_env(
            "HELPMEFINDTHEJOB_BACKUP_REMOTE", "DIRECTJOB_BACKUP_REMOTE", ""
        ).strip()
        backup_backend = (
            get_env("HELPMEFINDTHEJOB_BACKUP_BACKEND", "DIRECTJOB_BACKUP_BACKEND", "").strip()
            or "local"
        )
        push_configured = is_push_configured()
        brave_configured = bool(
            get_env("HELPMEFINDTHEJOB_BRAVE_API_KEY", "DIRECTJOB_BRAVE_API_KEY", "").strip()
        )
        stripe_active = os.environ.get(
            "DIRECTJOB_BILLING_BACKEND", ""
        ).strip() == "stripe" and bool(
            get_env("HELPMEFINDTHEJOB_STRIPE_API_KEY", "DIRECTJOB_STRIPE_API_KEY", "").strip()
        )
        webhook_configured = bool(
            get_env(
                "HELPMEFINDTHEJOB_STRIPE_WEBHOOK_SECRET", "DIRECTJOB_STRIPE_WEBHOOK_SECRET", ""
            ).strip()
        )
        # Subscription / membership counts (cheap; in-memory).
        push_subs = sum(1 for _ in self.repository.push_subscriptions.values())
        memberships = sum(1 for _ in self.repository.workspace_memberships.values())
        # Latest backup file mtime (best-effort; backups dir may not exist).
        last_backup = None
        try:
            backup_dir = Path("/var/backups/directjob")
            archives = sorted(backup_dir.glob("helpmefindthejob-*.tar.gz"))
            if archives:
                last_backup = datetime.fromtimestamp(
                    archives[-1].stat().st_mtime, tz=timezone.utc
                ).isoformat()
        except (OSError, ValueError):
            last_backup = None
        return {
            "push": {"configured": push_configured, "subscriptions": push_subs},
            "discoveryProviders": {
                "duckduckgo": True,  # always-on, no key
                "brave": brave_configured,
                "curated": True,
            },
            "billing": {
                "backend": backup_backend
                if False
                else (
                    get_env("HELPMEFINDTHEJOB_BILLING_BACKEND", "DIRECTJOB_BILLING_BACKEND")
                    or "manual"
                ),
                "stripeActive": stripe_active,
                "webhookConfigured": webhook_configured,
            },
            "backup": {
                "backend": backup_backend,
                "remoteConfigured": bool(backup_remote),
                "lastArchiveAt": last_backup,
            },
            "workspaces": {"membershipsTotal": memberships},
            "i18n": {"locales": ["en", "de"]},
            "legalReviewed": get_env_bool(
                "HELPMEFINDTHEJOB_LEGAL_REVIEWED",
                "DIRECTJOB_LEGAL_REVIEWED",
                default=False,
            ),
        }

    def admin_metrics(self) -> dict[str, Any]:
        users = self.auth_store.list_users()
        scheduler_state = [
            record.public_dict() | {"userId": record.user_id} for record in self.scheduler.all()
        ]
        recent_tickets = self.repository.list_support_tickets()[:5]
        return {
            "users": {
                "total": len(users),
                "active": sum(1 for user in users if user.active),
                "admins": sum(1 for user in users if user.role == "admin" and user.active),
            },
            "quotas": self.quota_store.admin_metrics(),
            "scheduler": scheduler_state,
            "openInvitations": [
                {
                    "id": token.id,
                    "email": token.email,
                    "role": token.role,
                    "createdBy": token.created_by,
                    "createdAt": token.created_at.isoformat(),
                    "expiresAt": token.expires_at.isoformat(),
                }
                for token in self.token_store.list_active("invitation")
            ],
            "recentTickets": [
                {
                    "id": ticket.id,
                    "subject": ticket.subject,
                    "status": ticket.status,
                    "createdAt": ticket.created_at.isoformat(),
                }
                for ticket in recent_tickets
            ],
            "appVersion": APP_VERSION,
            "environment": APP_ENV,
            "emailBackend": self.email_status()["backend"],
        }

    def readiness_report(self) -> dict[str, Any]:
        active_jobs = sum(1 for record in self.scheduler.all() if record.enabled)
        report = build_readiness_report(
            app_version=APP_VERSION,
            environment=APP_ENV,
            data_dir=self.data_path.parent,
            audit_path=self.admin_audit_path,
            scheduler_path=self.scheduler_path,
            active_scheduler_jobs=active_jobs,
        )
        return report.to_dict()

    def email_status(self) -> dict[str, Any]:
        from company_discovery.email_transport import ConsoleTransport, SmtpTransport

        transport = self.email_transport
        kind = "console"
        host = None
        port = None
        if isinstance(transport, SmtpTransport):
            kind = "smtp"
            host = transport.host
            port = transport.port
        elif isinstance(transport, ConsoleTransport):
            kind = "console"
        outbox_count = 0
        outbox_path = self.data_path.parent / "email_outbox.log"
        if outbox_path.exists():
            try:
                outbox_count = sum(
                    1
                    for line in outbox_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                )
            except OSError:
                outbox_count = 0
        return {
            "backend": kind,
            "host": host,
            "port": port,
            "fromAddress": email_from_address(),
            "publicUrl": APP_PUBLIC_URL or None,
            "outboxEntries": outbox_count,
        }

    def send_test_email(self, *, actor: AuthUser, target: str) -> dict[str, Any]:
        target = (target or actor.email).strip().casefold()
        if "@" not in target:
            raise ValueError("invalid_email")
        body = (
            "Helpmefindthejob test email.\n\n"
            f"Triggered by: {actor.email}\n"
            f"At: {now_utc().isoformat()}\n"
            "If you can read this, your email path is configured correctly. "
            "This message never contains tokens or secrets."
        )
        try:
            self.email_transport.send(
                Email(
                    to=target,
                    subject="Helpmefindthejob test email",
                    text=body,
                    from_address=email_from_address(),
                )
            )
        except Exception:  # noqa: BLE001 - test-email path is best-effort
            return {"status": "failed", "error": "smtp_failure"}
        self.record_admin_action(
            actor=actor,
            target=None,
            action="send_test_email",
            details={"target": target},
        )
        return {"status": "sent", "target": target, "backend": self.email_status()["backend"]}

    def request_account_deletion(
        self, *, user: AuthUser, reason: str | None = None
    ) -> SupportTicket:
        ticket = SupportTicket(
            user_id=user.id,
            subject="Account deletion request",
            body=(reason or "User requested account deletion via the app.").strip(),
            contact_email=user.email,
            status="account_deletion_pending",
        )
        saved = self.repository.save_support_ticket(ticket)
        # Mint a one-time confirmation token. The user must click the link
        # in the email to actually schedule the deletion (7-day grace).
        token = self.auth_store.start_account_deletion(user.id)
        confirm_url = self.public_url_for(f"/account/deletion-confirm?token={token}")
        self.log_analytics(user.id, "account_deletion_requested", {"ticketId": saved.id})
        try:
            self.email_transport.send(
                Email(
                    to=user.email,
                    subject="[Helpmefindthejob] Confirm account deletion",
                    text=(
                        "Hi,\n\n"
                        "We received a request to delete your Helpmefindthejob account.\n\n"
                        "If this was you, click the link below within the next 7 days to schedule the deletion. "
                        "After confirming, we wait another 7 days before erasing your data — you can cancel any time during that grace window from Settings → Privacy.\n\n"
                        f"Confirm deletion: {confirm_url}\n\n"
                        "If you did not request this, ignore this email — nothing will happen."
                    ),
                    from_address=email_from_address(),
                )
            )
        except Exception:  # noqa: BLE001, S110 - email best-effort
            pass
        try:
            self.email_transport.send(
                Email(
                    to=email_from_address(),
                    subject="[Helpmefindthejob] Account deletion request",
                    text=(
                        f"User: {user.email}\nUser id: {user.id}\nReason: {ticket.body}\n"
                        "User has been emailed a confirmation link. After they click it, the hard-delete fires 7 days later via the retention purge sweep."
                    ),
                    from_address=email_from_address(),
                )
            )
        except Exception:  # noqa: BLE001, S110 - email best-effort
            pass
        return saved

    def confirm_account_deletion(self, token: str) -> dict[str, Any]:
        user_id, scheduled_at = self.auth_store.confirm_account_deletion(token)
        self.log_analytics(
            user_id, "account_deletion_confirmed", {"scheduledAt": scheduled_at.isoformat()}
        )
        return {"userId": user_id, "scheduledAt": scheduled_at.isoformat()}

    def cancel_account_deletion(self, user: AuthUser) -> dict[str, Any]:
        cleared = self.auth_store.cancel_account_deletion(user.id)
        if cleared:
            self.log_analytics(user.id, "account_deletion_cancelled", {})
        return {"cleared": cleared}

    def get_account_deletion_state(self, user: AuthUser) -> dict[str, Any]:
        return self.auth_store.get_deletion_state(user.id)

    def seed_demo_data(self, user_id: str) -> list[dict[str, Any]]:
        """Seed five sample matched roles into the user's queue. Used by
        the empty-state CTA on the queue view so first-time users land
        on a populated screen instead of a blank page. Existing demo
        rows are not duplicated — repeated calls are no-ops once the
        five samples exist for the user.

        Holds ``_demo_seed_lock`` over the entire check-then-write so
        a burst of parallel calls (the user double-clicking, or a bot
        spamming the endpoint) doesn't race past the dedup check and
        produce 5×N rows. A single global lock is fine here because
        seeding is rare + bounded."""

        with self._demo_seed_lock:
            return self._seed_demo_data_locked(user_id)

    def _seed_demo_data_locked(self, user_id: str) -> list[dict[str, Any]]:
        from company_discovery.models import DiscoveredJob

        existing_demo_urls = {
            job.source_url
            for job in self.repository.list_discovered_jobs(user_id)
            if (job.structured_data or {}).get("is_demo")
        }
        samples: tuple[tuple[str, str, str, str, str, float, float, str], ...] = (
            (
                "Senior Backend Engineer",
                "Acme Health (Demo)",
                "https://demo.helpmefindthejob.com/acme-health",
                "Berlin",
                "https://demo.helpmefindthejob.com/jobs/senior-backend",
                0.92,
                0.88,
                "High overlap on Python + healthcare-management keywords; remote-friendly.",
            ),
            (
                "Frontend Engineer",
                "Sample SaaS (Demo)",
                "https://demo.helpmefindthejob.com/sample-saas",
                "Remote — DACH",
                "https://demo.helpmefindthejob.com/jobs/frontend",
                0.85,
                0.82,
                "Demo lead — TypeScript + design-system fit. Remote.",
            ),
            (
                "DevOps Engineer",
                "Demo Insurance (Demo)",
                "https://demo.helpmefindthejob.com/demo-insurance",
                "München",
                "https://demo.helpmefindthejob.com/jobs/devops",
                0.78,
                0.75,
                "Demo lead — Kubernetes / Terraform / SRE focus. Hybrid.",
            ),
            (
                "Data Engineer",
                "Mock Analytics (Demo)",
                "https://demo.helpmefindthejob.com/mock-analytics",
                "Hamburg",
                "https://demo.helpmefindthejob.com/jobs/data",
                0.88,
                0.84,
                "Demo lead — dbt + Snowflake + CDC; bilingual EN/DE team.",
            ),
            (
                "Product Manager",
                "Test Tech (Demo)",
                "https://demo.helpmefindthejob.com/test-tech",
                "Berlin",
                "https://demo.helpmefindthejob.com/jobs/product",
                0.74,
                0.71,
                "Demo lead — early-stage SaaS; PM-of-one with engineering background.",
            ),
        )
        # Ensure each demo company exists (one per role) so the standard
        # import flow — which requires a `company_id` — works for these
        # rows. Idempotent: companies are looked up by name first.
        existing_companies = {c.name: c for c in self.repository.list_companies(user_id)}
        created: list[dict[str, Any]] = []
        for title, company_name, company_site, location, url, confidence, fit, reason in samples:
            if url in existing_demo_urls:
                continue
            company = existing_companies.get(company_name)
            if company is None:
                company = self.service.create_company(
                    user_id=user_id,
                    name=company_name,
                    website_url=company_site,
                    sector="Demo",
                    notes="Sample company seeded for the empty-queue walkthrough. Safe to delete.",
                    watch_enabled=False,
                )
                existing_companies[company_name] = company
            job = DiscoveredJob(
                user_id=user_id,
                company_id=company.id,
                source_url=url,
                title=title,
                location=location,
                confidence_score=confidence,
                auto_fit_score=fit,
                auto_fit_reason=reason,
                structured_data={"is_demo": True, "company_name": company_name},
            )
            self.repository.save_discovered_job(job)
            created.append({"id": job.id, "title": title, "company_name": company_name})
        self.log_analytics(user_id, "demo_data_seeded", {"count": len(created)})
        return created

    def run_onboarding_drip(self) -> dict[str, int]:
        """Send the day-3 + day-7 onboarding emails for any user whose
        creation timestamp lands in the right window and who hasn't yet
        received that drip step. Idempotent — the per-step columns mean
        re-running the sweep is a no-op once everyone is up to date."""

        sent = {"day3": 0, "day7": 0}
        # Day-3 window is [3d, 7d) so users only get the day-3 email once
        # and don't get spammed if the sweep runs late.
        for user in self.auth_store.users_due_for_drip(
            column="drip_day3_sent_at",
            min_age_days=3,
            max_age_days=14,
        ):
            try:
                self._send_drip_day3(user)
                self.auth_store.mark_drip_sent(user.id, "drip_day3_sent_at")
                self.log_analytics(user.id, "drip_day3_sent", {})
                sent["day3"] += 1
            except Exception:  # noqa: BLE001 - email best-effort
                continue
        # Day-7 window is [7d, 30d) — bound the upper end so the cron
        # doesn't email someone who signed up six months ago and never
        # came back.
        for user in self.auth_store.users_due_for_drip(
            column="drip_day7_sent_at",
            min_age_days=7,
            max_age_days=30,
        ):
            try:
                self._send_drip_day7(user)
                self.auth_store.mark_drip_sent(user.id, "drip_day7_sent_at")
                self.log_analytics(user.id, "drip_day7_sent", {})
                sent["day7"] += 1
            except Exception:  # noqa: BLE001 - best-effort path; failure must not break the caller
                continue
        return sent

    def _send_drip_day3(self, user: AuthUser) -> None:
        public_url = self.public_url_for("/")
        help_url = self.public_url_for("/help#bookmarklet")
        body = (
            f"Hi,\n\n"
            "Three days in. The bookmarklet is the highest-leverage thing you can install: "
            "one click on a LinkedIn / Indeed / StepStone / XING job page captures it into your "
            "queue, even though those platforms block server-side scraping.\n\n"
            f"Setup walkthrough (3 steps): {help_url}\n"
            f"Open the app: {public_url}\n\n"
            "If something is unclear, reply to this email — we read every message.\n"
        )
        self.email_transport.send(
            Email(
                to=user.email,
                subject="[Helpmefindthejob] Day 3 — install the bookmarklet",
                text=body,
                from_address=email_from_address(),
            )
        )

    def _send_drip_day7(self, user: AuthUser) -> None:
        public_url = self.public_url_for("/")
        help_url = self.public_url_for("/help")
        body = (
            "Hi,\n\n"
            "One week in. Two questions:\n\n"
            '1. Did you find any roles worth applying to? If yes, did you tick the "Got a reply?" '
            "checkbox on the application form when companies wrote back? That's what populates "
            "your reply-rate card on the dashboard.\n\n"
            "2. What's been frustrating? Reply to this email with one sentence — it goes straight "
            "to the operator, not a support ticket queue.\n\n"
            f"Open the app: {public_url}\n"
            f"Help docs: {help_url}\n"
        )
        self.email_transport.send(
            Email(
                to=user.email,
                subject="[Helpmefindthejob] Day 7 — any luck?",
                text=body,
                from_address=email_from_address(),
            )
        )

    def send_email_verification(self, user: AuthUser) -> None:
        """Mint a fresh verification token and email the confirm link.
        Best-effort — a transport failure must not block sign-up; the
        user can request a resend from the auth gate."""

        token = self.auth_store.start_email_verification(user.id)
        confirm_url = self.public_url_for(f"/account/verify-email?token={token}")
        body = (
            "Hi,\n\n"
            "Welcome to Helpmefindthejob. Click the link below to verify your email address — "
            "this proves you own the inbox and unlocks the full app.\n\n"
            f"Verify your email: {confirm_url}\n\n"
            "If you did not sign up, ignore this email; the account stays unverified and unusable until someone clicks the link.\n"
        )
        try:
            self.email_transport.send(
                Email(
                    to=user.email,
                    subject="[Helpmefindthejob] Verify your email",
                    text=body,
                    from_address=email_from_address(),
                )
            )
        except Exception:  # noqa: BLE001, S110 - best-effort
            pass
        self.log_analytics(user.id, "email_verification_sent", {})

    def confirm_email_verification(self, token: str) -> dict[str, Any]:
        user_id = self.auth_store.confirm_email_verification(token)
        self.log_analytics(user_id, "email_verification_confirmed", {})
        return {"userId": user_id}

    def send_welcome_email(self, user: AuthUser) -> None:
        """Best-effort welcome email triggered on first sign-up. Hits
        the configured email transport (console in dev, SMTP in prod).
        Failures are swallowed by the caller — no welcome email should
        ever block a working account from being created."""

        public_url = self.public_url_for("/")
        help_url = self.public_url_for("/help")
        # Bookmarklet card lives in Settings → Bookmarklet; the
        # public_url above already points at the app, so we don't need
        # a separate bookmarklet_url variable.
        body = (
            f"Welcome to Helpmefindthejob.\n\n"
            "You signed in for the first time — here are three quick wins to make the product useful in 5 minutes:\n\n"
            "1. Add 5–10 companies whose careers pages you want to watch (Companies tab → Add).\n"
            "2. Set up a saved search for your role + city. We watch Indeed, StepStone, Arbeitnow, Muse, "
            "Bundesagentur and more daily.\n"
            "3. Install the bookmarklet so you can capture jobs from LinkedIn / Indeed in one click. "
            "Settings → Bookmarklet has a 3-step guide.\n\n"
            f"Help docs: {help_url}\n"
            f"Open the app: {public_url}\n\n"
            "Reply to this email if anything is unclear. We read every message."
        )
        self.email_transport.send(
            Email(
                to=user.email,
                subject="[Helpmefindthejob] Welcome — three quick wins",
                text=body,
                from_address=email_from_address(),
            )
        )
        self.log_analytics(user.id, "welcome_email_sent", {})

    def purge_due_account_deletions(self) -> list[dict[str, Any]]:
        """Hard-delete any account whose grace window has elapsed.
        Called from the retention purge cron and on app startup. Returns a
        list of summaries (one per deleted account) so callers can log."""

        results: list[dict[str, Any]] = []
        for user_id in self.auth_store.due_account_deletions():
            try:
                target = self.auth_store.get_user(user_id)
            except Exception:  # noqa: BLE001 - already gone
                continue
            try:
                summary = self.delete_user_account(actor=target, target_id=user_id)
                summary["trigger"] = "grace_expired"
                results.append(summary)
            except Exception as error:  # noqa: BLE001 - never block the sweep
                results.append({"userId": user_id, "status": "error", "error": str(error)})
        return results

    def delete_user_account(self, *, actor: AuthUser, target_id: str) -> dict[str, Any]:
        target = self.auth_store.get_user(target_id)
        if target.role == "admin" and target.active and self.auth_store.count_active_admins() <= 1:
            raise ValueError("last_admin_required")
        for company in list(self.repository.list_companies(target_id)):
            self.repository.delete_company(target_id, company.id)
        for kind in (
            "imported_jobs",
            "discovered_jobs",
            "scans",
            "discovery_runs",
            "saved_searches",
            "support_tickets",
            "analytics_events",
        ):
            store = getattr(self.repository, kind, {})
            for record_id in [
                k for k, item in list(store.items()) if getattr(item, "user_id", None) == target_id
            ]:
                store.pop(record_id, None)
        if hasattr(self.repository, "_connection"):
            for table in (
                "companies",
                "discovery_runs",
                "scans",
                "discovered_jobs",
                "imported_jobs",
                "saved_searches",
                "analytics_events",
                "support_tickets",
            ):
                self.repository._connection.execute(
                    f"DELETE FROM {table} WHERE user_id = ?", (target_id,)
                )
            self.repository._connection.commit()
        self.auth_store.delete_user_sessions(target_id)
        self.auth_store.connection.execute("DELETE FROM users WHERE id = ?", (target_id,))
        self.auth_store.connection.commit()
        self.scheduler._connection.execute("DELETE FROM schedules WHERE user_id = ?", (target_id,))
        self.scheduler._connection.commit()
        self.quota_store.connection.execute(
            "DELETE FROM user_counters WHERE user_id = ?", (target_id,)
        )
        self.quota_store.connection.commit()
        self.token_store.revoke_all_for(target.email)
        if target_id in self.ai_providers:
            del self.ai_providers[target_id]
            self.ai_config_path.parent.mkdir(parents=True, exist_ok=True)
            self.ai_config_path.write_text(
                json.dumps(
                    {
                        "users": {
                            key: value.public_dict() for key, value in self.ai_providers.items()
                        }
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        self.record_admin_action(
            actor=actor,
            target=target,
            action="delete_user",
            details={"email": target.email},
        )
        return {"status": "deleted", "userId": target_id, "email": target.email}

    def registration_open(self) -> bool:
        return ALLOW_REGISTRATION or not self.auth_store.has_users()

    def claim_login_slot(self, client_id: str) -> bool:
        """Atomically GC the window, check the cap, and claim a slot.
        Returns True (slot taken — the caller may attempt auth) or
        False (over cap — caller returns 429 and does NOT auth).

        Replaces the previous check-then-record pattern where 50
        parallel callers could each see < cap and slip through. With
        the atomic claim, only ``cap`` callers ever leave the lock
        with True per window.

        Successful logins should call :meth:`refund_login_slot` to put
        the slot back so the cap counts failures only — same semantics
        as the old ``record_login_failure``-on-failure pattern."""

        now = time.time()
        with self._login_lock:
            attempts = [
                item for item in self._login_attempts.get(client_id, []) if now - item < 600
            ]
            if len(attempts) >= 10:
                self._login_attempts[client_id] = attempts
                return False
            attempts.append(now)
            self._login_attempts[client_id] = attempts
            return True

    def refund_login_slot(self, client_id: str) -> None:
        """Pop the most recent slot we claimed in ``claim_login_slot``.
        Called on successful auth so the limit counts failures only."""

        with self._login_lock:
            attempts = self._login_attempts.get(client_id)
            if attempts:
                attempts.pop()

    # Backwards-compatible wrappers — kept so any external callers
    # / tests that exercise the old API don't break. New code should
    # use ``claim_login_slot`` + ``refund_login_slot`` instead.
    def login_allowed(self, client_id: str) -> bool:
        now = time.time()
        with self._login_lock:
            attempts = [
                item for item in self._login_attempts.get(client_id, []) if now - item < 600
            ]
            self._login_attempts[client_id] = attempts
            return len(attempts) < 10

    def record_login_failure(self, client_id: str) -> None:
        with self._login_lock:
            self._login_attempts.setdefault(client_id, []).append(time.time())

    def clear_login_failures(self, client_id: str) -> None:
        with self._login_lock:
            self._login_attempts.pop(client_id, None)

    def export_data(self, user_id: str) -> dict[str, Any]:
        return {
            "schemaVersion": EXPORT_SCHEMA_VERSION,
            "exportedAt": now_utc().isoformat(),
            "appVersion": APP_VERSION,
            "companies": self.repository.list_companies(user_id),
            "discoveredJobs": self.repository.list_discovered_jobs(user_id),
            "importedJobs": self.repository.list_imported_jobs(user_id),
            "scans": self.repository.list_scans(user_id),
            "discoveryRuns": self.repository.list_discovery_runs(user_id),
            "watchlistSchedule": self.schedule_for(user_id),
            "aiProvider": self.ai_provider_for(user_id).public_dict(),
        }

    def import_data(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if int(payload.get("schemaVersion") or 0) != EXPORT_SCHEMA_VERSION:
            raise ValueError("unsupported_export_schema")
        company_id_map = {
            item.get("id"): new_id("company") for item in payload.get("companies") or []
        }
        run_id_map = {item.get("id"): new_id("run") for item in payload.get("discoveryRuns") or []}
        scan_id_map = {item.get("id"): new_id("scan") for item in payload.get("scans") or []}
        discovered_id_map = {
            item.get("id"): new_id("discovered_job") for item in payload.get("discoveredJobs") or []
        }
        imported_id_map = {
            item.get("id"): new_id("job") for item in payload.get("importedJobs") or []
        }
        imported_counts = {
            "companies": 0,
            "discoveredJobs": 0,
            "importedJobs": 0,
            "scans": 0,
            "discoveryRuns": 0,
        }
        for item in payload.get("companies") or []:
            item = {
                **item,
                "id": company_id_map.get(item.get("id"), new_id("company")),
                "user_id": user_id,
            }
            self.repository.save_company(dataclass_from_payload(Company, item))
            imported_counts["companies"] += 1
        for item in payload.get("discoveryRuns") or []:
            item = {
                **item,
                "id": run_id_map.get(item.get("id"), new_id("run")),
                "user_id": user_id,
                "company_id": company_id_map.get(item.get("company_id")),
            }
            self.repository.save_discovery_run(dataclass_from_payload(CompanyDiscoveryRun, item))
            imported_counts["discoveryRuns"] += 1
        for item in payload.get("scans") or []:
            item = {
                **item,
                "id": scan_id_map.get(item.get("id"), new_id("scan")),
                "user_id": user_id,
                "company_id": company_id_map.get(item.get("company_id"), item.get("company_id")),
            }
            self.repository.save_scan(dataclass_from_payload(CareerPageScan, item))
            imported_counts["scans"] += 1
        for item in payload.get("discoveredJobs") or []:
            item = {
                **item,
                "id": discovered_id_map.get(item.get("id"), new_id("discovered_job")),
                "user_id": user_id,
                "company_id": company_id_map.get(item.get("company_id"), item.get("company_id")),
                "imported_job_id": imported_id_map.get(item.get("imported_job_id")),
            }
            self.repository.save_discovered_job(dataclass_from_payload(DiscoveredJob, item))
            imported_counts["discoveredJobs"] += 1
        for item in payload.get("importedJobs") or []:
            item = {
                **item,
                "id": imported_id_map.get(item.get("id"), new_id("job")),
                "user_id": user_id,
                "company_id": company_id_map.get(item.get("company_id"), item.get("company_id")),
                "discovered_job_id": discovered_id_map.get(
                    item.get("discovered_job_id"), item.get("discovered_job_id")
                ),
            }
            self.repository.save_imported_job(dataclass_from_payload(ImportedJob, item))
            imported_counts["importedJobs"] += 1
        if isinstance(payload.get("watchlistSchedule"), dict):
            schedule = payload["watchlistSchedule"]
            self.scheduler.upsert(
                user_id,
                enabled=bool(schedule.get("enabled")),
                interval_minutes=int(schedule.get("intervalMinutes") or 360),
            )
        if isinstance(payload.get("aiProvider"), dict):
            self.update_ai_provider(user_id, payload["aiProvider"])
        return {"status": "imported", "counts": imported_counts}

    def run_watchlist_scan(self, user_id: str, trigger: str = "manual") -> dict[str, Any]:
        companies = self.repository.list_companies(user_id)
        watched = [company for company in companies if company.watch_enabled]
        runs: list[CompanyDiscoveryRun] = []
        skipped: list[dict[str, Any]] = []
        for company in watched:
            if not company.career_page_url:
                skipped.append(
                    {"companyId": company.id, "name": company.name, "reason": "missing_career_page"}
                )
                continue
            hostname = urlparse(company.career_page_url).hostname or ""
            if hostname == "demo.example" or hostname.endswith(".example"):
                skipped.append(
                    {
                        "companyId": company.id,
                        "name": company.name,
                        "reason": "demo_fixture_not_scanned",
                    }
                )
                continue
            try:
                runs.append(self.start_scan(user_id, company.id, company.career_page_url))
            except QuotaError as error:
                skipped.append(
                    {"companyId": company.id, "name": company.name, "reason": error.code}
                )
        status = "queued" if runs else "nothing_to_scan"
        if trigger == "scheduled":
            # The DurableScheduler records the run on its own; we just return.
            self.scheduler.record_run(
                user_id,
                status=status,
                trigger=trigger,
                success=bool(runs) or status == "nothing_to_scan",
            )
        # Auto-push: notify the user about new saved-search matches found
        # by this batch. Cheap (in-memory diff against profile.last_push_notified_at).
        try:
            self.notify_new_matches(user_id)
        except Exception:  # noqa: BLE001, S110 — push side-effects must never break a scan
            pass
        return {
            "status": status,
            "runs": runs,
            "skipped": skipped,
            "schedule": self.schedule_for(user_id),
        }

    def run_saved_search(self, user_id: str, search_id: str, *, cap: int = 25) -> dict[str, Any]:
        """Run a SavedSearch through the aggregator pipeline.

        Top-N AggregatedJob results land as DiscoveredJob rows on the
        user's queue (with ``company_id=None`` because aggregator hits
        rarely match a known company in the watchlist). Existing
        dedup/merge semantics apply, so re-running the same query
        only adds new postings + records additional sources on
        existing rows via ``also_seen_at``.

        Returns ``{newJobs, mergedSources, candidates, query}`` so the
        UI can show "X new + Y already known" toasts and the scheduler
        can record the run.
        """

        search = self.repository.saved_searches.get(search_id)
        if search is None or search.user_id != user_id:
            raise KeyError(search_id)
        # Build a free-text query from name + roles. Persona/CV expansion is
        # Phase 2a's job; here we use the raw saved search payload so the
        # behaviour is predictable and offline-tunable.
        query_parts = [search.name] if search.name and search.name != "Untitled search" else []
        query_parts.extend(search.target_roles or [])
        query_parts.extend(search.sectors or [])
        query = " ".join(p.strip() for p in query_parts if p and p.strip())
        location = search.location
        agg_jobs, outcomes = self.aggregator_engine.search(
            query=query or (search.industry or ""),
            location=location,
            limit_per_provider=cap,
        )
        # Strict job-type filter applies to saved-search runs too —
        # if the user's profile has a job_type_filter set, the queue
        # only grows with jobs matching that role + location.
        profile = self.profile_for(user_id)
        if profile.job_type_filter:
            from company_discovery.job_type_filter import filter_jobs as _filter_jobs_by_type

            agg_jobs = _filter_jobs_by_type(
                agg_jobs,
                job_type=profile.job_type_filter,
                location=profile.job_type_location_filter or None,
            )
        new_jobs: list[DiscoveredJob] = []
        merged_sources: list[dict[str, str]] = []
        for job in agg_jobs:
            host = (urlparse(job.source_url).hostname or "").lower() or job.source
            candidate = DiscoveredJob(
                user_id=user_id,
                source_url=job.source_url,
                title=job.title[:160] or f"Listing on {host}",
                raw_snippet=(job.title or "")[:160] or None,
                raw_description=(job.description or "")[:2000] or None,
                location=job.location,
                confidence_score=0.55,
                structured_data={"captured_via": job.source, "host": host},
            )
            duplicate = self.repository.find_duplicate_discovered_job(candidate)
            if duplicate:
                existing = dict(duplicate.also_seen_at or {})
                existing[host] = {
                    "url": job.source_url,
                    "found_at": now_utc().isoformat(),
                    "source_label": job.source,
                }
                duplicate.also_seen_at = existing
                self.repository.save_discovered_job(duplicate)
                merged_sources.append({"discoveredJobId": duplicate.id, "sourceHost": host})
            else:
                saved = self.repository.save_discovered_job(candidate)
                new_jobs.append(saved)
        # Mark the search as run so the digest delta calculation is
        # consistent with manual run-now triggers.
        search.last_seen_at = now_utc()
        search.updated_at = now_utc()
        self.repository.save_saved_search(search)
        self.log_analytics(
            user_id,
            "saved_search_run",
            {
                "searchId": search.id,
                "query": query[:120],
                "location": location,
                "newJobs": len(new_jobs),
                "mergedSources": len(merged_sources),
                "candidates": len(agg_jobs),
            },
        )
        return {
            "searchId": search.id,
            "query": query,
            "location": location,
            "newJobs": len(new_jobs),
            "mergedSources": len(merged_sources),
            "candidates": len(agg_jobs),
            "providerOutcomes": [
                {
                    "provider": o.provider,
                    "jobCount": o.job_count,
                    "cached": o.cached,
                    "error": o.error,
                }
                for o in outcomes
            ],
        }

    def notify_new_matches(self, user_id: str, *, max_pushes: int = 5) -> dict[str, Any]:
        """Push to all of ``user_id``'s subscriptions for any unseen saved-search match.

        Idempotent: relies on ``UserProfile.last_push_notified_at`` so the
        same match isn't pushed twice across scans. Returns a small
        summary so callers (and tests) can assert on what fired.
        """

        if not is_push_configured():
            return {"status": "push_unavailable", "sent": 0}
        subs = self.repository.list_push_subscriptions(user_id)
        if not subs:
            return {"status": "no_subscriptions", "sent": 0}
        profile = self.profile_for(user_id)
        threshold = profile.last_push_notified_at
        searches = self.repository.list_saved_searches(user_id)
        if not searches:
            return {"status": "no_saved_searches", "sent": 0}
        jobs = self.repository.list_discovered_jobs(user_id)
        companies_by_id = {c.id: c for c in self.repository.list_companies(user_id)}
        candidates: list[tuple[DiscoveredJob, str]] = []
        seen_job_ids: set[str] = set()
        for search in searches:
            for job in jobs:
                if job.id in seen_job_ids or job.imported_job_id:
                    continue
                if threshold and job.discovered_at <= threshold:
                    continue
                company = companies_by_id.get(job.company_id)
                sector = company.sector if company else None
                if saved_search_matches_job(search, job, sector):
                    candidates.append((job, search.name))
                    seen_job_ids.add(job.id)
        # Newest first, capped.
        candidates.sort(key=lambda pair: pair[0].discovered_at, reverse=True)
        candidates = candidates[:max_pushes]
        sent = 0
        for job, search_name in candidates:
            company = companies_by_id.get(job.company_id)
            company_name = company.name if company else "Direct company"
            push_payload = PushPayload(
                title=f"New match: {job.title}",
                body=f"{company_name} · matches saved search “{search_name}”",
                url="/?queue=highlight",
            )
            for sub in subs:
                try:
                    send_push(sub, push_payload)
                    sent += 1
                except PushUnavailableError:
                    return {"status": "push_unavailable", "sent": sent}
                except Exception:  # noqa: BLE001 — stale subscription, just skip
                    continue
        if candidates:
            profile.last_push_notified_at = now_utc()
            self.repository.save_user_profile(profile)
        return {"status": "ok", "sent": sent, "candidates": len(candidates)}

    def seed_demo(self, user_id: str) -> dict[str, Any]:
        company = next(
            (
                item
                for item in self.repository.list_companies(user_id)
                if item.name == "Demo Klinikgruppe"
            ),
            None,
        )
        if company is None:
            company = self.service.create_company(
                user_id=user_id,
                name="Demo Klinikgruppe",
                website_url="https://demo.example",
                career_page_url="https://demo.example/karriere",
                sector="Hospital / clinic group",
                notes="Demo fixture for pilot walkthroughs. No live website was scanned.",
                watch_enabled=True,
            )
        job = DiscoveredJob(
            user_id=user_id,
            company_id=company.id,
            source_url="https://demo.example/jobs/junior-healthcare-project-manager",
            title="Junior Healthcare Project Manager",
            location="Berlin",
            raw_snippet="Junior Healthcare Project Manager",
            raw_description=(
                "Coordinate digital health and process-improvement projects with clinical, operations, "
                "and quality teams. Suitable for a junior healthcare-management profile."
            ),
            structured_data={"source": "local_demo_fixture"},
            confidence_score=0.9,
        )
        duplicate = self.repository.find_duplicate_discovered_job(job)
        saved_job = duplicate or self.repository.save_discovered_job(job)
        run = self.repository.save_discovery_run(
            CompanyDiscoveryRun(
                user_id=user_id,
                company_id=company.id,
                query=company.career_page_url,
                source_type="demo_fixture",
                status="completed",
                finished_at=now_utc(),
                pages_checked=1,
                jobs_found=0 if duplicate else 1,
                errors=[],
            )
        )
        self.repository.save_scan(
            CareerPageScan(
                user_id=user_id,
                company_id=company.id,
                career_page_url=company.career_page_url or "",
                status="completed",
                checked_robots=True,
                robots_allowed=True,
                pages_checked=1,
                jobs_found=0 if duplicate else 1,
                errors=[],
                source_urls=[company.career_page_url or ""],
            )
        )
        return {"company": company, "job": saved_job, "run": run}

    def start_scan(
        self, user_id: str, company_id: str, career_page_url: str | None
    ) -> CompanyDiscoveryRun:
        self.repository.get_company(user_id, company_id)
        self.quota_store.can_start_scan(user_id, target_url=career_page_url)
        active_key = (user_id, company_id)
        with self._active_lock:
            if active_key in self._active_company_scans:
                run = CompanyDiscoveryRun(
                    user_id=user_id,
                    company_id=company_id,
                    query=career_page_url,
                    source_type="career_page_scan",
                    status="already_running",
                    finished_at=now_utc(),
                    errors=[{"code": "scan_already_running"}],
                )
                return self.repository.save_discovery_run(run)
            self._active_company_scans.add(active_key)

        self.quota_store.record_scan_started(user_id, target_url=career_page_url)
        run = self.repository.save_discovery_run(
            CompanyDiscoveryRun(
                user_id=user_id,
                company_id=company_id,
                query=career_page_url,
                source_type="career_page_scan",
                status="queued",
            )
        )
        thread = Thread(
            target=self._run_scan, args=(user_id, run, company_id, career_page_url), daemon=True
        )
        thread.start()
        return run

    def _run_scan(
        self, user_id: str, run: CompanyDiscoveryRun, company_id: str, career_page_url: str | None
    ) -> None:
        try:
            self.service.scan_company_career_page(user_id, company_id, career_page_url, run)
        except Exception as error:  # noqa: BLE001 - background boundary
            run.status = "failed"
            run.errors = [{"code": "scan_failed", "message": str(error)}]
            run.finished_at = now_utc()
            self.repository.save_discovery_run(run)
        finally:
            with self._active_lock:
                self._active_company_scans.discard((user_id, company_id))
            self.quota_store.record_scan_finished(user_id)

    # Invitation + password reset helpers
    def claim_password_reset_slot(self, client_id: str) -> bool:
        """Atomic check-and-claim. Same shape as :meth:`claim_login_slot`
        but no refund concept — every reset request consumes a slot
        regardless of whether the email actually existed (we always
        return 202 to avoid leaking which addresses are registered)."""

        now = time.time()
        with self._reset_request_lock:
            attempts = [
                t
                for t in self._reset_requests.get(client_id, [])
                if now - t < PASSWORD_RESET_REQUEST_WINDOW
            ]
            if len(attempts) >= PASSWORD_RESET_REQUEST_LIMIT:
                self._reset_requests[client_id] = attempts
                return False
            attempts.append(now)
            self._reset_requests[client_id] = attempts
            return True

    def claim_register_slot(self, client_id: str) -> bool:
        """Atomic check-and-claim for public registration. Bootstrap
        admin path bypasses this (it's gated by ``has_users()`` upstream)."""

        now = time.time()
        with self._register_request_lock:
            attempts = [
                t
                for t in self._register_requests.get(client_id, [])
                if now - t < REGISTER_REQUEST_WINDOW
            ]
            if len(attempts) >= REGISTER_REQUEST_LIMIT:
                self._register_requests[client_id] = attempts
                return False
            attempts.append(now)
            self._register_requests[client_id] = attempts
            return True

    # Backwards-compatible wrappers (same intent as the login pair).
    def password_reset_allowed(self, client_id: str) -> bool:
        now = time.time()
        with self._reset_request_lock:
            attempts = [
                t
                for t in self._reset_requests.get(client_id, [])
                if now - t < PASSWORD_RESET_REQUEST_WINDOW
            ]
            self._reset_requests[client_id] = attempts
            return len(attempts) < PASSWORD_RESET_REQUEST_LIMIT

    def record_password_reset_request(self, client_id: str) -> None:
        with self._reset_request_lock:
            self._reset_requests.setdefault(client_id, []).append(time.time())

    def register_allowed(self, client_id: str) -> bool:
        now = time.time()
        with self._register_request_lock:
            attempts = [
                t
                for t in self._register_requests.get(client_id, [])
                if now - t < REGISTER_REQUEST_WINDOW
            ]
            self._register_requests[client_id] = attempts
            return len(attempts) < REGISTER_REQUEST_LIMIT

    def record_register_request(self, client_id: str) -> None:
        with self._register_request_lock:
            self._register_requests.setdefault(client_id, []).append(time.time())

    def public_url_for(self, path: str) -> str:
        if APP_PUBLIC_URL:
            return APP_PUBLIC_URL.rstrip("/") + path
        return path

    def send_invitation(self, *, actor: AuthUser, email: str, role: str) -> dict[str, Any]:
        normalized = email.strip().casefold()
        if not normalized or "@" not in normalized:
            raise ValueError("invalid_email")
        if role not in {"admin", "member"}:
            raise ValueError("invalid_role")
        # Revoke any prior invitation for this address so we never have two pending
        self.token_store.revoke_all_for(normalized, kind="invitation")
        issued = self.token_store.issue(
            kind="invitation",
            email=normalized,
            role=role,
            created_by=actor.id,
        )
        accept_url = self.public_url_for(f"/accept-invite?token={issued.raw_token}")
        message = (
            f"You have been invited to Helpmefindthejob as a {role}.\n\n"
            f"Accept your invitation here:\n{accept_url}\n\n"
            "If the link does not open, paste it into your browser. "
            "The invite expires in 48 hours and can be used once."
        )
        self.email_transport.send(
            Email(
                to=normalized,
                subject="Your Helpmefindthejob invitation",
                text=message,
                from_address=email_from_address(),
            )
        )
        self.record_admin_action(
            actor=actor,
            target=None,
            action="send_invite",
            details={"email": normalized, "role": role, "tokenId": issued.record.id},
        )
        return {
            "status": "sent",
            "tokenId": issued.record.id,
            "email": normalized,
            "role": role,
            "expiresAt": issued.record.expires_at.isoformat(),
            "acceptUrl": accept_url,
        }

    def accept_invitation(self, *, raw_token: str, password: str) -> AuthUser:
        if len(password) < 12:
            raise ValueError("password_too_short")
        record = self.token_store.consume("invitation", raw_token)
        if record is None:
            raise ValueError("invalid_token")
        try:
            user = self.auth_store.create_user(record.email, password, role=record.role)
        except ValueError as error:
            if str(error) != "email_already_exists":
                raise
            # Password reset semantics for an already-existing email
            existing = self.auth_store.authenticate(record.email, password)
            if existing is None:
                # Force-reset the password to the new one (admin path)
                target_id = self.auth_store.connection.execute(
                    "SELECT id FROM users WHERE email = ?",
                    (record.email,),
                ).fetchone()[0]
                self.auth_store.update_user(
                    target_id, password=password, role=record.role, active=True
                )
                user = self.auth_store.get_user(target_id)
            else:
                user = existing
        return user

    def request_password_reset(self, email: str) -> str | None:
        normalized = email.strip().casefold()
        if not normalized or "@" not in normalized:
            return None
        # Always revoke prior reset tokens
        self.token_store.revoke_all_for(normalized, kind="password_reset")
        try:
            self.auth_store.connection.execute(
                "SELECT 1 FROM users WHERE email = ?", (normalized,)
            ).fetchone()
        except Exception:  # noqa: BLE001 - any DB-layer failure in this lookup path is treated as "user does not exist"; we want a single fallback for the full failure surface
            return None
        row = self.auth_store.connection.execute(
            "SELECT id FROM users WHERE email = ?", (normalized,)
        ).fetchone()
        if row is None:
            # Do not leak existence; pretend success
            return None
        from datetime import timedelta as _td

        issued = self.token_store.issue(
            kind="password_reset",
            email=normalized,
            ttl=_td(hours=1),
        )
        reset_url = self.public_url_for(f"/reset-password?token={issued.raw_token}")
        message = (
            "We received a request to reset your Helpmefindthejob password.\n\n"
            f"If this was you, follow this link within 1 hour:\n{reset_url}\n\n"
            "If you did not request this, you can ignore this email."
        )
        self.email_transport.send(
            Email(
                to=normalized,
                subject="Reset your Helpmefindthejob password",
                text=message,
                from_address=email_from_address(),
            )
        )
        return reset_url

    # --- Phase 2/3 helpers ---

    def maybe_notify_slack(self, user_id: str, job) -> None:
        """Fire-and-forget Slack notification when ``job.auto_fit_score``
        crosses the user's threshold. No-op if disabled. Tracks notified
        ids on the profile so re-scoring doesn't double-ping."""

        profile = self.profile_for(user_id)
        url = (getattr(profile, "slack_webhook_url", "") or "").strip()
        if not url:
            return
        score = job.auto_fit_score or 0.0
        threshold = float(getattr(profile, "slack_fit_threshold", 0.70) or 0.0)
        if score < threshold:
            return
        notified = list(getattr(profile, "slack_notified_job_ids", []) or [])
        if job.id in notified:
            return
        company = self.repository.companies.get(job.company_id)
        company_name = (
            company.name
            if company
            else ((job.also_seen_at and next(iter(job.also_seen_at), "")) or "")
        )
        public_url = (
            get_env("HELPMEFINDTHEJOB_PUBLIC_URL", "DIRECTJOB_PUBLIC_URL")
            or "https://app.helpmefindthejob.com"
        )
        result = post_high_fit_notification(
            webhook_url=url,
            job_title=job.title or "",
            company_name=company_name,
            location=job.location,
            fit_score=score,
            fit_reason=job.auto_fit_reason,
            job_url=job.source_url,
            public_url=public_url,
        )
        # Track notified ids only on success — failed pings should retry later.
        if result.get("status") == "ok":
            notified.append(job.id)
            profile.slack_notified_job_ids = notified[-200:]
            self.repository.save_user_profile(profile)
            self.log_analytics(
                user_id,
                "slack_notified",
                {"discoveredJobId": job.id, "score": score},
            )

    def run_retention_purge(self, *, default_days: int = 90) -> dict[str, int]:
        """Sweep every user's old discovered jobs. Per-user
        ``profile.retention_days`` overrides the default. Imported jobs
        are kept regardless. Returns total deleted by user.

        Also fires the account-deletion grace sweep so accounts whose
        7-day grace has elapsed get hard-deleted in the same cron tick.

        Idempotent: safe to call repeatedly."""

        from datetime import timedelta

        results: dict[str, int] = {}
        for user in self.auth_store.list_users():
            profile = self.profile_for(user.id)
            days = int(getattr(profile, "retention_days", 0) or 0)
            if days <= 0:
                days = default_days
            if days <= 0:
                continue
            cutoff = now_utc() - timedelta(days=days)
            removed = self.repository.purge_discovered_jobs_older_than(
                user.id, cutoff=cutoff, keep_imported=True
            )
            if removed:
                results[user.id] = removed
                self.log_analytics(
                    user.id,
                    "retention_purge",
                    {"removed": removed, "days": days, "cutoff": cutoff.isoformat()},
                )
        deletions = self.purge_due_account_deletions()
        if deletions:
            results["__account_deletions"] = len(deletions)
        drip = self.run_onboarding_drip()
        if drip["day3"] or drip["day7"]:
            results["__drip_day3"] = drip["day3"]
            results["__drip_day7"] = drip["day7"]
        return results

    def current_plan(self) -> Plan | None:
        """Return the workspace's active plan as a Plan object, or None
        when ``Subscription.plan_id`` doesn't match any plan in the
        ``PLANS`` tuple (e.g. operator misconfigured, or a legacy
        plan id that's been removed). Callers must guard accordingly."""

        sub = self.get_subscription()
        return find_plan(sub.plan_id)

    def plan_limits(self) -> dict[str, Any]:
        """Snapshot of the active plan's tier limits — exactly the
        attributes ``Plan`` carries beyond label / price. ``None`` for
        ``savedSearchLimit`` means unlimited; the empty tuple for
        ``aiModesAllowed`` is currently never produced by any shipped
        plan but the enforcer treats it as "no AI at all" defensively."""

        plan = self.current_plan()
        if plan is None:
            # Fall through to the most permissive shape so a misconfig
            # doesn't accidentally lock a paying user out.
            return {
                "savedSearchLimit": None,
                "aiModesAllowed": ("manual", "byok", "managed"),
                "retentionDaysMax": 365,
                "dailyDigestEnabled": True,
            }
        return {
            "savedSearchLimit": plan.saved_search_limit,
            "aiModesAllowed": tuple(plan.ai_modes_allowed),
            "retentionDaysMax": plan.retention_days_max,
            "dailyDigestEnabled": plan.daily_digest_enabled,
        }

    def assert_can_add_saved_search(self, user_id: str) -> None:
        """Raise ``ValueError`` with code ``plan_saved_search_limit`` when
        the active plan caps saved-search count and the user has hit it.
        Called from the saved-search create endpoint before insertion."""

        limits = self.plan_limits()
        cap = limits["savedSearchLimit"]
        if cap is None:
            return
        existing = len(self.repository.list_saved_searches(self.effective_user_id(user_id)))
        if existing >= cap:
            raise ValueError("plan_saved_search_limit")

    def assert_ai_mode_allowed(self, mode: str) -> None:
        """Raise ``ValueError(plan_ai_mode_locked)`` when the requested
        invocation mode isn't included in the active plan's
        ``ai_modes_allowed``. Empty mode string falls through (the
        manual default isn't gated)."""

        wanted = (mode or "").strip().lower()
        if not wanted or wanted == "manual":
            return  # manual is always allowed; empty = no AI
        limits = self.plan_limits()
        if wanted not in limits["aiModesAllowed"]:
            raise ValueError("plan_ai_mode_locked")

    def cv_variant_outcomes(self, user_id: str, *, min_variants: int = 3) -> dict[str, Any]:
        """Per-variant reply-rate attribution (Phase 4 #44).

        For each ImportedJob with at least one ``cv_variant`` we count
        how many variants the user generated (numerator: total tailorings)
        and how many of those job applications later got a reply
        attributed to a specific variant. Returns aggregate counts plus
        a "winner" — the variant index with the highest attributed-reply
        rate, when at least ``min_variants`` variants exist across the
        user's queue. Hidden until then because n=1 is meaningless."""

        from collections import Counter

        per_index_total: Counter[int] = Counter()
        per_index_replied: Counter[int] = Counter()
        total_variants = 0
        for job in self.repository.list_imported_jobs(user_id):
            for variant in job.cv_variants or []:
                idx = int(variant.get("index") or 0)
                if idx <= 0:
                    continue
                per_index_total[idx] += 1
                total_variants += 1
                if variant.get("attributedReply"):
                    per_index_replied[idx] += 1
        ready = total_variants >= min_variants
        breakdown: list[dict[str, Any]] = []
        for idx, total in sorted(per_index_total.items()):
            replied = per_index_replied.get(idx, 0)
            rate = replied / total if total else 0.0
            breakdown.append(
                {
                    "index": idx,
                    "tailored": total,
                    "replied": replied,
                    "rate": round(rate, 4),
                }
            )
        winner = max(breakdown, key=lambda row: (row["rate"], row["replied"]), default=None)
        return {
            "ready": ready,
            "totalVariants": total_variants,
            "breakdown": breakdown,
            "winner": winner if (winner and winner["replied"] > 0) else None,
        }

    def assign_variant(
        self,
        *,
        experiment_id: str,
        identity: str,
        variants: tuple[str, ...] | list[str],
    ) -> str:
        """Deterministic A/B (or A/B/n) variant assignment (Phase 7 #61).

        Hash the ``experiment_id`` together with the visitor's stable
        identity (anonymous localStorage UUID for logged-out, user_id
        for logged-in), modulo the number of variants. Same identity →
        same variant for the lifetime of the experiment, which is the
        only correctness property an A/B test needs.

        Variants must be a non-empty list of slugs. The first slug is
        the control; the rest are treatments. Caller decides which to
        render."""

        if not variants:
            raise ValueError("variants_required")
        if not experiment_id:
            raise ValueError("experiment_id_required")
        if not identity:
            raise ValueError("identity_required")
        # SHA-256 of "<experiment_id>|<identity>" → integer → modulo.
        # The experiment_id in the prefix means a single visitor gets
        # different variants across different experiments (rather than
        # all the same — a "consistently lucky" visitor would skew our
        # results otherwise).
        digest = hashlib.sha256(f"{experiment_id}|{identity}".encode()).digest()
        bucket = int.from_bytes(digest[:8], "big") % len(variants)
        return variants[bucket]

    def experiment_config(self) -> list[dict[str, Any]]:
        """Read the operator-edited experiments config. Same pattern as
        ``list_seo_pages``: live re-read, malformed → empty, validated
        slugs only. Each entry: ``{id, description, variants: [slug, ...]}``."""

        path = self.data_path.parent / "experiments.json"
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        entries = payload.get("experiments") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return []
        result: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            exp_id = str(entry.get("id") or "").strip()
            variants = entry.get("variants")
            if not exp_id or not all(c.isalnum() or c in "-_" for c in exp_id):
                continue
            if not isinstance(variants, list) or not variants:
                continue
            cleaned_variants: list[str] = []
            for v in variants:
                v = str(v).strip()
                if v and all(c.isalnum() or c in "-_" for c in v):
                    cleaned_variants.append(v)
            if not cleaned_variants:
                continue
            result.append(
                {
                    "id": exp_id,
                    "description": str(entry.get("description") or "").strip(),
                    "variants": cleaned_variants,
                }
            )
        return result

    def list_seo_pages(self) -> list[dict[str, Any]]:
        """Read the operator-edited SEO-page config (Phase 1 #17). The
        file is re-read on every call so the operator can edit + reload
        without restarting the app. Returns an empty list if the file
        is missing or malformed (safer than crashing /jobs/<slug>).

        Operator path: copy ``deploy/seo-pages.json.example`` to
        ``<DATA_DIR>/seo-pages.json`` and edit the entries in place."""

        path = self.data_path.parent / "seo-pages.json"
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        pages = payload.get("pages") if isinstance(payload, dict) else None
        if not isinstance(pages, list):
            return []
        result = []
        for entry in pages:
            if not isinstance(entry, dict):
                continue
            slug = str(entry.get("slug") or "").strip()
            if not slug or not all(c.isalnum() or c == "-" for c in slug):
                continue
            result.append(
                {
                    "slug": slug,
                    "title": str(entry.get("title") or "").strip(),
                    "role": str(entry.get("role") or "").strip(),
                    "city": str(entry.get("city") or "").strip(),
                    "intro": str(entry.get("intro") or "").strip(),
                }
            )
        return result

    def find_seo_page(self, slug: str) -> dict[str, Any] | None:
        cleaned = (slug or "").strip()
        if not cleaned:
            return None
        for page in self.list_seo_pages():
            if page["slug"] == cleaned:
                return page
        return None

    def aggregate_skill_gaps(
        self, user_id: str, *, top_k: int = 3, min_jobs: int = 3
    ) -> dict[str, Any]:
        """Top-K skill gaps across the user's imported queue (Phase 4 #41).

        Returns ``{ready, top: [{skill, jobs, examples}, ...]}``. ``ready``
        is True when at least ``min_jobs`` imported jobs carry gaps —
        otherwise the dashboard card hides because the signal is too thin.
        ``examples`` is up to two job titles per gap so the user can recognise
        which roles drive the recommendation.

        Two-stage extraction:
        1. AI-derived gaps (``job.gaps``, populated by the auto-fit prompt's
           ``GAPS:`` line) — highest quality, but requires the user to have
           run auto-fit on at least ``min_jobs`` jobs.
        2. **Heuristic fallback**: when stage 1 produces no signal (the
           common case for Manual-mode users), scan each imported job's
           description against a curated skill vocabulary and report
           which terms appear across multiple JDs but are *absent* from
           the user's CV. Honors the same marketing promise without
           needing an AI call."""

        from collections import Counter

        counter: Counter[str] = Counter()
        examples: dict[str, list[str]] = {}
        jobs_with_gaps = 0
        for job in self.repository.list_imported_jobs(user_id):
            if not job.gaps:
                continue
            jobs_with_gaps += 1
            for gap in job.gaps:
                key = gap.strip().lower()
                if not key:
                    continue
                counter[key] += 1
                examples.setdefault(key, [])
                if len(examples[key]) < 2 and job.title:
                    examples[key].append(job.title)
        ready = jobs_with_gaps >= min_jobs
        top: list[dict[str, Any]] = []
        for key, jobs in counter.most_common(top_k):
            display = next(
                (
                    g
                    for job in self.repository.list_imported_jobs(user_id)
                    for g in (job.gaps or [])
                    if g.strip().lower() == key
                ),
                key,
            )
            top.append({"skill": display, "jobs": jobs, "examples": examples[key]})

        # Stage 2: heuristic fallback for Manual-mode users.
        if not top:
            top, jobs_with_gaps, ready = self._heuristic_skill_gaps(
                user_id,
                top_k=top_k,
                min_jobs=min_jobs,
            )
        return {"ready": ready, "jobsWithGaps": jobs_with_gaps, "top": top}

    # Curated skill vocabulary for the heuristic fallback. Lower-cased
    # surface forms. Order is preserved for display ranking ties.
    _SKILL_VOCAB: tuple[str, ...] = (
        # Languages
        "python",
        "java",
        "javascript",
        "typescript",
        "golang",
        "rust",
        "ruby",
        "php",
        "scala",
        "kotlin",
        "swift",
        "c++",
        "c#",
        # Role / area categories (common in DACH titles)
        "devops",
        "sre",
        "site reliability",
        "data engineering",
        "machine learning",
        "ml",
        "ai",
        "frontend",
        "backend",
        "fullstack",
        "full-stack",
        "mobile",
        "ios",
        "android",
        "embedded",
        "platform",
        "security",
        "qa",
        "quality assurance",
        # Frontend frameworks
        "react",
        "vue",
        "angular",
        "svelte",
        "tailwind",
        "next.js",
        "redux",
        # Backend frameworks
        "django",
        "fastapi",
        "flask",
        "spring",
        "rails",
        "node.js",
        "express",
        "graphql",
        "rest",
        "grpc",
        # Data
        "postgres",
        "postgresql",
        "mysql",
        "mongodb",
        "redis",
        "elasticsearch",
        "snowflake",
        "bigquery",
        "kafka",
        "rabbitmq",
        "sql",
        "nosql",
        "data warehouse",
        "dbt",
        "airflow",
        "spark",
        "hadoop",
        # Cloud / Infra
        "aws",
        "azure",
        "gcp",
        "kubernetes",
        "docker",
        "terraform",
        "ansible",
        "helm",
        "prometheus",
        "grafana",
        "ci/cd",
        "jenkins",
        "github actions",
        "linux",
        "microsoft",
        "cloud",
        # ML / AI
        "tensorflow",
        "pytorch",
        "scikit-learn",
        "pandas",
        "numpy",
        "llm",
        "langchain",
        "embeddings",
        "vector database",
        "rag",
        # DevOps / Security
        "oauth",
        "jwt",
        "soc2",
        "gdpr",
        "dsgvo",
        "iso 27001",
        # Marketing / Sales / Ops
        "hubspot",
        "salesforce",
        "marketo",
        "google ads",
        "google analytics",
        "looker",
        "tableau",
        "power bi",
        "ga4",
        "seo",
        "sem",
        "b2b saas",
        "demand generation",
        "performance marketing",
        "brand marketing",
        # Soft / methodology
        "agile",
        "scrum",
        "kanban",
    )

    def _heuristic_skill_gaps(
        self,
        user_id: str,
        *,
        top_k: int,
        min_jobs: int,
    ) -> tuple[list[dict[str, Any]], int, bool]:
        """Keyword-frequency skill gap extraction. No AI required."""
        from collections import Counter

        profile = self.profile_for(user_id)
        cv_text = (profile.cv_text or "").casefold()
        jobs = self.repository.list_imported_jobs(user_id)
        # Threshold: at least 1 imported job must exist to surface anything.
        if not jobs:
            return [], 0, False
        counter: Counter[str] = Counter()
        examples: dict[str, list[str]] = {}
        jobs_with_gap_count = 0
        for job in jobs:
            description = (job.description or "").casefold()
            title = (job.title or "").casefold()
            haystack = f"{title} {description}"
            if not haystack.strip():
                continue
            job_gaps_seen: set[str] = set()
            for skill in self._SKILL_VOCAB:
                skill_lc = skill.casefold()
                # Skill mentioned in the job AND missing from the CV
                if skill_lc in haystack and skill_lc not in cv_text:
                    counter[skill_lc] += 1
                    examples.setdefault(skill_lc, [])
                    if len(examples[skill_lc]) < 2 and job.title:
                        if job.title not in examples[skill_lc]:
                            examples[skill_lc].append(job.title)
                    job_gaps_seen.add(skill_lc)
            if job_gaps_seen:
                jobs_with_gap_count += 1
        top: list[dict[str, Any]] = []
        for key, jobs_count in counter.most_common(top_k):
            # Display: pick the original casing from the vocab (e.g. "AWS"
            # not "aws"). The vocab is mixed-case where capitalisation matters.
            display = next(
                (s for s in self._SKILL_VOCAB if s.casefold() == key),
                key,
            )
            # Title-case for terms that aren't acronyms in the vocab.
            if display == display.casefold():
                display = display.title()
            top.append({"skill": display, "jobs": jobs_count, "examples": examples[key]})
        # Ready when we have ≥1 imported job AND at least 1 skill surfaced.
        # min_jobs threshold from AI path doesn't apply — the heuristic is
        # cheaper signal so we don't need 3+ jobs to be honest about it.
        ready = bool(top) and len(jobs) >= 1
        return top, jobs_with_gap_count, ready

    # ---------------- Chat-router session storage ----------------
    # ClassVar — intentional process-wide singleton dict, not a per-
    # instance attribute. AppState is itself a process-wide singleton.
    _chat_sessions: ClassVar[dict[str, ChatSession]] = {}

    def chat_session_for(self, user_id: str) -> ChatSession:
        """Return the user's chat session. On first access in a process,
        rehydrate from ``profile.chat_state`` so an in-flight conversation
        survives a server restart."""
        if user_id not in self._chat_sessions:
            profile = self.profile_for(user_id)
            saved = getattr(profile, "chat_state", None)
            if saved and isinstance(saved, dict):
                # Reconstruct from on-disk JSON. Mirror of ChatSession.to_dict.
                history = [
                    ChatTurn(role=str(t.get("role", "")), content=str(t.get("content", "")))
                    for t in (saved.get("history") or [])
                    if isinstance(t, dict)
                ]
                pending_raw = saved.get("pending")
                pending = None
                if isinstance(pending_raw, dict) and pending_raw.get("commandName"):
                    pending = PendingCommand(
                        command_name=str(pending_raw["commandName"]),
                        args=dict(pending_raw.get("args") or {}),
                        awaiting=pending_raw.get("awaiting"),
                        awaiting_confirmation=bool(
                            pending_raw.get("awaitingConfirmation") or False
                        ),
                    )
                self._chat_sessions[user_id] = ChatSession(history=history, pending=pending)
            else:
                self._chat_sessions[user_id] = ChatSession()
        return self._chat_sessions[user_id]

    def chat_session_persist(self, user_id: str) -> None:
        """Snapshot the in-memory session to ``profile.chat_state``.
        Called after every message so a server restart doesn't lose
        in-flight pending commands. Merges with whatever else lives
        in ``chat_state`` (e.g. the R17 journey state) instead of
        clobbering it."""
        session = self._chat_sessions.get(user_id)
        if session is None:
            return
        # Cap history at 50 turns to keep the payload bounded.
        if len(session.history) > 50:
            session.history = session.history[-50:]
        profile = self.profile_for(user_id)
        # Preserve any other top-level keys (e.g. "journey") so the
        # journey state machine doesn't get wiped out on every reply.
        merged = dict(profile.chat_state or {})
        merged.update(session.to_dict())
        profile.chat_state = merged
        self.repository.save_user_profile(profile)

    def chat_reset(self, user_id: str) -> None:
        self._chat_sessions.pop(user_id, None)
        profile = self.profile_for(user_id)
        if getattr(profile, "chat_state", None) is not None:
            profile.chat_state = None
            self.repository.save_user_profile(profile)

    # Chat AI router — in-memory LRU cache + per-process metrics.
    # Cache key: (message_lower_stripped, last_3_assistant_replies_joined).
    # Same user-message + same recent context → same classification, so
    # we can serve repeated probes without re-billing the LLM.
    # ClassVar — intentional process-wide singleton cache + metrics dicts.
    _chat_router_cache: ClassVar[dict[tuple, tuple[float, str | None]]] = {}
    _CHAT_ROUTER_CACHE_TTL = 600  # seconds — 10 min
    _CHAT_ROUTER_CACHE_MAX = 1024
    # Per-user rate limit on AI-router classifications (cache hits don't
    # count). 20 LLM calls / 60s / user is roughly twice what a focused
    # tester can manually generate; above that we suspect a bug or
    # adversarial usage and fall back to keyword router.
    _chat_router_calls: ClassVar[dict[str, list[float]]] = {}
    _CHAT_ROUTER_RATE_LIMIT = 20
    _CHAT_ROUTER_RATE_WINDOW = 60
    chat_router_metrics: ClassVar[dict[str, int]] = {
        "calls": 0,
        "cache_hits": 0,
        "errors": 0,
        "via_user_provider": 0,
        "via_managed": 0,
        "no_provider_available": 0,
        "rate_limited": 0,
    }

    def _chat_router_cache_key(self, message: str, history: list[ChatTurn]) -> tuple:
        recent = " | ".join(t.content[:120] for t in history[-3:] if t.role == "assistant")
        return ((message or "").strip().casefold(), recent)

    def _chat_router_managed_provider(self) -> AIProviderConfig | None:
        """Construct an AIProviderConfig that points the dispatcher at
        the operator's managed key — used as fallback when the user is
        in Manual mode. Returns None when no managed key is configured."""
        managed_key = (
            get_env("HELPMEFINDTHEJOB_MANAGED_AI_KEY", "DIRECTJOB_MANAGED_AI_KEY") or ""
        ).strip()
        if not managed_key:
            return None
        # Opt-in flag so the operator decides whether to spend tokens
        # on chat-routing classifications.
        enabled = (
            (get_env("HELPMEFINDTHEJOB_CHAT_AI_ROUTER", "DIRECTJOB_CHAT_AI_ROUTER") or "")
            .strip()
            .lower()
        )
        if enabled not in {"true", "1", "yes", "on"}:
            return None
        upstream = (
            (
                get_env("HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER", "DIRECTJOB_MANAGED_AI_PROVIDER")
                or "openai"
            )
            .strip()
            .lower()
        )
        if upstream not in {"openai", "anthropic", "google_gemini", "deepseek", "openrouter"}:
            return None
        return AIProviderConfig(
            provider_id=upstream,
            invocation_mode="api",
            model=(
                get_env("HELPMEFINDTHEJOB_MANAGED_AI_MODEL", "DIRECTJOB_MANAGED_AI_MODEL") or ""
            ).strip(),
            credential_reference="HELPMEFINDTHEJOB_MANAGED_AI_KEY",
            base_url=(
                get_env("HELPMEFINDTHEJOB_MANAGED_AI_BASE_URL", "DIRECTJOB_MANAGED_AI_BASE_URL")
                or ""
            ).strip(),
            command="",
            notes="managed-chat-router",
        )

    def chat_ai_route_full(
        self, user_id: str, message: str, history: list[ChatTurn]
    ) -> tuple[str | None, dict]:
        """Like :meth:`chat_ai_route` but ALSO returns extracted args
        from the AI's JSON response. Returns ``(command_id, args_dict)``;
        empty args dict when the AI used the legacy bare-name format or
        didn't extract anything."""
        cmd = self.chat_ai_route(user_id, message, history)
        if cmd is None:
            return None, {}
        # The last classification's raw response is held in the cache
        # next to the parsed command id. We re-parse from the stash.
        raw = getattr(self, "_chat_router_last_raw", None) or ""
        args = parse_ai_router_extracted_args(raw)
        return cmd, args

    def chat_ai_route(self, user_id: str, message: str, history: list[ChatTurn]) -> str | None:
        """Classify the user's free-form intent into ONE of the known
        chat commands. Never executes — only proposes a command id.

        Routing waterfall:
          1. In-memory cache hit (same message + recent context).
          2. The user's configured AI provider (if non-Manual + consent OK).
          3. Operator-managed AI (when ``DIRECTJOB_CHAT_AI_ROUTER=true``
             AND ``HELPMEFINDTHEJOB_MANAGED_AI_KEY`` are set). This is the
             "long-term" path: Manual-mode testers get smart routing
             via the operator's key, no per-user provider config.
          4. ``None`` — caller falls back to the keyword router or help.

        Failures are swallowed; this method NEVER raises. A flaky LLM
        must not break the chat — the deterministic regex/keyword
        layers stay underneath.
        """
        self.chat_router_metrics["calls"] += 1

        # 1. Cache.
        cache_key = self._chat_router_cache_key(message, history)
        cached = self._chat_router_cache.get(cache_key)
        if cached is not None:
            cached_at, value = cached
            if time.time() - cached_at < self._CHAT_ROUTER_CACHE_TTL:
                self.chat_router_metrics["cache_hits"] += 1
                return value

        # 2. + 3. — pick a provider.
        provider: AIProviderConfig | None = None
        source = ""
        user_provider = self.ai_provider_for(user_id)
        profile = self.profile_for(user_id)
        if (
            user_provider.invocation_mode != "manual"
            and user_provider.provider_id != "manual"
            and _ai_consent_satisfied(profile, user_provider)
        ):
            provider = user_provider
            source = "user"
        else:
            managed = self._chat_router_managed_provider()
            if managed is not None:
                provider = managed
                source = "managed"

        if provider is None:
            self.chat_router_metrics["no_provider_available"] += 1
            self._chat_router_cache_put(cache_key, None)
            return None

        # Per-user rate limit — count NON-CACHED calls only. Cache
        # hits already returned above. Sliding 60s window.
        now = time.time()
        bucket = self._chat_router_calls.setdefault(user_id, [])
        # Drop expired entries.
        cutoff = now - self._CHAT_ROUTER_RATE_WINDOW
        bucket[:] = [t for t in bucket if t > cutoff]
        if len(bucket) >= self._CHAT_ROUTER_RATE_LIMIT:
            self.chat_router_metrics["rate_limited"] += 1
            # Don't cache rate-limit decisions (the window slides).
            return None
        bucket.append(now)

        # Bounded prompt — the AI must return only a command id.
        prompt = build_ai_router_prompt(
            message, [{"role": t.role, "content": t.content} for t in history]
        )
        try:
            from company_discovery.analysis import _dispatch_provider

            result = _dispatch_provider(prompt, provider, "")
            if result.status != "completed" or not result.output:
                self.chat_router_metrics["errors"] += 1
                self._chat_router_cache_put(cache_key, None)
                return None
            command = parse_ai_router_response(result.output)
            # Stash the raw response so chat_ai_route_full can re-parse
            # the args dict without re-billing the LLM.
            self._chat_router_last_raw = result.output
            self.chat_router_metrics[
                "via_user_provider" if source == "user" else "via_managed"
            ] += 1
            # Audit-log the classification (input first 120 chars, output id).
            self.log_analytics(
                user_id,
                "chat_ai_route",
                {
                    "source": source,
                    "message": (message or "")[:120],
                    "classified": command,
                },
            )
            self._chat_router_cache_put(cache_key, command)
            return command
        except Exception:  # noqa: BLE001 — router failure must not break chat
            self.chat_router_metrics["errors"] += 1
            self._chat_router_cache_put(cache_key, None)
            return None

    def _chat_router_cache_put(self, key: tuple, value: str | None) -> None:
        if len(self._chat_router_cache) >= self._CHAT_ROUTER_CACHE_MAX:
            # Drop oldest 10% (poor-man's LRU — by insertion order).
            drop_n = max(1, self._CHAT_ROUTER_CACHE_MAX // 10)
            for k in list(self._chat_router_cache.keys())[:drop_n]:
                self._chat_router_cache.pop(k, None)
        self._chat_router_cache[key] = (time.time(), value)

    # ---------------- Chat command handlers ----------------
    # Each handler runs AFTER user confirmation. Receives validated args.

    def chat_handler_add_company(self, user_id: str, args: dict) -> dict:
        from company_discovery.models import Company

        company = Company(
            user_id=user_id,
            name=args["name"],
            website_url=args["websiteUrl"],
            career_page_url=args.get("careerPageUrl") or None,
            watch_enabled=True,
        )
        saved = self.repository.save_company(company)
        self.log_analytics(user_id, "chat_cmd", {"name": "add_company", "company_id": saved.id})
        return {"ok": True, "id": saved.id, "message": f"Added **{saved.name}** to your watchlist."}

    def chat_handler_create_saved_search(self, user_id: str, args: dict) -> dict:
        try:
            record = self.save_saved_search(
                user_id,
                {
                    "name": args["name"],
                    "targetRoles": args["targetRoles"],
                    "location": args.get("location") or None,
                },
            )
        except ValueError as exc:
            return {"ok": False, "message": f"Couldn't save: {exc}"}
        self.log_analytics(user_id, "chat_cmd", {"name": "create_saved_search", "id": record.id})
        return {"ok": True, "id": record.id, "message": f"Saved search **{record.name}** created."}

    def chat_handler_find_jobs(self, user_id: str, args: dict) -> dict:
        """Run a job search and ALWAYS engage the journey's review
        phase so the user has a real continuation path (drill into a
        category → pick a job → letter / consult / save) regardless of
        whether the search was triggered by slash, keyword, NL, or the
        guided journey. Single code path — fixes the R18 bug where
        slash `/find` left the user stranded with no way to see or
        interact with the results.
        """
        from company_discovery.aggregators import rank_aggregated
        from company_discovery.job_type_filter import (
            filter_jobs as filter_jobs_by_type,
        )
        from company_discovery.job_type_filter import (
            filter_malformed_jobs,
            identify_bucket,
            normalize_location,
            persona_for_bucket,
        )
        from company_discovery.journey import (
            MAX_SEARCH_JOBS_CARRIED,
            PHASE_DONE,
            PHASE_REVIEW,
            cluster_jobs,
        )
        from company_discovery.personas import get_persona

        profile = self.profile_for(user_id)
        query = args["query"]
        location = args.get("location") or profile.location or None

        bucket_key = identify_bucket(query)
        jobs, outcomes = self.aggregator_engine.search(
            query=query,
            location=location,
            limit_per_provider=10,
            persona_id=profile.persona_id,
        )
        if bucket_key:
            jobs = filter_jobs_by_type(jobs, job_type=bucket_key, location=location)
        elif normalize_location(location):
            jobs = filter_jobs_by_type(jobs, job_type=None, location=location)
        persona = get_persona(profile.persona_id)
        keyword_tokens: list[str] = []
        for chunk in (query, *persona.default_target_roles):
            keyword_tokens.extend(re.findall(r"\w+", chunk.casefold()))
        ranked = rank_aggregated(jobs, keyword_tokens=keyword_tokens, location=location, cap=30)

        # Build the journey-style payload — same shape regardless of
        # caller — so the chat journey state has real continuation
        # data and the canvas can render the result cards.
        raw_dicts = [
            {
                "title": (j.title or "")[:200],
                "company": (j.company_name or "")[:120],
                "location": (j.location or "")[:120],
                "url": (j.source_url or "")[:300],
                "source": (j.source or "")[:60],
                "description": (j.description or "")[:600],
            }
            for j, _ in ranked[: MAX_SEARCH_JOBS_CARRIED * 2]
        ]
        # R21.3: drop jobs with swapped fields / garbage URLs.
        # Aggregator parsers sometimes get title↔location reversed
        # and surface garbage cards on the canvas.
        job_dicts = filter_malformed_jobs(raw_dicts)[:MAX_SEARCH_JOBS_CARRIED]
        if len(raw_dicts) != len(job_dicts):
            self.log_analytics(
                user_id,
                "aggregator_malformed_jobs_dropped",
                {"raw": len(raw_dicts), "kept": len(job_dicts)},
            )
        clusters = cluster_jobs(job_dicts)
        categorized: dict[str, list[str]] = {}
        jobs_by_id: dict[str, dict] = {}
        for category, items in clusters.items():
            ids: list[str] = []
            for j in items:
                job_id = j.get("url") or j.get("title") or ""
                if not job_id:
                    continue
                ids.append(job_id)
                jobs_by_id[job_id] = {
                    "title": j["title"],
                    "company": j["company"],
                    "location": j["location"],
                    "url": j["url"],
                    "source": j["source"],
                }
            if ids:
                categorized[category] = ids

        # R79.x: build the journey state ON the same profile
        # instance we mutate below — otherwise two `save_user_profile`
        # calls on different fetches of the same row race, and the
        # second one obliterates the first's writes. Concretely: the
        # journey save was being clobbered by the job_type_filter
        # save, so the post-search REVIEW phase never landed on disk
        # and the user's next message got the contextual fallback
        # instead of the new-search-intent interrupt.
        from company_discovery.journey import UserJourney

        journey = UserJourney.from_dict(
            (profile.chat_state or {}).get("journey"),
        )
        journey.role_text = query
        journey.bucket_key = bucket_key or ""
        if location:
            journey.location = location
        journey.search_results_by_category = categorized
        journey.search_jobs_by_id = jobs_by_id
        if not job_dicts:
            journey.phase = PHASE_DONE
        else:
            journey.phase = PHASE_REVIEW

        # Merge journey into chat_state on the SAME profile instance.
        merged_chat_state = dict(profile.chat_state or {})
        merged_chat_state["journey"] = journey.to_dict()
        profile.chat_state = merged_chat_state

        # R16: persist job-type filter so watchlist scans honour it.
        # R21.2: also auto-set persona so future ranking isn't biased
        # by an unrelated default.
        if bucket_key:
            profile.job_type_filter = bucket_key
            profile.job_type_location_filter = location or ""
            mapped_persona = persona_for_bucket(bucket_key)
            if mapped_persona and profile.persona_id != mapped_persona:
                profile.persona_id = mapped_persona
                self.log_analytics(
                    user_id,
                    "auto_persona_switch",
                    {"from_bucket": bucket_key, "to_persona": mapped_persona},
                )
        # ONE save — chat_state + filter + persona all together.
        self.repository.save_user_profile(profile)

        self.log_analytics(
            user_id,
            "chat_cmd",
            {
                "name": "find_jobs",
                "query": query[:120],
                "jobCount": len(job_dicts),
                "jobType": bucket_key or None,
                "categories": len(categorized),
            },
        )

        # Reply uses the user's own language (matches R16.1 fix).
        role_label = query
        if not job_dicts:
            return {
                "ok": True,
                "message": (
                    f"No matches for **{role_label}**"
                    f"{' in ' + location if location else ''} right now. "
                    "Try a different role or widen the location — "
                    "type **find a job** to start fresh."
                ),
                "jobs": [],
                "totalJobs": 0,
                "jobType": bucket_key,
                # No navigateTo — the canvas stays where it was.
            }

        cats_md = "\n".join(
            f"  - **{c}**: {len(ids)} job{'s' if len(ids) != 1 else ''}"
            for c, ids in categorized.items()
        )
        # Loop 16 (2026-05-20): Gate 6.5 partial-failure
        # transparency. When some providers fail (error field set
        # on the AggregationOutcome) but others returned results,
        # prepend an honest banner so the user knows the result
        # set is incomplete. Total-failure path is already handled
        # by the journey's run_search_with try/except wrapper
        # (returns the friendly "snag" message + PHASE_DONE).
        errored_outcomes = [o for o in outcomes if o.error]
        partial_banner = ""
        if errored_outcomes and job_dicts:
            total = len(outcomes)
            failed = len(errored_outcomes)
            partial_banner = (
                f"_(Some providers were temporarily unavailable "
                f"— {failed} of {total} reported errors. Results "
                f"below are from the working providers.)_\n\n"
            )
        msg = (
            partial_banner
            + f"Found **{len(job_dicts)}** {role_label} result(s)"
            + f"{' in ' + location if location else ''}."
            + (" (Strict role filter applied — only this job type.)" if bucket_key else "")
            + f"\n\n{cats_md}\n\n"
            "Reply with a **category name** to drill in, or look at "
            "the right panel to see all the cards."
        )
        return {
            "ok": True,
            "message": msg,
            "jobs": job_dicts,
            "totalJobs": len(job_dicts),
            "jobType": bucket_key,
            "categories": list(categorized.keys()),
            # Loop 16: errored providers carried in the response so
            # the run_search_with branch (which renders its own
            # summary_msg from categorized) can also surface the
            # partial-failure banner consistently.
            "erroredOutcomes": [
                {"provider": o.provider, "error": o.error}
                for o in errored_outcomes
            ],
            # PART 9 Loop 29: total provider count so the client's
            # post-op elapsed-time footer can say "took 12.3s across
            # N providers (M succeeded, K unavailable)" — gives the
            # user agency over "where did my time go" without
            # introducing real streaming (Phase 2 #77).
            "totalProviders": len(outcomes),
            # Tell the client to switch the canvas to the search-results
            # view so the user can SEE the results, not just hear that
            # they exist.
            "navigateTo": "searchResults",
        }

    def chat_handler_update_profile(self, user_id: str, args: dict) -> dict:
        updates = {}
        if args.get("persona"):
            updates["personaId"] = args["persona"]
        if args.get("location"):
            updates["location"] = args["location"]
        if args.get("targetRoles"):
            updates["targetRoles"] = args["targetRoles"]
        if not updates:
            return {"ok": False, "message": "Nothing to update — you didn't fill any field."}
        try:
            self.update_profile(user_id, updates)
        except ValueError as exc:
            return {"ok": False, "message": f"Couldn't update: {exc}"}
        self.log_analytics(
            user_id, "chat_cmd", {"name": "update_profile", "fields": list(updates.keys())}
        )
        return {"ok": True, "message": f"Updated: {', '.join(updates.keys())}."}

    def chat_handler_mark_applied(self, user_id: str, args: dict) -> dict:
        imported_id = args["importedJobId"]
        imported = self.repository.imported_jobs.get(imported_id)
        if not imported or imported.user_id != user_id:
            return {"ok": False, "message": f"Imported job {imported_id!r} not found."}
        imported.application_status = args["status"]
        if "replied" in args and args["replied"] and not imported.replied_at:
            imported.replied_at = now_utc()
        if "replied" in args and args["replied"] is False:
            imported.replied_at = None
        imported.updated_at = now_utc()
        self.repository.save_imported_job(imported)
        self.log_analytics(
            user_id,
            "chat_cmd",
            {"name": "mark_applied", "id": imported_id, "status": args["status"]},
        )
        return {
            "ok": True,
            "id": imported_id,
            "message": f"Marked **{imported.title}** as **{args['status']}**.",
        }

    def chat_handler_help(self, user_id: str, args: dict) -> dict:
        self.log_analytics(user_id, "chat_cmd", {"name": "help"})
        return {"ok": True, "message": render_help_text()}

    def chat_handler_open_cv_builder(self, user_id: str, args: dict) -> dict:
        """Navigate-style command — tells the client to open the CV
        Builder view. The client looks at result.navigateTo and
        switches views; no DB write here."""
        self.log_analytics(user_id, "chat_cmd", {"name": "open_cv_builder"})
        return {
            "ok": True,
            "navigateTo": "cvBuilder",
            "message": (
                "Opening the CV Builder. Walk through the sections — "
                "I'll format what you write but never invent facts. "
                "You can upload a photo and download as PDF at the end."
            ),
        }

    def chat_handler_tailor_cv(self, user_id: str, args: dict) -> dict:
        imported_id = args["importedJobId"]
        imported = self.repository.imported_jobs.get(imported_id)
        if not imported or imported.user_id != user_id:
            return {"ok": False, "message": f"Imported job {imported_id!r} not found."}
        profile = self.profile_for(user_id)
        if not (profile.cv_text or "").strip():
            return {"ok": False, "message": "Add a CV first (CV Builder or Settings)."}
        provider = self.ai_provider_for(user_id)
        if not _ai_consent_satisfied(profile, provider):
            return {"ok": False, "message": "AI consent required — confirm in Settings first."}
        from company_discovery.analysis import execute_cv_tailoring
        from company_discovery.persona_fixtures import friction_keywords_for

        result = execute_cv_tailoring(
            imported,
            provider,
            "",
            profile,
            friction_keywords=friction_keywords_for(profile.persona_id),
        )
        self.log_analytics(
            user_id, "chat_cmd", {"name": "tailor_cv", "id": imported_id, "status": result.status}
        )
        return {
            "ok": result.status == "completed",
            "message": (
                f"Tailored CV {result.status} for **{imported.title}**"
                if result.status == "completed"
                else f"Tailor result: {result.status}. {(result.error or '')[:120]}"
            ),
            "tailoredExcerpt": (result.output or "")[:400],
        }

    def chat_handler_run_saved_search(self, user_id: str, args: dict) -> dict:
        search_id = args["searchId"]
        try:
            result = self.run_saved_search(user_id, search_id)
        except KeyError:
            return {"ok": False, "message": f"Saved search {search_id!r} not found."}
        self.log_analytics(
            user_id,
            "chat_cmd",
            {
                "name": "run_saved_search",
                "id": search_id,
                "newJobs": result.get("newJobs"),
                "mergedSources": result.get("mergedSources"),
            },
        )
        return {
            "ok": True,
            "message": (
                f"Saved search ran: **{result.get('newJobs', 0)}** new, "
                f"**{result.get('mergedSources', 0)}** merged sources."
            ),
        }

    def chat_handler_set_persona(self, user_id: str, args: dict) -> dict:
        persona = args["persona"]
        from company_discovery.personas import PERSONAS

        if persona not in PERSONAS:
            return {
                "ok": False,
                "message": (f"Unknown persona {persona!r}. Valid: {', '.join(sorted(PERSONAS))}"),
            }
        try:
            self.update_profile(user_id, {"personaId": persona})
        except ValueError as exc:
            return {"ok": False, "message": f"Couldn't switch: {exc}"}
        self.log_analytics(user_id, "chat_cmd", {"name": "set_persona", "persona": persona})
        return {"ok": True, "message": f"Persona is now **{persona}**."}

    def chat_handler_delete_company(self, user_id: str, args: dict) -> dict:
        company_id = args["companyId"]
        try:
            self.repository.delete_company(user_id, company_id)
        except KeyError:
            return {"ok": False, "message": f"Company {company_id!r} not found in your watchlist."}
        self.log_analytics(user_id, "chat_cmd", {"name": "delete_company", "id": company_id})
        return {"ok": True, "message": f"Removed company **{company_id}** from your watchlist."}

    # ---------------- Guided job-search journey (R17) ----------------

    def _build_contextual_fallback(self, user_id: str, user_message: str) -> str:
        """Build a contextual no-route reply that knows the journey
        state, so the user is never left guessing. Replaces the
        generic "I'm not sure" dead-end (R19).
        """
        from company_discovery.journey import (
            PHASE_CV_CONSULT,
            PHASE_DRILL,
            PHASE_LETTER,
            PHASE_REVIEW,
            PHASE_TAILOR,
        )

        journey = self._journey_load(user_id)

        # In review phase: surface the categories the user can drill
        # into. They just searched and the answer is right there.
        if journey.phase == PHASE_REVIEW:
            categories = list(journey.search_results_by_category.keys())
            if categories:
                cats_md = "\n".join(f"  - **{c}**" for c in categories)
                return (
                    "I didn't catch that — you've got an active "
                    "search waiting. Reply with one of the "
                    "categories below to see the jobs in it:\n"
                    f"{cats_md}\n\n"
                    "Or type **cancel** to start over."
                )

        # In drill phase: ask for a number.
        if journey.phase == PHASE_DRILL:
            ids = journey.search_results_by_category.get(journey.picked_category, [])
            if ids:
                return (
                    "Reply with the **number** of the job you want to "
                    f"focus on (1–{len(ids)}). Or type **cancel** "
                    "to start over."
                )

        # In tailor phase: surface the per-job actions.
        if journey.phase == PHASE_TAILOR:
            return (
                "For this job I can:\n"
                "  - **letter** — draft a DACH-norm motivation letter\n"
                "  - **consult** — suggest CV enhancements for this JD\n"
                "  - **save** — mark interested and wrap up\n\n"
                "Which?"
            )

        # In letter / cv_consult: short menu.
        if journey.phase in (PHASE_LETTER, PHASE_CV_CONSULT):
            return "Reply **save** to wrap up, or **letter** / **consult** to see the other option."

        # No active journey OR fresh after sign-in: surface 3 starter
        # actions, not the abstract "help" command.
        return (
            "I'm not sure what you mean by that — here's what I can "
            "do right now:\n"
            "  - **find a job** — I'll ask a few questions and "
            "search for you\n"
            '  - **add a company** like *"watch Charité, career '
            'page karriere.charite.de"*\n'
            "  - **build my CV** — guided sectional walk\n\n"
            "Or type **help** for the full command list."
        )

    def _journey_load(self, user_id: str):
        from company_discovery.journey import UserJourney

        profile = self.profile_for(user_id)
        chat_state = profile.chat_state or {}
        return UserJourney.from_dict(chat_state.get("journey"))

    def _journey_save(self, user_id: str, journey) -> None:
        profile = self.profile_for(user_id)
        chat_state = dict(profile.chat_state or {})
        chat_state["journey"] = journey.to_dict()
        profile.chat_state = chat_state
        self.repository.save_user_profile(profile)

    def _journey_apply_profile_updates(self, user_id: str, updates: dict) -> None:
        if not updates:
            return
        profile = self.profile_for(user_id)
        for k, v in updates.items():
            if hasattr(profile, k):
                setattr(profile, k, v)
        self.repository.save_user_profile(profile)

    def _journey_ai_caller(self, user_id: str):
        """Return a callable(system, user) -> str | None that asks the
        configured AI provider, or None if no AI is available."""
        profile = self.profile_for(user_id)
        provider = self.ai_provider_for(user_id)
        if provider is None or provider.provider_id == "manual":
            return None
        if not _ai_consent_satisfied(profile, provider):
            return None
        from company_discovery.analysis import _dispatch_provider

        def _call(system: str, user_msg: str) -> str | None:
            # We bundle system + user into one prompt since the
            # existing _dispatch_provider takes a single string. The
            # provider adapters split on \n\n correctly. Errors are
            # swallowed; journey state machine falls back to template.
            prompt = f"{system}\n\n{user_msg}"
            try:
                result = _dispatch_provider(prompt, provider, "")
                if result.status != "completed":
                    return None
                return result.output
            except Exception:  # noqa: BLE001 - best-effort path; failure must not break the caller
                return None

        return _call

    def chat_handler_start_job_journey(self, user_id: str, args: dict) -> dict:
        from company_discovery.journey import PHASE_GREET, UserJourney

        # Fresh journey — overwrite whatever the user had before.
        journey = UserJourney(phase=PHASE_GREET)
        self._journey_save(user_id, journey)
        self.log_analytics(user_id, "chat_cmd", {"name": "start_job_journey"})
        # Run advance() once so the first reply is the welcome + first
        # discover question.
        return self.chat_journey_step(user_id, "")

    def chat_journey_step(self, user_id: str, message: str) -> dict:
        """Process one user message through the journey state machine.

        Called by the HTTP chat-message handler whenever the user has
        an active journey in progress. Returns the standard chat
        handler result shape.
        """
        from company_discovery.journey import advance

        journey = self._journey_load(user_id)
        profile = self.profile_for(user_id)
        has_cv = bool((profile.cv_text or "").strip())
        ai_caller = self._journey_ai_caller(user_id)
        result = advance(
            journey,
            message,
            has_existing_cv=has_cv,
            ai_available=ai_caller is not None,
            ai_caller=ai_caller,
            diagnostic_engine=self.diagnostic_engine,
        )
        if result.profile_updates:
            self._journey_apply_profile_updates(user_id, result.profile_updates)
        # Bug F Option B (Loop 10.2, 2026-05-20): journey-emitted
        # analytics events. Each (name, payload) entry gets a
        # log_analytics call so the OQ-2 telemetry hook lands on
        # the same channel as other journey instrumentation.
        for event_name, event_payload in (result.analytics_events or []):
            try:
                self.log_analytics(user_id, event_name, event_payload)
            except Exception:  # noqa: BLE001 - telemetry must never break chat
                pass
        if result.persist:
            self._journey_save(user_id, result.journey)
        # When the journey asks us to run a search, dispatch to
        # find_jobs with the merged target_roles list. The first role
        # is the user's stated one; aggregator search uses it as the
        # primary query.
        if result.run_search_with:
            target_roles = result.run_search_with.get("target_roles") or []
            primary_query = target_roles[0] if target_roles else "job"
            location = result.run_search_with.get("location") or None
            # Aggregators can fail (network, 5xx, rate-limit). The
            # journey must NOT crash on those — return a friendly
            # explanation and mark done so the user can try again.
            try:
                search_result = self.chat_handler_find_jobs(
                    user_id,
                    {"query": primary_query, "location": location},
                )
            except Exception as exc:  # noqa: BLE001 - best-effort path; failure must not break the caller
                self.log_analytics(
                    user_id, "chat_journey_step", {"phase": "search", "searchError": str(exc)[:200]}
                )
                journey_err = self._journey_load(user_id)
                from company_discovery.journey import PHASE_DONE

                journey_err.phase = PHASE_DONE
                self._journey_save(user_id, journey_err)
                return {
                    "ok": False,
                    "message": (
                        "The job search hit a snag (aggregator "
                        "issue). Try again in a minute — type "
                        "`find a job` to restart."
                    ),
                    "journeyPhase": "done",
                    "totalJobs": 0,
                }
            jobs = search_result.get("jobs") or []
            # Cluster by category using the new R17.5 helper.
            from company_discovery.journey import (
                MAX_SEARCH_JOBS_CARRIED,
                PHASE_DONE,
                PHASE_REVIEW,
                cluster_jobs,
            )

            clusters = cluster_jobs(jobs)
            categorized: dict[str, list[str]] = {}
            jobs_by_id: dict[str, dict] = {}
            # Hard cap on what we carry forward in the journey blob to
            # keep profile.chat_state from growing unboundedly when
            # the user re-searches across sessions.
            carried = 0
            for category, items in clusters.items():
                ids: list[str] = []
                for j in items:
                    if carried >= MAX_SEARCH_JOBS_CARRIED:
                        break
                    job_id = j.get("url") or j.get("title") or ""
                    if not job_id:
                        continue
                    ids.append(job_id)
                    # Persist only the small fields we render later
                    # (title / company / location / url / source).
                    jobs_by_id[job_id] = {
                        "title": (j.get("title") or "")[:200],
                        "company": (j.get("company") or "")[:120],
                        "location": (j.get("location") or "")[:120],
                        "url": (j.get("url") or "")[:300],
                        "source": (j.get("source") or "")[:60],
                    }
                    carried += 1
                if ids:
                    categorized[category] = ids
                if carried >= MAX_SEARCH_JOBS_CARRIED:
                    break
            journey2 = self._journey_load(user_id)
            journey2.search_results_by_category = categorized
            journey2.search_jobs_by_id = jobs_by_id
            if not jobs:
                # PART 6 Bug C piece 1-4 (2026-05-20): never-implicit-
                # done + cache-only diagnostic + persona-aware widening
                # affordances + auto-relax mode persistence.
                journey2.phase = PHASE_REVIEW
                # Piece 4: auto-mode persists across the search
                # dispatch. If the user was in auto_relax_offering
                # when this search fired (i.e., they said "yes" to
                # the last suggestion), re-enter auto-mode with the
                # next suggestion. Otherwise default to the menu.
                if journey2.auto_relax_active:
                    from company_discovery.widening import (
                        next_auto_relax_suggestion,
                    )

                    # Recompute new_laterals + next suggestion. The
                    # just-applied widening is already in
                    # applied_widenings (apply_widening did that).
                    laterals_count = 0
                    try:
                        from company_discovery.journey import (
                            _compute_new_laterals,
                        )

                        laterals_count = len(_compute_new_laterals(journey2))
                    except Exception:  # noqa: BLE001
                        laterals_count = 0
                    next_a = next_auto_relax_suggestion(
                        journey2, new_laterals_count=laterals_count
                    )
                    if next_a is not None:
                        journey2.auto_relax_offered_id = next_a.id
                        journey2.review_substate = "auto_relax_offering"
                    else:
                        # Auto-relax exhausted — exit auto-mode and
                        # show the menu (which by now will have
                        # retry + give-up only).
                        journey2.auto_relax_active = False
                        journey2.auto_relax_offered_id = ""
                        journey2.review_substate = "empty"
                else:
                    journey2.review_substate = "empty"
                # Piece 2: compute diagnostic via cache-only engine.
                diag = self.diagnostic_engine.generate(
                    role_text=(
                        (journey2.target_roles[0] if journey2.target_roles else "")
                        or ""
                    ),
                    location=journey2.location or None,
                    filters={
                        "remote_required": journey2.remote_required,
                        "salary_floor": journey2.salary_floor,
                        "company_size": journey2.company_size or None,
                    },
                )
                journey2.diagnostic_text = diag or ""
                # Piece 3: classify visa-constraint from persona fixture
                # so the widening menu can order affordances + surface
                # the Ausländerbehörde caveat. Look up the user's
                # friction_class → PersonaFixture → residency_status,
                # then classify. Bug F Option B (Loop 10.3, 2026-05-20):
                # the fixture lookup uses profile.friction_class (set
                # by the cv_check classifier hook) NOT profile.persona_id
                # (which only ever resolves to the 15-industry
                # registry, never to a fixture slug — Loop 9.2
                # investigation). Defaults to False when friction_class
                # is "" (classifier didn't resolve) → unconstrained UX.
                from company_discovery.widening import (
                    classify_visa_constraint,
                )
                from company_discovery.analysis import _persona_fixture_for

                try:
                    user_profile = self.profile_for(user_id)
                except Exception:  # noqa: BLE001 - empty-state path; failure must not break the caller
                    user_profile = None
                fclass = (
                    user_profile.friction_class
                    if user_profile and getattr(user_profile, "friction_class", None)
                    else ""
                )
                fixture = _persona_fixture_for(fclass)
                residency = getattr(fixture, "residency_status", "") or ""
                journey2.visa_constrained = classify_visa_constraint(residency)
            else:
                journey2.phase = PHASE_REVIEW
                journey2.review_substate = ""  # clear if previously set
                journey2.diagnostic_text = ""
                # A successful search clears the widening ledger AND
                # auto-relax state — the next empty-state recovery
                # (if it happens later) starts fresh per operator
                # decision 2026-05-20.
                journey2.applied_widenings = []
                journey2.proposed_laterals = []
                journey2.auto_relax_active = False
                journey2.auto_relax_declined = []
                journey2.auto_relax_offered_id = ""
            self._journey_save(user_id, journey2)
            if not jobs:
                # Piece 4: if dispatcher set substate to
                # auto_relax_offering, render the auto-relax
                # suggestion text directly so the user sees the
                # next prompt without an extra round-trip.
                if journey2.review_substate == "auto_relax_offering":
                    from company_discovery.journey import (
                        _compute_new_laterals,
                        _probe_auto_relax_count,
                    )
                    from company_discovery.widening import (
                        TRY_LATERALS,
                        format_auto_relax_suggestion,
                        next_auto_relax_suggestion,
                        probe_lateral_counts,
                    )

                    new_laterals = _compute_new_laterals(journey2)
                    next_a = next_auto_relax_suggestion(
                        journey2, new_laterals_count=len(new_laterals)
                    )
                    if next_a is not None:
                        lateral_options = (
                            new_laterals if next_a.id == TRY_LATERALS else None
                        )
                        count = _probe_auto_relax_count(
                            journey2,
                            next_a,
                            lateral_options=lateral_options,
                            engine=self.diagnostic_engine,
                        )
                        lateral_counts = (
                            probe_lateral_counts(
                                journey2,
                                lateral_options or [],
                                engine=self.diagnostic_engine,
                            )
                            if next_a.id == TRY_LATERALS
                            else None
                        )
                        summary_msg = format_auto_relax_suggestion(
                            next_a,
                            lateral_options=lateral_options,
                            lateral_counts=lateral_counts,
                            count=count,
                        )
                    else:
                        from company_discovery.journey import (
                            _format_review_empty_reply,
                        )

                        summary_msg = _format_review_empty_reply(
                            journey2,
                            diagnostic_text=journey2.diagnostic_text or None,
                            engine=self.diagnostic_engine,
                        )
                else:
                    from company_discovery.journey import (
                        _format_review_empty_reply,
                    )

                    summary_msg = _format_review_empty_reply(
                        journey2,
                        diagnostic_text=journey2.diagnostic_text or None,
                        engine=self.diagnostic_engine,
                    )
            else:
                jobs_summary = "\n".join(
                    f"  - **{c}**: {len(ids)} job(s)" for c, ids in categorized.items()
                )
                # Loop 16 (2026-05-20): Gate 6.5 partial-failure
                # transparency. chat_handler_find_jobs returned
                # `erroredOutcomes` per Loop 16 plumbing; surface
                # the same banner here so the journey-driven search
                # has parity with the slash-/find path.
                errored_outcomes = search_result.get("erroredOutcomes") or []
                partial_banner = ""
                if errored_outcomes:
                    total_outcomes = len(errored_outcomes) + max(
                        0, len(jobs) and 1
                    )  # we don't have total here; render relative count only
                    partial_banner = (
                        f"_(Some providers were temporarily "
                        f"unavailable — {len(errored_outcomes)} "
                        f"reported errors. Results below are from "
                        f"the working providers.)_\n\n"
                    )
                summary_msg = (
                    partial_banner
                    + f"**Found {len(jobs)} job(s) total.**\n"
                    + f"{jobs_summary}\n\n"
                    + "Reply with a **category name** to see the jobs in it."
                )
            # R21.x: include `jobs` + `navigateTo` so the client can
            # render the search-results canvas AFTER a journey-driven
            # search. Without these, the user finishes the journey
            # questions and the right panel stays empty — bug found
            # in the post-R21 audit. Flatten jobs_by_id into the
            # ordered list the client renderer expects.
            ordered_jobs = []
            for category in categorized:
                for jid in categorized[category]:
                    j = jobs_by_id.get(jid) or {}
                    if j:
                        ordered_jobs.append(j)
            return {
                "ok": True,
                "message": f"{result.reply}\n\n{summary_msg}",
                "totalJobs": len(jobs),
                "journeyPhase": journey2.phase,
                "jobs": ordered_jobs,
                "categories": list(categorized.keys()),
                "navigateTo": "searchResults" if ordered_jobs else None,
            }
        # Journey state machine can ask the chat layer to dispatch a
        # registered command (e.g. draft_motivation_letter). Typed
        # field, not a string sentinel — keeps implementation detail
        # out of the user-facing reply and prevents the user's text
        # from ever being interpreted as a dispatch.
        if result.invoke_command:
            cmd_name = result.invoke_command
            # Whitelist the commands the journey can invoke; the chat
            # router's full registry has destructive commands that
            # should never bypass the confirmation gate.
            allowed = {"draft_motivation_letter", "suggest_cv_enhancements"}
            if cmd_name not in allowed:
                self.log_analytics(
                    user_id,
                    "chat_journey_step",
                    {"phase": result.journey.phase, "invokeRejected": cmd_name},
                )
                return {
                    "ok": False,
                    "message": (
                        f"Sorry — I can't auto-invoke `{cmd_name}` from inside the journey."
                    ),
                    "journeyPhase": result.journey.phase,
                }
            cmd_result = self.chat_execute_command(user_id, cmd_name, {})
            self.log_analytics(
                user_id, "chat_journey_step", {"phase": result.journey.phase, "invoked": cmd_name}
            )
            return {
                "ok": cmd_result.get("ok", True),
                "message": cmd_result.get("message", "(done)"),
                "journeyPhase": result.journey.phase,
                "done": result.done,
                "invoked": cmd_name,
                "letter": cmd_result.get("letter"),
                "suggestions": cmd_result.get("suggestions"),
            }
        self.log_analytics(user_id, "chat_journey_step", {"phase": result.journey.phase})
        return {
            "ok": True,
            "message": result.reply,
            "journeyPhase": result.journey.phase,
            "done": result.done,
        }

    def chat_handler_accept_cv_text(self, user_id: str, args: dict) -> dict:
        cv_text = (args.get("cvText") or "").strip()
        if len(cv_text) < 40:
            return {"ok": False, "message": "That's very short — paste the full CV text."}
        profile = self.profile_for(user_id)
        profile.cv_text = cv_text
        self.repository.save_user_profile(profile)
        self.log_analytics(user_id, "chat_cmd", {"name": "accept_cv_text", "chars": len(cv_text)})
        return {
            "ok": True,
            "message": (
                f"Saved **{len(cv_text)} chars** to your profile. "
                "You can `/tailor` it for a specific job any time."
            ),
        }

    # build_cv_via_chat — sectional walk handled by the journey;
    # this entry point sets cv_status='building' inside the journey
    # state then runs one journey step so the user sees the first
    # question immediately.
    def chat_handler_show_view(self, user_id: str, args: dict) -> dict:
        """Navigate-style command. Resolves the user's free-text
        target ("watchlist", "queue", "today", "applications", …) to
        the matching canonical view id, returns navigateTo. Read-only
        — no DB write, no confirmation gate. The client honours
        navigateTo by clicking the corresponding nav-item."""
        raw = (args.get("target") or "").strip().lower()
        # Map synonyms → view id.
        synonyms: dict[str, tuple[str, ...]] = {
            "dashboard": (
                "dashboard",
                "today",
                "home",
                "heute",
                "startseite",
                "übersicht",
                "uebersicht",
            ),
            "companies": (
                "companies",
                "watchlist",
                "watch list",
                "company list",
                "firmen",
                "unternehmen",
            ),
            "jobs": (
                "jobs",
                "queue",
                "imported",
                "saved jobs",
                "job list",
                "stellen",
                "warteschlange",
            ),
            "brief": (
                "brief",
                "briefcase",
                "applications",
                "tracker",
                "bewerbungen",
                "anwendungen",
            ),
            "settings": ("settings", "profile", "preferences", "config", "einstellungen", "profil"),
            "cvBuilder": ("cvbuilder", "cv builder", "cv-builder", "lebenslauf"),
            "assistant": ("assistant", "chat"),
        }
        target_id = ""
        for view_id, words in synonyms.items():
            if raw in words or any(w in raw for w in words):
                target_id = view_id
                break
        if not target_id:
            allowed = ", ".join(synonyms.keys())
            return {
                "ok": False,
                "message": (f"I don't know which view {raw!r} maps to. Try one of: {allowed}."),
            }
        self.log_analytics(user_id, "chat_cmd", {"name": "show_view", "view": target_id})
        return {"ok": True, "navigateTo": target_id, "message": f"Opening **{target_id}**."}

    def chat_handler_download_cv(self, user_id: str, args: dict) -> dict:
        """Surface the print-view URL for the user's CV. The user
        clicks it → browser opens /api/cv/print?autoprint=1 → print
        dialog → Save as PDF. Read-only; no DB write."""
        profile = self.profile_for(user_id)
        cv_text = (profile.cv_text or "").strip()
        if not cv_text:
            return {
                "ok": False,
                "message": (
                    "There's no CV on your profile yet. Type "
                    "**build my CV** to create one (5 quick "
                    "questions), or paste your CV here."
                ),
            }
        self.log_analytics(user_id, "chat_cmd", {"name": "download_cv", "cvChars": len(cv_text)})
        return {
            "ok": True,
            "message": (
                "Your CV is ready to print. **Click here to "
                "open the print view:** "
                "[Download CV as PDF](/api/cv/print?autoprint=1)\n\n"
                "Your browser's print dialog will open — pick "
                "*Save as PDF* and you're set."
            ),
            "navigateTo": "cvPrint",
        }

    def chat_handler_delete_account(self, user_id: str, args: dict) -> dict:
        """Start GDPR right-to-erasure. We never erase in-chat — the
        flow always goes through the emailed confirmation link + a
        7-day grace window so the user can recover from a typo or a
        compromised session."""
        typed_email = (args.get("email") or "").strip().casefold()
        user = self.auth_store.get_user(user_id)
        if user is None:
            return {"ok": False, "message": "Auth state lost — please sign in again."}
        if typed_email != (user.email or "").casefold():
            return {
                "ok": False,
                "message": (
                    "That email doesn't match the one on your "
                    "account. Deletion not started. Try again "
                    "if you want to proceed."
                ),
            }
        try:
            ticket = self.request_account_deletion(
                user=user,
                reason="Requested via chat",
            )
        except Exception as exc:  # noqa: BLE001 - best-effort path; failure must not break the caller
            self.log_analytics(
                user_id,
                "chat_cmd",
                {"name": "delete_account", "status": "error", "error": str(exc)[:200]},
            )
            return {
                "ok": False,
                "message": (
                    "Couldn't start deletion right now — "
                    "please try again in a few minutes or "
                    "reach out via support."
                ),
            }
        self.log_analytics(user_id, "chat_cmd", {"name": "delete_account", "ticketId": ticket.id})
        return {
            "ok": True,
            "message": (
                "Deletion started. Check your email for a "
                "confirmation link — click it within 7 days to "
                "schedule the deletion. After confirming, a "
                "second 7-day grace window starts before your "
                "data is erased; you can cancel any time in "
                "Settings → Privacy."
            ),
        }

    def chat_handler_suggest_cv_enhancements(self, user_id: str, args: dict) -> dict:
        """Compare the user's CV against their picked job's JD and
        surface 3-5 gap-questions they can answer to strengthen
        their CV. Never auto-edits the CV — the user has the final
        say on every addition."""
        from company_discovery.cv_consult import consult

        journey = self._journey_load(user_id)
        if not journey.picked_job_id:
            return {
                "ok": False,
                "message": (
                    "Pick a job first (via the journey: type "
                    "`find a job`, drill into a category, pick a "
                    "number)."
                ),
            }
        job = journey.search_jobs_by_id.get(journey.picked_job_id, {})
        if not job:
            return {"ok": False, "message": "Picked job missing — type /start to refresh."}
        profile = self.profile_for(user_id)
        cv_text = (profile.cv_text or "").strip()
        if not cv_text:
            return {
                "ok": False,
                "message": (
                    "I need a CV to consult. Type "
                    "**build my CV** and I'll walk you through "
                    "5 quick questions, or paste your CV here."
                ),
            }
        ai_caller = self._journey_ai_caller(user_id)
        gaps, used_ai = consult(
            job=job,
            cv_text=cv_text,
            ai_caller=ai_caller,
        )
        self.log_analytics(
            user_id,
            "chat_cmd",
            {
                "name": "suggest_cv_enhancements",
                "jobUrl": job.get("url", "")[:120],
                "gapCount": len(gaps),
                "aiUsed": used_ai,
            },
        )
        if not gaps:
            return {
                "ok": True,
                "message": (
                    "Your CV already covers the visible JD "
                    "requirements. No gap suggestions for this "
                    "posting."
                ),
                "suggestions": [],
            }
        banner = (
            ""
            if used_ai
            else "_(I'm running without an AI right now — these "
            "are heuristic keyword diffs. Configure a "
            "provider for richer suggestions.)_\n\n"
        )
        lines = [f"  {i}. **{g['gap']}** — {g['question']}" for i, g in enumerate(gaps, 1)]
        listing = "\n".join(lines)
        return {
            "ok": True,
            "message": (
                f"{banner}Here's what I'd strengthen on your CV "
                f"for **{job.get('title', '')}** at "
                f"**{job.get('company', '')}**:\n\n"
                f"{listing}\n\n"
                "Reply to each one with your one-sentence story "
                "(or 'skip' if you don't have it). Type **save** "
                "when you're done to wrap up."
            ),
            "suggestions": gaps,
        }

    def chat_handler_draft_motivation_letter(self, user_id: str, args: dict) -> dict:
        """Draft a DACH-norm motivation letter for the user's picked
        job. The job comes from the journey state (R17.5 stored
        search_jobs_by_id). When no AI is configured, returns the
        templated skeleton with an honest banner — the journey never
        gets stuck."""
        from company_discovery.motivation_letter import (
            draft_with_ai,
            templated_fallback,
        )

        journey = self._journey_load(user_id)
        if not journey.picked_job_id:
            return {
                "ok": False,
                "message": (
                    "I don't know which job to write about yet. "
                    "Pick one from the journey first (type "
                    "`find a job`, drill into a category, then "
                    "pick a number)."
                ),
            }
        job = journey.search_jobs_by_id.get(journey.picked_job_id, {})
        if not job:
            return {
                "ok": False,
                "message": "Picked job's details are missing — try /start to refresh.",
            }
        profile = self.profile_for(user_id)
        cv_text = (profile.cv_text or "").strip()
        if not cv_text:
            return {
                "ok": False,
                "message": (
                    "I need a CV to draft a letter. Type "
                    "**build my CV** and I'll walk you through "
                    "5 quick questions, or paste your full CV "
                    "text here right now."
                ),
            }
        ai_caller = self._journey_ai_caller(user_id)
        letter = draft_with_ai(
            job=job,
            cv_text=cv_text,
            user_name="",
            user_location=profile.location or "",
            ai_caller=ai_caller,
        )
        if not letter:
            letter = templated_fallback(
                job=job,
                user_name="",
                user_location=profile.location or "",
            )
        # Persist to the journey for the next phase to consult against.
        # We don't auto-write to imported_job here because the user
        # hasn't imported the job yet — that's a separate /save step.
        self.log_analytics(
            user_id,
            "chat_cmd",
            {
                "name": "draft_motivation_letter",
                "jobUrl": job.get("url", "")[:120],
                "aiUsed": ai_caller is not None,
                "chars": len(letter),
            },
        )
        return {
            "ok": True,
            "message": (
                f"Here's the draft for **{job.get('title', '')}** "
                f"at **{job.get('company', '')}**:\n\n"
                f"---\n\n{letter}\n\n---\n\n"
                "Reply **save** to keep it on your applications, or "
                "**consult** to get CV enhancement ideas for this JD."
            ),
            "letter": letter,
            "letterChars": len(letter),
        }

    def chat_handler_build_cv_via_chat(self, user_id: str, args: dict) -> dict:
        """Start the sectional CV-build flow. Works from ANY journey
        phase — previous restriction (only PHASE_CV_CHECK) prevented
        a user stuck in PHASE_TAILOR from creating a CV when they
        needed one for the letter draft. R79.3 fix."""
        from company_discovery.journey import (
            _CV_BUILD_ORDER,
            PHASE_CV_CHECK,
            cv_build_prompt_for,
        )

        # Reset journey to a fresh CV_CHECK state regardless of where
        # the user was before. Any in-flight search results are
        # preserved by NOT clearing search_jobs_by_id — but the
        # phase changes so the discover/build flow runs cleanly.
        journey = self._journey_load(user_id)
        journey.phase = PHASE_CV_CHECK
        journey.cv_status = "building"
        journey.cv_build_step = _CV_BUILD_ORDER[0]
        journey.cv_build_answers = {}
        self._journey_save(user_id, journey)
        self.log_analytics(user_id, "chat_cmd", {"name": "build_cv_via_chat"})
        return {
            "ok": True,
            "message": (
                "OK — 5 quick questions and you'll have a CV "
                "ready. " + cv_build_prompt_for(_CV_BUILD_ORDER[0])
            ),
        }

    def chat_execute_command(self, user_id: str, command_name: str, args: dict) -> dict:
        """Dispatch a confirmed command. The router never calls
        handlers directly — execution always goes through this single
        choke point so we can centralise audit logging + future
        permission checks."""
        handlers = {
            "add_company": self.chat_handler_add_company,
            "create_saved_search": self.chat_handler_create_saved_search,
            "find_jobs": self.chat_handler_find_jobs,
            "update_profile": self.chat_handler_update_profile,
            "mark_applied": self.chat_handler_mark_applied,
            "tailor_cv": self.chat_handler_tailor_cv,
            "run_saved_search": self.chat_handler_run_saved_search,
            "set_persona": self.chat_handler_set_persona,
            "delete_company": self.chat_handler_delete_company,
            "open_cv_builder": self.chat_handler_open_cv_builder,
            "start_job_journey": self.chat_handler_start_job_journey,
            "accept_cv_text": self.chat_handler_accept_cv_text,
            "build_cv_via_chat": self.chat_handler_build_cv_via_chat,
            "draft_motivation_letter": self.chat_handler_draft_motivation_letter,
            "suggest_cv_enhancements": self.chat_handler_suggest_cv_enhancements,
            "show_view": self.chat_handler_show_view,
            "delete_account": self.chat_handler_delete_account,
            "download_cv": self.chat_handler_download_cv,
            "help": self.chat_handler_help,
        }
        if command_name not in handlers:
            return {"ok": False, "message": f"Unknown command: {command_name}."}
        return handlers[command_name](user_id, args)

    # ---------------- CV builder session storage ----------------
    #
    # In-memory dict keyed by user_id. Lives for the lifetime of the
    # server process. A future iteration will persist to a column on
    # user_profile so the state survives restarts; for now restart =
    # the user starts the builder over. The state is JSON-serialisable
    # via CvBuilderState.to_dict so persistence is a 1-line addition.
    # ClassVar — intentional process-wide CV-builder session map.
    _cv_builder_sessions: ClassVar[dict[str, CvBuilderState]] = {}

    def cv_builder_state_for(self, user_id: str) -> CvBuilderState:
        if user_id not in self._cv_builder_sessions:
            self._cv_builder_sessions[user_id] = CvBuilderState()
        return self._cv_builder_sessions[user_id]

    def cv_builder_reset(self, user_id: str) -> None:
        self._cv_builder_sessions.pop(user_id, None)

    def cv_builder_format_section(
        self,
        user_id: str,
        section_id: str,
        raw_field: str,
        raw_text: str,
    ) -> tuple[str, float, bool]:
        """Run the bounded AI-format prompt for ``raw_text``. Returns
        (output, fact_ratio, was_accepted). If the AI is not configured
        or the fact ratio is below threshold, we return the raw text
        unchanged with ``was_accepted=False`` so the caller stores the
        user's words rather than an unreliable AI rewrite.
        """
        provider = self.ai_provider_for(user_id)
        # Manual / unconfigured provider — no AI call. Return raw.
        if provider.invocation_mode == "manual" or provider.provider_id == "manual":
            return raw_text, 1.0, False
        prompt = build_format_prompt(section_id, raw_text)
        # We dispatch via the existing CLI/API adapter. Per AI consent
        # policy, only invoke when the user has consented.
        profile = self.profile_for(user_id)
        if not _ai_consent_satisfied(profile, provider):
            return raw_text, 1.0, False
        from company_discovery.analysis import _dispatch_provider

        result = _dispatch_provider(prompt, provider, "")
        if result.status != "completed" or not result.output:
            return raw_text, 1.0, False
        ai_output = result.output.strip()
        accept, ratio = validate_ai_format_output(raw_text, ai_output)
        if not accept:
            return raw_text, ratio, False
        return ai_output, ratio, True

    def application_outcomes_summary(self, user_id: str, *, threshold: int = 5) -> dict[str, Any]:
        """Reply-rate analytics for the dashboard. We only surface it to
        the user once they have ``threshold`` applications in flight —
        below that the rate is too noisy to interpret. ``ready=False``
        below the threshold so the frontend can hide the card.

        An "application" is any imported job that has been moved off
        the default ``saved`` status. ``replied`` is the user-confirmed
        ``replied_at`` flag (Phase 4 #42)."""

        applied_statuses = {"interested", "applied", "interview", "rejected", "archived"}
        total_applications = 0
        replied = 0
        for job in self.repository.list_imported_jobs(user_id):
            if job.application_status in applied_statuses:
                total_applications += 1
                if job.replied_at is not None:
                    replied += 1
        rate = (replied / total_applications) if total_applications else 0.0
        return {
            "totalApplications": total_applications,
            "replied": replied,
            "replyRate": round(rate, 4),
            "threshold": threshold,
            "ready": total_applications >= threshold,
        }

    def set_share_enabled(self, user_id: str, imported_job_id: str, enabled: bool) -> ImportedJob:
        imported = self.repository.imported_jobs.get(imported_job_id)
        if imported is None or imported.user_id != user_id:
            raise KeyError(imported_job_id)
        imported.share_enabled = bool(enabled)
        imported.updated_at = now_utc()
        self.repository.save_imported_job(imported)
        self.log_analytics(
            user_id,
            "share_link_toggled",
            {"importedJobId": imported_job_id, "enabled": bool(enabled)},
        )
        return imported

    def update_application_state(
        self,
        user_id: str,
        imported_job_id: str,
        payload: dict[str, Any],
    ) -> ImportedJob:
        imported = self.repository.imported_jobs.get(imported_job_id)
        if imported is None or imported.user_id != user_id:
            raise KeyError(imported_job_id)
        previous_status = imported.application_status
        previous_stage = imported.interview_stage
        history_note = None
        if "applicationStatus" in payload:
            status = payload["applicationStatus"]
            if status not in APPLICATION_STATUSES:
                raise ValueError("invalid_application_status")
            imported.application_status = status
        for src, dst in (
            ("applicationNotes", "application_notes"),
            ("coverLetterDraft", "cover_letter_draft"),
            ("nextAction", "next_action"),
        ):
            if src in payload:
                value = payload[src]
                setattr(imported, dst, str(value) if value is not None else None)
        if "interviewStage" in payload or "interview_stage" in payload:
            from company_discovery.models import INTERVIEW_STAGES

            raw_stage = payload.get("interviewStage", payload.get("interview_stage"))
            if raw_stage in (None, ""):
                imported.interview_stage = None
            else:
                stage = str(raw_stage)
                if stage not in INTERVIEW_STAGES:
                    raise ValueError("invalid_interview_stage")
                imported.interview_stage = stage
        if "reminderAt" in payload or "reminder_at" in payload:
            raw_reminder = payload.get("reminderAt", payload.get("reminder_at"))
            if not raw_reminder:
                imported.reminder_at = None
            else:
                try:
                    imported.reminder_at = datetime.fromisoformat(
                        str(raw_reminder).replace("Z", "+00:00")
                    )
                except ValueError as err:
                    raise ValueError("invalid_reminder_at") from err
        if "replied" in payload or "repliedAt" in payload or "replied_at" in payload:
            # Accept either a boolean checkbox (`replied`) or a literal
            # timestamp. ``replied=true`` stamps now() if not already
            # set; ``replied=false`` clears it. Idempotent: re-sending
            # the same boolean does not overwrite an existing stamp.
            previous_replied_at = imported.replied_at
            if "replied" in payload:
                wants = bool(payload.get("replied"))
                if wants and imported.replied_at is None:
                    imported.replied_at = now_utc()
                elif not wants:
                    imported.replied_at = None
            else:
                raw_replied = payload.get("repliedAt", payload.get("replied_at"))
                if not raw_replied:
                    imported.replied_at = None
                else:
                    try:
                        imported.replied_at = datetime.fromisoformat(
                            str(raw_replied).replace("Z", "+00:00")
                        )
                    except ValueError as err:
                        raise ValueError("invalid_replied_at") from err
            # CV-variant attribution (#44): on the transition from None
            # to a real timestamp, mark the most recent variant as the
            # one that earned the reply. On clearing, undo the flag so
            # the analytics stay clean if the user toggled by mistake.
            variants = list(imported.cv_variants or [])
            if previous_replied_at is None and imported.replied_at is not None and variants:
                variants[-1] = {**variants[-1], "attributedReply": True}
                imported.cv_variants = variants
            elif imported.replied_at is None and previous_replied_at is not None and variants:
                imported.cv_variants = [{**v, "attributedReply": False} for v in variants]
        if "historyNote" in payload:
            history_note = str(payload.get("historyNote") or "").strip() or None
        if "documentsChecklist" in payload:
            checklist = payload["documentsChecklist"]
            if not isinstance(checklist, list):
                raise ValueError("invalid_documents_checklist")
            cleaned: list[dict[str, Any]] = []
            for item in checklist:
                if not isinstance(item, dict):
                    continue
                cleaned.append(
                    {
                        "label": str(item.get("label") or "").strip(),
                        "complete": bool(item.get("complete")),
                    }
                )
            imported.documents_checklist = cleaned
        if (
            previous_status != imported.application_status
            or previous_stage != imported.interview_stage
            or history_note
        ):
            imported.application_history = list(imported.application_history or [])
            imported.application_history.append(
                {
                    "at": now_utc().isoformat(),
                    "status": imported.application_status,
                    "stage": imported.interview_stage,
                    "note": history_note,
                }
            )
            # Cap the timeline so it doesn't grow unbounded.
            if len(imported.application_history) > 50:
                imported.application_history = imported.application_history[-50:]
        return self.repository.save_imported_job(imported)

    def apply_watchlist_template(self, user_id: str, template_id: str) -> dict[str, Any]:
        template = get_template(template_id)
        if template is None:
            raise ValueError("unknown_template")
        added: list[Company] = []
        skipped: list[dict[str, str]] = []
        existing = self.repository.list_companies(user_id)
        existing_hosts = {urlparse(c.website_url).hostname or "" for c in existing}
        for entry in template.companies:
            host = urlparse(entry.website_url).hostname or ""
            if host and host in existing_hosts:
                skipped.append({"name": entry.name, "reason": "already_in_watchlist"})
                continue
            company = self.service.create_company(
                user_id=user_id,
                name=entry.name,
                website_url=entry.website_url,
                career_page_url=entry.career_page_url,
                sector=entry.sector,
                notes=f"Added from template '{template.label}'.",
                watch_enabled=True,
            )
            added.append(company)
        self.log_analytics(
            user_id, "watchlist_template_applied", {"templateId": template_id, "added": len(added)}
        )
        return {"added": added, "skipped": skipped, "templateId": template_id}

    def save_saved_search(self, user_id: str, payload: dict[str, Any]) -> SavedSearch:
        name = str(payload.get("name") or "").strip() or "Untitled search"
        target_roles = payload.get("targetRoles") or payload.get("target_roles") or []
        if isinstance(target_roles, str):
            target_roles = [item.strip() for item in target_roles.split(",") if item.strip()]
        existing_id = payload.get("id")
        existing = self.repository.saved_searches.get(existing_id) if existing_id else None
        if existing is not None and existing.user_id != user_id:
            raise KeyError(existing_id)
        # Tier limit (#24): refuse to *create* a new search past the
        # plan cap. Edits to an existing one are unaffected so the user
        # can keep curating the searches they already have.
        if existing is None:
            self.assert_can_add_saved_search(user_id)
        record = existing or SavedSearch(user_id=user_id, name=name)
        record.name = name
        record.target_roles = list(target_roles)
        record.industry = str(payload.get("industry") or "Healthcare")
        record.location = payload.get("location")
        sectors = payload.get("sectors") or []
        if isinstance(sectors, str):
            sectors = [item.strip() for item in sectors.split(",") if item.strip()]
        record.sectors = list(sectors)
        record.notes = payload.get("notes")
        return self.repository.save_saved_search(record)

    def delete_saved_search(self, user_id: str, search_id: str) -> None:
        self.repository.delete_saved_search(user_id, search_id)

    def discover_companies(
        self,
        *,
        target_roles: list[str],
        industry: str,
        location: str | None,
        limit: int = 12,
        persona_id: str | None = None,
    ) -> list[dict[str, Any]]:
        results = self.discovery_engine.discover(
            target_roles=target_roles,
            industry=industry,
            location=location,
            limit=limit,
            persona_id=persona_id,
        )
        items = [
            {
                "name": item.name,
                "website_url": item.website_url,
                "career_page_url": item.career_page_url,
                "sector": item.sector,
                "location_hint": item.location_hint,
                "relevanceScore": item.relevance_score,
                "relevanceReason": item.relevance_reason,
                "source": item.source,
                "type": "company",
            }
            for item in results
        ]
        return rank_candidates(
            items,
            target_roles=target_roles,
            industry=industry,
            location=location,
            persona_id=persona_id,
        )

    def inbound_token_for_user(self, user_id: str) -> str:
        """Stable per-user token used as the local-part of inbound email
        addresses (e.g. ``u-{token}@inbox.helpmefindthejob.com``).

        Derived as HMAC-SHA256 over the user-id + the server secret so it
        survives restarts and can be re-derived if a user loses their
        bookmarklet/email setup. The token has no read scope on the
        account — it's only usable to *land* a job in that user's queue.
        """

        import hashlib as _hashlib
        import hmac as _hmac

        secret = get_env(
            "HELPMEFINDTHEJOB_SECRET_KEY", "DIRECTJOB_SECRET_KEY", "dev-secret"
        ).encode("utf-8")
        digest = _hmac.new(secret, user_id.encode("utf-8"), _hashlib.sha256).hexdigest()
        return digest[:24]

    def repository_user_by_token(self, token: str) -> str | None:
        """Reverse-lookup helper for inbound-email routing.

        Iterates users + compares the derived token with constant-time
        equality. Caller passes the local-part captured from the
        recipient address.
        """

        import hmac as _hmac

        if not token:
            return None
        for user in self.auth_store.list_users():
            if _hmac.compare_digest(self.inbound_token_for_user(user.id), token):
                return user.id
        return None

    def run_user_daily(self, user_id: str, trigger: str = "scheduled") -> dict[str, Any]:
        """Combined daily run: watchlist scans + saved-search aggregator runs + email digest.

        Replaces the watchlist-only path that previously fronted the
        DurableScheduler. The new pipeline:

        1. Run all watched companies (existing ``run_watchlist_scan``).
        2. Run every saved search through ``run_saved_search`` so
           cross-aggregator results land in the queue.
        3. Send the user's daily digest (no-op when no email transport).
        4. Fire push notifications for any unseen new matches.

        Returns a small summary the scheduler logs back into its
        per-user run history.
        """

        scan_result = self.run_watchlist_scan(user_id, trigger=trigger)
        searches = self.repository.list_saved_searches(user_id)
        per_search: list[dict[str, Any]] = []
        for search in searches:
            try:
                per_search.append(self.run_saved_search(user_id, search.id))
            except Exception as exc:  # noqa: BLE001 - scheduler must keep running
                per_search.append(
                    {
                        "searchId": search.id,
                        "error": f"{type(exc).__name__}: {exc}"[:200],
                    }
                )
        digest_text = ""
        try:
            user = self.auth_store.get_user(user_id)
            digest_text = self.send_user_digest(user=user)
        except KeyError:
            digest_text = ""
        except Exception as exc:  # noqa: BLE001 - best-effort path; failure must not break the caller
            digest_text = f"digest_failed: {type(exc).__name__}"
        try:
            self.notify_new_matches(user_id)
        except Exception:  # noqa: BLE001, S110 - best-effort path; failure must not break the caller
            pass
        return {
            "trigger": trigger,
            "scan": scan_result,
            "savedSearchRuns": per_search,
            "digestSent": bool(digest_text and not digest_text.startswith("digest_failed")),
        }

    def build_user_digest(self, user_id: str, *, email: str) -> str:
        companies = self.repository.list_companies(user_id)
        discovered = self.repository.list_discovered_jobs(user_id)
        return build_digest(user_email=email, companies=companies, discovered_jobs=discovered)

    def send_user_digest(self, *, user: AuthUser) -> str:
        text = self.build_user_digest(user.id, email=user.email)
        self.email_transport.send(
            Email(
                to=user.email,
                subject="Your Helpmefindthejob digest",
                text=text,
                from_address=email_from_address(),
            )
        )
        return text

    def get_subscription(self) -> Subscription:
        return self.billing_backend.load()

    def update_subscription(
        self,
        *,
        actor: AuthUser,
        plan_id: str | None = None,
        status: str | None = None,
        seats: int | None = None,
        notes: str | None = None,
        customer_email: str | None = None,
    ) -> Subscription:
        sub = self.billing_backend.load()
        if plan_id and not any(p["id"] == plan_id for p in plans_payload()):
            raise ValueError("unknown_plan")
        if status and status not in {"active", "trialing", "past_due", "cancelled"}:
            raise ValueError("invalid_status")
        if plan_id:
            sub.plan_id = plan_id
        if status:
            sub.status = status
            if status == "cancelled" and not sub.cancelled_at:
                sub.cancelled_at = now_utc().isoformat()
        if seats is not None:
            sub.seats = max(1, int(seats))
        if notes is not None:
            sub.notes = notes
        if customer_email is not None:
            sub.customer_email = customer_email
        sub.last_event = now_utc().isoformat()
        result = self.billing_backend.save(sub)
        self.record_admin_action(
            actor=actor,
            target=None,
            action="update_billing",
            details={"plan": result.plan_id, "status": result.status, "seats": result.seats},
        )
        return result

    def log_analytics(
        self, user_id: str, kind: str, payload: dict[str, Any] | None = None
    ) -> AnalyticsEvent:
        event = AnalyticsEvent(user_id=user_id, kind=kind, payload=payload or {})
        return self.repository.save_analytics_event(event)

    def submit_support_ticket(
        self,
        *,
        user: AuthUser,
        subject: str,
        body: str,
        contact_email: str | None = None,
    ) -> SupportTicket:
        ticket = SupportTicket(
            user_id=user.id,
            subject=subject.strip() or "Support request",
            body=body.strip(),
            contact_email=(contact_email or user.email).strip().casefold(),
        )
        saved = self.repository.save_support_ticket(ticket)
        # Mirror to email so admins see it even without opening the app.
        try:
            self.email_transport.send(
                Email(
                    to=email_from_address(),
                    subject=f"[Helpmefindthejob support] {saved.subject}",
                    text=(f"From: {saved.contact_email}\nUser id: {user.id}\n\n{saved.body}\n"),
                    from_address=email_from_address(),
                )
            )
        except Exception:  # noqa: BLE001, S110 - never let email failure drop the ticket
            pass
        return saved

    def complete_password_reset(self, *, raw_token: str, password: str) -> AuthUser:
        if len(password) < 12:
            raise ValueError("password_too_short")
        record = self.token_store.consume("password_reset", raw_token)
        if record is None:
            raise ValueError("invalid_token")
        row = self.auth_store.connection.execute(
            "SELECT id FROM users WHERE email = ?", (record.email,)
        ).fetchone()
        if row is None:
            raise ValueError("invalid_token")
        return self.auth_store.update_user(row[0], password=password)


STATE = AppState()


class Handler(BaseHTTPRequestHandler):
    server_version = f"DirectJobScout/{APP_VERSION}"

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "worker-src 'self'; "
            "manifest-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "base-uri 'none'; "
            "frame-ancestors 'none'",
        )
        super().end_headers()

    def current_session(self) -> AuthSession | None:
        cookie_header = self.headers.get("Cookie", "")
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        morsel = cookie.get(SESSION_COOKIE_NAME)
        return STATE.auth_store.get_session(morsel.value if morsel else None)

    def require_auth(self) -> AuthSession | None:
        session = self.current_session()
        if session is None:
            self.send_error_json(HTTPStatus.UNAUTHORIZED, "unauthorized", "Sign in required")
            return None
        return session

    def require_csrf(self, session: AuthSession) -> bool:
        if self.headers.get("X-CSRF-Token") != session.csrf_token:
            self.send_error_json(HTTPStatus.FORBIDDEN, "csrf_failed", "Invalid CSRF token")
            return False
        return True

    def require_admin(self, session: AuthSession) -> bool:
        if not session.user.is_admin:
            self.send_error_json(HTTPStatus.FORBIDDEN, "admin_required", "Admin access required")
            return False
        return True

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/capture":
                # Bookmarklet landing page. Reads ?u=&t=, persists a captured
                # job for the signed-in user, then redirects to /?captured=1.
                from urllib.parse import parse_qs as _parse_qs

                session = self.current_session()
                if session is None:
                    # Send to login first; the bookmarklet user might be in
                    # a different browser session.
                    self.send_response(HTTPStatus.SEE_OTHER)
                    self.send_header("Location", "/?capture=needs_login")
                    self.end_headers()
                    return
                qs = _parse_qs(parsed.query or "")
                target_url = (qs.get("u", [""])[0] or "").strip()
                title = (qs.get("t", [""])[0] or "").strip()
                if not target_url or not target_url.startswith(("http://", "https://")):
                    self.send_response(HTTPStatus.SEE_OTHER)
                    self.send_header("Location", "/?capture=bad_url")
                    self.end_headers()
                    return
                host = (urlparse(target_url).hostname or "").lower()
                source_label = "bookmarklet:other"
                for needle, label in (
                    ("indeed.", "bookmarklet:indeed"),
                    ("linkedin.com", "bookmarklet:linkedin"),
                    ("stepstone.", "bookmarklet:stepstone"),
                    ("xing.com", "bookmarklet:xing"),
                ):
                    if needle in host:
                        source_label = label
                        break
                user_id = session.user.id
                data_user_id = STATE.effective_user_id(user_id)
                from company_discovery.models import DiscoveredJob

                candidate = DiscoveredJob(
                    user_id=data_user_id,
                    source_url=target_url,
                    title=(title or f"Captured from {host}")[:160],
                    raw_snippet=title[:160] or None,
                    confidence_score=0.5,
                    structured_data={"captured_via": source_label, "host": host},
                )
                duplicate = STATE.repository.find_duplicate_discovered_job(candidate)
                if duplicate:
                    existing = dict(duplicate.also_seen_at or {})
                    existing[host] = {
                        "url": target_url,
                        "found_at": now_utc().isoformat(),
                        "source_label": source_label,
                    }
                    duplicate.also_seen_at = existing
                    STATE.repository.save_discovered_job(duplicate)
                    captured_status = "merged"
                else:
                    STATE.repository.save_discovered_job(candidate)
                    captured_status = "captured"
                STATE.log_analytics(
                    user_id,
                    "captured_job",
                    {
                        "host": host,
                        "source": source_label,
                        "status": captured_status,
                    },
                )
                self.send_response(HTTPStatus.SEE_OTHER)
                self.send_header("Location", f"/?capture={captured_status}")
                self.end_headers()
                return
            if parsed.path == "/__reset__":
                # One-shot SW + cache nuker.
                #
                # Two important guarantees:
                # 1. The redirect fires UNCONDITIONALLY after 1.6s via
                #    a top-level setTimeout — even if any SW / Cache
                #    API await hangs (which can happen when the old
                #    SW is in a weird state). The cleanup runs in
                #    parallel; if it finishes early, all the better.
                # 2. The redirect target includes a cache-busting
                #    query string so the old SW's cache-first
                #    lookup misses (cache-match is query-sensitive
                #    by default) and falls through to a network fetch
                #    of the fresh /index.html.
                # 3. A manual "click here" link is always shown so
                #    the user can self-rescue if JS is disabled or
                #    everything goes sideways.
                html = (
                    '<!doctype html><html><head><meta charset="utf-8">'
                    "<title>Resetting…</title>"
                    "<style>body{font-family:sans-serif;padding:40px;max-width:560px;"
                    "background:#0f1014;color:#e8e8f0}h1{margin:0 0 12px}p{color:#a0a0b0;line-height:1.5}"
                    "a{color:#5fa8ff}</style>"
                    "</head><body>"
                    "<h1>Refreshing the app…</h1>"
                    '<p id="s">Clearing the old cached version, then reloading.</p>'
                    '<p><a href="/?_=manual" id="manual">If this doesn\'t redirect in 2 seconds, click here.</a></p>'
                    "<script>\n"
                    "// Schedule the redirect UNCONDITIONALLY — even if SW awaits hang.\n"
                    "setTimeout(function(){\n"
                    "  window.location.replace('/?_=' + Date.now());\n"
                    "}, 1600);\n"
                    "// Run cleanup in parallel. Failures are swallowed.\n"
                    "(async function(){\n"
                    "  const s = document.getElementById('s');\n"
                    "  function log(t){ try{ s.textContent = t; }catch(e){} }\n"
                    "  try {\n"
                    "    if ('serviceWorker' in navigator) {\n"
                    "      const rs = await Promise.race([\n"
                    "        navigator.serviceWorker.getRegistrations(),\n"
                    "        new Promise((res) => setTimeout(() => res([]), 800))\n"
                    "      ]);\n"
                    "      log('Unregistering ' + rs.length + ' service worker(s)…');\n"
                    "      await Promise.allSettled(rs.map(r => r.unregister()));\n"
                    "    }\n"
                    "  } catch(e) {}\n"
                    "  try {\n"
                    "    if ('caches' in window) {\n"
                    "      const ks = await Promise.race([\n"
                    "        caches.keys(),\n"
                    "        new Promise((res) => setTimeout(() => res([]), 800))\n"
                    "      ]);\n"
                    "      log('Clearing ' + ks.length + ' cache(s)…');\n"
                    "      await Promise.allSettled(ks.map(k => caches.delete(k)));\n"
                    "    }\n"
                    "  } catch(e) {}\n"
                    "  try { sessionStorage.clear(); } catch(e){}\n"
                    "  log('Done. Redirecting…');\n"
                    "})();\n"
                    "</script>"
                    "</body></html>"
                )
                self.send_text(html, content_type="text/html")
                return
            if parsed.path == "/api/health":
                session = self.current_session()
                from urllib.parse import parse_qs

                qs = parse_qs(parsed.query or "")
                detailed = (qs.get("detailed", ["0"])[0] or "0").lower() in ("1", "true", "yes")
                self.send_json(
                    STATE.health(session.user.id if session else None, detailed=detailed)
                )
                return
            if parsed.path == "/api/site-config":
                # Public, no-auth endpoint that surfaces the operator-set
                # site-wide config the frontend needs at boot. Today this
                # is just the optional analytics script URL — when set,
                # the frontend injects the script. When not set, we ship
                # zero third-party requests, which is the documented
                # default (see docs/cookie-audit.md).
                analytics_url = (
                    get_env(
                        "HELPMEFINDTHEJOB_ANALYTICS_SCRIPT_URL", "DIRECTJOB_ANALYTICS_SCRIPT_URL"
                    )
                    or ""
                ).strip()
                analytics_domain = (
                    get_env("HELPMEFINDTHEJOB_ANALYTICS_DOMAIN", "DIRECTJOB_ANALYTICS_DOMAIN") or ""
                ).strip()
                self.send_json(
                    {
                        "analytics": {
                            "scriptUrl": analytics_url or None,
                            "domain": analytics_domain or None,
                        }
                    }
                )
                return
            if parsed.path == "/api/auth/status":
                session = self.current_session()
                # ``hasUsers`` lets the frontend decide whether the
                # registration form is the first-account-bootstrap (no
                # consent needed — the operator wrote the policy) or a
                # public sign-up (consent checkboxes required).
                self.send_json(
                    {
                        "authenticated": session is not None,
                        "user": make_user_payload(session.user, session.csrf_token)
                        if session
                        else None,
                        "registrationOpen": STATE.registration_open(),
                        "hasUsers": STATE.auth_store.has_users(),
                    }
                )
                return
            if parsed.path.startswith("/api/auth/accept-invite/"):
                raw_token = parsed.path.split("/api/auth/accept-invite/", 1)[1]
                record = STATE.token_store.lookup("invitation", unquote(raw_token))
                if record is None:
                    self.send_error_json(
                        HTTPStatus.GONE, "invalid_token", "Invitation is expired or already used"
                    )
                    return
                self.send_json(
                    {
                        "invitation": {
                            "email": record.email,
                            "role": record.role,
                            "expiresAt": record.expires_at.isoformat(),
                        }
                    }
                )
                return
            if parsed.path.startswith("/api/auth/reset-password/"):
                raw_token = parsed.path.split("/api/auth/reset-password/", 1)[1]
                record = STATE.token_store.lookup("password_reset", unquote(raw_token))
                if record is None:
                    self.send_error_json(
                        HTTPStatus.GONE, "invalid_token", "Reset link is expired or already used"
                    )
                    return
                self.send_json(
                    {
                        "reset": {
                            "email": record.email,
                            "expiresAt": record.expires_at.isoformat(),
                        }
                    }
                )
                return
            if parsed.path.startswith("/share/job/"):
                job_id = parsed.path[len("/share/job/") :].strip("/")
                imported = STATE.repository.imported_jobs.get(job_id)
                if imported is None or not imported.share_enabled:
                    self._send_share_not_found_page()
                    return
                self._send_share_job_page(imported)
                return
            if parsed.path.startswith("/jobs/"):
                slug = parsed.path[len("/jobs/") :].strip("/").split("/", 1)[0]
                if not slug or not all(c.isalnum() or c == "-" for c in slug) or len(slug) > 80:
                    self._send_seo_page_not_found()
                    return
                page = STATE.find_seo_page(slug)
                if page is None:
                    self._send_seo_page_not_found()
                    return
                self._send_seo_page(page)
                return
            if parsed.path.startswith("/r/"):
                # Referral landing (#46). Stash the code in a Set-Cookie
                # so the registration form can read it via /api/site-config
                # equivalent (we expose it on /api/auth/status). Then
                # redirect the visitor to the home page so they can sign
                # up. Code is sanitised to URL-safe characters only —
                # anything else falls through to the static handler 404.
                code = parsed.path[len("/r/") :].strip("/").split("/", 1)[0]
                if not code or not all(c.isalnum() or c in "-_" for c in code) or len(code) > 32:
                    self.send_error_json(HTTPStatus.NOT_FOUND, "not_found", "Unknown referral code")
                    return
                self.send_response(HTTPStatus.SEE_OTHER)
                self.send_header("Location", "/?ref=" + code)
                # Short-lived cookie so the SPA can pick it up on the
                # registration form and forward it to /api/auth/register.
                # Referral cookie: HttpOnly so JS can't read it; SameSite=Lax
                # so it survives the SEE_OTHER redirect back to /register?ref=…
                # The SPA reads the ?ref= query param, not the cookie. Cookie
                # is server-side context only (forwarded to /api/auth/register
                # via the Cookie header on the next same-origin POST).
                self.send_header(
                    "Set-Cookie",
                    f"helpmefindthejob_ref={code}; Max-Age=2592000; Path=/; HttpOnly; SameSite=Lax",
                )
                self.end_headers()
                return
            if parsed.path == "/account/verify-email":
                from urllib.parse import parse_qs as _parse_qs

                qs = _parse_qs(parsed.query or "")
                raw_token = (qs.get("token", [""])[0] or "").strip()
                if not raw_token:
                    self._send_account_deletion_page(
                        title="Invalid link",
                        message="This verification link is missing its token. Copy and paste the entire URL from the email.",
                        ok=False,
                    )
                    return
                try:
                    STATE.confirm_email_verification(raw_token)
                except ValueError:
                    self._send_account_deletion_page(
                        title="Link expired",
                        message=(
                            "This verification link is invalid or has already been used. "
                            "Sign in and request a new one from the auth gate."
                        ),
                        ok=False,
                    )
                    return
                self._send_account_deletion_page(
                    title="Email verified",
                    message="Your email is verified. You can sign in now.",
                    ok=True,
                )
                return
            if parsed.path == "/account/deletion-confirm":
                from urllib.parse import parse_qs as _parse_qs

                qs = _parse_qs(parsed.query or "")
                raw_token = (qs.get("token", [""])[0] or "").strip()
                if not raw_token:
                    self._send_account_deletion_page(
                        title="Invalid link",
                        message="This confirmation link is missing its token. If you arrived here by clicking an email, the link may have wrapped — copy and paste the entire URL into the address bar.",
                        ok=False,
                    )
                    return
                try:
                    result = STATE.confirm_account_deletion(raw_token)
                except ValueError as error:
                    self._send_account_deletion_page(
                        title="Link expired",
                        message=(
                            "This confirmation link is invalid or has already been used. "
                            "If you still want to delete your account, sign in and request deletion again from "
                            "Settings → Privacy."
                        ),
                        ok=False,
                    )
                    _ = error  # error code already surfaced via the page text
                    return
                scheduled_iso = result["scheduledAt"]
                self._send_account_deletion_page(
                    title="Deletion scheduled",
                    message=(
                        "We have scheduled your account for permanent deletion in 7 days "
                        f"(on {scheduled_iso[:10]}). Sign in and visit Settings → Privacy "
                        "to cancel any time during the grace window."
                    ),
                    ok=True,
                )
                return
            if parsed.path.startswith("/api/"):
                session = self.require_auth()
                if session is None:
                    return
                user_id = session.user.id
            if parsed.path == "/api/account/deletion-status":
                self.send_json(STATE.get_account_deletion_state(session.user))
                return
            if parsed.path == "/api/applications/outcomes":
                self.send_json(STATE.application_outcomes_summary(STATE.effective_user_id(user_id)))
                return
            if parsed.path == "/api/account/referral":
                code = STATE.auth_store.ensure_referral_code(session.user.id)
                count = STATE.auth_store.count_referrals(session.user.id)
                self.send_json(
                    {
                        "code": code,
                        "url": STATE.public_url_for(f"/r/{code}"),
                        "referredCount": count,
                    }
                )
                return
            if parsed.path == "/api/bootstrap":
                self.send_json(STATE.bootstrap(user_id))
                return
            if parsed.path == "/api/admin/users":
                if not self.require_admin(session):
                    return
                users = [make_admin_user_payload(user) for user in STATE.auth_store.list_users()]
                self.send_json({"users": users})
                return
            if parsed.path == "/api/admin/metrics":
                if not self.require_admin(session):
                    return
                self.send_json(STATE.admin_metrics())
                return
            if parsed.path == "/api/admin/readiness":
                if not self.require_admin(session):
                    return
                self.send_json(STATE.readiness_report())
                return
            if parsed.path == "/api/admin/email/status":
                if not self.require_admin(session):
                    return
                self.send_json(STATE.email_status())
                return
            if parsed.path == "/api/admin/invitations":
                if not self.require_admin(session):
                    return
                tokens = STATE.token_store.list_active("invitation")
                self.send_json(
                    {
                        "invitations": [
                            {
                                "id": token.id,
                                "email": token.email,
                                "role": token.role,
                                "createdBy": token.created_by,
                                "createdAt": token.created_at.isoformat(),
                                "expiresAt": token.expires_at.isoformat(),
                            }
                            for token in tokens
                        ]
                    }
                )
                return
            if parsed.path == "/api/admin/analytics":
                if not self.require_admin(session):
                    return
                events = STATE.repository.list_analytics_events(limit=200)
                self.send_json({"events": events})
                return
            if parsed.path == "/api/managed-ai/waitlist":
                # Express interest in the operator-side managed AI tier.
                # We log it via analytics_event so admin can read the list
                # later. Real Stripe billing wiring is operator-pending.
                already = [
                    e
                    for e in STATE.repository.list_analytics_events(user_id=user_id, limit=20)
                    if (e.get("kind") if isinstance(e, dict) else getattr(e, "kind", None))
                    == "managed_ai_waitlist"
                ]
                if already:
                    self.send_json({"status": "already_on_waitlist"})
                    return
                STATE.log_analytics(
                    user_id,
                    "managed_ai_waitlist",
                    {"email": session.user.email, "requestedAt": now_utc().isoformat()},
                )
                self.send_json({"status": "added"})
                return
            if parsed.path == "/api/profile/slack-test":
                profile = STATE.profile_for(user_id)
                url = (profile.slack_webhook_url or "").strip()
                if not url:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "no_webhook", "Set a Slack webhook URL first."
                    )
                    return
                public_url = (
                    get_env("HELPMEFINDTHEJOB_PUBLIC_URL", "DIRECTJOB_PUBLIC_URL")
                    or "https://app.helpmefindthejob.com"
                )
                result = post_high_fit_notification(
                    webhook_url=url,
                    job_title="Test notification",
                    company_name="Helpmefindthejob",
                    location=None,
                    fit_score=0.95,
                    fit_reason="This is a test from your Settings page.",
                    job_url=None,
                    public_url=public_url,
                )
                STATE.log_analytics(user_id, "slack_test", {"status": result.get("status")})
                self.send_json({"result": result})
                return
            if parsed.path == "/api/admin/retention-purge":
                if not self.require_admin(session):
                    return
                results = STATE.run_retention_purge()
                self.send_json({"removedByUser": results, "total": sum(results.values())})
                return
            if parsed.path == "/api/audit-log":
                # User-facing audit log: only surface their own events, and
                # only the privacy-relevant kinds (auth, AI, exports,
                # consent changes). Cap at 50 most recent.
                relevant = {
                    "ai_analyze",
                    "cv_tailoring",
                    "cover_letter_draft",
                    "auto_fit",
                    "auto_fit_batch",
                    "totp_enabled",
                    "totp_disabled",
                    "cv_uploaded",
                    "ai_consent_granted",
                    "ai_consent_revoked",
                    "saved_search_run",
                    "captured_job",
                    "inbound_email",
                    "account_deletion_requested",
                }
                rows = STATE.repository.list_analytics_events(user_id=user_id, limit=200)
                visible = [
                    r
                    for r in rows
                    if (r.get("kind") if isinstance(r, dict) else r.kind) in relevant
                ][:50]
                self.send_json({"events": visible})
                return
            if parsed.path == "/api/admin/support":
                if not self.require_admin(session):
                    return
                tickets = STATE.repository.list_support_tickets()
                self.send_json({"tickets": tickets})
                return
            if parsed.path == "/api/admin/oversight/queue":
                # AI Act Article 14 minimum-viable human-oversight surface.
                # Returns recent AI-Act audit-log events for an oversight
                # person to review. Requires DIRECTJOB_HUMAN_OVERSIGHT_MODE
                # to be set to a truthy value; otherwise returns a 503
                # explaining the deployer-side configuration step.
                # See compliance/human-oversight-guide.md.
                if not self.require_admin(session):
                    return
                mode = (
                    get_env(
                        "HELPMEFINDTHEJOB_HUMAN_OVERSIGHT_MODE",
                        "DIRECTJOB_HUMAN_OVERSIGHT_MODE",
                        "",
                    )
                    or ""
                ).lower()
                if mode not in {"enabled", "true", "1", "yes", "on"}:
                    self.send_json(
                        {
                            "status": "disabled",
                            "mode": mode or "disabled",
                            "detail": (
                                "Set DIRECTJOB_HUMAN_OVERSIGHT_MODE=enabled to expose the "
                                "human-oversight queue. See compliance/human-oversight-guide.md "
                                "for the four oversight modes and selection guidance."
                            ),
                            "events": [],
                        }
                    )
                    return
                limit_raw = parsed.query and parse_qs(parsed.query).get("limit", ["100"])
                try:
                    limit = max(1, min(int(limit_raw[0]), 1000))
                except (ValueError, IndexError):
                    limit = 100
                event_type_filter = None
                if parsed.query:
                    qs = parse_qs(parsed.query)
                    if qs.get("event_type"):
                        event_type_filter = qs["event_type"][0]
                events = _read_ai_act_audit_tail(
                    DATA_ROOT / "ai_act_audit.log", limit, event_type_filter
                )
                self.send_json(
                    {
                        "status": "enabled",
                        "mode": "enabled",
                        "events": events,
                        "filter": {"limit": limit, "event_type": event_type_filter},
                        "totalReturned": len(events),
                    }
                )
                return
            if parsed.path == "/api/saved-searches":
                self.send_json({"savedSearches": STATE._saved_searches_with_alerts(user_id)})
                return
            if parsed.path == "/api/billing":
                self.send_json(
                    {"subscription": STATE.get_subscription().to_dict(), "plans": plans_payload()}
                )
                return
            if parsed.path == "/api/watchlist-templates":
                profile = STATE.profile_for(user_id)
                self.send_json({"templates": list_templates(profile.persona_id)})
                return
            if parsed.path == "/api/personas":
                self.send_json({"personas": list_personas_summary()})
                return
            if parsed.path == "/api/workspaces":
                self.send_json({"workspaces": STATE.list_user_workspaces(user_id)})
                return
            if parsed.path == "/api/push/key":
                self.send_json(
                    {
                        "configured": is_push_configured(),
                        "publicKey": vapid_public_key() or "",
                    }
                )
                return
            if parsed.path == "/api/push/subscriptions":
                subs = STATE.repository.list_push_subscriptions(user_id)
                self.send_json(
                    {
                        "subscriptions": [
                            {
                                "id": s.id,
                                "endpoint": s.endpoint,
                                "userAgent": s.user_agent,
                                "createdAt": s.created_at.isoformat(),
                            }
                            for s in subs
                        ]
                    }
                )
                return
            if parsed.path == "/api/profile":
                profile = STATE.profile_for(user_id)
                self.send_json({"profile": STATE._profile_payload(profile)})
                return
            if parsed.path == "/api/chat/state":
                # The GET handler doesn't define data_user_id at the
                # top — resolve it inline for this route.
                eff_user_id = STATE.effective_user_id(user_id)
                session = STATE.chat_session_for(eff_user_id)
                self.send_json({"session": session.to_dict()})
                return
            if parsed.path == "/api/chat/commands":
                self.send_json({"commands": list_chat_commands()})
                return
            if parsed.path == "/api/cv-builder/state":
                # Read-only GET counterpart. Client calls this without a
                # method (default GET) to load the wizard on view-nav;
                # before this route existed it 404'd → Python stdlib's
                # default 404 body ("File not found") leaked into the
                # photo status, broke the section renderer, and stuck
                # the header health pill at "Error".
                eff_user_id = STATE.effective_user_id(user_id)
                state = STATE.cv_builder_state_for(eff_user_id)
                section_obj = (
                    get_section(state.current_section_id) if state.current_section_id else None
                )
                self.send_json(
                    {
                        "state": state.to_dict(),
                        "currentSection": (
                            _serialise_cv_section(section_obj) if section_obj else None
                        ),
                        "sectionOrder": [s.section_id for s in SECTIONS],
                    }
                )
                return
            if parsed.path == "/api/cv/print":
                # Print-styled HTML of the user's saved CV. Browser
                # save-as-PDF gives us best-in-class typography without
                # a server-side PDF library. Append ?autoprint=1 to
                # auto-trigger the print dialog on load.
                profile = STATE.profile_for(user_id)
                cv_text = profile.cv_text or ""
                if not cv_text.strip():
                    self.send_text(
                        "<!doctype html><html><body><p>No CV saved yet — "
                        "build one in CV Builder first.</p></body></html>",
                        content_type="text/html",
                    )
                    return
                auto = urlparse(self.path).query and "autoprint" in urlparse(self.path).query
                html = render_cv_print_html(cv_text, auto_print=bool(auto))
                self.send_text(html, content_type="text/html")
                return
            if parsed.path == "/api/digest/preview":
                self.send_json(
                    {"digest": STATE.build_user_digest(user_id, email=session.user.email)}
                )
                return
            if parsed.path == "/api/exports/imported.csv":
                csv_body = imported_jobs_to_csv(STATE.repository.list_imported_jobs(user_id))
                self.send_text(csv_body, content_type="text/csv", filename="imported-jobs.csv")
                return
            if parsed.path == "/api/exports/imported.md":
                md_body = imported_jobs_to_markdown(STATE.repository.list_imported_jobs(user_id))
                self.send_text(md_body, content_type="text/markdown", filename="imported-jobs.md")
                return
            if parsed.path == "/api/exports/discovered.csv":
                csv_body = discovered_jobs_to_csv(STATE.repository.list_discovered_jobs(user_id))
                self.send_text(csv_body, content_type="text/csv", filename="discovered-jobs.csv")
                return
            if parsed.path == "/api/exports/discovered.md":
                md_body = discovered_jobs_to_markdown(
                    STATE.repository.list_discovered_jobs(user_id)
                )
                self.send_text(md_body, content_type="text/markdown", filename="discovered-jobs.md")
                return
            if parsed.path == "/api/data/export":
                self.send_json(STATE.export_data(user_id))
                return
            if parsed.path.startswith("/api/admin/users/") and parsed.path.endswith("/export"):
                if not self.require_admin(session):
                    return
                target_id = parsed.path[len("/api/admin/users/") : -len("/export")]
                try:
                    target = STATE.auth_store.get_user(target_id)
                except KeyError:
                    self.send_error_json(HTTPStatus.NOT_FOUND, "not_found", "User not found")
                    return
                payload = STATE.export_data(target_id)
                payload["targetUser"] = {
                    "id": target.id,
                    "email": target.email,
                    "role": target.role,
                    "active": target.active,
                }
                STATE.record_admin_action(
                    actor=session.user,
                    target=target,
                    action="export_user_data",
                    details={"email": target.email},
                )
                self.send_json(payload)
                return
            if parsed.path == "/api/companies":
                self.send_json({"companies": STATE.repository.list_companies(user_id)})
                return
            if parsed.path == "/api/discovered-jobs":
                self.send_json({"discoveredJobs": STATE.repository.list_discovered_jobs(user_id)})
                return
            if parsed.path == "/api/summary":
                self.send_json({"summary": STATE.repository.watchlist_summary(user_id)})
                return
            self.serve_static(parsed.path)
        except Exception as error:  # noqa: BLE001 - top-level HTTP boundary
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", str(error))

    def do_HEAD(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/api/health":
                self.send_json(STATE.health(None), include_body=False)
                return
            if parsed.path.startswith("/api/"):
                self.send_error_json(
                    HTTPStatus.NOT_FOUND, "not_found", "Unknown endpoint", include_body=False
                )
                return
            self.serve_static(parsed.path, include_body=False)
        except Exception as error:  # noqa: BLE001 - top-level HTTP boundary
            self.send_error_json(
                HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", str(error), include_body=False
            )

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]

            # Stripe webhook needs raw bytes for signature verification, so it
            # must run before we json.loads the body.
            if parsed.path == "/api/inbound/email":
                # Inbound webhook from Resend / Postmark / Mailgun for
                # email-forward ingest. The webhook secret + per-user
                # token route the message to the right account.
                #
                # Activation steps for the operator:
                #   1. Wire MX for inbox.helpmefindthejob.com to the inbound
                #      provider (Resend supports this).
                #   2. Set DIRECTJOB_INBOUND_EMAIL_SECRET in prod env.
                #   3. Configure the provider's webhook to POST here.
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_JSON_BODY_BYTES:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "bad_body", "Webhook body required"
                    )
                    return
                raw = self.rfile.read(length)
                expected_secret = get_env(
                    "HELPMEFINDTHEJOB_INBOUND_EMAIL_SECRET", "DIRECTJOB_INBOUND_EMAIL_SECRET", ""
                ).strip()
                if not expected_secret:
                    self.send_error_json(
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        "inbound_email_unconfigured",
                        "Inbound email is not configured. Set DIRECTJOB_INBOUND_EMAIL_SECRET.",
                    )
                    return
                provided_secret = self.headers.get("X-DirectJob-Inbound-Secret", "")
                # Constant-time comparison to avoid timing attacks.
                import hmac as _hmac

                if not _hmac.compare_digest(expected_secret, provided_secret):
                    self.send_error_json(
                        HTTPStatus.UNAUTHORIZED, "bad_inbound_secret", "Invalid inbound secret"
                    )
                    return
                try:
                    event = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "bad_json", "Inbound body is not valid JSON"
                    )
                    return
                # Resend / Postmark / Mailgun all expose roughly the
                # same shape; we read defensively.
                to_field = event.get("to") or event.get("ToFull") or event.get("recipient") or ""
                to_addresses = (
                    [to_field]
                    if isinstance(to_field, str)
                    else ([t.get("Email") if isinstance(t, dict) else str(t) for t in to_field])
                )
                token = ""
                for addr in to_addresses:
                    m = re.match(r"^u-([A-Za-z0-9_-]{8,})@", str(addr or ""))
                    if m:
                        token = m.group(1)
                        break
                target_user_id: str | None = None
                if token:
                    profile_user = self.repository_user_by_token(token)  # type: ignore[attr-defined]
                    target_user_id = profile_user
                if target_user_id is None:
                    self.send_error_json(
                        HTTPStatus.NOT_FOUND,
                        "no_user",
                        "Could not resolve recipient token to a user",
                    )
                    return
                from company_discovery.email_ingest import parse_email_to_jobs
                from company_discovery.models import DiscoveredJob

                jobs = parse_email_to_jobs(
                    sender=str(event.get("from") or event.get("From") or ""),
                    subject=str(event.get("subject") or event.get("Subject") or ""),
                    text_body=str(event.get("text") or event.get("TextBody") or ""),
                    html_body=str(event.get("html") or event.get("HtmlBody") or ""),
                )
                new_count = 0
                merged_count = 0
                for ingested in jobs:
                    candidate = DiscoveredJob(
                        user_id=target_user_id,
                        source_url=ingested.url,
                        title=ingested.title[:160] or "Captured listing",
                        confidence_score=0.5,
                        location=ingested.location,
                        structured_data={
                            "captured_via": ingested.source,
                            "company_hint": ingested.company,
                        },
                    )
                    duplicate = STATE.repository.find_duplicate_discovered_job(candidate)
                    if duplicate:
                        host = (urlparse(ingested.url).hostname or "").lower()
                        merged = dict(duplicate.also_seen_at or {})
                        merged[host] = {
                            "url": ingested.url,
                            "found_at": now_utc().isoformat(),
                            "source_label": ingested.source,
                        }
                        duplicate.also_seen_at = merged
                        STATE.repository.save_discovered_job(duplicate)
                        merged_count += 1
                    else:
                        STATE.repository.save_discovered_job(candidate)
                        new_count += 1
                STATE.log_analytics(
                    target_user_id,
                    "inbound_email",
                    {
                        "newJobs": new_count,
                        "merged": merged_count,
                        "candidates": len(jobs),
                    },
                )
                self.send_json(
                    {
                        "status": "ok",
                        "newJobs": new_count,
                        "mergedSources": merged_count,
                        "candidates": len(jobs),
                    }
                )
                return

            if parsed.path == "/api/billing/webhook":
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_JSON_BODY_BYTES:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "bad_body", "Webhook body required"
                    )
                    return
                raw = self.rfile.read(length)
                signature_header = self.headers.get("Stripe-Signature", "")
                secret = get_env(
                    "HELPMEFINDTHEJOB_STRIPE_WEBHOOK_SECRET", "DIRECTJOB_STRIPE_WEBHOOK_SECRET", ""
                ).strip()
                if not secret:
                    self.send_error_json(
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        "webhook_unconfigured",
                        "HELPMEFINDTHEJOB_STRIPE_WEBHOOK_SECRET not set.",
                    )
                    return
                if not verify_stripe_webhook_signature(raw, signature_header, secret):
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST,
                        "bad_signature",
                        "Webhook signature verification failed.",
                    )
                    return
                try:
                    event = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "bad_json", "Webhook body is not valid JSON."
                    )
                    return
                # Idempotency dedup (PART I.4 of the deep audit). Stripe
                # retries on non-2xx for up to ~3 days; if a previous
                # delivery succeeded but our 200-OK response was lost,
                # the same event.id arrives again. Short-circuit on a
                # second arrival to avoid double-applying subscription
                # state + analytics side-effects.
                event_id = str(event.get("id") or "")
                event_type = str(event.get("type") or "")
                is_first_delivery = STATE.auth_store.mark_stripe_event_processed(
                    event_id, event_type
                )
                if not is_first_delivery:
                    self.send_json(
                        {"status": "ok", "appliedType": event_type, "deduplicated": True}
                    )
                    return
                price_to_plan = {
                    get_env(
                        "HELPMEFINDTHEJOB_STRIPE_PRICE_TEAM", "DIRECTJOB_STRIPE_PRICE_TEAM", ""
                    ): "team",
                    get_env(
                        "HELPMEFINDTHEJOB_STRIPE_PRICE_ORG", "DIRECTJOB_STRIPE_PRICE_ORG", ""
                    ): "org",
                    get_env(
                        "HELPMEFINDTHEJOB_STRIPE_PRICE_PRO_MONTHLY",
                        "DIRECTJOB_STRIPE_PRICE_PRO_MONTHLY",
                        "",
                    ): "pro_monthly",
                    get_env(
                        "HELPMEFINDTHEJOB_STRIPE_PRICE_PRO_ANNUAL",
                        "DIRECTJOB_STRIPE_PRICE_PRO_ANNUAL",
                        "",
                    ): "pro_annual",
                }
                resolver = lambda price_id: price_to_plan.get(price_id) or ""
                current = STATE.get_subscription()
                next_state = apply_stripe_event(event, current, plan_resolver=resolver)
                if next_state is not current:
                    STATE.billing_backend.save(next_state)
                self.send_json({"status": "ok", "appliedType": event.get("type")})
                return

            payload = self.read_json_body()

            if parsed.path == "/api/auth/login":
                client_id = self.client_address[0] if self.client_address else "unknown"
                # Atomically claim a slot — under burst this strictly
                # caps the number of in-flight failures at the limit
                # (vs the old check-then-record pattern that let a
                # handful of attempts slip past). Refund on success so
                # the cap counts failures only.
                if not STATE.claim_login_slot(client_id):
                    self.send_error_json(
                        HTTPStatus.TOO_MANY_REQUESTS,
                        "rate_limited",
                        "Too many failed login attempts",
                    )
                    return
                user = STATE.auth_store.authenticate(
                    payload.get("email", ""), payload.get("password", "")
                )
                if user is None:
                    self.send_error_json(
                        HTTPStatus.UNAUTHORIZED, "invalid_login", "Invalid email or password"
                    )
                    return
                STATE.refund_login_slot(client_id)
                STATE.clear_login_failures(client_id)
                if REQUIRE_EMAIL_VERIFICATION and not STATE.auth_store.is_email_verified(user.id):
                    self.send_error_json(
                        HTTPStatus.FORBIDDEN,
                        "email_unverified",
                        "Verify your email before signing in. Check your inbox or request a new link.",
                    )
                    return
                if STATE.auth_store.has_totp_enabled(user.id):
                    challenge = STATE.auth_store.issue_2fa_challenge(user.id)
                    self.send_json({"requires2fa": True, "challengeToken": challenge})
                    return
                session = STATE.auth_store.create_session(user)
                max_age = int((session.expires_at - now_utc()).total_seconds())
                self.send_json(
                    {
                        "user": make_user_payload(user, session.csrf_token),
                        "bootstrap": STATE.bootstrap(user.id),
                    },
                    headers={"Set-Cookie": session_cookie_header(session.token, max_age)},
                )
                return

            if parsed.path == "/api/auth/2fa-verify":
                challenge_token = str(payload.get("challengeToken") or "").strip()
                code = str(payload.get("code") or "").strip()
                user_id = STATE.auth_store.consume_2fa_challenge(challenge_token)
                if not user_id:
                    self.send_error_json(
                        HTTPStatus.UNAUTHORIZED, "invalid_challenge", "Challenge expired or invalid"
                    )
                    return
                # Try TOTP first, then recovery codes (which look different — usually 10 hex chars).
                ok = STATE.auth_store.verify_user_totp(
                    user_id, code
                ) or STATE.auth_store.consume_recovery_code(user_id, code)
                if not ok:
                    self.send_error_json(
                        HTTPStatus.UNAUTHORIZED, "invalid_2fa_code", "Invalid 2FA code"
                    )
                    return
                user = STATE.auth_store.get_user(user_id)
                session = STATE.auth_store.create_session(user)
                max_age = int((session.expires_at - now_utc()).total_seconds())
                self.send_json(
                    {
                        "user": make_user_payload(user, session.csrf_token),
                        "bootstrap": STATE.bootstrap(user.id),
                    },
                    headers={"Set-Cookie": session_cookie_header(session.token, max_age)},
                )
                return

            if parsed.path == "/api/auth/register":
                if not STATE.registration_open():
                    self.send_error_json(
                        HTTPStatus.FORBIDDEN, "registration_closed", "Registration is closed"
                    )
                    return
                # Rate-limit registration except for the first-account
                # bootstrap path (no users yet → admin gets created). Without
                # this an attacker could spam-create accounts and pump the
                # outbound email transport.
                is_bootstrap = not STATE.auth_store.has_users()
                if not is_bootstrap:
                    client_id = self.client_address[0] if self.client_address else "unknown"
                    # Atomic claim — strict cap under burst.
                    if not STATE.claim_register_slot(client_id):
                        self.send_error_json(
                            HTTPStatus.TOO_MANY_REQUESTS,
                            "rate_limited",
                            "Too many registration attempts. Try again later.",
                        )
                        return
                    # DSGVO consent (#30). Public sign-ups must tick
                    # both the Terms and the Privacy boxes — otherwise
                    # the account creation is refused. The bootstrap
                    # admin path is exempt because the operator IS the
                    # one writing the policy.
                    tos_ok = bool(payload.get("tosAccepted"))
                    privacy_ok = bool(payload.get("privacyAccepted"))
                    if not tos_ok or not privacy_ok:
                        self.send_error_json(
                            HTTPStatus.BAD_REQUEST,
                            "consent_required",
                            "Accept the Terms and the Privacy policy to create an account.",
                        )
                        return
                role = "admin" if is_bootstrap else "member"
                user = STATE.auth_store.create_user(
                    payload.get("email", ""), payload.get("password", ""), role=role
                )
                # Stamp the very first sign-in (register doesn't go through authenticate()).
                login_at = now_utc()
                STATE.auth_store.connection.execute(
                    "UPDATE users SET last_login_at = ?, last_active_at = ? WHERE id = ?",
                    (login_at.isoformat(), login_at.isoformat(), user.id),
                )
                STATE.auth_store.connection.commit()
                # Referral capture (#46): if the form supplied a referrer
                # code we stamp it on the new user. record_referral is
                # tolerant of bad codes (no-op on bad / self / inactive
                # referrer) so sign-up is never blocked by a typo.
                referrer_code = str(payload.get("referrerCode") or "").strip()
                if referrer_code and not is_bootstrap:
                    STATE.auth_store.record_referral(user.id, referrer_code)
                # Mint the new user's own referral code so the dashboard
                # can show their share URL immediately.
                STATE.auth_store.ensure_referral_code(user.id)
                if is_bootstrap:
                    # Bootstrap admin owns the mailbox already; flag the
                    # account verified directly. Skip the verify email.
                    STATE.auth_store.mark_email_verified(user.id)
                else:
                    STATE.auth_store.record_consent(user.id, tos=True, privacy=True)
                    # Email verification + welcome are both best-effort.
                    try:
                        STATE.send_email_verification(user)
                    except Exception:  # noqa: BLE001, S110 - best-effort path; failure must not break the caller
                        pass
                    try:
                        STATE.send_welcome_email(user)
                    except Exception:  # noqa: BLE001, S110 - email failure must not block sign-in
                        pass
                user = STATE.auth_store.get_user(user.id)
                session = STATE.auth_store.create_session(user)
                max_age = int((session.expires_at - now_utc()).total_seconds())
                self.send_json(
                    {
                        "user": make_user_payload(user, session.csrf_token),
                        "bootstrap": STATE.bootstrap(user.id),
                    },
                    HTTPStatus.CREATED,
                    headers={"Set-Cookie": session_cookie_header(session.token, max_age)},
                )
                return

            if parsed.path == "/api/auth/logout":
                session = self.current_session()
                if session:
                    STATE.auth_store.delete_session(session.token)
                self.send_json(
                    {"status": "signed_out"},
                    headers={"Set-Cookie": session_cookie_header("", 0)},
                )
                return

            if parsed.path == "/api/auth/forgot-password":
                client_id = self.client_address[0] if self.client_address else "unknown"
                if not STATE.claim_password_reset_slot(client_id):
                    self.send_error_json(
                        HTTPStatus.TOO_MANY_REQUESTS,
                        "rate_limited",
                        "Too many reset requests. Try again later.",
                    )
                    return
                STATE.request_password_reset(payload.get("email", ""))
                # Always return 202 to avoid leaking which emails exist.
                self.send_json({"status": "sent_if_known"}, HTTPStatus.ACCEPTED)
                return
            if parsed.path == "/api/auth/verify-email/resend":
                # Public, rate-limited (re-using the password-reset
                # bucket so the two flows can't combine into a flood).
                # Always returns 202 to avoid revealing which addresses
                # already have an account.
                client_id = self.client_address[0] if self.client_address else "unknown"
                if not STATE.claim_password_reset_slot(client_id):
                    self.send_error_json(
                        HTTPStatus.TOO_MANY_REQUESTS,
                        "rate_limited",
                        "Too many requests. Try again later.",
                    )
                    return
                email = str(payload.get("email") or "").strip().lower()
                if email:
                    for candidate in STATE.auth_store.list_users():
                        if (
                            candidate.email.lower() == email
                            and not STATE.auth_store.is_email_verified(candidate.id)
                        ):
                            try:
                                STATE.send_email_verification(candidate)
                            except Exception:  # noqa: BLE001, S110 - best-effort path; failure must not break the caller
                                pass
                            break
                self.send_json({"status": "sent_if_known"}, HTTPStatus.ACCEPTED)
                return

            if parsed.path.startswith("/api/auth/reset-password/"):
                raw_token = parsed.path.split("/api/auth/reset-password/", 1)[1]
                new_password = str(payload.get("newPassword") or "")
                try:
                    STATE.complete_password_reset(
                        raw_token=unquote(raw_token), password=new_password
                    )
                except ValueError as error:
                    code = str(error)
                    status = HTTPStatus.GONE if code == "invalid_token" else HTTPStatus.BAD_REQUEST
                    self.send_error_json(status, code, code)
                    return
                self.send_json({"status": "password_reset"})
                return

            if parsed.path.startswith("/api/auth/accept-invite/"):
                raw_token = parsed.path.split("/api/auth/accept-invite/", 1)[1]
                new_password = str(payload.get("newPassword") or "")
                try:
                    user = STATE.accept_invitation(
                        raw_token=unquote(raw_token), password=new_password
                    )
                except ValueError as error:
                    code = str(error)
                    status = HTTPStatus.GONE if code == "invalid_token" else HTTPStatus.BAD_REQUEST
                    self.send_error_json(status, code, code)
                    return
                session = STATE.auth_store.create_session(user)
                max_age = int((session.expires_at - now_utc()).total_seconds())
                self.send_json(
                    {
                        "user": make_user_payload(user, session.csrf_token),
                        "bootstrap": STATE.bootstrap(user.id),
                    },
                    HTTPStatus.CREATED,
                    headers={"Set-Cookie": session_cookie_header(session.token, max_age)},
                )
                return

            if parsed.path.startswith("/api/"):
                session = self.require_auth()
                if session is None or not self.require_csrf(session):
                    return
                user_id = session.user.id
                data_user_id = STATE.effective_user_id(user_id)

            if parsed.path == "/api/auth/change-password":
                current_password = str(payload.get("currentPassword") or "")
                new_password = str(payload.get("newPassword") or "")
                if STATE.auth_store.authenticate(session.user.email, current_password) is None:
                    self.send_error_json(
                        HTTPStatus.FORBIDDEN,
                        "invalid_current_password",
                        "Current password is incorrect",
                    )
                    return
                STATE.auth_store.update_user(user_id, password=new_password)
                self.send_json(
                    {"status": "password_changed"},
                    headers={"Set-Cookie": session_cookie_header("", 0)},
                )
                return

            if parsed.path == "/api/auth/totp/enroll":
                if STATE.auth_store.has_totp_enabled(user_id):
                    self.send_error_json(
                        HTTPStatus.CONFLICT,
                        "totp_already_enabled",
                        "2FA is already enabled. Disable it first to re-enroll.",
                    )
                    return
                enrollment = STATE.auth_store.start_totp_enrollment(user_id)
                self.send_json(enrollment)
                return

            if parsed.path == "/api/auth/totp/confirm":
                code = str(payload.get("code") or "").strip()
                try:
                    recovery_codes = STATE.auth_store.confirm_totp_enrollment(user_id, code)
                except ValueError as error:
                    self.send_error_json(HTTPStatus.BAD_REQUEST, str(error), str(error))
                    return
                STATE.log_analytics(user_id, "totp_enabled", {})
                self.send_json({"status": "enabled", "recoveryCodes": recovery_codes})
                return

            if parsed.path == "/api/auth/totp/disable":
                password = str(payload.get("password") or "")
                try:
                    STATE.auth_store.disable_totp(user_id, password)
                except ValueError as error:
                    self.send_error_json(HTTPStatus.FORBIDDEN, str(error), str(error))
                    return
                STATE.log_analytics(user_id, "totp_disabled", {})
                self.send_json({"status": "disabled"})
                return

            if parsed.path == "/api/admin/users":
                if not self.require_admin(session):
                    return
                user = STATE.auth_store.create_user(
                    payload.get("email", ""),
                    payload.get("password", ""),
                    role=payload.get("role") or "member",
                )
                STATE.record_admin_action(
                    actor=session.user,
                    target=user,
                    action="create_user",
                    details={"role": user.role},
                )
                self.send_json(
                    {
                        "user": make_admin_user_payload(user),
                        "users": [
                            make_admin_user_payload(item) for item in STATE.auth_store.list_users()
                        ],
                    },
                    HTTPStatus.CREATED,
                )
                return

            if parsed.path == "/api/admin/invitations":
                if not self.require_admin(session):
                    return
                try:
                    result = STATE.send_invitation(
                        actor=session.user,
                        email=str(payload.get("email") or ""),
                        role=str(payload.get("role") or "member"),
                    )
                except ValueError as error:
                    self.send_error_json(HTTPStatus.BAD_REQUEST, str(error), str(error))
                    return
                self.send_json(result, HTTPStatus.CREATED)
                return

            if parsed.path == "/api/companies":
                company = STATE.service.create_company(
                    user_id=data_user_id,
                    name=payload["name"],
                    website_url=payload["websiteUrl"],
                    career_page_url=payload.get("careerPageUrl") or None,
                    sector=payload.get("sector") or None,
                    notes=payload.get("notes") or None,
                    watch_enabled=bool(payload.get("watchEnabled", True)),
                )
                self.send_json(
                    {"company": company, "bootstrap": STATE.bootstrap(user_id)}, HTTPStatus.CREATED
                )
                return

            if parsed.path == "/api/suggest-companies":
                profile = STATE.profile_for(user_id)
                persona_id = str(
                    payload.get("personaId") or profile.persona_id or DEFAULT_PERSONA_ID
                )
                persona = get_persona(persona_id)
                target_roles = payload.get("targetRoles") or list(
                    profile.target_roles or persona.default_target_roles
                )
                industry = payload.get("industry") or profile.industry or persona.default_industry
                location = payload.get("location") or profile.location or None
                suggestions = STATE.service.suggest_relevant_companies(
                    target_roles=target_roles,
                    industry=industry,
                    location=location,
                    persona_id=persona.id,
                )
                ranked = rank_candidates(
                    suggestions,
                    target_roles=target_roles,
                    industry=industry,
                    location=location,
                    persona_id=persona.id,
                )
                self.send_json({"suggestions": ranked, "personaId": persona.id})
                return
            if parsed.path == "/api/captured-jobs":
                # Bookmarklet ingest. Phase 3 — bridges Indeed / LinkedIn /
                # StepStone / Xing into the queue without server-side scraping
                # (the user's own browser does the read; we only persist the URL +
                # title they were already looking at).
                target_url = str(payload.get("url") or "").strip()
                title = str(payload.get("title") or "").strip()
                description = str(payload.get("description") or "").strip()
                if not target_url or not target_url.startswith(("http://", "https://")):
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "bad_url", "Valid http(s) URL required"
                    )
                    return
                host = (urlparse(target_url).hostname or "").lower()
                source_label = "bookmarklet:other"
                for needle, label in (
                    ("indeed.", "bookmarklet:indeed"),
                    ("linkedin.com", "bookmarklet:linkedin"),
                    ("stepstone.", "bookmarklet:stepstone"),
                    ("xing.com", "bookmarklet:xing"),
                ):
                    if needle in host:
                        source_label = label
                        break
                if not title:
                    title = f"Captured from {host}"
                # Persist as a DiscoveredJob with NO company_id (aggregator-style).
                # Dedup against any existing rows the user already has via the
                # standard dedup engine.
                from company_discovery.models import DiscoveredJob

                candidate = DiscoveredJob(
                    user_id=data_user_id,
                    source_url=target_url,
                    title=title[:160],
                    raw_snippet=title[:160],
                    raw_description=description[:2000] or None,
                    confidence_score=0.5,
                    structured_data={"captured_via": source_label, "host": host},
                )
                duplicate = STATE.repository.find_duplicate_discovered_job(candidate)
                if duplicate:
                    existing = dict(duplicate.also_seen_at or {})
                    existing[host] = {
                        "url": target_url,
                        "found_at": now_utc().isoformat(),
                        "source_label": source_label,
                    }
                    duplicate.also_seen_at = existing
                    STATE.repository.save_discovered_job(duplicate)
                    saved = duplicate
                    status_code = "merged"
                else:
                    saved = STATE.repository.save_discovered_job(candidate)
                    status_code = "captured"
                STATE.log_analytics(
                    user_id,
                    "captured_job",
                    {
                        "host": host,
                        "source": source_label,
                        "status": status_code,
                    },
                )
                self.send_json(
                    {
                        "status": status_code,
                        "discoveredJobId": saved.id,
                        "source": source_label,
                    }
                )
                return

            if parsed.path == "/api/jobs/search":
                # Cross-aggregator job search. Phase 1 surface — Phase 2
                # promotes this to a saved-query / digest spine.
                profile = STATE.profile_for(user_id)
                query = str(payload.get("query") or "").strip()
                if not query:
                    persona = get_persona(profile.persona_id)
                    query = " ".join(profile.target_roles or list(persona.default_target_roles))
                location = payload.get("location") or profile.location or None
                limit_per_provider = int(payload.get("limitPerProvider") or 25)
                limit_per_provider = max(1, min(100, limit_per_provider))
                jobs, outcomes = STATE.aggregator_engine.search(
                    query=query,
                    location=location,
                    limit_per_provider=limit_per_provider,
                    persona_id=profile.persona_id,
                )
                # Rank by persona-keyword match + freshness + source-priority.
                # Persona keywords come from the user's profile + the raw query
                # so a tech persona searching "policy" doesn't drown in healthcare
                # results, and vice versa.
                persona = get_persona(profile.persona_id)
                keyword_tokens: list[str] = []
                # Raw query words first (highest signal — what the user just typed).
                keyword_tokens.extend(re.findall(r"\w+", query.casefold()))
                # Then persona's preferred terms.
                for role in persona.default_target_roles:
                    keyword_tokens.extend(re.findall(r"\w+", role.casefold()))
                cap = int(payload.get("cap") or 50)
                cap = max(5, min(200, cap))
                ranked = rank_aggregated(
                    jobs,
                    keyword_tokens=keyword_tokens,
                    location=location,
                    cap=cap,
                    dismissed_terms=list(profile.dismissed_terms or []),
                )
                attributions = [
                    {"name": a.name, "label": a.label, "url": a.url}
                    for a in STATE.aggregator_engine.attributions()
                ]
                STATE.log_analytics(
                    user_id,
                    "jobs_search",
                    {
                        "query": query[:120],
                        "location": location,
                        "providerCount": len(outcomes),
                        "jobCount": len(jobs),
                    },
                )
                self.send_json(
                    {
                        "query": query,
                        "location": location,
                        "totalCandidates": len(jobs),
                        "jobs": [
                            {
                                "title": j.title,
                                "companyName": j.company_name,
                                "source": j.source,
                                "sourceUrl": j.source_url,
                                "location": j.location,
                                "description": j.description,
                                "postedAt": j.posted_at.isoformat() if j.posted_at else None,
                                "salaryHint": j.salary_hint,
                                "score": score,
                            }
                            for j, score in ranked
                        ],
                        "outcomes": [
                            {
                                "provider": o.provider,
                                "jobCount": o.job_count,
                                "cached": o.cached,
                                "error": o.error,
                            }
                            for o in outcomes
                        ],
                        "attributions": attributions,
                    }
                )
                return

            if parsed.path == "/api/discover-companies":
                profile = STATE.profile_for(user_id)
                persona_id = str(
                    payload.get("personaId") or profile.persona_id or DEFAULT_PERSONA_ID
                )
                persona = get_persona(persona_id)
                target_roles = payload.get("targetRoles") or list(
                    profile.target_roles or persona.default_target_roles
                )
                industry = payload.get("industry") or profile.industry or persona.default_industry
                location = payload.get("location") or profile.location or None
                results = STATE.discover_companies(
                    target_roles=target_roles,
                    industry=industry,
                    location=location,
                    limit=int(payload.get("limit") or 12),
                    persona_id=persona.id,
                )
                self.send_json({"results": results, "personaId": persona.id})
                return
            if parsed.path == "/api/profile":
                try:
                    profile = STATE.update_profile(user_id, payload)
                except ValueError as error:
                    self.send_error_json(HTTPStatus.BAD_REQUEST, str(error), str(error))
                    return
                self.send_json(
                    {
                        "profile": STATE._profile_payload(profile),
                        "bootstrap": STATE.bootstrap(user_id),
                    }
                )
                return
            if parsed.path == "/api/profile/photo-upload":
                # CV photo upload. Accept base64 just like cv-upload.
                # Runs through cv_photo.normalise_photo_upload which:
                #   - Validates magic number (PNG/JPEG/WebP only — no SVG)
                #   - Strips EXIF (JPEG) and ancillary chunks (PNG)
                #   - Caps at 512KB raw
                # The resulting data URI is stored on the profile and
                # also surfaced to the CV builder's header section.
                import base64 as _b64
                import binascii as _bx

                from company_discovery.cv_photo import (
                    PhotoValidationError,
                    normalise_photo_upload,
                )

                content_b64 = str(
                    payload.get("contentBase64") or payload.get("content_base64") or ""
                )
                if not content_b64:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "missing_fields", "contentBase64 required"
                    )
                    return
                try:
                    raw = _b64.b64decode(content_b64, validate=False)
                except (_bx.Error, ValueError):
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "invalid_base64", "Could not decode upload"
                    )
                    return
                try:
                    data_uri = normalise_photo_upload(raw)
                except PhotoValidationError as error:
                    code = str(error)
                    human = {
                        "empty": "The photo file appears to be empty.",
                        "too_large": "Photo must be under 512KB.",
                        "unsupported_mime": "Only JPEG, PNG, and WebP photos are accepted. SVG is rejected for safety.",
                    }.get(code, code)
                    self.send_error_json(HTTPStatus.BAD_REQUEST, code, human)
                    return
                profile = STATE.profile_for(user_id)
                profile.cv_photo_data_uri = data_uri
                STATE.repository.save_user_profile(profile)
                STATE.log_analytics(user_id, "cv_photo_uploaded", {"sizeBytes": len(raw)})
                self.send_json(
                    {
                        "cvPhotoDataUri": data_uri,
                        "sizeBytes": len(raw),
                    }
                )
                return
            if parsed.path == "/api/profile/photo":
                # DELETE-via-POST shortcut (avoid second handler).
                if str(payload.get("action") or "").lower() != "remove":
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST,
                        "unknown_action",
                        "Set action='remove' to clear the photo.",
                    )
                    return
                profile = STATE.profile_for(user_id)
                profile.cv_photo_data_uri = None
                STATE.repository.save_user_profile(profile)
                self.send_json({"cvPhotoDataUri": None})
                return
            if parsed.path == "/api/profile/cv-upload":
                import base64
                import binascii

                filename = str(payload.get("filename") or "").strip()
                content_b64 = str(
                    payload.get("contentBase64") or payload.get("content_base64") or ""
                )
                if not filename or not content_b64:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST,
                        "missing_fields",
                        "filename and contentBase64 required",
                    )
                    return
                try:
                    blob = base64.b64decode(content_b64, validate=True)
                except binascii.Error:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "invalid_base64", "Could not decode upload"
                    )
                    return
                try:
                    text = extract_cv_text(filename, blob)
                except CvExtractError as error:
                    self.send_error_json(HTTPStatus.BAD_REQUEST, str(error), str(error))
                    return
                try:
                    profile = STATE.update_profile(user_id, {"cvText": text})
                except ValueError as error:
                    self.send_error_json(HTTPStatus.BAD_REQUEST, str(error), str(error))
                    return
                STATE.log_analytics(
                    user_id, "cv_uploaded", {"filename": filename, "chars": len(text)}
                )
                from company_discovery.personas import PERSONAS, suggest_persona_from_text

                ranked = suggest_persona_from_text(text, top_k=3)
                personaSuggestions = [
                    {
                        "personaId": pid,
                        "label": PERSONAS[pid].label if pid in PERSONAS else pid,
                        "score": score,
                    }
                    for pid, score in ranked
                ]
                self.send_json(
                    {
                        "profile": STATE._profile_payload(profile),
                        "bootstrap": STATE.bootstrap(user_id),
                        "extractedChars": len(text),
                        "personaSuggestions": personaSuggestions,
                    }
                )
                return
            if parsed.path == "/api/profile/persona-suggest":
                # Used by the UI when the user wants to re-evaluate the
                # persona suggestion without re-uploading their CV.
                profile = STATE.repository.get_user_profile(user_id)
                cv_text = (profile.cv_text or "") if profile else ""
                from company_discovery.personas import PERSONAS, suggest_persona_from_text

                ranked = suggest_persona_from_text(cv_text, top_k=5)
                self.send_json(
                    {
                        "personaSuggestions": [
                            {
                                "personaId": pid,
                                "label": PERSONAS[pid].label if pid in PERSONAS else pid,
                                "score": score,
                            }
                            for pid, score in ranked
                        ],
                    }
                )
                return
            # ---------------- Chat-router API ----------------
            #
            # /api/chat/message — user sends a message. The server
            # routes it (slash → keyword → AI → ask-for-help), elicits
            # missing params one at a time, shows a confirmation prompt
            # before executing any DB write, then dispatches via the
            # central audit-logged choke point.
            if parsed.path == "/api/chat/message":
                session = STATE.chat_session_for(data_user_id)
                raw_message = payload.get("message")
                if raw_message is None:
                    raw_message = ""
                user_message = str(raw_message).strip()
                # Empty replies are allowed ONLY when we're awaiting an
                # optional param (the user wants to skip it). Reject
                # all other empty messages.
                awaiting_optional = (
                    session.pending is not None
                    and session.pending.awaiting is not None
                    and not session.pending.awaiting_confirmation
                    and any(
                        p.name == session.pending.awaiting and not p.required
                        for p in CHAT_REGISTRY[session.pending.command_name].params
                    )
                )
                if not user_message and not awaiting_optional:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "empty_message", "Empty chat message."
                    )
                    return
                session.history.append(ChatTurn(role="user", content=user_message))

                # ── R17 guided journey: if the user has an active
                # journey (not GREET/DONE), keep routing messages
                # through the state machine so the conversation flows
                # naturally without slash commands. Also auto-start a
                # journey on explicit job-seeking intent.
                from company_discovery.journey import (
                    PHASE_CV_CHECK,
                    PHASE_DONE,
                    PHASE_GREET,
                    looks_like_cv_creation_intent,
                    looks_like_new_search_intent,
                    should_auto_start,
                )

                journey_now = STATE._journey_load(data_user_id)
                in_journey = journey_now.phase not in (PHASE_GREET, PHASE_DONE)
                # R21.x: a user in a post-search phase (REVIEW / DRILL /
                # TAILOR / LETTER / CV_CONSULT) who types "search for X"
                # or a bare role keyword wants a NEW search — not a
                # category drill of the OLD results. Without this
                # escape hatch the user is stuck rejecting the same
                # "Which category?" prompt forever (real bug seen on
                # prod 0.79.1: "search for pflege" rejected three
                # times after a Bartender search). Reset the journey
                # state + let the auto-start path handle it.
                # R79.3: CV-creation intent escape hatch. From real
                # prod transcript: user picks a job, has no CV, types
                # "i don't have a cv and i need you to create ne one"
                # — currently stuck in the tailor letter/consult/save
                # menu. This routes them straight to the sectional
                # CV-build flow regardless of journey phase.
                if looks_like_cv_creation_intent(user_message, journey_now.phase):
                    STATE.log_analytics(
                        data_user_id,
                        "chat_cmd",
                        {"name": "cv_creation_interrupt", "from_phase": journey_now.phase},
                    )
                    from company_discovery.journey import (
                        _CV_BUILD_ORDER,
                        UserJourney,
                        cv_build_prompt_for,
                    )

                    # Set journey into the sectional-build state so the
                    # next user message answers the first question.
                    fresh = UserJourney()
                    fresh.phase = PHASE_CV_CHECK
                    fresh.cv_status = "building"
                    fresh.cv_build_step = _CV_BUILD_ORDER[0]
                    STATE._journey_save(data_user_id, fresh)
                    reply = (
                        "OK — 5 quick questions and you'll have a CV "
                        "ready. " + cv_build_prompt_for(_CV_BUILD_ORDER[0])
                    )
                    session.history.append(ChatTurn(role="assistant", content=reply))
                    STATE.chat_session_persist(data_user_id)
                    self.send_json(
                        {
                            "reply": reply,
                            "journeyPhase": fresh.phase,
                            "session": session.to_dict(),
                        }
                    )
                    return
                if in_journey and looks_like_new_search_intent(user_message, journey_now.phase):
                    STATE.log_analytics(
                        data_user_id,
                        "chat_cmd",
                        {"name": "new_search_interrupt", "from_phase": journey_now.phase},
                    )
                    from company_discovery.journey import UserJourney

                    STATE._journey_save(data_user_id, UserJourney())
                    # If we can extract a role from the message,
                    # fire find_jobs directly — no need to ask the
                    # questions again. Otherwise kick off the
                    # journey at the role-question.
                    nl_args = extract_keyword_args("find_jobs", user_message)
                    if nl_args.get("query"):
                        result = STATE.chat_handler_find_jobs(
                            data_user_id,
                            {
                                "query": nl_args["query"],
                                "location": nl_args.get("location") or None,
                            },
                        )
                        reply = result.get("message") or "Done."
                        session.history.append(ChatTurn(role="assistant", content=reply))
                        STATE.chat_session_persist(data_user_id)
                        payload_out = {
                            "reply": reply,
                            "executed": "find_jobs",
                            "result": result,
                            "session": session.to_dict(),
                        }
                        for key in ("navigateTo", "totalJobs", "jobs", "jobType", "categories"):
                            if key in result:
                                payload_out[key] = result[key]
                        self.send_json(payload_out)
                        return
                    # No role extracted — start the journey at
                    # PHASE_DISCOVER so it asks "what kind of role?".
                    journey_result = STATE.chat_journey_step(
                        data_user_id,
                        "",
                    )
                    reply = journey_result.get("message") or "(continuing)"
                    session.history.append(ChatTurn(role="assistant", content=reply))
                    STATE.chat_session_persist(data_user_id)
                    self.send_json(
                        {
                            "reply": reply,
                            "journeyPhase": journey_result.get("journeyPhase"),
                            "session": session.to_dict(),
                        }
                    )
                    return
                if not in_journey and should_auto_start(journey_now, user_message):
                    # Start fresh journey + dispatch the very first
                    # turn so the user sees the welcome immediately.
                    STATE.log_analytics(data_user_id, "chat_cmd", {"name": "start_job_journey"})
                    from company_discovery.journey import UserJourney

                    STATE._journey_save(data_user_id, UserJourney())
                    journey_result = STATE.chat_journey_step(
                        data_user_id,
                        user_message,
                    )
                    reply = journey_result.get("message") or "(continuing)"
                    session.history.append(
                        ChatTurn(role="assistant", content=reply),
                    )
                    STATE.chat_session_persist(data_user_id)
                    self.send_json(
                        {
                            "reply": reply,
                            "journeyPhase": journey_result.get("journeyPhase"),
                            "invoked": journey_result.get("invoked"),
                            "letter": journey_result.get("letter"),
                            "suggestions": journey_result.get("suggestions"),
                            "totalJobs": journey_result.get("totalJobs"),
                            "jobs": journey_result.get("jobs"),
                            "categories": journey_result.get("categories"),
                            "navigateTo": journey_result.get("navigateTo"),
                            "session": session.to_dict(),
                        }
                    )
                    return
                if in_journey and (
                    session.pending is None or not session.pending.awaiting_confirmation
                ):
                    # Route the message through the journey state
                    # machine. Skip when a pending command is awaiting
                    # explicit confirmation (yes/no) — that's part of
                    # the typed-command flow and takes priority.
                    journey_result = STATE.chat_journey_step(
                        data_user_id,
                        user_message,
                    )
                    reply = journey_result.get("message") or "(continuing)"
                    session.history.append(
                        ChatTurn(role="assistant", content=reply),
                    )
                    STATE.chat_session_persist(data_user_id)
                    self.send_json(
                        {
                            "reply": reply,
                            "journeyPhase": journey_result.get("journeyPhase"),
                            "invoked": journey_result.get("invoked"),
                            "letter": journey_result.get("letter"),
                            "suggestions": journey_result.get("suggestions"),
                            "totalJobs": journey_result.get("totalJobs"),
                            "jobs": journey_result.get("jobs"),
                            "categories": journey_result.get("categories"),
                            "navigateTo": journey_result.get("navigateTo"),
                            "session": session.to_dict(),
                        }
                    )
                    return

                # ── If a command is pending confirmation, the next user
                # message is treated as a yes/no/edit, not a new command.
                if session.pending and session.pending.awaiting_confirmation:
                    if is_confirmation_yes(user_message):
                        cmd_name = session.pending.command_name
                        args = dict(session.pending.args)
                        result = STATE.chat_execute_command(data_user_id, cmd_name, args)
                        session.pending = None
                        reply = result.get("message") or "Done."
                        session.history.append(ChatTurn(role="assistant", content=reply))
                        STATE.chat_session_persist(data_user_id)
                        self.send_json(
                            {
                                "reply": reply,
                                "journeyPhase": STATE._journey_load(data_user_id).phase,
                                "executed": cmd_name,
                                "result": result,
                                "session": session.to_dict(),
                            }
                        )
                        return
                    if is_confirmation_no(user_message):
                        cancelled = session.pending.command_name
                        session.pending = None
                        reply = f"Cancelled — {cancelled} not run."
                        session.history.append(ChatTurn(role="assistant", content=reply))
                        STATE.chat_session_persist(data_user_id)
                        self.send_json(
                            {
                                "reply": reply,
                                "journeyPhase": STATE._journey_load(data_user_id).phase,
                                "cancelled": cancelled,
                                "session": session.to_dict(),
                            }
                        )
                        return
                    # Anything else mid-confirmation is treated as "user
                    # changed their mind / wants to edit" — restart the
                    # elicitation for the same command.
                    session.pending.awaiting_confirmation = False
                    # Fall through to the elicitation loop below.

                # ── If we're mid-elicitation (waiting for a specific
                # param), validate this message as the answer to that
                # param and either advance or re-prompt.
                if session.pending and session.pending.awaiting:
                    cmd = CHAT_REGISTRY[session.pending.command_name]
                    param = next(
                        (p for p in cmd.params if p.name == session.pending.awaiting), None
                    )
                    if param is None:
                        # Defensive — should not happen.
                        session.pending = None
                    else:
                        # Empty replies on optional fields = "skip this".
                        if not param.required and not user_message:
                            session.pending.args[param.name] = None
                            session.pending.awaiting = None
                        else:
                            ok, val = fill_param_from_message(cmd, param, user_message)
                            if not ok:
                                reply = f"{val} {param.prompt}"
                                session.history.append(ChatTurn(role="assistant", content=reply))
                                STATE.chat_session_persist(data_user_id)
                                self.send_json(
                                    {
                                        "reply": reply,
                                        "journeyPhase": STATE._journey_load(data_user_id).phase,
                                        "awaiting": param.name,
                                        "session": session.to_dict(),
                                    }
                                )
                                return
                            session.pending.args[param.name] = val
                            session.pending.awaiting = None

                # ── If no pending command, try to route the message.
                if session.pending is None:
                    routed: tuple[str, str] | None = None
                    slash = parse_slash_command(user_message)
                    if slash:
                        routed = slash
                    else:
                        # Try keyword router first (cheap, no AI call).
                        kw = keyword_route(user_message)
                        if kw:
                            routed = (kw, "")
                            # Best-effort args extraction from natural-language
                            # so the user doesn't have to repeat themselves.
                            # E.g. "find bartender jobs in Berlin" → pre-fill
                            # query=Bartender, location=Berlin so the server
                            # only needs the confirmation prompt.
                            _ai_extracted_args = extract_keyword_args(kw, user_message)
                        else:
                            # AI router as last resort. The ``_full``
                            # variant ALSO returns any args the AI was
                            # able to extract verbatim from the user
                            # message (the JSON-output prompt) — we
                            # then pre-fill the pending command's args
                            # so the user doesn't have to type the same
                            # info twice. Each value still passes its
                            # per-param validator below, so a malformed
                            # URL still re-prompts cleanly.
                            ai_name, ai_args = STATE.chat_ai_route_full(
                                data_user_id, user_message, session.history
                            )
                            if ai_name:
                                routed = (ai_name, "")
                                # Stash for the rest-pre-fill below.
                                _ai_extracted_args = ai_args
                    if routed is None:
                        # R19: context-aware fallback. Read the
                        # journey state so a user with active search
                        # results gets surfaced the next-best action
                        # (drill into a category) instead of the
                        # generic "type help" dead-end.
                        reply = STATE._build_contextual_fallback(
                            data_user_id,
                            user_message,
                        )
                        session.history.append(ChatTurn(role="assistant", content=reply))
                        STATE.chat_session_persist(data_user_id)
                        self.send_json(
                            {
                                "reply": reply,
                                "journeyPhase": STATE._journey_load(data_user_id).phase,
                                "session": session.to_dict(),
                            }
                        )
                        return
                    cmd_name, rest = routed
                    session.pending = PendingCommand(command_name=cmd_name)
                    # Pre-fill any inline args from the slash form.
                    if rest:
                        inline = parse_slash_inline_args(cmd_name, rest)
                        for k, v in inline.items():
                            cmd = CHAT_REGISTRY[cmd_name]
                            param = next((p for p in cmd.params if p.name == k), None)
                            if param is None:
                                continue
                            ok, val = fill_param_from_message(cmd, param, v)
                            if ok:
                                session.pending.args[k] = val
                    # Pre-fill args the AI extracted from natural language.
                    # Each value runs through the per-param validator so
                    # malformed URLs / empty strings still re-prompt.
                    ai_args = locals().get("_ai_extracted_args", {}) or {}
                    if ai_args:
                        cmd = CHAT_REGISTRY[cmd_name]
                        for k, v in ai_args.items():
                            if not isinstance(k, str):
                                continue
                            param = next((p for p in cmd.params if p.name == k), None)
                            if param is None:
                                continue
                            # Coerce non-strings to string for the validator.
                            ok, val = fill_param_from_message(cmd, param, str(v))
                            if ok and k not in session.pending.args:
                                session.pending.args[k] = val

                # ── Determine the next missing required param.
                cmd = CHAT_REGISTRY[session.pending.command_name]
                missing = next_missing_param(cmd, session.pending.args)
                # Commands with NO params (e.g., help) execute immediately
                # without a confirmation step.
                if not cmd.params:
                    result = STATE.chat_execute_command(
                        data_user_id, cmd.name, session.pending.args
                    )
                    session.pending = None
                    reply = result.get("message") or "Done."
                    session.history.append(ChatTurn(role="assistant", content=reply))
                    STATE.chat_session_persist(data_user_id)
                    self.send_json(
                        {
                            "reply": reply,
                            "journeyPhase": STATE._journey_load(data_user_id).phase,
                            "executed": cmd.name,
                            "result": result,
                            "session": session.to_dict(),
                        }
                    )
                    return
                if missing:
                    session.pending.awaiting = missing.name
                    reply = missing.prompt
                    if missing.hint:
                        reply += f"\n_({missing.hint})_"
                    session.history.append(ChatTurn(role="assistant", content=reply))
                    STATE.chat_session_persist(data_user_id)
                    self.send_json(
                        {
                            "reply": reply,
                            "journeyPhase": STATE._journey_load(data_user_id).phase,
                            "awaiting": missing.name,
                            "session": session.to_dict(),
                        }
                    )
                    return
                # All required params filled — also offer optional ones.
                next_optional = next(
                    (
                        p
                        for p in cmd.params
                        if not p.required and p.name not in session.pending.args
                    ),
                    None,
                )
                if next_optional:
                    session.pending.awaiting = next_optional.name
                    reply = next_optional.prompt
                    if next_optional.hint:
                        reply += f"\n_({next_optional.hint})_"
                    session.history.append(ChatTurn(role="assistant", content=reply))
                    STATE.chat_session_persist(data_user_id)
                    self.send_json(
                        {
                            "reply": reply,
                            "journeyPhase": STATE._journey_load(data_user_id).phase,
                            "awaiting": next_optional.name,
                            "optional": True,
                            "session": session.to_dict(),
                        }
                    )
                    return
                # R19: read-only commands (find_jobs, show_view,
                # suggest_*, draft_*) skip the confirmation gate.
                # Asking permission to think is friction; only
                # destructive operations need the yes/no prompt.
                if not cmd.requires_confirmation:
                    result = STATE.chat_execute_command(
                        data_user_id, cmd.name, session.pending.args
                    )
                    session.pending = None
                    reply = result.get("message") or "Done."
                    session.history.append(ChatTurn(role="assistant", content=reply))
                    STATE.chat_session_persist(data_user_id)
                    payload_out = {
                        "reply": reply,
                        "executed": cmd.name,
                        "result": result,
                        "session": session.to_dict(),
                    }
                    # Surface navigateTo + extra payload fields the
                    # handler returned so the client can react.
                    for key in (
                        "navigateTo",
                        "totalJobs",
                        "letter",
                        "suggestions",
                        "jobs",
                        "jobType",
                    ):
                        if key in result:
                            payload_out[key] = result[key]
                    self.send_json(payload_out)
                    return
                # Show confirmation prompt.
                session.pending.awaiting_confirmation = True
                reply = cmd.confirmation_message(session.pending.args)
                session.history.append(ChatTurn(role="assistant", content=reply))
                STATE.chat_session_persist(data_user_id)
                self.send_json(
                    {
                        "reply": reply,
                        "journeyPhase": STATE._journey_load(data_user_id).phase,
                        "awaitingConfirmation": True,
                        "pendingArgs": session.pending.args,
                        "session": session.to_dict(),
                    }
                )
                return

            if parsed.path == "/api/chat/reset":
                STATE.chat_reset(data_user_id)
                self.send_json({"reply": "Chat reset.", "session": None})
                return

            # ---------------- CV Builder API ----------------
            # Deterministic, fact-grounded CV creation. The state machine
            # lives in cv_builder.py; routes here are thin handlers that
            # update / read the per-user in-memory session.
            if parsed.path == "/api/cv-builder/start":
                STATE.cv_builder_reset(data_user_id)
                state = STATE.cv_builder_state_for(data_user_id)
                state.current_section_id = next_section_id(None)
                section = get_section(state.current_section_id)
                self.send_json(
                    {
                        "state": state.to_dict(),
                        "currentSection": _serialise_cv_section(section),
                        "sectionOrder": [s.section_id for s in SECTIONS],
                    }
                )
                return

            if parsed.path == "/api/cv-builder/state":
                state = STATE.cv_builder_state_for(data_user_id)
                section = (
                    get_section(state.current_section_id) if state.current_section_id else None
                )
                self.send_json(
                    {
                        "state": state.to_dict(),
                        "currentSection": _serialise_cv_section(section) if section else None,
                        "sectionOrder": [s.section_id for s in SECTIONS],
                    }
                )
                return

            if (
                len(parts) == 4
                and parts[:2] == ["api", "cv-builder"]
                and parts[2] == "section"
                and parts[3] not in {"finish"}
            ):
                # /api/cv-builder/section/{section_id} — submit one
                # section's user answers. AI format runs on the
                # designated 'raw' field(s); fact-ratio gate decides
                # whether to store the AI rewrite or the raw text.
                #
                # Pass {"action": "skip"} to advance past an optional
                # section (certifications, projects) without adding any
                # entry — those sections' fields are required *if* an
                # entry is being created, but the section itself is not.
                section_id = parts[3]
                try:
                    section = get_section(section_id)
                except KeyError:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST,
                        "unknown_section",
                        f"Unknown CV section: {section_id}",
                    )
                    return
                state = STATE.cv_builder_state_for(data_user_id)
                if str(payload.get("action") or "").lower() == "skip":
                    state.current_section_id = next_section_id(section.section_id)
                    next_section_obj = (
                        get_section(state.current_section_id) if state.current_section_id else None
                    )
                    self.send_json(
                        {
                            "state": state.to_dict(),
                            "currentSection": (
                                _serialise_cv_section(next_section_obj)
                                if next_section_obj
                                else None
                            ),
                            "aiMeta": {},
                            "finished": state.current_section_id is None,
                        }
                    )
                    return
                answers = payload.get("answers")
                if not isinstance(answers, dict):
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "invalid_answers", "answers must be a JSON object"
                    )
                    return
                # Validate required fields are present.
                missing = [
                    q.key
                    for q in section.questions
                    if q.required and not str(answers.get(q.key) or "").strip()
                ]
                if missing:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST,
                        "missing_required",
                        f"Missing required fields: {', '.join(missing)}",
                    )
                    return
                # Run AI format on each *_raw field.
                stored: dict[str, Any] = {}
                ai_meta: dict[str, Any] = {}
                for q in section.questions:
                    val = answers.get(q.key)
                    if val is None:
                        continue
                    if isinstance(val, str):
                        val = val.strip()
                    stored[q.key] = val
                    if isinstance(val, str) and q.key.endswith("_raw") and val:
                        formatted, ratio, accepted = STATE.cv_builder_format_section(
                            data_user_id,
                            section.section_id,
                            q.key,
                            val,
                        )
                        # The formatted output is stored under the 'formatted' key
                        # so the assembly step prefers it over the raw text.
                        stored["formatted"] = formatted
                        ai_meta["factRatio"] = ratio
                        ai_meta["aiAccepted"] = accepted
                if section.repeatable:
                    state.sections.setdefault(section.section_id, []).append(stored)
                else:
                    state.sections[section.section_id] = [stored]
                # Advance unless the section is repeatable AND the user
                # explicitly says they want another entry. Default is
                # 'advance' so the wizard never gets stuck.
                advance = bool(payload.get("advance", True))
                if advance:
                    state.current_section_id = next_section_id(section.section_id)
                next_section_obj = (
                    get_section(state.current_section_id) if state.current_section_id else None
                )
                self.send_json(
                    {
                        "state": state.to_dict(),
                        "currentSection": (
                            _serialise_cv_section(next_section_obj) if next_section_obj else None
                        ),
                        "aiMeta": ai_meta,
                        "finished": state.current_section_id is None,
                    }
                )
                return

            if parsed.path == "/api/cv-builder/finish":
                state = STATE.cv_builder_state_for(data_user_id)
                profile = STATE.profile_for(user_id)
                cv_markdown = assemble_cv_markdown(
                    state,
                    photo_data_uri=profile.cv_photo_data_uri,
                )
                # Persist into the user's profile.cv_text so the rest
                # of the product (Fit, Tailor, Skill-gap) picks it up.
                profile.cv_text = cv_markdown
                STATE.repository.save_user_profile(profile)
                STATE.cv_builder_reset(data_user_id)
                self.send_json(
                    {
                        "cvText": cv_markdown,
                        "cvLength": len(cv_markdown),
                        "bootstrap": STATE.bootstrap(user_id),
                    }
                )
                return

            if parsed.path == "/api/saved-searches":
                try:
                    record = STATE.save_saved_search(data_user_id, payload)
                except ValueError as error:
                    code = str(error)
                    if code == "plan_saved_search_limit":
                        self.send_error_json(
                            HTTPStatus.PAYMENT_REQUIRED,
                            code,
                            "Your plan caps the number of saved searches. Upgrade or delete one before adding another.",
                        )
                    else:
                        self.send_error_json(HTTPStatus.BAD_REQUEST, code, code)
                    return
                self.send_json(
                    {
                        "savedSearch": record,
                        "savedSearches": STATE._saved_searches_with_alerts(user_id),
                    }
                )
                return
            if parsed.path == "/api/push/subscribe":
                endpoint = str(payload.get("endpoint") or "").strip()
                keys = payload.get("keys") or {}
                p256dh = str(keys.get("p256dh") or "").strip()
                auth_key = str(keys.get("auth") or "").strip()
                if not endpoint or not p256dh or not auth_key:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST,
                        "missing_keys",
                        "endpoint + keys.p256dh + keys.auth required",
                    )
                    return
                existing = STATE.repository.find_push_subscription(endpoint)
                if existing is not None:
                    if existing.user_id != user_id:
                        self.send_error_json(
                            HTTPStatus.FORBIDDEN,
                            "endpoint_owned_by_other",
                            "Subscription belongs to another user",
                        )
                        return
                    existing.p256dh = p256dh
                    existing.auth = auth_key
                    existing.user_agent = self.headers.get("User-Agent", "")[:200]
                    STATE.repository.save_push_subscription(existing)
                    sub_id = existing.id
                else:
                    sub = PushSubscription(
                        user_id=user_id,
                        endpoint=endpoint,
                        p256dh=p256dh,
                        auth=auth_key,
                        user_agent=self.headers.get("User-Agent", "")[:200],
                    )
                    STATE.repository.save_push_subscription(sub)
                    sub_id = sub.id
                self.send_json({"status": "ok", "subscriptionId": sub_id})
                return
            if parsed.path == "/api/push/unsubscribe":
                endpoint = str(payload.get("endpoint") or "").strip()
                if not endpoint:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "missing_endpoint", "endpoint required"
                    )
                    return
                existing = STATE.repository.find_push_subscription(endpoint)
                if existing is not None and existing.user_id == user_id:
                    STATE.repository.delete_push_subscription(existing.id)
                self.send_json({"status": "ok"})
                return
            if parsed.path == "/api/push/test":
                if not is_push_configured():
                    self.send_error_json(
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        "push_unavailable",
                        "Push is not configured. Set DIRECTJOB_VAPID_PUBLIC_KEY and DIRECTJOB_VAPID_PRIVATE_KEY.",
                    )
                    return
                subs = STATE.repository.list_push_subscriptions(user_id)
                if not subs:
                    self.send_error_json(
                        HTTPStatus.NOT_FOUND,
                        "no_subscriptions",
                        "No push subscriptions for this user.",
                    )
                    return
                payload_obj = PushPayload(
                    title=str(payload.get("title") or "Helpmefindthejob"),
                    body=str(payload.get("body") or "Test notification."),
                    url="/",
                )
                outcomes: list[dict[str, Any]] = []
                for sub in subs:
                    try:
                        send_push(sub, payload_obj)
                        outcomes.append({"id": sub.id, "status": "sent"})
                    except PushUnavailableError as error:
                        outcomes.append(
                            {"id": sub.id, "status": "unavailable", "error": str(error)}
                        )
                    except Exception as error:  # noqa: BLE001 — push service may 404/410
                        outcomes.append(
                            {"id": sub.id, "status": "error", "error": str(error)[:200]}
                        )
                self.send_json({"outcomes": outcomes})
                return
            if parsed.path == "/api/workspaces/active":
                workspace_id = str(
                    payload.get("workspaceId") or payload.get("workspace_id") or ""
                ).strip()
                if not workspace_id:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "missing_workspace", "workspaceId is required"
                    )
                    return
                try:
                    STATE.resolve_workspace_owner(user_id, workspace_id)
                except ValueError:
                    self.send_error_json(
                        HTTPStatus.FORBIDDEN,
                        "workspace_forbidden",
                        "You are not a member of that workspace.",
                    )
                    return
                profile = STATE.profile_for(user_id)
                profile.active_workspace_id = workspace_id
                STATE.repository.save_user_profile(profile)
                self.send_json(
                    {
                        "profile": STATE._profile_payload(profile),
                        "bootstrap": STATE.bootstrap(user_id),
                    }
                )
                return

            if len(parts) == 4 and parts[:2] == ["api", "workspaces"] and parts[3] == "invite":
                workspace_id = parts[2]
                inviter_membership = STATE.repository.find_workspace_membership(
                    user_id, workspace_id
                )
                if inviter_membership is None or inviter_membership.role not in ("owner", "admin"):
                    self.send_error_json(
                        HTTPStatus.FORBIDDEN,
                        "workspace_forbidden",
                        "Only workspace owners or admins can invite.",
                    )
                    return
                invitee_email = str(payload.get("email") or "").strip().lower()
                if not invitee_email or "@" not in invitee_email:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "invalid_email", "email is required"
                    )
                    return
                # v2 invite: target user must already exist on the platform.
                target_user = next(
                    (u for u in STATE.auth_store.list_users() if u.email == invitee_email),
                    None,
                )
                if target_user is None:
                    self.send_error_json(
                        HTTPStatus.NOT_FOUND,
                        "user_not_found",
                        "Invitee must already have an account. Send them a regular signup invite first.",
                    )
                    return
                existing = STATE.repository.find_workspace_membership(target_user.id, workspace_id)
                if existing is not None:
                    self.send_json({"status": "already_member", "membershipId": existing.id})
                    return
                membership = WorkspaceMembership(
                    user_id=target_user.id,
                    workspace_id=workspace_id,
                    workspace_owner_id=inviter_membership.workspace_owner_id,
                    role="member",
                    label=inviter_membership.label,
                )
                STATE.repository.save_workspace_membership(membership)
                STATE.log_analytics(
                    user_id,
                    "workspace_invite",
                    {"workspaceId": workspace_id, "email": invitee_email},
                )
                self.send_json(
                    {
                        "status": "added",
                        "membershipId": membership.id,
                        "userId": target_user.id,
                    }
                )
                return

            if len(parts) == 4 and parts[:2] == ["api", "saved-searches"] and parts[3] == "run-now":
                try:
                    result = STATE.run_saved_search(data_user_id, parts[2])
                except KeyError:
                    self.send_error_json(
                        HTTPStatus.NOT_FOUND, "not_found", "Saved search not found"
                    )
                    return
                self.send_json(
                    {
                        "result": result,
                        "savedSearches": STATE._saved_searches_with_alerts(data_user_id),
                        "bootstrap": STATE.bootstrap(user_id),
                    }
                )
                return
            if len(parts) == 4 and parts[:2] == ["api", "saved-searches"] and parts[3] == "matches":
                search = STATE.repository.saved_searches.get(parts[2])
                if not search or search.user_id != user_id:
                    self.send_error_json(
                        HTTPStatus.NOT_FOUND, "not_found", "Saved search not found"
                    )
                    return
                jobs = STATE.repository.list_discovered_jobs(user_id)
                companies_by_id = {c.id: c for c in STATE.repository.list_companies(user_id)}
                only_unseen = bool(payload.get("unseenOnly"))
                if only_unseen:
                    matches = unseen_matches_for_search(search, jobs, companies_by_id)
                else:
                    matches = matches_for_search(search, jobs, companies_by_id)
                self.send_json(
                    {
                        "matches": [asdict(job) for job in matches],
                        "alerts": alert_summary_for_search(search, jobs, companies_by_id),
                    }
                )
                return
            if (
                len(parts) == 4
                and parts[:2] == ["api", "saved-searches"]
                and parts[3] == "mark-seen"
            ):
                search = STATE.repository.saved_searches.get(parts[2])
                if not search or search.user_id != user_id:
                    self.send_error_json(
                        HTTPStatus.NOT_FOUND, "not_found", "Saved search not found"
                    )
                    return
                search.last_seen_at = now_utc()
                STATE.repository.save_saved_search(search)
                self.send_json(
                    {
                        "savedSearch": asdict(search),
                        "savedSearches": STATE._saved_searches_with_alerts(user_id),
                    }
                )
                return
            if parsed.path == "/api/digest/send":
                text = STATE.send_user_digest(user=session.user)
                self.send_json({"status": "sent", "preview": text})
                return
            if parsed.path == "/api/admin/billing":
                if not self.require_admin(session):
                    return
                try:
                    sub = STATE.update_subscription(
                        actor=session.user,
                        plan_id=payload.get("planId"),
                        status=payload.get("status"),
                        seats=payload.get("seats"),
                        notes=payload.get("notes"),
                        customer_email=payload.get("customerEmail"),
                    )
                except ValueError as error:
                    self.send_error_json(HTTPStatus.BAD_REQUEST, str(error), str(error))
                    return
                self.send_json({"subscription": sub.to_dict()})
                return
            if parsed.path == "/api/admin/email/test":
                if not self.require_admin(session):
                    return
                target = str(payload.get("target") or session.user.email)
                try:
                    result = STATE.send_test_email(actor=session.user, target=target)
                except ValueError as error:
                    self.send_error_json(HTTPStatus.BAD_REQUEST, str(error), str(error))
                    return
                self.send_json(result)
                return
            if parsed.path == "/api/admin/billing/checkout":
                if not self.require_admin(session):
                    return
                if not isinstance(STATE.billing_backend, StripeBillingBackend):
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST,
                        "stripe_disabled",
                        "Stripe backend not active. Set DIRECTJOB_BILLING_BACKEND=stripe and credentials.",
                    )
                    return
                plan_id = str(payload.get("planId") or "")
                if not plan_id:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "missing_plan", "planId is required"
                    )
                    return
                try:
                    result = STATE.billing_backend.create_checkout_session(
                        plan_id=plan_id,
                        customer_email=payload.get("customerEmail") or session.user.email,
                    )
                except ValueError as error:
                    code = str(error)
                    self.send_error_json(HTTPStatus.BAD_REQUEST, code, code)
                    return
                except RuntimeError as error:
                    # Strip raw Stripe error detail before surfacing it to the admin —
                    # the upstream message can include verbose request/response context.
                    raw_code = str(error).split(":", 1)[0].strip() or "billing_backend_error"
                    self.send_error_json(
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        raw_code,
                        "Stripe call failed. Check the configured Stripe credentials and product/price IDs.",
                    )
                    return
                STATE.record_admin_action(
                    actor=session.user,
                    target=None,
                    action="create_checkout_session",
                    details={"planId": plan_id, "sessionId": result.get("id")},
                )
                self.send_json({"checkout": result})
                return
            if parsed.path == "/api/account/deletion-request":
                ticket = STATE.request_account_deletion(
                    user=session.user,
                    reason=str(payload.get("reason") or ""),
                )
                self.send_json({"ticket": ticket, "emailSent": True}, HTTPStatus.CREATED)
                return
            if parsed.path == "/api/account/deletion-cancel":
                self.send_json(STATE.cancel_account_deletion(session.user))
                return
            if parsed.path == "/api/demo-data/seed":
                created = STATE.seed_demo_data(STATE.effective_user_id(user_id))
                self.send_json(
                    {"seeded": created, "bootstrap": STATE.bootstrap(user_id)}, HTTPStatus.CREATED
                )
                return
            if parsed.path == "/api/billing/portal":
                if not isinstance(STATE.billing_backend, StripeBillingBackend):
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST,
                        "stripe_disabled",
                        "Stripe backend not active. Self-managed billing is unavailable on the manual backend.",
                    )
                    return
                subscription = STATE.get_subscription()
                customer_id = subscription.customer_id or ""
                if not customer_id:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST,
                        "no_customer",
                        "No Stripe customer linked yet. Complete a checkout first.",
                    )
                    return
                return_url = STATE.public_url_for("/?billing=portal-return")
                try:
                    result = STATE.billing_backend.create_portal_session(
                        customer_id=customer_id,
                        return_url=return_url,
                    )
                except ValueError as error:
                    code = str(error)
                    self.send_error_json(HTTPStatus.BAD_REQUEST, code, code)
                    return
                except RuntimeError as error:
                    raw_code = str(error).split(":", 1)[0].strip() or "billing_backend_error"
                    self.send_error_json(
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        raw_code,
                        "Stripe portal call failed. Operator has been notified.",
                    )
                    return
                STATE.log_analytics(
                    user_id, "billing_portal_opened", {"sessionId": result.get("id")}
                )
                self.send_json({"portal": result})
                return
            if parsed.path == "/api/analytics/event":
                kind = str(payload.get("kind") or "").strip()
                if not kind:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "missing_kind", "Event kind is required"
                    )
                    return
                event = STATE.log_analytics(user_id, kind, payload.get("payload") or {})
                self.send_json({"event": event}, HTTPStatus.CREATED)
                return
            if parsed.path == "/api/support":
                ticket = STATE.submit_support_ticket(
                    user=session.user,
                    subject=str(payload.get("subject") or ""),
                    body=str(payload.get("body") or ""),
                    contact_email=payload.get("contactEmail"),
                )
                self.send_json({"ticket": ticket}, HTTPStatus.CREATED)
                return
            if (
                len(parts) == 4
                and parts[:2] == ["api", "watchlist-templates"]
                and parts[3] == "apply"
            ):
                try:
                    result = STATE.apply_watchlist_template(data_user_id, parts[2])
                except ValueError as error:
                    self.send_error_json(HTTPStatus.BAD_REQUEST, str(error), str(error))
                    return
                self.send_json({"result": result, "bootstrap": STATE.bootstrap(user_id)})
                return
            if (
                len(parts) == 4
                and parts[:2] == ["api", "imported-jobs"]
                and parts[3] == "application"
            ):
                try:
                    job = STATE.update_application_state(data_user_id, parts[2], payload)
                except KeyError:
                    self.send_error_json(
                        HTTPStatus.NOT_FOUND, "not_found", "Imported job not found"
                    )
                    return
                except ValueError as error:
                    self.send_error_json(HTTPStatus.BAD_REQUEST, str(error), str(error))
                    return
                self.send_json({"job": job, "bootstrap": STATE.bootstrap(user_id)})
                return
            if len(parts) == 4 and parts[:2] == ["api", "imported-jobs"] and parts[3] == "share":
                try:
                    job = STATE.set_share_enabled(
                        data_user_id, parts[2], bool(payload.get("enabled"))
                    )
                except KeyError:
                    self.send_error_json(
                        HTTPStatus.NOT_FOUND, "not_found", "Imported job not found"
                    )
                    return
                share_url = (
                    STATE.public_url_for(f"/share/job/{job.id}") if job.share_enabled else None
                )
                self.send_json(
                    {"job": job, "shareUrl": share_url, "bootstrap": STATE.bootstrap(user_id)}
                )
                return

            if parsed.path == "/api/ai-provider":
                try:
                    config = STATE.update_ai_provider(user_id, payload)
                except ValueError as error:
                    code = str(error)
                    if code == "plan_ai_mode_locked":
                        self.send_error_json(
                            HTTPStatus.PAYMENT_REQUIRED,
                            code,
                            "Your plan does not include this AI mode. Manual handoff stays available; upgrade to unlock bring-your-own-key or Managed AI.",
                        )
                    else:
                        self.send_error_json(HTTPStatus.BAD_REQUEST, code, code)
                    return
                self.send_json(
                    {"aiProvider": config.public_dict(), "bootstrap": STATE.bootstrap(user_id)}
                )
                return

            if parsed.path == "/api/watchlist/scan":
                result = STATE.run_watchlist_scan(user_id, trigger="manual")
                self.send_json({"result": result, "bootstrap": STATE.bootstrap(user_id)})
                return

            if parsed.path == "/api/watchlist/schedule":
                schedule = STATE.update_watchlist_schedule(user_id, payload)
                self.send_json(
                    {"watchlistSchedule": schedule, "bootstrap": STATE.bootstrap(user_id)}
                )
                return

            if parsed.path == "/api/demo/seed":
                demo = STATE.seed_demo(user_id)
                self.send_json(
                    {"demo": demo, "bootstrap": STATE.bootstrap(user_id)}, HTTPStatus.CREATED
                )
                return

            if parsed.path == "/api/data/import":
                result = STATE.import_data(user_id, payload)
                self.send_json({"result": result, "bootstrap": STATE.bootstrap(user_id)})
                return

            if (
                len(parts) == 4
                and parts[:2] == ["api", "companies"]
                and parts[3] == "find-career-page"
            ):
                result = STATE.service.find_company_career_page(data_user_id, parts[2])
                self.send_json({"result": result, "bootstrap": STATE.bootstrap(user_id)})
                return

            if len(parts) == 4 and parts[:2] == ["api", "companies"] and parts[3] == "scan":
                career_page_url = payload.get("careerPageUrl") or None
                if career_page_url:
                    STATE.service.update_company(
                        data_user_id, parts[2], career_page_url=career_page_url
                    )
                run = STATE.start_scan(data_user_id, parts[2], career_page_url)
                self.send_json({"run": run, "bootstrap": STATE.bootstrap(user_id)})
                return

            if len(parts) == 4 and parts[:2] == ["api", "companies"] and parts[3] == "extract-html":
                company = STATE.repository.get_company(data_user_id, parts[2])
                page_url = payload.get("pageUrl") or company.career_page_url or company.website_url
                jobs = STATE.service.extract_direct_jobs_from_company_site(
                    company,
                    page_url,
                    payload.get("html", ""),
                )
                saved = []
                errors = []
                for job in jobs:
                    duplicate = STATE.repository.find_duplicate_discovered_job(job)
                    if duplicate:
                        errors.append(
                            {
                                "code": "duplicate_discovered_job",
                                "sourceUrl": job.source_url,
                                "duplicateId": duplicate.id,
                            }
                        )
                    else:
                        saved.append(STATE.repository.save_discovered_job(job))
                self.send_json(
                    {"jobs": saved, "errors": errors, "bootstrap": STATE.bootstrap(user_id)}
                )
                return

            if len(parts) == 4 and parts[:2] == ["api", "discovered-jobs"] and parts[3] == "import":
                imported = STATE.service.import_discovered_job(data_user_id, parts[2])
                self.send_json({"job": imported, "bootstrap": STATE.bootstrap(user_id)})
                return

            if parsed.path == "/api/discovered-jobs/bulk-import":
                # Multi-select import. Accepts ``{"ids": ["...", ...]}``.
                # Reports per-id ``{"id": ..., "status": "imported" | "error", ...}``
                # so the client can show a partial-success toast.
                ids = payload.get("ids") or []
                if not isinstance(ids, list):
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "invalid_ids", "ids must be a list"
                    )
                    return
                ids = [str(x) for x in ids if str(x).strip()][:100]
                outcomes: list[dict[str, Any]] = []
                imported_count = 0
                for did in ids:
                    try:
                        imported = STATE.service.import_discovered_job(data_user_id, did)
                        outcomes.append(
                            {"id": did, "status": "imported", "importedJobId": imported.id}
                        )
                        imported_count += 1
                    except KeyError:
                        outcomes.append({"id": did, "status": "error", "code": "not_found"})
                    except ValueError as error:
                        outcomes.append({"id": did, "status": "error", "code": str(error)})
                STATE.log_analytics(
                    user_id,
                    "bulk_import",
                    {"requested": len(ids), "imported": imported_count},
                )
                self.send_json(
                    {
                        "outcomes": outcomes,
                        "imported": imported_count,
                        "bootstrap": STATE.bootstrap(user_id),
                    }
                )
                return

            if (
                len(parts) == 4
                and parts[:2] == ["api", "imported-jobs"]
                and parts[3] == "prepare-brief"
            ):
                imported = STATE.repository.imported_jobs[parts[2]]
                if imported.user_id != data_user_id:
                    raise KeyError(parts[2])
                profile = STATE.profile_for(user_id)
                brief = build_job_decision_brief_prompt(
                    imported,
                    STATE.ai_provider_for(user_id),
                    profile,
                )
                imported.analysis_status = "brief_ready"
                STATE.repository.save_imported_job(imported)
                self.send_json({"brief": brief, "bootstrap": STATE.bootstrap(user_id)})
                return

            if (
                len(parts) == 4
                and parts[:2] == ["api", "imported-jobs"]
                and parts[3] == "prepare-cover-letter"
            ):
                imported = STATE.repository.imported_jobs[parts[2]]
                if imported.user_id != data_user_id:
                    raise KeyError(parts[2])
                profile = STATE.profile_for(user_id)
                brief = build_cover_letter_brief_prompt(
                    imported,
                    STATE.ai_provider_for(user_id),
                    profile,
                )
                self.send_json({"brief": brief})
                return

            if len(parts) == 4 and parts[:2] == ["api", "imported-jobs"] and parts[3] == "analyze":
                imported = STATE.repository.imported_jobs[parts[2]]
                if imported.user_id != data_user_id:
                    raise KeyError(parts[2])
                runtime_credential = str(
                    payload.get("credentialValue") or payload.get("runtimeCredential") or ""
                )
                if len(runtime_credential) > 4096:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "bad_request", "Credential value is too long"
                    )
                    return
                STATE.quota_store.can_run_ai(user_id)
                profile = STATE.profile_for(user_id)
                provider = STATE.ai_provider_for(user_id)
                if not _ai_consent_satisfied(profile, provider):
                    self.send_error_json(
                        HTTPStatus.PRECONDITION_FAILED,
                        "ai_consent_required",
                        "Confirm consent in Settings before running AI on your CV.",
                    )
                    return
                result = execute_job_decision_brief(
                    imported,
                    provider,
                    runtime_credential,
                    profile,
                )
                STATE.quota_store.record_ai_run(user_id)
                imported.analysis_status = result.status
                imported.analysis_output = result.output or None
                imported.analysis_error = result.error or None
                imported.analysis_provider_id = result.provider_id
                imported.analyzed_at = now_utc()
                if result.output:
                    structured = parse_freeform(result.output)
                    structured_dict = structured.to_dict()
                    imported.structured_analysis = structured_dict
                    imported.fit_score = structured.fit_score
                    imported.recommendation = structured.recommendation
                STATE.repository.save_imported_job(imported)
                STATE.log_analytics(
                    user_id,
                    "ai_analyze",
                    {"providerId": imported.analysis_provider_id, "status": result.status},
                )
                self.send_json({"analysis": asdict(result), "bootstrap": STATE.bootstrap(user_id)})
                return

            if (
                len(parts) == 4
                and parts[:2] == ["api", "imported-jobs"]
                and parts[3] == "draft-cover-letter"
            ):
                imported = STATE.repository.imported_jobs[parts[2]]
                if imported.user_id != data_user_id:
                    raise KeyError(parts[2])
                runtime_credential = str(
                    payload.get("credentialValue") or payload.get("runtimeCredential") or ""
                )
                if len(runtime_credential) > 4096:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "bad_request", "Credential value is too long"
                    )
                    return
                STATE.quota_store.can_run_ai(user_id)
                profile = STATE.profile_for(user_id)
                provider = STATE.ai_provider_for(user_id)
                if not _ai_consent_satisfied(profile, provider):
                    self.send_error_json(
                        HTTPStatus.PRECONDITION_FAILED,
                        "ai_consent_required",
                        "Confirm consent in Settings before running AI on your CV.",
                    )
                    return
                result = execute_cover_letter_brief(
                    imported,
                    provider,
                    runtime_credential,
                    profile,
                )
                STATE.quota_store.record_ai_run(user_id)
                if result.status == "completed" and result.output:
                    imported.cover_letter_draft = result.output
                    STATE.repository.save_imported_job(imported)
                STATE.log_analytics(
                    user_id,
                    "cover_letter_draft",
                    {"providerId": result.provider_id, "status": result.status},
                )
                self.send_json({"draft": asdict(result), "bootstrap": STATE.bootstrap(user_id)})
                return

            if (
                len(parts) == 4
                and parts[:2] == ["api", "imported-jobs"]
                and parts[3] == "tailor-cv"
            ):
                imported = STATE.repository.imported_jobs[parts[2]]
                if imported.user_id != data_user_id:
                    raise KeyError(parts[2])
                runtime_credential = str(
                    payload.get("credentialValue") or payload.get("runtimeCredential") or ""
                )
                if len(runtime_credential) > 4096:
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST, "bad_request", "Credential value is too long"
                    )
                    return
                STATE.quota_store.can_run_ai(user_id)
                profile = STATE.profile_for(user_id)
                if not (profile.cv_text or "").strip():
                    self.send_error_json(
                        HTTPStatus.BAD_REQUEST,
                        "missing_cv",
                        "Add a CV in Settings → Persona & profile before tailoring.",
                    )
                    return
                provider = STATE.ai_provider_for(user_id)
                if not _ai_consent_satisfied(profile, provider):
                    self.send_error_json(
                        HTTPStatus.PRECONDITION_FAILED,
                        "ai_consent_required",
                        "Confirm consent in Settings before running AI on your CV.",
                    )
                    return
                from company_discovery.persona_fixtures import friction_keywords_for

                result = execute_cv_tailoring(
                    imported,
                    provider,
                    runtime_credential,
                    profile,
                    friction_keywords=friction_keywords_for(profile.persona_id),
                )
                STATE.quota_store.record_ai_run(user_id)
                # CV variant attribution (#44): persist a small record
                # of every successful tailoring run so we can correlate
                # variants with replies later. Excerpt is bounded so the
                # JSON payload stays under control.
                if result.status == "completed" and result.output:
                    next_index = len(imported.cv_variants or []) + 1
                    excerpt = (result.output or "")[:400]
                    imported.cv_variants = list(imported.cv_variants or []) + [
                        {
                            "index": next_index,
                            "createdAt": now_utc().isoformat(),
                            "excerpt": excerpt,
                            "attributedReply": False,
                        }
                    ]
                    imported.updated_at = now_utc()
                    STATE.repository.save_imported_job(imported)
                STATE.log_analytics(
                    user_id,
                    "cv_tailoring",
                    {
                        "providerId": result.provider_id,
                        "status": result.status,
                        "variantIndex": len(imported.cv_variants or []),
                    },
                )
                self.send_json(
                    {
                        "tailored": asdict(result),
                        "variantIndex": len(imported.cv_variants or [])
                        if result.status == "completed"
                        else None,
                    }
                )
                return

            if (
                len(parts) == 4
                and parts[:2] == ["api", "discovered-jobs"]
                and parts[3] == "auto-fit"
            ):
                discovered = STATE.repository.discovered_jobs.get(parts[2])
                if not discovered or discovered.user_id != data_user_id:
                    raise KeyError(parts[2])
                runtime_credential = str(
                    payload.get("credentialValue") or payload.get("runtimeCredential") or ""
                )
                STATE.quota_store.can_run_ai(user_id)
                profile = STATE.profile_for(user_id)
                provider = STATE.ai_provider_for(user_id)
                if not _ai_consent_satisfied(profile, provider):
                    self.send_error_json(
                        HTTPStatus.PRECONDITION_FAILED,
                        "ai_consent_required",
                        "Confirm consent in Settings before running AI on your CV.",
                    )
                    return
                company = STATE.repository.companies.get(discovered.company_id)
                company_name = company.name if company else "Unknown company"
                result = execute_auto_fit(
                    discovered,
                    company_name,
                    provider,
                    runtime_credential,
                    profile,
                )
                STATE.quota_store.record_ai_run(user_id)
                if result.status == "completed":
                    score, reason, gaps = parse_auto_fit_output(result.output)
                    if score is not None:
                        discovered.auto_fit_score = score
                        discovered.auto_fit_reason = reason
                        discovered.auto_fit_at = now_utc()
                        discovered.auto_fit_provider_id = result.provider_id
                        if gaps:
                            discovered.gaps = gaps
                        STATE.repository.save_discovered_job(discovered)
                        STATE.maybe_notify_slack(user_id, discovered)
                STATE.log_analytics(
                    user_id,
                    "auto_fit",
                    {
                        "providerId": result.provider_id,
                        "status": result.status,
                        "score": discovered.auto_fit_score,
                    },
                )
                self.send_json(
                    {
                        "result": asdict(result),
                        "discoveredJob": asdict(discovered),
                        "bootstrap": STATE.bootstrap(user_id),
                    }
                )
                return

            if parsed.path == "/api/discovered-jobs/auto-fit-all":
                runtime_credential = str(
                    payload.get("credentialValue") or payload.get("runtimeCredential") or ""
                )
                limit = int(payload.get("limit") or 10)
                limit = max(1, min(25, limit))
                profile = STATE.profile_for(user_id)
                provider = STATE.ai_provider_for(user_id)
                if not _ai_consent_satisfied(profile, provider):
                    self.send_error_json(
                        HTTPStatus.PRECONDITION_FAILED,
                        "ai_consent_required",
                        "Confirm consent in Settings before running AI on your CV.",
                    )
                    return
                companies_by_id = {c.id: c for c in STATE.repository.list_companies(user_id)}
                jobs = [
                    j
                    for j in STATE.repository.list_discovered_jobs(user_id)
                    if not j.imported_job_id and j.auto_fit_score is None
                ][:limit]
                outcomes: list[dict[str, Any]] = []
                for job in jobs:
                    try:
                        STATE.quota_store.can_run_ai(user_id)
                    except QuotaError as error:
                        outcomes.append(
                            {
                                "discoveredJobId": job.id,
                                "status": "quota_exhausted",
                                "code": error.code,
                            }
                        )
                        break
                    company = companies_by_id.get(job.company_id)
                    company_name = company.name if company else "Unknown company"
                    res = execute_auto_fit(job, company_name, provider, runtime_credential, profile)
                    STATE.quota_store.record_ai_run(user_id)
                    if res.status == "completed":
                        score, reason, gaps = parse_auto_fit_output(res.output)
                        if score is not None:
                            job.auto_fit_score = score
                            job.auto_fit_reason = reason
                            job.auto_fit_at = now_utc()
                            job.auto_fit_provider_id = res.provider_id
                            if gaps:
                                job.gaps = gaps
                            STATE.repository.save_discovered_job(job)
                            STATE.maybe_notify_slack(user_id, job)
                    outcomes.append(
                        {
                            "discoveredJobId": job.id,
                            "status": res.status,
                            "score": job.auto_fit_score,
                            "error": res.error or None,
                        }
                    )
                STATE.log_analytics(
                    user_id,
                    "auto_fit_batch",
                    {
                        "requested": len(jobs),
                        "completed": sum(1 for o in outcomes if o["status"] == "completed"),
                    },
                )
                self.send_json({"outcomes": outcomes, "bootstrap": STATE.bootstrap(user_id)})
                return

            self.send_error_json(HTTPStatus.NOT_FOUND, "not_found", "Unknown endpoint")
        except QuotaError as error:
            self.send_error_json(HTTPStatus.TOO_MANY_REQUESTS, error.code, error.message)
        except (KeyError, ValueError) as error:
            self.send_error_json(
                HTTPStatus.BAD_REQUEST, "bad_request", f"Missing or invalid field: {error}"
            )
        except Exception as error:  # noqa: BLE001 - top-level HTTP boundary
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", str(error))

    def do_PATCH(self) -> None:
        try:
            parsed = urlparse(self.path)
            parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
            session = self.require_auth()
            if session is None or not self.require_csrf(session):
                return
            user_id = session.user.id
            data_user_id = STATE.effective_user_id(user_id)
            if len(parts) == 4 and parts[:3] == ["api", "admin", "users"]:
                if not self.require_admin(session):
                    return
                payload = self.read_json_body()
                target_id = parts[3]
                target_before = STATE.auth_store.get_user(target_id)
                if target_id == session.user.id and (
                    ("role" in payload and payload.get("role") != target_before.role)
                    or ("active" in payload and bool(payload.get("active")) != target_before.active)
                ):
                    self.send_error_json(
                        HTTPStatus.FORBIDDEN,
                        "self_modify_forbidden",
                        "Admins cannot change their own role or active status",
                    )
                    return
                update: dict[str, Any] = {}
                if "role" in payload:
                    update["role"] = payload["role"]
                if "active" in payload:
                    update["active"] = bool(payload["active"])
                if payload.get("password"):
                    update["password"] = payload["password"]
                user = STATE.auth_store.update_user(target_id, **update)
                if "role" in update and update["role"] != target_before.role:
                    STATE.record_admin_action(
                        actor=session.user,
                        target=user,
                        action="update_role",
                        details={"from": target_before.role, "to": user.role},
                    )
                if "active" in update and bool(update["active"]) != target_before.active:
                    STATE.record_admin_action(
                        actor=session.user,
                        target=user,
                        action="update_active",
                        details={"from": target_before.active, "to": user.active},
                    )
                if "password" in update:
                    STATE.record_admin_action(
                        actor=session.user,
                        target=user,
                        action="reset_password",
                    )
                self.send_json(
                    {
                        "user": make_admin_user_payload(user),
                        "users": [
                            make_admin_user_payload(item) for item in STATE.auth_store.list_users()
                        ],
                    }
                )
                return
            if len(parts) == 3 and parts[:2] == ["api", "companies"]:
                payload = to_snake_case_payload(self.read_json_body())
                company = STATE.service.update_company(data_user_id, parts[2], **payload)
                self.send_json({"company": company, "bootstrap": STATE.bootstrap(user_id)})
                return
            self.send_error_json(HTTPStatus.NOT_FOUND, "not_found", "Unknown endpoint")
        except (KeyError, ValueError) as error:
            self.send_error_json(
                HTTPStatus.BAD_REQUEST, "bad_request", f"Missing or invalid field: {error}"
            )
        except Exception as error:  # noqa: BLE001 - top-level HTTP boundary
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", str(error))

    def do_DELETE(self) -> None:
        try:
            parsed = urlparse(self.path)
            parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
            session = self.require_auth()
            if session is None or not self.require_csrf(session):
                return
            user_id = session.user.id
            data_user_id = STATE.effective_user_id(user_id)
            if len(parts) == 3 and parts[:2] == ["api", "companies"]:
                # Cross-user / missing-id deletes must surface as 404
                # rather than a generic 400 — the row simply doesn't
                # exist in the caller's namespace.
                try:
                    STATE.repository.delete_company(data_user_id, parts[2])
                except KeyError:
                    self.send_error_json(HTTPStatus.NOT_FOUND, "not_found", "Company not found")
                    return
                self.send_json({"bootstrap": STATE.bootstrap(user_id)})
                return
            if len(parts) == 3 and parts[:2] == ["api", "saved-searches"]:
                try:
                    STATE.delete_saved_search(data_user_id, parts[2])
                except KeyError:
                    self.send_error_json(
                        HTTPStatus.NOT_FOUND, "not_found", "Saved search not found"
                    )
                    return
                self.send_json({"savedSearches": STATE._saved_searches_with_alerts(user_id)})
                return
            if len(parts) == 4 and parts[:3] == ["api", "admin", "users"]:
                if not self.require_admin(session):
                    return
                target_id = parts[3]
                if target_id == session.user.id:
                    self.send_error_json(
                        HTTPStatus.FORBIDDEN,
                        "self_modify_forbidden",
                        "Admins cannot delete themselves",
                    )
                    return
                try:
                    result = STATE.delete_user_account(actor=session.user, target_id=target_id)
                except KeyError:
                    self.send_error_json(HTTPStatus.NOT_FOUND, "not_found", "User not found")
                    return
                except ValueError as error:
                    self.send_error_json(HTTPStatus.FORBIDDEN, str(error), str(error))
                    return
                self.send_json(
                    result
                    | {
                        "users": [
                            make_admin_user_payload(item) for item in STATE.auth_store.list_users()
                        ]
                    }
                )
                return
            self.send_error_json(HTTPStatus.NOT_FOUND, "not_found", "Unknown endpoint")
        except KeyError as error:
            self.send_error_json(
                HTTPStatus.BAD_REQUEST, "bad_request", f"Missing or invalid field: {error}"
            )
        except Exception as error:  # noqa: BLE001 - top-level HTTP boundary
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", str(error))

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        if length > MAX_JSON_BODY_BYTES:
            raise ValueError("request body too large")
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def send_json(
        self,
        payload: dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK,
        headers: dict[str, str] | None = None,
        include_body: bool = True,
    ) -> None:
        body = json.dumps(jsonable(payload), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if include_body:
            self.wfile.write(body)

    def send_error_json(
        self, status: HTTPStatus, code: str, message: str, include_body: bool = True
    ) -> None:
        self.send_json(
            {"error": {"code": code, "message": message}}, status, include_body=include_body
        )

    def send_text(
        self,
        body: str,
        *,
        content_type: str,
        filename: str | None = None,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(encoded)

    def _send_seo_page_not_found(self) -> None:
        body = (
            "<!doctype html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8" />\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1" />\n'
            '  <meta name="robots" content="noindex,nofollow" />\n'
            "  <title>Job alert not found — Helpmefindthejob</title>\n"
            '  <link rel="stylesheet" href="/styles.css" />\n'
            "</head>\n"
            '<body class="legal-body">\n'
            '  <main class="legal-page">\n'
            '    <a href="/" class="legal-back">← Helpmefindthejob</a>\n'
            "    <h1>Job alert not found</h1>\n"
            "    <p>This job-alert page does not exist. Head to "
            '<a href="/">helpmefindthejob.com</a> to set up your own saved search — we watch the '
            "company pages + the major aggregators daily.</p>\n"
            "  </main>\n"
            "</body>\n"
            "</html>\n"
        )
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _send_seo_page(self, page: dict[str, Any]) -> None:
        from html import escape as _escape

        title = page["title"] or f"{page['role']} jobs in {page['city']}"
        intro = page["intro"] or (
            f"Helpmefindthejob watches direct career pages and the major aggregators for "
            f"{page['role']} roles in {page['city']}."
        )
        canonical = STATE.public_url_for(f"/jobs/{page['slug']}")
        signup_url = STATE.public_url_for("/")
        og_description = intro[:280]
        body = (
            "<!doctype html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8" />\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1" />\n'
            '  <meta name="robots" content="index,follow" />\n'
            f"  <title>{_escape(title)} — Helpmefindthejob</title>\n"
            f'  <meta name="description" content="{_escape(og_description)}" />\n'
            f'  <link rel="canonical" href="{_escape(canonical)}" />\n'
            '  <meta property="og:type" content="article" />\n'
            f'  <meta property="og:title" content="{_escape(title)}" />\n'
            f'  <meta property="og:description" content="{_escape(og_description)}" />\n'
            f'  <meta property="og:url" content="{_escape(canonical)}" />\n'
            '  <link rel="stylesheet" href="/styles.css" />\n'
            "</head>\n"
            '<body class="legal-body">\n'
            '  <main class="legal-page">\n'
            '    <a href="/" class="legal-back">← Helpmefindthejob</a>\n'
            f"    <h1>{_escape(title)}</h1>\n"
            f"    <p>{_escape(intro)}</p>\n"
            "    <section>\n"
            "      <h2>How it works</h2>\n"
            "      <ol>\n"
            f"        <li>Sign up — free.</li>\n"
            f"        <li>Set up a saved search for <strong>{_escape(page['role'])}</strong> "
            f"in <strong>{_escape(page['city'])}</strong>.</li>\n"
            "        <li>We dedupe across the company sites + the major aggregators daily. "
            "Triage the queue with keyboard shortcuts in five minutes.</li>\n"
            "      </ol>\n"
            "    </section>\n"
            "    <section>\n"
            "      <h2>Why not just LinkedIn?</h2>\n"
            "      <p>LinkedIn under-indexes mid-market and German employer sites; their search is "
            "tuned for engagement, not coverage. We watch the company pages directly and supplement "
            "with the public aggregators (Indeed, StepStone, Arbeitnow, Bundesagentur, Muse).</p>\n"
            "    </section>\n"
            "    <section>\n"
            f'      <p><a class="btn btn-primary" href="{_escape(signup_url)}">'
            "Sign up — start your saved search</a></p>\n"
            "    </section>\n"
            '    <p class="legal-footer">\n'
            '      <a href="/privacy">Privacy</a>\n'
            '      <a href="/terms">Terms</a>\n'
            '      <a href="/data-retention">Data retention</a>\n'
            '      <a href="/impressum">Impressum</a>\n'
            "    </p>\n"
            "  </main>\n"
            "</body>\n"
            "</html>\n"
        )
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        # Long cache — these pages change rarely, and Google treats
        # cache-friendly responses as a positive signal.
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(encoded)

    def _send_share_not_found_page(self) -> None:
        body = (
            "<!doctype html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8" />\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1" />\n'
            '  <meta name="robots" content="noindex,nofollow" />\n'
            "  <title>Job not available — Helpmefindthejob</title>\n"
            '  <link rel="stylesheet" href="/styles.css" />\n'
            "</head>\n"
            '<body class="legal-body">\n'
            '  <main class="legal-page">\n'
            '    <a href="/" class="legal-back">← Helpmefindthejob</a>\n'
            "    <h1>Job not available</h1>\n"
            "    <p>This job's share link has been disabled by its owner, or the link is wrong. "
            'If you arrived here by mistake, head to <a href="/">helpmefindthejob.com</a>.</p>\n'
            "  </main>\n"
            "</body>\n"
            "</html>\n"
        )
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _send_share_job_page(self, imported: ImportedJob) -> None:
        from html import escape as _escape

        title = imported.title or "Job opening"
        company = imported.company_name or "—"
        location = imported.location or ""
        signup_url = STATE.public_url_for("/")
        canonical = STATE.public_url_for(f"/share/job/{imported.id}")
        description = (imported.description or "").strip() or (
            f"{title} at {company}" + (f" — {location}" if location else "") + "."
        )
        og_description = description[:280]
        body = (
            "<!doctype html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8" />\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1" />\n'
            '  <meta name="robots" content="index,follow" />\n'
            f"  <title>{_escape(title)} at {_escape(company)} — Helpmefindthejob</title>\n"
            f'  <meta name="description" content="{_escape(og_description)}" />\n'
            f'  <link rel="canonical" href="{_escape(canonical)}" />\n'
            '  <meta property="og:type" content="article" />\n'
            f'  <meta property="og:title" content="{_escape(title)} at {_escape(company)}" />\n'
            f'  <meta property="og:description" content="{_escape(og_description)}" />\n'
            f'  <meta property="og:url" content="{_escape(canonical)}" />\n'
            '  <link rel="stylesheet" href="/styles.css" />\n'
            "</head>\n"
            '<body class="legal-body">\n'
            '  <main class="legal-page">\n'
            '    <a href="/" class="legal-back">← Helpmefindthejob</a>\n'
            f"    <h1>{_escape(title)}</h1>\n"
            f'    <p class="muted"><strong>{_escape(company)}</strong>'
            + (f" · {_escape(location)}" if location else "")
            + "</p>\n"
            "    <section>\n"
            f"      <p>{_escape(description)}</p>\n"
            "    </section>\n"
            "    <section>\n"
            "      <h2>Want jobs like this in your inbox?</h2>\n"
            "      <p>Helpmefindthejob watches direct career pages plus the major aggregators "
            "(Indeed, StepStone, Arbeitnow, Bundesagentur, Muse) and dedupes the queue. "
            "No LinkedIn feed, no algorithm, no surveillance.</p>\n"
            f'      <p><a class="btn btn-primary" href="{_escape(signup_url)}">Sign up — it\'s free</a></p>\n'
            "    </section>\n"
            f'    <p class="muted small">Original job listing: <a rel="noopener nofollow" target="_blank" href="{_escape(imported.source_url)}">{_escape(imported.source_url)}</a></p>\n'
            '    <p class="legal-footer">\n'
            '      <a href="/privacy">Privacy</a>\n'
            '      <a href="/terms">Terms</a>\n'
            '      <a href="/data-retention">Data retention</a>\n'
            '      <a href="/impressum">Impressum</a>\n'
            "    </p>\n"
            "  </main>\n"
            "</body>\n"
            "</html>\n"
        )
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        # Public, indexable, but cache lightly so an owner-disable
        # propagates within minutes.
        self.send_header("Cache-Control", "public, max-age=300")
        self.end_headers()
        self.wfile.write(encoded)

    def _send_account_deletion_page(self, *, title: str, message: str, ok: bool) -> None:
        """Render the small server-side confirmation page reached from the
        account-deletion email link. Server-rendered (not SPA) because the
        user may not have an active session when they click."""

        accent = "#7c5cff" if ok else "#f97373"
        from html import escape as _escape

        body = (
            "<!doctype html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8" />\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1" />\n'
            '  <meta name="robots" content="noindex,nofollow" />\n'
            f"  <title>{_escape(title)} — Helpmefindthejob</title>\n"
            '  <link rel="stylesheet" href="/styles.css" />\n'
            "</head>\n"
            '<body class="legal-body">\n'
            '  <main class="legal-page">\n'
            '    <a href="/" class="legal-back">← Back to Helpmefindthejob</a>\n'
            f'    <h1 style="color: {accent}">{_escape(title)}</h1>\n'
            f"    <p>{_escape(message)}</p>\n"
            '    <p class="muted small">If something is wrong, contact <a href="mailto:support@helpmefindthejob.com">support@helpmefindthejob.com</a>.</p>\n'
            "  </main>\n"
            "</body>\n"
            "</html>\n"
        )
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK if ok else HTTPStatus.GONE)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def serve_static(self, request_path: str, include_body: bool = True) -> None:
        spa_routes = {"/accept-invite", "/reset-password", "/forgot-password"}
        if request_path in {"", "/"}:
            path = "/index.html"
        elif request_path in spa_routes:
            path = "/index.html"
        else:
            path = request_path
        candidate = (STATIC_ROOT / path.lstrip("/")).resolve()
        if (
            not str(candidate).startswith(str(STATIC_ROOT.resolve()))
            or not candidate.exists()
            or candidate.is_dir()
        ):
            # Try a `.html` fallback so /privacy serves /privacy.html.
            html_candidate = (STATIC_ROOT / (path.lstrip("/") + ".html")).resolve()
            if (
                str(html_candidate).startswith(str(STATIC_ROOT.resolve()))
                and html_candidate.exists()
                and not html_candidate.is_dir()
            ):
                candidate = html_candidate
            else:
                self.send_error_json(HTTPStatus.NOT_FOUND, "not_found", "File not found")
                return
        content = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        guessed = mimetypes.guess_type(candidate.name)[0]
        if guessed is None and candidate.suffix.lower() == ".webmanifest":
            guessed = "application/manifest+json"
        self.send_header("Content-Type", guessed or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if include_body:
            self.wfile.write(content)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - signature inherited from BaseHTTPRequestHandler; rename would break the override
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", default=get_env("HELPMEFINDTHEJOB_HOST", "COMPANY_DISCOVERY_HOST", "127.0.0.1")
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(get_env("HELPMEFINDTHEJOB_PORT", "COMPANY_DISCOVERY_PORT", "8765")),
    )
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    visible_host = "127.0.0.1" if args.host in {"0.0.0.0", ""} else args.host
    print(f"Company Discovery app running at http://{visible_host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
