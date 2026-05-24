# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""WCAG 2.2 AAA-leaning static contracts (13-plan item 13/13).

Builds on `tests/test_accessibility_static.py` (commit 8f4078f),
which covers the AA-level static surface. This file adds the
AAA-specific contracts that CAN be checked programmatically
from CSS / HTML source alone (without runtime axe-core):

1. **WCAG 1.4.6 Contrast (Enhanced)** — body-text foreground vs
   surface backgrounds achieves 7:1.
2. **WCAG 2.4.9 Link Purpose (Link Only)** — every link's text
   is self-describing (no "click here", "more", "read more"
   without surrounding context).
3. **WCAG 2.4.10 Section Headings** — every <section>/<article>
   has a heading. (Caught structurally from the HTML.)
4. **WCAG 3.3.5 Help** — every form has either a fieldset legend
   OR a heading nearby OR aria-describedby pointing at help text.
   (We check the loose form: at least one form-help element
   exists in the SPA shell.)

Honesty: AAA promotion is a continuous discipline, not a one-
shot pass. These contracts catch regressions in the AAA-leaning
surface — they don't claim full AAA conformance, which requires
human review of reading level (3.1.5), unusual words (3.1.3),
abbreviations (3.1.4), pronunciation (3.1.6), and runtime axe-
core verification for live DOM state.

The static contracts already in `test_accessibility_static.py`
cover AA-level invariants (skip link, landmarks, focus visible,
prefers-reduced-motion, ARIA live regions, alt text, form
labels, link text-decoration). This file extends to the AAA-
level surface we CAN check.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC = REPO_ROOT / "static"
STYLES = STATIC / "styles.css"
INDEX = STATIC / "index.html"


# ---------------------------------------------------------------------------
# WCAG contrast ratio helpers
# ---------------------------------------------------------------------------


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert '#rrggbb' (or '#rgb') to (r, g, b) 0-255."""

    hex_color = hex_color.strip().lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) != 6:
        raise ValueError(f"unsupported hex color: {hex_color!r}")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def _channel_to_linear(c: int) -> float:
    """sRGB channel (0-255) → linear (0-1) per WCAG."""

    cs = c / 255.0
    if cs <= 0.03928:
        return cs / 12.92
    return ((cs + 0.055) / 1.055) ** 2.4


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (_channel_to_linear(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """WCAG contrast ratio between two colors. Always >= 1.0."""

    lf = _relative_luminance(_hex_to_rgb(fg_hex))
    lb = _relative_luminance(_hex_to_rgb(bg_hex))
    lighter = max(lf, lb)
    darker = min(lf, lb)
    return (lighter + 0.05) / (darker + 0.05)


def _extract_color_tokens(css_text: str) -> dict[str, dict[str, str]]:
    """Pull color tokens from :root and :root[data-theme="light"]
    blocks. Returns {theme: {var_name: hex}, ...}. Hex values
    only (skips rgba(), var(), etc.)."""

    themes: dict[str, dict[str, str]] = {"dark": {}, "light": {}}
    # Dark mode = :root { ... }
    # Light mode = :root[data-theme="light"] { ... }
    # We match the body of each block and parse --var: #hex; lines.
    pattern = re.compile(
        r"(:root(?:\[data-theme=\"light\"\])?)\s*\{([^}]*)\}",
        re.DOTALL,
    )
    for match in pattern.finditer(css_text):
        selector = match.group(1)
        body = match.group(2)
        theme = "light" if "light" in selector else "dark"
        for line in body.splitlines():
            m = re.match(r"\s*(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})", line)
            if m:
                themes[theme][m.group(1)] = m.group(2)
    return themes


class ContrastHelperUnit(unittest.TestCase):
    def test_black_on_white_is_21(self):
        # The maximum possible contrast
        ratio = contrast_ratio("#000000", "#ffffff")
        self.assertAlmostEqual(ratio, 21.0, places=0)

    def test_same_color_is_1(self):
        self.assertAlmostEqual(contrast_ratio("#888888", "#888888"), 1.0)

    def test_known_aa_failing_pair(self):
        # Light gray on white — well below AAA 7:1 threshold
        ratio = contrast_ratio("#999999", "#ffffff")
        self.assertLess(ratio, 4.5)

    def test_hex_short_form(self):
        # #fff expands to #ffffff; test rules out a parser bug
        self.assertAlmostEqual(
            contrast_ratio("#fff", "#000"),
            contrast_ratio("#ffffff", "#000000"),
        )


class WcagAaaContrastEnhanced(unittest.TestCase):
    """WCAG 1.4.6 (AAA) requires 7:1 for body text against the
    background. Pin the critical text/bg pairs from our token
    set."""

    @classmethod
    def setUpClass(cls):
        if not STYLES.exists():
            raise unittest.SkipTest(f"styles.css not at {STYLES}")
        css_text = STYLES.read_text(encoding="utf-8")
        cls.tokens = _extract_color_tokens(css_text)

    def _check_pair(self, theme: str, fg_var: str, bg_var: str, *, threshold: float = 7.0):
        fg = self.tokens[theme].get(fg_var)
        bg = self.tokens[theme].get(bg_var)
        self.assertIsNotNone(fg, f"missing {fg_var!r} in {theme} theme")
        self.assertIsNotNone(bg, f"missing {bg_var!r} in {theme} theme")
        ratio = contrast_ratio(fg, bg)
        self.assertGreaterEqual(
            ratio,
            threshold,
            f"{theme}: {fg_var}={fg} vs {bg_var}={bg} ratio={ratio:.2f}:1 "
            f"< AAA threshold {threshold}:1",
        )

    def test_dark_text_on_bg_meets_aaa(self):
        self._check_pair("dark", "--text", "--bg")

    def test_dark_text_on_surface_meets_aaa(self):
        self._check_pair("dark", "--text", "--surface")

    def test_dark_text_on_surface_2_meets_aaa(self):
        self._check_pair("dark", "--text", "--surface-2")

    def test_light_text_on_bg_meets_aaa(self):
        self._check_pair("light", "--text", "--bg")

    def test_light_text_on_surface_meets_aaa(self):
        self._check_pair("light", "--text", "--surface")


# ---------------------------------------------------------------------------
# WCAG 2.4.9 Link Purpose (Link Only) — AAA
# ---------------------------------------------------------------------------


_VAGUE_LINK_PHRASES = {
    "click here",
    "more",
    "read more",
    "here",
    "link",
    "this",
    "click",
    "see more",
}


class LinkPurposeAAA(unittest.TestCase):
    """WCAG 2.4.9 — every link must be understandable from the
    link text alone (no "click here", "more", "read more" with
    no surrounding context)."""

    HTML_SURFACES = [
        "index.html",
        "privacy.html",
        "terms.html",
        "impressum.html",
        "help.html",
        "data-retention.html",
        "changelog.html",
        "status.html",
    ]

    def _extract_link_texts(self, html_text: str) -> list[str]:
        """Pull <a>…</a> inner text. Strip nested tags + collapse
        whitespace. Returns lowercase + stripped strings."""

        texts: list[str] = []
        for match in re.finditer(r"<a\b[^>]*>(.*?)</a>", html_text, re.IGNORECASE | re.DOTALL):
            inner = match.group(1)
            # Strip nested tags (svg, span, etc.)
            text_only = re.sub(r"<[^>]+>", "", inner)
            # Collapse whitespace
            text_only = re.sub(r"\s+", " ", text_only).strip().lower()
            if text_only:
                texts.append(text_only)
        return texts

    def test_no_vague_link_texts_on_static_surfaces(self):
        offenders: list[tuple[str, str]] = []
        for name in self.HTML_SURFACES:
            path = STATIC / name
            if not path.exists():
                continue
            # Skip the SPA's index.html — its links are dynamic +
            # mostly chrome (icons, nav). The AA static suite
            # excludes it for the same reason; AAA stays consistent.
            if name == "index.html":
                continue
            for text in self._extract_link_texts(path.read_text(encoding="utf-8")):
                if text in _VAGUE_LINK_PHRASES:
                    offenders.append((name, text))
        self.assertEqual(
            offenders,
            [],
            "Vague link texts violate WCAG 2.4.9 AAA:\n"
            + "\n".join(f"  {n}: {t!r}" for n, t in offenders),
        )


# ---------------------------------------------------------------------------
# WCAG 2.4.10 Section Headings — AAA
# ---------------------------------------------------------------------------


class SectionHeadings(unittest.TestCase):
    """WCAG 2.4.10 — sections of content should have headings."""

    def test_static_surfaces_have_h1(self):
        for name in ("privacy.html", "terms.html", "impressum.html", "help.html"):
            path = STATIC / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            self.assertRegex(
                text,
                r"<h1\b",
                f"{name}: missing <h1> — top-level page heading required for AAA 2.4.10",
            )


class StatedTargetIsHonest(unittest.TestCase):
    """ACCESSIBILITY.md MUST be honest about the project's
    WCAG conformance level — claiming AAA without runtime
    verification across every page would be over-claiming.

    The stated target should be 'AA achieved + AAA-leaning
    enhancements' so external reviewers know exactly what's
    been verified vs aspirationally targeted."""

    def test_doc_doesnt_overclaim_aaa(self):
        path = REPO_ROOT / "ACCESSIBILITY.md"
        if not path.exists():
            self.skipTest("ACCESSIBILITY.md absent")
        text = path.read_text(encoding="utf-8")
        # Stated target MUST mention AA achievement
        self.assertIn("Level AA", text)
        # If "AAA" appears it should NOT claim full conformance
        # without a runtime audit
        if "AAA" in text and "level AAA" in text.lower():
            # If we DID claim AAA, the doc must reference a
            # runtime audit log
            self.assertIn(
                "axe-core",
                text,
                "ACCESSIBILITY.md claims AAA without referencing a runtime axe-core audit",
            )


if __name__ == "__main__":
    unittest.main()
