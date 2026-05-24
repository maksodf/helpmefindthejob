# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Contract tests for company_discovery.city_adjacency + the
JobIndex.count_with_adjacent_cities integration (Phase 2 #71 Phase
D / #74 substrate)."""

from __future__ import annotations

import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.aggregators import AggregatedJob
from company_discovery.city_adjacency import (
    AdjacencyEdge,
    adjacent_cities,
    all_known_cities,
    edge_count,
    neighbour_keys,
)
from company_discovery.job_index import JobIndex


class CityAdjacencyGraph(unittest.TestCase):
    def test_edge_count_is_substantial(self) -> None:
        # We curated >= 40 edges across DACH metro areas. Lower
        # than 30 would mean the table is too sparse to deliver on
        # the #74 promise.
        self.assertGreaterEqual(edge_count(), 40)

    def test_known_cities_includes_seven_top_dach_metros(self) -> None:
        known = set(all_known_cities())
        for c in (
            "berlin",
            "hamburg",
            "munchen",
            "koln",
            "frankfurt",
            "stuttgart",
            "leipzig",
        ):
            self.assertIn(c, known, f"{c!r} missing from adjacency graph")

    def test_adjacent_cities_returns_symmetric_edges(self) -> None:
        # The spec example: Berlin ↔ Halle is NOT directly adjacent
        # in our graph (too far for daily commute) — instead Berlin
        # ↔ Potsdam and Leipzig ↔ Halle are the curated edges.
        # Verify symmetry on a real edge.
        b_edges = {(e.a, e.b) for e in adjacent_cities("berlin")}
        p_edges = {(e.a, e.b) for e in adjacent_cities("potsdam")}
        self.assertTrue(
            any("potsdam" in pair for pair in b_edges),
            "Berlin should list Potsdam as a neighbour",
        )
        self.assertTrue(
            any("berlin" in pair for pair in p_edges),
            "Potsdam should list Berlin as a neighbour (symmetric)",
        )

    def test_normalisation_handles_accents_and_case(self) -> None:
        # München → munchen, Köln → koln; both should resolve to
        # the curated keys.
        munchen = adjacent_cities("München")
        koln = adjacent_cities("Köln")
        self.assertGreater(len(munchen), 0, "München should normalise to munchen")
        self.assertGreater(len(koln), 0, "Köln should normalise to koln")

    def test_max_minutes_filter_drops_far_edges(self) -> None:
        # Berlin↔Brandenburg is ~65 min; restricting to 45 should
        # drop it but keep the 30-min Potsdam edge.
        all_berlin = neighbour_keys("berlin")
        within_45 = neighbour_keys("berlin", max_minutes=45)
        self.assertIn("potsdam", within_45)
        self.assertIn("brandenburg", all_berlin)
        self.assertNotIn("brandenburg", within_45)

    def test_unknown_city_yields_empty_tuple(self) -> None:
        self.assertEqual(adjacent_cities("Atlantis"), ())
        self.assertEqual(neighbour_keys("Atlantis"), ())
        self.assertEqual(adjacent_cities(None), ())
        self.assertEqual(neighbour_keys(""), ())

    def test_neighbour_keys_excludes_source_city(self) -> None:
        # Self-loop guard: if the curator accidentally adds an
        # edge (X, X), neighbour_keys must not return X for X.
        for city in all_known_cities():
            nks = neighbour_keys(city)
            self.assertNotIn(city, nks, f"{city!r} should not be its own neighbour")

    def test_edges_carry_minutes_and_mode(self) -> None:
        for e in adjacent_cities("frankfurt"):
            self.assertIsInstance(e, AdjacencyEdge)
            self.assertIsInstance(e.minutes, int)
            self.assertGreater(e.minutes, 0)
            self.assertLessEqual(e.minutes, 120)
            self.assertIn(e.mode, {"S-Bahn", "RE/IC", "ICE", "U-Bahn", "mixed"})


class JobIndexAdjacencyIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.index = JobIndex(Path(self.tmp.name) / "idx.sqlite3")
        self.addCleanup(self.index.close)

    def _seed(self, jobs: list[AggregatedJob]) -> None:
        self.index.upsert_jobs(jobs)

    def _job(self, url: str, title: str, location: str) -> AggregatedJob:
        return AggregatedJob(
            title=title,
            company_name="Test GmbH",
            source="test",
            source_url=url,
            location=location,
            description=title,
        )

    def test_same_city_only_when_no_adjacency_data(self) -> None:
        self._seed(
            [
                self._job("https://e.x/1", "Dev", "Berlin"),
                self._job("https://e.x/2", "Dev", "Berlin"),
                self._job("https://e.x/3", "Dev", "Munich"),
            ]
        )
        out = self.index.count_with_adjacent_cities(location="Berlin")
        self.assertEqual(out["city_count"], 2)
        # Berlin neighbours don't exist in index → counts are 0
        self.assertGreater(len(out["adjacent"]), 0)
        self.assertTrue(all(a["count"] == 0 for a in out["adjacent"]))

    def test_aggregates_across_adjacent_cities(self) -> None:
        # Spec-grade example: Leipzig ↔ Halle, both with postings
        self._seed(
            [
                self._job("https://e.x/L1", "Pflege", "Leipzig"),
                self._job("https://e.x/L2", "Pflege", "Leipzig"),
                self._job("https://e.x/L3", "Pflege", "Leipzig"),
                self._job("https://e.x/H1", "Pflege", "Halle"),
                self._job("https://e.x/H2", "Pflege", "Halle"),
                self._job("https://e.x/X1", "Pflege", "Munich"),
            ]
        )
        out = self.index.count_with_adjacent_cities(location="Leipzig")
        self.assertEqual(out["city"], "leipzig")
        self.assertEqual(out["city_count"], 3)
        halle = next((a for a in out["adjacent"] if a["city"] == "halle"), None)
        self.assertIsNotNone(halle)
        self.assertEqual(halle["count"], 2)
        self.assertEqual(halle["minutes"], 25)
        self.assertEqual(halle["mode"], "S-Bahn")
        # Total is the spec-promised aggregate: same-city + adjacent
        # postings (3 Leipzig + 2 Halle = 5, plus any other empty
        # neighbours from the graph)
        self.assertGreaterEqual(out["total_with_adjacent"], 5)

    def test_max_minutes_filter_drops_distant_neighbour(self) -> None:
        # Berlin↔Brandenburg is 65 min; with max_minutes=45 it
        # should not appear in the adjacent list.
        self._seed(
            [
                self._job("https://e.x/B1", "Dev", "Berlin"),
                self._job("https://e.x/B2", "Dev", "Brandenburg"),
            ]
        )
        out = self.index.count_with_adjacent_cities(location="Berlin", max_minutes=45)
        adjacent_cities_in_result = {a["city"] for a in out["adjacent"]}
        self.assertNotIn("brandenburg", adjacent_cities_in_result)
        self.assertIn("potsdam", adjacent_cities_in_result)

    def test_unknown_city_returns_empty_adjacent(self) -> None:
        self._seed([self._job("https://e.x/1", "Dev", "Atlantis")])
        out = self.index.count_with_adjacent_cities(location="Atlantis")
        self.assertEqual(out["adjacent"], [])
        # city_count still works on the normalised key
        self.assertEqual(out["city_count"], 1)
        self.assertEqual(out["total_with_adjacent"], 1)

    def test_munich_munchen_alias_unifies_counts(self) -> None:
        """Phase 2 #74 alias fix (2026-05-21): a job posting using
        English "Munich" and another using German "München" must be
        counted as the SAME city. Without alias resolution, the
        index would split them into "munich" vs "munchen" and
        adjacency lookups for one would miss the other.
        """
        self._seed(
            [
                self._job("https://e.x/M1", "Software", "Munich"),
                self._job("https://e.x/M2", "Software", "München"),
                self._job("https://e.x/M3", "Software", "Muenchen"),  # oe-form
                self._job("https://e.x/A1", "Software", "Augsburg"),
            ]
        )
        # Query for either spelling should aggregate all 3 Munich postings
        out_en = self.index.count_with_adjacent_cities(location="Munich")
        out_de = self.index.count_with_adjacent_cities(location="München")
        self.assertEqual(out_en["city_count"], 3)
        self.assertEqual(out_de["city_count"], 3)
        # Augsburg is an adjacent city in our graph (40 min RE/IC)
        augsburg_en = next((a for a in out_en["adjacent"] if a["city"] == "augsburg"), None)
        augsburg_de = next((a for a in out_de["adjacent"] if a["city"] == "augsburg"), None)
        self.assertIsNotNone(augsburg_en)
        self.assertIsNotNone(augsburg_de)
        self.assertEqual(augsburg_en["count"], 1)
        self.assertEqual(augsburg_de["count"], 1)

    def test_cologne_koln_alias_unifies_counts(self) -> None:
        """Same as Munich test but for Köln/Cologne — second-most-
        common EN-spelling-vs-DE-spelling case."""
        self._seed(
            [
                self._job("https://e.x/K1", "Dev", "Cologne"),
                self._job("https://e.x/K2", "Dev", "Köln"),
                self._job("https://e.x/B1", "Dev", "Bonn"),
            ]
        )
        out = self.index.count_with_adjacent_cities(location="Cologne")
        self.assertEqual(out["city_count"], 2)
        bonn = next((a for a in out["adjacent"] if a["city"] == "bonn"), None)
        self.assertIsNotNone(bonn)
        self.assertEqual(bonn["count"], 1)

    def test_default_call_aggregates_all_role_buckets(self) -> None:
        # No filter on role_bucket: every posting should count.
        self._seed(
            [
                self._job("https://e.x/L1", "Krankenpflegerin Geriatrie", "Leipzig"),
                self._job("https://e.x/L2", "Senior Developer", "Leipzig"),
                self._job("https://e.x/H1", "Pflegehelferin", "Halle"),
                self._job("https://e.x/H2", "Marketing Manager", "Halle"),
            ]
        )
        all_out = self.index.count_with_adjacent_cities(location="Leipzig")
        self.assertEqual(all_out["city_count"], 2)
        halle_all = next(a for a in all_out["adjacent"] if a["city"] == "halle")
        self.assertEqual(halle_all["count"], 2)
        self.assertGreaterEqual(all_out["total_with_adjacent"], 4)


if __name__ == "__main__":
    unittest.main()
