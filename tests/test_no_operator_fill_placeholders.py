# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Root-cause guard: no `[OPERATOR FILL: ...]` placeholders may ship to production.

AUDIT-1 incident (2026-05-22): the German Impressum at
`static/impressum.html` shipped with eight unfilled
`[OPERATOR FILL: ...]` placeholders rendered live to users. That's a
§ 5 TMG violation in Germany (operator-identification placeholders
where the legal entity name, address, phone, and date should be) and
a credibility kill for grant reviewers. The original template was
designed with placeholder syntax intended to be substituted at deploy
time; the substitution step was never wired into CI.

This test is that substitution step's missing guard. It scans every
served static HTML file under `static/` and fails if **any** of them
contain the literal string `OPERATOR FILL`. The same guard catches
adjacent placeholder syntaxes that have surfaced in past audits
(`TODO:`, `TBD:`, `XXX:`) at the start of a tag's text content.

If you legitimately need a placeholder during development, leave it
in a `<!-- comment -->` (still gets caught — comments rot in
production too) OR mark it `&#91;OPERATOR FILL:` (HTML-entity escape)
so it doesn't render visibly while you wait for the real value.

Origin: phase2-backlog AUDIT-1; root-cause fix per the operator's
"no gaps behind" doctrine.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "static"


# Forbidden literal strings — anything that screams "draft text shipped
# accidentally to production". Extend as new patterns surface.
FORBIDDEN_LITERALS = (
    "OPERATOR FILL",
    "[OPERATOR FILL",
    "TBD:",
    "TODO:",
    "XXX:",
    "[REPLACE WITH",
    "FIXME:",
)


class StaticHtmlHasNoPlaceholderResidue(unittest.TestCase):
    """No `*.html` file under `static/` may contain known placeholder
    literals at deploy time. Failing this test means a draft string
    is about to ship to production.
    """

    def test_no_forbidden_literals_in_any_static_html(self) -> None:
        # Strip <code>...</code> and <pre>...</pre> content first —
        # literal text inside those (e.g. changelog entries documenting
        # the past OPERATOR FILL bug) is documentation, not residue.
        code_re = re.compile(r"<code[^>]*>.*?</code>|<pre[^>]*>.*?</pre>", re.DOTALL)
        offenders: list[tuple[str, str, int]] = []
        for html_path in sorted(STATIC_DIR.rglob("*.html")):
            raw = html_path.read_text(encoding="utf-8")
            text = code_re.sub("", raw)
            for needle in FORBIDDEN_LITERALS:
                if needle in text:
                    idx = text.index(needle)
                    line_no = text.count("\n", 0, idx) + 1
                    offenders.append(
                        (str(html_path.relative_to(REPO_ROOT)), needle, line_no),
                    )

        if offenders:
            lines = [
                f"  {path}:{line_no} contains forbidden literal {needle!r}"
                for path, needle, line_no in offenders
            ]
            self.fail(
                "Placeholder residue found in static HTML — these would "
                "ship to production:\n" + "\n".join(lines)
            )

    def test_impressum_has_real_operator_data_not_placeholders(self) -> None:
        """Sharper assertion specifically for the §5 TMG Impressum:
        the file must contain the substantive German legal-required
        sections (Anbieter, Anschrift fragment, Telefon with +49 prefix,
        Verantwortlich) with NON-placeholder content.
        """
        impressum = (STATIC_DIR / "impressum.html").read_text(encoding="utf-8")

        for required in (
            "<h2>Anbieter</h2>",
            "<h2>Kontakt</h2>",
            "<h2>Verantwortlich für den Inhalt</h2>",
            "<h2>Registereintrag</h2>",
            "Telefon:",
            "+49",  # international phone-format
            "Deutschland",
            "Stand:",
        ):
            with self.subTest(required=required):
                self.assertIn(
                    required,
                    impressum,
                    f"Impressum missing required section/marker: {required!r}",
                )


if __name__ == "__main__":
    unittest.main()
