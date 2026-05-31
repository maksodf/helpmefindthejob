# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Article 14 deployer-wide AI kill-switch.

`HELPMEFINDTHEJOB_DETERMINISTIC_ONLY=true` must force every AI invocation
(non-streaming and streaming) onto the deterministic / no-AI handoff path,
regardless of the configured provider — the emergency control the compliance
pack (human-oversight-guide.md, deployer-operating-manual.md, the FRIA R5
mitigation, GDPR Art-35 DPIA) and the grant application's Risks section
document. This test pins the invariant so the documented control cannot
silently regress.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from company_discovery import analysis  # noqa: E402
from company_discovery.ai_providers import AIProviderConfig  # noqa: E402

_VAR = "HELPMEFINDTHEJOB_DETERMINISTIC_ONLY"


class AiKillSwitchTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = os.environ.get(_VAR)

    def tearDown(self) -> None:
        if self._saved is None:
            os.environ.pop(_VAR, None)
        else:
            os.environ[_VAR] = self._saved

    def test_default_off_does_not_short_circuit(self) -> None:
        """Unset (default): the kill-switch guard does NOT fire — a manual
        provider shows its own handoff message, not the kill-switch one."""
        os.environ.pop(_VAR, None)
        res = analysis._dispatch_provider_impl(
            "prompt", AIProviderConfig(provider_id="manual", invocation_mode="manual"), ""
        )
        self.assertEqual(res.status, "handoff_required")
        self.assertNotIn("DETERMINISTIC_ONLY", res.error or "")

    def test_kill_switch_forces_no_ai_nonstreaming(self) -> None:
        """Set: even a real API provider is short-circuited to the no-AI
        handoff path before any credential/network step."""
        os.environ[_VAR] = "true"
        res = analysis._dispatch_provider_impl(
            "prompt", AIProviderConfig(provider_id="openai", invocation_mode="api"), ""
        )
        self.assertEqual(res.status, "handoff_required")
        self.assertIn("DETERMINISTIC_ONLY", res.error or "")

    def test_kill_switch_forces_no_ai_streaming(self) -> None:
        """Set: the streaming dispatch yields a single ('final', handoff)
        event — no token stream, no provider call."""
        os.environ[_VAR] = "1"
        events = list(
            analysis._dispatch_provider_streaming_impl(
                "prompt", AIProviderConfig(provider_id="openai", invocation_mode="api"), ""
            )
        )
        self.assertEqual(len(events), 1)
        kind, result = events[0]
        self.assertEqual(kind, "final")
        self.assertEqual(result.status, "handoff_required")
        self.assertIn("DETERMINISTIC_ONLY", result.error or "")


if __name__ == "__main__":
    unittest.main()
