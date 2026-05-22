# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""WCAG 1.3.1 + 4.1.2 root-cause guard: every form control in any
user-facing static HTML file MUST have a programmatic label.

A "programmatic label" is one of:
  1. ``<label for="X">`` matching the control's ``id="X"``
  2. ``aria-label="..."`` directly on the control
  3. ``aria-labelledby="..."`` referencing a visible element's id

Without one of these, screen reader users hear the input's type
("edit text") with no indication of what to enter. This is a
WCAG-AA failure for every uncovered control.

AUDIT-7 incident (2026-05-22): 70 of 95 form controls in
``static/index.html`` had no programmatic label. The SPA used the
``<label class="field"><span>label</span><input id="X"></label>``
pattern, which relies on implicit-wrap association. The implicit
association is technically per HTML5 spec but is unreliable across
screen readers; the audit caught this gap. This test pins the
explicit-association fix forward-going.

Files covered: every ``.html`` file under ``static/`` that is
served as a user-facing page.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC = REPO_ROOT / "static"


# Pages that ship form controls intended for human interaction.
# Pages that don't (e.g. pure-narrative status / changelog) are
# allowlisted off this check.
COVERED_PAGES = (
    "index.html",
    # Legal pages don't have form controls today — if they grow any,
    # add here. They're left out for now because the test would
    # pointlessly pass on zero inputs.
)


def _form_control_ids(html: str) -> list[str]:
    pattern = r'<(?:input|select|textarea)\b[^>]*\bid="([^"]+)"'
    return re.findall(pattern, html)


def _labels_with_for(html: str) -> set[str]:
    return set(re.findall(r'<label[^>]*\bfor="([^"]+)"', html))


def _ids_with_aria_label(html: str) -> set[str]:
    out: set[str] = set()
    for tag in ("input", "select", "textarea"):
        # aria-label appears before id
        out |= set(
            re.findall(
                rf'<{tag}[^>]*\baria-label="[^"]+"[^>]*\bid="([^"]+)"',
                html,
            )
        )
        # id appears before aria-label
        out |= set(
            re.findall(
                rf'<{tag}[^>]*\bid="([^"]+)"[^>]*\baria-label="[^"]+"',
                html,
            )
        )
    return out


def _ids_with_aria_labelledby(html: str) -> set[str]:
    out: set[str] = set()
    for tag in ("input", "select", "textarea"):
        out |= set(
            re.findall(
                rf'<{tag}[^>]*\baria-labelledby="[^"]+"[^>]*\bid="([^"]+)"',
                html,
            )
        )
        out |= set(
            re.findall(
                rf'<{tag}[^>]*\bid="([^"]+)"[^>]*\baria-labelledby="[^"]+"',
                html,
            )
        )
    return out


class EveryFormControlHasProgrammaticLabel(unittest.TestCase):
    def test_every_input_select_textarea_has_a_label(self) -> None:
        offenders: list[tuple[str, str]] = []
        for page in COVERED_PAGES:
            path = STATIC / page
            self.assertTrue(path.exists(), f"Missing test target: {page}")
            html = path.read_text(encoding="utf-8")

            controls = _form_control_ids(html)
            labelled_via_for = _labels_with_for(html)
            labelled_via_aria = _ids_with_aria_label(html)
            labelled_via_aria_by = _ids_with_aria_labelledby(html)

            for control_id in controls:
                if (
                    control_id not in labelled_via_for
                    and control_id not in labelled_via_aria
                    and control_id not in labelled_via_aria_by
                ):
                    offenders.append((page, control_id))

        if offenders:
            details = "\n".join(
                f"  {page} #id={cid}: no <label for=>, no aria-label, no aria-labelledby"
                for page, cid in offenders
            )
            self.fail(
                "Form controls without a programmatic label "
                "(WCAG 1.3.1 / 4.1.2 failure):\n" + details
            )

    def test_no_dangling_label_for_attrs(self) -> None:
        """A <label for="X"> that points at a non-existent id is worse
        than no label — screen readers announce nothing AND clicking
        the label does nothing."""

        for page in COVERED_PAGES:
            html = (STATIC / page).read_text(encoding="utf-8")
            fors = set(re.findall(r'<label[^>]*\bfor="([^"]+)"', html))
            all_ids = set(re.findall(r'\bid="([^"]+)"', html))
            dangling = sorted(f for f in fors if f not in all_ids)
            self.assertEqual(
                dangling,
                [],
                f"{page}: <label for=> pointing at non-existent ids: "
                f"{dangling}",
            )

    def test_no_duplicate_ids(self) -> None:
        """Duplicate ids break label/aria associations + cause
        ``getElementById`` to return only the first match — silent UI
        bugs."""

        from collections import Counter

        for page in COVERED_PAGES:
            html = (STATIC / page).read_text(encoding="utf-8")
            all_ids = re.findall(r'\bid="([^"]+)"', html)
            dups = sorted(k for k, v in Counter(all_ids).items() if v > 1)
            self.assertEqual(
                dups,
                [],
                f"{page}: duplicate ids: {dups}",
            )


if __name__ == "__main__":
    unittest.main()
