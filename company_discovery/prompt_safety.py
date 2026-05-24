# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Canonical prompt-injection sanitiser (Phase 2 backlog #45).

Three modules currently ship copy-pasted variants of the same
``_sanitize_for_prompt`` helper:

- :mod:`company_discovery.motivation_letter`
- :mod:`company_discovery.cv_consult`
- :mod:`company_discovery.journey`

Drift between them creates exactly the bug we're trying to avoid:
an injection seed neutralised in one path is open in another.
This module is the single source of truth. The three local helpers
re-export the canonical implementation so callers don't need to
change, but every new caller should import from here directly.

Defense in depth: this is the OUTER perimeter (input-side cleanup).
The INNER perimeter is the system-prompt's data-tag pattern
(``<applicant_cv> … </applicant_cv>``) plus a strict output parser.
Neither replaces the other.
"""

from __future__ import annotations

import re

# Longest field we ever inline. CV bodies can be long; we cap at
# 32 000 chars (~8000 tokens) so a maliciously huge payload can't
# push our own instructions past the model's context cliff.
DEFAULT_MAX_FIELD_CHARS = 32_000

# Tighter cap for short fields (job title, location, etc.) — these
# should never be more than a couple hundred chars in legitimate
# use.
SHORT_FIELD_CHARS = 500


# The eight injection-seed patterns we neutralise. Order matters:
# the longer / more-specific patterns run first so they don't get
# half-rewritten by a later pattern.
_INJECTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Classic "ignore previous instructions" — English variants
    (
        re.compile(r"(?i)ignore (?:all )?previous (?:instructions?|prompts?)"),
        "[neutralised:ignore-previous]",
    ),
    # "disregard the above" / "disregard previous" — English
    (
        re.compile(r"(?i)disregard (?:the )?(?:above|previous|prior)"),
        "[neutralised:disregard]",
    ),
    # Role-play takeover — "you are now an evil AI" etc.
    (
        re.compile(r"(?i)you are (?:now )?an? [a-zA-ZÄÖÜäöüß0-9_\-]+"),
        "[neutralised:role-play]",
    ),
    # System-prompt spoofing — "System:" / "SYSTEM:" / "[SYSTEM]"
    (
        re.compile(r"(?i)\bsystem\s*[:=]"),
        "[neutralised:system-claim]:",
    ),
    # Bracketed role tag — "[SYSTEM]", "[ASSISTANT]", "[USER]"
    (
        re.compile(r"(?i)\[(?:system|assistant|user)\]"),
        "[neutralised:role-tag]",
    ),
    # Common German variants — DACH user base has many German CVs.
    # Allow both -en (dative/accusative plural) and -e (nominative
    # plural) forms; both are grammatical for "vorherige[n]
    # Anweisungen" depending on case.
    (
        re.compile(
            r"(?i)ignoriere (?:alle )?(?:vorherigen?|vorigen?) (?:anweisungen|instruktionen)"
        ),
        "[neutralised:ignoriere-vorherige]",
    ),
    (
        re.compile(r"(?i)du bist (?:jetzt|nun) (?:ein|eine) [a-zA-ZÄÖÜäöüß0-9_\-]+"),
        "[neutralised:rolle-uebernahme]",
    ),
    # XML-ish tag injection — closing our data tags + re-opening
    # something else. We strip rather than rewrite so the structure
    # of the inner perimeter doesn't get confused.
    (
        re.compile(r"</?(?:applicant_cv|job_posting|system|assistant|user)\s*/?>", re.IGNORECASE),
        "[neutralised:tag-injection]",
    ),
)

# Control characters that can flip downstream rendering or hide
# content from the test inspection. We strip them entirely.
# - C0 controls (\x00-\x1f minus \t \n \r) and DEL (\x7f)
# - Quality-audit addition (2026-05-21): Unicode bidi controls
#   (Trojan Source / CVE-2021-42574). These let an attacker
#   render benign text on screen while injecting different
#   tokens into the LLM context:
#     U+202A LEFT-TO-RIGHT EMBEDDING
#     U+202B RIGHT-TO-LEFT EMBEDDING
#     U+202C POP DIRECTIONAL FORMATTING
#     U+202D LEFT-TO-RIGHT OVERRIDE
#     U+202E RIGHT-TO-LEFT OVERRIDE
#     U+2066 LEFT-TO-RIGHT ISOLATE
#     U+2067 RIGHT-TO-LEFT ISOLATE
#     U+2068 FIRST STRONG ISOLATE
#     U+2069 POP DIRECTIONAL ISOLATE
# - Zero-width characters that can hide injection tokens between
#   benign-looking letters:
#     U+200B ZERO WIDTH SPACE
#     U+200C ZERO WIDTH NON-JOINER
#     U+200D ZERO WIDTH JOINER
#     U+FEFF ZERO WIDTH NO-BREAK SPACE / BOM
_CONTROL_CHAR_PATTERN = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f"
    r"‪-‮⁦-⁩"
    r"​-‍﻿]"
)

# Raw markdown headers (h1-h6) that would collide with our own
# SECTION markers. We strip just the leading ``#`` chars; the text
# content is preserved.
_MD_HEADER_PATTERN = re.compile(r"^#{1,6}\s+", flags=re.MULTILINE)


def sanitize_for_prompt(text: str | None, limit: int = DEFAULT_MAX_FIELD_CHARS) -> str:
    """Canonical prompt-injection sanitiser.

    Applies, in order:

    1. Strip control characters (zero-width and other footguns)
    2. Neutralise the eight known injection seeds (EN + DE)
    3. Strip markdown-header prefixes that could be confused with
       our own prompt section markers
    4. Cap at ``limit`` chars

    Idempotent: applying twice returns the same string as applying
    once. ``None`` / empty input → empty string.
    """

    if not text:
        return ""
    text = _CONTROL_CHAR_PATTERN.sub("", text)
    for pattern, replacement in _INJECTION_PATTERNS:
        text = pattern.sub(replacement, text)
    text = _MD_HEADER_PATTERN.sub("", text)
    if len(text) > limit:
        text = text[:limit]
    return text


def sanitize_short_field(text: str | None) -> str:
    """Convenience: sanitize_for_prompt with the short-field cap."""

    return sanitize_for_prompt(text, limit=SHORT_FIELD_CHARS)


def looks_like_injection_attempt(text: str | None) -> bool:
    """True iff ``text`` matches any of the known injection seeds.

    Useful for logging / alerting; the sanitiser already neutralises
    matches before they reach the LLM, so this function is purely a
    detection hook.
    """

    if not text:
        return False
    for pattern, _ in _INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False
