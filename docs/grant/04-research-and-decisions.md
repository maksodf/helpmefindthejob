# Research Findings and Decisions Log

**Status**: living record. Append when new research lands or a strategic decision is made.

This document consolidates: (a) every primary-source fact we have verified during planning, (b) every strategic decision made with its date and reasoning, and (c) open research questions still pending.

If a number, claim, or decision in `01-project-brief.md` ever seems off, the source of truth is here. Strategic decisions in this document override prose anywhere else in the workspace.

---

## Part A — Verified facts (sourced)

### Funder: NLnet NGI Zero Commons Fund

| Fact | Verified value | Source |
|---|---|---|
| Grant range | €5,000 – €50,000 (scale-up beyond on proven potential) | NLnet Commons Fund page |
| Cumulative cap per third party | €500,000 over fund lifetime | NLnet Commons Fund FAQ |
| Programme period | 2024-01-01 to 2027-06-30 | NLnet, EU CORDIS project 101135429 |
| Total programme budget | €21.6 million | NLnet, EU CORDIS |
| Deadline cadence | Every 2 months (rolling) | NLnet Commons Fund page |
| Recent open call | 13th call: 1 April 2026 – 1 June 2026 12:00 CEST | NLnet announcement |
| Next call deadline (approximate) | 1 August 2026 (call 14, dates inferred from cadence) | inferred from 2-month rolling pattern |
| Payment model | Milestone-based, results-only — no progress reports | Guide for Applicants |
| Geographic priority | EU + Horizon-associated; non-EU eligible with European dimension | Guide for Applicants |
| Open-source requirement | Recognised free/open licence, full source published | Guide for Applicants |
| Above €50k obligations | Prior completed milestone, WCAG compliance contractually, security audit contractually | Guide for Applicants |
| Review criteria | Technical merits, strategic NGI relevance, value for money | Guide for Applicants |

### EU AI Act timing and obligations

| Fact | Verified value | Source |
|---|---|---|
| Regulation | (EU) 2024/1689 | EUR-Lex |
| Entry into force | 1 August 2024 | EUR-Lex |
| **High-risk AI (Annex III) obligations applicable from** | **2 August 2026** | AI Act Service Desk; Lexology guidance |
| DirectJob Scout's classification | High-risk under Annex III §4(a) and §4(b) — employment-related AI | Annex III text |
| Required: risk management | Article 9 | AI Act |
| Required: data governance | Article 10 | AI Act |
| Required: technical documentation | Article 11 + Annex IV | AI Act |
| Required: record-keeping (logs) | Article 12 | AI Act |
| Required: transparency to deployers | Article 13 | AI Act |
| Required: human oversight | Article 14 | AI Act |
| Required: accuracy + robustness + cybersecurity | Article 15 | AI Act |
| Maximum fine for non-compliance | €15M or 3% global turnover | AI Act |

### German labor market and welfare data

| Fact | Verified value | Source |
|---|---|---|
| Occupations with shortage in 2024 | 163 out of ~1,200 assessed | Bundesagentur für Arbeit 2025 statement |
| Unfilled healthcare positions | ~46,000 (general practitioners, specialists, nurses, elderly-care) | OECD Economic Surveys: Germany 2025 |
| German unemployment rate, 2026 average | 6.5% | Statista cite, BA data |
| Total employed persons, March 2026 | ~45.52 million | German Federal Statistical Office (Destatis) |
| Specific Ukrainian-refugee challenge | Job-finding rates decreased since 2022 due to limited German language skills | OECD 2025 Survey |
| Welfare structure | Bürgergeld (replaced Hartz IV January 2023) | SGB II |
| Bürgergeld single-adult amount, 2026 | ~€563/month + housing + ancillary | BMAS 2026 announcement |
| Healthcare-shortage Triple Win countries | Bosnia, Philippines, Vietnam, Tunisia, Indonesia, Mexico, India | GIZ / BA Triple Win |
| MBE service points across DE | ~700 | BAMF |
| IQ-Netzwerk regional networks | 16 | netzwerk-iq.de |
| Optionskommunen (autonomous Jobcenter) | 104 | BMAS |

### The reference winners we studied (6 projects)

| Project | License | Funded | Institutional wrapper | Tech domain |
|---|---|---|---|---|
| Tenzu | AGPL-3.0 | Apr 2026, NGI0 Commons | BIRU Scop (French co-op) | Project management web app |
| OpenVoiceOS | Apache-2.0 | Oct 2025, NGI0 Commons | Community / Open Voice Network | Voice assistant |
| CityBikes / pybikes | AGPL-3.0 | Jun 2024, NGI0 Commons | 10-year community | Bike-share data API |
| dweb-search | AGPL-3.0 | NGI0 Discovery | ipfs-search organisation | Decentralised search |
| QLever Similarity | Apache-2.0 | Mar 2026, NGI0 Commons | University of Freiburg (academic lab) | Graph database |
| **Redwax** | **Apache-2.0 + CLA** | NGI0 PET + NGI0 Commons + Server Modernisation (multi-grant arc) | **The Commons Conservancy** | PKI infrastructure |

### The Commons Conservancy

| Fact | Verified value | Source |
|---|---|---|
| Legal form | Dutch stichting (foundation) | Commons Conservancy site |
| Founded | 3 October 2016 | Commons Conservancy site |
| Founders / origin | NLnet + NRENs | Commons Conservancy site |
| Cost to join | Free | Commons Conservancy site |
| MoU with NLnet | Yes — automatic thematic fund creation on entry | Commons Conservancy site |
| Notable Programmes | FileSender, eduVPN, Redwax, Internet of Coins, SimpleSAMLphp | Commons Conservancy site |
| Mission | Multi-tenant legal infrastructure for free/open software | Commons Conservancy mission statement |
| Required of new Programmes | Sign the Pledge (Code of Conduct based on IEEE ethics) | "How to set up a new Programme" |

### Reference rates for European civic-tech work

| Item | Verified value | Source |
|---|---|---|
| EU civic-tech contractor hourly rate (mid-range) | €50 – €70 per hour | Industry benchmark, multi-source |
| Senior FOSS contributor / lead engineer rate | €70 – €120 per hour | Industry benchmark |
| German civic-tech permanent rate (employee) | €45,000 – €70,000 annual gross | Glassdoor, kununu |
| Beratungsstelle advisor hourly cost (loaded) | ~€45 / hour | German NGO budget benchmarks |
| Professional translator (advisor-client setting) | €60 – €120 / hour | German market benchmark |

---

## Part B — Strategic decisions log

Each decision is dated. Each can be reopened — but reopening means changing the docs and reissuing the decision, not informally drifting.

### 2026-05-17 — Initial decisions captured during planning sessions

#### Decision 1: License — Apache 2.0 + Contributor License Agreement

**Decided**: 2026-05-17.

**Earlier proposal**: AGPL-3.0. **Revised after**: Redwax research; recognition that 5 of 6 reference projects with infrastructure framing use Apache 2.0 or AGPL with CLA-equivalent pattern; the project's primary positioning is *infrastructure* (the MCP server as composition surface), not *end-user application*.

**Reasoning**:
- Apache 2.0 maximises institutional adoption — many corporate/public-sector environments forbid AGPL
- Aligns with the cost-saving doctrine (government and NGO deployment is core)
- The CLA preserves the project's ability to relicense or dual-license later if needed (matching Redwax's pattern)
- Apache 2.0 is OSI-recognised, NGI0-acceptable
- Pattern across cohort: infrastructure → Apache; end-user app → AGPL

**Owner of this decision**: maintainer (with input from this planning session).

**Reversibility**: harder once code is published. Initial commit should be Apache 2.0 from the start.

#### Decision 2: Institutional wrapper — apply to The Commons Conservancy

**Decided**: 2026-05-17.

**Reasoning**:
- Free, multi-tenant legal-entity wrapper for the project
- NLnet co-founded it and has an explicit MoU with it
- Matches Redwax's model (Redwax is itself a Commons Conservancy Programme)
- Solves the single-author / no-legal-entity blocker
- EU-anchored, which strengthens the application's European-dimension claim

**Scope**: apply during Week 2 of the execution plan. See `02-execution-plan.md` §2.

#### Decision 3: TU Berlin academic affiliation — deferred to optional background task

**Decided**: 2026-05-17.

**Reasoning**:
- TU Berlin would be additive but is a third-party dependency we do not control
- Cold emails to faculty in May can sit unread for weeks
- The Commons Conservancy route is independently sufficient
- One single-shot email is a 1-hour task with low downside and possible upside; commit to that and no more

**Scope**: one email by end of Week 1, no follow-up unless replied to. See `11-institutional-outreach.md` Template G.

#### Decision 4: Positioning — EU-wide commons, Germany-first reference deployment

**Decided**: 2026-05-17.

**Earlier framing**: "German-first, EU-exportable."

**Reasoning**:
- EU-wide aligns with NGI's mission and NLnet's strategic-relevance criterion
- Removes a structural ceiling on the project
- Germany remains the first concrete deployment context because that is where the maintainer is and where realistic partner pilots exist
- The architecture is country-neutral; localisation is a translation exercise, not an engineering pivot

#### Decision 5: Anchor persona model — multi-persona panel of five

**Decided**: 2026-05-17.

**Earlier proposal**: single anchor persona "Aïcha, Tunisian nurse."

**Reasoning**:
- A single persona reads as tokenism
- A panel proves the system serves a category of human situations, not a demographic
- The panel doubles as a design forcing function (RTL languages, regulated professions, EU vs non-EU work rights, refugee-status nuances)
- Real anonymised testers can replace fictional ones over time

**Composition**: Aïcha (Tunisia / Nurse / Anerkennung), Yusuf (Turkey / Engineer / EU Blue Card), Olga (Ukraine / Tech / §24 protection), Mahmoud (Syria / Trade / subsidiary protection), Maria (Romania / Care / EU citizen with language barrier). See `07-personas.md`.

#### Decision 6: Language strategy — EN + DE shipped, others on post-grant roadmap

**Decided**: 2026-05-17.

**Reasoning**:
- Core functionality must be 100% reliable in 2 languages before adding more (maintainer position, accepted)
- Adding RTL languages (Arabic) requires UI work beyond translation
- A translator contributor pathway is documented as a Week 3 task; new languages land as native-speaker contributors arrive
- The post-grant roadmap names: Arabic, Ukrainian/Russian, Turkish, Romanian (mapped to the persona panel)

#### Decision 7: Cost-saving doctrine — adopt as project-level design principle

**Decided**: 2026-05-17.

**Reasoning**: every feature evaluated against "reduce institutional operational cost while improving end-user outcomes." Reframes the pitch from charity to value-creation; directly addresses what budget-holders need; matches the political incentives of public-sector adopters. Documented in `08-cost-saving-doctrine.md`.

#### Decision 8: AI Act compliance — build in as a project-level deliverable

**Decided**: 2026-05-17.

**Reasoning**:
- Enforcement date is 2 August 2026 — within the project's funding window
- Most commercial competitors are not compliant; this is a durable moat
- Every institutional adopter inherits a compliant configuration, lowering their adoption friction
- Cost: ~3–4 days of documentation + UI work + audit logging integration; payoff is the single largest cost-saving mechanism the project offers

Documented in `10-ai-act-compliance.md`.

#### Decision 9: Institutional integration — pitch readiness, not adoption

**Decided**: 2026-05-17.

**Reasoning**:
- Real Jobcenter / BA / federal-level adoption cycles are 18–36 months — outside any reasonable grant window
- Reviewers familiar with German public-sector procurement will see through "will be adopted by BA in 2027" as naive
- The honest claim is: designed for institutional adoption, standards-anchored (ESCO, EURES schema, schema.org, MCP), AI-Act-compliant by design, with realistic Phase 1 pilots at Beratungsstellen / Optionskommunen / university career services
- One letter of support from one of those is enough to make the readiness claim concrete

#### Decision 10: Grant ask — frugal default, max only if scope justifies

**Decided**: 2026-05-17.

**Reasoning**: do not exaggerate. Ask for the budget the milestones require. Be defensible on the budget breakdown. Default ask sits at €30–€40k; only justify €50k if the milestone work clearly prices that high after detailed breakdown.

#### Decision 11: Housing-agent integration — pursue Option B (real integration) by default

**Decided**: 2026-05-17.

**Reasoning**:
- The maintainer has a personal contact (a friend) who built the housing agent
- Real integration is the strongest possible proof of the MCP-composition claim
- Falls back to Option A (mock stub) only if the friend cannot collaborate
- Collaboration message drafted in Week 1; integration shipped in Week 2

See `11-institutional-outreach.md` Template F.

#### Decision 12: Repository sanitisation — do not rewrite history; replace forward, document the residue

**Decided**: 2026-05-17.

**Reasoning**:
- Rewriting git history loses signed commits and breaks any existing checkouts/forks
- The audit identified internal residue (`khalo.org`, tester names, "sellable-readiness" docs) — sanitise the *current state* in Week 1, document the early history honestly in `CONTRIBUTORS-NOTE.md`
- Winners (Tenzu) are honest about early-stage instability — we mirror that honesty rather than pretending to be polished from day one

#### Decision 13: Maintainer time commitment — 18 hours/day available, with sustainability caveat

**Captured**: 2026-05-17.

**Note**: maintainer commits to 18 hours/day across the 4-week window. Plan calibrates for this generous availability — scope can be ambitious. Sustainability flag: hours 15–18 are marginally less productive; protect sleep and break time. Output quality > input hours.

#### Decision 14: `keepbuildingtill100%tracker.MD` — delete, do not preserve

**Decided**: 2026-05-17.

**Reasoning**: maintainer position — content may contradict current direction, causes confusion. Execute deletion in Week 1 sanitisation.

#### Decision 15: Co-maintainer recruitment — delegate to the maintainer's partner

**Decided**: 2026-05-17.

**Reasoning**: maintainer's partner takes on the bureaucratic/community-organising work. We do not plan or research this from the technical side; we integrate the partner's outcome when ready.

---

## Part C — Open research questions

These are not yet decided. Listed so a future agent or planning session can prioritise them.

### Open R1: Verify the next NLnet Commons Fund deadline that aligns with the 4-week window

- Call 13 deadline was 1 June 2026; call 14 estimated 1 August 2026 from cadence
- Maintainer said "4 weeks from 2026-05-17" implies a submission target around mid-June, which falls *after* the 1 June 2026 deadline of call 13
- **Action**: verify call 14 deadline by visiting NLnet directly when planning execution. If it is later than mid-June, the schedule has more buffer. If it is mid-June exactly, the plan compresses by 2 weeks.

### Open R2: Are there NGI0-funded employment/migration/civic-jobs projects already?

- Initial search did not surface any
- Important for positioning: if there are, we differentiate; if there are not, we explain the gap
- **Action**: dedicated half-day research pass through the NGI0 funded-projects index when execution starts

### Open R3: NLnet application form exact questions

- The application form is short and standard but its exact questions shape Week 4 application drafting
- **Action**: visit the NLnet apply page directly during Week 3 to capture the form structure before drafting

### Open R4: Letter-of-support contact names

- Templates are ready; specific named contacts at MBE / IQ-Netzwerk / university offices not yet identified
- **Action**: Week 1 — maintainer or a research-helper identifies one named contact per top-ranked partner

### Open R5: Pre-existing FOSS / civic-tech for migrants in Germany

- Handbook Germany, Migration_lab, Welcome.app — what does the existing landscape look like? Differentiation requires knowing
- **Action**: half-day research pass during Week 1

### Open R6: TU Berlin specific contact

- Generic departments listed in `11-institutional-outreach.md`; specific professor/office not yet chosen
- **Action**: maintainer chooses one based on personal knowledge / web search; sends one email by end of Week 1

### Open R7: WCAG 2.2 AA conformance precise scope

- Committed to as a grant deliverable; precise scope (which user flows, which conformance criteria) needs definition
- **Action**: Week 3 — define audit scope, select criteria, possibly engage HAN University accessibility support (an NLnet-provided service)

### Open R8: Hosting cost for the public demo deployment

- Demo deployment in Week 3 needs a stable URL (`demo.<domain>` or similar)
- **Action**: Week 2 — maintainer picks hosting provider, secures domain, sets up cert + monitoring

### Open R9: ESCO mapping data — extract from authoritative source

- ESCO is open data; the relevant download formats and licensing must be confirmed before integration
- **Action**: Week 2 — verify ESCO data licensing (Creative Commons), download the dataset, map at least 30 high-value occupations to start

### Open R10: Budget per-milestone breakdown

- Decided to be frugal-by-default, max €50k if justified; exact per-milestone breakdown unfinalised
- **Action**: Week 4 — when application is drafted, exact breakdown emerges from the milestone deliverables; document in `12-application-package.md`

---

## How to update this document

- **New verified fact**: add to Part A with source citation
- **New strategic decision**: add to Part B with date, reasoning, and reversibility note
- **New open question**: add to Part C with required action

Append entries; do not delete (decisions can be reopened, but the original is preserved).
