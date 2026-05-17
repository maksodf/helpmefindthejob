# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Phase 2d — score-rank-cap layer for aggregated jobs."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.aggregators import (
    AggregatedJob,
    rank_aggregated,
    score_job,
    source_priority,
)


class SourcePriorityTests(unittest.TestCase):
    def test_known_sources_ranked_higher_than_unknown(self) -> None:
        self.assertGreater(source_priority("greenhouse"), source_priority("unknown_provider"))
        self.assertGreater(source_priority("curated"), source_priority("duckduckgo"))
        self.assertGreater(source_priority("muse"), source_priority("brave_search"))


class ScoreJobTests(unittest.TestCase):
    NOW = datetime(2026, 5, 9, 12, tzinfo=timezone.utc)

    def _job(self, **overrides) -> AggregatedJob:
        defaults = dict(
            title="Healthcare Policy Consultant",
            company_name="PPH",
            source="muse",
            source_url="https://x/y",
            location="Berlin",
            description="Consulting on health policy reform in DACH.",
            posted_at=self.NOW - timedelta(hours=2),
        )
        defaults.update(overrides)
        return AggregatedJob(**defaults)

    def test_keyword_match_increases_score(self) -> None:
        job = self._job()
        with_match = score_job(job, keyword_tokens=["healthcare", "policy"], now=self.NOW)
        no_match = score_job(job, keyword_tokens=["unrelated"], now=self.NOW)
        self.assertGreater(with_match, no_match)

    def test_freshness_decays(self) -> None:
        recent = self._job(posted_at=self.NOW - timedelta(hours=2))
        stale = self._job(posted_at=self.NOW - timedelta(days=20))
        ancient = self._job(posted_at=self.NOW - timedelta(days=60))
        self.assertGreater(score_job(recent, now=self.NOW), score_job(stale, now=self.NOW))
        self.assertGreater(score_job(stale, now=self.NOW), score_job(ancient, now=self.NOW))

    def test_location_match_boost(self) -> None:
        job = self._job(location="Berlin, Germany")
        self.assertGreater(
            score_job(job, location="Berlin", now=self.NOW),
            score_job(job, location="Tokyo", now=self.NOW),
        )

    def test_remote_treated_as_match(self) -> None:
        job = self._job(location="Remote — Worldwide")
        self.assertGreater(
            score_job(job, location="Berlin", now=self.NOW),  # remote allowed
            score_job(self._job(location="Singapore only"), location="Berlin", now=self.NOW),
        )

    def test_dismissed_term_in_title_drops_score(self) -> None:
        job = self._job(title="Insurance Claims Adjuster", company_name="Allstate")
        baseline = score_job(job, now=self.NOW)
        penalised = score_job(
            job,
            now=self.NOW,
            dismissed_terms=["Insurance Claims Adjuster"],
        )
        self.assertLess(penalised, baseline)
        self.assertAlmostEqual(baseline - penalised, 0.20, places=2)

    def test_dismissed_term_in_company_drops_score(self) -> None:
        job = self._job(title="Senior Engineer", company_name="ContosoCo")
        baseline = score_job(job, now=self.NOW)
        penalised = score_job(job, now=self.NOW, dismissed_terms=["ContosoCo"])
        self.assertLess(penalised, baseline)

    def test_dismissed_terms_irrelevant_no_change(self) -> None:
        job = self._job(title="Healthcare Policy Consultant", company_name="PPH")
        baseline = score_job(job, now=self.NOW)
        unchanged = score_job(job, now=self.NOW, dismissed_terms=["wholly-different-string"])
        self.assertEqual(baseline, unchanged)

    def test_dismissed_terms_penalty_capped(self) -> None:
        # Even with five dismissed substring hits, the total penalty is
        # capped at 0.40 so a strong signal can still surface. Build a
        # high-baseline job (keyword + location + freshness all maxed)
        # so the cap is observable rather than floored at zero.
        job = self._job(title="Senior Frontend Engineer Healthcare Policy", company_name="ContosoCo")
        terms = ["senior", "frontend", "engineer", "contoso", "co"]
        baseline = score_job(
            job,
            now=self.NOW,
            keyword_tokens=["healthcare", "policy"],
            location="Berlin",
        )
        penalised = score_job(
            job,
            now=self.NOW,
            keyword_tokens=["healthcare", "policy"],
            location="Berlin",
            dismissed_terms=terms,
        )
        delta = round(baseline - penalised, 2)
        self.assertGreaterEqual(delta, 0.39)
        self.assertLessEqual(delta, 0.41)


class RankWithDismissedTests(unittest.TestCase):
    NOW = datetime(2026, 5, 9, 12, tzinfo=timezone.utc)

    def test_dismissed_jobs_ranked_below_neutral(self) -> None:
        # Two equally-fresh jobs with the same source priority. The
        # dismissed one should rank strictly lower.
        keep = AggregatedJob(
            title="Backend Engineer", company_name="OpenCo", source="muse",
            source_url="https://x/keep", location="Berlin", description="x",
            posted_at=self.NOW - timedelta(hours=1),
        )
        drop = AggregatedJob(
            title="Insurance Claims Adjuster", company_name="Allstate", source="muse",
            source_url="https://x/drop", location="Berlin", description="x",
            posted_at=self.NOW - timedelta(hours=1),
        )
        ranked = rank_aggregated(
            [drop, keep],
            location="Berlin",
            now=self.NOW,
            dismissed_terms=["Insurance Claims Adjuster"],
        )
        self.assertEqual(ranked[0][0].title, "Backend Engineer")
        self.assertGreater(ranked[0][1], ranked[1][1])


class RankAggregatedTests(unittest.TestCase):
    NOW = datetime(2026, 5, 9, 12, tzinfo=timezone.utc)

    def test_orders_by_composite_score(self) -> None:
        good = AggregatedJob(
            title="Healthcare Policy Consultant",
            company_name="PPH",
            source="curated",
            source_url="https://pph/jobs/1",
            location="Berlin",
            description="health policy consulting",
            posted_at=self.NOW - timedelta(hours=1),
        )
        bad = AggregatedJob(
            title="Auto Claims Adjuster",
            company_name="Allstate",
            source="muse",
            source_url="https://muse/jobs/2",
            location="Atlanta",
            description="insurance claims",
            posted_at=self.NOW - timedelta(days=20),
        )
        ranked = rank_aggregated(
            [bad, good],
            keyword_tokens=["healthcare", "policy"],
            location="Berlin",
            now=self.NOW,
        )
        self.assertEqual(ranked[0][0].title, "Healthcare Policy Consultant")
        self.assertGreater(ranked[0][1], ranked[1][1])

    def test_cap_applied(self) -> None:
        jobs = [
            AggregatedJob(title=f"Role {i}", company_name="Co", source="muse",
                          source_url=f"https://x/{i}", description="x", posted_at=self.NOW)
            for i in range(20)
        ]
        ranked = rank_aggregated(jobs, cap=5, now=self.NOW)
        self.assertEqual(len(ranked), 5)


if __name__ == "__main__":
    unittest.main()
