# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Property-based tests for :mod:`company_discovery.chat_router`.

Closes part of phase2-backlog item #43. Generates thousands of
random inputs against the slash-command parser, keyword router,
and arg-extractor; asserts invariants that should hold for any
input regardless of content / length / casing / locale.
"""

from __future__ import annotations

import string
import unittest

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from company_discovery import chat_router
from company_discovery.chat_router import (
    REGISTRY,
    extract_keyword_args,
    keyword_route,
    parse_slash_command,
)

_SETTINGS = settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

# Free-form user input — covers EN + DE + punctuation + emoji-free
# unicode. The MAX_MESSAGE_CHARS cap in journey.py is 5000; we
# generate up to 200 chars for fast property runs.
_MESSAGE_STRATEGY = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),
        min_codepoint=0x20,
        max_codepoint=0x024F,
    ),
    min_size=0,
    max_size=200,
)

# Slash-command-like inputs — bias the generator towards strings
# that LOOK like commands so we explore the slash-path more.
_SLASH_PREFIX = st.sampled_from(["/", "  /", "\t/", "/ ", "/\t"])
_SLASH_BODY = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),
        min_codepoint=0x20,
        max_codepoint=0x024F,
    ),
    min_size=1,
    max_size=80,
)
_SLASH_STRATEGY = st.builds(lambda prefix, body: prefix + body, _SLASH_PREFIX, _SLASH_BODY)


# Known command names from the registry (for arg-extraction tests
# where command_name needs to be valid).
_KNOWN_COMMANDS = sorted(REGISTRY.keys())


class ParseSlashCommandInvariants(unittest.TestCase):
    """parse_slash_command must:
    - Never raise on any input
    - Return None OR (str, str)
    - For non-/ inputs: always None
    - The returned command name must be a registered command
    """

    @_SETTINGS
    @given(message=_MESSAGE_STRATEGY)
    def test_never_raises_returns_correct_type(self, message):
        result = parse_slash_command(message)
        if result is not None:
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 2)
            self.assertIsInstance(result[0], str)
            self.assertIsInstance(result[1], str)

    @_SETTINGS
    @given(message=_MESSAGE_STRATEGY)
    def test_non_slash_input_returns_none(self, message):
        if message.strip() and not message.strip().startswith("/"):
            self.assertIsNone(parse_slash_command(message))

    @_SETTINGS
    @given(message=_MESSAGE_STRATEGY)
    def test_returned_command_name_is_registered(self, message):
        result = parse_slash_command(message)
        if result is not None:
            cmd_name, _ = result
            self.assertIn(
                cmd_name,
                _KNOWN_COMMANDS,
                f"parse_slash_command returned unregistered command {cmd_name!r}",
            )

    @_SETTINGS
    @given(message=_SLASH_STRATEGY)
    def test_slash_inputs_either_resolve_or_return_none(self, message):
        """All slash-prefixed inputs return either a tuple or None
        — they never raise, never return malformed values."""

        result = parse_slash_command(message)
        self.assertTrue(result is None or isinstance(result, tuple))


class KeywordRouteInvariants(unittest.TestCase):
    """keyword_route must:
    - Never raise
    - Return None OR a registered command name
    - Empty / whitespace-only inputs return None
    """

    @_SETTINGS
    @given(message=_MESSAGE_STRATEGY)
    def test_never_raises_returns_correct_type(self, message):
        result = keyword_route(message)
        self.assertTrue(result is None or isinstance(result, str))

    @_SETTINGS
    @given(message=_MESSAGE_STRATEGY)
    def test_returned_command_name_is_registered(self, message):
        result = keyword_route(message)
        if result is not None:
            self.assertIn(
                result,
                _KNOWN_COMMANDS,
                f"keyword_route returned unregistered command {result!r}",
            )

    @_SETTINGS
    @given(message=st.sampled_from(["", " ", "\t", "\n", "    ", " \t \n "]))
    def test_empty_or_whitespace_returns_none(self, message):
        self.assertIsNone(keyword_route(message))


class ExtractKeywordArgsInvariants(unittest.TestCase):
    """extract_keyword_args must:
    - Never raise on any (command_name, message)
    - Always return a dict[str, str]
    - For unknown commands, return an empty dict (graceful)
    """

    @_SETTINGS
    @given(
        command_name=st.text(alphabet=string.ascii_lowercase + "_", min_size=0, max_size=30),
        message=_MESSAGE_STRATEGY,
    )
    def test_returns_dict_of_str_str(self, command_name, message):
        result = extract_keyword_args(command_name, message)
        self.assertIsInstance(result, dict)
        for key, value in result.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, str)

    @_SETTINGS
    @given(
        command_name=st.sampled_from(_KNOWN_COMMANDS),
        message=_MESSAGE_STRATEGY,
    )
    def test_known_command_never_raises(self, command_name, message):
        # Just call and let any uncaught exception fail the test.
        extract_keyword_args(command_name, message)


class ParseSlashAndKeywordAreConsistent(unittest.TestCase):
    """If parse_slash_command resolves a slash to a command name,
    feeding the SAME slash-stripped message back into keyword_route
    must NOT return a DIFFERENT command name. (Either same or None.)
    This protects against the routing layer choosing two different
    commands for the same input via the two code paths."""

    @_SETTINGS
    @given(message=_SLASH_STRATEGY)
    def test_slash_and_keyword_dont_disagree(self, message):
        slash_result = parse_slash_command(message)
        keyword_result = keyword_route(message)
        if slash_result is not None and keyword_result is not None:
            self.assertEqual(
                slash_result[0],
                keyword_result,
                "slash and keyword routers disagree on the same input",
            )


class DeterministicProperty(unittest.TestCase):
    """Same input → same output. Catches accidental statefulness."""

    @_SETTINGS
    @given(message=_MESSAGE_STRATEGY)
    def test_parse_slash_command_deterministic(self, message):
        self.assertEqual(parse_slash_command(message), parse_slash_command(message))

    @_SETTINGS
    @given(message=_MESSAGE_STRATEGY)
    def test_keyword_route_deterministic(self, message):
        self.assertEqual(keyword_route(message), keyword_route(message))


if __name__ == "__main__":
    unittest.main()
