<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 DirectJob Scout contributors -->

# Roadmap

**Last updated**: 2026-05-18 (alongside the v0.1.0 release).
**Time horizon**: eight quarters — **2026 Q3 → 2028 Q2**.

This is the public-facing roadmap. The internal multi-phase plan,
funding-arc detail, and decision rationale live in
[`docs/grant/03-post-grant.md`](docs/grant/03-post-grant.md); this
document is a quarterly summary suitable for partners, contributors,
prospective deployers, and grant reviewers.

Language convention: **we plan to**, **scoped for**, **anticipated**,
**under consideration** — never **we will**. The work below is plan,
not promise. Updates to this document accompany every major milestone
or scope decision.

---

## At a glance

| Quarter | Focus | Status |
|---|---|---|
| 2026 Q3 | Grant-sprint completion + first stable release | **In progress** — v0.1.0 shipped 2026-05-18 |
| 2026 Q4 | Third UI language + first NGO pilot deployment + WIP reintegration begins | Scoped |
| 2027 Q1 | Phase 2 NLnet application + framework extraction begins | Anticipated |
| 2027 Q2 | Housing-agent integration hardened; healthcare-agent scoping starts | Anticipated |
| 2027 Q3 | Multi-agent orchestrator scoping | Anticipated |
| 2027 Q4 | Multi-agent civic platform first integration | Anticipated |
| 2028 Q1 | Multi-country localisation begins (Austria) | Under consideration |
| 2028 Q2 | Multi-country localisation continues (France, Netherlands) | Under consideration |

The status column reflects honest project state at the time of writing.
"Scoped" means the work is planned and the resources are in view;
"anticipated" means the work depends on prior milestones landing as
expected; "under consideration" means the work is on the long horizon
and the actual quarter could shift.

---

## 2026 Q3 — Grant-sprint completion + first stable release

**Status**: in progress. v0.1.0 shipped 2026-05-18.

We plan to:

- Complete the remaining Week 3 grant-sprint items: public demo
  deployment (§3.4), documentation site at `docs.<public-domain>`
  (§3.5), accessibility audit and `ACCESSIBILITY.md` (§3.6),
  translator contributor pathway (§3.7), reproducible build via Nix
  flake (§3.8).
- Submit the **Commons Conservancy Programme application** (Week 2
  task 2.1; draft at `docs/grant/commons-conservancy-application-2026-05-18.md`).
- Conduct **institutional outreach** in Week 4: at least one
  Migrationsberatungsstelle, at least one IQ-Netzwerk regional office,
  the TU Berlin Career Service. Goal: one credible letter of support
  for the NLnet application.
- Submit the **NLnet NGI Zero Commons Fund application** by the end
  of Week 4 (target call 14, ~2026-08-01 deadline; final date verified
  per `docs/grant/04-research-and-decisions.md` Open R1).
- Sign v0.1.0 release artifacts with `cosign` and publish the SBOM
  (CycloneDX format).
- Tag a **v0.2.0** post-submission release covering Week 4 polish
  and any minor fixes surfaced during application drafting.

---

## 2026 Q4 — Third UI language + first NGO pilot + WIP reintegration

**Status**: scoped.

We plan to:

- Ship **Arabic** as the third UI language (RTL-rendering work first,
  then translation contributor onboarding via the §3.7 pathway).
  Arabic primarily serves Aïcha + Mahmoud from the persona panel.
- Stand up the **first NGO pilot deployment** at the partner
  Beratungsstelle / IQ-Netzwerk office / Optionskommune that
  contributed a letter of support during the NLnet application.
  Pilot scope: 1–3 advisors plus their clients, 12 weeks, with
  structured feedback collection.
- Run the **first end-to-end bias-testing methodology execution** at
  the pilot deployment (`docs/grant/10-ai-act-compliance.md`
  §"Accuracy + bias testing"). Anticipated outcome: persona-anchored
  bias evidence + advisor-trust calibration data.
- Begin the **WIP reintegration triage** per Decision 16 — the
  parked LLM cost-tracking layer, model router, CV extraction /
  rendering / tailoring modules, and tool-registry layer queued up
  in `docs/grant/03-post-grant.md` are reviewed for fit against the
  civic-commons positioning and either ramped, hardened, or
  deferred.

If the NLnet application is funded (anticipated decision window:
late 2026 Q4), the funded milestones overlap with the work above and
move into 2027 execution.

---

## 2027 Q1 — Phase 2 NLnet application + framework extraction begins

**Status**: anticipated (depends on Phase 1 grant disposition and
pilot evidence).

We plan to:

- Begin **framework extraction** of the shared abstractions across
  DirectJob Scout and any other civic agent the project ecosystem
  has produced (the parallel housing agent, anticipated companion
  healthcare or residency agents). Scope: chat router, journey state
  machine, MCP server packaging, encrypted-profile SDK, i18n loader.
  Initial scoping in 2026 Q4; actual extraction work spans Q1–Q2 2027.
- Submit the **Phase 2 NLnet application** (anticipated ask:
  €40–80k depending on framework-extraction scope). Aligned with the
  multi-grant arc precedent (Redwax pattern: NGI0 PET → NGI0 PKI →
  NGI0 Server Modernisation).
- Apply for **Sovereign Tech Fund** funding in parallel as a
  diversification hedge (German federal fund for critical open-source
  infrastructure; civic-tech alignment strong).
- Submit a **FOSDEM 2027 talk proposal** for the late-September 2026
  deadline (note: this slips into Q3 2026 if calendar tightens) —
  deliverable lands at FOSDEM Brussels in early February 2027.
- Engage with the **HAN University accessibility audit support**
  service offered by NLnet (if funded) for full WCAG 2.2 AA
  conformance work.

---

## 2027 Q2 — Housing-agent integration hardened + healthcare-agent scoping

**Status**: anticipated.

We plan to:

- **Harden the housing-agent integration** that landed during the
  Phase 1 grant sprint (whichever Decision-20 disposition applied:
  Option A mock stub if no friend collaboration, Option B real
  integration if a friend confirmed). The hardening pass takes the
  v0.1.0 reference integration to production-quality with the same
  MCP-composition contract.
- Begin **healthcare-agent scoping** as the second domain in the
  multi-agent civic platform (Krankenversicherung selection, GP
  registration, language-assisted appointments — see Phase 3 plan
  in `docs/grant/03-post-grant.md`). Scoping conversation with
  potential domain-expert collaborators starts here; actual build
  is 2027 Q4.
- Run the **second NGO pilot deployment** — second partner
  organisation, second sector, comparable 12-week structure.
- Cross-platform test-suite cleanup so the CI matrix can broaden
  back to `ubuntu` + `macos-latest` + `windows-latest` (deferred
  in §3.2 — see `docs/grant/03-post-grant.md` Phase 2 item #8).

---

## 2027 Q3 — Multi-agent orchestrator scoping

**Status**: anticipated.

We plan to:

- Scope the **multi-agent orchestrator** that routes a user
  conversation across DirectJob Scout + housing + healthcare
  (+ any other civic agent the ecosystem has produced) in a single
  session. Architecture sketch in `docs/grant/03-post-grant.md`
  §"Phase 3 architectural shape"; the implementable detail emerges
  here.
- Apply for the **Sovereign Tech Fund** or **EU NGI orchestration**
  track for the orchestrator-layer funding (this is structurally
  a separate funding ask from any per-domain agent grants).
- Sustainability work: onboard 2–3 active co-maintainers with named
  responsibilities in `AUTHORS.md`; stand up a public community
  channel (Matrix preferred for the European-sovereignty signal).

---

## 2027 Q4 — Multi-agent civic platform first integration

**Status**: anticipated.

We plan to:

- Ship the **first orchestrator-routed multi-agent civic integration**
  end-to-end — a user starts a conversation with DirectJob Scout,
  gets handed off to the healthcare agent for Krankenversicherung
  registration, returns to DirectJob Scout for the job-application
  step, etc. The portable civic profile (`docs/grant/09-mcp-composition.md`)
  is the data layer that travels with consent across agents.
- Deliver the **FOSDEM 2028 talk** on the multi-agent civic platform
  (assumes the 2027 Q1 talk-proposal cycle landed for FOSDEM 2027,
  with a second talk targeted for FOSDEM 2028).
- Codeberg mirror published for European-sovereignty resilience.

---

## 2028 Q1 — Multi-country localisation begins (Austria)

**Status**: under consideration.

We plan to:

- Localise to **Austria** as the cheapest second-country proof: shared
  German language, similar bureaucratic structure, smaller scale to
  validate the architecture's country-neutrality claim.
- Pilot deployment with a partner organisation in Vienna or
  Salzburg.
- Per-country domain data structure (recognised credentials, agency
  contacts, legal-information boundaries) generalised so the next
  countries are cheaper.

---

## 2028 Q2 — Multi-country localisation continues (France, Netherlands)

**Status**: under consideration.

We plan to:

- Localise to **France** — large migrant population, strong civic-tech
  ecosystem, French co-op partners (BIRU pattern).
- Localise to **Netherlands** — NLnet's home turf, smaller scale,
  multilingual default. Anticipated: Dutch + English + French.
- Each new-country onboarding follows the per-country domain data
  template established for Austria.

---

## Beyond the eight-quarter horizon

The longer-horizon vision lives in
[`docs/grant/03-post-grant.md`](docs/grant/03-post-grant.md) §"Phase 4":
expansion to Belgium, UK, Ireland, Spain, Portugal, Italy, Nordic
countries. The architecture is country-neutral once Phase 3 is solid;
cross-country localisation is a porting exercise, not a rebuild.

The longer-horizon **sustainability model** also lives in the
post-grant doc: five layers across self-hosting (free), hosted
support (low-margin), institutional support contracts, the multi-grant
arc, and foundation governance. Out of scope for this quarterly
roadmap; in scope for any grant or partnership conversation.

---

## How this document changes

Updates land alongside:

- Every quarterly milestone reached (note actual outcome vs scoped
  outcome).
- Every grant decision (acceptance, rejection, scope-shift).
- Every strategic decision logged in `docs/grant/04-research-and-decisions.md`
  Part B that affects the multi-quarter view.

Substantive scope changes go through the same review as code: PR,
maintainer review, merge. Honest scope evolution is encouraged —
silent slippage is not.

---

## Append log

- **2026-05-18**: initial roadmap drafted alongside the v0.1.0 release.
  Eight-quarter horizon covering 2026 Q3 → 2028 Q2. Status of each
  quarter reflects honest project state at time of writing.
