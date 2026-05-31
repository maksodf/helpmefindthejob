# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic multi-agent planner (docs/agent-architecture.md §2).

The planner turns a high-level user goal into an ordered plan of specialist
steps, runs each step through its typed contract, and emits a **trust receipt**
into the Article-12 audit chain at every handoff. It is fully deterministic and
needs no AI provider: routing is rule-based (a goal's declared ``needs`` map to
specialists in a fixed canonical order), so the same goal always yields the same
plan — the no-AI fallback the architecture requires. An AI layer may later
propose richer decompositions, but this rule-based planner is always the floor.

Specialists are injected as plain callables (``handlers``), so the planner is
transport-agnostic: an in-process ``company_discovery`` helper and a
``mesh/`` HTTP agent look identical to it. Every step validates the specialist's
input AND output against ``civic_agents.contracts``; a violation is recorded + receipted
as a failed step rather than allowed to corrupt downstream state.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from civic_agents.contracts import ContractViolation, get_contract

#: Fixed dependency order — a CV exists before a letter cites it, recognition is
#: scoped before housing handoff, compliance closes the trace. Routing is keyed
#: off this so plan order is deterministic regardless of ``needs`` ordering.
CANONICAL_ORDER: tuple[str, ...] = (
    "cv_agent",
    "search_agent",
    "anerkennung_agent",
    "letter_agent",
    "housing_agent",
    "compliance_agent",
)

#: User-facing capability name → specialist agent.
NEED_TO_SPECIALIST: dict[str, str] = {
    "cv": "cv_agent",
    "search": "search_agent",
    "anerkennung": "anerkennung_agent",
    "letter": "letter_agent",
    "housing": "housing_agent",
    "compliance": "compliance_agent",
}


class ReceiptSink(Protocol):
    """Anything that can record a trust receipt — satisfied by
    ``company_discovery.audit_log.AuditLogEmitter``."""

    def emit(
        self,
        event_type: str,
        *,
        outcome: str = ...,
        event_payload: dict[str, Any] | None = ...,
    ) -> Any: ...


Handler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class Goal:
    """A structured user goal. ``context`` carries the specialist input fields
    (role, location, target_lang, …); the planner reads it deterministically."""

    goal_id: str
    persona_slug: str
    needs: tuple[str, ...]
    context: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanStep:
    specialist: str
    input_payload: dict[str, Any]


@dataclass(frozen=True)
class Plan:
    goal_id: str
    steps: tuple[PlanStep, ...]


@dataclass(frozen=True)
class StepResult:
    specialist: str
    status: str  # "ok" | "input_violation" | "handler_error" | "output_violation"
    output: dict[str, Any] | None
    receipt_emitted: bool
    error: str | None = None


@dataclass(frozen=True)
class ExecutionTrace:
    goal_id: str
    results: tuple[StepResult, ...]

    @property
    def ok(self) -> bool:
        return all(r.status == "ok" for r in self.results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goalId": self.goal_id,
            "ok": self.ok,
            "steps": [
                {
                    "specialist": r.specialist,
                    "status": r.status,
                    "receiptEmitted": r.receipt_emitted,
                    "error": r.error,
                }
                for r in self.results
            ],
        }


def _digest(payload: dict[str, Any] | None) -> str:
    """Stable content fingerprint of a payload (for the receipt; never the raw
    payload, which may carry PII)."""
    canonical = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _build_input(specialist: str, goal: Goal) -> dict[str, Any]:
    """Deterministically construct a specialist's input from the goal. Always
    supplies the contract's required keys; optional context fields pass through."""
    ctx = goal.context
    if specialist == "cv_agent":
        return {"persona_slug": goal.persona_slug, "target_lang": str(ctx.get("target_lang", "de"))}
    if specialist == "search_agent":
        return {
            "role": str(ctx.get("role", "")),
            "location": str(ctx.get("location", "")),
            "persona": goal.persona_slug,
            "friction_class": str(ctx.get("friction_class", "")),
        }
    if specialist == "anerkennung_agent":
        return {
            "persona_slug": goal.persona_slug,
            "current_status": str(ctx.get("current_status", "")),
            "target_profession": str(ctx.get("target_profession", "")),
        }
    if specialist == "letter_agent":
        return {
            "job": dict(ctx.get("job", {})),
            "profile": dict(ctx.get("profile", {"persona_slug": goal.persona_slug})),
            "friction_context": str(ctx.get("friction_context", "")),
        }
    if specialist == "housing_agent":
        return {
            "user_consent_scope": list(ctx.get("user_consent_scope", [])),
            "target_city": str(ctx.get("target_city", "")),
            "employment_status": str(ctx.get("employment_status", "")),
        }
    if specialist == "compliance_agent":
        return {
            "event_class": str(ctx.get("event_class", "plan_closeout")),
            "user_opaque_id": str(ctx.get("user_opaque_id", "")),
            "ai_output_ref": str(ctx.get("ai_output_ref", goal.goal_id)),
        }
    raise KeyError(f"no input builder for specialist {specialist!r}")


def decompose(goal: Goal) -> Plan:
    """Rule-based goal → ordered plan. Deterministic: unknown needs are dropped,
    known needs are routed + sorted into CANONICAL_ORDER, duplicates collapsed."""
    wanted = {NEED_TO_SPECIALIST[n] for n in goal.needs if n in NEED_TO_SPECIALIST}
    steps = tuple(
        PlanStep(specialist=s, input_payload=_build_input(s, goal))
        for s in CANONICAL_ORDER
        if s in wanted
    )
    return Plan(goal_id=goal.goal_id, steps=steps)


def execute(
    plan: Plan,
    handlers: Mapping[str, Handler],
    audit: ReceiptSink,
    *,
    stop_on_failure: bool = False,
) -> ExecutionTrace:
    """Run each step: validate input → call handler → validate output → emit a
    trust receipt. A contract violation or handler error becomes a failed (but
    receipted) step. By default the plan continues so the trace is complete;
    pass ``stop_on_failure=True`` to halt at the first bad step."""
    results: list[StepResult] = []
    for index, step in enumerate(plan.steps):
        contract = get_contract(step.specialist)
        status = "ok"
        output: dict[str, Any] | None = None
        error: str | None = None

        try:
            contract.validate_input(step.input_payload)
            handler = handlers.get(step.specialist)
            if handler is None:
                raise KeyError(f"no handler registered for {step.specialist!r}")
            output = handler(step.input_payload)
            contract.validate_output(output)
        except ContractViolation as exc:
            status = "input_violation" if exc.direction == "input" else "output_violation"
            error = exc.detail
            output = None
        except Exception as exc:  # handler raised / no handler
            status = "handler_error"
            error = f"{type(exc).__name__}: {exc}"
            output = None

        # The trust receipt: a tamper-evident audit record per handoff. It carries
        # digests (not raw payloads) so the chain never leaks PII; it is HMAC-
        # chained + anchorable like every other Article-12 record.
        audit.emit(
            "planner_step",
            outcome="ok" if status == "ok" else "error",
            event_payload={
                "goalId": plan.goal_id,
                "stepIndex": index,
                "specialist": step.specialist,
                "status": status,
                "inputDigest": _digest(step.input_payload),
                "outputDigest": _digest(output),
            },
        )
        results.append(
            StepResult(
                specialist=step.specialist,
                status=status,
                output=output,
                receipt_emitted=True,
                error=error,
            )
        )
        if status != "ok" and stop_on_failure:
            break

    return ExecutionTrace(goal_id=plan.goal_id, results=tuple(results))


def run(
    goal: Goal,
    handlers: Mapping[str, Handler],
    audit: ReceiptSink,
    *,
    stop_on_failure: bool = False,
) -> ExecutionTrace:
    """Decompose ``goal`` and execute the plan — the planner's top-level entry."""
    return execute(decompose(goal), handlers, audit, stop_on_failure=stop_on_failure)
