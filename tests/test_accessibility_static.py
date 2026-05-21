# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""4-week plan W4 D16-17: accessibility static contracts
(invariant 12).

The project has already passed three rounds of axe-core CLI 4.11
+ axe-playwright runs at WCAG 2.2 Level AA (0 violations across
all surfaces). Going beyond AA to AAA requires runtime rendering
(contrast ratio 7:1, keyboard-only navigation, etc.) — too
expensive for a CI gate that runs on every commit.

These STATIC tests are the CI-cheap guardrails that pin the
accessibility invariants the dynamic audits already verify, so a
future refactor that quietly removes the skip-link, strips
focus-visible CSS, or breaks the heading hierarchy fails fast in
unit-test land rather than in the next quarterly axe run.

Coverage:
1. **Skip link** present + linked to a tabbable target.
2. **HTML lang attribute** set (WCAG 3.1.1 Language of Page).
3. **Landmarks**: <header>, <main>, <nav>, <footer> or roles.
4. **Heading hierarchy**: no skipped levels (h1 → h3 with no h2).
5. **Form inputs**: every <input>/<select>/<textarea> has either
   a <label for=…>, an aria-label, or aria-labelledby.
6. **Images**: every <img> has alt (or role="presentation"/
   aria-hidden).
7. **Buttons**: every <button> has accessible text (text content,
   aria-label, or aria-labelledby).
8. **Focus styles**: :focus-visible rules in CSS for interactive
   elements (button, input, link).
9. **Reduced motion**: @media (prefers-reduced-motion: reduce)
   rule present so the UI honors the user's OS-level setting.
10. **ARIA live regions**: at least one aria-live region present
    for dynamic content (status/alert/log).
11. **Lang switch present** for the locale picker (WCAG 3.1.2
    Language of Parts — when the user changes locale, the page's
    lang attr must update; this is wired in JS).

These are necessary-but-not-sufficient for AAA. The full picture
requires the dynamic axe-core runs in
`scripts/accessibility-audit-auth-surfaces.py`.
"""

from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC = REPO_ROOT / "static"
INDEX_HTML = STATIC / "index.html"
STYLES_CSS = STATIC / "styles.css"


# All public HTML surfaces audited by the dynamic runs
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


class _AttrCollector(HTMLParser):
    """HTMLParser that captures (tag, attrs, text_content_estimate)
    for inspection. We don't need DOM-perfect parsing — just
    enough to assert structural invariants."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str], int]] = []
        self._open_stack: list[tuple[int, list[str]]] = []
        self.html_attrs: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        idx = len(self.tags)
        self.tags.append((tag, attr_dict, idx))
        self._open_stack.append((idx, []))
        if tag == "html":
            self.html_attrs = attr_dict

    def handle_startendtag(self, tag, attrs):
        attr_dict = dict(attrs)
        self.tags.append((tag, attr_dict, len(self.tags)))

    def handle_endtag(self, tag):
        if self._open_stack:
            idx, texts = self._open_stack.pop()
            # Backfill the captured text content for that tag
            tag_name, attrs, i = self.tags[idx]
            attrs["__text_content__"] = "".join(texts).strip()
            self.tags[idx] = (tag_name, attrs, i)

    def handle_data(self, data):
        for _idx, texts in self._open_stack:
            texts.append(data)


def _parse(html_path: Path) -> _AttrCollector:
    parser = _AttrCollector()
    parser.feed(html_path.read_text(encoding="utf-8"))
    return parser


class SkipLinkPresent(unittest.TestCase):
    def test_index_has_skip_link(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        self.assertRegex(
            text,
            r'<a[^>]+class="[^"]*skip-link[^"]*"[^>]+href="#[^"]+"',
            "index.html missing a class='skip-link' anchor — keyboard "
            "users rely on this to jump past the navigation",
        )

    def test_skip_link_targets_existing_id(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        m = re.search(r'<a[^>]+class="[^"]*skip-link[^"]*"[^>]+href="#([^"]+)"', text)
        self.assertIsNotNone(m, "skip-link not found")
        target = m.group(1)
        self.assertRegex(
            text,
            rf'\bid="{re.escape(target)}"',
            f"skip-link points at #{target} but no element with id='{target}' exists",
        )


class HtmlLangAttribute(unittest.TestCase):
    def test_every_html_surface_declares_lang(self):
        for name in HTML_SURFACES:
            path = STATIC / name
            if not path.exists():
                continue
            parsed = _parse(path)
            self.assertIn(
                "lang",
                parsed.html_attrs,
                f"{name}: <html> missing lang attribute (WCAG 3.1.1)",
            )
            lang = parsed.html_attrs["lang"]
            # Must be a valid BCP 47 prefix (2-3 lowercase letters
            # optionally followed by region/script)
            self.assertRegex(
                lang,
                r"^[a-z]{2,3}([-_][a-zA-Z0-9]{2,4})*$",
                f"{name}: lang='{lang}' is not valid BCP 47",
            )


class Landmarks(unittest.TestCase):
    def test_index_has_main_landmark(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        self.assertTrue(
            re.search(r"<main\b", text) or re.search(r'role="main"', text),
            "index.html missing <main> or role='main' landmark",
        )

    def test_index_has_nav_landmark(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        self.assertTrue(
            re.search(r"<nav\b", text) or re.search(r'role="navigation"', text),
            "index.html missing <nav> or role='navigation' landmark",
        )

    def test_index_has_header_landmark(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        self.assertTrue(
            re.search(r"<header\b", text) or re.search(r'role="banner"', text),
            "index.html missing <header> or role='banner' landmark",
        )


class HeadingHierarchy(unittest.TestCase):
    """WCAG 1.3.1: headings communicate structure. Skipped levels
    (h1 → h3 with no h2) confuse screen readers. We tolerate
    repeated levels (h2 → h2) but not jumps."""

    def _collect_heading_levels(self, html: str) -> list[int]:
        levels = []
        for match in re.finditer(r"<h([1-6])\b", html, re.IGNORECASE):
            levels.append(int(match.group(1)))
        return levels

    def test_static_surfaces_have_at_least_one_h1(self):
        for name in HTML_SURFACES:
            path = STATIC / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            levels = self._collect_heading_levels(text)
            if not levels:
                continue  # empty pages don't need headings
            self.assertIn(
                1,
                levels,
                f"{name}: no <h1> — every page needs one top-level heading",
            )

    def test_static_surfaces_no_skipped_heading_levels(self):
        """A jump from h1 → h3 (skipping h2) is a WCAG 2.2 1.3.1
        warning. We only check the static surfaces; the SPA's
        index.html mixes server-rendered + dynamic templates so its
        heading hierarchy is verified by the dynamic axe-core run."""

        for name in HTML_SURFACES:
            if name == "index.html":
                continue  # SPA; dynamic templates checked by axe runs
            path = STATIC / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            levels = self._collect_heading_levels(text)
            if not levels:
                continue
            for i, current in enumerate(levels[1:], start=1):
                prev = levels[i - 1]
                if current > prev:
                    self.assertLessEqual(
                        current - prev,
                        1,
                        f"{name}: heading skip h{prev} → h{current} at index "
                        f"{i} — re-rank headings so no level is skipped",
                    )


class FocusVisibleStyles(unittest.TestCase):
    """:focus-visible CSS pseudo-class is the modern way to render
    keyboard-focus indicators without flashing them on mouse click.
    AAA 2.4.7 requires visible focus."""

    def test_focus_visible_rules_present(self):
        css = STYLES_CSS.read_text(encoding="utf-8")
        self.assertIn(":focus-visible", css)

    def test_focus_visible_covers_core_interactive_elements(self):
        css = STYLES_CSS.read_text(encoding="utf-8")
        # The rule MUST cover at least buttons + inputs (most common
        # interactive elements). We accept either tag selectors
        # (button, input) OR utility-class selectors (.btn, .input)
        # since both produce equivalent rendered behaviour.
        button_pattern = r"(\bbutton|\.btn)[^,{]*?:focus-visible"
        input_pattern = r"(\binput|\.input|\.form-control)[^,{]*?:focus-visible"
        self.assertRegex(
            css,
            button_pattern,
            "no :focus-visible rule covers buttons (button or .btn)",
        )
        self.assertRegex(
            css,
            input_pattern,
            "no :focus-visible rule covers inputs (input or .input)",
        )


class ReducedMotionMediaQuery(unittest.TestCase):
    """WCAG 2.3.3 Animation from Interactions (AAA) — users with
    vestibular disorders need to opt out of motion. Honor the OS
    `prefers-reduced-motion` setting."""

    def test_reduced_motion_query_present(self):
        css = STYLES_CSS.read_text(encoding="utf-8")
        self.assertRegex(
            css,
            r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)",
            "no @media (prefers-reduced-motion: reduce) — users with "
            "vestibular disorders can't opt out of animations",
        )


class AriaLiveRegions(unittest.TestCase):
    """WCAG 4.1.3 Status Messages — dynamic content updates MUST
    be announced to screen readers via aria-live."""

    def test_index_has_at_least_one_live_region(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        self.assertRegex(
            text,
            r'aria-live="(polite|assertive)"',
            "index.html has no aria-live regions — screen readers "
            "won't announce dynamic updates (toasts, status pills, "
            "scan progress)",
        )

    def test_index_has_status_role_or_alert_role(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        # role=status is for non-urgent updates; role=alert for
        # urgent. At least one of either must be present.
        self.assertTrue(
            'role="status"' in text or 'role="alert"' in text or 'role="log"' in text,
            "index.html has no role=status/alert/log — dynamic updates "
            "aren't announced",
        )


class FormControlsAreLabeled(unittest.TestCase):
    """WCAG 1.3.1 + 3.3.2 — every form control needs a programmatic
    label so screen readers announce it. Accepts <label for=>,
    aria-label, aria-labelledby, or wrapping <label>."""

    def _orphan_inputs(self, html_text: str) -> list[str]:
        orphans = []
        # Collect all label[for=…] targets
        label_targets = set(
            re.findall(r'<label[^>]+\bfor="([^"]+)"', html_text)
        )
        # Iterate every form input
        for match in re.finditer(
            r'<(input|select|textarea)\b[^>]*>', html_text, re.IGNORECASE
        ):
            tag_block = match.group(0)
            tag = match.group(1).lower()
            # hidden inputs don't need labels (they're not perceived)
            if re.search(r'\btype="hidden"', tag_block, re.IGNORECASE):
                continue
            # type="submit"/"button"/"reset"/"image" carry their own value
            type_match = re.search(r'\btype="([^"]+)"', tag_block, re.IGNORECASE)
            if type_match and type_match.group(1).lower() in (
                "submit",
                "button",
                "reset",
                "image",
            ):
                continue
            id_match = re.search(r'\bid="([^"]+)"', tag_block, re.IGNORECASE)
            has_aria_label = bool(re.search(r'\baria-label="', tag_block, re.IGNORECASE))
            has_aria_labelledby = bool(
                re.search(r'\baria-labelledby="', tag_block, re.IGNORECASE)
            )
            has_label_for = id_match and id_match.group(1) in label_targets
            if not (has_aria_label or has_aria_labelledby or has_label_for):
                orphans.append(tag_block[:120])
        return orphans

    def test_static_surfaces_have_no_orphan_form_controls(self):
        # We check only the small static surfaces (legal pages
        # etc.) for orphan form controls. The SPA's index.html is
        # large + has dynamic JS-injected controls so we exclude it
        # — the dynamic axe-core run covers it.
        for name in HTML_SURFACES:
            if name == "index.html":
                continue
            path = STATIC / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            orphans = self._orphan_inputs(text)
            self.assertEqual(
                orphans,
                [],
                f"{name}: form controls without a programmatic label: {orphans}",
            )


class ImagesHaveAlt(unittest.TestCase):
    """WCAG 1.1.1 Non-text Content — every <img> needs alt
    (decorative imgs use alt='' or aria-hidden)."""

    def test_no_img_lacks_alt(self):
        for name in HTML_SURFACES:
            path = STATIC / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r"<img\b[^>]*>", text, re.IGNORECASE):
                tag = match.group(0)
                has_alt = re.search(r"\balt=", tag, re.IGNORECASE)
                has_aria_hidden = re.search(r'\baria-hidden="true"', tag, re.IGNORECASE)
                has_role_pres = re.search(r'\brole="presentation"', tag, re.IGNORECASE)
                self.assertTrue(
                    has_alt or has_aria_hidden or has_role_pres,
                    f"{name}: <img> without alt/aria-hidden/role=presentation: {tag[:100]}",
                )


class LinksAreNotJustChromeColor(unittest.TestCase):
    """WCAG 1.4.1 Use of Color — links MUST be distinguishable
    from surrounding text by more than color alone (underline,
    weight, icon). We pin that the CSS has at least one rule
    where anchor styling includes text-decoration."""

    def test_links_styled_with_text_decoration(self):
        css = STYLES_CSS.read_text(encoding="utf-8")
        # Look for an `a` rule that mentions text-decoration. The
        # absence of any `text-decoration:` for anchors would mean
        # links are color-only.
        self.assertRegex(
            css,
            r"\ba\s*\{[^}]*text-decoration",
            "No anchor rule sets text-decoration — links may be "
            "color-only, failing WCAG 1.4.1 Use of Color",
        )


class HtmlLangSwitchesWithLocale(unittest.TestCase):
    """WCAG 3.1.2 Language of Parts — when the user changes locale,
    the page's lang attribute MUST update. The JS layer does this
    in `_applyLocaleDirection` (W3 D15 multilingual scaffolding)."""

    def test_locale_change_updates_html_lang(self):
        app_js = (STATIC / "app.js").read_text(encoding="utf-8")
        # The function MUST set document.documentElement.lang
        self.assertIn("document.documentElement.lang", app_js)
        # AND it MUST set document.documentElement.dir for RTL
        self.assertIn("document.documentElement.dir", app_js)


class NoAutoplayAudio(unittest.TestCase):
    """WCAG 1.4.2 Audio Control AA + AAA — no autoplay >3s. We
    pin: no <audio autoplay> or <video autoplay without muted>."""

    def test_no_autoplaying_media(self):
        for name in HTML_SURFACES:
            path = STATIC / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            # Find every <audio> or <video> tag
            for match in re.finditer(
                r"<(audio|video)\b[^>]*>", text, re.IGNORECASE
            ):
                tag = match.group(0)
                if re.search(r"\bautoplay\b", tag, re.IGNORECASE):
                    # Allow if muted (autoplaying silently is OK per spec)
                    self.assertRegex(
                        tag,
                        r"\bmuted\b",
                        f"{name}: <{match.group(1)} autoplay> without muted "
                        "— WCAG 1.4.2 forbids unprompted audio >3s",
                    )


class SkipLinkIsFirstFocusable(unittest.TestCase):
    """AAA 2.4.1 Bypass Blocks (already AA) + best practice — the
    skip link should be the FIRST focusable element so it's
    reachable in one Tab press."""

    def test_skip_link_appears_before_main_content(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        skip_match = re.search(r'<a[^>]+class="[^"]*skip-link', text)
        main_match = re.search(r"<main\b|<nav\b|<header\b", text)
        self.assertIsNotNone(skip_match, "no skip-link")
        self.assertIsNotNone(main_match, "no main/nav/header")
        self.assertLess(
            skip_match.start(),
            main_match.start(),
            "skip-link appears AFTER the first landmark — it must "
            "be the first focusable element so a single Tab "
            "press reaches it",
        )


class ButtonsHaveAccessibleName(unittest.TestCase):
    """WCAG 4.1.2 — every <button> needs an accessible name (text
    content, aria-label, or aria-labelledby)."""

    def _orphan_buttons(self, html_text: str) -> list[str]:
        orphans = []
        # Find every <button>…</button> block
        for match in re.finditer(
            r"<button\b([^>]*)>(.*?)</button>", html_text, re.IGNORECASE | re.DOTALL
        ):
            attrs = match.group(1)
            content = match.group(2)
            # Strip tags + comments from content
            text_only = re.sub(r"<[^>]+>", "", content)
            text_only = re.sub(r"<!--.*?-->", "", text_only, flags=re.DOTALL).strip()
            has_text = bool(text_only)
            has_aria_label = bool(re.search(r'\baria-label="', attrs, re.IGNORECASE))
            has_aria_labelledby = bool(
                re.search(r'\baria-labelledby="', attrs, re.IGNORECASE)
            )
            has_title = bool(re.search(r'\btitle="[^"]+"', attrs, re.IGNORECASE))
            if not (has_text or has_aria_label or has_aria_labelledby or has_title):
                orphans.append(match.group(0)[:160])
        return orphans

    def test_static_surfaces_have_no_orphan_buttons(self):
        # Same scope as form controls — small static surfaces only;
        # the SPA's JS-injected buttons are covered by the dynamic
        # axe-core run.
        for name in HTML_SURFACES:
            if name == "index.html":
                continue
            path = STATIC / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            orphans = self._orphan_buttons(text)
            self.assertEqual(
                orphans,
                [],
                f"{name}: buttons without accessible name: {orphans}",
            )


if __name__ == "__main__":
    unittest.main()
