# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Tests for :mod:`company_discovery.locale_parser`.

Pins the locale-aware yes/no token recognition for the two supported
locales (``en`` and ``de``) plus the regression test that keeps the
``journey.py`` ad-hoc intent-detection regex in sync with the canonical
``NEGATIVE_SEARCH_PREFIX_RE`` from the parser module.
"""

from __future__ import annotations

import unittest
from typing import ClassVar

from company_discovery import locale_parser
from company_discovery.locale_parser import (
    NEGATIVE_SEARCH_PREFIX_RE,
    NO_TOKENS_DE,
    NO_TOKENS_EN,
    YES_TOKENS_DE,
    YES_TOKENS_EN,
    is_no,
    is_yes,
    parse_yes_no,
)


class EnglishTokenTests(unittest.TestCase):
    AFFIRMATIVES: ClassVar[list[str]] = ["yes", "yeah", "yep", "yup", "ok", "okay", "sure", "y"]
    NEGATIVES: ClassVar[list[str]] = ["no", "nope", "nah", "n"]

    def test_all_affirmatives_recognised(self) -> None:
        for token in self.AFFIRMATIVES:
            self.assertTrue(is_yes(token, "en"), msg=token)
            self.assertEqual(parse_yes_no(token, "en"), "yes", msg=token)

    def test_all_negatives_recognised(self) -> None:
        for token in self.NEGATIVES:
            self.assertTrue(is_no(token, "en"), msg=token)
            self.assertEqual(parse_yes_no(token, "en"), "no", msg=token)

    def test_german_only_affirmative_not_recognised_in_en(self) -> None:
        # 'ja' is a German affirmative; it must not match in 'en'.
        self.assertFalse(is_yes("ja", "en"))
        self.assertIsNone(parse_yes_no("ja", "en"))


class GermanTokenTests(unittest.TestCase):
    AFFIRMATIVES: ClassVar[list[str]] = [
        "ja",
        "jo",
        "jep",
        "jepp",
        "doch",
        "klar",
        "bestimmt",
        "sicher",
    ]
    NEGATIVES: ClassVar[list[str]] = ["nein", "nö", "ne", "ne-ne", "niemals"]

    def test_all_affirmatives_recognised(self) -> None:
        for token in self.AFFIRMATIVES:
            self.assertTrue(is_yes(token, "de"), msg=token)
            self.assertEqual(parse_yes_no(token, "de"), "yes", msg=token)

    def test_all_negatives_recognised(self) -> None:
        for token in self.NEGATIVES:
            self.assertTrue(is_no(token, "de"), msg=token)
            self.assertEqual(parse_yes_no(token, "de"), "no", msg=token)

    def test_english_only_negative_not_recognised_in_de(self) -> None:
        # 'nope' is an English negative; it must not match in 'de'.
        self.assertFalse(is_no("nope", "de"))
        self.assertIsNone(parse_yes_no("nope", "de"))


class LocaleNormalisationTests(unittest.TestCase):
    def test_full_locale_tag_reduced(self) -> None:
        self.assertTrue(is_yes("ja", "de_DE"))
        self.assertTrue(is_yes("ja", "de-DE"))
        self.assertTrue(is_yes("ja", "DE"))
        self.assertTrue(is_yes("yes", "en_US"))
        self.assertTrue(is_yes("yes", "en-GB"))

    def test_unknown_locale_falls_back_to_en(self) -> None:
        # 'fr' is not supported; should fall back to 'en' rules.
        self.assertTrue(is_yes("yes", "fr"))
        self.assertFalse(is_yes("ja", "fr"))

    def test_empty_locale_treats_as_en(self) -> None:
        self.assertTrue(is_yes("yes", ""))
        self.assertTrue(is_yes("yes", None))


class TokenNormalisationTests(unittest.TestCase):
    def test_case_insensitive(self) -> None:
        self.assertTrue(is_yes("YES", "en"))
        self.assertTrue(is_yes("Yes", "en"))
        self.assertTrue(is_yes("JA", "de"))

    def test_trailing_punctuation_stripped(self) -> None:
        for variant in ["yes.", "yes!", "yes,", "yes;", "yes:"]:
            self.assertTrue(is_yes(variant, "en"), msg=variant)
        for variant in ["nein!", "nö.", "ja!"]:
            self.assertTrue(parse_yes_no(variant, "de") is not None, msg=variant)

    def test_surrounding_whitespace_stripped(self) -> None:
        self.assertTrue(is_yes("  yes  ", "en"))
        self.assertTrue(is_no("\tnein\n", "de"))

    def test_empty_input(self) -> None:
        self.assertFalse(is_yes("", "en"))
        self.assertFalse(is_no("", "en"))
        self.assertIsNone(parse_yes_no("", "en"))
        self.assertFalse(is_yes(None, "en"))


class NegativeSearchPrefixRegexTests(unittest.TestCase):
    """Pin the cross-locale '<no-token> + search-verb' compound regex
    behaviour, and assert that every negative token in the canonical
    sets is covered by it. This is the source-of-truth check for the
    journey-state-machine intent detection that uses the same shape."""

    def test_matches_each_negative_token_with_search_verb(self) -> None:
        for token in NO_TOKENS_EN | NO_TOKENS_DE:
            message = f"{token} search for engineer"
            self.assertTrue(
                NEGATIVE_SEARCH_PREFIX_RE.match(message),
                msg=f"failed to match {token!r}",
            )

    def test_matches_german_search_verbs(self) -> None:
        for verb in ("suche", "finde"):
            self.assertTrue(NEGATIVE_SEARCH_PREFIX_RE.match(f"nein {verb} stelle"))
            self.assertTrue(NEGATIVE_SEARCH_PREFIX_RE.match(f"nope {verb} stelle"))

    def test_does_not_match_bare_negative(self) -> None:
        # A bare 'no' without a search-verb following must not fire the
        # intent — the user is just disagreeing, not redirecting.
        self.assertIsNone(NEGATIVE_SEARCH_PREFIX_RE.match("no"))
        self.assertIsNone(NEGATIVE_SEARCH_PREFIX_RE.match("nein"))
        self.assertIsNone(NEGATIVE_SEARCH_PREFIX_RE.match("nope please stop"))

    def test_does_not_match_affirmative_prefix(self) -> None:
        # 'yes search for X' is not a redirect — that's a confirmation.
        self.assertIsNone(NEGATIVE_SEARCH_PREFIX_RE.match("yes search for engineer"))
        self.assertIsNone(NEGATIVE_SEARCH_PREFIX_RE.match("ja suche stelle"))


class JourneyRegexStaysInSyncTests(unittest.TestCase):
    """Regression guard: the ad-hoc negative-search-prefix regex inside
    ``company_discovery.journey`` must accept exactly the union of
    NO_TOKENS_EN and NO_TOKENS_DE before a search verb. If a future
    refactor adds a new negative token to ``locale_parser`` but forgets
    to update ``journey.py``, this test fires."""

    def test_journey_module_regex_accepts_all_canonical_negatives(self) -> None:
        # Import the looks_like_new_search_intent function which uses the
        # journey-side regex. Walking all canonical negatives should yield
        # True for each.
        from company_discovery.journey import looks_like_new_search_intent

        for token in NO_TOKENS_EN | NO_TOKENS_DE:
            message = f"{token} search for engineer"
            self.assertTrue(
                looks_like_new_search_intent(message, "review"),
                msg=f"journey regex missed {token!r}",
            )


if __name__ == "__main__":
    unittest.main()
