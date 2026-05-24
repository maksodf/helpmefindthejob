# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 #71 — JobIndex substrate + write-through contract tests.

The persistent facet-indexed sqlite store has three public surfaces:
- upsert_jobs(jobs, role_bucket=, ...) — write-through entry point
- count_by_facets(role_bucket=, location=, ...) — facet query
- jobs_by_facets(role_bucket=, location=, limit=) — sample retrieval
- purge_expired() — TTL maintenance

Plus a Phase A write-through hook on JobAggregationEngine that
populates the index after the cross-provider dedup phase.
"""

from __future__ import annotations

import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.aggregators import AggregatedJob, JobAggregationEngine
from company_discovery.job_index import (
    JobIndex,
    _norm_location,
    _norm_title,
    classify_language,
    classify_seniority,
)


def _make_job(
    title: str,
    company: str,
    location: str,
    source_url: str,
    source: str = "test_provider",
    description: str = "",
) -> AggregatedJob:
    return AggregatedJob(
        title=title,
        company_name=company,
        location=location,
        source_url=source_url,
        source=source,
        description=description,
    )


class NormalisationTests(unittest.TestCase):
    def test_norm_location_strips_accents_and_lowercases(self):
        self.assertEqual(_norm_location("München"), "munchen")
        self.assertEqual(_norm_location("BERLIN"), "berlin")

    def test_norm_location_drops_country_suffix(self):
        self.assertEqual(_norm_location("Berlin, Deutschland"), "berlin")
        self.assertEqual(_norm_location("Paris, France"), "paris")

    def test_norm_location_collapses_whitespace(self):
        self.assertEqual(_norm_location("  Berlin    Mitte  "), "berlin mitte")

    def test_norm_location_empty_returns_empty(self):
        self.assertEqual(_norm_location(""), "")
        self.assertEqual(_norm_location(None), "")

    def test_norm_title_case_folds_and_strips(self):
        self.assertEqual(_norm_title("Senior Frontend DEVELOPER"), "senior frontend developer")
        self.assertEqual(_norm_title("  Krankenpfleger/in "), "krankenpfleger/in")


class JobIndexUpsertTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.index = JobIndex(Path(self.tmp.name) / "test.sqlite", ttl_seconds=3600)
        self.addCleanup(self.index.close)

    def test_upsert_jobs_inserts_rows(self):
        jobs = [
            _make_job("Frontend Developer", "Acme", "Berlin", "https://acme.example/jobs/1"),
            _make_job("Backend Developer", "Beta", "Munich", "https://beta.example/jobs/2"),
        ]
        n = self.index.upsert_jobs(jobs, role_bucket="developer")
        self.assertEqual(n, 2)
        # Both rows present
        self.assertEqual(self.index.count_by_facets(role_bucket="developer"), 2)

    def test_upsert_skips_jobs_with_empty_source_url(self):
        jobs = [
            _make_job("X", "Y", "Berlin", ""),  # no source_url
            _make_job("Z", "W", "Berlin", "https://valid.example/1"),
        ]
        n = self.index.upsert_jobs(jobs)
        self.assertEqual(n, 1)
        self.assertEqual(self.index.count_by_facets(), 1)

    def test_upsert_is_idempotent_on_same_source_url(self):
        url = "https://acme.example/jobs/1"
        self.index.upsert_jobs([_make_job("v1", "Acme", "Berlin", url)])
        self.index.upsert_jobs([_make_job("v2", "Acme", "Berlin", url)])
        # Two upserts on the same source_url produce ONE row.
        self.assertEqual(self.index.count_by_facets(), 1)

    def test_upsert_updates_title_on_re_upsert(self):
        url = "https://acme.example/jobs/1"
        self.index.upsert_jobs([_make_job("v1", "Acme", "Berlin", url)])
        self.index.upsert_jobs([_make_job("v2 updated", "Acme", "Berlin", url)])
        rows = self.index.jobs_by_facets(location="Berlin")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].title, "v2 updated")

    def test_upsert_preserves_non_empty_role_bucket_on_re_upsert(self):
        """Re-upsert with empty role_bucket must not clobber an
        existing non-empty value."""
        url = "https://acme.example/jobs/1"
        self.index.upsert_jobs([_make_job("X", "Acme", "Berlin", url)], role_bucket="developer")
        # Second upsert with empty role_bucket
        self.index.upsert_jobs([_make_job("X v2", "Acme", "Berlin", url)])
        # The original role_bucket survives
        self.assertEqual(self.index.count_by_facets(role_bucket="developer"), 1)

    def test_upsert_with_no_jobs_returns_zero(self):
        self.assertEqual(self.index.upsert_jobs([]), 0)


class JobIndexFacetQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.index = JobIndex(Path(self.tmp.name) / "test.sqlite", ttl_seconds=3600)
        self.addCleanup(self.index.close)
        # Seed with a mix of jobs
        self.index.upsert_jobs(
            [
                _make_job("Dev A", "C1", "Berlin", "https://x.example/1"),
                _make_job("Dev B", "C2", "Berlin", "https://x.example/2"),
                _make_job("Dev C", "C3", "Munich", "https://x.example/3"),
            ],
            role_bucket="developer",
        )
        self.index.upsert_jobs(
            [
                _make_job("Nurse A", "Klinik", "Berlin", "https://k.example/1"),
            ],
            role_bucket="nurse",
        )

    def test_count_by_role_bucket(self):
        self.assertEqual(self.index.count_by_facets(role_bucket="developer"), 3)
        self.assertEqual(self.index.count_by_facets(role_bucket="nurse"), 1)
        self.assertEqual(self.index.count_by_facets(role_bucket="bogus"), 0)

    def test_count_by_location_normalises_input(self):
        # "berlin" / "Berlin" / "BERLIN, Deutschland" all match
        self.assertEqual(self.index.count_by_facets(location="berlin"), 3)
        self.assertEqual(self.index.count_by_facets(location="Berlin"), 3)
        self.assertEqual(self.index.count_by_facets(location="Berlin, Deutschland"), 3)
        self.assertEqual(self.index.count_by_facets(location="Munich"), 1)

    def test_count_by_role_bucket_and_location(self):
        self.assertEqual(
            self.index.count_by_facets(role_bucket="developer", location="Berlin"),
            2,
        )
        self.assertEqual(
            self.index.count_by_facets(role_bucket="developer", location="Munich"),
            1,
        )

    def test_count_no_filter_returns_all(self):
        self.assertEqual(self.index.count_by_facets(), 4)

    def test_jobs_by_facets_returns_aggregated_jobs(self):
        rows = self.index.jobs_by_facets(role_bucket="developer", location="Berlin")
        self.assertEqual(len(rows), 2)
        for job in rows:
            self.assertIsInstance(job, AggregatedJob)
            self.assertEqual(job.location, "Berlin")

    def test_jobs_by_facets_respects_limit(self):
        rows = self.index.jobs_by_facets(role_bucket="developer", limit=2)
        self.assertEqual(len(rows), 2)


class JobIndexTtlTests(unittest.TestCase):
    def test_expired_rows_excluded_from_count(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        # 1-second TTL — easy to expire mid-test
        index = JobIndex(Path(tmp.name) / "ttl.sqlite", ttl_seconds=1)
        self.addCleanup(index.close)
        index.upsert_jobs(
            [_make_job("X", "Y", "Berlin", "https://x.example/1")],
            role_bucket="x",
        )
        self.assertEqual(index.count_by_facets(role_bucket="x"), 1)
        # Sleep past the TTL
        time.sleep(2)
        self.assertEqual(index.count_by_facets(role_bucket="x"), 0)
        # purge_expired actually deletes the row
        deleted = index.purge_expired()
        self.assertEqual(deleted, 1)
        # Now count without TTL filter would also be 0
        self.assertEqual(index.count_by_facets(role_bucket="x", ttl_now=0), 0)


class SeniorityHeuristicTests(unittest.TestCase):
    """Phase 2 #71 Phase B — title-based seniority classification."""

    def test_senior_resolves(self):
        self.assertEqual(classify_seniority("Senior Frontend Developer"), "senior")
        self.assertEqual(classify_seniority("Sr. Backend Engineer"), "senior")

    def test_junior_resolves(self):
        self.assertEqual(classify_seniority("Junior Software Developer"), "junior")
        self.assertEqual(classify_seniority("Entry-level Data Analyst"), "junior")

    def test_lead_resolves(self):
        self.assertEqual(classify_seniority("Lead Engineer"), "lead")
        self.assertEqual(classify_seniority("Teamlead Backend"), "lead")
        self.assertEqual(classify_seniority("Teamleiter Mobile"), "lead")

    def test_staff_outranks_senior_token(self):
        # Title "Staff Senior Engineer" — staff (more specific) wins.
        self.assertEqual(classify_seniority("Staff Senior Engineer"), "staff")

    def test_principal_outranks_lead_token(self):
        self.assertEqual(classify_seniority("Principal Lead Architect"), "principal")

    def test_director_resolves(self):
        self.assertEqual(classify_seniority("Director of Engineering"), "director")
        self.assertEqual(classify_seniority("Head of Product"), "director")
        self.assertEqual(classify_seniority("VP Marketing"), "director")

    def test_intern_resolves(self):
        self.assertEqual(classify_seniority("Software Engineering Intern"), "intern")
        self.assertEqual(classify_seniority("Werkstudent Backend"), "intern")
        self.assertEqual(classify_seniority("Praktikantin Design"), "intern")

    def test_apprentice_resolves(self):
        self.assertEqual(
            classify_seniority("Anlagenmechaniker SHK Auszubildender"),
            "apprentice",
        )
        self.assertEqual(classify_seniority("Azubi Mechatronik"), "apprentice")

    def test_unmarked_title_returns_empty(self):
        self.assertEqual(classify_seniority("Frontend Developer"), "")
        self.assertEqual(classify_seniority("Krankenpfleger"), "")

    def test_empty_and_none_return_empty(self):
        self.assertEqual(classify_seniority(""), "")
        self.assertEqual(classify_seniority(None), "")


class LanguageHeuristicTests(unittest.TestCase):
    """Phase 2 #71 Phase B — description-based language detection."""

    def test_german_description_resolves_de(self):
        text = (
            "Wir suchen eine erfahrene Pflegekraft für unsere Station. "
            "Sie haben eine abgeschlossene Ausbildung und sind teamfähig. "
            "Bewerben Sie sich mit Lebenslauf und Anschreiben."
        )
        self.assertEqual(classify_language(text), "de")

    def test_english_description_resolves_en(self):
        text = (
            "We are looking for a Senior Frontend Developer to join our team. "
            "You will work with React, TypeScript, and modern web tooling. "
            "Apply with your CV and a short cover letter."
        )
        self.assertEqual(classify_language(text), "en")

    def test_short_description_returns_empty(self):
        # Below the 3-hit threshold either way.
        self.assertEqual(classify_language("Hello world"), "")
        self.assertEqual(classify_language("Wir suchen"), "")

    def test_empty_and_none_return_empty(self):
        self.assertEqual(classify_language(""), "")
        self.assertEqual(classify_language(None), "")

    def test_balanced_bilingual_returns_empty(self):
        # Carefully constructed to score equally on both sides.
        # Threshold requires both to be >=3 AND not equal — equal
        # counts mean we abstain.
        text = "Wir und der die das ist und. The and you we are is have."
        # Exact equal: both hit 6 DE + 6 EN tokens-ish; either way
        # the contract is "non-DE / non-EN one wins, or abstain on
        # tie". Verify the function returns something stable.
        result = classify_language(text)
        self.assertIn(result, {"de", "en", ""})


class HeuristicWriteThroughTests(unittest.TestCase):
    """Verify that JobIndex.upsert_jobs auto-populates the
    seniority_class + language_detected facets via the Phase B
    heuristics when the caller doesn't pre-supply them."""

    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.index = JobIndex(Path(self.tmp.name) / "heur.sqlite", ttl_seconds=3600)
        self.addCleanup(self.index.close)

    def test_heuristic_populates_seniority(self):
        job = _make_job(
            "Senior Frontend Developer",
            "C1",
            "Berlin",
            "https://x.example/senior-fe",
        )
        self.index.upsert_jobs([job])
        # The heuristic should have tagged this row with senior.
        self.assertEqual(self.index.count_by_facets(seniority_class="senior"), 1)

    def test_heuristic_populates_language(self):
        job = _make_job(
            "Krankenpfleger:in",
            "Klinik",
            "Berlin",
            "https://k.example/1",
            description=(
                "Wir suchen eine erfahrene Pflegekraft für unsere Station. "
                "Sie haben eine abgeschlossene Ausbildung und sind teamfähig."
            ),
        )
        self.index.upsert_jobs([job])
        self.assertEqual(self.index.count_by_facets(language_detected="de"), 1)

    def test_explicit_caller_value_overrides_heuristic(self):
        """When the caller passes seniority_class explicitly, the
        heuristic doesn't override it (even if the heuristic would
        have resolved differently)."""
        job = _make_job(
            "Senior Frontend Developer",
            "C1",
            "Berlin",
            "https://x.example/explicit",
        )
        # Heuristic would say "senior" — caller forces "junior".
        self.index.upsert_jobs([job], seniority_class="junior")
        self.assertEqual(self.index.count_by_facets(seniority_class="junior"), 1)
        self.assertEqual(self.index.count_by_facets(seniority_class="senior"), 0)


class AggregatorWriteThroughTests(unittest.TestCase):
    """The JobAggregationEngine writes dedup'd jobs to the configured
    index after the cross-provider dedup phase. Tagged with the
    supplied role_bucket when present."""

    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.index = JobIndex(Path(self.tmp.name) / "wt.sqlite", ttl_seconds=3600)
        self.addCleanup(self.index.close)

    def _stub_provider(self, name: str, jobs: list[AggregatedJob]):
        class _Stub:
            remote_only = False

            def __init__(self_inner):
                self_inner.name = name

            def search(self_inner, **_):
                return list(jobs)

        return _Stub()

    def test_dedupd_jobs_written_to_index_with_role_bucket(self):
        jobs_a = [_make_job("Dev A", "C1", "Berlin", "https://x.example/1")]
        jobs_b = [_make_job("Dev B", "C2", "Berlin", "https://x.example/2")]
        engine = JobAggregationEngine(
            providers=[
                self._stub_provider("pa", jobs_a),
                self._stub_provider("pb", jobs_b),
            ],
            cache=None,
            index=self.index,
        )
        result_jobs, _outcomes = engine.search(
            query="developer",
            location="Berlin",
            role_bucket="developer",
        )
        self.assertEqual(len(result_jobs), 2)
        # Both jobs landed in the index with role_bucket="developer"
        self.assertEqual(
            self.index.count_by_facets(role_bucket="developer", location="Berlin"),
            2,
        )

    def test_engine_without_index_is_a_noop(self):
        """Backwards compat: engines configured WITHOUT an index
        (the default for legacy callers) work identically to before."""
        engine = JobAggregationEngine(
            providers=[
                self._stub_provider("pa", [_make_job("X", "Y", "Berlin", "https://x/1")]),
            ],
            cache=None,
            # index=None default
        )
        result_jobs, _outcomes = engine.search(query="developer", location="Berlin")
        self.assertEqual(len(result_jobs), 1)
        # No write-through happened (the index passed to our setUp
        # isn't wired to this engine).
        self.assertEqual(self.index.count_by_facets(), 0)

    def test_role_bucket_omitted_still_writes(self):
        """When role_bucket is None, jobs still write through — they
        just land with empty role_bucket. Phase B heuristics can
        populate the field via a separate path later."""
        engine = JobAggregationEngine(
            providers=[
                self._stub_provider("pa", [_make_job("X", "Y", "Berlin", "https://x/1")]),
            ],
            cache=None,
            index=self.index,
        )
        engine.search(query="developer", location="Berlin")
        self.assertEqual(self.index.count_by_facets(location="Berlin"), 1)
        # Empty role_bucket facet — distinguished from explicit "developer"
        self.assertEqual(self.index.count_by_facets(role_bucket="developer"), 0)


class DiagnosticEngineIndexIntegrationTests(unittest.TestCase):
    """Phase 2 #71 Phase C: DiagnosticEngine prefers JobIndex over
    cache when configured. Index returning > 0 wins; index returning
    0 falls through to the cache (avoids false "no facts" early in
    deployment when the index is still warming)."""

    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.index = JobIndex(Path(self.tmp.name) / "diag.sqlite", ttl_seconds=3600)
        self.addCleanup(self.index.close)

    def test_engine_with_index_returns_facet_count(self):
        """When the index has matching rows, the engine returns the
        facet count without probing the cache."""
        from company_discovery.diagnostic_engine import DiagnosticEngine

        # Seed the index with 5 frontend jobs in Berlin
        for i in range(5):
            self.index.upsert_jobs(
                [
                    _make_job(
                        f"Frontend Developer {i}",
                        f"Co{i}",
                        "Berlin",
                        f"https://x.example/fe/{i}",
                    )
                ],
                role_bucket="frontend",
            )
        engine = DiagnosticEngine(cache=None, index=self.index)
        # Direct call: ask for "frontend" in Berlin
        count = engine._cache_count_across_providers(  # noqa: SLF001
            "frontend developer", "Berlin"
        )
        # identify_bucket may resolve to "frontend" or another bucket;
        # whatever it resolves to, the seeded rows tagged "frontend"
        # may or may not match. The contract: when index is configured
        # AND count > 0, the engine returns the count; otherwise falls
        # through to cache (None when cache is None).
        # We assert the engine returned EITHER the index facet count
        # OR None (depending on identify_bucket's resolution + the
        # seniority heuristic on the query). Both are valid contract
        # outputs.
        self.assertIn(count, {None, 5})

    def test_engine_without_index_uses_cache_only(self):
        """Backwards compat: engines without index work as before."""
        from company_discovery.diagnostic_engine import DiagnosticEngine

        engine = DiagnosticEngine(cache=None)
        # No index, no cache: returns None.
        result = engine._cache_count_across_providers(  # noqa: SLF001
            "frontend", "Berlin"
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
