# Bias-methodology comparative report

Generated 2026-05-21T18:12:26+00:00 by `scripts/bias_comparative_report.py`.

## What this report measures

For each AI provider, this report runs the SAME prompt (the production `build_auto_fit_prompt`) against the SAME 7-persona × N-scenario panel, captures the fit-score the provider returns, and reports per-provider + per-persona aggregates plus cross-provider disagreement.

**No competitor in this space publishes this data.** It exists because the project's bias-methodology test harness is reproducible — anyone with API keys can re-run via `--live`; everyone else can re-validate via `--replay-only` against the cached responses checked into the repo.

## Per-provider summary

| Provider | OK | Errors | Skipped (no key) | Over budget | Cache misses | Total cost (€) |
|---|---|---|---|---|---|---|
| deepseek | 70 | 0 | 0 | 0 | 0 | 0.0000 |
| ollama | 70 | 0 | 0 | 0 | 0 | 0.0000 |

## Per-persona mean score by provider

| Provider | aicha | kaethe | mahmoud | maria | olga | tobias | yusuf |
|---|---|---|---|---|---|---|---|
| deepseek | 56.4 | 70.0 | 59.2 | 58.9 | 61.3 | 74.3 | 59.9 |
| ollama | 62.2 | 67.4 | 57.0 | 60.1 | 50.4 | 67.0 | 52.6 |

## Top 20 highest-disagreement cells

These are cells where providers disagree most strongly on the same (persona, scenario). Worth investigating: which provider is right? Or are both legitimately interpreting different facets?

| Persona | Scenario | Spread | Provider scores |
|---|---|---|---|
| olga | olga_mixed_distant_city | 30 | deepseek=70, ollama=40 |
| olga | olga_weak_wrong_industry_c | 29 | deepseek=34, ollama=5 |
| olga | olga_weak_wrong_industry_b | 22 | deepseek=35, ollama=13 |
| tobias | tobias_weak_wrong_industry_a | 22 | deepseek=47, ollama=25 |
| aicha | aicha_mixed_format_mismatch | 21 | deepseek=53, ollama=74 |
| yusuf | yusuf_mixed_distant_city | 21 | deepseek=59, ollama=38 |
| olga | olga_mixed_language_barrier | 21 | deepseek=56, ollama=35 |
| mahmoud | mahmoud_mixed_format_mismatch | 20 | deepseek=55, ollama=75 |
| olga | olga_mixed_format_mismatch | 19 | deepseek=56, ollama=75 |
| tobias | tobias_weak_wrong_industry_b | 19 | deepseek=44, ollama=25 |
| tobias | tobias_weak_wrong_industry_c | 19 | deepseek=44, ollama=25 |
| kaethe | kaethe_weak_wrong_industry_a | 18 | deepseek=34, ollama=52 |
| mahmoud | ausbildung_shk_hamburg | 17 | deepseek=90, ollama=73 |
| kaethe | kaethe_mixed_distant_city | 17 | deepseek=74, ollama=57 |
| mahmoud | mahmoud_mixed_language_barrier | 16 | deepseek=48, ollama=64 |
| kaethe | kaethe_strong_partner_network | 16 | deepseek=90, ollama=74 |
| kaethe | kaethe_mixed_recency_friction | 16 | deepseek=73, ollama=89 |
| yusuf | bluecard_automotive_engineer | 15 | deepseek=90, ollama=75 |
| aicha | aicha_mixed_language_barrier | 14 | deepseek=50, ollama=64 |
| aicha | aicha_mixed_adjacent_specialty | 14 | deepseek=70, ollama=84 |

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

