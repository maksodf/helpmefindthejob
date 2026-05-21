# Bias-methodology comparative report

Generated 2026-05-21T18:00:03+00:00 by `scripts/bias_comparative_report.py`.

## What this report measures

For each AI provider, this report runs the SAME prompt (the production `build_auto_fit_prompt`) against the SAME 7-persona × N-scenario panel, captures the fit-score the provider returns, and reports per-provider + per-persona aggregates plus cross-provider disagreement.

**No competitor in this space publishes this data.** It exists because the project's bias-methodology test harness is reproducible — anyone with API keys can re-run via `--live`; everyone else can re-validate via `--replay-only` against the cached responses checked into the repo.

## Per-provider summary

| Provider | OK | Errors | Skipped (no key) | Over budget | Cache misses | Total cost (€) |
|---|---|---|---|---|---|---|
| deepseek | 70 | 0 | 0 | 0 | 0 | 0.0000 |

## Per-persona mean score by provider

| Provider | aicha | kaethe | mahmoud | maria | olga | tobias | yusuf |
|---|---|---|---|---|---|---|---|
| deepseek | 56.4 | 70.0 | 59.2 | 58.9 | 61.3 | 74.3 | 59.9 |

## Top 20 highest-disagreement cells

These are cells where providers disagree most strongly on the same (persona, scenario). Worth investigating: which provider is right? Or are both legitimately interpreting different facets?

| Persona | Scenario | Spread | Provider scores |
|---|---|---|---|
| _(no cross-provider data available in this run)_ | | | |

## Methodology

- Prompt builder: `company_discovery.analysis.build_auto_fit_prompt` (production prompt — same one used by `/auto-fit`)
- Score parser: `company_discovery.analysis.parse_auto_fit_output` (0–100 integer; reasons/gaps optional)
- Personas: 7 fixtures from `company_discovery.persona_fixtures.PERSONAS`
- Temperature: 0 across all providers (reproducibility)

## Re-running

```bash
# Replay-only (no API calls; reads from data/bias_comparative_cache/)
python -m scripts.bias_comparative_report --replay-only

# Live run against one provider
python -m scripts.bias_comparative_report --live --providers deepseek
```

