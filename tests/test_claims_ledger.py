# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Phase 8 — the claims ledger is honest + non-dangling.

claims-ledger.json maps every headline claim to (a) the committed artefact that
backs it, (b) the test that asserts it, and (c) the one command a stranger runs
to verify it. This test is the ledger's own gate:

1. Every cited artefact + asserting-test file exists.
2. Every ``oneCommand`` points at something real (a package/module/script in the
   repo) — so the "run this to verify" promise can't dangle.
3. The asserting tests are real test modules.
4. Human-track items (real users, external audit, co-maintainers, partners,
   third-party adoption) stay ``not-built`` — code cannot mark them done, and
   this gate fails loudly if someone tries (the integrity spine, enforced).
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_LEDGER_PATH = REPO_ROOT / "claims-ledger.json"


def _ledger() -> dict:
    return json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))


def _command_target_exists(command: str) -> bool:
    """Does the thing ``command`` invokes exist in the repo?"""
    parts = command.split()
    if not parts:
        return False
    # `python -m MODULE [...]`  (and `python -m unittest tests.MODULE`)
    if parts[0] in ("python", "python3") and len(parts) >= 3 and parts[1] == "-m":
        target = parts[3] if parts[2] == "unittest" and len(parts) >= 4 else parts[2]
        rel = target.replace(".", "/")
        candidates = [
            REPO_ROOT / rel,
            REPO_ROOT / f"{rel}.py",
            REPO_ROOT / rel / "__init__.py",
            REPO_ROOT / rel / "__main__.py",
        ]
        return any(c.exists() for c in candidates)
    # `./scripts/foo.sh` or `scripts/foo.sh`
    script = parts[0].lstrip("./")
    return (REPO_ROOT / script).exists()


class LedgerStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ledger = _ledger()

    def test_has_buildable_claims_and_human_track(self):
        self.assertGreaterEqual(len(self.ledger["buildableClaims"]), 8)
        self.assertGreaterEqual(len(self.ledger["humanTrackItems"]), 4)

    def test_every_claim_has_required_fields(self):
        for claim in self.ledger["buildableClaims"]:
            for key in ("id", "dimension", "claim", "artifacts", "assertingTests", "oneCommand"):
                self.assertIn(key, claim, f"claim missing {key!r}: {claim.get('id')}")
            self.assertTrue(claim["artifacts"])
            self.assertTrue(claim["assertingTests"])

    def test_claim_ids_unique(self):
        ids = [c["id"] for c in self.ledger["buildableClaims"]]
        self.assertEqual(len(ids), len(set(ids)), f"duplicate claim ids: {ids}")


class EveryClaimIsBacked(unittest.TestCase):
    def test_artefacts_and_tests_exist(self):
        missing: list[str] = []
        for claim in _ledger()["buildableClaims"]:
            for rel in list(claim["artifacts"]) + list(claim["assertingTests"]):
                if not (REPO_ROOT / rel).exists():
                    missing.append(f"{claim['id']} -> {rel}")
        self.assertEqual(missing, [], f"ledger cites missing files: {missing}")

    def test_one_commands_point_at_something_real(self):
        dangling = [
            f"{c['id']}: {c['oneCommand']}"
            for c in _ledger()["buildableClaims"]
            if not _command_target_exists(c["oneCommand"])
        ]
        self.assertEqual(dangling, [], f"ledger one-commands dangle: {dangling}")

    def test_asserting_tests_are_test_modules(self):
        for claim in _ledger()["buildableClaims"]:
            for test_path in claim["assertingTests"]:
                self.assertTrue(
                    test_path.startswith("tests/") and test_path.endswith(".py"),
                    f"{claim['id']} asserting test is not a test module: {test_path}",
                )


class HumanTrackStaysHonest(unittest.TestCase):
    def test_human_track_items_are_all_not_built(self):
        # The integrity spine: code cannot produce real users / external audit /
        # co-maintainers / partners / third-party adoption. If a future edit
        # flips one to "built", this fails — keeping the application honest.
        for item in _ledger()["humanTrackItems"]:
            self.assertEqual(
                item["status"],
                "not-built",
                f"human-track item claims built status: {item['item']}",
            )
            self.assertEqual(item.get("owner"), "operator")


if __name__ == "__main__":
    unittest.main()
