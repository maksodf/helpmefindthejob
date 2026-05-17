# What Comes After the 4 Weeks

**Last updated**: 2026-05-17

This document covers what happens after the application is submitted — both success paths (we win) and failure paths (we don't). It also captures the multi-phase grant arc and the longer-term vision so future agent sessions and contributors can see where the project is heading beyond the immediate funding push.

---

## Immediately after submission (Week 5)

Whether the application is in or not, the same disciplined non-feature work continues for one more week to keep momentum.

- [ ] Archive the submitted application text in `docs/grant/submitted-application-<date>.md` for the record
- [ ] Tag a `v0.2.0` release reflecting all the Week 1–4 work
- [ ] Resume product-feature work cautiously — do not undo any of the commons hardening
- [ ] Continue NGO outreach: even without funding, NGO partnerships matter
- [ ] Continue the housing-agent integration work; the proof-of-composition gets stronger every week

---

## If we win the grant

### Within 2 weeks of acceptance

- Sign the grant agreement with NLnet
- Set up the milestone-based deliverable tracking they expect
- Engage NLnet support services declared in the proposal:
  - Accessibility audit by HAN University
  - Packaging support by NixOS Foundation (if Nix flake was committed to)
  - Security audit (if scope is above €50k)
  - Governance/sustainability mentoring

### Milestones during the grant (typical 6–9 month execution window)

These map roughly to the deliverables proposed. Specific milestones get updated when the application is drafted.

1. **M1: MCP server hardening** — full schema versioning, integration tests, published as a discrete artifact for external consumption
2. **M2: Third UI language** — translation contributed by an NGO partner, native-reviewed
3. **M3: WCAG 2.2 AA conformance** — audit complete, fixes deployed, conformance statement published
4. **M4: Reference NGO deployment** — one Beratungsstelle running an instance for real users
5. **M5: Portable encrypted-profile spec** — JSON schema for civic profiles, import/export tooling, documented
6. **M6: Final deliverables published** — code shipped under AGPL-3.0, all docs on the site, security audit results addressed

### Sustainability work during the grant

- File for a legal entity wrapper (lightweight: a French SCOP, a German Verein, or a Dutch Stichting)
- Onboard 2–3 active co-maintainers with named responsibilities in AUTHORS.md
- Set up a public community channel (Matrix preferred over Discord for an open-commons project)
- Publish quarterly progress reports on the website (separate from grant milestone payments)

---

## If we don't win the grant

A rejection is not a failure of the project, only of one round. NGI0 runs multiple calls per year.

### Within 1 week of rejection

- Request feedback from NLnet (they sometimes provide it)
- Compare our application to recently-funded ones in the same call
- Note specific gaps for next round

### Within 4 weeks of rejection

- Address the specific gaps identified
- Apply to other relevant funds (in priority order):
  - **NGI0 next call** (Commons Fund runs multiple times per year)
  - **Sovereign Tech Fund** (German federal fund for critical open-source infrastructure) — possibly stronger fit given German focus
  - **Prototype Fund Deutschland** (Open Knowledge Foundation DE, BMBF-backed) — explicitly civic-tech
  - **EU NGI other tracks** (Entrust, Discovery if revived, etc.)
  - **Mercator Stiftung / Bosch Stiftung** — German foundation route, longer timelines

### Continue building regardless

- The hardening work from Weeks 1–4 is valuable whether funded or not
- The repo is now grant-credible — apply again next round
- Continue NGO outreach: partner deployments do not require grant money
- Continue MCP composition work with the housing agent

---

## Phase 2: Framework extraction (12–18 months after grant)

This is the work we explicitly *deferred* during the 4-week sprint. It becomes viable once:

- DirectJob Scout has shipped v1.0 (feature-complete per the original product vision)
- The housing agent is production-stable and visible
- The MCP integration between them has been live for several months
- Patterns of shared logic have crystallized into obvious abstractions

### What gets extracted

The "Civic Agent Toolkit" the earlier session scoped:

- `chat_router.py` → standalone library: command registry, intent routing, multi-turn elicitation, confirmation gates
- Journey state machine → standalone library: phase definitions, callback protocol, AI-provider abstraction
- Encrypted profile-at-rest → standalone library: ChaCha20 vault with portable JSON schema
- i18n loader → namespaced multi-app translation system
- AI provider abstraction → already standalone-ready (`ai_providers.py`)

### Why we defer it

- The earlier audit found ~11 weeks of refactor work to extract cleanly
- Premature abstraction without a third consumer risks bloated base classes
- The grant rewards delivered code, not future libraries
- We can pitch this as Phase 2 with the existing track record from Phase 1

### Phase 2 grant strategy

- Apply to NGI0 a second time with two existing reference implementations (jobs + housing) and the explicit framework extraction as the new scope
- Budget: €40–80k for ~10 weeks of two-engineer refactor + docs + WCAG audit + packaging
- The framework is the commons; the existing agents become the proof

---

## Phase 3: Multi-agent civic platform (18–36 months)

If Phase 1 and Phase 2 land, the next horizon is genuine multi-agent civic composition.

### Domains we'd add (in priority order)

1. **Healthcare access** (Krankenversicherung selection, GP registration, language-assisted appointments)
2. **Residency / visa** (carefully: must stay informational under Rechtsdienstleistungsgesetz, partner with Beratungsstellen)
3. **Education / language courses** (Integrationskurs, Berufssprachkurs, recognition of foreign diplomas)
4. **Financial onboarding** (Bankkonto, Steuer-ID, Lohnsteuerklasse)
5. **Housing** (already in-flight as the second agent)

### Architectural shape

- Each domain is an independent agent built on the Civic Agent Toolkit (Phase 2 framework)
- All agents share a portable user profile (with explicit consent per share)
- A meta-orchestrator handles routing between agents in a single conversation
- Government / NGO / Beratungsstelle deployers can pick which agents to enable

### Funding strategy for Phase 3

- Sovereign Tech Fund or EU NGI for the orchestration layer
- Per-domain grants from sector-specific funds (Diakonie for migration, BMFSFJ for family/integration, BMG for healthcare)
- Optional: hosted Pro tier for end users who choose convenience over self-hosting; revenue flows back to the foundation

---

## Phase 4: Multi-country expansion (36+ months)

The architecture is country-neutral once Phase 3 is solid. Localization to other EU countries is a porting exercise, not a rebuild.

### Likely early targets

- **Austria** — language overlap, similar bureaucratic structure, smaller scale → cheap proof
- **France** — large migrant population, civic-tech ecosystem strong, French co-op partners exist (BIRU pattern)
- **Netherlands** — NLnet's home turf, smaller scale, multilingual norm
- **Belgium** — multilingual by default (NL/FR/DE), Brussels EU centrality
- Then UK / Ireland / Spain / Portugal / Italy

### What expansion requires

- Per-country domain data (recognized credentials, agency contacts, legal-information boundaries)
- Native-speaker translation contributors
- Local NGO deployment partners
- Compliance review per jurisdiction

---

## Sustainability model (the long answer)

For a civic commons to survive past the initial grant, it needs a sustainability model that does not require the maintainers to subsidize it indefinitely.

### Layers of sustainability

1. **Self-hosting (free)** — individuals, small NGOs, hobbyists. No money flows.
2. **Hosted Pro tier (low-margin)** — for end users who don't want to self-host. Revenue funds development of the open commons.
3. **Institutional support contracts** — Beratungsstellen, public agencies, larger NGOs pay for deployment help, training, SLA, custom integrations. Revenue funds development.
4. **Grant arc** — NGI0 Phase 1 → Phase 2 → Sovereign Tech Fund → Prototype Fund → EU programmes. Each grant funds a specific extension, never general operations.
5. **Foundation / legal entity** — once the project has a track record, register as a foundation (Stichting in NL, gGmbH or Verein in DE) to receive philanthropic donations and apply for restricted funds.

### What sustainability is NOT

- Not advertising-supported (incompatible with commons)
- Not data-monetization (incompatible with privacy positioning)
- Not vendor lock-in (incompatible with AGPL + BYO-AI)
- Not "all on the maintainer's free time" (unsustainable)

---

## How this document changes

Update this document when:

- A grant application is submitted, accepted, or rejected (note the outcome and lessons)
- A milestone is reached (note the date and what shipped)
- A phase transition happens (Phase 1 → 2, etc.)
- A strategic decision shifts the long-term direction
- A new funding source becomes relevant

Append entries below this line with dates:

**2026-05-17**: document created during pre-application planning session.
