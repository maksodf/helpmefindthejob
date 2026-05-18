# Grant Application Workspace — Start Here

**Purpose**: track everything related to the NLnet NGI Zero Commons Fund application for DirectJob Scout. This folder is the single source of truth for the strategic vision, research findings, decisions, and execution plan. If you (human or agent) are picking up this work mid-flight, read the files in this folder in the order below before touching anything.

---

## What's in this folder

| File | Purpose |
|---|---|
| `00-START-HERE.md` | This file. Orientation. |
| `01-project-brief.md` | The strategic source of truth: mission, positioning, decisions, eight strategic choices, full audit. **Read first.** |
| `02-execution-plan.md` | 4-week task list with checkboxes. Tick boxes as work is completed. |
| `03-post-grant.md` | What happens after the 4 weeks: win, lose, Phases 2/3/4. |
| `04-research-and-decisions.md` | Verified facts (sourced), decisions log (dated), open research questions. |
| `05-risks-and-stakeholders.md` | Risk register + stakeholder map. Reviewed weekly during execution. |
| `06-glossary.md` | Quick reference for German bureaucratic, EU policy, and project-specific terms. |
| `07-personas.md` | The five-persona panel (Aïcha, Yusuf, Olga, Mahmoud, Maria) used in proposal narrative, demos, public artifacts. |
| `08-cost-saving-doctrine.md` | The project-level design principle: every feature reduces institutional cost while improving outcomes. |
| `09-mcp-composition.md` | Technical spine: how the MCP server exposes the project as composable civic infrastructure. |
| `10-ai-act-compliance.md` | Compliance pack for EU AI Act high-risk-AI obligations, applicable 2 August 2026. The institutional moat. |
| `11-institutional-outreach.md` | Outreach tracker, partner-targeting strategy, cold-contact templates, letter-of-support template. |
| `12-application-package.md` | The actual application draft, milestone budget breakdown, submission checklist. |

---

## TL;DR for fast onboarding

**The goal**: win a Phase 1 NLnet NGI Zero Commons Fund grant of ~€37,000 (within the €50k first-round cap) to harden DirectJob Scout into a credible open-source civic-employment commons. Multi-grant arc planned beyond Phase 1.

**The deadline**: ~4 weeks from 2026-05-17 — verify the exact NLnet call deadline in `04-research-and-decisions.md` Open Question R1 before committing to a date.

**The product positioning**: not "an open-source job app." It is **an open-source EU-wide civic employment commons that captures specialist HR and bureaucratic-navigation knowledge into modular, MCP-composable tools** — the Redwax pattern applied to civic life. **Friction-driven, not demographic-driven**: serves anyone facing structural friction in the European labor market. Migrants and EU-mobile workers are the most acute use case and primary narrative anchor; the same architecture serves career changers, returning workers, the long-term unemployed, and others (Decision 21). Germany is the first reference deployment because that is where the maintainer is.

**The institutional home**: Programme of **The Commons Conservancy** (NLnet-co-founded Dutch stichting; application target Week 2).

**The license**: Apache 2.0 + Contributor License Agreement. (Not AGPL — this was a deliberate revision after Redwax research; reasoning in `04-research-and-decisions.md` Decision 1.)

**The moat**: EU AI Act compliance built in for the 2 August 2026 enforcement deadline. Every institution deploying our agent inherits a compliant configuration, avoiding €30–€200k of consulting otherwise required.

**The strategic doctrine**: every feature evaluated against "does it reduce institutional operational cost while improving end-user outcomes?" — see `08-cost-saving-doctrine.md`.

**The current honest state**: feature-rich working MVP with strong privacy/encryption/i18n/Docker stories. Missing: LICENSE file, governance scaffolding, MCP composition proof, sanitised commercial residue, public demo, AI Act compliance pack. All addressed across Weeks 1–4 of `02-execution-plan.md`.

---

## Rules for any agent (or contributor) working on this

1. **No new product features during these 4 weeks.** Every hour on features is an hour not on the application.
2. **No framework extraction.** Deferred to Phase 2; see `03-post-grant.md`.
3. **License everything you write under Apache 2.0.** Add SPDX-License-Identifier headers in new source files.
4. **Never commit secrets, real keys, or PII.** Sanitise any `khalo.org`, real tester names, or production URLs before pushing.
5. **Mobile-friendly assumption**: the maintainer reviews on a phone for planning; for execution, computer is recommended. Small diffs, clear commit messages.
6. **Honest about instability**: do not over-polish to look finished. NGI0 winners are honest about alpha state.
7. **Anchor persona panel**: every public-facing example, screenshot, narrative uses one of the seven personas (five most-acute migrants + two wider friction-class). Primary narrative weight stays with the migrant five; the wider two demonstrate the friction-class claim architecturally. See `07-personas.md`.
8. **Cost-saving doctrine applies to every feature decision.** When in doubt, re-read `08-cost-saving-doctrine.md`.
9. **AI Act compliance is non-negotiable scope.** Cannot be cut for time. See `10-ai-act-compliance.md`.
10. **One credible letter of support is enough.** Don't pad outreach. See `11-institutional-outreach.md`.

---

## How to update this folder

- **Strategic changes** (positioning, scope, target funder): update `01-project-brief.md` and add a dated entry to `04-research-and-decisions.md`.
- **Execution progress** (tasks done, blockers found): update `02-execution-plan.md` checkboxes and note in the tracking notes section.
- **New verified fact**: add to `04-research-and-decisions.md` Part A with source.
- **New risk or stakeholder**: add to `05-risks-and-stakeholders.md`.
- **Long-term vision changes**: update `03-post-grant.md`.

**Strategic changes go in separate commits from code changes** so decision history is visible in git log.

---

## Source-of-truth precedence

If documents disagree:

1. `01-project-brief.md` — strategic context wins
2. `04-research-and-decisions.md` — specific decisions and facts win
3. `02-execution-plan.md` — current task list wins
4. The README and CLAUDE.md at repo root — pointers only, never source of truth
5. Internal commercial docs (operator-runbook, marketing-copy, sellable-readiness-*) — **scheduled for relocation in Week 1**. Do not treat as guidance for grant work.

---

## What's been done as of 2026-05-17

The planning phase is complete. The workspace now contains:

- A clear strategic vision with eight binding decisions documented
- A 4-week execution plan calibrated to ~140–180 hours of available work
- Full reverse-engineering of six NGI0 reference winners
- Full Redwax research, leading to the Apache 2.0 + Commons Conservancy decisions
- The cost-saving doctrine adopted as a project-level design principle
- The multi-persona panel defined for proposal and design use
- The complete EU AI Act compliance plan, calibrated to the 2 August 2026 enforcement date
- The institutional-outreach strategy with templates and target lists
- A risk register and stakeholder map for ongoing review
- A draft application package ready to be adapted to NLnet's form
- All sources cited, no claims unverified

The next step is **execution**, starting with Week 1 of `02-execution-plan.md`.
