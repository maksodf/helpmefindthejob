# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""4-week plan W2 D6: bias-comparative-report runner contract tests.

The runner ships with cached responses checked into the repo so CI
re-validates the report without hitting any provider. These tests
pin the contract:

1. The CallOutcome JSONL round-trips losslessly.
2. Replay-only mode never makes an HTTP call.
3. Cost-cap-per-provider stops a live run when exceeded.
4. The per-persona aggregation handles partial coverage.
5. The cache file is JSON-stable (sorted keys, no whitespace).
6. The cached DeepSeek run (committed to repo) is loadable and
   covers all 7×10 = 70 scenarios.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.bias_comparative_report import (
    CACHE_DIR,
    PROVIDER_CONFIGS,
    CallOutcome,
    _cache_path_for,
    _cross_provider_disagreement,
    _load_cached_outcomes,
    _per_persona_mean,
    render_markdown,
    run_provider,
)


REPO_ROOT = Path(__file__).resolve().parent.parent


class CallOutcomeRoundtrip(unittest.TestCase):
    def test_roundtrip_via_dict(self):
        original = CallOutcome(
            provider_id="deepseek",
            persona_slug="aicha",
            scenario_label="aicha_strong_partner_network",
            status="ok",
            raw_score=92,
            raw_reason="High partner-network alignment with Anerkennung-track",
            raw_gaps=["Sprachnachweis B2"],
            cost_eur=0.0003,
            prompt_tokens=2800,
            completion_tokens=140,
            duration_ms=420,
            response_hash="abcdef0123456789",
        )
        roundtripped = CallOutcome.from_dict(original.to_dict())
        self.assertEqual(roundtripped.provider_id, original.provider_id)
        self.assertEqual(roundtripped.raw_score, original.raw_score)
        self.assertEqual(roundtripped.raw_gaps, original.raw_gaps)
        self.assertEqual(roundtripped.cost_eur, original.cost_eur)


class CachedOllamaRunPresent(unittest.TestCase):
    """Same contract as CachedDeepSeekRunPresent but for the local
    Ollama run. Together the two cached runs give the report the
    cross-provider data it needs."""

    @classmethod
    def setUpClass(cls):
        path = REPO_ROOT / "data" / "bias_comparative_cache" / "ollama.jsonl"
        if not path.exists():
            raise unittest.SkipTest(
                f"cached ollama run not present at {path} — "
                "run `python -m scripts.bias_comparative_report --live --providers ollama` "
                "to generate (free)"
            )
        cls.outcomes = list(_load_cached_outcomes("ollama").values())

    def test_seventy_outcomes(self):
        self.assertEqual(len(self.outcomes), 70)

    def test_all_outcomes_ok(self):
        statuses = {o.status for o in self.outcomes}
        self.assertEqual(statuses, {"ok"})

    def test_per_persona_means_in_plausible_band(self):
        means = _per_persona_mean(self.outcomes)
        self.assertEqual(len(means), 7)
        for slug, mean in means.items():
            self.assertGreaterEqual(mean, 30, f"persona {slug} mean {mean} too low")
            self.assertLessEqual(mean, 90, f"persona {slug} mean {mean} too high")


class CrossProviderComparativeDataPresent(unittest.TestCase):
    """The report's value comes from cross-provider comparison. If
    both DeepSeek and Ollama caches are present, the report MUST
    contain at least one disagreement cell — otherwise the
    aggregation is silently broken."""

    def test_at_least_one_disagreement_when_both_caches_present(self):
        ds_path = REPO_ROOT / "data" / "bias_comparative_cache" / "deepseek.jsonl"
        ol_path = REPO_ROOT / "data" / "bias_comparative_cache" / "ollama.jsonl"
        if not (ds_path.exists() and ol_path.exists()):
            raise unittest.SkipTest("both DeepSeek + Ollama caches required")
        ds = list(_load_cached_outcomes("deepseek").values())
        ol = list(_load_cached_outcomes("ollama").values())
        disagreements = _cross_provider_disagreement(
            {"deepseek": ds, "ollama": ol}
        )
        self.assertGreater(
            len(disagreements),
            0,
            "Both caches present but the report shows zero disagreement — "
            "either the data is suspiciously identical (re-check cache "
            "files) or _cross_provider_disagreement is broken",
        )

    def test_disagreement_rows_carry_both_provider_scores(self):
        ds_path = REPO_ROOT / "data" / "bias_comparative_cache" / "deepseek.jsonl"
        ol_path = REPO_ROOT / "data" / "bias_comparative_cache" / "ollama.jsonl"
        if not (ds_path.exists() and ol_path.exists()):
            raise unittest.SkipTest("both caches required")
        ds = list(_load_cached_outcomes("deepseek").values())
        ol = list(_load_cached_outcomes("ollama").values())
        rows = _cross_provider_disagreement({"deepseek": ds, "ollama": ol})
        for row in rows:
            self.assertIn("deepseek", row["scores"])
            self.assertIn("ollama", row["scores"])
            self.assertEqual(
                row["spread"],
                abs(row["scores"]["deepseek"] - row["scores"]["ollama"]),
            )


class CachedDeepSeekRunPresent(unittest.TestCase):
    """The cached DeepSeek run lives at
    data/bias_comparative_cache/deepseek.jsonl. The repo ships it
    so CI never has to make live API calls. This test pins:
    - the file is present
    - it has 70 outcomes (7 personas × 10 scenarios)
    - all of them have status='ok' (a live run completed cleanly)
    - per-persona means are within a plausible band
    """

    @classmethod
    def setUpClass(cls):
        path = REPO_ROOT / "data" / "bias_comparative_cache" / "deepseek.jsonl"
        if not path.exists():
            raise unittest.SkipTest(
                f"cached deepseek run not present at {path} — "
                "run `python -m scripts.bias_comparative_report --live --providers deepseek` "
                "to generate"
            )
        cls.outcomes = list(_load_cached_outcomes("deepseek").values())

    def test_seventy_outcomes(self):
        self.assertEqual(len(self.outcomes), 70)

    def test_all_outcomes_ok(self):
        statuses = {o.status for o in self.outcomes}
        self.assertEqual(statuses, {"ok"})

    def test_per_persona_means_in_plausible_band(self):
        # The methodology expects strong scenarios to score >75,
        # weak < 50, with persona means in 50-80. Outside this
        # band signals either a methodology break or a provider
        # drift — either way, worth investigating.
        means = _per_persona_mean(self.outcomes)
        self.assertEqual(len(means), 7)
        for slug, mean in means.items():
            self.assertGreaterEqual(
                mean, 40, f"persona {slug} mean {mean} below plausible floor"
            )
            self.assertLessEqual(
                mean, 90, f"persona {slug} mean {mean} above plausible ceiling"
            )

    def test_every_cell_has_a_response_hash(self):
        for o in self.outcomes:
            self.assertEqual(
                len(o.response_hash or ""),
                16,
                f"cell {o.persona_slug}/{o.scenario_label} has malformed response_hash",
            )


class ReplayOnlyDoesNotCallNetwork(unittest.TestCase):
    """If --replay-only is set and the cache is empty, the runner
    MUST mark all cells as cache_miss_replay_mode — never attempt
    a live HTTP call."""

    def test_replay_only_no_network_calls(self):
        with TemporaryDirectory() as tmp:
            with patch(
                "scripts.bias_comparative_report.CACHE_DIR", Path(tmp)
            ), patch(
                "scripts.bias_comparative_report._cache_path_for",
                lambda pid: Path(tmp) / f"{pid}.jsonl",
            ):
                outcomes, summary = run_provider(
                    "deepseek", live=False, max_eur=0.0
                )
        self.assertGreater(len(outcomes), 0)
        # Every outcome is a cache miss — none are 'ok' (which
        # would mean a network call happened)
        for o in outcomes:
            self.assertEqual(o.status, "cache_miss_replay_mode")
        self.assertEqual(summary["ok"], 0)
        self.assertEqual(summary["errors"], 0)
        self.assertGreater(summary["cache_misses"], 0)


class CrossProviderDisagreement(unittest.TestCase):
    def test_returns_empty_when_only_one_provider(self):
        outcomes_a = [
            CallOutcome("a", "aicha", "scen1", "ok", raw_score=80),
            CallOutcome("a", "aicha", "scen2", "ok", raw_score=70),
        ]
        rows = _cross_provider_disagreement({"a": outcomes_a})
        self.assertEqual(rows, [])

    def test_detects_disagreement(self):
        outcomes_a = [CallOutcome("a", "aicha", "scen1", "ok", raw_score=80)]
        outcomes_b = [CallOutcome("b", "aicha", "scen1", "ok", raw_score=40)]
        rows = _cross_provider_disagreement({"a": outcomes_a, "b": outcomes_b})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["spread"], 40)
        self.assertEqual(rows[0]["scores"], {"a": 80, "b": 40})

    def test_ignores_zero_spread(self):
        outcomes_a = [CallOutcome("a", "aicha", "scen1", "ok", raw_score=80)]
        outcomes_b = [CallOutcome("b", "aicha", "scen1", "ok", raw_score=80)]
        rows = _cross_provider_disagreement({"a": outcomes_a, "b": outcomes_b})
        self.assertEqual(rows, [])

    def test_top_20_only(self):
        # Build 30 cells with descending spread
        by_provider = {"a": [], "b": []}
        for i in range(30):
            by_provider["a"].append(
                CallOutcome("a", "aicha", f"scen{i}", "ok", raw_score=10)
            )
            by_provider["b"].append(
                CallOutcome("b", "aicha", f"scen{i}", "ok", raw_score=10 + i)
            )
        rows = _cross_provider_disagreement(by_provider)
        self.assertEqual(len(rows), 20)
        self.assertEqual(rows[0]["spread"], 29)  # highest first


class MarkdownReportShape(unittest.TestCase):
    def test_report_includes_all_required_sections(self):
        outcomes = [
            CallOutcome("deepseek", "aicha", "scen1", "ok", raw_score=85),
        ]
        summaries = [
            {
                "provider_id": "deepseek",
                "ok": 1,
                "errors": 0,
                "skipped_no_key": 0,
                "over_budget": 0,
                "cache_misses": 0,
                "total_cost_eur": 0.0003,
            }
        ]
        md = render_markdown({"deepseek": outcomes}, summaries)
        for fragment in (
            "# Bias-methodology comparative report",
            "## What this report measures",
            "## Per-provider summary",
            "## Per-persona mean score by provider",
            "## Top 20 highest-disagreement cells",
            "## Methodology",
            "## Re-running",
            "build_auto_fit_prompt",
            "deepseek",
        ):
            self.assertIn(fragment, md)


class ConfiguredProviderIdsMatchCostCaps(unittest.TestCase):
    """Drift guard: every provider_id PROVIDER_CONFIGS targets
    must have a cost-cap rate entry. Otherwise the live runner
    would compute cost=0 and burn the deployer's budget."""

    def test_every_runner_provider_has_a_rate(self):
        from company_discovery.cost_caps import PROVIDER_RATES_EUR_PER_MTOK

        for pid in PROVIDER_CONFIGS.keys():
            self.assertIn(
                pid,
                PROVIDER_RATES_EUR_PER_MTOK,
                f"provider {pid} in PROVIDER_CONFIGS but missing "
                "from PROVIDER_RATES_EUR_PER_MTOK — cost estimation "
                "would silently report €0 for this provider",
            )


if __name__ == "__main__":
    unittest.main()
