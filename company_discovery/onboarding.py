"""Pure-function onboarding checklist for the dashboard.

The checklist is computed from app state, not stored. That keeps it
honest: it can never drift from the real data. Each step has an id,
label, hint, and a "complete" boolean.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .ai_providers import AIProviderConfig
from .models import Company, DiscoveredJob, ImportedJob, SavedSearch, UserProfile


@dataclass
class OnboardingStep:
    id: str
    label: str
    hint: str
    complete: bool


def build_checklist(
    *,
    companies: Sequence[Company],
    discovered_jobs: Sequence[DiscoveredJob],
    imported_jobs: Sequence[ImportedJob],
    ai_provider: AIProviderConfig,
    schedule_enabled: bool,
    saved_searches: Sequence[SavedSearch] = (),
    profile: UserProfile | None = None,
) -> list[OnboardingStep]:
    has_company = bool(companies)
    has_career_page = any(c.career_page_url for c in companies)
    has_scan = bool(discovered_jobs)
    has_import = bool(imported_jobs)
    has_brief = any(j.analysis_status not in ("pending",) for j in imported_jobs)
    has_provider = ai_provider.provider_id != "manual"
    has_saved_search = bool(saved_searches)
    has_cv = bool(profile and (profile.cv_text or "").strip())
    return [
        # Saved-search-first ordering — this is the primary path now;
        # company watchlist is an enrichment, not a prerequisite.
        OnboardingStep(
            id="cv",
            label="Add your CV",
            hint="Paste or upload your CV — we use it for persona auto-suggest and AI Brief.",
            complete=has_cv,
        ),
        OnboardingStep(
            id="saved_search",
            label="Set up a saved search",
            hint="Tell us the role + location. We'll watch the major aggregators daily.",
            complete=has_saved_search,
        ),
        OnboardingStep(
            id="add_company",
            label="(Optional) Add a company watchlist",
            hint="Optional — if you have specific employers in mind, watch them directly.",
            complete=has_company,
        ),
        OnboardingStep(
            id="career_page",
            label="(Optional) Confirm a career page",
            hint="At least one company has a stored career-page URL.",
            complete=has_career_page,
        ),
        OnboardingStep(
            id="scan",
            label="See your first matches",
            hint="Run a saved search or scan a company.",
            complete=has_scan,
        ),
        OnboardingStep(
            id="import",
            label="Import a role",
            hint="Open Discovered Jobs and click Import on something promising.",
            complete=has_import,
        ),
        OnboardingStep(
            id="brief",
            label="Prepare or run an AI brief",
            hint="Open AI Brief and prepare a brief — manual mode is fine.",
            complete=has_brief,
        ),
        OnboardingStep(
            id="ai_provider",
            label="Configure your AI provider (optional)",
            hint="Bring your own OpenAI / Gemini / Claude / Ollama key.",
            complete=has_provider,
        ),
        OnboardingStep(
            id="schedule",
            label="Enable automatic scans (optional)",
            hint="Lets the durable scheduler check your watchlist on its own.",
            complete=schedule_enabled,
        ),
    ]


def needs_first_run_wizard(
    *,
    saved_searches: Sequence[SavedSearch],
    companies: Sequence[Company],
    profile: UserProfile | None,
    discovered_jobs: Sequence[DiscoveredJob],
    imported_jobs: Sequence[ImportedJob],
    dismissed: bool,
) -> bool:
    """A user gets the wizard only if they've done basically nothing yet
    AND haven't already dismissed it. The dismissed flag is stored on
    UserProfile.onboarding_dismissed so it survives reloads."""

    if dismissed:
        return False
    if saved_searches or companies or imported_jobs or discovered_jobs:
        return False
    return True


def checklist_progress(steps: Sequence[OnboardingStep]) -> dict[str, int]:
    completed = sum(1 for step in steps if step.complete)
    total = len(steps)
    return {"completed": completed, "total": total}
