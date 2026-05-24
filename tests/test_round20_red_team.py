# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 backlog #29 — Red-team adversarial harness packaged as a
single-command unittest target.

The ad-hoc agents at ``tests/e2e/red_team/`` have always been
runnable via ``python -m tests.e2e.red_team`` against a live
deployment. This file wraps them as a standard unittest module so
``python -m unittest tests.test_round20_red_team`` works the same
way — meaning CI / pre-deploy gates can run them without learning
a separate invocation.

**Gating**: tests run ONLY when ``E2E_BASE_URL`` is set. Without
it, every test is SKIPPED (not failed) so the standard suite
remains environment-independent.

**Failure policy**: an agent's run fails the test if it produces
any ``CRITICAL`` or ``HIGH`` severity finding. ``MEDIUM`` and
``INFO`` findings are reported via test output but don't fail —
they're useful for triage without blocking the gate.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# Make the red_team package importable as a flat module set —
# mirrors the __main__.py pattern.
_HERE = Path(__file__).resolve().parent
_RED_TEAM_DIR = _HERE / "e2e" / "red_team"
if str(_RED_TEAM_DIR) not in sys.path:
    sys.path.insert(0, str(_RED_TEAM_DIR))

_BASE_URL_ENV_VAR = "E2E_BASE_URL"


def _base_url() -> str:
    return os.environ.get(_BASE_URL_ENV_VAR, "").strip()


@unittest.skipUnless(_base_url(), f"set {_BASE_URL_ENV_VAR} to run red-team agents")
class RedTeamAdversarialSuite(unittest.TestCase):
    """One test method per red-team agent. Each method spawns a
    fresh adversarial run against the configured BASE_URL and
    asserts no CRITICAL or HIGH finding surfaced.

    The agent set is hard-coded by name here rather than reflected
    from ALL_AGENTS — drift means an agent was added or removed,
    which the operator should surface explicitly when extending
    the gate.
    """

    @classmethod
    def setUpClass(cls) -> None:
        # Defer the import so collection works even when the
        # red_team package isn't importable in some test envs.
        from agents import ALL_AGENTS  # noqa: WPS433 - intentional late import
        from harness import RedTeamAgent  # noqa: WPS433

        cls._agents_by_name = {name: (persona, fn) for name, persona, fn in ALL_AGENTS}
        cls._RedTeamAgent = RedTeamAgent

    def _run_agent(self, agent_name: str) -> None:
        persona, runner = self._agents_by_name[agent_name]
        agent = self._RedTeamAgent(agent_name, persona)
        try:
            runner(agent)
        except Exception as exc:  # noqa: BLE001 - we report failures via assertions
            agent.report.errored = True
            agent.report.error_text = f"{type(exc).__name__}: {exc}"[:500]
        # Surface findings for visibility
        critical_or_high = [f for f in agent.report.findings if f.severity in ("CRITICAL", "HIGH")]
        medium_or_info = [f for f in agent.report.findings if f.severity in ("MEDIUM", "INFO")]
        if medium_or_info:
            print(
                f"\n[red-team {agent_name}] {len(medium_or_info)} non-blocking findings:",
                file=sys.stderr,
            )
            for finding in medium_or_info:
                print(
                    f"  [{finding.severity}] {finding.title} — {finding.detail[:200]}",
                    file=sys.stderr,
                )
        # Run-level error = fail
        self.assertFalse(
            agent.report.errored,
            f"Agent {agent_name} crashed: {agent.report.error_text}",
        )
        # CRITICAL or HIGH finding = fail
        self.assertFalse(
            critical_or_high,
            f"Agent {agent_name} produced {len(critical_or_high)} CRITICAL/HIGH findings: "
            + "; ".join(f"[{f.severity}] {f.title}" for f in critical_or_high),
        )

    def test_nina_perfectionist(self) -> None:
        self._run_agent("Nina")

    def test_tobias_injector(self) -> None:
        self._run_agent("Tobias")

    def test_mehmet_multilingual(self) -> None:
        self._run_agent("Mehmet")

    def test_olga_impatient(self) -> None:
        self._run_agent("Olga")

    def test_anna_abuser(self) -> None:
        self._run_agent("Anna")

    def test_pavel_persona_pivoter(self) -> None:
        self._run_agent("Pavel")

    def test_boris_boundary_tester(self) -> None:
        self._run_agent("Boris")

    def test_greta_marathoner(self) -> None:
        self._run_agent("Greta")

    def test_klaus_slash_spammer(self) -> None:
        self._run_agent("Klaus")

    def test_yusuf_jd_injector(self) -> None:
        self._run_agent("Yusuf")


class RedTeamRegistryDriftGuard(unittest.TestCase):
    """Catches accidental drift between the ALL_AGENTS list and the
    test methods above. If you add a new agent to ALL_AGENTS, you
    MUST also add a matching test method here — this test fails
    until you do."""

    def test_every_agent_has_a_test_method(self) -> None:
        from agents import ALL_AGENTS

        # Every name in ALL_AGENTS must have a test_<name>_<persona>
        # method in RedTeamAdversarialSuite.
        method_names = {
            attr
            for attr in dir(RedTeamAdversarialSuite)
            if attr.startswith("test_") and attr != "test_every_agent_has_a_test_method"
        }
        for name, _persona, _fn in ALL_AGENTS:
            slug = name.lower()
            matching = [m for m in method_names if m.startswith(f"test_{slug}_")]
            self.assertTrue(
                matching,
                f"Agent {name} has no matching test_{slug}_* method in "
                f"RedTeamAdversarialSuite — add one when extending the harness",
            )


if __name__ == "__main__":
    unittest.main()
