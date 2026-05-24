# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Docs site quality contract (phase2-backlog #37).

Closes the "no docs site at Stripe/Vercel quality" gap. The
mkdocs config now carries the polish flags that the top-tier
docs sites (Stripe, Vercel, Next.js, Resend) ship by default:

- Stripe-style instant navigation (SPA-like routing with progress
  bar)
- Sticky tabs on scroll
- Section indexes (landing pages for nav sections)
- Search with suggestions + share-deep-links
- Code annotations + cross-page tab sync
- Edit-this-page + view-source actions
- Auto-hiding header
- Dismissible announcement bar
- Mermaid diagram support
- Tabbed content blocks (Python/Curl/JS code-example tabs)
- Magic-link to GitHub issues / PRs

This test pins all the flags as a regression guard so a future
refactor doesn't silently remove the polish.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MKDOCS_CONFIG = REPO_ROOT / "mkdocs.yml"


class MkdocsConfigCarriesPolishFlags(unittest.TestCase):
    def setUp(self):
        self.src = MKDOCS_CONFIG.read_text(encoding="utf-8")

    def test_navigation_polish_flags(self):
        """Stripe-tier nav: tabs.sticky, sections, indexes, path,
        instant + instant.progress, footer, top, tracking."""

        for flag in (
            "navigation.tabs",
            "navigation.tabs.sticky",
            "navigation.sections",
            "navigation.indexes",
            "navigation.path",
            "navigation.instant",
            "navigation.instant.progress",
            "navigation.footer",
            "navigation.top",
            "navigation.tracking",
        ):
            with self.subTest(flag=flag):
                self.assertIn(flag, self.src)

    def test_search_polish_flags(self):
        for flag in ("search.suggest", "search.highlight", "search.share"):
            with self.subTest(flag=flag):
                self.assertIn(flag, self.src)

    def test_content_polish_flags(self):
        for flag in (
            "content.code.copy",
            "content.code.annotate",
            "content.tabs.link",
            "content.action.edit",
            "content.action.view",
            "content.tooltips",
        ):
            with self.subTest(flag=flag):
                self.assertIn(flag, self.src)

    def test_chrome_polish_flags(self):
        """Header autohide + announcement-dismiss + toc.follow."""

        for flag in ("header.autohide", "announce.dismiss", "toc.follow"):
            with self.subTest(flag=flag):
                self.assertIn(flag, self.src)


class MkdocsExtensionsExpanded(unittest.TestCase):
    def setUp(self):
        self.src = MKDOCS_CONFIG.read_text(encoding="utf-8")

    def test_pymdownx_extensions(self):
        for ext in (
            "pymdownx.tabbed",  # code-example tabs
            "pymdownx.snippets",  # file inclusion
            "pymdownx.tasklist",  # task lists
            "pymdownx.emoji",
            "pymdownx.keys",  # keyboard shortcuts
            "pymdownx.mark",  # ==highlighted==
            "pymdownx.tilde",  # ~~strike~~
            "pymdownx.caret",  # ^^insert^^
            "pymdownx.smartsymbols",
            "pymdownx.magiclink",  # auto-link GitHub URLs
            "pymdownx.critic",  # critic-markup diff
            "pymdownx.betterem",  # better emphasis
            "pymdownx.inlinehilite",
        ):
            with self.subTest(ext=ext):
                self.assertIn(ext, self.src)

    def test_core_extensions(self):
        for ext in ("admonition", "attr_list", "footnotes", "def_list", "abbr"):
            with self.subTest(ext=ext):
                self.assertIn(ext, self.src)

    def test_mermaid_support(self):
        """Mermaid superfence for architecture / sequence diagrams."""

        self.assertIn("mermaid", self.src)
        self.assertIn("custom_fences", self.src)

    def test_magiclink_configured_with_repo(self):
        """The shorthand auto-link feature needs user + repo names
        to expand `#123` → GitHub issue link."""

        self.assertIn("user: maksodf", self.src)
        self.assertIn("repo: helpmefindthejob", self.src)


class MkdocsStrictBuildPasses(unittest.TestCase):
    """The strict build catches broken links + missing pages. This
    test runs the actual `mkdocs build --strict` so regressions
    surface in CI."""

    def test_strict_build_succeeds(self):
        # mkdocs lives in requirements-dev.txt (not in the runtime
        # requirements.txt the CI test.yml installs). Skip rather
        # than fail when mkdocs is unavailable — the dedicated
        # docs-publish.yml workflow runs `mkdocs build --strict`
        # under its own installation and is the authoritative
        # signal for docs-site-build correctness. This unit-test
        # belt remains useful locally (where the dev environment
        # has mkdocs) and on any future test.yml expansion that
        # adopts the dev requirements.
        import importlib.util

        if importlib.util.find_spec("mkdocs") is None:
            self.skipTest(
                "mkdocs not installed (test.yml installs requirements.txt "
                "only; docs-publish.yml workflow handles the strict-build "
                "check under its own dev-deps installation)"
            )

        result = subprocess.run(
            ["python", "-m", "mkdocs", "build", "--strict"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        # If strict mode aborts, the return code is non-zero. The
        # informational links to grant/* (excluded by design) are
        # logged at INFO level, not WARNING, so they don't trip
        # strict mode.
        self.assertEqual(
            result.returncode,
            0,
            f"mkdocs build --strict failed:\nSTDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}",
        )


class StatusOverlaysSupported(unittest.TestCase):
    """`extra.status` enables `status: new` / `status: deprecated`
    page front-matter for visually flagging surfaces."""

    def setUp(self):
        self.src = MKDOCS_CONFIG.read_text(encoding="utf-8")

    def test_status_section_present(self):
        self.assertIn("status:", self.src)
        self.assertIn("new:", self.src)
        self.assertIn("deprecated:", self.src)


if __name__ == "__main__":
    unittest.main()
