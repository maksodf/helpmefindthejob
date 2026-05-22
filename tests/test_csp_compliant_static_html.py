# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression guard: every public static HTML file must comply with our
production CSP (`script-src 'self'; style-src 'self' …`).

Two CSP violations surfaced in AUDIT-2 + AUDIT-3 (2026-05-22):

* AUDIT-2: ``static/status.html`` shipped an inline ``<script>const
  REFRESH_MS = 30000; …</script>`` block that the browser silently
  blocked. The status page never updated.
* AUDIT-3: ``static/index.html`` shipped 11 ``style="..."`` inline
  attributes. Some layout elements (chat form row, CV-builder photo
  panel, CV-builder action group) rendered visibly broken in
  production because the browser refused to apply the styles.

This test enforces both invariants forward-going. Any new HTML file
under ``static/`` that introduces an inline ``style="..."`` attribute
or a bare ``<script>...</script>`` block (with executable body, not
``application/ld+json``) will fail CI before the deploy.

If you legitimately need inline styles, lift them into a class in
``static/styles.css`` and reference via ``class=``. If you need an
inline script, extract it to a ``.js`` file and reference via
``<script src="..." defer>``.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "static"


# Files where inline content was historically necessary (e.g. third-
# party widgets that you can't avoid). Empty for now; populate with
# justification if a real exception ever lands.
INLINE_ALLOWLIST: tuple[str, ...] = ()


# Matches <script type="application/ld+json">…</script> blocks. These
# are NOT executable JS — CSP allows them without 'unsafe-inline'.
_LD_JSON_SCRIPT_RE = re.compile(
    r'<script\s+type="application/ld\+json">.*?</script>',
    re.DOTALL,
)

# Matches any non-empty <script>…</script> with an executable body
# (after removing JSON-LD + external-src scripts).
_EXECUTABLE_INLINE_SCRIPT_RE = re.compile(
    r"<script(?![^>]*\bsrc=)(?![^>]*\btype=\"application/ld\+json\")[^>]*>"
    r"\s*\S.*?</script>",
    re.DOTALL,
)


def _strip_ld_json_scripts(html: str) -> str:
    return _LD_JSON_SCRIPT_RE.sub("", html)


class NoInlineStyleAttributesInStaticHtml(unittest.TestCase):
    """CSP ``style-src 'self'`` blocks inline style attributes —
    every static HTML page must use external CSS classes only.
    """

    def test_no_inline_style_attribute_in_any_static_html(self) -> None:
        offenders: list[tuple[str, int, str]] = []
        for path in sorted(STATIC_DIR.rglob("*.html")):
            rel = str(path.relative_to(REPO_ROOT))
            if rel in INLINE_ALLOWLIST:
                continue
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                if 'style="' in line:
                    offenders.append((rel, lineno, line.strip()[:160]))
        if offenders:
            details = "\n".join(
                f"  {p}:{ln}: {snippet}"
                for p, ln, snippet in offenders
            )
            self.fail(
                "Inline style=\"...\" attributes found in static HTML; "
                "CSP 'style-src 'self'' will block them. Lift each into "
                "a class in static/styles.css and reference via class=\":\n"
                + details
            )


class NoExecutableInlineScriptsInStaticHtml(unittest.TestCase):
    """CSP ``script-src 'self'`` blocks inline executable scripts —
    only ``<script type=\"application/ld+json\">`` and ``<script
    src=\"...\">`` are CSP-allowed.
    """

    def test_no_executable_inline_script_in_any_static_html(self) -> None:
        offenders: list[tuple[str, str]] = []
        for path in sorted(STATIC_DIR.rglob("*.html")):
            rel = str(path.relative_to(REPO_ROOT))
            if rel in INLINE_ALLOWLIST:
                continue
            text = path.read_text(encoding="utf-8")
            stripped = _strip_ld_json_scripts(text)
            match = _EXECUTABLE_INLINE_SCRIPT_RE.search(stripped)
            if match:
                snippet = match.group(0)[:200].replace("\n", " ")
                offenders.append((rel, snippet))
        if offenders:
            details = "\n".join(f"  {p}: {snippet}" for p, snippet in offenders)
            self.fail(
                "Inline <script>...</script> with executable body found in "
                "static HTML; CSP 'script-src 'self'' will block it. Extract "
                "the body to a .js file under static/ and reference via "
                "<script src=\"/file.js\" defer>:\n"
                + details
            )


if __name__ == "__main__":
    unittest.main()
