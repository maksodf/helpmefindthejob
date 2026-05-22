# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Test package marker.

Makes ``tests/`` a regular package (rather than a namespace package)
which is the canonical layout for unittest discovery and avoids
subtle import-order surprises with third-party tooling (pytest,
coverage, mypy --strict).

We also set a deterministic ``HELPMEFINDTHEJOB_AUDIT_SALT`` here for
any consumer that imports the package directly — e.g. pytest, which
auto-imports test packages before running tests. Note: stdlib
``unittest.TestLoader.discover()`` does **not** import the test
package, so this setdefault is a no-op for the canonical
``python3 -m unittest discover -s tests`` invocation. The actual
test-suite suppression of the dev-mode missing-salt warning is
achieved by ``company_discovery.audit_log._resolve_salt`` now using
``warnings.warn(UserWarning)`` instead of a raw stderr print — test
runners filter UserWarning by default.

Tests that **need** to exercise the missing-salt path
(``tests.test_phase13_audit_log.SaltFailFastTests``) snapshot, clear,
and restore both ``HELPMEFINDTHEJOB_AUDIT_SALT`` and the legacy
``HELPMEFINDTHEJOB_AUDIT_SALT`` in their own ``setUp`` / ``addCleanup`` —
so this default does not interfere with them.

PART A.3 of the 2026-05-19 deep-audit sweep.
"""

from __future__ import annotations

import base64
import os

# A 32-byte all-zero salt encoded as base64. Deterministic + obviously
# non-secret + clearly identifiable as a test fixture in any log line
# that captures it. Setting it via setdefault preserves any value the
# operator (or CI) already set.
_DETERMINISTIC_TEST_SALT = base64.b64encode(b"\x00" * 32).decode("ascii")
os.environ.setdefault("HELPMEFINDTHEJOB_AUDIT_SALT", _DETERMINISTIC_TEST_SALT)
