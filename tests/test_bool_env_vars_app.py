# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression test for the bool env-var parsing fix landed during
PART 6 (2026-05-20).

Origin: PART 6 walk #1 setup discovered that
``HELPMEFINDTHEJOB_ALLOW_REGISTRATION=1`` silently failed to open
registration. Root cause: app.py used a strict ``.casefold() ==
"true"`` check that rejected ``"True"``, ``"TRUE"``, ``"1"``,
``"yes"``, ``"on"`` while ``env_compat.get_env_bool`` already accepted
all of those. Fix: route through ``get_env_bool`` for all three
inconsistent sites (``ALLOW_REGISTRATION``, ``COOKIE_SECURE``,
``legalReviewed``).

This test guards the fix by importing app.py in a subprocess with
each truthy token and verifying the constant evaluates to True. Run
in a subprocess (not in-process) because the constants are computed
at module-import time; ``importlib.reload`` works in principle but
``app`` has stateful side effects (data dir setup, DB migrations)
that we'd rather not re-fire repeatedly within one process.
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest

_TRUTHY_TOKENS = ("true", "True", "TRUE", "1", "yes", "YES", "on", "On")
_FALSY_TOKENS = ("false", "False", "0", "no", "off", "maybe", "")


def _resolve_constant(env_var: str, value: str, constant: str) -> bool:
    """Spawn a subprocess with ``env_var=value`` set and print the
    value of ``app.<constant>``. Returns the parsed bool."""
    env = dict(os.environ)
    env[env_var] = value
    # Use a tmp data dir so the test doesn't disturb the dev DB.
    env.setdefault("HELPMEFINDTHEJOB_DATA_DIR", "/tmp/test-bool-env-app")
    env.setdefault("HELPMEFINDTHEJOB_AUDIT_LOG_SALT", "test-static-salt-32chars-1234567890ab")
    proc = subprocess.run(
        [sys.executable, "-c", f"import app; print(app.{constant})"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    out = proc.stdout.strip()
    if out not in {"True", "False"}:
        raise AssertionError(
            f"subprocess for {env_var}={value!r} produced unexpected stdout: "
            f"{out!r}\nstderr: {proc.stderr}"
        )
    return out == "True"


class AllowRegistrationParsingTests(unittest.TestCase):
    """Verify HELPMEFINDTHEJOB_ALLOW_REGISTRATION accepts the permissive
    truthy set, matching env_compat.get_env_bool semantics."""

    def test_truthy_tokens_open_registration(self) -> None:
        for token in _TRUTHY_TOKENS:
            with self.subTest(token=token):
                self.assertTrue(
                    _resolve_constant(
                        "HELPMEFINDTHEJOB_ALLOW_REGISTRATION",
                        token,
                        "ALLOW_REGISTRATION",
                    ),
                    f"ALLOW_REGISTRATION should be True for token {token!r}",
                )

    def test_falsy_tokens_keep_registration_closed(self) -> None:
        for token in _FALSY_TOKENS:
            with self.subTest(token=token):
                self.assertFalse(
                    _resolve_constant(
                        "HELPMEFINDTHEJOB_ALLOW_REGISTRATION",
                        token,
                        "ALLOW_REGISTRATION",
                    ),
                    f"ALLOW_REGISTRATION should be False for token {token!r}",
                )


class CookieSecureParsingTests(unittest.TestCase):
    """Same permissive contract for HELPMEFINDTHEJOB_COOKIE_SECURE."""

    def test_truthy_tokens_enable_cookie_secure(self) -> None:
        for token in _TRUTHY_TOKENS:
            with self.subTest(token=token):
                self.assertTrue(
                    _resolve_constant(
                        "HELPMEFINDTHEJOB_COOKIE_SECURE",
                        token,
                        "COOKIE_SECURE",
                    ),
                    f"COOKIE_SECURE should be True for token {token!r}",
                )


if __name__ == "__main__":
    unittest.main()
