# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Property-based tests for :mod:`company_discovery.locale_parser`.

Closes part of phase2-backlog item #43 ("No mutation testing, no
property-based testing, no fuzzing beyond AEAD. Add Hypothesis-based
property tests for the locale parser, chat-router, journey state
machine.").

Example-based tests in ``test_phase11_locale_parser.py`` pin
specific tokens. These tests complement that by generating
thousands of inputs and asserting **invariants** that should hold
for ANY input:

1. ``is_yes`` / ``is_no`` / ``parse_yes_no`` never raise.
2. Output types are always correct (bool / Optional[str]).
3. No token is simultaneously yes AND no in the same locale.
4. Every token in YES_TOKENS_<lang> is recognised as yes.
5. Every token in NO_TOKENS_<lang> is recognised as no.
6. Behaviour is locale-deterministic: same (text, locale) → same result.
"""

from __future__ import annotations

import unittest

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from company_discovery.locale_parser import (
    NO_TOKENS_DE,
    NO_TOKENS_EN,
    YES_TOKENS_DE,
    YES_TOKENS_EN,
    is_no,
    is_yes,
    parse_yes_no,
)

# Common settings: don't shrink for hours; ~200 examples is plenty
# to surface invariant violations for these small surfaces.
_SETTINGS = settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


# A reasonable text generator: ASCII + common Latin-1 (covers German
# umlauts) + emoji-free unicode within the BMP. Limits length so
# property runs stay fast.
_TEXT_STRATEGY = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),  # exclude surrogates only
        min_codepoint=0x20,
        max_codepoint=0x024F,  # Latin Extended-B end
    ),
    min_size=0,
    max_size=80,
)

_LOCALE_STRATEGY = st.sampled_from(["en", "de", None, "fr", "EN", "  de  "])


class LocaleParserInvariants(unittest.TestCase):
    @_SETTINGS
    @given(text=_TEXT_STRATEGY, locale=_LOCALE_STRATEGY)
    def test_is_yes_never_raises_and_returns_bool(self, text, locale):
        result = is_yes(text, locale)
        self.assertIsInstance(result, bool)

    @_SETTINGS
    @given(text=_TEXT_STRATEGY, locale=_LOCALE_STRATEGY)
    def test_is_no_never_raises_and_returns_bool(self, text, locale):
        result = is_no(text, locale)
        self.assertIsInstance(result, bool)

    @_SETTINGS
    @given(text=_TEXT_STRATEGY, locale=_LOCALE_STRATEGY)
    def test_parse_yes_no_returns_valid_value(self, text, locale):
        result = parse_yes_no(text, locale)
        self.assertIn(result, (None, "yes", "no"))

    @_SETTINGS
    @given(text=_TEXT_STRATEGY, locale=_LOCALE_STRATEGY)
    def test_is_yes_and_is_no_are_mutually_exclusive(self, text, locale):
        """For any input, a token cannot be both yes AND no in the
        same locale. If it is, the parser is internally inconsistent."""

        yes = is_yes(text, locale)
        no = is_no(text, locale)
        self.assertFalse(
            yes and no,
            f"input {text!r} is BOTH yes and no in locale {locale!r}",
        )

    @_SETTINGS
    @given(text=_TEXT_STRATEGY, locale=_LOCALE_STRATEGY)
    def test_parse_yes_no_matches_is_yes_is_no(self, text, locale):
        """The composite parse_yes_no must be consistent with the
        two individual predicates. Catches drift between code paths."""

        result = parse_yes_no(text, locale)
        if result == "yes":
            self.assertTrue(is_yes(text, locale))
            self.assertFalse(is_no(text, locale))
        elif result == "no":
            self.assertFalse(is_yes(text, locale))
            self.assertTrue(is_no(text, locale))
        else:
            self.assertIsNone(result)


class EveryDeclaredYesTokenIsRecognised(unittest.TestCase):
    """Property: every token the module declares as YES_TOKENS_<lang>
    must be recognised by is_yes() with that locale. Catches drift
    between the constant list and the recognition function."""

    @_SETTINGS
    @given(token=st.sampled_from(sorted(YES_TOKENS_EN)))
    def test_every_yes_en_token_is_yes(self, token):
        self.assertTrue(is_yes(token, "en"))

    @_SETTINGS
    @given(token=st.sampled_from(sorted(YES_TOKENS_DE)))
    def test_every_yes_de_token_is_yes(self, token):
        self.assertTrue(is_yes(token, "de"))

    @_SETTINGS
    @given(token=st.sampled_from(sorted(NO_TOKENS_EN)))
    def test_every_no_en_token_is_no(self, token):
        self.assertTrue(is_no(token, "en"))

    @_SETTINGS
    @given(token=st.sampled_from(sorted(NO_TOKENS_DE)))
    def test_every_no_de_token_is_no(self, token):
        self.assertTrue(is_no(token, "de"))


class LocaleParserIsDeterministic(unittest.TestCase):
    """Property: same input twice → same output. Catches accidental
    statefulness."""

    @_SETTINGS
    @given(text=_TEXT_STRATEGY, locale=_LOCALE_STRATEGY)
    def test_is_yes_deterministic(self, text, locale):
        first = is_yes(text, locale)
        second = is_yes(text, locale)
        self.assertEqual(first, second)

    @_SETTINGS
    @given(text=_TEXT_STRATEGY, locale=_LOCALE_STRATEGY)
    def test_parse_yes_no_deterministic(self, text, locale):
        first = parse_yes_no(text, locale)
        second = parse_yes_no(text, locale)
        self.assertEqual(first, second)


class CaseInsensitivityProperty(unittest.TestCase):
    """The parser is documented as case-insensitive. Verify across
    random capitalisations."""

    @_SETTINGS
    @given(token=st.sampled_from(sorted(YES_TOKENS_EN)))
    def test_yes_tokens_match_uppercase(self, token):
        self.assertTrue(is_yes(token.upper(), "en"))

    @_SETTINGS
    @given(token=st.sampled_from(sorted(NO_TOKENS_EN)))
    def test_no_tokens_match_uppercase(self, token):
        self.assertTrue(is_no(token.upper(), "en"))

    @_SETTINGS
    @given(token=st.sampled_from(sorted(YES_TOKENS_DE)))
    def test_de_yes_tokens_match_titlecase(self, token):
        # Many German YES tokens are commonly capitalised (Ja → JA, ja)
        self.assertTrue(is_yes(token.title(), "de"))


if __name__ == "__main__":
    unittest.main()
