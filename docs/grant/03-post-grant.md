# What Comes After the 4-Week Sprint

**Last updated**: 2026-05-17

This document covers what happens after the application is submitted — both success paths (we win) and failure paths (we don't) — and the longer-term multi-phase vision for the project past Phase 1.

---

## Immediately after submission (Week 5)

Whether the application is in or not, disciplined non-feature work continues for one more week to lock in momentum and let the maintainer recover.

- [ ] Archive the submitted application text in `docs/grant/submitted-application-<date>.md`
- [ ] Tag a `v0.2.0` release reflecting all Week 1–4 work
- [ ] Communicate transparently with any letter-of-support partner about submission status
- [ ] Continue any in-flight housing-agent integration
- [ ] Take at least 2 full rest days
- [ ] Resume feature work cautiously — do not undo any of the commons hardening
- [ ] Begin the WIP reintegration triage (next section)

---

## WIP reintegration triage (begins Week 5 / day-after-submission)

### Context

During the planning phase (May 2026), an existing branch named `wip/product-work` was created to park substantial in-flight feature work that was developed on `main` in parallel with the grant-sprint planning. The branch was created to keep the 4-week sprint focused on commons-hardening rather than feature integration, while preserving every byte of recent product engineering for future use.

The `wip/product-work` branch contains, at minimum:

- **CV layer**: `cv_extraction`, `cv_renderer`, `cv_tailor` modules — pull structured CV data from documents, render to printable/exportable formats, tailor CVs per job posting
- **LLM cost / observability layer**: `llm_cost_tracker`, `llm_pricing`, `llm_response_cache` modules — instrument token usage, attribute cost per call, cache deterministic AI responses
- **Model routing**: `model_router` — route requests to the cheapest viable model per task
- **Tool layer**: `tool_actions_store`, `tool_registry`, `tool_use_router`, and the `company_discovery/tools/` directory — internal tool-use orchestration parallel to the MCP server
- **Probe scripts, tests, screenshots, reports** — development artifacts
- **`HANDOFF_RESTART.md`** — session-handoff note from a prior coding session

Engineering maturity per module is not yet verified. The triage process below establishes maturity before any reintegration.

### Why a triage process is needed

Three failure modes are common when reintegrating WIP work:

1. **Bulk-merge regression**: pulling all modules in at once causes cascading test failures and obscures which change caused what
2. **Misaligned features**: modules built for the earlier commercial vision (Pro/Free tier, billing-driven features) may not serve the civic-commons positioning
3. **Compliance-debt accumulation**: features added without audit logging, transparency notices, or human-oversight hooks accumulate AI Act compliance debt that has to be repaid later — at higher cost

The triage prevents all three.

### Strategic ranking (initial priority — adjusted after triage reveals actual maturity)

| Rank | Module(s) | Strategic alignment | Reasoning |
|---|---|---|---|
| 1 | `llm_cost_tracker`, `llm_pricing`, `llm_response_cache` | Highest | Cost-saving-doctrine evidence in code form. Every euro avoided becomes a measurable number. Low integration cost (mostly additive observability around `ai_providers.py`). |
| 2 | `model_router` | High | Strengthens BYO-AI story and reinforces cost-saving directly. Depends on cost-tracker data to route well; naturally sequenced after rank 1. |
| 3 | `cv_extraction`, `cv_renderer`, `cv_tailor` | High | CV is the single most-used user touchpoint. Persona panel (especially Mahmoud's Ausbildung-format Bewerbungsmappe need) depends on richer CV capabilities. |
| 4 | `tool_registry`, `tool_use_router`, `tool_actions_store`, `company_discovery/tools/` | High but framework-shaped | Structurally parallel to the MCP server. In Phase 2's framework extraction (see below), this is likely the internal implementation layer that powers MCP tools we expose externally. Best brought back together with framework-extraction work. |
| 5 | Probe scripts, screenshots, reports | Low | Development artifacts. Most go to `private/`. A small number of probe scripts may have value as integration tests if they exercise specific flows. |
| 6 | `HANDOFF_RESTART.md` and similar session-handoff notes | None | Scaffolding, not product. Move to `private/` or delete after content review. |

### The four-question triage gate

Apply to every module before reintegration. A module that fails any one of these does not merge until the failure is resolved.

1. **Strategic alignment**: does it serve the cost-saving doctrine, the MCP composition story, the persona panel's actual needs, or the EU-wide positioning? If not — defer indefinitely or delete.
2. **Engineering maturity**: are there tests? Does the test suite pass? Are the dependencies pinned? If not — schedule the hardening work *before* merging.
3. **AI Act compliance**: does the module add new AI-driven behaviour? If so, does it have audit logging, transparency notices, human-oversight hooks per the compliance pack in `10-ai-act-compliance.md`? If not — extend the compliance work to cover it *before* merging.
4. **Persona impact**: does at least one persona in `07-personas.md` concretely benefit? Can the benefit be described in one specific sentence about a specific persona? If not — the module is solving a hypothetical, not a real need; defer.

### Reintegration discipline (anti-patterns to avoid)

- **Do not merge everything at once.** Each module lands on its own branch, with its own PR, its own test pass, its own rollback path.
- **Do not merge without tests.** If a WIP module has tests, those run green. If it does not, write them before merging. The cost is real; pay it once.
- **Do not merge without observation.** Each reintegrated module ships behind a feature flag (env-var-driven) for the first week. Observe before defaulting it on.
- **Do not merge directly into `main`.** Merge into a Phase 2 working branch (e.g. `phase-2-cost-layer`), exercise it, observe, then merge to main when it has been live and stable for a week.
- **Do not break the `v0.1.0` release shape.** The grant application points at a specific release artifact. Do not surprise reviewers with `v0.5.0` by the time they look. Tag minor versions, do not skip.
- **Do not pull modules in just because they are "almost done."** "Almost done" is the most expensive state in software. Either finish it deliberately or leave it parked.

### The triage session — concrete next step

The day after grant submission (Week 5 day 1), run a single triage session with the coding agent:

1. Check out the `wip/product-work` branch and read each module's current state
2. For each module, apply the four-question gate above and record the answer in a new file `docs/grant/wip-triage-<date>.md`
3. Sort the modules into three buckets:
   - **Ready to merge** after a hardening pass (tests + audit logging + transparency notice if AI-related)
   - **Needs hardening first** before merging is realistic
   - **Defer to framework-extraction window** OR **delete**
4. Produce the Phase 2 reintegration plan with the priority order from the strategic ranking, adjusted for whatever the actual code state reveals
5. Commit the plan to `docs/grant/wip-triage-<date>.md` and link it from this section as the reference

### What success looks like

By the end of Phase 2 (~6–12 months after grant submission):

- The **LLM cost layer** is live, producing real numbers from at least one institutional pilot deployment — cost-saving claims become measured, not estimated
- The **model router** is routing in production, with telemetry showing actual cost reductions
- The **CV layer** has shipped its most user-facing capabilities (extraction + tailor at minimum); rendering quality matches German hiring conventions
- The **tool layer** has been folded into the framework extraction or has been deliberately retired in favour of the MCP-exposed surface
- All other WIP modules are either reintegrated, deferred with an explicit second-look date, or deleted with a one-line rationale in the triage log

**The single most important rule**: every reintegrated module passes through the same hardening gauntlet the grant sprint built (CI, lint, type check, coverage, security scan, audit logging, AI Act compliance review). The 4 weeks of grant work raise the project's quality bar permanently. Every future feature, including reintegrated WIP, meets that bar or does not ship.

---

## If we win the grant

### Within 2 weeks of acceptance

- Sign the grant agreement with NLnet
- Set up the milestone-based deliverable tracking
- Engage NLnet support services declared in the proposal:
  - Accessibility audit by HAN University
  - Packaging support by NixOS Foundation
  - Security audit (if scope is above €50k or if requested)
  - Governance/sustainability mentoring
- Publish a project update naming the grant, on the website and via partners

### Milestones during the grant (6–9 month execution window)

The exact milestones submitted in the application become the binding deliverable list. The grant calls for ~6 milestones based on `12-application-package.md`:

1. **M1 — Legal and narrative foundations** (delivered before submission for the application itself)
2. **M2 — MCP composition reference** (delivered before submission)
3. **M3 — EU AI Act compliance pack** (delivered before submission, refined during grant)
4. **M4 — Public demo deployment and accessibility** (refined during grant; full WCAG 2.2 AA conformance attempted)
5. **M5 — Reproducible builds and quality signalling** (delivered before submission, refined during grant)
6. **M6 — Institutional readiness and standards interop** (Commons Conservancy admission completed; ESCO/EURES expanded; first institutional pilot scoped)

Most of the Phase 1 deliverables are shipped *before* submission as evidence of execution capability. The grant funds the *refinement, documentation, audits, and institutional pilots* during the 6–9 month period.

### Sustainability work during the grant

- File for additional legal-entity scaffolding if Commons Conservancy admission needs supplementing
- Onboard 2–3 active co-maintainers with named responsibilities in `AUTHORS.md`
- Set up a public community channel (Matrix preferred for the European-sovereignty signal; alternative: GitHub Discussions)
- Publish quarterly progress reports separate from grant milestone payments
- Submit a FOSDEM 2027 talk proposal (deadline typically late September 2026)
- Begin scoping the Phase 2 application

---

## If we don't win the grant

A rejection is one round, not the project's end. NLnet runs rolling 2-month deadlines.

### Within 1 week of rejection

- Request feedback from NLnet (sometimes provided)
- Compare the application to recently-funded ones in the same call
- Note specific gaps for the next round

### Within 4 weeks of rejection

- Address the specific gaps
- Apply to the next NLnet call (cadence: 2 months)
- In parallel, apply to other relevant funds:
  - **Sovereign Tech Fund** (German federal fund for critical open-source infrastructure, run by SPRIND) — particularly strong fit given the German civic-tech alignment
  - **Prototype Fund Deutschland** (Open Knowledge Foundation DE, BMBF-backed) — civic-tech-aligned, smaller grants, faster cycles
  - **EU NGI other tracks** (Entrust, PET if revived, etc.)
  - **Mercator Stiftung / Bosch Stiftung** — German foundation route, longer timelines
  - **EU AMIF** (Asylum, Migration and Integration Fund) if positioning aligns

### Continue building regardless

- The hardening work from Weeks 1–4 is valuable whether funded or not
- The repo is now grant-credible — apply again next round
- Continue NGO outreach: partner deployments do not require grant money
- Continue MCP composition work with the housing agent

---

## Phase 2 (~6–12 months after Phase 1 grant): Multi-grant arc + framework extraction

### What gets done in Phase 2

1. **Framework extraction** — the work explicitly deferred during Phase 1. Once DirectJob Scout and the housing agent have both been running for several months, the shared abstractions become obvious. The 11-week refactor scoped earlier (chat router, journey state machine, MCP server packaging, encrypted-profile SDK, i18n loader) becomes the Phase 2 grant.
2. **Second NLnet application** — leveraging Phase 1 completion as evidence of delivery capability. NLnet's program rewards multi-round arcs (Redwax precedent).
3. **First institutional pilot deployment** — at the partner Beratungsstelle / IQ-Netzwerk office / Optionskommune that signed the letter of support.
4. **Security audit through NLnet support services** if not already done.
5. **WCAG 2.2 AA full conformance** with HAN University audit support.
6. **FOSDEM 2027 talk delivered** — credibility multiplier.
7. **Codeberg mirror** for European-sovereignty resilience.

### Phase 2 grant ask

- €40–80k depending on framework-extraction scope
- Three or four milestones, each verifiable
- Aligned with the multi-grant arc precedent (Redwax: NGI0 PET → NGI0 PKI → NGI0 Server Modernisation)

---

## Phase 3 (~12–24 months): Multi-agent civic platform

If Phase 1 and Phase 2 land, the next horizon is genuine multi-domain civic composition.

### Domains we'd add (priority order)

1. **Healthcare access** — Krankenversicherung selection, GP registration, language-assisted appointments
2. **Residency / visa support** — informational only (Rechtsdienstleistungsgesetz constraints), partnered with Beratungsstellen
3. **Education / language courses** — Integrationskurs, Berufssprachkurs, foreign-diploma recognition
4. **Financial onboarding** — Bankkonto, Steuer-ID, Lohnsteuerklasse
5. **Housing** — already in flight as the partner agent

### Architectural shape

- Each domain is an independent agent built on the Civic Agent Toolkit (Phase 2 framework)
- All agents share the portable civic profile, with explicit consent per share
- A meta-orchestrator routes between agents in a single conversation
- Government / NGO / Beratungsstelle deployers pick which agents to enable

### Funding strategy for Phase 3

- Sovereign Tech Fund or EU NGI for the orchestration layer
- Per-domain grants from sector-specific funds (Diakonie for migration, BMFSFJ for family/integration, BMG for healthcare, BMBF for education)
- Possible hosted Pro tier for end users who choose convenience over self-hosting; revenue flows back to the foundation governance

---

## Phase 4 (~24–48 months): Multi-country expansion

The architecture is country-neutral once Phase 3 is solid. Cross-country localisation is a porting exercise, not a rebuild.

### Likely early targets

- **Austria** — language overlap, similar bureaucratic structure → cheapest proof
- **France** — large migrant population, civic-tech ecosystem strong, French co-op partners exist (BIRU pattern)
- **Netherlands** — NLnet's home turf, smaller scale, multilingual norm
- **Belgium** — multilingual by default (NL/FR/DE), Brussels EU centrality
- Then UK / Ireland / Spain / Portugal / Italy / Nordic countries

### What expansion requires

- Per-country domain data (recognised credentials, agency contacts, legal-information boundaries)
- Native-speaker translation contributors
- Local NGO deployment partners
- Compliance review per jurisdiction (GDPR baseline + national variations)

---

## Sustainability model (the long-term answer)

For a civic commons to survive past the initial grant arc, it needs a sustainability model that does not require maintainers to subsidise it indefinitely.

### Five layers

1. **Self-hosting (free)** — individuals, small NGOs, hobbyists. No money flows.
2. **Hosted support (low-margin)** — for institutional deployers who want hosting plus light SLA. Revenue funds development.
3. **Institutional support contracts** — Beratungsstellen, public agencies, larger NGOs pay for deployment help, training, custom integrations, AI-Act-compliance-pack customisation. Revenue funds development.
4. **Grant arc** — NGI0 Phase 1 → Phase 2 → Sovereign Tech Fund → Prototype Fund → EU AMIF → EU NGI tracks → German federal foundations. Each grant funds a specific extension, never general operations.
5. **Foundation governance** — once the project has a track record, Commons Conservancy or a follow-on dedicated foundation can receive philanthropic donations and apply for restricted funds.

### What sustainability is NOT

- Not advertising-supported (incompatible with commons)
- Not data-monetisation (incompatible with privacy positioning)
- Not vendor lock-in (incompatible with Apache 2.0 + BYO-AI)
- Not "all on the maintainer's free time" (unsustainable, demonstrated repeatedly in the FOSS world)

---

## How this document changes

Update this document when:

- A grant application is submitted, accepted, or rejected (note outcome and lessons)
- A milestone is reached (note date and what shipped)
- A phase transition happens (Phase 1 → 2 etc.)
- A strategic decision shifts long-term direction
- A new funding source becomes relevant

Append entries with dates below this line:

**2026-05-17**: document updated to reflect Apache 2.0 + CLA license, The Commons Conservancy admission target, the cost-saving doctrine, AI Act compliance, multi-persona panel, EU-wide positioning, and the verified Bundesagentur für Arbeit labor-shortage primary-source data.
