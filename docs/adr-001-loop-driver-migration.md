# ADR-001 — Migrate from hand-rolled tool-use router to a vendor agent SDK

**Status:** Proposed
**Date:** 2026-05-16
**Phase:** Phase 1 Step 9 (decision-only; migration is Phase 2 work)
**Related:** `~/Desktop/personal Projects/_portfolio-architecture/chat-tool-invocation.md`

---

## Context

DirectJob Scout currently runs a hand-rolled tool-use loop in
`company_discovery/tool_use_router.py`. The portfolio-level research
(`_portfolio-architecture/chat-tool-invocation.md` §8) was unsparing
on this point:

> Past ~20 tools, hand-rolled loop drivers become load-bearing
> technical debt. The SDK gives you the loop, sub-agents, context
> compaction, MCP, tracing — for free. Keep ownership of the *tool
> definition layer* and *response formatting layer*; cede the
> orchestration loop.

Phase 1's tool-coverage work (Step 7) is set to expand DJS's tool
count from 14 → ~40 (the 25 tool-coverage gaps from the priority
framework, plus existing tools). xboard, the sibling project in the
portfolio, already has 36 tools and a similarly hand-rolled loop.
Both projects are at or past the documented inflection point.

## What the hand-rolled router does today

`tool_use_router.run_tool_use` (DJS):
- Drives the message loop (up to 8 iterations).
- Calls Anthropic or OpenAI directly via `urllib` + JSON-RPC.
- Manages retries (single retry, fixed 500ms backoff).
- Handles process-level response caching.
- Refuses unknown tool names and pre-confirmation for destructive
  commands.

xboard's `agent-loop.ts` does the equivalent in TypeScript with
slightly more sophistication (cross-provider fallback, atomic cost
reservation, per-tenant rate-limit queues).

Neither has: native MCP support, sub-agent isolation, context
compaction, structured tracing, durable execution, or schema-strict
tool calling without manual wiring.

## Options considered

### Option A — Claude Agent SDK
- **Pros:** The agent loop extracted from Claude Code; built-in
  sub-agents, context compaction, MCP, prompt caching, defer-loading,
  Tool Search Tool, tracing primitives. Tight to Anthropic's contract
  (which is the portfolio default).
- **Cons:** Claude-only. No first-class OpenAI fallback. Switching
  the default model later means migrating off the SDK.

### Option B — Pydantic AI
- **Pros:** Model-portable by string swap (Claude → GPT-4o → Gemini).
  Type-safe agent code with Pydantic-native validation matches the
  Step 1 registry pattern exactly. Logfire integration covers Step 8
  observability for free. Smallest cognitive surface.
- **Cons:** Less mature than Anthropic Agent SDK; smaller community;
  some Anthropic-specific features (Tool Search Tool, programmatic
  tool calling) not exposed as ergonomically.

### Option C — LangGraph
- **Pros:** Heaviest, most production-proven for stateful agents.
  Checkpoints + durable execution + explicit DAG.
- **Cons:** Overkill at our tool count. Steepest learning curve.
  Adds framework lock-in beyond what the SDK options impose.

### Option D — Stay hand-rolled
- **Pros:** No migration cost. Full control.
- **Cons:** Carries the cost the research called out. Every Step 7
  tool grows the surface area. Tracing, MCP, sub-agents, context
  compaction become incremental in-house projects rather than
  framework features.

## Decision

**Migrate to Pydantic AI in Phase 2.**

Reasoning:
1. The Step 1 registry already uses Pydantic for input/output
   schemas. Pydantic AI consumes those models natively — minimal
   re-shape work.
2. Model portability is real value: per the canonical product vision
   (`memory/project_canonical_vision.md`), we manage the model
   centrally and may rotate providers (cost engineering, vendor
   redundancy, regional sovereignty). A Claude-only SDK constrains
   that.
3. Pydantic AI + Logfire delivers Step 8 (observability) as a side
   effect, not a separate workstream.
4. The Anthropic-specific features we'd lose (Tool Search Tool,
   programmatic tool calling) don't apply at our tool count yet
   (research recommends Tool Search at 150+ tools; we'll cross that
   threshold in a Phase 3 timeframe, if at all).

## Migration plan (Phase 2)

1. Add `pydantic-ai` to `requirements.txt`.
2. Define a `Agent` instance per chat session in
   `company_discovery/agent.py`. Configure with the Claude model the
   existing model-router selects.
3. Register all 40+ Tool definitions on the Agent. The existing
   Pydantic input/output models + handlers translate 1:1.
4. Replace `tool_use_router.run_tool_use` with a thin wrapper that
   calls `agent.run_stream(...)` and propagates results to the
   existing dispatch closure in `app.py`. Keep the WireToolResult
   shape so the rest of `app.py` doesn't change.
5. Move cost-cap reservation + per-call recording into Pydantic
   AI's `result_validator` hook so the existing
   `llm_cost_tracker` keeps recording.
6. Adopt Logfire as the observability backend (covers Step 8).
7. Delete `tool_use_router._call_anthropic` /
   `_call_openai` / `_call_anthropic`'s retry logic once Pydantic AI
   is proven (it handles all three).

**Estimated horizon:** 1-2 weeks at one engineer. No production
behaviour change visible to users; internal architecture only.

## Consequences

- One dependency added (`pydantic-ai`). Already required for Step 1
  Pydantic-based tool registry, so the Pydantic ecosystem is in.
- The hand-rolled `_call_anthropic` / `_call_openai` deletes ~200
  lines of code. Net loss in our maintenance burden.
- xboard, in TypeScript, can adopt the same pattern via
  `@pydantic-ai/typescript` or remain on its TypeScript SDK — to be
  decided in its own ADR when xboard's Phase 2 starts.
- We lose direct visibility into the prompt body sent to Anthropic
  (Pydantic AI abstracts it). Mitigated by Logfire's request/response
  span capture.

## Open questions

- Does Pydantic AI's tool calling support Anthropic's `cache_control`
  on the last tool, per Step 2's optimisation? **Action**: verify
  before migration kicks off.
- Does Pydantic AI's structured-output mode interact correctly with
  our Tier I → reversal-token pipeline? **Action**: prototype on
  `set_persona` as the migration sanity check.
- What's the Logfire pricing model? Whether to self-host or use
  managed depends on cost at our chat volume (~1M chats/year).
  **Action**: scope before Phase 2 kicks off.

---

**Reviewer:** (open)
**Next step:** Phase 1 Steps 7 + 8 first, then this ADR is acted on
in Phase 2.
