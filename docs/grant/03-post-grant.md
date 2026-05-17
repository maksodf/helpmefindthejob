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
