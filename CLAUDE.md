# CLAUDE.md — Agent Onboarding

Any Claude session (or other coding agent) working on this repository should read this file first, then **read the grant workspace at `docs/grant/`** before touching anything.

---

## What this project is

**DirectJob Scout** is being repositioned as an **open-source, multilingual, privacy-preserving civic employment agent** for the German labor-shortage gap. It is MCP-exposed (Model Context Protocol) so other open civic agents can compose with it. The MCP server is the commons interface. German-first, EU-exportable.

This is *not* a commercial SaaS, even though earlier iterations of the codebase contain commercial-product residue (Pro/Free tier, "sellable-readiness" docs, `khalo.org` hardcoded). The active project direction is the civic-commons framing.

---

## What we are currently doing

Preparing the project for an **NLnet NGI Zero Commons Fund** grant application. Target submission window: ~4 weeks from 2026-05-17.

The work has three layers running in parallel:
1. **Strategic/documentation** — captured in `docs/grant/`
2. **Repository hardening** — LICENSE, governance files, README, sanitization, CI
3. **MCP composition proof** — docs + reference integration + integration test

---

## Where to find context (read in this order)

1. **`docs/grant/00-START-HERE.md`** — orientation
2. **`docs/grant/01-project-brief.md`** — strategic context, audit findings, decisions
3. **`docs/grant/02-execution-plan.md`** — the 4-week task list, tick boxes as you progress
4. **`docs/grant/03-post-grant.md`** — what happens after week 4

If you change strategic direction, update `01-project-brief.md`. If you complete a task, update `02-execution-plan.md`.

---

## Hard rules for this 4-week window

1. **No new product features.** Every hour on features is an hour not on the application.
2. **No framework extraction.** Deferred to Phase 2 (see `03-post-grant.md`).
3. **License everything you write under AGPL-3.0.** Add SPDX headers in new source files.
4. **Never commit secrets, real keys, or PII.** Sanitize before pushing.
5. **Mobile-friendly assumption**: maintainer reviews on a phone. Small diffs, clear commit messages.
6. **Honest about instability**: do not over-polish to look finished. NGI0 winners are honest about alpha state.
7. **Anchor user persona**: every public-facing example, screenshot, narrative uses the named persona Aïcha (Tunisian-trained nurse navigating German Anerkennung). See `01-project-brief.md` §7.

---

## What's in the repository

| Path | Role |
|---|---|
| `app.py` (~7.3k lines) | HTTP handler, session, chat/journey dispatch |
| `mcp_server.py` | MCP server skeleton — needs hardening (Week 2) |
| `company_discovery/chat_router.py` | Slash commands, intent routing, multi-turn state machine |
| `company_discovery/journey.py` | 12-phase job-search wizard |
| `company_discovery/aggregators.py` + `aggregator_providers.py` | Job-board fan-out, dedup |
| `company_discovery/ai_providers.py` | BYO-AI abstraction (OpenAI/Gemini/DeepSeek/OpenRouter/Ollama/manual/Claude Code) |
| `company_discovery/personas.py` | 5 personas + ranking |
| `company_discovery/cv_builder.py` | Sectional CV interview, encrypted at rest |
| `company_discovery/analysis.py` | AI calls: fit score, cover letter, tailor, brief |
| `company_discovery/billing.py` | Stripe — **moved out of public messaging during grant work** |
| `static/i18n/{en,de}.json` | Translation bundles |
| `docs/grant/` | **Read these files first.** |
| `docs/` (other files) | Mostly internal commercial docs — scheduled for relocation in Week 1 |

---

## Branch convention

Active branch: `claude/project-analysis-bpHCo` (or a derivative branch).

Create week-specific branches off this for execution: `claude/week-1-foundations`, `claude/week-2-mcp-proof`, etc.

---

## How to update this CLAUDE.md

This file should stay short and orient agents to the workspace. If the orientation summary above stops being accurate, edit this file. For substantive context, edit `docs/grant/` instead.

---

## If something seems off

- The repository has known narrative residue (commercial framing, `khalo.org`, tester names) that will be cleaned up in Week 1 per `02-execution-plan.md`. Don't be surprised by it; don't add to it.
- Tests fail locally due to a `cryptography` / `cffi` build issue — scheduled for fix in Week 3.
- If you find a strategic ambiguity not covered in `docs/grant/`, ask the maintainer rather than guessing.
