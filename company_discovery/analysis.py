# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from company_discovery.env_compat import get_env

from . import audit_log
from .ai_providers import AIProviderConfig
from .models import DiscoveredJob, ImportedJob, UserProfile
from .personas import get_persona


@dataclass
class AnalysisExecutionResult:
    status: str
    provider_id: str
    invocation_mode: str
    output: str = ""
    error: str = ""
    prompt: str = ""


_HEALTHCARE_SECTION_LABEL = "Healthcare relevance"
_GENERIC_SECTION_LABEL = "Persona relevance"


def _persona_fixture_for(slug: str | None):
    """Lookup the canonical :class:`PersonaFixture` for the friction-
    class slug, or ``None`` if the slug isn't in the seven-panel
    fixture set.

    The fixture carries fields the lighter ``Persona`` object does not:
    ``residency_status`` (visa / Aufenthaltstitel), ``friction_notes``
    (gap-year, Anerkennung pathway, language proficiency, etc.). These
    feed the analysis prompts so the AI's reasoning is anchored to the
    candidate's real friction context, not a generic role-and-industry
    sketch.

    Bug F Option B (Loop 10.3, 2026-05-20): callers pass
    ``profile.friction_class`` (set by the cv_check classification
    hook from CV text). Earlier consumers passed ``profile.persona_id``
    which never resolved to a fixture slug -- Loop 9.2 investigation
    confirmed that production users only ever land in the 15-industry
    registry, not the 7-fixture panel, so the lookup always returned
    None. The friction_class field (Loop 10.2) closes that gap.

    Defensive lookup: any failure returns ``None`` so the prompt
    builder degrades gracefully to the lighter ``Persona`` context.
    """
    if not slug:
        return None
    try:
        from company_discovery.persona_fixtures import PERSONAS

        for fixture in PERSONAS:
            if fixture.slug == slug:
                return fixture
        return None
    except Exception:  # noqa: BLE001, S110 - persona-fixture lookup is best-effort context enrichment; failure must not break the AI call
        return None


def _candidate_profile_block(
    profile: UserProfile | None,
    persona_id_default: str = "healthcare-management",
) -> tuple[str, str]:
    """Return a ``(persona_label, profile_lines_block)`` tuple.

    ``profile_lines_block`` is the multi-line "Candidate target profile"
    section embedded in every prompt. It always falls back to a sensible
    persona-specific default so the brief stays useful even when the user
    has not filled in their profile yet.

    Friction-context enrichment (PART 1 of the 2026-05-19 product-quality
    sweep): when the persona_id matches a known fixture in
    ``persona_fixtures.PERSONAS``, the block also surfaces
    ``residency_status`` (Aufenthaltstitel / visa) and ``friction_notes``
    (Anerkennung pathway, gap years, language proficiency). This makes
    every downstream prompt (auto-fit, decision brief, cover letter,
    CV tailoring) friction-aware without per-prompt rewrites.
    """

    persona_id = profile.persona_id if profile and profile.persona_id else persona_id_default
    persona = get_persona(persona_id)
    lines: list[str] = [f"- Persona: {persona.label} — {persona.description}"]

    target_roles = (
        list(profile.target_roles)
        if profile and profile.target_roles
        else list(persona.default_target_roles)
    )
    if target_roles:
        lines.append("- Target roles: " + ", ".join(target_roles))

    industry = (
        profile.industry if profile and profile.industry else persona.default_industry
    ) or ""
    if industry:
        lines.append(f"- Industry preference: {industry}")

    if profile and profile.location:
        lines.append(f"- Preferred location: {profile.location}")
    if profile and profile.seniority:
        lines.append(f"- Seniority target: {profile.seniority}")
    if profile and profile.years_experience is not None:
        lines.append(f"- Years of experience: {profile.years_experience}")
    if profile and profile.languages:
        lines.append("- Languages: " + ", ".join(profile.languages))
    if profile and profile.notes:
        lines.append(f"- Candidate notes: {profile.notes.strip()}")

    # Friction-context enrichment from PersonaFixture when available.
    # Bug F Option B (Loop 10.3, 2026-05-20): the fixture lookup
    # uses profile.friction_class (the cv_check-classified slug),
    # NOT profile.persona_id. persona_id stays as the industry-
    # segment registry signal driving breadth context above; the
    # friction-class slug drives the friction-context enrichment
    # below. Two fields, two concerns.
    fixture_slug = (
        profile.friction_class if profile and profile.friction_class
        else ""
    )
    fixture = _persona_fixture_for(fixture_slug)
    if fixture is not None:
        if fixture.residency_status:
            lines.append(f"- Aufenthaltstitel / residency status: {fixture.residency_status}")
        if fixture.friction_notes:
            lines.append(
                f"- Friction context (Anerkennung / Wiedereinstieg / language / etc.): "
                f"{fixture.friction_notes.strip()}"
            )

    if profile and (profile.cv_text or "").strip():
        cv = profile.cv_text.strip()
        if len(cv) > 4000:
            cv = cv[:4000] + "\n…(CV truncated to 4000 characters)"
        lines.append("\nCandidate CV (free-text, possibly partial):\n" + cv)
    else:
        lines.append(
            "- No CV uploaded yet — be cautious about claims of fit beyond what the role description supports."
        )

    return persona.label, "\n".join(lines)


def build_job_decision_brief_prompt(
    job: ImportedJob,
    provider: AIProviderConfig,
    profile: UserProfile | None = None,
) -> dict[str, str]:
    persona_label, profile_block = _candidate_profile_block(profile)
    provider_label = provider.provider_id.replace("_", " ").title()
    persona_id = profile.persona_id if profile and profile.persona_id else "healthcare-management"
    section_label = (
        _HEALTHCARE_SECTION_LABEL
        if persona_id == "healthcare-management"
        else _GENERIC_SECTION_LABEL
    )
    prompt = f"""You are helping evaluate a job opportunity for a {persona_label} candidate.

Create a concise Job Decision Brief for this role.

Strict rules:
- Use ONLY facts present in the candidate profile + the job description below. Do not invent the candidate's experience, skills, or visa status. Do not invent the company's culture, salary, or team size unless the JD states it.
- For LEGAL claims (visa rules, Anerkennung pathways, Bürgergeld eligibility, Aufenthaltstitel obligations), do not give legal advice; direct the candidate to BAMF, Bundesagentur für Arbeit, or a Migrationsberatungsstelle.
- Friction-context acknowledgment (NON-NEGOTIABLE when profile carries friction): if the candidate profile includes residency_status OR friction_notes, section 4 (Risks and blockers) MUST include at least one explicit friction-context line tying the friction to whether-to-apply, and section 8 (Application angle) MUST address how the candidate's friction context fits this specific role. Omitting friction when documented produces a generic brief that doesn't serve the candidate's actual situation.
- If the JD is in German, match its register; if English, use English. State the language assumption if the JD is empty.
- Format (NON-NEGOTIABLE): action-oriented sections — 4 (Risks and blockers), 7 (Likely keywords/tools), 8 (Application angle), 9 (Missing information to verify manually) — MUST be enumerated bullets with clear actions, NOT narrative blobs. Analytical sections — 3 (Why it fits), 5 (Seniority check), 6 (persona relevance section) — MAY be short prose paragraphs (2-3 sentences each).
- Forbidden filler phrases (case-insensitive — do NOT use these tired generic-application markers anywhere in the brief): "Hiermit bewerbe ich mich", "I am writing to express my interest", "I would like to apply for the position", "In conclusion", "Overall, this is", "It is important to note that", "Here are some key points", "I would recommend". These signal an untailored output. Use specific, role-anchored phrasing instead.

Candidate target profile:
{profile_block}

Job source:
- Source type: direct company career page
- Company: {job.company_name}
- Title: {job.title}
- Location: {job.location or "Unknown"}
- URL: {job.source_url}

Job description:
{job.description or "No full description was extracted. Use only the visible title/source facts and mark uncertainty clearly."}

Return exactly these sections:
1. Recommendation: Apply / Maybe / Skip
2. Fit score: 0-100 (avoid round-number anchoring; use the granular score that fits)
3. Why it fits
4. Risks and blockers — INCLUDE any friction-context concern (visa / language / Anerkennung) that materially affects this application
5. Seniority check
6. {section_label}
7. Likely keywords/tools
8. Application angle
9. Missing information to verify manually
10. Source confidence — note for each non-trivial claim above whether it is grounded in (a) the JD text, (b) the candidate's profile, or (c) general AI inference. Inference-only claims must be marked accordingly.
"""
    return {
        "title": f"Job Decision Brief: {job.title}",
        "providerId": provider.provider_id,
        "providerLabel": provider_label,
        "invocationMode": provider.invocation_mode,
        "prompt": prompt,
        "handoffInstruction": "Run this prompt with the user's selected AI subscription/provider. Do not require a vendor-specific key in this app.",
    }


def build_cover_letter_brief_prompt(
    job: ImportedJob,
    provider: AIProviderConfig,
    profile: UserProfile | None = None,
) -> dict[str, str]:
    """Build a prompt that drafts a job-specific cover letter."""

    persona_label, profile_block = _candidate_profile_block(profile)
    provider_label = provider.provider_id.replace("_", " ").title()
    prompt = f"""You are drafting a tailored cover letter for a {persona_label} candidate.

Goal: produce a polished cover letter (~280 words) that the candidate can
edit and send. Match the language of the job description (e.g. write in
German if the description is in German). If unsure, default to English
and note the assumption at the end.

Strict rules:
- Use ONLY facts present in the candidate profile + the job description below. Never invent the candidate's employers, dates, titles, achievements, certifications, language levels, or visa status.
- Acknowledge the candidate's documented friction context (Aufenthaltstitel / Anerkennung / Wiedereinstieg / language level) when it materially helps explain the candidate's fit — but DO NOT over-emphasise friction in the opening (the opening should foreground capability + interest, not bureaucratic context).
- German register: if writing in German, default to "Sehr geehrte Damen und Herren" unless the JD names a specific contact; close with "Mit freundlichen Grüßen"; address the reader with "Sie", never "du".
- Do not give legal advice. If a visa or Anerkennung question is implied, point the candidate to BAMF or the Migrationsberatungsstelle in the editing-notes section, never in the letter body.
- Job-specificity (NON-NEGOTIABLE): the letter body MUST reference at least 2 DISTINCT facts from the job description — (1) the role title in the opening or closing call-to-action, AND (2) at least one specific responsibility, required skill, or company-context detail named in the JD (e.g., a specific tool, a specific team structure, a specific clinical area, a specific business domain). Source restriction is absolute: if the JD does not explicitly state a fact, do NOT invent it. If the JD is thin on specifics, use generic-but-honest language ("the role's clinical focus", "the team's emphasis on X as described in the listing") and flag it in the editing notes.
- Format (NON-NEGOTIABLE): the letter body is flowing PROSE only — three paragraphs, no markdown bullets, no enumerated lists, no headers inside the body. The editing-notes section MAY use bullets; the letter itself MAY NOT.
- Forbidden filler phrases (case-insensitive): do NOT write "Hiermit bewerbe ich mich", "I am writing to express my interest", "I would like to apply for the position", "In conclusion", "Overall, this is", "It is important to note that", "Here are some key points", "I would recommend". These are tired generic-application markers and signal an untailored letter. Open the letter with a SPECIFIC anchor (the role + the company context that motivated the application). Close with a SPECIFIC call to action, not a generic platitude.

Candidate profile:
{profile_block}

Job:
- Company: {job.company_name}
- Title: {job.title}
- Location: {job.location or "Unknown"}
- URL: {job.source_url}

Job description:
{job.description or "No full description was extracted — use only the visible title/source facts and stay generic where the description is unknown."}

Return exactly these sections:
1. Subject line / opening salutation (Sehr geehrte... / Dear...).
2. Cover letter body (3 short paragraphs):
   - Why the candidate is excited about *this specific* company / role
   - Concrete experience and skills that map onto the role's needs (use ONLY CV facts)
   - A short closing with a clear call to action
3. Editing notes for the candidate: 2-4 bullets calling out claims that need
   to be verified, sentences to personalize further, or weak spots to fix.
4. Draft assumptions: list any inference you made (language, seniority,
   missing CV details). Be honest if information is thin.
5. Source citations (Quellen) — NOT part of the letter, for the candidate's
   verification only. For each non-trivial factual claim in the body
   (sections 1+2 above), list its source verbatim. Format:
       - "<claim sentence from letter>"
         ← [CV] "<quoted CV excerpt the claim derives from>"
       - "<claim sentence from letter>"
         ← [JD] "<quoted JD excerpt the claim derives from>"
       - "<claim sentence from letter>"
         ← [Inference] (one-line honest explanation of the assumption)
   Aim for 3-6 entries covering every non-trivial fact-bearing claim. This
   surface implements the source-class hierarchy doctrine at
   docs/grant/14-source-class-hierarchy.md — the candidate can audit every
   claim back to its CV (class E), JD (class E), or labelled inference
   (class G) origin.
"""
    return {
        "title": f"Cover Letter Draft: {job.title}",
        "providerId": provider.provider_id,
        "providerLabel": provider_label,
        "invocationMode": provider.invocation_mode,
        "prompt": prompt,
        "handoffInstruction": "Run this prompt with the user's selected AI subscription/provider. Do not require a vendor-specific key in this app.",
    }


def build_auto_fit_prompt(
    job: DiscoveredJob,
    company_name: str,
    provider: AIProviderConfig,
    profile: UserProfile | None = None,
) -> dict[str, str]:
    """Build a short prompt that asks the AI for a fit score 0–100 + 1-line reason.

    Designed to be cheap to run on every newly discovered job — the
    output is parsed by :func:`parse_auto_fit_output` into a structured
    score so the queue can be sorted by fit.

    Per-criterion decomposition (R4 finding from the R12-polish bias
    run): asking for a single 0–100 score caused the model to anchor
    on round numbers (85, 92) instead of producing a true continuous
    score. The prompt now asks for four sub-scores summed into a
    total, which forces the model to reason granularly rather than
    pick a familiar round number. Output stays backwards-compatible
    (the SCORE line still carries the total), so
    :func:`parse_auto_fit_output` doesn't need to change.
    """

    persona_label, profile_block = _candidate_profile_block(profile)
    prompt = f"""You are scoring a job posting for a {persona_label} candidate.

Output exactly these lines, no headers, no other text:
SCORE_SKILLS: <integer 0-25> — match between the candidate's CV skills and the JD's required skills
SCORE_EXPERIENCE: <integer 0-25> — seniority + years-of-experience + relevance of past roles vs the JD
SCORE_LOCATION_LANGUAGE: <integer 0-25> — geographic + language fit (CEFR level vs JD language; visa / residency status if relevant)
SCORE_FRICTION_FIT: <integer 0-25> — how well this role accommodates the candidate's documented friction context (Anerkennung pathway, Wiedereinstieg, visa, gap-year)
SCORE: <integer 0-100, MUST equal the sum of the four sub-scores above>
REASON: <one short sentence, max 25 words, naming the dominant driver of the score>
GAPS: <up to three short skill phrases, comma-separated, that the JD demands but the candidate's CV does not show. Use empty string when no clear gaps>

Anchor scale for SCORE_SKILLS, SCORE_EXPERIENCE, SCORE_LOCATION_LANGUAGE (each on 0-25; bands span the full range):
  22-25 = exceptional match — the CV directly meets or exceeds the JD's bar at the level requested (rare; reserve for cases where you can name the specific match)
  17-21 = good match — most of the criterion's requirements are met with one or two minor gaps
  13-16 = moderate match — some requirements met, several gaps but transferable
  8-12 = weak match — few requirements met, significant gaps
  0-7 = wrong domain entirely for this criterion (or N/A treated as neutral-low)

SCORE_FRICTION_FIT anchor scale uses pathway-differentiation (NOT the generic match scale above — friction-fit asks "does THIS job accommodate the candidate's documented friction?", not "does the candidate match the criterion?"):
  22-25 = friction present + CLEAN pathway + employer accommodation. The job is EXPLICITLY structured to accommodate the candidate's friction class. DECISION RULE (apply mechanically — if the JD names ANY of these AND the candidate's friction context matches, score 22+; do NOT downgrade to "ambiguous" just because the language isn't ornate):
    - JD names "EU Blue Card" / "Blue Card sponsorship" / "Blaue Karte" — AND candidate is a non-EU professional whose residency_status implies Blue Card need (e.g., Turkish national targeting Germany; non-EU professional with a degree-equivalent qualification): CLEAN
    - JD names "English-team" / "English-speaking team" / "English-language work environment" / "international working language" — AND candidate's German is below C1 (residency_status / friction_notes indicates B1/B2/learning German): CLEAN
    - JD names "Anerkennungs-freundlich" / "Anerkennung-friendly" / "supports Anerkennung process" / "Anerkennungspartner" — AND candidate is on §16d AufenthG or otherwise in recognition pathway: CLEAN
    - JD names "Wiedereinstiegsprogramm" / "Wiedereinstiegspflege" / "returner mentor-program" — AND candidate is a Wiedereinsteigerin (gap of 5+ years from prior career): CLEAN
    - JD names "Ausbildung" / "duale Ausbildung" / "Trainee-Programm" / "Quereinsteiger willkommen" — AND candidate is a §4 AsylG subsidiary-protection holder, late-career pivot, or career changer: CLEAN
    - JD names "§16d" / "§24 AufenthG recognition" / "post-Brexit residency support" — AND candidate's status directly matches: CLEAN
  If the JD does NOT name an element matching the candidate's friction, fall through to 17-21 (clear pathway) or below per the rest of this scale. The decision rule does NOT shift the anchor scale up — it tells you when to award the top band that already exists.
  17-21 = friction present + CLEAR pathway. The employer mentions relevant pathway elements (visa-sponsorship language, language-school benefit, returner-mentorship) without being explicitly structured around the candidate's friction class.
  12-16 = friction present + AMBIGUOUS pathway. The JD doesn't address the candidate's friction explicitly; not hostile, but not welcoming either.
  5-11 = friction present + HIGH BARRIER. Requirements don't fit the candidate's friction profile (C2 German required for B1 candidate; permanent-residence-required for §16d holder; no language support listed for a non-German-fluent applicant).
  0-4 = friction present + NO pathway. The JD explicitly excludes the candidate's status ("only EU citizens"; "C1 German native-speaker level" for a B1 candidate; "permanent contract requires unrestricted work permit").
If friction is genuinely not material to THIS role (e.g., fully-remote tech role for a candidate with no documented friction), score 17-22 as "neutral / role accommodates as needed."

Entry-level / training-program JDs (Ausbildung, Trainee, Praktikum, Quereinsteiger, Berufseinstieg):
For these JDs, SCORE_SKILLS and SCORE_EXPERIENCE evaluate the candidate's FOUNDATIONAL POTENTIAL and APTITUDE for the program, NOT their current professional level. An Ausbildung JD that says "Vorkenntnisse nicht erforderlich, wir bilden Sie aus" expects candidates with relevant interest + foundational fit, not professionally-credentialed skills. Score HIGH (17-22) on SKILLS and EXPERIENCE when the candidate's profile fits the entry-level demographic (informal exposure to the trade, motivation, basic prerequisites met), even if their CV doesn't list the trade's professional-level certifications. The JD's bar IS entry-level for these roles; matching that bar is a strong fit.

Calibration: a job that genuinely matches the candidate's target role
+ experience + language + friction context should aggregate to
SCORE >= 75 (good-to-exceptional across the four criteria). A
moderate match should land 50-65. A weak / wrong-domain match should
land < 30.

Strict rules:
- Do NOT invent facts about the candidate beyond what the profile block contains.
- Do NOT invent facts about the job beyond what the snippet contains.
- The four sub-scores MUST sum to exactly the SCORE total.
- Avoid round-number anchoring: if the granular sub-scores sum to 73, output 73, NOT 75.
- Avoid anchor-point parking (SELF-CHECK rule, direction-symmetric): the anchors (22, 17, 13, 8, 2; and 22, 17, 12, 5, 0 for SCORE_FRICTION_FIT) describe the CENTER of each band, but each band is a continuous range. SELF-CHECK after drafting your four sub-scores: count how many are at exact anchor values (22, 17, 13, 12, 8, 5, 2, 0). If 3 or 4 are at exact anchors, look at each in turn:
    • Was the match TEXTBOOK at the anchor (clean, no asymmetric signal in either direction)? Then the anchor stands — that's an honest read.
    • Was the match SLIGHTLY ABOVE OR SLIGHTLY BELOW the anchor's textbook center? Then revise to the intermediate value that captures the direction you observed.
  The revision direction is determined by the OBSERVED signal — NOT by a default. A good match with one minor gap is 16 (slightly weaker than textbook good); a good match exceeding textbook in one dimension is 19 (slightly stronger). A moderate match with stronger transferable skills is 15; a moderate match with several gaps is 11. An exceptional match with one tiny weakness is 23; a textbook-good match approaching exceptional is 21. UP-revision and DOWN-revision are EQUALLY likely a priori — choose based on the specific signal, not on a default direction. Use intermediate values (3-4, 6-7, 9-12, 14-16, 18-21, 23-24) when the match has a signal that doesn't sit exactly on the anchor.

Candidate target profile:
{profile_block}

Job:
- Company: {company_name}
- Title: {job.title}
- Location: {job.location or "Unknown"}
- URL: {job.source_url}

Snippet / partial description (may be empty):
{(job.raw_description or job.raw_snippet or "")[:1500]}
"""
    return {
        "title": f"Auto-fit: {job.title}",
        "providerId": provider.provider_id,
        "providerLabel": provider.provider_id.replace("_", " ").title(),
        "invocationMode": provider.invocation_mode,
        "prompt": prompt,
        "handoffInstruction": "Auto-fit is intended for direct-API providers. Manual handoff still works but defeats the purpose.",
    }


_QUERY_EXPANSION_FENCED_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```", re.IGNORECASE | re.DOTALL
)
_QUERY_EXPANSION_BARE_RE = re.compile(r"(\{(?:[^{}]|\{[^{}]*\})*\})", re.DOTALL)


def build_cv_query_expansion_prompt(
    profile: UserProfile | None,
    free_text: str | None,
    provider: AIProviderConfig,
) -> dict[str, str]:
    """Ask the LLM to translate a CV + free-text wish into a search query.

    Output JSON shape (the parser tolerates fences + prose around it):

        {
          "persona_id": "healthcare-management",
          "target_roles": ["healthcare policy consultant", "..."],
          "industry": "Healthcare consulting",
          "location": "Berlin",
          "keywords": ["health policy", "consulting", "DACH", "..."],
          "language": "en" | "de"
        }
    """

    persona_label, profile_block = _candidate_profile_block(profile)
    free_text_block = (free_text or "").strip() or "(no free-text wish provided)"
    valid_personas = ", ".join(sorted(get_persona(None).id for _ in range(1)))  # placeholder
    from .personas import PERSONAS

    valid_personas = ", ".join(sorted(PERSONAS.keys()))

    prompt = f"""You are converting a candidate's CV + a free-text wish into a structured search query for a job-aggregator pipeline.

Candidate profile (existing):
{profile_block}

Free-text wish from the user:
{free_text_block}

Return a SINGLE JSON object (no commentary, no Markdown fences) with EXACTLY these keys:
  persona_id     — one of: {valid_personas}
  target_roles   — array of 3-5 specific role titles (job-board-friendly phrasing)
  industry       — one short industry label
  location       — short location string ("" if global / remote)
  keywords       — array of 3-7 search keywords (1-3 words each)
  language       — "en" or "de", inferred from the CV/wish

Rules:
- Use the CV's actual content if present; don't invent skills.
- If the wish contradicts the persona, prefer the wish.
- Keep keywords short and concrete — they will be used as substring matches against job titles + descriptions.
- Output JSON only. No prose.
"""
    return {
        "title": "CV → query expansion",
        "providerId": provider.provider_id,
        "providerLabel": provider.provider_id.replace("_", " ").title(),
        "invocationMode": provider.invocation_mode,
        "prompt": prompt,
        "handoffInstruction": "Return one JSON object only. No fences, no comments.",
    }


def parse_query_expansion_output(output: str) -> dict[str, object] | None:
    """Extract the JSON envelope from an LLM expansion response.

    Tolerates Markdown fences and surrounding prose. Returns ``None`` on
    failure so the caller can fall back to persona defaults.
    """

    if not output:
        return None
    candidates: list[str] = []
    fenced = _QUERY_EXPANSION_FENCED_RE.search(output)
    if fenced:
        candidates.append(fenced.group(1))
    bare = _QUERY_EXPANSION_BARE_RE.search(output)
    if bare:
        candidates.append(bare.group(1))
    candidates.append(output.strip())
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except (TypeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        if "target_roles" not in data and "keywords" not in data:
            continue
        # Coerce types defensively.
        cleaned: dict[str, object] = {}
        cleaned["persona_id"] = str(data.get("persona_id") or "").strip() or None
        cleaned["target_roles"] = [
            str(r).strip() for r in (data.get("target_roles") or []) if str(r).strip()
        ][:8]
        cleaned["industry"] = str(data.get("industry") or "").strip() or None
        cleaned["location"] = str(data.get("location") or "").strip() or None
        cleaned["keywords"] = [
            str(k).strip() for k in (data.get("keywords") or []) if str(k).strip()
        ][:10]
        lang = str(data.get("language") or "").strip().lower()
        cleaned["language"] = lang if lang in ("en", "de") else None
        return cleaned
    return None


def execute_cv_query_expansion(
    profile: UserProfile | None,
    free_text: str | None,
    provider: AIProviderConfig,
    runtime_credential: str = "",
    *,
    cap_context=None,
    receipt_emitter=None,
) -> AnalysisExecutionResult:
    brief = build_cv_query_expansion_prompt(profile, free_text, provider)
    return _dispatch_provider(
        brief["prompt"],
        provider,
        runtime_credential,
        purpose="cv_query_expansion",
        cap_context=cap_context,
        receipt_emitter=receipt_emitter,
    )


_AUTO_FIT_SCORE_RE = re.compile(r"score\s*[:\-]\s*(\d{1,3})", re.IGNORECASE)
_AUTO_FIT_REASON_RE = re.compile(r"reason\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_AUTO_FIT_GAPS_RE = re.compile(r"gaps\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE)


def parse_auto_fit_output(output: str) -> tuple[float | None, str | None, list[str]]:
    """Extract ``(score 0-1, reason, gaps)`` from the AI output.

    Returns ``(None, None, [])`` when the model didn't follow the format.
    The ``gaps`` list is empty when the model omitted the GAPS line or
    when the line was literally empty (the prompt allows the empty
    answer when no clear gaps exist)."""

    if not output:
        return None, None, []
    score_match = _AUTO_FIT_SCORE_RE.search(output)
    reason_match = _AUTO_FIT_REASON_RE.search(output)
    gaps_match = _AUTO_FIT_GAPS_RE.search(output)
    score = None
    if score_match:
        try:
            value = int(score_match.group(1))
        except ValueError:
            value = None
        if value is not None:
            score = max(0.0, min(1.0, value / 100.0))
    reason = reason_match.group(1).strip() if reason_match else None
    if reason and len(reason) > 280:
        reason = reason[:277] + "…"
    gaps: list[str] = []
    if gaps_match:
        raw = gaps_match.group(1).strip()
        # Strip a wrapping pair of quotes if the model added them
        if len(raw) >= 2 and raw[0] in "\"'" and raw[-1] == raw[0]:
            raw = raw[1:-1]
        for chunk in raw.split(","):
            cleaned = chunk.strip().strip(".").strip()
            if cleaned and len(cleaned) <= 60:
                gaps.append(cleaned)
            if len(gaps) >= 3:
                break
    return score, reason, gaps


def execute_auto_fit(
    job: DiscoveredJob,
    company_name: str,
    provider: AIProviderConfig,
    runtime_credential: str = "",
    profile: UserProfile | None = None,
    *,
    cap_context=None,
    receipt_emitter=None,
) -> AnalysisExecutionResult:
    brief = build_auto_fit_prompt(job, company_name, provider, profile)
    return _dispatch_provider(
        brief["prompt"],
        provider,
        runtime_credential,
        purpose="fit_score",
        cap_context=cap_context,
        receipt_emitter=receipt_emitter,
    )


def build_cv_tailoring_prompt(
    job: ImportedJob,
    provider: AIProviderConfig,
    profile: UserProfile | None = None,
    friction_keywords: list[str] | None = None,
) -> dict[str, str]:
    """Build a prompt that rewrites the candidate's CV for a specific job.

    ``friction_keywords`` (added 2026-05-19) — optional list of
    persona-specific bureaucratic / career-context vocabulary the
    candidate's situation involves (e.g., ``["§16d", "Anerkennung",
    "BIBB"]`` for an Anerkennung-track healthcare candidate; ``["TVöD",
    "Civic Tech"]`` for a public-sector tech career-changer). When
    supplied, the prompt asks the model to surface these terms in the
    tailored CV so the candidate's friction situation reads as
    authentic. Default ``None`` preserves backward compatibility — the
    friction-context instruction itself is always present, listing
    common friction categories as examples.

    This is the production-prompt remediation of the R12-polish bias-
    testing finding: criterion (d) friction-context-keyword check
    failed 27/70 because the prompt did not ask the model to
    acknowledge the candidate's friction situation. See
    ``docs/grant/bias-testing-2026-05-18-polish.md`` §"CV-tailoring
    results" for the source finding.
    """

    persona_label, profile_block = _candidate_profile_block(profile)
    friction_vocab_line = ""
    if friction_keywords:
        seen: set[str] = set()
        unique_kw: list[str] = []
        for kw in friction_keywords:
            norm = (kw or "").strip()
            if norm and norm not in seen:
                seen.add(norm)
                unique_kw.append(norm)
        if unique_kw:
            friction_vocab_line = (
                "\nThe candidate's documented friction-context vocabulary "
                "includes: " + ", ".join(unique_kw) + ". Use these terms "
                "verbatim where they fit the role's documented requirements."
            )

    prompt = f"""You are tailoring a resume / CV for a specific job opening on behalf of a {persona_label} candidate.

Goal: rewrite the candidate's CV so that it foregrounds the experience and
language the hiring team will respond to, *without inventing facts*. If the
candidate's CV doesn't actually contain a piece of evidence the job asks for,
say so in the editing notes — don't fabricate it.

Friction-context acknowledgment (NON-NEGOTIABLE when profile carries friction):
If the candidate profile includes `residency_status` OR `friction_notes` —
that is, the candidate has documented bureaucratic / career-context friction
— the tailored CV MUST include at least one explicit reference to the
friction context. Place the reference EITHER as a Summary-line acknowledgment
("Currently in §16d Anerkennungsverfahren, expected recognition in Q3"),
OR as a context line in the relevant Experience block, OR as a Languages /
Status sub-section. This applies REGARDLESS of how strong the candidate's
skills / role match is — a confident skills+role match does NOT excuse
omitting friction. Omitting friction when it's documented produces a CV
that does not read as authentic to the candidate's situation, and it
hides exactly the information a friction-aware employer is looking for.

Common friction categories to surface: visa or residency status (§16d,
§24, Blue Card, EU citizenship, Freizügigkeit); recognition pathway
(Anerkennung, Anabin, BIBB); career-shift context (Wiedereinstieg,
civic-tech career change, Familienpause); employment framework (TVöD,
Ausbildung, Bewerbungsmappe); language proficiency level. Use the
candidate's own friction vocabulary so the surfaced context reads as
authentic, not generic.{friction_vocab_line}

Forbidden filler phrases (case-insensitive — do NOT use these tired
generic-application markers anywhere in the CV body or notes): "Hiermit
bewerbe ich mich", "I am writing to express my interest", "I would like
to apply for the position", "In conclusion", "Overall, this is", "It is
important to note that", "Here are some key points", "I would recommend".
These are signals of an untailored output; the candidate's CV should
read as specific to the role, not generic.

Candidate profile (target persona, current CV, and notes):
{profile_block}

Target job:
- Company: {job.company_name}
- Title: {job.title}
- Location: {job.location or "Unknown"}
- URL: {job.source_url}

Job description:
{job.description or "No full description was extracted. Stay close to what the candidate's existing CV supports."}

Return exactly these sections, in this order, in plain text (no markdown):

1. Tailored CV — the full rewritten CV the candidate can paste into a
   document. Same broad sections as a normal CV (Summary, Experience,
   Skills, Education, Languages). Use bullet points where the original
   CV did. Match the language of the job description (German if the
   description is in German, otherwise English).
2. Diff vs. original — 3-6 short bullets describing what you changed and
   why (e.g. "Moved 'process redesign' bullet to top of role X because
   the JD opens with process improvement").
3. Missing evidence — bullets calling out claims the JD asks for that
   the candidate's CV does NOT support. Be honest.
4. Suggested follow-up edits — short bullets the candidate should do
   themselves before sending (e.g. add metric for X, ask manager for
   confirmation of Y).
"""
    return {
        "title": f"Tailored CV: {job.title}",
        "providerId": provider.provider_id,
        "providerLabel": provider.provider_id.replace("_", " ").title(),
        "invocationMode": provider.invocation_mode,
        "prompt": prompt,
        "handoffInstruction": "CV tailoring needs the candidate's actual CV in the profile. If profile.cv_text is empty, the model will produce generic output.",
    }


def execute_cv_tailoring(
    job: ImportedJob,
    provider: AIProviderConfig,
    runtime_credential: str = "",
    profile: UserProfile | None = None,
    friction_keywords: list[str] | None = None,
    *,
    cap_context=None,
    receipt_emitter=None,
) -> AnalysisExecutionResult:
    brief = build_cv_tailoring_prompt(job, provider, profile, friction_keywords=friction_keywords)
    return _dispatch_provider(
        brief["prompt"],
        provider,
        runtime_credential,
        purpose="tailor_cv",
        cap_context=cap_context,
        receipt_emitter=receipt_emitter,
    )


def execute_job_decision_brief(
    job: ImportedJob,
    provider: AIProviderConfig,
    runtime_credential: str = "",
    profile: UserProfile | None = None,
    *,
    cap_context=None,
    receipt_emitter=None,
) -> AnalysisExecutionResult:
    brief = build_job_decision_brief_prompt(job, provider, profile)
    return _dispatch_provider(
        brief["prompt"],
        provider,
        runtime_credential,
        purpose="job_decision_brief",
        cap_context=cap_context,
        receipt_emitter=receipt_emitter,
    )


def execute_cover_letter_brief(
    job: ImportedJob,
    provider: AIProviderConfig,
    runtime_credential: str = "",
    profile: UserProfile | None = None,
    *,
    cap_context=None,
    receipt_emitter=None,
) -> AnalysisExecutionResult:
    brief = build_cover_letter_brief_prompt(job, provider, profile)
    return _dispatch_provider(
        brief["prompt"],
        provider,
        runtime_credential,
        purpose="cover_letter",
        cap_context=cap_context,
        receipt_emitter=receipt_emitter,
    )


def _dispatch_provider(
    prompt: str,
    provider: AIProviderConfig,
    runtime_credential: str,
    *,
    purpose: str = "unknown",
    cap_context=None,
    receipt_emitter=None,
) -> AnalysisExecutionResult:
    """Dispatch the prompt to the configured AI provider and emit an
    AI Act Article 12 audit-log ``ai_invocation`` event around the call.

    ``purpose`` identifies which analysis call invoked the dispatch
    (e.g. ``"fit_score"``, ``"cover_letter"``, ``"tailor_cv"``,
    ``"motivation_letter"``, ``"skill_gap_brief"``). It feeds the
    audit log's ``prompt_template_id`` field and the cost-saving
    measurement queries.

    Existing callers that omit ``purpose`` log as ``"unknown"``; new
    callers should pass an explicit value.

    Phase 2 #46 root-cause refactor (2026-05-21): ``cap_context`` is
    the single per-user cost-cap gate. When set to a
    :class:`company_discovery.cost_caps.CostCapContext`, this
    function will (a) call ``enforce_cap`` before the AI invocation
    — raising :class:`CostCapExceeded` if the user is over budget —
    and (b) call ``record_invocation`` after the call so the next
    cap check sees this run's cost. ``None`` means "no cap" (only
    legitimate for system-internal calls that aren't user-
    attributable). Every user-initiated dispatch site MUST pass a
    context; un-gated user calls are a security bug.
    """
    from company_discovery.cost_caps import (
        CostCapContext,
        enforce_cap,
        record_invocation,
    )

    if cap_context is not None:
        if not isinstance(cap_context, CostCapContext):
            raise TypeError(
                f"cap_context must be a CostCapContext, got {type(cap_context).__name__}"
            )
        # enforce_cap raises CostCapExceeded if over budget. We let
        # it propagate so the caller can render a friendly UX
        # surface. We log an analytics event for the refusal here
        # so ops + the user's own activity log carry visibility
        # — without it, refused calls would be invisible.
        from company_discovery.cost_caps import CostCapExceeded as _CCE
        from company_discovery.models import AnalyticsEvent as _AE

        try:
            enforce_cap(
                user_id=cap_context.user_id,
                repository=cap_context.repository,
                cap_eur=cap_context.cap_eur,
                provider_id=provider.provider_id,
                invocation_mode=provider.invocation_mode,
                prompt_text=prompt,
                locale=cap_context.locale,
            )
        except _CCE as cap_err:
            try:
                cap_context.repository.save_analytics_event(
                    _AE(
                        user_id=cap_context.user_id,
                        kind="ai_invocation_refused_cap",
                        payload={
                            "purpose": purpose,
                            "provider_id": provider.provider_id,
                            "cap_eur": cap_err.cap_eur,
                            "spent_eur": cap_err.spent_eur,
                            "next_call_eur": cap_err.next_call_eur,
                        },
                    )
                )
            except Exception:  # noqa: BLE001 - Case E best-effort: refusal log failure must not break the refusal itself
                pass
            raise

    started = time.monotonic()
    result: AnalysisExecutionResult | None = None
    error_class: str | None = None
    try:
        result = _dispatch_provider_impl(prompt, provider, runtime_credential)
        return result
    except BaseException as exc:
        error_class = type(exc).__name__
        raise
    finally:
        _emit_dispatch_audit(
            prompt=prompt,
            provider=provider,
            purpose=purpose,
            started=started,
            result=result,
            error_class=error_class,
        )
        # Post-call cost recording — runs even on dispatch failure
        # so a partial response is still accounted for. Case E best-
        # effort: a failed write must not break the AI call.
        if cap_context is not None:
            try:
                response_text = (result.output if result else "") or ""
                record_invocation(
                    user_id=cap_context.user_id,
                    repository=cap_context.repository,
                    provider_id=provider.provider_id,
                    invocation_mode=provider.invocation_mode,
                    prompt_text=prompt,
                    response_text=response_text,
                )
            except Exception:  # noqa: BLE001 - Case E best-effort
                pass
        # Post-call Trust Receipt emission (Invariant 2). The receipt
        # is emitted only on completed dispatches with output —
        # there's nothing to attest to on a failed call. Case E
        # best-effort: receipt-emit failure must NEVER break the
        # AI call, even though it's the user's evidence packet.
        # A failed receipt leaves the audit log + result intact.
        if receipt_emitter is not None and result is not None and result.output:
            try:
                receipt_emitter(
                    purpose=purpose,
                    prompt_text=prompt,
                    response_text=result.output or "",
                    provider_id=result.provider_id or provider.provider_id,
                )
            except Exception:  # noqa: BLE001 - Case E best-effort
                pass


def _emit_dispatch_audit(
    *,
    prompt: str,
    provider: AIProviderConfig,
    purpose: str,
    started: float,
    result: AnalysisExecutionResult | None,
    error_class: str | None,
) -> None:
    """Compose and emit the ``ai_invocation`` audit-log event for a
    completed (or failed) :func:`_dispatch_provider` call. Never raises."""
    duration_ms = int((time.monotonic() - started) * 1000)
    try:
        emitter = audit_log.default_emitter()
    except Exception:  # noqa: BLE001 - emitter init can fail many ways; failure must skip audit, never break the AI call
        return
    try:
        if result is None:
            outcome = "error"
            ai_provider = (provider.provider_id if provider else "unknown") or "unknown"
            err_label = error_class or "Unknown"
            response_hash = None
        else:
            if result.status == "handoff_required":
                outcome = "declined"
            elif result.error:
                outcome = "error"
            else:
                outcome = "ok"
            ai_provider = result.provider_id or (provider.provider_id if provider else "unknown")
            err_label = None if outcome == "ok" else (result.status or error_class)
            response_hash = emitter.short_hash(result.output) if result.output else None
        prompt_template_id = emitter.short_hash(f"purpose:{purpose}") if purpose else None
        prompt_hash = emitter.short_hash(prompt)
        audit_log.emit_ai_invocation(
            purpose=purpose,
            ai_provider=ai_provider or "unknown",
            prompt_template_id=prompt_template_id[:8] if prompt_template_id else None,
            duration_ms=duration_ms,
            outcome=outcome,
            prompt_hash=prompt_hash,
            response_hash=response_hash,
            error_class=err_label,
            emitter=emitter,
        )
    except Exception:  # noqa: BLE001, S110 - audit logging is best-effort; failures surface via the emitter's own stderr channel, not by failing the AI call
        # Audit logging never breaks the AI call. Failures surface via
        # the emitter's own stderr warning channel.
        pass


def _dispatch_provider_impl(
    prompt: str,
    provider: AIProviderConfig,
    runtime_credential: str,
) -> AnalysisExecutionResult:
    if provider.invocation_mode == "manual" or provider.provider_id == "manual":
        return AnalysisExecutionResult(
            status="handoff_required",
            provider_id=provider.provider_id,
            invocation_mode=provider.invocation_mode,
            prompt=prompt,
            error="No AI execution provider selected.",
        )
    # Managed AI (#26): rebind to the operator's upstream provider +
    # key before the actual dispatch. Operator config:
    #   HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER  e.g. "openai" (default)
    #   HELPMEFINDTHEJOB_MANAGED_AI_KEY       the operator's API key
    #   (legacy DIRECTJOB_MANAGED_AI_* still accepted with DeprecationWarning
    #   via the env_compat shim)
    #   DIRECTJOB_MANAGED_AI_MODEL     optional; falls back to a sane default
    #   DIRECTJOB_MANAGED_AI_BASE_URL  optional; for OpenAI-compatible gateways
    if provider.provider_id == "managed":
        upstream = (
            (
                get_env("HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER", "DIRECTJOB_MANAGED_AI_PROVIDER")
                or "openai"
            )
            .strip()
            .lower()
        )
        if upstream not in {"openai", "anthropic", "google_gemini", "deepseek", "openrouter"}:
            return AnalysisExecutionResult(
                status="configuration_error",
                provider_id="managed",
                invocation_mode=provider.invocation_mode,
                prompt=prompt,
                error="HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER must be one of: openai, anthropic, google_gemini, deepseek, openrouter.",
            )
        if not (
            get_env("HELPMEFINDTHEJOB_MANAGED_AI_KEY", "DIRECTJOB_MANAGED_AI_KEY") or ""
        ).strip():
            return AnalysisExecutionResult(
                status="configuration_error",
                provider_id="managed",
                invocation_mode=provider.invocation_mode,
                prompt=prompt,
                error="Managed AI is enabled in the picker but HELPMEFINDTHEJOB_MANAGED_AI_KEY is not set on the server.",
            )
        provider = AIProviderConfig(
            provider_id=upstream,
            invocation_mode="api",
            model=(
                get_env("HELPMEFINDTHEJOB_MANAGED_AI_MODEL", "DIRECTJOB_MANAGED_AI_MODEL")
                or provider.model
                or ""
            ).strip(),
            credential_reference="HELPMEFINDTHEJOB_MANAGED_AI_KEY",
            base_url=(
                get_env("HELPMEFINDTHEJOB_MANAGED_AI_BASE_URL", "DIRECTJOB_MANAGED_AI_BASE_URL")
                or ""
            ).strip(),
            command="",
            notes="managed",
        )
    if provider.invocation_mode == "local_http" and provider.provider_id == "ollama":
        return _execute_ollama(prompt, provider)
    if provider.invocation_mode == "api" and provider.provider_id in {
        "openai",
        "deepseek",
        "openrouter",
        "custom",
    }:
        return _execute_openai_compatible(prompt, provider, runtime_credential)
    if provider.invocation_mode == "api" and provider.provider_id == "google_gemini":
        return _execute_google_gemini(prompt, provider, runtime_credential)
    if provider.invocation_mode == "cli" and provider.provider_id in {
        "codex_cli",
        "claude_code",
        "anthropic",
        "custom",
    }:
        return _execute_cli(prompt, provider)
    return AnalysisExecutionResult(
        status="unsupported",
        provider_id=provider.provider_id,
        invocation_mode=provider.invocation_mode,
        prompt=prompt,
        error="No direct adapter is available for this provider/mode yet. Use the handoff prompt.",
    )


def _resolve_api_key(provider: AIProviderConfig, runtime_credential: str) -> tuple[str, str]:
    runtime_key = runtime_credential.strip()
    if runtime_key:
        return runtime_key, "session"
    key_name = provider.credential_reference.strip()
    if not key_name:
        return "", "missing"
    return os.environ.get(key_name, ""), key_name


def _credential_error(
    provider: AIProviderConfig, prompt: str, source: str
) -> AnalysisExecutionResult:
    if source == "missing":
        message = "Missing API key. Enter a session-only key or configure an environment variable reference."
    else:
        message = (
            f"Environment variable {source} is not set and no session-only API key was provided."
        )
    return AnalysisExecutionResult(
        "configuration_error",
        provider.provider_id,
        provider.invocation_mode,
        prompt=prompt,
        error=message,
    )


def _execute_openai_compatible(
    prompt: str,
    provider: AIProviderConfig,
    runtime_credential: str = "",
) -> AnalysisExecutionResult:
    api_key, credential_source = _resolve_api_key(provider, runtime_credential)
    if not api_key:
        return _credential_error(provider, prompt, credential_source)

    default_base_urls = {
        "openai": "https://api.openai.com/v1",
        "deepseek": "https://api.deepseek.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
    }
    base_url = (provider.base_url or default_base_urls.get(provider.provider_id) or "").rstrip("/")
    if not base_url.startswith("https://") and provider.provider_id != "custom":
        return AnalysisExecutionResult(
            "configuration_error",
            provider.provider_id,
            provider.invocation_mode,
            prompt=prompt,
            error="Provider base URL must use HTTPS.",
        )

    payload = {
        "model": provider.model or "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    request = Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return AnalysisExecutionResult(
            "provider_error",
            provider.provider_id,
            provider.invocation_mode,
            prompt=prompt,
            error=f"Provider HTTP {error.code}",
        )
    except (OSError, URLError, json.JSONDecodeError) as error:
        return AnalysisExecutionResult(
            "provider_error",
            provider.provider_id,
            provider.invocation_mode,
            prompt=prompt,
            error=str(error),
        )

    output = ""
    choices = body.get("choices") or []
    if choices:
        output = choices[0].get("message", {}).get("content", "") or choices[0].get("text", "")
    return AnalysisExecutionResult(
        "completed" if output else "provider_error",
        provider.provider_id,
        provider.invocation_mode,
        output=output,
        prompt=prompt,
        error="" if output else "Provider returned no text.",
    )


def _execute_google_gemini(
    prompt: str,
    provider: AIProviderConfig,
    runtime_credential: str = "",
) -> AnalysisExecutionResult:
    api_key, credential_source = _resolve_api_key(provider, runtime_credential)
    if not api_key:
        return _credential_error(provider, prompt, credential_source)
    model = provider.model or "gemini-1.5-flash"
    base_url = (provider.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }
    request = Request(
        f"{base_url}/models/{model}:generateContent?key={api_key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return AnalysisExecutionResult(
            "provider_error",
            provider.provider_id,
            provider.invocation_mode,
            prompt=prompt,
            error=f"Provider HTTP {error.code}",
        )
    except (OSError, URLError, json.JSONDecodeError) as error:
        return AnalysisExecutionResult(
            "provider_error",
            provider.provider_id,
            provider.invocation_mode,
            prompt=prompt,
            error=str(error),
        )

    candidates = body.get("candidates") or []
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    output = "\n".join(part.get("text", "") for part in parts if part.get("text"))
    return AnalysisExecutionResult(
        "completed" if output else "provider_error",
        provider.provider_id,
        provider.invocation_mode,
        output=output,
        prompt=prompt,
        error="" if output else "Gemini returned no text.",
    )


def _dispatch_provider_streaming(
    prompt: str,
    provider: AIProviderConfig,
    runtime_credential: str,
    *,
    purpose: str = "unknown",
    cap_context=None,
    receipt_emitter=None,
):
    """Streaming counterpart to :func:`_dispatch_provider`.

    Generator: yields ``("token", str)`` events as token chunks arrive,
    then a final ``("final", AnalysisExecutionResult)`` event with
    accumulated output + status. Mirrors the audit-log emission shape
    of :func:`_dispatch_provider` — one ``ai_invocation`` event fires
    after the stream completes (success or failure).

    Phase 2 #46 root-cause refactor (2026-05-21): when ``cap_context``
    is set, this generator calls ``enforce_cap`` BEFORE opening the
    streaming connection (refusing up front is cheaper than aborting
    mid-stream) and ``record_invocation`` AFTER the stream completes.
    ``None`` means "no cap" — only legitimate for system-internal
    calls.

    Per-provider streaming support:
    - ``ollama`` (local_http): NDJSON streaming via /api/generate with
      ``stream: true``. Each line is ``{"response": "<token>",
      "done": bool}``.
    - ``openai`` / ``deepseek`` / ``openrouter`` / ``custom`` (api): SSE
      streaming via /v1/chat/completions with ``stream: true``. Each
      ``data:`` line is a ChatCompletion chunk; ``[DONE]`` terminates.
    - ``google_gemini`` (api): NDJSON-style streamGenerateContent
      endpoint. Each chunk is a partial GenerateContentResponse.
    - CLI providers (``codex_cli`` / ``claude_code`` / ``anthropic`` via
      CLI / ``custom`` via CLI): the underlying CLI is single-shot —
      we wrap the result as a one-event ``("final", ...)`` yield. The
      caller still benefits from the unified streaming interface but
      doesn't see per-token narration until the CLI itself supports
      streaming (Phase 2 follow-on).
    - ``manual`` / ``managed`` (manual): handoff or single-event final.
    """
    import time as _time

    from company_discovery.cost_caps import (
        CostCapContext,
        enforce_cap,
        record_invocation,
    )

    if cap_context is not None:
        if not isinstance(cap_context, CostCapContext):
            raise TypeError(
                f"cap_context must be a CostCapContext, got {type(cap_context).__name__}"
            )
        # Pre-flight cap check. Raises CostCapExceeded if over budget;
        # generator caller catches and yields a friendly done_payload.
        # Refusal is logged via ai_invocation_refused_cap analytics
        # event for ops + user visibility (same shape as the non-
        # streaming chokepoint).
        from company_discovery.cost_caps import CostCapExceeded as _CCE
        from company_discovery.models import AnalyticsEvent as _AE

        try:
            enforce_cap(
                user_id=cap_context.user_id,
                repository=cap_context.repository,
                cap_eur=cap_context.cap_eur,
                provider_id=provider.provider_id,
                invocation_mode=provider.invocation_mode,
                prompt_text=prompt,
                locale=cap_context.locale,
            )
        except _CCE as cap_err:
            try:
                cap_context.repository.save_analytics_event(
                    _AE(
                        user_id=cap_context.user_id,
                        kind="ai_invocation_refused_cap",
                        payload={
                            "purpose": purpose,
                            "provider_id": provider.provider_id,
                            "cap_eur": cap_err.cap_eur,
                            "spent_eur": cap_err.spent_eur,
                            "next_call_eur": cap_err.next_call_eur,
                            "streaming": True,
                        },
                    )
                )
            except Exception:  # noqa: BLE001 - Case E best-effort
                pass
            raise

    started = _time.monotonic()
    final_result: AnalysisExecutionResult | None = None
    error_class: str | None = None
    try:
        for event in _dispatch_provider_streaming_impl(
            prompt, provider, runtime_credential
        ):
            yield event
            if isinstance(event, tuple) and event[0] == "final":
                final_result = event[1]
                break
    except BaseException as exc:
        error_class = type(exc).__name__
        raise
    finally:
        _emit_dispatch_audit(
            prompt=prompt,
            provider=provider,
            purpose=purpose,
            started=started,
            result=final_result,
            error_class=error_class,
        )
        if cap_context is not None:
            try:
                response_text = (final_result.output if final_result else "") or ""
                record_invocation(
                    user_id=cap_context.user_id,
                    repository=cap_context.repository,
                    provider_id=provider.provider_id,
                    invocation_mode=provider.invocation_mode,
                    prompt_text=prompt,
                    response_text=response_text,
                )
            except Exception:  # noqa: BLE001 - Case E best-effort
                pass
        # Trust Receipt emission for streaming dispatches — same
        # contract as the single-shot path. Only fires on a
        # completed stream with non-empty output.
        if (
            receipt_emitter is not None
            and final_result is not None
            and final_result.output
        ):
            try:
                receipt_emitter(
                    purpose=purpose,
                    prompt_text=prompt,
                    response_text=final_result.output or "",
                    provider_id=final_result.provider_id or provider.provider_id,
                )
            except Exception:  # noqa: BLE001 - Case E best-effort
                pass


def _dispatch_provider_streaming_impl(
    prompt: str,
    provider: AIProviderConfig,
    runtime_credential: str,
):
    """Route to the per-provider streaming function. Mirrors the
    invocation-mode dispatch in :func:`_dispatch_provider_impl`.
    Yields ``("token", str)`` events then a final ``("final",
    AnalysisExecutionResult)`` event."""

    if provider.invocation_mode == "manual" or provider.provider_id == "manual":
        yield (
            "final",
            AnalysisExecutionResult(
                status="handoff_required",
                provider_id=provider.provider_id,
                invocation_mode=provider.invocation_mode,
                prompt=prompt,
                error="No AI execution provider selected.",
            ),
        )
        return
    # Managed AI: rebind to the operator's upstream provider before
    # the streaming dispatch (parity with _dispatch_provider_impl).
    if provider.provider_id == "managed":
        upstream = (
            (
                get_env("HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER", "DIRECTJOB_MANAGED_AI_PROVIDER")
                or "openai"
            )
            .strip()
            .lower()
        )
        if upstream not in {"openai", "anthropic", "google_gemini", "deepseek", "openrouter"}:
            yield (
                "final",
                AnalysisExecutionResult(
                    status="configuration_error",
                    provider_id="managed",
                    invocation_mode=provider.invocation_mode,
                    prompt=prompt,
                    error="HELPMEFINDTHEJOB_MANAGED_AI_PROVIDER must be one of: openai, anthropic, google_gemini, deepseek, openrouter.",
                ),
            )
            return
        if not (
            get_env("HELPMEFINDTHEJOB_MANAGED_AI_KEY", "DIRECTJOB_MANAGED_AI_KEY") or ""
        ).strip():
            yield (
                "final",
                AnalysisExecutionResult(
                    status="configuration_error",
                    provider_id="managed",
                    invocation_mode=provider.invocation_mode,
                    prompt=prompt,
                    error="Managed AI is enabled in the picker but HELPMEFINDTHEJOB_MANAGED_AI_KEY is not set on the server.",
                ),
            )
            return
        provider = AIProviderConfig(
            provider_id=upstream,
            invocation_mode="api",
            model=(
                get_env("HELPMEFINDTHEJOB_MANAGED_AI_MODEL", "DIRECTJOB_MANAGED_AI_MODEL")
                or provider.model
                or ""
            ).strip(),
            credential_reference="HELPMEFINDTHEJOB_MANAGED_AI_KEY",
            base_url=(
                get_env("HELPMEFINDTHEJOB_MANAGED_AI_BASE_URL", "DIRECTJOB_MANAGED_AI_BASE_URL")
                or ""
            ).strip(),
            command="",
            notes="managed",
        )
    if provider.invocation_mode == "local_http" and provider.provider_id == "ollama":
        yield from _execute_ollama_streaming(prompt, provider)
        return
    if provider.invocation_mode == "api" and provider.provider_id in {
        "openai",
        "deepseek",
        "openrouter",
        "custom",
    }:
        yield from _execute_openai_compatible_streaming(prompt, provider, runtime_credential)
        return
    if provider.invocation_mode == "api" and provider.provider_id == "google_gemini":
        yield from _execute_google_gemini_streaming(prompt, provider, runtime_credential)
        return
    if provider.invocation_mode == "cli" and provider.provider_id in {
        "codex_cli",
        "claude_code",
        "anthropic",
        "custom",
    }:
        # CLI providers are single-shot today. Wrap the result as a
        # one-event "final" yield so the consumer sees the unified
        # streaming contract. Per-token CLI streaming is a Phase 2
        # follow-on (depends on the upstream CLI supporting it).
        result = _execute_cli(prompt, provider)
        yield ("final", result)
        return
    yield (
        "final",
        AnalysisExecutionResult(
            status="unsupported",
            provider_id=provider.provider_id,
            invocation_mode=provider.invocation_mode,
            prompt=prompt,
            error="No direct adapter is available for this provider/mode yet. Use the handoff prompt.",
        ),
    )


def _execute_ollama_streaming(prompt: str, provider: AIProviderConfig):
    """Stream tokens from a local Ollama via /api/generate with
    ``stream: true``. Yields ``("token", str)`` per response chunk
    and a final ``("final", AnalysisExecutionResult)`` carrying the
    accumulated output."""

    base_url = (provider.base_url or "http://127.0.0.1:11434").rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        yield (
            "final",
            AnalysisExecutionResult(
                "configuration_error",
                provider.provider_id,
                provider.invocation_mode,
                prompt=prompt,
                error="Ollama execution is limited to local http://127.0.0.1 or localhost.",
            ),
        )
        return
    payload = {"model": provider.model or "llama3.1", "prompt": prompt, "stream": True}
    request = Request(
        f"{base_url}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    accumulated: list[str] = []
    try:
        with urlopen(request, timeout=300) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                token = chunk.get("response", "")
                if token:
                    accumulated.append(token)
                    yield ("token", token)
                if chunk.get("done"):
                    break
    except (HTTPError, OSError, URLError) as error:
        yield (
            "final",
            AnalysisExecutionResult(
                "provider_error",
                provider.provider_id,
                provider.invocation_mode,
                output="".join(accumulated),
                prompt=prompt,
                error=str(error),
            ),
        )
        return
    output = "".join(accumulated)
    yield (
        "final",
        AnalysisExecutionResult(
            "completed" if output else "provider_error",
            provider.provider_id,
            provider.invocation_mode,
            output=output,
            prompt=prompt,
            error="" if output else "Ollama returned no text.",
        ),
    )


def _execute_openai_compatible_streaming(
    prompt: str, provider: AIProviderConfig, runtime_credential: str
):
    """Stream tokens from an OpenAI-compatible chat-completions endpoint
    (OpenAI, DeepSeek, OpenRouter, custom) via SSE with ``stream: true``.
    Each ``data:`` line carries a ChatCompletion chunk;  ``[DONE]``
    terminates."""

    api_key, _key_source = _resolve_api_key(provider, runtime_credential)
    if not api_key:
        yield (
            "final",
            AnalysisExecutionResult(
                "configuration_error",
                provider.provider_id,
                provider.invocation_mode,
                prompt=prompt,
                error="API key not provided. Set the env var or pass a session key.",
            ),
        )
        return
    base_url = (provider.base_url or "https://api.openai.com/v1").rstrip("/")
    body = {
        "model": provider.model or "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    request = Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    accumulated: list[str] = []
    try:
        with urlopen(request, timeout=300) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").rstrip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                try:
                    token = chunk["choices"][0]["delta"].get("content", "") or ""
                except (KeyError, IndexError, TypeError):
                    token = ""
                if token:
                    accumulated.append(token)
                    yield ("token", token)
    except (HTTPError, OSError, URLError) as error:
        yield (
            "final",
            AnalysisExecutionResult(
                "provider_error",
                provider.provider_id,
                provider.invocation_mode,
                output="".join(accumulated),
                prompt=prompt,
                error=str(error),
            ),
        )
        return
    output = "".join(accumulated)
    yield (
        "final",
        AnalysisExecutionResult(
            "completed" if output else "provider_error",
            provider.provider_id,
            provider.invocation_mode,
            output=output,
            prompt=prompt,
            error="" if output else "OpenAI-compatible stream returned no text.",
        ),
    )


def _execute_google_gemini_streaming(
    prompt: str, provider: AIProviderConfig, runtime_credential: str
):
    """Stream tokens from Google Gemini's streamGenerateContent endpoint.
    The response is a JSON array streamed as it's generated; each
    element is a partial GenerateContentResponse."""

    api_key, _key_source = _resolve_api_key(provider, runtime_credential)
    if not api_key:
        yield (
            "final",
            AnalysisExecutionResult(
                "configuration_error",
                provider.provider_id,
                provider.invocation_mode,
                prompt=prompt,
                error="API key not provided. Set GEMINI_API_KEY or pass a session key.",
            ),
        )
        return
    model = provider.model or "gemini-1.5-flash"
    base_url = (
        provider.base_url
        or "https://generativelanguage.googleapis.com/v1beta"
    ).rstrip("/")
    url = (
        f"{base_url}/models/{model}:streamGenerateContent"
        f"?alt=sse&key={api_key}"
    )
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    accumulated: list[str] = []
    try:
        with urlopen(request, timeout=300) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").rstrip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if not data_str or data_str == "[DONE]":
                    continue
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                try:
                    parts = chunk["candidates"][0]["content"]["parts"]
                    token = "".join(p.get("text", "") for p in parts)
                except (KeyError, IndexError, TypeError):
                    token = ""
                if token:
                    accumulated.append(token)
                    yield ("token", token)
    except (HTTPError, OSError, URLError) as error:
        yield (
            "final",
            AnalysisExecutionResult(
                "provider_error",
                provider.provider_id,
                provider.invocation_mode,
                output="".join(accumulated),
                prompt=prompt,
                error=str(error),
            ),
        )
        return
    output = "".join(accumulated)
    yield (
        "final",
        AnalysisExecutionResult(
            "completed" if output else "provider_error",
            provider.provider_id,
            provider.invocation_mode,
            output=output,
            prompt=prompt,
            error="" if output else "Gemini stream returned no text.",
        ),
    )


def _execute_ollama(prompt: str, provider: AIProviderConfig) -> AnalysisExecutionResult:
    base_url = (provider.base_url or "http://127.0.0.1:11434").rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        return AnalysisExecutionResult(
            "configuration_error",
            provider.provider_id,
            provider.invocation_mode,
            prompt=prompt,
            error="Ollama execution is limited to local http://127.0.0.1 or localhost.",
        )
    payload = {"model": provider.model or "llama3.1", "prompt": prompt, "stream": False}
    request = Request(
        f"{base_url}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (HTTPError, OSError, URLError, json.JSONDecodeError) as error:
        return AnalysisExecutionResult(
            "provider_error",
            provider.provider_id,
            provider.invocation_mode,
            prompt=prompt,
            error=str(error),
        )
    output = body.get("response", "")
    return AnalysisExecutionResult(
        "completed" if output else "provider_error",
        provider.provider_id,
        provider.invocation_mode,
        output=output,
        prompt=prompt,
        error="" if output else "Ollama returned no text.",
    )


def _execute_cli(prompt: str, provider: AIProviderConfig) -> AnalysisExecutionResult:
    command = provider.command.strip()
    if not command:
        return AnalysisExecutionResult(
            "configuration_error",
            provider.provider_id,
            provider.invocation_mode,
            prompt=prompt,
            error="Missing CLI command.",
        )
    parts = command.split()
    allowed = {
        "codex": "codex",
        "claude": "claude",
        "gemini": "gemini",
    }
    if parts[0] not in allowed:
        return AnalysisExecutionResult(
            "configuration_error",
            provider.provider_id,
            provider.invocation_mode,
            prompt=prompt,
            error="CLI command must start with an allowed local AI binary.",
        )
    try:
        completed = subprocess.run(
            parts,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return AnalysisExecutionResult(
            "provider_error",
            provider.provider_id,
            provider.invocation_mode,
            prompt=prompt,
            error=str(error),
        )
    if completed.returncode != 0:
        return AnalysisExecutionResult(
            "provider_error",
            provider.provider_id,
            provider.invocation_mode,
            prompt=prompt,
            error=completed.stderr[-1000:],
        )
    return AnalysisExecutionResult(
        "completed",
        provider.provider_id,
        provider.invocation_mode,
        output=completed.stdout,
        prompt=prompt,
    )
