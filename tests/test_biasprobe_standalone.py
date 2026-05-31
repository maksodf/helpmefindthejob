# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Phase 4 — standalone-extraction guards for the ``biasprobe`` package.

The definition of "extracted, not just moved":

1. ``biasprobe`` imports + replays + renders with the application package
   (``company_discovery``) import-FORBIDDEN — proving zero code coupling. (Its
   default report *prose* names the reference setup's modules, which is text,
   not an import — the source check below targets import statements only.)
2. The bundled caches (``biasprobe/data/``) are byte-identical to the canonical
   ``data/bias_comparative_cache/`` and are git-tracked — so a fresh clone
   reproduces the published numbers and the two copies never drift silently.
3. The CLI gate: ``python -m biasprobe`` renders the comparative report offline.
"""

from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Subprocess probe: block every ``company_discovery`` import, then drive the full
# biasprobe replay/metrics/report surface. A moved-but-coupled module would pull
# the application package in transitively and fail loudly here.
_ISOLATION_PROBE = """
import sys
import importlib.abc


class _Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name == "company_discovery" or name.startswith("company_discovery."):
            raise ImportError("blocked application import: " + name)
        return None


sys.meta_path.insert(0, _Block())

import biasprobe

cache_dir = biasprobe.DEFAULT_CACHE_DIR
providers = biasprobe.discover_providers(cache_dir)
assert providers, "no bundled caches discovered"

by_provider = {}
summaries = []
for pid in providers:
    outcomes = list(biasprobe.load_outcomes(cache_dir, pid).values())
    assert outcomes, "empty cache for " + pid
    by_provider[pid] = outcomes
    summaries.append(biasprobe.summarize(pid, outcomes))

md = biasprobe.render_markdown(by_provider, summaries)
assert "# Bias-methodology comparative report" in md
for pid in providers:
    assert pid in md, pid

means = biasprobe.per_persona_mean(by_provider[providers[0]])
assert means, "per_persona_mean produced nothing without the application"
disagreement = biasprobe.cross_provider_disagreement(by_provider)
assert isinstance(disagreement, list)
print("OK")
"""


class BiasprobeIsStandalone(unittest.TestCase):
    def test_imports_and_works_with_application_code_forbidden(self):
        proc = subprocess.run(
            [sys.executable, "-c", _ISOLATION_PROBE],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"biasprobe is not standalone (it pulled in forbidden application code):\n{proc.stderr}",
        )
        self.assertIn("OK", proc.stdout)

    def test_biasprobe_source_does_not_import_application_package(self):
        # The real coupling is an import statement. Report *prose* may name the
        # reference run's modules (that's describing how the cached data was made).
        import_re = re.compile(r"^\s*(?:from|import)\s+company_discovery\b", re.MULTILINE)
        for path in (REPO_ROOT / "biasprobe").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(
                import_re.search(text),
                f"{path.relative_to(REPO_ROOT)} imports the application package — not standalone",
            )


class PackagedCachesMatchCanonical(unittest.TestCase):
    """The bundled biasprobe caches must not drift from the canonical
    ``data/bias_comparative_cache/`` (the live runner writes the canonical copy;
    standalone ``python -m biasprobe`` users read the packaged copy)."""

    CACHES = ("deepseek.jsonl", "ollama.jsonl")

    def test_bundled_caches_byte_identical_to_canonical(self):
        for name in self.CACHES:
            canonical = (REPO_ROOT / "data" / "bias_comparative_cache" / name).read_bytes()
            packaged = (REPO_ROOT / "biasprobe" / "data" / name).read_bytes()
            self.assertEqual(
                canonical,
                packaged,
                f"{name}: biasprobe/data/ has drifted from data/bias_comparative_cache/ — "
                "re-sync the two (they must stay byte-identical).",
            )

    def test_bundled_caches_are_git_tracked(self):
        if not (REPO_ROOT / ".git").exists():
            self.skipTest("not a git checkout (e.g. installed sdist) — cannot verify tracking")
        result = subprocess.run(
            ["git", "ls-files", "biasprobe/data/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        tracked = {line.strip() for line in result.stdout.splitlines() if line.strip()}
        for name in self.CACHES:
            rel = f"biasprobe/data/{name}"
            self.assertIn(
                rel,
                tracked,
                f"{rel} present but NOT git-tracked — it will be absent on a fresh clone "
                f"and `python -m biasprobe` will have no data. Re-include it in .gitignore.",
            )


class BiasprobeCliGate(unittest.TestCase):
    def test_cli_renders_report_offline(self):
        proc = subprocess.run(
            [sys.executable, "-m", "biasprobe"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("# Bias-methodology comparative report", proc.stdout)
        self.assertIn("## Top 20 highest-disagreement cells", proc.stdout)
        self.assertIn("deepseek", proc.stdout)
        self.assertIn("ollama", proc.stdout)


if __name__ == "__main__":
    unittest.main()
