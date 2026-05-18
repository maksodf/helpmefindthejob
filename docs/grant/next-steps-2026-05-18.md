<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 DirectJob Scout contributors -->

# Next steps — 5 concrete items derived from current repo state

**Date**: 2026-05-18 (post-cleanup of advisory-introduced false dependencies — see `cleanup-audit-2026-05-18.md`).
**Authority**: this report supersedes the prior advisory speculation about §3.4 sequencing. The 5 items below are derived from the audit and the verified state of the repository, not from any prior pre-decided framing.
**Constraint**: each item names deliverable + planning-workspace anchor + prerequisites + estimate + agent-doable-vs-needs-maintainer.

---

## Step 1 — Resolve Open R8 (demo URL in the public tree)

**STATUS — CLOSED 2026-05-18 — placeholder convention retained per maintainer decision. Historical context preserved below for audit trail.**


| Field | Value |
|---|---|
| **Deliverable** | A one-line maintainer answer to `04-research-and-decisions.md` Open R8 (updated 2026-05-18): "public tree continues to use `app.directjob-scout.example` placeholders (Decision 12 default)" **OR** "name the real subdomain in the public tree (reversing the Week 1 task 1.4 sanitisation for the demo URL only)." Once answered, a small public-tree edit follows if the maintainer chose option B. |
| **Planning anchor** | `04-research-and-decisions.md` Open R8 (now re-scoped). `docs/grant/02-execution-plan.md` §3.4 references this open question as a §3.4 prerequisite. Decision 12. |
| **Prerequisites** | A single one-line decision from the maintainer. **Not in place today.** |
| **Estimate** | Maintainer time: ~30 seconds. Agent time (option B follow-through, if chosen): ~10 minutes for a small commit updating README + `12-application-package.md` + any application-package draft references. |
| **Agent-doable?** | **No — requires maintainer input first.** The question is a personal-preference / sanitisation-policy call; pre-deciding it would violate Rule 5. Once answered, the follow-through is agent-doable. |

---

## Step 2 — §3.4 generic deployment recipe + seven-persona seed script

| Field | Value |
|---|---|
| **Deliverable** | `docs/deployment-recipe.md` — a generic recipe that extends the existing `docs/production-deployment.md` with the persona-seed step and the "use existing infrastructure" framing. Plus a `scripts/seed-personas.py` that reads `docs/grant/07-personas.md` and seeds all seven demo accounts (Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias) with a shared maintainer-chosen demo password. Idempotent (re-run = no-op; partial-state cleanup + retry). The recipe document is **generic**, not Hetzner-specific. |
| **Planning anchor** | `docs/grant/02-execution-plan.md` §3.4 (the re-anchored task list). Decision 21 (seven personas). |
| **Prerequisites** | The maintainer-chosen demo password (one-line answer; default = TBD placeholder in the seed script with a `--password` flag the maintainer passes at run time). Nothing else — runs against the existing `docker-compose.prod.yml` + Caddy stack. **Demo password decision NOT in place today.** |
| **Estimate** | Recipe: ~2 hours. Seed script + tests: ~2 hours. Total: ~4 hours including a green test pass. |
| **Agent-doable?** | **Yes — autonomous** once the demo-password decision is logged. The recipe extends existing docs; the seed script reads from version-controlled persona source-of-truth; both are pure-software deliverables. |

---

## Step 3 — Open R12 close (synthetic-cohort bias-testing interim run)

| Field | Value |
|---|---|
| **Deliverable** | Three artefacts the methodology at `compliance/accuracy-and-bias-testing.md` already specifies but has not yet produced: (a) `tests/fixtures/personas/` — synthetic-but-realistic profile records for all seven personas, shaped per §2.1; (b) `tests/test_bias_methodology.py` — runs the methodology against the fixtures and asserts the divergence-from-tolerance counts under the bands of §2.4; (c) `docs/grant/bias-testing-2026-05-XX.md` — the first executed run's report per §2.5. Closes the transparency notice's "preliminary results due Week 3" claim before NLnet submission. |
| **Planning anchor** | `docs/grant/04-research-and-decisions.md` Open R12 (added 2026-05-18 with status `IN PROGRESS — scheduled for Phase 1 close before NLnet submission`). Methodology contract at `compliance/accuracy-and-bias-testing.md` §§2–6 (executed here, not redesigned). |
| **Prerequisites** | The seven persona profiles in `docs/grant/07-personas.md` are the source of truth (already settled). An AI provider chosen for the first run — Ollama default for fully-offline / reproducible-result reasons; `manual` provider also acceptable if the maintainer prefers documented hand-replay of prompts. **AI-provider choice is the one open prerequisite**; everything else is in place today. |
| **Estimate** | ~6–10 h. **Persona-fixture work-share with Step 2**: the fixtures at `tests/fixtures/personas/` and the seed records used by `scripts/seed-personas.py` consume the same persona-source-of-truth and emit comparable record shapes. Sharing the fixture-builder between R12 and §3.4 saves ~2–3 h of duplicate work and reduces drift risk. The two steps should be bundled into a single execution slice for that reason. |
| **Agent-doable?** | **Yes — autonomous** once the AI-provider choice is locked. The methodology is documented; the fixtures are mechanical; the bias-testing report is structured per §2.5. Maintainer reviews the divergence table after the first run; remediation surface (if any) is the next-after. |

---

## Step 4 — §3.5 documentation site (mkdocs-material on GitHub Pages)

| Field | Value |
|---|---|
| **Deliverable** | A `mkdocs.yml` at repo root, mkdocs-material theme configured, navigation mirroring the README + ROADMAP + CHANGELOG + ARCHITECTURE + STANDARDS + /compliance/ + docs/grant/ structure, and a `.github/workflows/docs-publish.yml` that deploys to GitHub Pages on every push to `main` (and the working branch during the grant sprint). Landing page mirrors the README's reframed opener (Aïcha + Käthe vignette). |
| **Planning anchor** | `docs/grant/02-execution-plan.md` §3.5. Decision 21 (friction-class framing in landing-page copy). |
| **Prerequisites** | GitHub Pages enabled for the repo (maintainer action — *Settings → Pages → Source: GitHub Actions*). The current branch protection settings are sufficient. **GitHub Pages may or may not be enabled today** — that needs verification by the maintainer or via `gh api`. |
| **Estimate** | ~3 hours including the workflow file, the mkdocs config, the navigation structure, and a green Pages deploy. |
| **Agent-doable?** | **Yes — autonomous** for the workflow + config + navigation. The maintainer flicks the GitHub Pages source setting once (~30 seconds) if it's not already on. |

---

## Step 5 — §3.6 accessibility audit + `ACCESSIBILITY.md`

| Field | Value |
|---|---|
| **Deliverable** | `ACCESSIBILITY.md` at repo root documenting the WCAG 2.2 AA conformance scope, current state (honestly: not yet audited at AA scale), known gaps, and remediation plan. The audit covers `app.py` HTTP-served HTML, `static/index.html`, the seven `/compliance/transparency-notice.md` + `/compliance/deployer-operating-manual.md` user-facing artifacts (per the maintainer's §3.6 framing earlier in this session — "extend WCAG 2.2 AA target to cover the /compliance/ transparency-notice and deployer-operating-manual as well"). Includes a Pa11y or axe-core CLI run-list and the documented results. |
| **Planning anchor** | `docs/grant/02-execution-plan.md` §3.6. WCAG 2.2 AA target listed under `STANDARDS.md`. The audit is part of the NLnet application's M4 milestone. |
| **Prerequisites** | An axe-core or Pa11y CLI run-target (the existing static + the running app's main routes). The maintainer can also use the NLnet support service "Accessibility audit by HAN University" post-funding (per `docs/grant/03-post-grant.md`), but a self-administered Phase 1 audit is the §3.6 deliverable. **No external prerequisites.** |
| **Estimate** | ~6 hours. Initial axe-core/Pa11y run + categorised findings + remediation list. The actual remediation work is iterative and not all in §3.6. |
| **Agent-doable?** | **Mostly yes** — running axe-core, drafting the findings table, writing the remediation plan, all autonomous. Some triage calls ("is this AA non-conformance or AAA enhancement?") may surface as 2–3 specific questions. |

---

## Step 6 — §3.7 translator contributor pathway

| Field | Value |
|---|---|
| **Deliverable** | `TRANSLATING.md` at repo root (or `docs/translating.md`) documenting how a native-speaker contributor onboards to add or maintain a language bundle. Covers the bundle file location (`static/i18n/<locale>.json`), the parity contract (`tests/test_phase0_i18n_parity.py`), the German bureaucratic conventions to preserve (when a string is a German legal term, do not translate), the consent-first attribution policy (per Decision 18), and the per-language status table (EN + DE shipped; Arabic, Ukrainian, Turkish, Romanian on the post-grant roadmap with Käthe + Tobias as German-native personas that add no language-roadmap cost). |
| **Planning anchor** | `docs/grant/02-execution-plan.md` §3.7. Decision 6 (language strategy). Decision 18 (consent-first authorship). Decision 21 (Käthe + Tobias addition to the panel without language-roadmap cost). |
| **Prerequisites** | None — the existing i18n parity test gives the contract; the persona panel + Decision 21 framing are settled; consent-first attribution policy is in place via `AUTHORS.md`. **All prerequisites in place today.** |
| **Estimate** | ~2 hours. Pure-software deliverable. |
| **Agent-doable?** | **Yes — autonomous.** Pure-doc work over settled decisions. |

---

## What is NOT in the 6-step list

The maintainer's earlier in-session framing mentioned §3.8 (Nix flake) and Week 4 (outreach + application drafting + cosign signing + final polish). Those are real, but they are **further out** than the six immediate steps above. Specifically:

- **§3.8 Nix flake**: agent-doable autonomously; depends on the Phase 1 baseline being stable. Estimate ~4 hours. Sequenced after §3.7.
- **§3.9 outreach follow-ups**: deferred per Decision 19 to Week 4 start. Not in the next-6.
- **Week 4 tasks**: outreach send pass, sustainability section in README, letter-of-support consolidation, application drafting, final polish, submission. These are dependent on Week 3 completion and an active outreach window; not in the next-6.
- **§2.5 housing-agent integration**: deferred — friend-response window active through 2026-05-23. Maintainer signal triggers either Option A (mock stub, agent-doable) or Option B (real friend collaboration). Not in the next-6.

*Open R12 was promoted into the next-six list as the new Step 3 per maintainer decision 2026-05-18 (i — close in Phase 1). The earlier "possible-advisory-artifact" framing is superseded by Open R12 in `04-research-and-decisions.md`.*

---

## Order of execution recommended

R8 ANSWERED 2026-05-18 (placeholder convention retained); Step 1 is closed. The remaining dependency order:

1. ~~Step 1 (Open R8 answer)~~ — **closed** 2026-05-18.
2. Step 2 + Step 3 **bundled** (§3.4 deployment recipe + seed script **and** R12 bias-testing interim run). The persona-fixture work-share between the two steps saves ~2–3 h of duplicate work and reduces drift risk; bundle into a single execution slice.
3. Step 4 (docs site) — independent; can run in parallel with the Step 2 + 3 bundle.
4. Step 5 (accessibility audit) — independent; can run in parallel.
5. Step 6 (translator pathway) — independent; can run in parallel.

Steps 2+3, 4, 5, and 6 are largely parallel after R8's closure.

---

## What I am explicitly not recommending

- **No new hosting provider**, registrar, monitoring vendor, or domain. The maintainer's existing infrastructure stays.
- **No new VM** or compute target. The existing `scripts/deploy.sh` toolchain works against any SSH-accessible host the maintainer already operates.
- **No introduction of external service accounts** beyond what is already in the codebase (Stripe, SMTP provider, AI providers — all configurable, none required).
- **No sequence-jumping**: §3.4 → §3.5 → §3.6 → §3.7 → §3.8 → Week 4 stays. No promotion of "the next thing" without maintainer green-light.

Append-log: this report supersedes any prior advisory speculation about §3.4 sequencing. Future re-reads should treat this document and the audit as the current state of next-steps thinking.
