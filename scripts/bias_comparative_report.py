#!/usr/bin/env python3
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""4-week plan W2 D6: cross-provider bias-methodology runner.

Runs the 7-persona × N-scenario bias methodology against each of
the configured paid + local AI providers, caches every
``(provider_id, persona_slug, scenario_label)`` → response on
disk, and produces a comparative report.

Design decisions:

- **One live run, many CI replays.** The expensive part (8k+
  paid-API calls) is a deliberate operator action. The cached
  responses ship in the repo so CI re-validates the report from
  cache. Re-running live is rare (when adding a new provider,
  or quarterly to detect provider drift).

- **Failure isolation.** A provider that goes down does NOT
  poison the report. The cache records its status per call. The
  report has a "providers we couldn't reach this run" section.

- **Cost ceiling enforced.** Each provider gets a max-EUR
  budget the runner refuses to exceed. Default €10/provider —
  the operator overrides via ``--max-eur-per-provider``.

- **No PII in cache.** The cache stores prompt + response by
  short hash (first 16 hex of SHA-256). Plaintext lives only
  in the per-run JSONL the operator inspects on their laptop —
  never committed.

- **Cache is JSON-stable.** Sorted keys, no whitespace, so a
  reviewer's `diff` between runs is meaningful.

Usage::

    # Cache-replay (for CI + report regeneration)
    python -m scripts.bias_comparative_report --replay-only

    # Live run against configured providers
    python -m scripts.bias_comparative_report --live \\
        --providers deepseek,ollama \\
        --max-eur-per-provider 5

The cache lives at ``data/bias_comparative_cache/`` and the
report at ``docs/grant/bias-comparative-report-<date>.md``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.ai_providers import AIProviderConfig  # noqa: E402
from company_discovery.analysis import (  # noqa: E402
    build_auto_fit_prompt,
    parse_auto_fit_output,
)
from company_discovery.models import DiscoveredJob, UserProfile  # noqa: E402
from company_discovery.persona_fixtures import (  # noqa: E402
    PERSONAS,
    BiasScenario,
    PersonaFixture,
)

CACHE_DIR = REPO_ROOT / "data" / "bias_comparative_cache"
REPORT_DIR = REPO_ROOT / "docs" / "grant"


# Per-provider EUR/Mtok rates — should mirror cost_caps.PROVIDER_RATES_EUR_PER_MTOK
# but we re-import to avoid coupling test infrastructure to the cap
# substrate's exact key names.
# The replay / metrics / report core lives in the standalone, import-isolated
# ``biasprobe`` package. This module is the Helpmefindthejob live-run adapter
# (provider callers + the production ``build_auto_fit_prompt`` seam) and
# re-exports the core symbols so existing callers + tests keep their imports.
from biasprobe import (  # noqa: E402
    CallOutcome,
    cache_path,
    cross_provider_disagreement,
    per_persona_mean,
    render_markdown,
)
from biasprobe.outcomes import append_outcome_to_path, load_outcomes_from_path  # noqa: E402
from company_discovery.cost_caps import PROVIDER_RATES_EUR_PER_MTOK

# Hand-curated subset of providers the runner can target. Each
# entry maps the public provider_id to (env_var_for_key, model,
# api_url_template). Local-only providers (ollama / manual /
# claude_code / codex_cli) target the local URL convention.
PROVIDER_CONFIGS: dict[str, dict[str, Any]] = {
    "deepseek": {
        "env_key": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "kind": "openai_compatible",
    },
    "openai": {
        "env_key": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
        "url": "https://api.openai.com/v1/chat/completions",
        "kind": "openai_compatible",
    },
    "google_gemini": {
        "env_key": "GOOGLE_GEMINI_API_KEY",
        "model": "gemini-1.5-flash",
        "url": (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-1.5-flash:generateContent"
        ),
        "kind": "google",
    },
    "anthropic": {
        "env_key": "ANTHROPIC_API_KEY",
        "model": "claude-3-5-haiku-20241022",
        "url": "https://api.anthropic.com/v1/messages",
        "kind": "anthropic",
    },
    "ollama": {
        "env_key": None,
        "model": os.environ.get("HELPMEFINDTHEJOB_BIAS_MODEL", "llama3.1:8b"),
        "url": os.environ.get("HELPMEFINDTHEJOB_OLLAMA_URL", "http://localhost:11434")
        + "/api/generate",
        "kind": "ollama",
    },
}


# ---------------------------------------------------------------------------
# Cache helpers — thin wrappers over biasprobe. Routed through ``_cache_path_for``
# so a patched CACHE_DIR / _cache_path_for (tests) still controls read/write.
# ---------------------------------------------------------------------------


def _cache_path_for(provider_id: str) -> Path:
    return cache_path(CACHE_DIR, provider_id)


def _load_cached_outcomes(provider_id: str) -> dict[tuple[str, str], CallOutcome]:
    return load_outcomes_from_path(_cache_path_for(provider_id))


def _append_outcome_to_cache(outcome: CallOutcome) -> None:
    append_outcome_to_path(_cache_path_for(outcome.provider_id), outcome)


# ---------------------------------------------------------------------------
# Provider clients (stdlib HTTP — no SDK dependency)
# ---------------------------------------------------------------------------


def _call_openai_compatible(
    url: str, api_key: str, model: str, prompt: str
) -> tuple[str, int, int]:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 400,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = payload.get("usage", {})
    return (
        content,
        int(usage.get("prompt_tokens", 0)),
        int(usage.get("completion_tokens", 0)),
    )


def _call_google(url: str, api_key: str, model: str, prompt: str) -> tuple[str, int, int]:
    body = json.dumps(
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 400},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{url}?key={api_key}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    parts = payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    content = "".join(p.get("text", "") for p in parts)
    usage = payload.get("usageMetadata", {})
    return (
        content,
        int(usage.get("promptTokenCount", 0)),
        int(usage.get("candidatesTokenCount", 0)),
    )


def _call_anthropic(url: str, api_key: str, model: str, prompt: str) -> tuple[str, int, int]:
    body = json.dumps(
        {
            "model": model,
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    parts = payload.get("content", [])
    content = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    usage = payload.get("usage", {})
    return (
        content,
        int(usage.get("input_tokens", 0)),
        int(usage.get("output_tokens", 0)),
    )


def _call_ollama(url: str, _api_key: str, model: str, prompt: str) -> tuple[str, int, int]:
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return (
        payload.get("response", ""),
        int(payload.get("prompt_eval_count", 0)),
        int(payload.get("eval_count", 0)),
    )


_CALLERS: dict[str, Callable[..., tuple[str, int, int]]] = {
    "openai_compatible": _call_openai_compatible,
    "google": _call_google,
    "anthropic": _call_anthropic,
    "ollama": _call_ollama,
}


# ---------------------------------------------------------------------------
# Prompt construction (production builder)
# ---------------------------------------------------------------------------


def _scenarios_for_persona(persona: PersonaFixture) -> Iterable[BiasScenario]:
    """Yield every scoring scenario the methodology covers for this
    persona. We use scenarios only (not cv_tailoring_scenarios) so
    the comparative report cleanly parses to a single
    fit-score-per-cell grid."""
    return persona.scenarios


def _build_fit_prompt(persona: PersonaFixture, scenario: BiasScenario) -> str:
    profile = UserProfile(
        user_id=f"bias-comparative-{persona.slug}",
        persona_id=persona.slug,
        target_roles=list(persona.target_roles),
        industry=persona.industry,
        location=persona.location,
        seniority=persona.seniority,
        years_experience=persona.years_experience,
        languages=list(persona.languages),
        cv_text=persona.cv_summary,
    )
    job = DiscoveredJob(
        user_id=profile.user_id,
        source_url=f"https://demo.helpmefindthejob.org/bias-comparative/{scenario.label}",
        title=scenario.job_title,
        location=scenario.job_location,
        raw_description=scenario.job_description,
    )
    provider = AIProviderConfig(provider_id="bias-comparative-runner")
    # BiasScenario carries no employer name — the bias test is
    # about response shape, not employer realism. Use the same
    # synthetic-employer convention as tests/test_bias_methodology.py.
    company_name = f"Synthetic employer ({scenario.label})"
    built = build_auto_fit_prompt(job, company_name, provider, profile)
    return built["prompt"]


# ---------------------------------------------------------------------------
# Cost estimation (mirror cost_caps but local to keep runner standalone)
# ---------------------------------------------------------------------------


def _estimate_cost_eur(provider_id: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = PROVIDER_RATES_EUR_PER_MTOK.get(
        provider_id, {"prompt_per_mtok": 0.0, "completion_per_mtok": 0.0}
    )
    p = prompt_tokens / 1_000_000 * rates["prompt_per_mtok"]
    c = completion_tokens / 1_000_000 * rates["completion_per_mtok"]
    return round(p + c, 6)


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Live run + replay
# ---------------------------------------------------------------------------


def run_provider(
    provider_id: str,
    *,
    live: bool,
    max_eur: float,
    progress: Callable[[str], None] | None = None,
) -> tuple[list[CallOutcome], dict[str, Any]]:
    """Walk every persona × scenario for this provider. Replays
    from cache by default; only hits the network when ``live`` is
    True and the cache doesn't already have the cell."""
    cfg = PROVIDER_CONFIGS.get(provider_id)
    if cfg is None:
        return [], {"status": "unknown_provider"}
    cache = _load_cached_outcomes(provider_id)
    outcomes: list[CallOutcome] = []
    api_key = ""
    if cfg.get("env_key"):
        api_key = os.environ.get(cfg["env_key"], "").strip()
    spent_eur = 0.0
    skipped_no_key = 0
    spent_capped = 0
    caller = _CALLERS[cfg["kind"]]
    for persona in PERSONAS:
        for scenario in _scenarios_for_persona(persona):
            cell_key = (persona.slug, scenario.label)
            if cell_key in cache:
                outcomes.append(cache[cell_key])
                continue
            if not live:
                outcomes.append(
                    CallOutcome(
                        provider_id=provider_id,
                        persona_slug=persona.slug,
                        scenario_label=scenario.label,
                        status="cache_miss_replay_mode",
                    )
                )
                continue
            if cfg.get("env_key") and not api_key:
                outcomes.append(
                    CallOutcome(
                        provider_id=provider_id,
                        persona_slug=persona.slug,
                        scenario_label=scenario.label,
                        status="skipped_no_key",
                    )
                )
                skipped_no_key += 1
                continue
            if spent_eur >= max_eur:
                outcomes.append(
                    CallOutcome(
                        provider_id=provider_id,
                        persona_slug=persona.slug,
                        scenario_label=scenario.label,
                        status="over_budget",
                    )
                )
                spent_capped += 1
                continue
            prompt = _build_fit_prompt(persona, scenario)
            t0 = time.monotonic()
            try:
                content, ptoks, ctoks = caller(cfg["url"], api_key, cfg["model"], prompt)
                score, reason, gaps = parse_auto_fit_output(content)
                cost = _estimate_cost_eur(provider_id, ptoks, ctoks)
                spent_eur += cost
                # parse_auto_fit_output returns score as a 0-1 float
                # (or None on parse failure). Convert to 0-100
                # integer for the report; that's the bands the
                # methodology tables use.
                raw_score_int: int | None = None
                if score is not None:
                    raw_score_int = max(0, min(100, int(round(score * 100))))
                outcome = CallOutcome(
                    provider_id=provider_id,
                    persona_slug=persona.slug,
                    scenario_label=scenario.label,
                    status="ok",
                    raw_score=raw_score_int,
                    raw_reason=(reason or "")[:200] or None,
                    raw_gaps=list(gaps or [])[:5],
                    cost_eur=cost,
                    prompt_tokens=ptoks,
                    completion_tokens=ctoks,
                    duration_ms=int((time.monotonic() - t0) * 1000),
                    response_hash=_short_hash(content),
                )
                _append_outcome_to_cache(outcome)
                outcomes.append(outcome)
                if progress:
                    progress(
                        f"  ✓ {provider_id} {persona.slug}/{scenario.label} "
                        f"score={outcome.raw_score} cost=€{cost:.4f} "
                        f"(spent €{spent_eur:.2f}/€{max_eur:.2f})"
                    )
            except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as exc:
                outcome = CallOutcome(
                    provider_id=provider_id,
                    persona_slug=persona.slug,
                    scenario_label=scenario.label,
                    status="error",
                    error_class=f"{type(exc).__name__}: {exc}"[:200],
                    duration_ms=int((time.monotonic() - t0) * 1000),
                )
                _append_outcome_to_cache(outcome)
                outcomes.append(outcome)
                if progress:
                    progress(
                        f"  ✗ {provider_id} {persona.slug}/{scenario.label} {outcome.error_class}"
                    )
    summary = {
        "provider_id": provider_id,
        "total_cells": len(outcomes),
        "ok": sum(1 for o in outcomes if o.status == "ok"),
        "errors": sum(1 for o in outcomes if o.status == "error"),
        "skipped_no_key": skipped_no_key,
        "over_budget": spent_capped,
        "cache_misses": sum(1 for o in outcomes if o.status == "cache_miss_replay_mode"),
        "total_cost_eur": round(spent_eur, 4),
    }
    return outcomes, summary


# ---------------------------------------------------------------------------
# Aggregation + Markdown report
# ---------------------------------------------------------------------------


# _per_persona_mean, _cross_provider_disagreement, and render_markdown now live
# in the standalone biasprobe package (imported at the top of this module).
# Re-export the metric helpers under their historical private names so existing
# callers + tests keep importing them from here.
_per_persona_mean = per_persona_mean
_cross_provider_disagreement = cross_provider_disagreement


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Make real API calls for cache misses (default: replay-only).",
    )
    parser.add_argument(
        "--replay-only",
        action="store_true",
        help="Replay from cache only — never make a real API call. Used in CI.",
    )
    parser.add_argument(
        "--providers",
        default=",".join(PROVIDER_CONFIGS.keys()),
        help=(
            "Comma-separated provider ids to run. Defaults to all "
            f"configured: {','.join(PROVIDER_CONFIGS.keys())}"
        ),
    )
    parser.add_argument(
        "--max-eur-per-provider",
        type=float,
        default=10.0,
        help="Hard cost ceiling per provider (default €10).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Markdown report output path. Defaults to docs/grant/bias-comparative-report-<date>.md"
        ),
    )
    args = parser.parse_args(argv)

    if args.live and args.replay_only:
        print("ERROR: --live and --replay-only are mutually exclusive", file=sys.stderr)
        return 2

    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    unknown = [p for p in providers if p not in PROVIDER_CONFIGS]
    if unknown:
        print(f"ERROR: unknown providers: {unknown}", file=sys.stderr)
        return 2

    by_provider: dict[str, list[CallOutcome]] = {}
    summaries: list[dict[str, Any]] = []
    for provider_id in providers:
        outs, summary = run_provider(
            provider_id,
            live=args.live,
            max_eur=args.max_eur_per_provider,
            progress=print if args.live else None,
        )
        by_provider[provider_id] = outs
        summaries.append(summary)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = args.output or (
        REPORT_DIR / f"bias-comparative-report-{datetime.now(timezone.utc).date().isoformat()}.md"
    )
    md = render_markdown(by_provider, summaries)
    output_path.write_text(md, encoding="utf-8")
    print(f"\nWrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
