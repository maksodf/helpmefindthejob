# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Phase 7 — machine-checkable compliance traceability.

The compliance pack claims, per EU AI Act / GDPR article, that an evidence
artefact exists. ``compliance/starter-kit/kit-manifest.json`` is the
machine-readable article→artefact matrix; these tests turn every claim into a
build gate:

1. Every artefact + code reference the manifest cites MUST exist on disk — a
   deleted or renamed file breaks the build here, not silently in front of a
   reviewer (the Artifact-Backing Rule for the compliance surface).
2. ``code-wired`` entries MUST carry at least one code reference (the claim that
   running code backs the article cannot be made without naming the code).
3. The manifest MUST NOT drift from ``compliance/INDEX.md``'s article-to-file
   reverse lookup — every article one documents, the other documents too.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_MANIFEST_PATH = REPO_ROOT / "compliance" / "starter-kit" / "kit-manifest.json"
_INDEX_PATH = REPO_ROOT / "compliance" / "INDEX.md"
_VALID_STATUS = {"code-wired", "template", "doc"}


def _manifest() -> dict:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


class ManifestStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.articles = _manifest()["articles"]

    def test_manifest_is_non_trivial(self):
        self.assertGreaterEqual(len(self.articles), 16)

    def test_every_entry_has_required_fields(self):
        for entry in self.articles:
            for key in ("regulation", "article", "title", "status", "artifacts"):
                self.assertIn(key, entry, f"entry missing {key!r}: {entry}")
            self.assertIn(entry["status"], _VALID_STATUS, f"bad status: {entry}")
            self.assertTrue(entry["artifacts"], f"entry cites no artefact: {entry}")

    def test_code_wired_entries_name_their_code(self):
        for entry in self.articles:
            if entry["status"] == "code-wired":
                self.assertTrue(
                    entry.get("codeRefs"),
                    f"{entry['regulation']} Art.{entry['article']} is 'code-wired' but "
                    "names no codeRefs — an unbacked code claim",
                )


class TraceabilityArtifactsExist(unittest.TestCase):
    """The gate: every cited artefact + code ref must exist."""

    def test_every_cited_path_exists(self):
        missing: list[str] = []
        for entry in _manifest()["articles"]:
            cited = list(entry["artifacts"]) + list(entry.get("codeRefs", []))
            for rel in cited:
                if not (REPO_ROOT / rel).exists():
                    missing.append(f"{entry['regulation']} Art.{entry['article']} -> {rel}")
        self.assertEqual(missing, [], f"manifest cites missing artefacts: {missing}")


class ManifestMatchesIndex(unittest.TestCase):
    """Drift guard between the manifest and INDEX.md's reverse lookup."""

    @staticmethod
    def _index_articles() -> set[tuple[str, str]]:
        text = _INDEX_PATH.read_text(encoding="utf-8")
        section = text.split("## Article-to-file reverse lookup", 1)[-1]
        return set(re.findall(r"(AI Act|GDPR) \| Article (\d+)", section))

    @staticmethod
    def _manifest_articles() -> set[tuple[str, str]]:
        return {(e["regulation"], e["article"]) for e in _manifest()["articles"]}

    def test_no_drift_between_manifest_and_index(self):
        index = self._index_articles()
        manifest = self._manifest_articles()
        self.assertEqual(
            manifest,
            index,
            f"manifest↔INDEX drift — manifest-only={sorted(manifest - index)}, "
            f"index-only={sorted(index - manifest)}",
        )

    def test_index_reverse_lookup_was_actually_found(self):
        # guard against a silent regex/parse break that would make the drift
        # check vacuously pass
        self.assertGreater(len(self._index_articles()), 10)


if __name__ == "__main__":
    unittest.main()
