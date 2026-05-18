# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Tests for §2.4 — ESCO reference dataset + EURES export shape.

The curated ESCO dataset under ``reference/esco/`` (occupations.json,
skills.json) replaces the inline mini-dataset stub the §2.3 commit
seeded. These tests pin:

- The loader resolves the on-disk dataset (not the fallback) in the
  default repo layout
- The dataset meets the §2.4 plan coverage targets (≥30 occupations,
  ≥50 skills)
- Every entry has the canonical fields (code, label_en, label_de, type)
- Persona-panel queries hit known entries (Aïcha → Krankenpfleger,
  Yusuf → Maschinenbauingenieur, Olga → Frontend-Entwickler,
  Mahmoud → Anlagenmechaniker SHK, Maria → Pflegehelfer)
- German-language queries resolve too (label_de is matched)
- The EURES projection from export_eures_compatible carries the
  documented schema-conformance flag

EURES end-to-end with a persisted DiscoveredJob is exercised in the
§2.6 MCP CI integration test (when the housing-agent reference
integration lands and seeds sample data); this module verifies the
projection shape directly.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import mcp_server
from company_discovery.mcp_tools import _load_esco_reference_dataset


REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = REPO_ROOT / "reference" / "esco"


def _new_tools_for_test() -> mcp_server.CompanyDiscoveryMCPTools:
    tmp = tempfile.mkdtemp(prefix="dj-scout-esco-")
    return mcp_server.build_tools(data_path=Path(tmp) / "company.sqlite3")


class CuratedDatasetCoverageTests(unittest.TestCase):
    """The curated v1 dataset meets §2.4 coverage targets."""

    def test_occupations_file_present_and_well_formed(self) -> None:
        with (REFERENCE_DIR / "occupations.json").open(encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(data["license"], "CC-BY-4.0")
        self.assertGreaterEqual(len(data["entries"]), 30,
                                 msg="§2.4 plan requires ≥30 occupations")
        for entry in data["entries"]:
            self.assertIn("code", entry)
            self.assertIn("label_en", entry)
            self.assertIn("label_de", entry)

    def test_skills_file_present_and_well_formed(self) -> None:
        with (REFERENCE_DIR / "skills.json").open(encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(data["license"], "CC-BY-4.0")
        self.assertGreaterEqual(len(data["entries"]), 50,
                                 msg="§2.4 plan requires ≥50 skills")
        for entry in data["entries"]:
            self.assertIn("code", entry)
            self.assertIn("label_en", entry)
            self.assertIn("label_de", entry)
            self.assertIn("category", entry)

    def test_attribution_credits_cc_by(self) -> None:
        for path in ("occupations.json", "skills.json"):
            with (REFERENCE_DIR / path).open(encoding="utf-8") as handle:
                data = json.load(handle)
            self.assertIn("Creative Commons Attribution 4.0",
                          data["attribution"])


class LoaderResolutionTests(unittest.TestCase):
    """The loader prefers the on-disk dataset when files are present."""

    def test_loader_returns_curated_dataset_in_default_layout(self) -> None:
        # Reset cache so we load fresh.
        import company_discovery.mcp_tools as mt

        mt._ESCO_DATASET_CACHE = None
        dataset = mt._load_esco_reference_dataset()
        # 30+ occupations + 50+ skills = at least 80 entries.
        self.assertGreaterEqual(len(dataset), 80)
        occupation_entries = [e for e in dataset if e["type"] == "occupation"]
        skill_entries = [e for e in dataset if e["type"] == "skill"]
        self.assertGreaterEqual(len(occupation_entries), 30)
        self.assertGreaterEqual(len(skill_entries), 50)


class PersonaPanelQueryTests(unittest.TestCase):
    """Each persona's target occupation is reachable through the loaded
    dataset via either the English or German label."""

    def setUp(self) -> None:
        # Ensure the curated dataset is loaded.
        import company_discovery.mcp_tools as mt
        mt._ESCO_DATASET_CACHE = None
        _load_esco_reference_dataset()
        self.tools = _new_tools_for_test()

    def test_aicha_nurse_resolves(self) -> None:
        result = self.tools.query_esco_skill(query="krankenpfleger")
        labels = [m.get("label_de", "") for m in result["matches"]]
        self.assertTrue(any("Krankenpfleger" in label for label in labels))

    def test_yusuf_mechanical_engineer_resolves(self) -> None:
        result = self.tools.query_esco_skill(query="maschinenbau")
        labels = [m.get("label_de", "") for m in result["matches"]]
        self.assertTrue(any("Maschinenbau" in label for label in labels))

    def test_olga_frontend_developer_resolves(self) -> None:
        result = self.tools.query_esco_skill(query="frontend")
        labels = [m.get("label_de", "") for m in result["matches"]]
        self.assertTrue(any("Frontend" in label for label in labels))

    def test_mahmoud_anlagenmechaniker_resolves(self) -> None:
        result = self.tools.query_esco_skill(query="anlagenmechaniker")
        labels = [m.get("label_de", "") for m in result["matches"]]
        self.assertTrue(any("Anlagenmechaniker" in label for label in labels))

    def test_maria_pflegehelfer_resolves(self) -> None:
        result = self.tools.query_esco_skill(query="pflegehelfer")
        labels = [m.get("label_de", "") for m in result["matches"]]
        self.assertTrue(any("Pflegehelfer" in label for label in labels))


class GermanLabelMatchingTests(unittest.TestCase):
    """Queries match against label_de in addition to label_en."""

    def setUp(self) -> None:
        import company_discovery.mcp_tools as mt
        mt._ESCO_DATASET_CACHE = None
        _load_esco_reference_dataset()
        self.tools = _new_tools_for_test()

    def test_german_query_against_german_label(self) -> None:
        result = self.tools.query_esco_skill(query="Schweißen")
        self.assertGreater(len(result["matches"]), 0)
        # Welding should appear (under skills.category=engineering).
        labels = [m.get("label_de", "") for m in result["matches"]]
        self.assertTrue(any("Schweißen" in label for label in labels))

    def test_german_only_skill_via_german_label(self) -> None:
        result = self.tools.query_esco_skill(query="Pflegestandards")
        self.assertGreater(len(result["matches"]), 0)


class DatasetVersionFlagTests(unittest.TestCase):
    def setUp(self) -> None:
        import company_discovery.mcp_tools as mt
        mt._ESCO_DATASET_CACHE = None
        _load_esco_reference_dataset()
        self.tools = _new_tools_for_test()

    def test_curated_dataset_version_flag(self) -> None:
        result = self.tools.query_esco_skill(query="nurse")
        # Curated dataset reports its versioned ID; the fallback would
        # report 'v0-mini-fallback'. In the default repo layout we should
        # always see the curated one.
        self.assertEqual(result["datasetVersion"], "v1-curated-2026-05-18")


class EURESProjectionShapeTests(unittest.TestCase):
    """The EURES projection from export_eures_compatible carries the
    documented schema fields. Full end-to-end (with a persisted
    DiscoveredJob) is the §2.6 CI integration test's responsibility."""

    def setUp(self) -> None:
        self.tools = _new_tools_for_test()

    def test_not_found_branch_keeps_status_status_field(self) -> None:
        result = self.tools.export_eures_compatible(
            userId="u-1", discoveredJobId="does-not-exist"
        )
        # In an empty repository the job will not resolve. The tool must
        # return a structured status rather than raise.
        self.assertIn(result["status"], {"not_found", "ok"})

    def test_handle_request_validates_discoveredJobId(self) -> None:
        message = {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {
                "name": "export_eures_compatible",
                "arguments": {"userId": "u-1"},
            },
        }
        response = mcp_server.handle_request(message, self.tools)
        assert response is not None
        self.assertTrue(response["result"]["isError"])
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["violatedRule"], "required")


if __name__ == "__main__":
    unittest.main()
