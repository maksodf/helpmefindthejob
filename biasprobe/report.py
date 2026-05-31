# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Render a comparative bias report (Markdown) from cached outcomes.

The report is intentionally plain Markdown so it renders on GitHub, in the
docs site, and in a grant PDF unchanged. ``generated_by`` is the only
domain-injected string — it defaults to the employment reference runner so the
in-repo report stays byte-identical, and ``python -m biasprobe`` overrides it to
attribute the standalone replay.

Stdlib only (``datetime``); no host-application coupling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from biasprobe.metrics import cross_provider_disagreement, per_persona_mean
from biasprobe.outcomes import CallOutcome

DEFAULT_GENERATED_BY = "`scripts/bias_comparative_report.py`"


def render_markdown(
    by_provider: dict[str, list[CallOutcome]],
    summaries: list[dict[str, Any]],
    *,
    generated_by: str = DEFAULT_GENERATED_BY,
) -> str:
    lines: list[str] = []
    lines.append("# Bias-methodology comparative report")
    lines.append("")
    lines.append(
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by {generated_by}."
    )
    lines.append("")
    lines.append("## What this report measures")
    lines.append("")
    lines.append(
        "For each AI provider, this report runs the SAME prompt (the production "
        "`build_auto_fit_prompt`) against the SAME 7-persona × N-scenario panel, "
        "captures the fit-score the provider returns, and reports per-provider + "
        "per-persona aggregates plus cross-provider disagreement."
    )
    lines.append("")
    lines.append(
        "Comparative per-persona bias data like this is rarely published in the "
        "employment-AI space. It exists here because the bias-methodology harness "
        "is reproducible — anyone with API keys can re-run via `--live`; everyone "
        "else can re-validate via `--replay-only` against the cached responses "
        "checked into the repo."
    )
    lines.append("")
    lines.append("## Per-provider summary")
    lines.append("")
    lines.append(
        "| Provider | OK | Errors | Skipped (no key) | Over budget | Cache misses | Total cost (€) |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for s in summaries:
        lines.append(
            f"| {s['provider_id']} | {s['ok']} | {s['errors']} | {s['skipped_no_key']} | "
            f"{s['over_budget']} | {s['cache_misses']} | {s['total_cost_eur']:.4f} |"
        )
    lines.append("")
    lines.append("## Per-persona mean score by provider")
    lines.append("")
    persona_slugs = sorted({o.persona_slug for outs in by_provider.values() for o in outs})
    header = "| Provider | " + " | ".join(persona_slugs) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (len(persona_slugs) + 1))
    for provider_id, outs in sorted(by_provider.items()):
        means = per_persona_mean(outs)
        row = (
            f"| {provider_id} | "
            + " | ".join(
                f"{means.get(p, float('nan')):.1f}" if p in means else "—" for p in persona_slugs
            )
            + " |"
        )
        lines.append(row)
    lines.append("")
    lines.append("## Top 20 highest-disagreement cells")
    lines.append("")
    lines.append(
        "These are cells where providers disagree most strongly on the same "
        "(persona, scenario). Worth investigating: which provider is right? "
        "Or are both legitimately interpreting different facets?"
    )
    lines.append("")
    lines.append("| Persona | Scenario | Spread | Provider scores |")
    lines.append("|---|---|---|---|")
    disagreements = cross_provider_disagreement(by_provider)
    if not disagreements:
        lines.append("| _(no cross-provider data available in this run)_ | | | |")
    else:
        for cell in disagreements:
            scores_str = ", ".join(f"{p}={s}" for p, s in cell["scores"].items())
            lines.append(
                f"| {cell['persona']} | {cell['scenario']} | {cell['spread']} | {scores_str} |"
            )
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append(
        "- Prompt builder: `company_discovery.analysis.build_auto_fit_prompt` "
        "(production prompt — same one used by `/auto-fit`)"
    )
    lines.append(
        "- Score parser: `company_discovery.analysis.parse_auto_fit_output` "
        "(0–100 integer; reasons/gaps optional)"
    )
    lines.append("- Personas: 7 fixtures from `company_discovery.persona_fixtures.PERSONAS`")
    lines.append("- Temperature: 0 across all providers (reproducibility)")
    lines.append("")
    lines.append("## Re-running")
    lines.append("")
    lines.append("```bash")
    lines.append("# Replay-only (no API calls; reads from data/bias_comparative_cache/)")
    lines.append("python -m scripts.bias_comparative_report --replay-only")
    lines.append("")
    lines.append("# Live run against one provider")
    lines.append("python -m scripts.bias_comparative_report --live --providers deepseek")
    lines.append("```")
    lines.append("")
    return "\n".join(lines) + "\n"
