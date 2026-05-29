<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# biasprobe — reproducible comparative bias evaluation for employment AI

`biasprobe` measures how different LLM providers score the **same** prompt
against the **same** panel of job-seeker personas, then surfaces per-persona
means and the cells where providers disagree most. Every published number is
**replayable offline** from committed caches — no API keys, no network, no
host-application import:

```console
$ python -m biasprobe
# Bias-methodology comparative report
...
```

**Why this is unusual.** Most employment-AI products never publish *any*
comparative bias data; the few that mention fairness rarely ship the raw
per-cell scores or a way to reproduce them. `biasprobe` makes the methodology a
build artifact: anyone with API keys can re-run live, and everyone else can
re-validate against the cached responses checked into the repo.

> The personas are **synthetic fixtures**, not real users. `biasprobe` measures
> *model behaviour on a controlled panel* — a necessary, not sufficient, part of
> a fairness story. Real-user outcome measurement is a separate, human-owned track.

## Use it

Standalone (replays the bundled caches):

```console
$ python -m biasprobe                      # report to stdout
$ python -m biasprobe --output report.md   # write it
$ python -m biasprobe --cache-dir DIR       # replay your own <provider>.jsonl caches
$ python -m biasprobe --providers deepseek  # restrict to some providers
```

As a library:

```python
import biasprobe

cache_dir = biasprobe.DEFAULT_CACHE_DIR
by_provider, summaries = {}, []
for pid in biasprobe.discover_providers(cache_dir):
    outcomes = list(biasprobe.load_outcomes(cache_dir, pid).values())
    by_provider[pid] = outcomes
    summaries.append(biasprobe.summarize(pid, outcomes))

print(biasprobe.render_markdown(by_provider, summaries))
print(biasprobe.per_persona_mean(by_provider["deepseek"]))
print(biasprobe.cross_provider_disagreement(by_provider))
```

## Published numbers (bundled caches)

Per-persona **mean fit-score** (0–100), 70 cells per provider (7 personas × 10
scenarios), 0 errors. Regenerate with `python -m biasprobe`.

| Provider | aïcha | käthe | mahmoud | maria | olga | tobias | yusuf |
|---|---|---|---|---|---|---|---|
| deepseek | 56.4 | 70.0 | 59.2 | 58.9 | 61.3 | 74.3 | 59.9 |
| ollama (llama3.1:8b) | 62.2 | 67.4 | 57.0 | 60.1 | 50.4 | 67.0 | 52.6 |

The highest cross-provider disagreement cell is `olga_mixed_distant_city`
(spread 30: deepseek 70 vs ollama 40) — the kind of cell a reviewer should
investigate. Full table in the generated report.

## Methodology + provenance

- **Prompt** — the production fit-scoring prompt the app actually serves, so the
  harness measures shipped behaviour rather than a proxy.
- **Temperature 0** across all providers, for reproducibility.
- **Cache** — append-only JSONL per provider, keyed by `(persona, scenario)`.
  `biasprobe/data/` is byte-identical to the repo-canonical
  `data/bias_comparative_cache/` (pinned by `tests/test_biasprobe_standalone.py`).
- Full write-up: [`compliance/accuracy-and-bias-testing.md`](../compliance/accuracy-and-bias-testing.md).

## Relationship to Helpmefindthejob

`biasprobe` is the import-isolated **replay / metrics / report core** (stdlib
only). The Helpmefindthejob **live runner** lives at
`scripts/bias_comparative_report.py`: it adds the provider HTTP callers and the
production `build_auto_fit_prompt` seam, then delegates replay, aggregation and
rendering back to this package.

To adapt `biasprobe` to another employment-AI project: keep this package as-is,
write your own live runner that produces `CallOutcome` rows from your personas +
your production prompt, and append them to a cache dir. `python -m biasprobe
--cache-dir <yours>` then renders the same comparative report over your data.
(The default report prose names this project's reference modules — edit it for
your domain.)

## License

Apache-2.0. The bundled caches are model outputs over synthetic fixtures, not
user data.
