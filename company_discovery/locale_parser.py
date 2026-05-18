# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Locale-aware yes/no parser.

Replaces the ad-hoc regex token matching scattered across
``company_discovery.journey``. One canonical set of affirmatives and
negatives per supported locale, exposed via :func:`is_yes`,
:func:`is_no`, and :func:`parse_yes_no`.

Supported locales (Week 1 scope):

* ``en`` — English
* ``de`` — German (formal + common colloquial variants)

Adding a new locale: extend the ``YES_TOKENS_<lang>`` and
``NO_TOKENS_<lang>`` constants below and the ``_LOCALE_SETS`` dispatch
map. The parser stays simple-set-membership; we deliberately do not
attempt to parse complex German negation grammar at this layer.

The parser is the canonical source of yes/no token sets. Any code in
the journey state machine that needs to match a negative or affirmative
should consult these sets via the regex helpers exposed at the bottom
of this module rather than hard-coding tokens.
"""

from __future__ import annotations

import re
from typing import Final

# --- Canonical token sets -------------------------------------------------

YES_TOKENS_EN: Final[frozenset[str]] = frozenset(
    {
        "yes",
        "yeah",
        "yep",
        "yup",
        "ok",
        "okay",
        "sure",
        "y",
    }
)

NO_TOKENS_EN: Final[frozenset[str]] = frozenset(
    {
        "no",
        "nope",
        "nah",
        "n",
    }
)

# German — formal + the most common colloquial / regional variants the
# project's partner orgs (MBE / IQ-Netzwerk / RINWA) report seeing in
# day-to-day counselling.
YES_TOKENS_DE: Final[frozenset[str]] = frozenset(
    {
        # Formal
        "ja",
        # Colloquial / regional affirmatives
        "jo",
        "jep",
        "jepp",
        "doch",
        "klar",
        "bestimmt",
        "sicher",
    }
)

NO_TOKENS_DE: Final[frozenset[str]] = frozenset(
    {
        # Formal
        "nein",
        # Colloquial / regional negatives
        "nö",
        "ne",
        "ne-ne",
        "niemals",
    }
)


_LOCALE_SETS: Final[dict[str, tuple[frozenset[str], frozenset[str]]]] = {
    "en": (YES_TOKENS_EN, NO_TOKENS_EN),
    "de": (YES_TOKENS_DE, NO_TOKENS_DE),
}


# --- Normalisation --------------------------------------------------------

# Strip trailing punctuation users naturally type after a yes/no token:
# "ja!", "no, search for X", "yep." etc.
_TRAILING_PUNCT_CHARS: Final[str] = ".,!?;:"


def _normalize_locale(locale: str | None) -> str:
    """Reduce ``en_US`` / ``en-GB`` / ``EN`` to ``en``. Unknown locales
    fall back to ``en`` so a missing locale tag never silently switches
    matching to the wrong language."""

    if not locale:
        return "en"
    head = locale.split("_", 1)[0].split("-", 1)[0]
    head = head.strip().lower()
    return head if head in _LOCALE_SETS else "en"


def _normalize_token(text: str | None) -> str:
    if not text:
        return ""
    return text.strip().strip(_TRAILING_PUNCT_CHARS).lower()


# --- Public API -----------------------------------------------------------


def is_yes(text: str | None, locale: str | None = "en") -> bool:
    """True iff ``text`` is a recognised affirmative for ``locale``.

    Locale-aware: only the locale's affirmative set is consulted. A
    colloquial German ``jo`` returns True under ``de`` and False under
    ``en`` (since ``jo`` is not an English affirmative). This is
    deliberate: cross-locale matching would conflict with tokens that
    have different meanings in different languages.
    """

    norm = _normalize_token(text)
    if not norm:
        return False
    yes_tokens, _ = _LOCALE_SETS[_normalize_locale(locale)]
    return norm in yes_tokens


def is_no(text: str | None, locale: str | None = "en") -> bool:
    """True iff ``text`` is a recognised negative for ``locale``."""

    norm = _normalize_token(text)
    if not norm:
        return False
    _, no_tokens = _LOCALE_SETS[_normalize_locale(locale)]
    return norm in no_tokens


def parse_yes_no(text: str | None, locale: str | None = "en") -> str | None:
    """Return ``'yes'``, ``'no'``, or ``None`` (when the token is neither
    a recognised affirmative nor a recognised negative for the locale)."""

    if is_yes(text, locale):
        return "yes"
    if is_no(text, locale):
        return "no"
    return None


# --- Regex helpers for compound matching ---------------------------------


def _alternation(tokens: frozenset[str]) -> str:
    """Build a regex-safe ``a|b|c`` from a token set. Longer tokens first
    so ``ne-ne`` is matched before ``ne``."""

    sorted_tokens = sorted(tokens, key=len, reverse=True)
    return "|".join(re.escape(t) for t in sorted_tokens)


def _no_tokens_alternation(*locales: str) -> str:
    """Union of negative token alternations across the given locales.

    Used to build compound regexes (e.g. ``<no-token> + search-verb``)
    that should fire across English and German without hard-coding the
    token list at the call site."""

    union: set[str] = set()
    for loc in locales or ("en", "de"):
        _, no_tokens = _LOCALE_SETS[_normalize_locale(loc)]
        union |= no_tokens
    sorted_tokens = sorted(union, key=len, reverse=True)
    return "|".join(re.escape(t) for t in sorted_tokens)


def _yes_tokens_alternation(*locales: str) -> str:
    """Union of affirmative token alternations across the given locales."""

    union: set[str] = set()
    for loc in locales or ("en", "de"):
        yes_tokens, _ = _LOCALE_SETS[_normalize_locale(loc)]
        union |= yes_tokens
    sorted_tokens = sorted(union, key=len, reverse=True)
    return "|".join(re.escape(t) for t in sorted_tokens)


# Pre-built compound regex shared with :mod:`company_discovery.journey`
# for "negative-prefix + search-verb" intent detection. Cross-locale
# (matches English and German negatives) because the search-verb half
# of the pattern is itself cross-locale.
NEGATIVE_SEARCH_PREFIX_RE: Final[re.Pattern[str]] = re.compile(
    rf"^\s*(?:{_no_tokens_alternation('en', 'de')})\s*[,!.]?\s+"
    r"(?:search|find|look|suche|finde)\b",
    re.IGNORECASE,
)
