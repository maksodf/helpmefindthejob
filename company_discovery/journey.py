"""Stateful job-search journey — the ChatGPT-style end-to-end flow.

A user types "I want to find a job" and the agent walks them through:

    1. greet      — welcome + frame the journey
    2. discover   — open questions: role, location, years, languages
    3. cv_check   — paste, reuse profile, or build sectional via chat
    4. inspire    — lateral role suggestions ("you'd also fit X, Y, Z")
    5. preferences — soft filters: remote, salary band, company size
    6. search     — run aggregator with merged target list + filter
    7. review     — categorize results, ask which bucket to drill into
    8. drill      — list top jobs in chosen category, ask which to pick
    9. tailor     — for picked job: offer letter + CV-enhancement consult
    10. letter    — drafted motivation letter (DACH norm)
    11. cv_consult — gap-by-gap CV consultation against the JD
    12. done      — journey complete; user can /start again any time

This module is the **state machine** — a pure function
``advance(journey, user_message, profile, ai_caller)`` returns the
next state + the agent's reply + side-effects to apply.

Why pure? So the chat HTTP handler stays the only place that writes.
Tests can drive the state machine without spinning up the full app.

Side effects are explicit dicts: ``{"profile_updates": {...},
"persist_journey": bool, "run_search": bool, …}``. The caller (the
HTTP handler) applies them.

AI dependency
=============

Steps 4 (inspire), 7 (review/categorize), 10 (letter), 11 (cv_consult)
benefit from an LLM. When no AI provider is configured, each falls
back to a templated path AND surfaces an honest message: "I'm
running without an AI right now — this is the templated version.
Configure a provider in /profile to get personalized output."
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------- Phases ----------------

PHASE_GREET = "greet"
PHASE_DISCOVER = "discover"
PHASE_CV_CHECK = "cv_check"
PHASE_INSPIRE = "inspire"
PHASE_PREFS = "preferences"
PHASE_SEARCH = "search"
PHASE_REVIEW = "review"
PHASE_DRILL = "drill"
PHASE_TAILOR = "tailor"
PHASE_LETTER = "letter"
PHASE_CV_CONSULT = "cv_consult"
PHASE_DONE = "done"

ALL_PHASES = (
    PHASE_GREET, PHASE_DISCOVER, PHASE_CV_CHECK, PHASE_INSPIRE,
    PHASE_PREFS, PHASE_SEARCH, PHASE_REVIEW, PHASE_DRILL,
    PHASE_TAILOR, PHASE_LETTER, PHASE_CV_CONSULT, PHASE_DONE,
)

# Discover step micro-states
DISCOVER_ASK_ROLE = "ask_role"
DISCOVER_ASK_LOCATION = "ask_location"
DISCOVER_ASK_YEARS = "ask_years"
DISCOVER_ASK_LANGS = "ask_langs"
DISCOVER_DONE = "done"

# Triggers — explicit job-seeking phrases ONLY (per scope decision).
# Greetings like "hi" or "hello" do NOT auto-start the journey.
JOURNEY_TRIGGER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:i (?:want|need|wanna)|help me|can you help)"
                r"\b.*\b(?:find|look|search|get)\b.*\b(?:job|jobs|role|roles|work|position)\b",
                re.IGNORECASE),
    re.compile(r"\b(?:find|look for|search for|get|need)\b.*\b(?:a |me a )?\b(?:job|role|position|work)\b",
                re.IGNORECASE),
    re.compile(r"\b(?:start|begin)\b.*\b(?:job search|journey|hunt)\b", re.IGNORECASE),
    # German
    re.compile(r"\b(?:suche|finde|brauche)\b.*\b(?:job|stelle|arbeit|position)\b", re.IGNORECASE),
    re.compile(r"\bhilf mir\b.*\b(?:job|stelle|arbeit)\b", re.IGNORECASE),
    re.compile(r"\bich (?:will|möchte|brauche)\b.*\b(?:job|stelle|arbeit)\b", re.IGNORECASE),
)


def looks_like_journey_trigger(message: str) -> bool:
    """True iff the message explicitly asks for help finding a job.

    Returns False on bare greetings. The journey only auto-starts on
    explicit intent so returning users typing "hi" don't get re-routed
    into onboarding.
    """
    if not message:
        return False
    return any(pat.search(message) for pat in JOURNEY_TRIGGER_PATTERNS)


# ---------------- State ----------------


@dataclass
class UserJourney:
    """Per-user journey position. Serialised to JSON in
    ``profile.chat_state["journey"]`` so it survives server restart."""

    phase: str = PHASE_GREET
    # Where we are inside the discover phase.
    discover_step: str = DISCOVER_ASK_ROLE
    # User-stated answers gathered along the way.
    role_text: str = ""        # what the user typed for the role
    bucket_key: str = ""       # taxonomy hit (if any)
    location: str = ""         # raw user text — passed through to aggregator
    location_canonical: str = ""  # normalised (germany / anywhere / city)
    years_experience: int | None = None
    languages: list[str] = field(default_factory=list)
    # CV branch.
    cv_status: str = "unknown"  # unknown | uploaded | building | declined
    cv_build_section_idx: int = 0  # if building via chat
    # Sectional build via chat — small fixed schema. Each key is one
    # question; each value is the user's verbatim answer (fact-ratio
    # gate downstream keeps it honest).
    cv_build_answers: dict[str, str] = field(default_factory=dict)
    cv_build_step: str = ""  # name | location | summary | recent_role | skills | done
    # Inspiration suggestions accepted by the user.
    lateral_roles: list[str] = field(default_factory=list)
    target_roles: list[str] = field(default_factory=list)  # final search list
    # Preferences (soft).
    remote_required: bool | None = None
    salary_floor: int | None = None
    company_size: str = ""  # startup | mid | enterprise | any
    # Search outcome. category → list of job-ids (URLs in practice).
    search_results_by_category: dict[str, list[str]] = field(default_factory=dict)
    # Side-car: full job detail by id, so the drill phase can render
    # title/company/location/link without re-querying. Each value is
    # the small dict shape we already use in find_jobs sample lists.
    search_jobs_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    picked_category: str = ""
    picked_job_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "discoverStep": self.discover_step,
            "roleText": self.role_text,
            "bucketKey": self.bucket_key,
            "location": self.location,
            "locationCanonical": self.location_canonical,
            "yearsExperience": self.years_experience,
            "languages": list(self.languages),
            "cvStatus": self.cv_status,
            "cvBuildSectionIdx": self.cv_build_section_idx,
            "cvBuildAnswers": dict(self.cv_build_answers),
            "cvBuildStep": self.cv_build_step,
            "lateralRoles": list(self.lateral_roles),
            "targetRoles": list(self.target_roles),
            "remoteRequired": self.remote_required,
            "salaryFloor": self.salary_floor,
            "companySize": self.company_size,
            "searchResultsByCategory": dict(self.search_results_by_category),
            "searchJobsById": dict(self.search_jobs_by_id),
            "pickedCategory": self.picked_category,
            "pickedJobId": self.picked_job_id,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "UserJourney":
        if not payload:
            return cls()
        return cls(
            phase=payload.get("phase") or PHASE_GREET,
            discover_step=payload.get("discoverStep") or DISCOVER_ASK_ROLE,
            role_text=payload.get("roleText") or "",
            bucket_key=payload.get("bucketKey") or "",
            location=payload.get("location") or "",
            location_canonical=payload.get("locationCanonical") or "",
            years_experience=payload.get("yearsExperience"),
            languages=list(payload.get("languages") or []),
            cv_status=payload.get("cvStatus") or "unknown",
            cv_build_section_idx=int(payload.get("cvBuildSectionIdx") or 0),
            cv_build_answers=dict(payload.get("cvBuildAnswers") or {}),
            cv_build_step=payload.get("cvBuildStep") or "",
            lateral_roles=list(payload.get("lateralRoles") or []),
            target_roles=list(payload.get("targetRoles") or []),
            remote_required=payload.get("remoteRequired"),
            salary_floor=payload.get("salaryFloor"),
            company_size=payload.get("companySize") or "",
            search_results_by_category=dict(
                payload.get("searchResultsByCategory") or {}
            ),
            search_jobs_by_id=dict(payload.get("searchJobsById") or {}),
            picked_category=payload.get("pickedCategory") or "",
            picked_job_id=payload.get("pickedJobId") or "",
        )


# ---------------- Advance result ----------------


@dataclass
class AdvanceResult:
    """What :func:`advance` returns. The chat-message HTTP handler
    applies the side effects + sends the reply."""

    reply: str
    journey: UserJourney
    # If True, the caller should persist the journey to profile.chat_state.
    persist: bool = True
    # Profile fields the caller should write back. Keys map to
    # UserProfile attributes (e.g. {"target_roles": [...]}). Strings,
    # ints, lists only — no datetimes.
    profile_updates: dict[str, Any] = field(default_factory=dict)
    # When set, the caller should run the find_jobs handler with these
    # args. Drives the search phase.
    run_search_with: dict[str, Any] | None = None
    # When True, the journey has reached PHASE_DONE — the user can
    # /start a new one any time.
    done: bool = False


# ---------------- Entry: should we start the journey? ----------------


def should_auto_start(journey: UserJourney, message: str) -> bool:
    """True iff we should kick a fresh journey for the user based on
    this message. A journey starts when:

    - The user has no journey, or is in PHASE_DONE, AND
    - The message matches one of the explicit job-seeking triggers
    """
    if journey.phase not in (PHASE_GREET, PHASE_DONE):
        return False
    return looks_like_journey_trigger(message)


# ---------------- The state machine ----------------


def advance(
    journey: UserJourney,
    message: str,
    *,
    has_existing_cv: bool = False,
    ai_available: bool = False,
    ai_caller: Callable[[str, str], str | None] | None = None,
) -> AdvanceResult:
    """Advance the journey by one user turn.

    ``message`` is the user's latest message.
    ``has_existing_cv`` is True iff ``profile.cv_text`` is non-empty.
    ``ai_available`` is True iff an AI provider is configured AND
        the user has granted consent. When False, AI-dependent steps
        fall back to templated output with an honest message.
    ``ai_caller`` is an injectable callable so tests can drive the
        AI-dependent steps deterministically. Signature:
        ``ai_caller(system_prompt, user_message) -> str | None``.
    """
    msg = (message or "").strip()

    # --- Phase: greet ---
    if journey.phase == PHASE_GREET:
        journey.phase = PHASE_DISCOVER
        journey.discover_step = DISCOVER_ASK_ROLE
        reply = (
            "Got it — let's find you a job. I'll ask a few short "
            "questions, then search for you and show what fits.\n\n"
            "**1. What kind of role are you looking for?** "
            "(e.g., \"Pflegehelfer\", \"bartender\", \"backend "
            "engineer\", \"barista\")"
        )
        return AdvanceResult(reply=reply, journey=journey)

    # --- Phase: discover ---
    if journey.phase == PHASE_DISCOVER:
        return _advance_discover(journey, msg)

    # --- Phase: cv_check ---
    if journey.phase == PHASE_CV_CHECK:
        return _advance_cv_check(journey, msg, has_existing_cv=has_existing_cv)

    # --- Phase: inspire ---
    if journey.phase == PHASE_INSPIRE:
        return _advance_inspire(journey, msg,
                                  ai_available=ai_available,
                                  ai_caller=ai_caller)

    # --- Phase: preferences ---
    if journey.phase == PHASE_PREFS:
        return _advance_prefs(journey, msg)

    # --- Phase: review (categorized results presented) ---
    if journey.phase == PHASE_REVIEW:
        return _advance_review(journey, msg)

    # --- Phase: drill (showing jobs in chosen category) ---
    if journey.phase == PHASE_DRILL:
        return _advance_drill(journey, msg)

    # --- Phase: tailor (post-job-pick menu) ---
    if journey.phase == PHASE_TAILOR:
        lc = (msg or "").lower().strip()
        if "letter" in lc or "motivation" in lc or "schreiben" in lc:
            journey.phase = PHASE_LETTER
            return AdvanceResult(
                reply="__INVOKE_COMMAND:draft_motivation_letter__",
                journey=journey,
            )
        if "consult" in lc or "enhance" in lc or "improve" in lc:
            journey.phase = PHASE_CV_CONSULT
            return AdvanceResult(
                reply="__INVOKE_COMMAND:suggest_cv_enhancements__",
                journey=journey,
            )
        if "save" in lc or "mark" in lc or "interested" in lc:
            journey.phase = PHASE_DONE
            return AdvanceResult(
                reply=(
                    "Saved your interest in this role. Type `find a job` "
                    "any time to start a fresh search."
                ),
                journey=journey,
                done=True,
            )
        return AdvanceResult(
            reply=(
                "Reply **letter** for the motivation draft, **consult** "
                "for CV enhancements, or **save** to move on."
            ),
            journey=journey,
            persist=False,
        )

    if journey.phase in (PHASE_LETTER, PHASE_CV_CONSULT):
        # After the dedicated command ran, the user is shown the
        # output. Their next message either continues (save / consult)
        # or wraps up. For simplicity, "save" wraps up; anything
        # else falls back to the tailor menu re-prompt.
        lc = (msg or "").lower().strip()
        if "save" in lc or "done" in lc or "thanks" in lc:
            journey.phase = PHASE_DONE
            return AdvanceResult(
                reply=(
                    "Saved. Type `find a job` to start another search."
                ),
                journey=journey,
                done=True,
            )
        if "consult" in lc and journey.phase == PHASE_LETTER:
            journey.phase = PHASE_CV_CONSULT
            return AdvanceResult(
                reply="__INVOKE_COMMAND:suggest_cv_enhancements__",
                journey=journey,
            )
        return AdvanceResult(
            reply=(
                "Reply **save** to wrap up, **consult** for CV "
                "enhancement ideas, or `find a job` for a new search."
            ),
            journey=journey,
            persist=False,
        )

    if journey.phase == PHASE_DONE:
        return AdvanceResult(
            reply="Journey complete. Type `find a job` to start a new search.",
            journey=journey,
            persist=False,
            done=True,
        )

    # Unknown phase — reset.
    journey.phase = PHASE_GREET
    return AdvanceResult(
        reply="Let me restart — type \"find a job\" to begin.",
        journey=journey,
    )


# ---------------- Phase: discover ----------------


def _advance_discover(journey: UserJourney, msg: str) -> AdvanceResult:
    # Late-import to avoid circular dep with chat_router → job_type_filter.
    from company_discovery.job_type_filter import (
        identify_bucket_with_match, normalize_location,
    )

    step = journey.discover_step
    profile_updates: dict[str, Any] = {}

    if step == DISCOVER_ASK_ROLE:
        if not msg:
            return AdvanceResult(
                reply="What kind of role? (e.g., \"Pflegehelfer\", "
                      "\"bartender\", \"backend engineer\")",
                journey=journey,
                persist=False,
            )
        journey.role_text = msg
        bucket_key, matched = identify_bucket_with_match(msg)
        if bucket_key:
            journey.bucket_key = bucket_key
            # Auto-persist the role filter so watchlist scans honour it.
            profile_updates["job_type_filter"] = bucket_key
        journey.discover_step = DISCOVER_ASK_LOCATION
        reply = (
            f"Got it: **{msg}**.\n\n"
            "**2. Where?** (city, country, or \"anywhere\" / \"remote\")"
        )
        return AdvanceResult(reply=reply, journey=journey,
                              profile_updates=profile_updates)

    if step == DISCOVER_ASK_LOCATION:
        if not msg:
            return AdvanceResult(
                reply="Where? (city, country, or \"anywhere\")",
                journey=journey,
                persist=False,
            )
        journey.location = msg
        journey.location_canonical = normalize_location(msg) or ""
        profile_updates["location"] = msg
        profile_updates["job_type_location_filter"] = msg
        journey.discover_step = DISCOVER_ASK_YEARS
        reply = (
            f"Noted: **{msg}**.\n\n"
            "**3. How many years' experience do you have in this kind "
            "of role?** (a number is fine — e.g., \"3\" or \"about 7\")"
        )
        return AdvanceResult(reply=reply, journey=journey,
                              profile_updates=profile_updates)

    if step == DISCOVER_ASK_YEARS:
        years = _parse_years(msg)
        journey.years_experience = years
        if years is not None:
            profile_updates["years_experience"] = years
            # Map years → seniority for the persona heuristics.
            if years < 2:
                profile_updates["seniority"] = "junior"
            elif years < 6:
                profile_updates["seniority"] = "mid"
            else:
                profile_updates["seniority"] = "senior"
        journey.discover_step = DISCOVER_ASK_LANGS
        reply = (
            "**4. Which languages do you work in?** "
            "(comma-separated, e.g., \"Deutsch, English\")"
        )
        return AdvanceResult(reply=reply, journey=journey,
                              profile_updates=profile_updates)

    if step == DISCOVER_ASK_LANGS:
        langs = [l.strip() for l in (msg.replace(";", ",").split(","))
                  if l.strip()]
        journey.languages = langs[:6]  # cap
        if langs:
            profile_updates["languages"] = langs[:6]
        journey.discover_step = DISCOVER_DONE
        journey.phase = PHASE_CV_CHECK
        reply = (
            "Thanks. Quick summary:\n"
            f"  - Role: **{journey.role_text}**\n"
            f"  - Where: **{journey.location}**\n"
            f"  - Experience: **{journey.years_experience or 'unspecified'}**\n"
            f"  - Languages: **{', '.join(journey.languages) or 'unspecified'}**\n\n"
            "**Do you have a CV ready?** Three options:\n"
            "  - Paste it in chat (drop the whole text)\n"
            "  - Reuse the CV already on your profile (if any)\n"
            "  - I'll help you build one section by section right here"
        )
        return AdvanceResult(reply=reply, journey=journey,
                              profile_updates=profile_updates)

    # Defensive: unknown discover step.
    journey.discover_step = DISCOVER_ASK_ROLE
    return AdvanceResult(
        reply="Let me restart the questions — what kind of role?",
        journey=journey,
    )


def _parse_years(text: str) -> int | None:
    """Pull an integer years count from messy free text.
    "3" → 3, "about 7 years" → 7, "ten" → 10, "" → None."""
    if not text:
        return None
    # Numeric first.
    m = re.search(r"\b(\d{1,2})\b", text)
    if m:
        n = int(m.group(1))
        if 0 <= n <= 60:
            return n
    # Word numbers.
    words = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
        # German
        "null": 0, "eins": 1, "ein": 1, "zwei": 2, "drei": 3, "vier": 4,
        "fünf": 5, "fuenf": 5, "sechs": 6, "sieben": 7, "acht": 8,
        "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12, "zwoelf": 12,
        "fünfzehn": 15, "fuenfzehn": 15, "zwanzig": 20,
    }
    lc = text.lower()
    for word, value in words.items():
        if re.search(rf"\b{word}\b", lc):
            return value
    return None


# ---------------- Phase: cv_check ----------------


# ---------------- Result clustering ----------------
#
# When the search returns N jobs we group them so the user can drill
# into a category they care about, ChatGPT-style. The heuristic is
# deliberately simple — keyword buckets over the title + a fallback
# of "Other". An AI-backed clusterer is a Round-18 upgrade.

_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Clinical / Pflege", ("pflege", "nurse", "nursing", "clinical",
                              "krank", "altenpflege", "betreuung",
                              "care", "hca", "patient")),
    ("Hospitality / Bar", ("bartender", "barkeeper", "barista", "café",
                              "cafe", "kellner", "waiter", "wait staff",
                              "host", "server", "restaurant", "hotel")),
    ("Tech / Engineering", ("engineer", "developer", "backend", "frontend",
                              "devops", "sre", "platform", "ml", "data",
                              "fullstack", "tech")),
    ("Marketing / Brand", ("marketing", "growth", "brand", "seo",
                              "content", "social", "crm", "performance")),
    ("Operations / Admin", ("operations", "ops", "admin", "coordinator",
                              "assistant", "office", "manager")),
)


def categorize_job(title: str, description: str = "") -> str:
    """Bucket a job into one of the curated categories. Returns
    \"Other\" if nothing matches — that's still a valid category the
    user can drill into."""
    hay = f"{title or ''} {description or ''}".lower()
    for category, needles in _CATEGORY_KEYWORDS:
        for needle in needles:
            if needle in hay:
                return category
    return "Other"


def cluster_jobs(jobs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group jobs by category. ``jobs`` is the list of job dicts the
    find_jobs handler emits (title + company + location + url + source).
    Returns ``{category: [job, ...]}``. Order is determined by the
    insertion order of _CATEGORY_KEYWORDS so the UI stays predictable."""
    buckets: dict[str, list[dict[str, Any]]] = {}
    for job in jobs:
        cat = categorize_job(
            job.get("title", ""),
            job.get("description") or job.get("rawDescription") or "",
        )
        buckets.setdefault(cat, []).append(job)
    return buckets


# Sectional build via chat — minimal 5-step schema. Each step's
# prompt is shown verbatim to the user. Order matters.
_CV_BUILD_SEQUENCE: tuple[tuple[str, str], ...] = (
    ("name", "**1/5 — What's your full name?**"),
    ("location", "**2/5 — What city / region are you in?**"),
    ("summary", "**3/5 — In 2-3 sentences: what do you do, and what "
                "are you best known for?** Write casually — I'll keep "
                "the wording, never invent."),
    ("recent_role", "**4/5 — Your most recent role.** Tell me: "
                     "company, title, dates (TT.MM.JJJJ), and 2-3 "
                     "things you actually did there."),
    ("skills", "**5/5 — Your skills.** Comma-separated. "
                "Only list ones you'd defend in an interview."),
)
_CV_BUILD_STEP_PROMPTS = dict(_CV_BUILD_SEQUENCE)
_CV_BUILD_ORDER = tuple(k for k, _ in _CV_BUILD_SEQUENCE)


def cv_build_next_step(current: str) -> str:
    """Return the next step after ``current`` in the build sequence,
    or "done" if the sequence is complete."""
    if not current:
        return _CV_BUILD_ORDER[0]
    try:
        idx = _CV_BUILD_ORDER.index(current)
    except ValueError:
        return _CV_BUILD_ORDER[0]
    return _CV_BUILD_ORDER[idx + 1] if idx + 1 < len(_CV_BUILD_ORDER) else "done"


def cv_build_prompt_for(step: str) -> str:
    """The user-facing question for a build step. Empty for "done"."""
    return _CV_BUILD_STEP_PROMPTS.get(step, "")


def assemble_cv_from_build(answers: dict[str, str]) -> str:
    """Assemble the sectional-build answers into a plain-text CV.
    DACH-norm-ish: name + location + summary + most-recent role + skills.

    The wizard's full pipeline (formatted Markdown + photo) lives in
    company_discovery.cv_builder.assemble_cv_markdown. The chat-built
    CV is intentionally simpler — the user can later /tailor it
    against a specific job. We never invent: every field is the
    user's literal text, sanitised only for length.
    """
    def s(k: str, default: str = "") -> str:
        return (answers.get(k) or default).strip()[:1000]

    name = s("name", "")
    location = s("location", "")
    summary = s("summary", "")
    recent = s("recent_role", "")
    skills = s("skills", "")

    parts: list[str] = []
    if name:
        parts.append(f"# {name}")
    if location:
        parts.append(location)
    if summary:
        parts.append(f"\n## Summary\n\n{summary}")
    if recent:
        parts.append(f"\n## Recent experience\n\n{recent}")
    if skills:
        parts.append(f"\n## Skills\n\n{skills}")
    return "\n".join(parts)


def _advance_cv_check(
    journey: UserJourney, msg: str, *, has_existing_cv: bool
) -> AdvanceResult:
    if journey.cv_status == "unknown":
        # First entry — ask which path. If the user has an existing CV,
        # offer that as the easy default.
        lower = msg.lower().strip()
        if has_existing_cv and lower in {"reuse", "use existing", "yes",
                                          "ja", "use my cv", "use it"}:
            journey.cv_status = "uploaded"
            journey.phase = PHASE_INSPIRE
            chained = _advance_inspire(journey, "",
                                          ai_available=False,
                                          ai_caller=None)
            chained.reply = (
                "Reusing your existing CV. Moving on to suggestions.\n\n"
                + chained.reply
            )
            return chained
        if lower in {"build", "build one", "build it", "help me build",
                      "no", "nein", "neu", "no cv"}:
            journey.cv_status = "building"
            journey.cv_build_step = _CV_BUILD_ORDER[0]
            return AdvanceResult(
                reply=(
                    "OK — I'll walk you through 5 quick questions.\n\n"
                    + cv_build_prompt_for(journey.cv_build_step)
                ),
                journey=journey,
            )
        if len(msg) >= 80:
            # Looks like the user pasted a CV.
            journey.cv_status = "uploaded"
            journey.phase = PHASE_INSPIRE
            chained = _advance_inspire(journey, "",
                                          ai_available=False,
                                          ai_caller=None)
            chained.reply = (
                f"Got it — captured **{len(msg)} chars** of CV. "
                f"Moving on to suggestions.\n\n{chained.reply}"
            )
            chained.profile_updates = {
                **chained.profile_updates, "cv_text": msg,
            }
            return chained
        # Couldn't determine intent — re-ask.
        existing_hint = (
            "  - Reply **\"reuse\"** to use your existing CV\n"
            if has_existing_cv else ""
        )
        return AdvanceResult(
            reply=(
                "Three ways forward:\n"
                f"{existing_hint}"
                "  - **Paste** the whole CV text in this chat\n"
                "  - **\"build\"** — I'll ask you section by section"
            ),
            journey=journey,
            persist=False,
        )

    # Sectional build in progress.
    if journey.cv_status == "building":
        step = journey.cv_build_step or _CV_BUILD_ORDER[0]
        if step == "done":
            assembled = assemble_cv_from_build(journey.cv_build_answers)
            journey.phase = PHASE_INSPIRE
            return AdvanceResult(
                reply=(
                    f"Saved CV ({len(assembled)} chars). Moving on to "
                    "suggestions."
                ),
                journey=journey,
                profile_updates={"cv_text": assembled},
            )
        # Empty message at the kick-off — just ask the current step.
        if not msg:
            return AdvanceResult(
                reply=cv_build_prompt_for(step),
                journey=journey,
                persist=False,
            )
        # Store the user's answer, advance to next step.
        journey.cv_build_answers[step] = msg.strip()
        next_step = cv_build_next_step(step)
        journey.cv_build_step = next_step
        if next_step == "done":
            assembled = assemble_cv_from_build(journey.cv_build_answers)
            journey.phase = PHASE_INSPIRE
            # Chain into the inspire phase immediately so the user
            # gets the suggestions in the same turn instead of having
            # to send another message.
            chained = _advance_inspire(journey, "",
                                          ai_available=False,
                                          ai_caller=None)
            chained.reply = (
                f"Got it. CV assembled ({len(assembled)} chars). "
                f"Moving on to suggestions.\n\n{chained.reply}"
            )
            chained.profile_updates = {
                **chained.profile_updates, "cv_text": assembled,
            }
            return chained
        return AdvanceResult(
            reply=cv_build_prompt_for(next_step),
            journey=journey,
        )

    # cv_status uploaded already — advance.
    if journey.cv_status == "uploaded":
        journey.phase = PHASE_INSPIRE
        return AdvanceResult(
            reply="Moving to suggestions.",
            journey=journey,
        )

    return AdvanceResult(
        reply="(unknown CV state — please retry)",
        journey=journey,
        persist=False,
    )


# ---------------- Phase: inspire ----------------


def _advance_inspire(
    journey: UserJourney, msg: str, *,
    ai_available: bool,
    ai_caller: Callable[[str, str], str | None] | None,
) -> AdvanceResult:
    # On entry, we MAY have no msg — that's the first turn after CV.
    # Generate suggestions and offer them.
    if not journey.lateral_roles:
        suggestions = _suggest_lateral_roles(
            role_text=journey.role_text,
            bucket_key=journey.bucket_key,
            years_experience=journey.years_experience,
            ai_available=ai_available,
            ai_caller=ai_caller,
        )
        journey.lateral_roles = suggestions["roles"]
        prefix = (
            "" if ai_available
            else ("_(I'm working without an AI right now — these are "
                  "templated from your persona defaults.)_\n\n")
        )
        roles_md = "\n".join(f"  - {r}" for r in journey.lateral_roles)
        reply = (
            f"{prefix}"
            f"Based on what you've told me, you'd also be competitive for:\n"
            f"{roles_md}\n\n"
            "**Want me to search those too?** Reply:\n"
            "  - **yes** to add all\n"
            "  - **no** to stick with just your stated role\n"
            "  - or paste a comma-separated list of the ones you want"
        )
        return AdvanceResult(reply=reply, journey=journey)

    # User responding to the suggestion offer.
    lc = msg.lower().strip()
    if lc in {"yes", "y", "all", "ja", "sure", "ok", "okay"}:
        journey.target_roles = [journey.role_text] + journey.lateral_roles
    elif lc in {"no", "n", "nein", "skip", "stick"}:
        journey.target_roles = [journey.role_text]
    elif msg:
        chosen = [t.strip() for t in msg.split(",") if t.strip()]
        journey.target_roles = [journey.role_text] + chosen
    else:
        return AdvanceResult(
            reply="Reply **yes**, **no**, or a comma-separated list.",
            journey=journey,
            persist=False,
        )

    journey.phase = PHASE_PREFS
    return AdvanceResult(
        reply=(
            f"Locked in: searching for **{', '.join(journey.target_roles)}**.\n\n"
            "**Any deal-breakers?** Reply with any of:\n"
            "  - **remote** if remote is required\n"
            "  - **min 50k** (or any salary floor)\n"
            "  - **startup / mid / enterprise** for company size\n"
            "  - **none** / **skip** to move on"
        ),
        journey=journey,
    )


def _suggest_lateral_roles(
    *, role_text: str, bucket_key: str, years_experience: int | None,
    ai_available: bool, ai_caller: Callable[[str, str], str | None] | None,
) -> dict[str, Any]:
    """Return ``{"roles": [str, ...]}`` — 3-5 lateral roles for the
    user. When AI is available, asks the LLM via ``ai_caller``;
    otherwise falls back to the bucket's neighbours from the
    taxonomy (or a generic adjacent-role list)."""
    if ai_available and ai_caller is not None:
        system = (
            "You are a career advisor. Given a job seeker's "
            "stated target role and years of experience, suggest "
            "3-5 adjacent roles they'd be qualified for but didn't "
            "explicitly ask about. Output ONLY a JSON list of "
            "strings, no prose. Example: "
            "[\"Pflegeassistent\", \"Altenpfleger\", \"OTA\"]."
        )
        user_msg = (
            f"Target role: {role_text}\n"
            f"Years experience: {years_experience or 'unspecified'}"
        )
        try:
            raw = ai_caller(system, user_msg)
        except Exception:  # noqa: BLE001
            raw = None
        roles = _parse_role_list(raw or "")
        if roles:
            return {"roles": roles}

    # Templated fallback by bucket — uses the taxonomy's neighbouring
    # buckets so the user gets a sensible alternative even with no AI.
    fallback_map = {
        "bartender": ["Barista", "Restaurant Server", "Bar Manager",
                       "Event Bartender"],
        "barista": ["Bartender", "Café Manager", "Coffee Shop Assistant",
                     "Event Crew"],
        "cafe_worker": ["Barista", "Restaurant Server", "Café Manager"],
        "pflegehelfer": ["Pflegeassistent", "Altenpflegehelfer",
                          "Krankenpflegehelfer", "Pflegekraft"],
        "waiter": ["Bartender", "Hospitality Crew", "Restaurant Host",
                    "Banquet Server"],
    }
    by_bucket = fallback_map.get(bucket_key)
    if by_bucket:
        return {"roles": by_bucket}
    # Last-resort generic: just echo the user's role with seniority
    # variants so they see SOMETHING.
    base = role_text.strip() or "Job"
    return {"roles": [f"Senior {base}", f"Lead {base}", f"Assistant {base}"]}


def _parse_role_list(text: str) -> list[str]:
    """Pull a list of role strings from an AI response. Accepts both
    a JSON array and a newline / comma-separated fallback."""
    text = (text or "").strip()
    if not text:
        return []
    import json as _json
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        try:
            parsed = _json.loads(m.group(0))
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed
                         if str(x).strip()][:5]
        except (_json.JSONDecodeError, ValueError):
            pass
    items = [t.strip("- •*\t ") for t in re.split(r"[\n,]", text)
              if t.strip()]
    return [i for i in items if i and not i.startswith("{")][:5]


# ---------------- Phase: preferences ----------------


def _advance_prefs(journey: UserJourney, msg: str) -> AdvanceResult:
    lc = msg.lower().strip()
    if lc in {"none", "skip", "no preference", "nothing"}:
        pass  # accept defaults
    else:
        if "remote" in lc:
            journey.remote_required = True
        # Salary floor: "min 50k" / "50000+" / "at least 45000"
        m = re.search(r"\b(\d{2,3})\s*[kK]?\b", lc)
        if m:
            v = int(m.group(1))
            journey.salary_floor = v * 1000 if v < 1000 else v
        if "startup" in lc:
            journey.company_size = "startup"
        elif "enterprise" in lc or "large" in lc:
            journey.company_size = "enterprise"
        elif "mid" in lc or "medium" in lc:
            journey.company_size = "mid"

    journey.phase = PHASE_SEARCH
    return AdvanceResult(
        reply=(
            f"Searching for **{', '.join(journey.target_roles)}** in "
            f"**{journey.location or 'anywhere'}**…"
        ),
        journey=journey,
        run_search_with={
            "target_roles": list(journey.target_roles),
            "location": journey.location or None,
            "remote_required": journey.remote_required,
            "salary_floor": journey.salary_floor,
            "company_size": journey.company_size or None,
        },
    )


# ---------------- Phase: review ----------------


def _advance_review(journey: UserJourney, msg: str) -> AdvanceResult:
    """User has been shown the categorized results and is picking a
    category. Renders the top-N jobs in the chosen category with
    title/company/location/link so the user can drill into a specific
    posting (R17.5)."""
    categories = list(journey.search_results_by_category.keys())
    if not categories:
        journey.phase = PHASE_DONE
        return AdvanceResult(
            reply=(
                "No results to drill into. Try a different role or "
                "widen the location. Type \"find a job\" to retry."
            ),
            journey=journey,
            done=True,
        )
    lc = msg.lower().strip()
    # Match the category by exact lowercased name OR substring (so
    # "clinical" matches "Clinical / Pflege").
    picked = next(
        (c for c in categories
          if c.lower() == lc or lc in c.lower() or c.lower().split(" /")[0] == lc),
        None,
    )
    if not picked:
        cats_md = "\n".join(f"  - {c}" for c in categories)
        return AdvanceResult(
            reply=(
                "Which category should I dig into? Reply with one of:\n"
                f"{cats_md}"
            ),
            journey=journey,
            persist=False,
        )
    journey.picked_category = picked
    journey.phase = PHASE_DRILL
    # Render top 10 jobs in the picked category.
    job_ids = journey.search_results_by_category.get(picked, [])[:10]
    lines: list[str] = []
    for i, jid in enumerate(job_ids, 1):
        job = journey.search_jobs_by_id.get(jid, {})
        title = job.get("title", "(no title)")
        company = job.get("company") or ""
        location = job.get("location") or ""
        url = job.get("url") or ""
        company_loc = " · ".join(p for p in (company, location) if p)
        suffix = f" — {company_loc}" if company_loc else ""
        link = f"\n     {url}" if url else ""
        lines.append(f"  {i}. **{title}**{suffix}{link}")
    listing = "\n".join(lines) or "  (no jobs in this category)"
    return AdvanceResult(
        reply=(
            f"**{picked}** — top {len(job_ids)} job(s):\n"
            f"{listing}\n\n"
            "Reply with the **number** of the job you want to focus on."
        ),
        journey=journey,
    )


# ---------------- Phase: drill ----------------


def _advance_drill(journey: UserJourney, msg: str) -> AdvanceResult:
    """User has been shown the top-N jobs in their chosen category;
    they're picking one to focus on. Returns the picked job's
    details + the next-action menu (letter / CV consult / save)."""
    job_ids = journey.search_results_by_category.get(
        journey.picked_category, []
    )
    if not job_ids:
        journey.phase = PHASE_DONE
        return AdvanceResult(
            reply="No jobs in that category. Try `find a job` again.",
            journey=journey,
            done=True,
        )
    m = re.search(r"\b(\d+)\b", msg or "")
    if not m:
        return AdvanceResult(
            reply="Type the number of the job (e.g., \"1\" or \"3\").",
            journey=journey,
            persist=False,
        )
    idx = int(m.group(1)) - 1
    if idx < 0 or idx >= len(job_ids):
        return AdvanceResult(
            reply=f"That number's out of range — pick 1-{len(job_ids)}.",
            journey=journey,
            persist=False,
        )
    job_id = job_ids[idx]
    journey.picked_job_id = job_id
    journey.phase = PHASE_TAILOR
    # Surface the chosen job's details verbatim.
    job = journey.search_jobs_by_id.get(job_id, {})
    title = job.get("title", "(no title)")
    company = job.get("company", "")
    location = job.get("location", "")
    url = job.get("url", "")
    detail_lines = [f"**{title}**"]
    if company:
        detail_lines.append(f"Company: {company}")
    if location:
        detail_lines.append(f"Location: {location}")
    if url:
        detail_lines.append(f"Apply / view: {url}")
    detail = "\n".join(detail_lines)
    return AdvanceResult(
        reply=(
            f"{detail}\n\n"
            "For this job I can:\n"
            "  - **letter** — draft a DACH-norm motivation letter\n"
            "  - **consult** — suggest CV enhancements specific to this JD\n"
            "  - **save** — mark as interested and move on\n\n"
            "Which?"
        ),
        journey=journey,
    )
