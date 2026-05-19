# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Regression tests for the env-compat shim
(``company_discovery.env_compat``). Added with the pre-submission
scope-tightening slice (PART 3)."""

from __future__ import annotations

import os
import unittest
import warnings

from company_discovery import env_compat


class _EnvSandbox(unittest.TestCase):
    """Mixin: snapshot + restore the env keys each test touches so
    parallel-test sandbox bleeds cannot mask drift."""

    KEYS = (
        "HELPMEFINDTHEJOB_TEST_VAR",
        "DIRECTJOB_TEST_VAR",
        "COMPANY_DISCOVERY_TEST_VAR",
        "HELPMEFINDTHEJOB_INT_VAR",
        "DIRECTJOB_INT_VAR",
        "HELPMEFINDTHEJOB_BOOL_VAR",
        "DIRECTJOB_BOOL_VAR",
    )

    def setUp(self) -> None:
        self._saved = {k: os.environ.get(k) for k in self.KEYS}
        for k in self.KEYS:
            os.environ.pop(k, None)
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class GetEnvTests(_EnvSandbox):
    """Core contract for ``get_env(new, legacy, default)``."""

    def test_new_name_only_set(self) -> None:
        os.environ["HELPMEFINDTHEJOB_TEST_VAR"] = "new-value"
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            value = env_compat.get_env("HELPMEFINDTHEJOB_TEST_VAR", "DIRECTJOB_TEST_VAR")
        self.assertEqual(value, "new-value")
        self.assertEqual([w for w in caught if issubclass(w.category, DeprecationWarning)], [])

    def test_legacy_name_only_set_emits_deprecation_warning(self) -> None:
        os.environ["DIRECTJOB_TEST_VAR"] = "legacy-value"
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            value = env_compat.get_env("HELPMEFINDTHEJOB_TEST_VAR", "DIRECTJOB_TEST_VAR")
        self.assertEqual(value, "legacy-value")
        dep = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        self.assertEqual(len(dep), 1)
        message = str(dep[0].message)
        self.assertIn("DIRECTJOB_TEST_VAR", message)
        self.assertIn("HELPMEFINDTHEJOB_TEST_VAR", message)

    def test_new_takes_precedence_when_both_set(self) -> None:
        os.environ["HELPMEFINDTHEJOB_TEST_VAR"] = "new-value"
        os.environ["DIRECTJOB_TEST_VAR"] = "legacy-value"
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            value = env_compat.get_env("HELPMEFINDTHEJOB_TEST_VAR", "DIRECTJOB_TEST_VAR")
        self.assertEqual(value, "new-value")
        # New name takes precedence ⇒ no deprecation warning.
        self.assertEqual([w for w in caught if issubclass(w.category, DeprecationWarning)], [])

    def test_default_returned_when_neither_set(self) -> None:
        value = env_compat.get_env(
            "HELPMEFINDTHEJOB_TEST_VAR", "DIRECTJOB_TEST_VAR", default="fallback"
        )
        self.assertEqual(value, "fallback")

    def test_default_none_when_neither_set_and_no_default(self) -> None:
        self.assertIsNone(env_compat.get_env("HELPMEFINDTHEJOB_TEST_VAR", "DIRECTJOB_TEST_VAR"))

    def test_empty_string_is_returned_not_treated_as_missing(self) -> None:
        # Per the docstring, the shim is transparent — it does not
        # strip or treat empty as missing. That is the caller's job.
        os.environ["HELPMEFINDTHEJOB_TEST_VAR"] = ""
        value = env_compat.get_env(
            "HELPMEFINDTHEJOB_TEST_VAR", "DIRECTJOB_TEST_VAR", default="fallback"
        )
        self.assertEqual(value, "")

    def test_multiple_legacy_names_tried_in_order(self) -> None:
        # Variables that lived under TWO legacy prefixes (the
        # COMPANY_DISCOVERY_* generation) accept an iterable.
        os.environ["COMPANY_DISCOVERY_TEST_VAR"] = "oldest-value"
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            value = env_compat.get_env(
                "HELPMEFINDTHEJOB_TEST_VAR",
                ("DIRECTJOB_TEST_VAR", "COMPANY_DISCOVERY_TEST_VAR"),
            )
        self.assertEqual(value, "oldest-value")
        dep = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        self.assertEqual(len(dep), 1)
        self.assertIn("COMPANY_DISCOVERY_TEST_VAR", str(dep[0].message))

    def test_first_legacy_takes_precedence_over_second(self) -> None:
        os.environ["DIRECTJOB_TEST_VAR"] = "directjob-value"
        os.environ["COMPANY_DISCOVERY_TEST_VAR"] = "older-value"
        # Reading a legacy env var legitimately emits DeprecationWarning
        # (the shim's documented behaviour); suppress that for the
        # precedence assertion so `python3 -W error` doesn't flag it.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            value = env_compat.get_env(
                "HELPMEFINDTHEJOB_TEST_VAR",
                ("DIRECTJOB_TEST_VAR", "COMPANY_DISCOVERY_TEST_VAR"),
            )
        self.assertEqual(value, "directjob-value")

    def test_no_legacy_name_means_no_fallback(self) -> None:
        os.environ["DIRECTJOB_TEST_VAR"] = "ignored"
        value = env_compat.get_env("HELPMEFINDTHEJOB_TEST_VAR")
        # No legacy passed ⇒ DIRECTJOB_TEST_VAR is not consulted.
        self.assertIsNone(value)


class GetEnvIntTests(_EnvSandbox):
    """Contract for the int-parsing wrapper."""

    def test_parses_int_from_new_name(self) -> None:
        os.environ["HELPMEFINDTHEJOB_INT_VAR"] = "42"
        self.assertEqual(
            env_compat.get_env_int("HELPMEFINDTHEJOB_INT_VAR", "DIRECTJOB_INT_VAR", default=0),
            42,
        )

    def test_parses_int_from_legacy_name(self) -> None:
        os.environ["DIRECTJOB_INT_VAR"] = "  17 "
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.assertEqual(
                env_compat.get_env_int("HELPMEFINDTHEJOB_INT_VAR", "DIRECTJOB_INT_VAR", default=0),
                17,
            )

    def test_unparseable_returns_default(self) -> None:
        os.environ["HELPMEFINDTHEJOB_INT_VAR"] = "not-a-number"
        self.assertEqual(
            env_compat.get_env_int("HELPMEFINDTHEJOB_INT_VAR", "DIRECTJOB_INT_VAR", default=99),
            99,
        )

    def test_empty_returns_default(self) -> None:
        os.environ["HELPMEFINDTHEJOB_INT_VAR"] = "   "
        self.assertEqual(
            env_compat.get_env_int("HELPMEFINDTHEJOB_INT_VAR", "DIRECTJOB_INT_VAR", default=12),
            12,
        )

    def test_missing_returns_default(self) -> None:
        self.assertEqual(
            env_compat.get_env_int("HELPMEFINDTHEJOB_INT_VAR", "DIRECTJOB_INT_VAR", default=7),
            7,
        )


class GetEnvBoolTests(_EnvSandbox):
    """Contract for the bool-parsing wrapper."""

    def test_true_tokens_yield_true(self) -> None:
        for token in ("true", "True", "TRUE", "1", "yes", "YES", "on", "On"):
            with self.subTest(token=token):
                os.environ["HELPMEFINDTHEJOB_BOOL_VAR"] = token
                self.assertTrue(
                    env_compat.get_env_bool(
                        "HELPMEFINDTHEJOB_BOOL_VAR", "DIRECTJOB_BOOL_VAR", False
                    ),
                    f"expected token {token!r} to parse as True",
                )

    def test_other_tokens_yield_false(self) -> None:
        for token in ("false", "0", "no", "off", "maybe", ""):
            with self.subTest(token=token):
                os.environ["HELPMEFINDTHEJOB_BOOL_VAR"] = token
                self.assertFalse(
                    env_compat.get_env_bool(
                        "HELPMEFINDTHEJOB_BOOL_VAR", "DIRECTJOB_BOOL_VAR", False
                    ),
                    f"expected token {token!r} to parse as False",
                )

    def test_missing_returns_default(self) -> None:
        self.assertTrue(
            env_compat.get_env_bool("HELPMEFINDTHEJOB_BOOL_VAR", "DIRECTJOB_BOOL_VAR", default=True)
        )
        self.assertFalse(
            env_compat.get_env_bool(
                "HELPMEFINDTHEJOB_BOOL_VAR", "DIRECTJOB_BOOL_VAR", default=False
            )
        )


if __name__ == "__main__":
    unittest.main()
