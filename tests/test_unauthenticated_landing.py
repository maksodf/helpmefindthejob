# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Unauthenticated landing-block contract (pre-deployment polish).

Previously, ``static/index.html`` opened with a bare
"Sign in to continue" auth gate — meaning an NLnet reviewer or
first-time visitor landing on `helpmefindthejob.org` saw a gate,
not the project mission. The unauthenticated landing block sits
above the auth-card inside `#authGate` so it's visible exactly
when the user is NOT signed in, and disappears the moment they
authenticate.

Tests pin: the mission block is present, the i18n keys exist in
EN + DE, the four narrative bullets are in place, the
docs/GitHub/changelog/status links are wired, and the layout
class is applied for the responsive side-by-side layout.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = REPO_ROOT / "static" / "index.html"
EN_BUNDLE = REPO_ROOT / "static" / "i18n" / "en.json"
DE_BUNDLE = REPO_ROOT / "static" / "i18n" / "de.json"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"


class LandingBlockPresentInIndex(unittest.TestCase):
    def setUp(self):
        self.src = INDEX_HTML.read_text(encoding="utf-8")

    def test_auth_layout_wrapper_present(self):
        """The two-column layout wrapper must exist so the mission
        block can sit beside the auth-card on desktop and stack on
        mobile."""

        self.assertIn('class="auth-layout"', self.src)

    def test_mission_section_present(self):
        self.assertIn('class="auth-mission"', self.src)
        self.assertIn('id="missionHeading"', self.src)

    def test_mission_lives_inside_authgate(self):
        """The mission block must be inside `#authGate` so it
        inherits the same auth-gated visibility (hidden when
        signed in)."""

        gate_start = self.src.find('id="authGate"')
        gate_end = self.src.find("</main>", gate_start)
        gate_section = self.src[gate_start:gate_end]
        self.assertIn('class="auth-mission"', gate_section)

    def test_four_narrative_bullets_present(self):
        """The bullets carry the four moats: AI Act / MCP / friction-
        class / Commons Conservancy. Pin all four so the narrative
        doesn't silently drop a moat."""

        for i in (1, 2, 3, 4):
            with self.subTest(bullet=i):
                self.assertIn(f'data-i18n="landing.bullet{i}.head"', self.src)
                self.assertIn(f'data-i18n="landing.bullet{i}.body"', self.src)

    def test_seven_persona_panel_referenced(self):
        """Aïcha · Yusuf · Olga · Mahmoud · Maria · Käthe · Tobias —
        the panel must show somewhere on the landing or in a
        translation key."""

        # Persona panel is in bullet3.body (DE + EN). Check EN bundle
        # since the inline fallback in index.html doesn't carry the
        # full panel string verbatim.
        en = json.loads(EN_BUNDLE.read_text(encoding="utf-8"))
        bullet3 = en.get("landing.bullet3.body", "")
        for persona in ("Aïcha", "Yusuf", "Olga", "Mahmoud", "Maria", "Käthe", "Tobias"):
            with self.subTest(persona=persona):
                self.assertIn(persona, bullet3)

    def test_project_links_present(self):
        """The 4 project links (help / GitHub / changelog / status)
        give the visitor concrete ways to explore beyond signing in."""

        self.assertIn('href="/help"', self.src)
        self.assertIn("github.com/maksodf/helpmefindthejob", self.src)
        self.assertIn('href="/status"', self.src)
        self.assertIn('href="https://helpmefindthejob.org/changelog"', self.src)

    def test_alpha_honesty_disclaimer(self):
        """The "alpha — main branch may be unstable" line keeps the
        landing honest about tier (CLAUDE.md hard rule #6)."""

        en = json.loads(EN_BUNDLE.read_text(encoding="utf-8"))
        self.assertIn("Alpha", en.get("landing.foot", ""))


class I18nLandingKeysParity(unittest.TestCase):
    """All landing.* keys must exist in BOTH bundles."""

    def setUp(self):
        self.en = json.loads(EN_BUNDLE.read_text(encoding="utf-8"))
        self.de = json.loads(DE_BUNDLE.read_text(encoding="utf-8"))

    def test_landing_keys_in_both_bundles(self):
        en_landing = {k for k in self.en if k.startswith("landing.")}
        de_landing = {k for k in self.de if k.startswith("landing.")}
        self.assertEqual(
            en_landing,
            de_landing,
            f"landing.* key drift between bundles: "
            f"en-only={en_landing - de_landing}, "
            f"de-only={de_landing - en_landing}",
        )

    def test_minimum_landing_key_count(self):
        en_landing = [k for k in self.en if k.startswith("landing.")]
        # 4 bullets × 2 (head + body) + tag + headline + lead + 3
        # links + foot = 15 keys
        self.assertGreaterEqual(len(en_landing), 14)

    def test_de_landing_strings_non_empty(self):
        for key, value in self.de.items():
            if not key.startswith("landing."):
                continue
            with self.subTest(key=key):
                self.assertTrue(
                    value.strip(),
                    f"de.json[{key!r}] is empty — DACH market is "
                    "the primary deployment target; missing DE "
                    "strings break the first impression for the "
                    "primary persona panel.",
                )

    def test_blue_card_term_kept_verbatim(self):
        """Per docs/translating.md German-bureaucratic-conventions
        preservation rule, 'Blue Card' stays verbatim in DE
        translations. After the AUDIT-32 + 33 landing rewrite
        (2026-05-23) the term moved from landing.lead into
        landing.personas.maria (the EU Blue Card persona card);
        the preservation rule applies wherever the term lives."""

        carrier_keys = ("landing.lead", "landing.personas.maria")
        appears = any("Blue Card" in self.de.get(k, "") for k in carrier_keys)
        self.assertTrue(
            appears,
            f"'Blue Card' must appear verbatim in one of {carrier_keys}",
        )

    def test_wiedereinstieg_term_kept_verbatim(self):
        """Same preservation rule for 'Wiedereinstieg'. Post-
        AUDIT-32/33 it lives in landing.personas.kaethe (the
        re-entry persona)."""
        carrier_keys = ("landing.lead", "landing.personas.kaethe")
        appears = any("Wiedereinstieg" in self.de.get(k, "") for k in carrier_keys)
        self.assertTrue(
            appears,
            f"'Wiedereinstieg' must appear verbatim in one of {carrier_keys}",
        )


class CssStylesPresent(unittest.TestCase):
    def setUp(self):
        self.src = STYLES_CSS.read_text(encoding="utf-8")

    def test_layout_class_styled(self):
        self.assertIn(".auth-layout", self.src)

    def test_mission_classes_styled(self):
        for klass in (
            ".auth-mission",
            ".auth-mission-tag",
            ".auth-mission-headline",
            ".auth-mission-lead",
            ".auth-mission-bullets",
            ".auth-mission-links",
            ".auth-mission-link",
            ".auth-mission-foot",
        ):
            with self.subTest(klass=klass):
                self.assertIn(klass, self.src)

    def test_responsive_breakpoint(self):
        """Mobile-first stacked layout with a >=900px desktop
        breakpoint that switches to side-by-side."""

        self.assertIn("@media (min-width: 900px)", self.src)


if __name__ == "__main__":
    unittest.main()
