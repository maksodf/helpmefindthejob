<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Agent architecture

**Audience**: maintainer planning the post-v0.80.0 multi-agent refactor; integrators understanding the boundary between in-process subsystems vs. external MCP-composable civic agents.

**Status**: design doc — describes the present (chat-router monolith) AND the Phase-2 target (specialist agents behind a planner). The multi-agent refactor is Phase-2 work; no new product features ship during the NLnet window, so the diagram below is the design contract, not yet the implementation.

---

## 1. Present state (v0.80.0) — chat-router monolith

Every AI-touching capability lives behind `company_discovery/chat_router.py` (the slash-command + intent-classifier surface) which dispatches to a small set of helpers in `company_discovery/analysis.py` (fit-scoring, cover-letter, CV-tailor, brief, query-expansion) plus `company_discovery/journey.py` (12-phase journey state machine) plus `company_discovery/cv_builder.py` (sectional CV interview).

```text
┌─────────────────────────────────────────────────────────────────┐
│                    USER (chat composer surface)                  │
└──────────────────────────────────┬──────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│             chat_router.py — intent + slash dispatch             │
│                                                                  │
│  • build_ai_router_prompt — natural-language intent classifier   │
│  • parse_ai_router_response — pin to REGISTRY command id         │
│  • REGISTRY — closed catalogue of supported chat commands        │
└────────┬────────────┬──────────────┬───────────────┬────────────┘
         │            │              │               │
         ▼            ▼              ▼               ▼
┌───────────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────┐
│ journey.py    │ │analysis  │ │cv_builder  │ │aggregators   │
│ 12-phase      │ │.py       │ │.py         │ │_providers.py │
│ state machine │ │          │ │            │ │              │
│               │ │ fit-score│ │ sectional  │ │ Adzuna /     │
│ discover →    │ │ cover-   │ │ interview  │ │ Indeed /     │
│ cv_check →    │ │ letter   │ │ +          │ │ LinkedIn /   │
│ search →      │ │ cv-tailor│ │ AEAD       │ │ EURES        │
│ analyze →     │ │ brief    │ │ encrypted  │ │ fan-out      │
│ letter →      │ │ query-   │ │ at rest    │ │              │
│ apply →       │ │ expansion│ │            │ │              │
│ track → done  │ │          │ │            │ │              │
└───────────────┘ └──────────┘ └────────────┘ └──────────────┘
                       │
                       ▼
            ┌────────────────────────┐
            │ ai_providers.py        │
            │ BYO-AI dispatcher      │
            │ (OpenAI / Anthropic /  │
            │  Gemini / DeepSeek /   │
            │  OpenRouter / Ollama / │
            │  Codex CLI / Claude    │
            │  Code / manual)        │
            └────────────────────────┘
```

The monolith is justified at v0.80.0 because the chat-router's REGISTRY layer already enforces the contract every command must satisfy (input shape, output shape, audit-log entry, cost-cap context). The "everything in chat_router" framing overstates the coupling — capability is already split across the modules above, with chat_router as the dispatcher front-end. What HASN'T happened yet is the explicit **agent boundary**: each helper module today is a function-call away from chat_router, not a process-isolated or stable-interface-isolated agent.

---

## 2. Phase-2 target — specialist agents behind a planner

The multi-agent refactor introduces a **planner agent** that decomposes user goals into sub-goals and routes each to a **specialist agent** with a typed contract.

> **Implemented on the `claude/ceiling-sprint` branch (2026-05).** The planner and the six typed contracts below now ship in the `civic_agents/` package (`civic_agents/contracts.py`, `civic_agents/planner.py`): deterministic rule-based routing (the no-AI fallback), JSON-Schema-validated handoffs, and a trust receipt emitted into the Article-12 audit chain per step. `tests/test_civic_agents.py` carries the golden-trace replay that verifies the receipts land in the HMAC chain and are externally anchorable. The §2 design below is the specification it implements; §2.3 (“Why this isn’t shipped at v0.80.0”) is retained as the historical rationale for why it post-dates that release.

```text
┌─────────────────────────────────────────────────────────────────┐
│                    USER (chat composer surface)                  │
└──────────────────────────────────┬──────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PLANNER AGENT (new, planned)                    │
│                                                                  │
│  Receives high-level goal: "help me get a healthcare job in     │
│  Berlin with my Tunisian credentials"                            │
│  Decomposes to sub-goals; routes each to specialist agents      │
│  Tracks state across the multi-step plan; surfaces progress     │
│  narration to the user                                          │
└──┬──────┬──────┬──────┬──────┬──────┬───────────────────────────┘
   │      │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼      ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐┌────────────┐
│cv_agent││search_ ││anerken-││letter_ ││housing_││compliance_ │
│        ││agent   ││nung_   ││agent   ││agent   ││agent       │
│        ││        ││agent   ││        ││        ││            │
│sectional││job     ││§16d    ││DACH-   ││handoff ││Article 22  │
│CV build││match + ││track + ││norm    ││to      ││surface +   │
│+ photo ││fit-    ││docs    ││Anschr- ││partner ││audit-log   │
│consent ││score   ││check + ││eiben   ││(real   ││emitter +   │
│        ││        ││deadline││draft + ││per     ││consent     │
│        ││        ││countdwn││edit    ││Decision││enforcement │
│        ││        ││        ││        ││20)     ││            │
└───┬────┘└───┬────┘└───┬────┘└───┬────┘└───┬────┘└─────┬──────┘
    │        │         │         │         │            │
    └────────┴─────────┴─────────┴─────────┴────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │ cost_cap_context │
                  │ — single         │
                  │ chokepoint every │
                  │ agent passes     │
                  │ through; per-    │
                  │ agent budget     │
                  │ allocation       │
                  └──────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │ audit_log.py     │
                  │ Article 12       │
                  │ HMAC-chain;      │
                  │ every agent      │
                  │ handoff logged   │
                  └──────────────────┘
```

### Specialist-agent contracts (typed inputs → outputs)

| Agent | Owns | Input contract | Output contract |
|---|---|---|---|
| `cv_agent` | Sectional CV interview, photo consent, encrypted-at-rest persistence | `{persona_slug, target_lang, prior_cv_text?}` | `{cv_text, cv_sections, cv_export_paths, consent_log}` |
| `search_agent` | Aggregator fan-out, dedup, persona-aware ranking | `{role, location, persona, friction_class}` | `{discovered_jobs: DiscoveredJob[], dedup_groups, source_attribution}` |
| `anerkennung_agent` | §16d/§18/§4/Blue-Card status, recognition-decision tracking, document checklist, Senatsverwaltung URL routing | `{persona_slug, current_status, target_profession}` | `{recognition_steps, missing_documents, target_deadline, senatsverwaltung_url}` |
| `letter_agent` | DACH-norm Anschreiben drafting; friction-context proactive framing | `{job, profile, friction_context}` | `{letter_text, paragraph_edits, regenerate_handles}` |
| `housing_agent` | Handoff to partner housing-search civic agent (Option B) | `{user_consent_scope, target_city, employment_status}` | `{referral_payload, partner_agent_uri}` |
| `compliance_agent` | Article 22 right-to-human-review surface, audit-log emission, consent enforcement | `{event_class, user_opaque_id, AI_output_ref}` | `{audit_log_entry_id, escalation_path, retention_clock}` |

Each contract is JSON-Schema validated. A specialist agent is a function (today; Phase 2 may upgrade to subprocess or HTTP for process-isolation, but the contract stays the same).

### Why the boundary matters

**Today** (v0.80.0 monolith):
- Tests for cv_builder logic share fixtures with chat_router intent classification — refactoring one risks breaking the other.
- A future contributor adding a new capability (e.g., "language-course pairing") would extend `analysis.py` or `chat_router.py` and inherit all the surrounding context.
- The MCP server (`mcp_server.py`) wraps the SAME helpers as the chat-router does — but with a different glue layer + a different intent surface.

**Phase 2** (specialist agents):
- Each agent has its own test fixture set + its own JSON-Schema contract + its own deprecation cycle.
- A new capability lands as a new agent OR as an extension of an existing agent's contract (versioned per the per-tool schema-versioning rules).
- The MCP server becomes the SAME planner-agent surface — internal callers get the agent via function-call; external MCP clients get the agent via `tools/list` + `tools/call`. One interface, two transports.

### Why this isn't shipped at v0.80.0

The NLnet window's hard rule says "no new product features." A multi-agent refactor IS a substantial new product surface even though the user-visible behavior would be near-identical. The refactor is scoped for the 2026-Q4 post-grant work alongside the framework-extraction theme (per `docs/grant/03-post-grant.md`).

What IS shipped at v0.80.0:
- The monolith IS internally organised so the refactor is mechanical, not a redesign — chat_router calls into purpose-built helpers; each helper already has a documented input/output shape.
- The contract for each Phase-2 agent is documented above so a future contributor (or future-me) can land the refactor without re-deriving design choices.
- The MCP tool catalogue at `company_discovery/mcp_tools.py` already exposes the agent-shaped surfaces (suggest_relevant_companies, score_fit, draft_letter, propose_referral, record_user_outcome, get_user_profile_for_consent, etc.) so an external integrator can ALREADY compose the project at the agent boundary — they just don't yet see the planner-agent wrapper.

## 3. Cross-references

- Chat-router source: [`company_discovery/chat_router.py`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/chat_router.py)
- Analysis helpers: [`company_discovery/analysis.py`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/analysis.py)
- CV builder: [`company_discovery/cv_builder.py`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/cv_builder.py)
- Journey state machine: [`company_discovery/journey.py`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/journey.py)
- MCP composition spec: [`grant/09-mcp-composition.md`](grant/09-mcp-composition.md) + v2 section with real worked examples
- Post-grant Phase 2 roadmap: [`grant/03-post-grant.md`](grant/03-post-grant.md)
