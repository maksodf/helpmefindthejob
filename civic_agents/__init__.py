# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Typed specialist-agent contracts + a deterministic planner.

This package wires the multi-agent layer that ``docs/agent-architecture.md`` §2
documents as the "Phase-2 target": a planner decomposes a user goal into
sub-goals and routes each to a specialist agent across a typed, JSON-Schema
contract, emitting a trust receipt into the Article-12 audit chain at every
handoff. Specialists are functions today (some in-process, some bound to the
federated ``mesh/`` HTTP agents); the contract is transport-independent.
"""

from __future__ import annotations

from civic_agents.contracts import (
    CONTRACTS,
    ContractViolation,
    SpecialistContract,
    get_contract,
)
from civic_agents.planner import (
    CANONICAL_ORDER,
    ExecutionTrace,
    Goal,
    Plan,
    PlanStep,
    StepResult,
    decompose,
    execute,
    run,
)

__all__ = [
    "CONTRACTS",
    "ContractViolation",
    "SpecialistContract",
    "get_contract",
    "CANONICAL_ORDER",
    "ExecutionTrace",
    "Goal",
    "Plan",
    "PlanStep",
    "StepResult",
    "decompose",
    "execute",
    "run",
]
