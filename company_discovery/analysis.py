from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

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
    # R23.9 — token usage + resolved model name so the cost tracker
    # can record legacy AI calls (briefs, letters, CV consults) the
    # same way R22.6 records the tool-use chat. 0 + "" when the
    # provider didn't return usage (CLI / ollama / error path).
    input_tokens: int = 0
    output_tokens: int = 0
    model_used: str = ""


_HEALTHCARE_SECTION_LABEL = "Healthcare relevance"
_GENERIC_SECTION_LABEL = "Persona relevance"


def _candidate_profile_block(
    profile: UserProfile | None,
    persona_id_default: str = "healthcare-management",
) -> tuple[str, str]:
    """Return a ``(persona_label, profile_lines_block)`` tuple.

    ``profile_lines_block`` is the multi-line "Candidate target profile"
    section embedded in every prompt. It always falls back to a sensible
    persona-specific default so the brief stays useful even when the user
    has not filled in their profile yet.
    """

    persona_id = profile.persona_id if profile and profile.persona_id else persona_id_default
    persona = get_persona(persona_id)
    lines: list[str] = [f"- Persona: {persona.label} — {persona.description}"]

    target_roles = list(profile.target_roles) if profile and profile.target_roles else list(persona.default_target_roles)
    if target_roles:
        lines.append("- Target roles: " + ", ".join(target_roles))

    industry = (profile.industry if profile and profile.industry else persona.default_industry) or ""
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

    if profile and (profile.cv_text or "").strip():
        cv = profile.cv_text.strip()
        if len(cv) > 4000:
            cv = cv[:4000] + "\n…(CV truncated to 4000 characters)"
        lines.append("\nCandidate CV (free-text, possibly partial):\n" + cv)
    else:
        lines.append("- No CV uploaded yet — be cautious about claims of fit beyond what the role description supports.")

    return persona.label, "\n".join(lines)


def build_job_decision_brief_prompt(
    job: ImportedJob,
    provider: AIProviderConfig,
    profile: UserProfile | None = None,
) -> dict[str, str]:
    persona_label, profile_block = _candidate_profile_block(profile)
    provider_label = provider.provider_id.replace("_", " ").title()
    persona_id = profile.persona_id if profile and profile.persona_id else "healthcare-management"
    section_label = _HEALTHCARE_SECTION_LABEL if persona_id == "healthcare-management" else _GENERIC_SECTION_LABEL
    prompt = f"""You are helping evaluate a job opportunity for a {persona_label} candidate.

Create a concise Job Decision Brief for this role.

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
2. Fit score: 0-100
3. Why it fits
4. Risks and blockers
5. Seniority check
6. {section_label}
7. Likely keywords/tools
8. Application angle
9. Missing information to verify manually
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
   - Concrete experience and skills that map onto the role's needs
   - A short closing with a clear call to action
3. Editing notes for the candidate: 2-4 bullets calling out claims that need
   to be verified, sentences to personalize further, or weak spots to fix.
4. Draft assumptions: list any inference you made (language, seniority,
   missing CV details). Be honest if information is thin.
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
    """

    persona_label, profile_block = _candidate_profile_block(profile)
    prompt = f"""You are scoring a job posting for a {persona_label} candidate.

Output exactly three lines, no headers, no other text:
SCORE: <integer 0-100>
REASON: <one short sentence, max 25 words>
GAPS: <up to three short skill phrases, comma-separated, that the JD demands but the candidate's CV does not show. Use empty string when no clear gaps>

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


_QUERY_EXPANSION_FENCED_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.IGNORECASE | re.DOTALL)
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
        cleaned["target_roles"] = [str(r).strip() for r in (data.get("target_roles") or []) if str(r).strip()][:8]
        cleaned["industry"] = str(data.get("industry") or "").strip() or None
        cleaned["location"] = str(data.get("location") or "").strip() or None
        cleaned["keywords"] = [str(k).strip() for k in (data.get("keywords") or []) if str(k).strip()][:10]
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
    record_call=None,
) -> AnalysisExecutionResult:
    from company_discovery.model_router import TASK_KEYWORD_EXTRACTION
    brief = build_cv_query_expansion_prompt(profile, free_text, provider)
    return _dispatch_provider(brief["prompt"], provider, runtime_credential,
                                task=TASK_KEYWORD_EXTRACTION,
                                record_call=record_call)


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
        if len(raw) >= 2 and raw[0] in '"\'' and raw[-1] == raw[0]:
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
    record_call=None,
) -> AnalysisExecutionResult:
    from company_discovery.model_router import TASK_JOB_RANKING
    brief = build_auto_fit_prompt(job, company_name, provider, profile)
    return _dispatch_provider(brief["prompt"], provider, runtime_credential,
                                task=TASK_JOB_RANKING,
                                record_call=record_call)


def build_cv_tailoring_prompt(
    job: ImportedJob,
    provider: AIProviderConfig,
    profile: UserProfile | None = None,
) -> dict[str, str]:
    """Build a prompt that rewrites the candidate's CV for a specific job."""

    persona_label, profile_block = _candidate_profile_block(profile)
    prompt = f"""You are tailoring a resume / CV for a specific job opening on behalf of a {persona_label} candidate.

Goal: rewrite the candidate's CV so that it foregrounds the experience and
language the hiring team will respond to, *without inventing facts*. If the
candidate's CV doesn't actually contain a piece of evidence the job asks for,
say so in the editing notes — don't fabricate it.

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
    *,
    record_call=None,
) -> AnalysisExecutionResult:
    from company_discovery.model_router import TASK_CV_CONSULT
    brief = build_cv_tailoring_prompt(job, provider, profile)
    return _dispatch_provider(brief["prompt"], provider, runtime_credential,
                                task=TASK_CV_CONSULT,
                                record_call=record_call)


def execute_job_decision_brief(
    job: ImportedJob,
    provider: AIProviderConfig,
    runtime_credential: str = "",
    profile: UserProfile | None = None,
    *,
    record_call=None,
) -> AnalysisExecutionResult:
    from company_discovery.model_router import TASK_BRIEF
    brief = build_job_decision_brief_prompt(job, provider, profile)
    return _dispatch_provider(brief["prompt"], provider, runtime_credential,
                                task=TASK_BRIEF,
                                record_call=record_call)


def execute_cover_letter_brief(
    job: ImportedJob,
    provider: AIProviderConfig,
    runtime_credential: str = "",
    profile: UserProfile | None = None,
    *,
    record_call=None,
) -> AnalysisExecutionResult:
    from company_discovery.model_router import TASK_LETTER
    brief = build_cover_letter_brief_prompt(job, provider, profile)
    return _dispatch_provider(brief["prompt"], provider, runtime_credential,
                                task=TASK_LETTER,
                                record_call=record_call)


def _dispatch_provider(
    prompt: str,
    provider: AIProviderConfig,
    runtime_credential: str,
    *,
    task: str = "",
    record_call=None,
) -> AnalysisExecutionResult:
    """Run an LLM prompt against the configured provider.

    ``task`` (optional) is one of the constants in
    :mod:`company_discovery.model_router`. When set, the model is
    chosen via that router (cheap / medium / premium tier) unless
    the caller already pinned ``provider.model``. With no task,
    behavior matches the pre-R23.5 path — provider.model wins or a
    provider-specific default is used.
    """
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
    #   DIRECTJOB_MANAGED_AI_PROVIDER  e.g. "openai" (default)
    #   DIRECTJOB_MANAGED_AI_KEY       the operator's API key
    #   DIRECTJOB_MANAGED_AI_MODEL     optional; falls back to a sane default
    #   DIRECTJOB_MANAGED_AI_BASE_URL  optional; for OpenAI-compatible gateways
    if provider.provider_id == "managed":
        upstream = (os.environ.get("DIRECTJOB_MANAGED_AI_PROVIDER") or "openai").strip().lower()
        if upstream not in {"openai", "anthropic", "google_gemini", "deepseek", "openrouter"}:
            return AnalysisExecutionResult(
                status="configuration_error",
                provider_id="managed",
                invocation_mode=provider.invocation_mode,
                prompt=prompt,
                error="DIRECTJOB_MANAGED_AI_PROVIDER must be one of: openai, anthropic, google_gemini, deepseek, openrouter.",
            )
        if not (os.environ.get("DIRECTJOB_MANAGED_AI_KEY") or "").strip():
            return AnalysisExecutionResult(
                status="configuration_error",
                provider_id="managed",
                invocation_mode=provider.invocation_mode,
                prompt=prompt,
                error="Managed AI is enabled in the picker but DIRECTJOB_MANAGED_AI_KEY is not set on the server.",
            )
        # R23.5: if the caller named a task, the model router picks
        # the right tier (cheap/medium/premium); otherwise honour
        # the legacy single-model env. The router itself falls back
        # to DIRECTJOB_MANAGED_AI_MODEL when no per-tier override
        # is set, so existing deployments behave identically until
        # someone sets the per-tier env vars.
        from company_discovery.model_router import select_model
        legacy_model = (
            os.environ.get("DIRECTJOB_MANAGED_AI_MODEL")
            or provider.model
            or ""
        ).strip()
        chosen_model = select_model(
            upstream, task,
            explicit_model=legacy_model if not task else "",
        ) or legacy_model
        provider = AIProviderConfig(
            provider_id=upstream,
            invocation_mode="api",
            model=chosen_model,
            credential_reference="DIRECTJOB_MANAGED_AI_KEY",
            base_url=(os.environ.get("DIRECTJOB_MANAGED_AI_BASE_URL") or "").strip(),
            command="",
            notes="managed",
        )
    if provider.invocation_mode == "local_http" and provider.provider_id == "ollama":
        result = _execute_ollama(prompt, provider)
    elif provider.invocation_mode == "api" and provider.provider_id in {"openai", "deepseek", "openrouter", "custom"}:
        result = _execute_openai_compatible(prompt, provider, runtime_credential)
    elif provider.invocation_mode == "api" and provider.provider_id == "google_gemini":
        result = _execute_google_gemini(prompt, provider, runtime_credential)
    elif provider.invocation_mode == "cli" and provider.provider_id in {"codex_cli", "claude_code", "anthropic", "custom"}:
        result = _execute_cli(prompt, provider)
    else:
        return AnalysisExecutionResult(
            status="unsupported",
            provider_id=provider.provider_id,
            invocation_mode=provider.invocation_mode,
            prompt=prompt,
            error="No direct adapter is available for this provider/mode yet. Use the handoff prompt.",
        )
    # R23.9 / R24.0 — record the legacy AI call into the cost tracker
    # so the operator dashboard reflects briefs / letters / consults /
    # etc. Best-effort: log exceptions rather than swallow silently so
    # cost-tracker hiccups (disk full, schema migration, etc.) surface
    # in operator logs.
    #
    # We record EVERY completed call (not only status="completed") —
    # API errors that returned token counts (some providers charge for
    # input tokens even on 400/refusal) should be visible in the
    # dashboard. Calls with NO usage data (CLI mode, transport error)
    # naturally record 0 tokens.
    if record_call is not None and result.status != "configuration_error":
        try:
            record_call(provider.provider_id or "",
                          result.model_used or provider.model,
                          task or "legacy_ai",
                          result.input_tokens, result.output_tokens)
        except Exception as exc:  # noqa: BLE001
            import logging as _logging
            _logging.getLogger("directjob.cost").warning(
                "record_call failed in _dispatch_provider: %s", exc)
    return result


def _resolve_api_key(provider: AIProviderConfig, runtime_credential: str) -> tuple[str, str]:
    runtime_key = runtime_credential.strip()
    if runtime_key:
        return runtime_key, "session"
    key_name = provider.credential_reference.strip()
    if not key_name:
        return "", "missing"
    return os.environ.get(key_name, ""), key_name


def _credential_error(provider: AIProviderConfig, prompt: str, source: str) -> AnalysisExecutionResult:
    if source == "missing":
        message = "Missing API key. Enter a session-only key or configure an environment variable reference."
    else:
        message = f"Environment variable {source} is not set and no session-only API key was provided."
    return AnalysisExecutionResult("configuration_error", provider.provider_id, provider.invocation_mode, prompt=prompt, error=message)


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
        return AnalysisExecutionResult("configuration_error", provider.provider_id, provider.invocation_mode, prompt=prompt, error="Provider base URL must use HTTPS.")

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
        return AnalysisExecutionResult("provider_error", provider.provider_id, provider.invocation_mode, prompt=prompt, error=f"Provider HTTP {error.code}")
    except (OSError, URLError, json.JSONDecodeError) as error:
        return AnalysisExecutionResult("provider_error", provider.provider_id, provider.invocation_mode, prompt=prompt, error=str(error))

    output = ""
    choices = body.get("choices") or []
    if choices:
        output = choices[0].get("message", {}).get("content", "") or choices[0].get("text", "")
    # R23.9 — surface usage so _dispatch_provider can record cost.
    usage = body.get("usage") or {}
    return AnalysisExecutionResult(
        "completed" if output else "provider_error",
        provider.provider_id, provider.invocation_mode,
        output=output, prompt=prompt,
        error="" if output else "Provider returned no text.",
        input_tokens=int(usage.get("prompt_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or 0),
        model_used=payload["model"],
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
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}
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
        return AnalysisExecutionResult("provider_error", provider.provider_id, provider.invocation_mode, prompt=prompt, error=f"Provider HTTP {error.code}")
    except (OSError, URLError, json.JSONDecodeError) as error:
        return AnalysisExecutionResult("provider_error", provider.provider_id, provider.invocation_mode, prompt=prompt, error=str(error))

    candidates = body.get("candidates") or []
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    output = "\n".join(part.get("text", "") for part in parts if part.get("text"))
    # R23.9 — Gemini's usageMetadata block carries token counts.
    usage = body.get("usageMetadata") or {}
    return AnalysisExecutionResult(
        "completed" if output else "provider_error",
        provider.provider_id, provider.invocation_mode,
        output=output, prompt=prompt,
        error="" if output else "Gemini returned no text.",
        input_tokens=int(usage.get("promptTokenCount") or 0),
        output_tokens=int(usage.get("candidatesTokenCount") or 0),
        model_used=model,
    )


def _execute_ollama(prompt: str, provider: AIProviderConfig) -> AnalysisExecutionResult:
    base_url = (provider.base_url or "http://127.0.0.1:11434").rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        return AnalysisExecutionResult("configuration_error", provider.provider_id, provider.invocation_mode, prompt=prompt, error="Ollama execution is limited to local http://127.0.0.1 or localhost.")
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
        return AnalysisExecutionResult("provider_error", provider.provider_id, provider.invocation_mode, prompt=prompt, error=str(error))
    output = body.get("response", "")
    return AnalysisExecutionResult("completed" if output else "provider_error", provider.provider_id, provider.invocation_mode, output=output, prompt=prompt, error="" if output else "Ollama returned no text.")


def _execute_cli(prompt: str, provider: AIProviderConfig) -> AnalysisExecutionResult:
    command = provider.command.strip()
    if not command:
        return AnalysisExecutionResult("configuration_error", provider.provider_id, provider.invocation_mode, prompt=prompt, error="Missing CLI command.")
    parts = command.split()
    allowed = {
        "codex": "codex",
        "claude": "claude",
        "gemini": "gemini",
    }
    if parts[0] not in allowed:
        return AnalysisExecutionResult("configuration_error", provider.provider_id, provider.invocation_mode, prompt=prompt, error="CLI command must start with an allowed local AI binary.")
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
        return AnalysisExecutionResult("provider_error", provider.provider_id, provider.invocation_mode, prompt=prompt, error=str(error))
    if completed.returncode != 0:
        return AnalysisExecutionResult("provider_error", provider.provider_id, provider.invocation_mode, prompt=prompt, error=completed.stderr[-1000:])
    return AnalysisExecutionResult("completed", provider.provider_id, provider.invocation_mode, output=completed.stdout, prompt=prompt)
