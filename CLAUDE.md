# CLAUDE.md — Agent Onboarding

Any Claude session (or other coding agent) working on this repository should read this file first, then **read the grant workspace at `docs/grant/`** before touching anything.

---

## What this project is

**DirectJob Scout** is an **open-source EU-wide civic employment commons** — an MCP-composable tool that captures specialist HR and bureaucratic-navigation knowledge into modular, standards-anchored modules and puts that knowledge directly into the hands of anyone facing structural friction in the European labor market. Migrants and EU-mobile workers are the most acute use case and the primary narrative anchor in proposal and demo material, but the architecture is friction-driven rather than demographic-driven and the same friction affects career changers, returning workers, the long-term unemployed, returning expats, and others (see Decision 21 in `docs/grant/04-research-and-decisions.md`). Germany is the first reference deployment; the architecture is EU-wide.

The project is being prepared as a Programme of **The Commons Conservancy** (Dutch stichting co-founded by NLnet). License is **Apache 2.0 with Contributor License Agreement**.

This is *not* a commercial SaaS, even though earlier iterations of the codebase carried commercial-product framing. The Week 1 sanitisation pass (see `docs/grant/02-execution-plan.md` task 1.4) replaced the public-facing residue with `directjob-scout.example` placeholders and relocated the commercial-vision docs to `private/`. The active project direction is civic-commons. Early git commits may still reference legacy strings; see `CONTRIBUTORS-NOTE.md` for the history-preservation rationale.

---

## What we are currently doing

Preparing the project for the **NLnet NGI Zero Commons Fund** application. Target submission window: ~4 weeks from 2026-05-17 — exact NLnet call deadline verified at start of execution.

Three workstreams run in parallel:
1. **Strategic/documentation** — captured in `docs/grant/` (planning phase complete as of 2026-05-17)
2. **Repository hardening** — LICENSE, governance files, README, sanitisation, CI, MCP composition proof
3. **EU AI Act compliance pack** — required by 2 August 2026 enforcement date; built in as project-level deliverable

---

## Where to find context (read in this order)

1. **`docs/grant/00-START-HERE.md`** — orientation and table of contents
2. **`docs/grant/01-project-brief.md`** — the strategic source of truth
3. **`docs/grant/13-lessons-learned.md`** — behavioural rules from prior sessions. Read this before generating any prompt for the coding agent, recommending a scope change, or editing planning docs.
4. **`docs/grant/04-research-and-decisions.md`** — verified facts, decisions log, open questions
5. **`docs/grant/02-execution-plan.md`** — week-by-week task list with checkboxes
6. Everything else in `docs/grant/` as relevant

If you change strategic direction, update `01-project-brief.md` AND log the decision in `04-research-and-decisions.md`. If you complete a task, tick the box in `02-execution-plan.md` and add a note if scope changed.

---

## Hard rules for this 4-week window

1. **No new product features.** Every hour on features is an hour not on the application.
2. **No framework extraction.** Deferred to Phase 2 (see `docs/grant/03-post-grant.md`).
3. **License everything you write under Apache 2.0.** Add SPDX-License-Identifier headers in new source files.
4. **Never commit secrets, real keys, or PII.** Sanitise before pushing. The Week 1 task 1.4 sanitisation pass cleared the `khalo.org` and tester-name residue from the current working tree; do not reintroduce it. Git history is preserved per Decision 12.
5. **Mobile-friendly assumption**: maintainer reviews on a phone for planning, computer for execution. Small diffs, clear commit messages.
6. **Honest about instability**: do not over-polish. NGI0 winners are honest about alpha state. Tenzu literally says "main branch may be unstable."
7. **Anchor persona panel**: every public-facing example, screenshot, narrative uses one of the seven personas — five most-acute migrant (Aïcha, Yusuf, Olga, Mahmoud, Maria) plus two wider friction-class (Käthe, Tobias) per Decision 21. Primary narrative weight stays with the migrant five — the wider two demonstrate the friction-class claim architecturally. See `docs/grant/07-personas.md`.
8. **Cost-saving doctrine**: every feature decision is evaluated against "does it reduce institutional cost while improving outcomes?" See `docs/grant/08-cost-saving-doctrine.md`.
9. **EU AI Act compliance is in scope and non-negotiable.** See `docs/grant/10-ai-act-compliance.md`.

---

## Key strategic decisions (binding unless explicitly reopened)

| Decision | Choice |
|---|---|
| License | Apache 2.0 + CLA |
| Institutional wrapper | The Commons Conservancy (application target: Week 2) |
| Positioning | EU-wide civic employment commons; Germany first reference deployment |
| TU Berlin affiliation | Optional 1-hour email only; deferred as dependency |
| Personas | Panel of seven (five most-acute migrant + two wider friction-class) per Decisions 5 and 21 |
| Languages | EN + DE shipped; Arabic, Ukrainian, Turkish, Romanian on post-grant roadmap |
| Cost-saving doctrine | Project-level design principle |
| AI Act compliance | Build in as deliverable for 2 August 2026 enforcement |
| Housing-agent integration | Option A (mock stub) default; Option B (real, via friend) only if collaborator confirms; self-built (C/D) deferred to Phase 2 per Decision 20 |
| Grant ask | €37,000 across 6 milestones, frugal-by-default |
| Repository sanitisation | Do not rewrite history; sanitise current state, document residue honestly |
| `keepbuildingtill100%tracker.MD` | Delete in Week 1 |

Full reasoning for every decision in `docs/grant/04-research-and-decisions.md` Part B.

---

## What's in the repository

| Path | Role |
|---|---|
| `app.py` | HTTP handler, session, chat/journey dispatch |
| `mcp_server.py` | MCP server skeleton — hardened in Week 2 |
| `company_discovery/chat_router.py` | Slash commands, intent routing, multi-turn state machine |
| `company_discovery/journey.py` | 12-phase job-search journey state machine |
| `company_discovery/aggregators.py` + `aggregator_providers.py` | Job-board fan-out, dedup |
| `company_discovery/ai_providers.py` | BYO-AI abstraction (OpenAI/Gemini/DeepSeek/OpenRouter/Ollama/manual/Claude Code) |
| `company_discovery/personas.py` | Persona system + ranking |
| `company_discovery/cv_builder.py` | Sectional CV interview, encrypted at rest |
| `company_discovery/analysis.py` | AI calls: fit score, cover letter, tailor, brief |
| `company_discovery/billing.py` | Stripe — billing moved out of public messaging during grant work |
| `static/i18n/{en,de}.json` | Translation bundles |
| `docs/grant/` | **Planning workspace. Read first.** |
| `docs/mcp-server.md` | Public MCP server documentation (Week 2 task 2.2 output) |
| `docs/esco-integration.md` | ESCO + EURES integration reference (Week 2 task 2.4 output) |
| `private/` (gitignored) | Internal commercial-vision docs relocated from `docs/` during Week 1 sanitisation. Not for public reference. |

---

## Branch convention

Active working branch: `claude/project-analysis-bpHCo`.

Create week-specific branches off the working branch for execution: `claude/week-1-foundations`, `claude/week-2-mcp-and-compliance`, etc.

---

## How to update this CLAUDE.md

Keep this file short and oriented toward agents. If the orientation summary above stops being accurate, edit this file. For substantive context, edit `docs/grant/` instead.

---

## If something seems off

- The Week 1 task 1.4 sanitisation pass replaced `khalo.org` references with `directjob-scout.example` placeholders, neutralised tester-name leakage in code and test comments, and relocated commercial-vision docs (sellable-readiness, operator-launch, marketing-copy, press-kit, launch-day-content, operator-package, operator-starters, operator-final-punchlist, legal-review-brief, deployment-handoff) to `private/` (gitignored). Do not reintroduce. The Pro/Free framing in the README is removed by Week 1 task 1.3 (README rewrite).
- The historical `cryptography` / `cffi` build issue (Linux without pre-built wheels + no rust + build-essential) is closed as of Week 3 task 3.1. `cryptography` is now explicitly pinned in `requirements.txt` to a range with broad wheel coverage (`>=42.0.0,<50.0.0`), and the `fresh-clone-install` CI workflow at `.github/workflows/fresh-clone-install.yml` verifies on every push that `pip install -r requirements.txt` succeeds on `python:3.11-slim` and `python:3.12-slim` followed by a representative smoke-test slice (encryption-at-rest + AEAD fuzzing + audit log + MCP integration). If you still hit a build failure, your environment is missing pre-built wheel support for cryptography on your specific platform; running inside Docker (`docker compose exec directjob-scout python3 -m unittest discover -s tests -v`) is a known-good fallback.
- If you find a strategic ambiguity not covered in `docs/grant/`, ask the maintainer rather than guessing.
- If you must make a decision without the maintainer present, document it in `docs/grant/04-research-and-decisions.md` and surface it for confirmation at the next interaction.
