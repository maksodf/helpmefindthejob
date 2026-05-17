# Grant Application Workspace — Start Here

**Purpose of this folder**: track everything related to the NLnet NGI Zero Commons Fund application for DirectJob Scout. This is the single source of truth for the strategic vision, research findings, and execution plan. If you (human or agent) are picking up this work mid-flight, read the four files in this folder in order.

---

## What's in this folder

| File | Purpose |
|---|---|
| `00-START-HERE.md` | This file. Orientation. |
| `01-project-brief.md` | The full strategic context: vision, NGI0 research findings, gap analysis, positioning decisions. Read this first if you're new. |
| `02-execution-plan.md` | The 4-week plan to make the project grant-competitive. Check progress here. |
| `03-post-grant.md` | What happens after the 4 weeks — both success and failure paths. |

---

## TL;DR for a fast onboarding

**The goal**: win a €5k–€50k grant from NLnet NGI Zero Commons Fund (or scale up to €500k across multi-round arc) to harden DirectJob Scout into a credible open-source civic-employment commons.

**The deadline**: ~4 weeks from 2026-05-17. (Verify the exact NGI0 call deadline before submitting — the calendar shows recurring calls; aim for the next open window.)

**The product positioning**: not "an open-source job app" — it is **an open, multilingual, privacy-preserving civic-employment agent, MCP-exposed so other open civic agents can compose with it**. The MCP server is the commons interface. Germany-first, EU-exportable.

**The strategic risk**: the codebase today reads as a commercial SaaS that happens to be open-source, not as a commons. Without 60–80 hours of disciplined non-feature work on legal/governance/narrative/CI/MCP-proof, NLnet reviewers will reject it.

**The honest current state**: feature-rich working MVP with strong privacy/encryption/i18n/Docker stories, but no LICENSE file, no governance scaffolding, no proof of the MCP-composition claim, single-author, hardcoded internal references, and a "sellable-readiness" narrative throughout. See `01-project-brief.md` for the full audit.

---

## Rules for any agent (or contributor) working on this

1. **Do not add product features during these 4 weeks.** Every hour on features is an hour not on the application.
2. **Do not refactor for the "framework extraction"** discussed in earlier sessions — that's Phase 2 work; doing it now produces neither a clean library nor a fundable application.
3. **Every change must move the project toward NGI0-credibility.** If you're not sure why a task is on the plan, re-read `01-project-brief.md` §"Where we stand vs. the winner bar."
4. **Update `02-execution-plan.md` after completing any task.** Tick the box, add a note if scope changed.
5. **Mobile-friendly assumption**: the maintainer reviews on a phone. Keep diffs small, commit messages descriptive, and headings clear.
6. **Never commit secrets, real API keys, or PII.** Sanitize any `khalo.org`, real tester names, or production URLs before pushing.
7. **License everything you write under AGPL-3.0** (the project's chosen license — see `01-project-brief.md` §"License decision"). Add SPDX headers in new source files.

---

## How to update this folder

- **Strategic changes** (positioning, scope, target funder): update `01-project-brief.md` and note the decision date.
- **Execution progress** (tasks done, blockers found): update `02-execution-plan.md` and tick checkboxes.
- **Long-term vision changes**: update `03-post-grant.md`.
- **Re-orientation for a new agent**: update this `00-START-HERE.md` only if the high-level summary above is no longer accurate.

If you make a strategic change, **commit it in a separate commit from code changes** so the decision history is visible in git log.

---

## Source-of-truth precedence

If documents disagree, this is the order:

1. `01-project-brief.md` — strategic context wins
2. `02-execution-plan.md` — current task list wins
3. The README and CLAUDE.md at repo root — pointers only, never source of truth
4. Internal commercial docs in `docs/*` (operator-runbook, marketing-copy, sellable-readiness-*) — **scheduled for deletion or relocation in Week 1**. Do not treat them as guidance for grant work.
