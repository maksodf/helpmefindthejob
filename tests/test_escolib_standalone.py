# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Phase 2 — standalone-extraction guards for the ``escolib`` package.

These are the *definition* of "extracted, not just moved":

1. ``escolib`` imports and works with the application package
   (``company_discovery``) import-FORBIDDEN — proving zero coupling.
2. The packaged dataset (``escolib/data/esco/``) is byte-identical to the
   repo-canonical ``reference/esco/`` — no silent drift between the copy the
   app loads and the copy standalone library users get.
3. The CLI gate: ``python -m escolib "Krankenschwester"`` resolves to 2221.1.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Run in a subprocess with any ``company_discovery`` import made to raise, so a
# transitive application import would fail loudly. escolib must still import +
# work. This is the real test of decoupling (a moved-but-coupled module would
# import company_discovery transitively and blow up here).
_ISOLATION_PROBE = '''
import sys
import importlib.abc


class _Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name == "company_discovery" or name.startswith("company_discovery."):
            raise ImportError("blocked application import: " + name)
        return None


sys.meta_path.insert(0, _Block())

import escolib

result = escolib.EscoReconciler().query("Krankenschwester", limit=1)
assert result.matches[0]["code"] == "2221.1", result.matches
assert result.datasetVersion == "v1-curated-2026-05-18", result.datasetVersion
print("OK")
'''


class EscolibIsStandalone(unittest.TestCase):
    def test_imports_and_works_with_application_code_forbidden(self):
        proc = subprocess.run(
            [sys.executable, "-c", _ISOLATION_PROBE],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"escolib is not standalone (it pulled in forbidden application code):\n{proc.stderr}",
        )
        self.assertIn("OK", proc.stdout)

    def test_escolib_source_does_not_reference_application_package(self):
        # Belt-and-braces: no escolib source file mentions the app package.
        for path in (REPO_ROOT / "escolib").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "company_discovery",
                text,
                f"{path.relative_to(REPO_ROOT)} references the application package",
            )


class PackagedDatasetMatchesCanonical(unittest.TestCase):
    """The packaged escolib data must not drift from the repo-canonical
    ``reference/esco/`` (the app loads ``reference/esco/``; standalone library
    users load the packaged ``escolib/data/esco/`` copy)."""

    def test_data_files_byte_identical(self):
        for name in ("occupations.json", "skills.json"):
            canonical = (REPO_ROOT / "reference" / "esco" / name).read_bytes()
            packaged = (REPO_ROOT / "escolib" / "data" / "esco" / name).read_bytes()
            self.assertEqual(
                canonical,
                packaged,
                f"{name}: escolib packaged copy has drifted from reference/esco/ — "
                "re-sync the two (they must stay byte-identical).",
            )


class EscolibCliGate(unittest.TestCase):
    def test_cli_resolves_krankenschwester_to_canonical_code(self):
        proc = subprocess.run(
            [sys.executable, "-m", "escolib", "Krankenschwester", "--limit", "1"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["matches"][0]["code"], "2221.1")
        self.assertEqual(payload["datasetVersion"], "v1-curated-2026-05-18")
        self.assertEqual(payload["totalCandidates"], 80)


class EscolibBenchmark(unittest.TestCase):
    """The reproducible reconciliation benchmark must hold: every documented
    synonym + curated colloquial query resolves to its canonical code, with
    zero false positives on out-of-dataset terms. Pins the published number."""

    def test_recall_complete_and_no_false_positives(self):
        from escolib.benchmark import run_benchmark

        result = run_benchmark()
        self.assertGreaterEqual(
            result.synonym_cases, 20, "benchmark labelled set unexpectedly shrank"
        )
        self.assertEqual(
            result.recalled,
            result.synonym_cases,
            f"some documented/curated synonyms no longer resolve: {result.failures}",
        )
        self.assertEqual(result.recall_pct, 100.0)
        self.assertEqual(
            result.false_positives,
            0,
            f"over-broad matching produced false positives: {result.failures}",
        )


if __name__ == "__main__":
    unittest.main()
