"""Per-task model router (R23.5).

Picks the right model for each task type so the operator pays the
minimum LLM cost without compromising user-perceived quality. The
user never sees this layer — they just type into chat and the
right model gets the job.

Tiers
=====

CHEAP    routing / typo / intent classification / ranking
MEDIUM   the R22 tool-use chat, CV section formatting
PREMIUM  motivation letter, CV consult, job brief

Per-provider defaults
=====================

Anthropic:
  cheap   = claude-haiku-4-5
  medium  = claude-haiku-4-5
  premium = claude-sonnet-4-6

OpenAI:
  cheap   = gpt-4o-mini
  medium  = gpt-4o-mini
  premium = gpt-4o

DeepSeek:
  cheap   = deepseek-chat
  medium  = deepseek-chat
  premium = deepseek-reasoner

Google Gemini:
  cheap   = gemini-1.5-flash
  medium  = gemini-1.5-flash
  premium = gemini-1.5-pro

OpenRouter / custom:
  fall through — caller's explicit model wins.

Env overrides
=============

Operators can override any tier per provider via env, without code
changes:

  DIRECTJOB_MODEL_ANTHROPIC_CHEAP
  DIRECTJOB_MODEL_ANTHROPIC_MEDIUM
  DIRECTJOB_MODEL_ANTHROPIC_PREMIUM
  DIRECTJOB_MODEL_OPENAI_CHEAP
  ... etc

A legacy single-model env (DIRECTJOB_MANAGED_AI_MODEL) is honoured
only when there's no per-tier override and the caller didn't pass
an explicit model. This keeps existing deployments working.
"""

from __future__ import annotations

import os

# Task IDs. Use these constants at call sites so a future renaming
# can't silently break callers.
TASK_CHAT_ROUTING = "chat_routing"
TASK_TOOL_USE_CHAT = "tool_use_chat"
TASK_LETTER = "motivation_letter"
TASK_CV_CONSULT = "cv_consult"
TASK_CV_FORMAT = "cv_section_format"
TASK_BRIEF = "job_brief"
TASK_JOB_RANKING = "job_ranking"
TASK_KEYWORD_EXTRACTION = "keyword_extraction"
# R24.5 — extract a raw CV blob into the strict CvDocument schema.
# Structured-JSON output; a medium model is fine since the work is
# mechanical (read text, map to fields) rather than creative.
TASK_CV_EXTRACT = "cv_extract"

# Cost tiers.
TIER_CHEAP = "cheap"
TIER_MEDIUM = "medium"
TIER_PREMIUM = "premium"

# Task → tier mapping. Keep this as the SINGLE source of truth for
# "how important is this task" — adding a new task means adding it
# here, not sprinkling tier guesses across the codebase.
TASK_TIER: dict[str, str] = {
    TASK_CHAT_ROUTING: TIER_CHEAP,
    TASK_KEYWORD_EXTRACTION: TIER_CHEAP,
    TASK_JOB_RANKING: TIER_CHEAP,
    TASK_CV_FORMAT: TIER_MEDIUM,
    TASK_TOOL_USE_CHAT: TIER_MEDIUM,
    TASK_CV_EXTRACT: TIER_MEDIUM,
    TASK_LETTER: TIER_PREMIUM,
    TASK_CV_CONSULT: TIER_PREMIUM,
    TASK_BRIEF: TIER_PREMIUM,
}

# Per-provider, per-tier default models. Operators can override any
# of these via env (see module docstring). Update the defaults here
# when a provider releases a cheaper / better model.
DEFAULT_MODELS: dict[str, dict[str, str]] = {
    "anthropic": {
        TIER_CHEAP: "claude-haiku-4-5",
        TIER_MEDIUM: "claude-haiku-4-5",
        TIER_PREMIUM: "claude-sonnet-4-6",
    },
    "openai": {
        TIER_CHEAP: "gpt-4o-mini",
        TIER_MEDIUM: "gpt-4o-mini",
        TIER_PREMIUM: "gpt-4o",
    },
    "deepseek": {
        TIER_CHEAP: "deepseek-chat",
        TIER_MEDIUM: "deepseek-chat",
        TIER_PREMIUM: "deepseek-reasoner",
    },
    "google_gemini": {
        TIER_CHEAP: "gemini-1.5-flash",
        TIER_MEDIUM: "gemini-1.5-flash",
        TIER_PREMIUM: "gemini-1.5-pro",
    },
}


def _env_key(provider_id: str, tier: str) -> str:
    return f"DIRECTJOB_MODEL_{provider_id.upper()}_{tier.upper()}"


def select_model(provider_id: str, task: str,
                  *, explicit_model: str = "") -> str:
    """Return the model name to use.

    Resolution order:
    1. ``explicit_model`` argument (caller knows best).
    2. ``DIRECTJOB_MODEL_<PROVIDER>_<TIER>`` env override.
    3. ``DEFAULT_MODELS[provider][tier]`` baked-in default.
    4. ``DIRECTJOB_MANAGED_AI_MODEL`` legacy env (single-model fallback).
    5. Empty string — caller decides.
    """
    if explicit_model:
        return explicit_model

    tier = TASK_TIER.get(task, TIER_MEDIUM)
    pid = (provider_id or "").lower()

    env_override = os.environ.get(_env_key(pid, tier))
    if env_override:
        return env_override.strip()

    provider_map = DEFAULT_MODELS.get(pid)
    if provider_map and tier in provider_map:
        return provider_map[tier]

    legacy = (os.environ.get("DIRECTJOB_MANAGED_AI_MODEL") or "").strip()
    return legacy


def tier_for_task(task: str) -> str:
    """Public helper for telemetry — what tier was a given task on?"""
    return TASK_TIER.get(task, TIER_MEDIUM)
