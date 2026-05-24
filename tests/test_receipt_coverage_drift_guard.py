# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Drift guard: every user-facing AI dispatch site must wire
``receipt_emitter`` AND ``cap_context``.

Quality-bar rationale: the cost-cap fail-closed protection and
the Trust Receipt audit trail are BOTH invariants the project
ships. A new chat handler / REST endpoint that wires only the
cap_context (missing receipt_emitter) would silently skip
receipt creation — the user would lose evidence of decisions
made on their behalf. This test fails the build if any
dispatch site uses ``cap_context=`` without a matching
``receipt_emitter=`` AND isn't on the explicit exemption list.

Explicit exemptions live in EXEMPT_CALL_SITES below with a
recorded reason. Adding a site to the exemption list is a
DELIBERATE engineering choice — the test catches accidental
omissions, not deliberate ones.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Sites that intentionally do NOT emit Trust Receipts, with
# reason. Adding a new site requires reviewer sign-off on the
# reason — the test compares positions textually, so keep
# reasons specific.
EXEMPT_CALL_SITES: dict[str, str] = {
    # Chat-router intent classification runs many times per
    # conversation and produces no user-visible artifact.
    # Emitting receipts here would flood the user's log.
    'purpose="chat_router"': (
        "chat router runs many times per conversation; no user-visible "
        "artifact to attest to; would flood the receipt log"
    ),
}


def _has_receipt_emitter_in_call(call_text: str) -> bool:
    return "receipt_emitter=" in call_text


def _is_exempt(call_text: str) -> bool:
    return any(marker in call_text for marker in EXEMPT_CALL_SITES.keys())


class ReceiptCoverageDriftGuard(unittest.TestCase):
    def test_every_dispatch_with_cap_context_also_has_receipt_emitter(self) -> None:
        """Walk app.py + every site calling _dispatch_provider /
        _dispatch_provider_streaming / execute_* with a
        ``cap_context=`` and assert each also passes
        ``receipt_emitter=`` (or is on the exemption list)."""

        violations: list[tuple[str, int, str]] = []
        for source_file in (REPO_ROOT / "app.py",):
            text = source_file.read_text(encoding="utf-8")
            # Match either of:
            #   foo(... cap_context=... )
            # capturing the full call (greedy with balanced
            # parens isn't supported by stdlib re, so we walk
            # the text and parse manually).
            line_starts = [0]
            for m in re.finditer(r"\n", text):
                line_starts.append(m.end())
            for match in re.finditer(r"\bcap_context\s*=", text):
                # Find the enclosing function call: walk
                # backwards to the most-recent unmatched "("
                pos = match.start()
                depth = 0
                start = pos
                while start > 0:
                    start -= 1
                    ch = text[start]
                    if ch == ")":
                        depth += 1
                    elif ch == "(":
                        if depth == 0:
                            break
                        depth -= 1
                # Find matching closing paren
                end = match.start()
                depth = 0
                while end < len(text):
                    ch = text[end]
                    if ch == "(":
                        depth += 1
                    elif ch == ")":
                        if depth == 0:
                            break
                        depth -= 1
                    end += 1
                call_text = text[start : end + 1]
                # Skip the helper definitions themselves
                # (lines like ``def receipt_emitter_for`` —
                # they LOOK like they have cap_context but
                # they're the helper docs).
                line_no = sum(1 for s in line_starts if s <= pos)
                # Skip lines inside string literals (docstrings)
                # by checking the immediate surrounding context
                # for triple-quote markers — pragmatic
                # heuristic.
                preceding = text[max(0, pos - 600) : pos]
                if preceding.count('"""') % 2 == 1:
                    continue  # we're inside a docstring
                if _is_exempt(call_text):
                    continue
                if not _has_receipt_emitter_in_call(call_text):
                    violations.append(
                        (
                            str(source_file.relative_to(REPO_ROOT)),
                            line_no,
                            call_text[:200].replace("\n", " "),
                        )
                    )

        self.assertFalse(
            violations,
            "Found cap_context= call sites missing receipt_emitter=:\n"
            + "\n".join(f"  {f}:{ln}  {snippet}" for f, ln, snippet in violations)
            + "\n\nEvery user-facing AI dispatch site must emit a Trust "
            "Receipt OR be on EXEMPT_CALL_SITES with a recorded reason.",
        )


if __name__ == "__main__":
    unittest.main()
