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

### Project deployment state (verified 2026-05-17)

| Fact | Verified value | Source |
|---|---|---|
| Public launch status | Never publicly launched | Maintainer attestation, 2026-05-17 |
| Active deployment | Single private instance, one tester (the maintainer's partner) | Maintainer attestation, 2026-05-17 |
| Paying users | Zero | Maintainer attestation, 2026-05-17 |
| Stripe subscriptions | Zero active | Maintainer attestation, 2026-05-17 |
| Public traffic | None | Maintainer attestation, 2026-05-17 |
| Commercial residue scope | One-way removal, no user migration required | Implied by all the above |

This clarification reframes parts of the audit in `01-project-brief.md` §4 and downgrades risk R15 in `05-risks-and-stakeholders.md`. See Decision 17 in Part B for the stakeholder consequences.

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

**Update (2026-05-17, same day)**: superseded in substance by Decision 17 below. The partner is not a recruitment *target* — the partner is already an active contributor. Decision 15 is preserved for history; Decision 17 is the current operating model.

#### Decision 16: WIP product-work — park, do not integrate during the 4-week grant sprint; triage post-submission

**Decided**: 2026-05-17.

**Context**: The `wip/product-work` branch parks substantial in-flight feature work that was developed on `main` in parallel with grant-sprint planning: CV extraction/renderer/tailor modules, LLM cost tracker / pricing / response cache, model router, tool registry/use-router/actions-store, the `company_discovery/tools/` directory, plus probe scripts and development artifacts.

**Decision**:
1. Park the WIP entirely during the 4-week grant sprint. No reintegration during Weeks 1–4.
2. Begin a structured triage session on Week 5 day 1 (the day after grant submission).
3. Apply a four-question gate to each module (strategic alignment, engineering maturity, AI Act compliance, persona impact) before any module merges.
4. Reintegrate by priority: LLM cost layer first (cost-saving doctrine evidence in code), then model router, then CV layer, then tool layer with framework extraction. Each module merges through the hardening gauntlet (CI, lint, type check, coverage, security scan, audit logging, AI Act compliance review) — none ships without it.

**Reasoning**:
- The 4-week sprint is for credibility hardening, not feature integration. NLnet funds existing technical merit made legible; pulling in unstable WIP weakens the application.
- The WIP modules are strategically aligned (especially the LLM cost layer, which is direct cost-saving-doctrine evidence) but are not required for the grant application. They are first-class candidates for Phase 2.
- Premature reintegration risks: cascading test failures, compliance debt, and merging modules built for the deprecated commercial vision rather than the civic-commons positioning.
- The detailed triage process and strategic ranking are documented in `03-post-grant.md` §"WIP reintegration triage."

**Reversibility**: soft. If a specific WIP module is found in Week 2 to be critical to the application (e.g., the LLM cost tracker turns out to produce data we need to substantiate cost-saving claims), it can be individually merged with explicit decision logged here. Default remains: parked.

#### Decision 17: Stakeholder collapse — partner is co-maintainer, sole tester, domain expert, and bureaucratic-coordination lead

**Decided / clarified**: 2026-05-17.

**Reasoning**: The "maintainer's partner" referenced in Decision 15 is the same person who is the maintainer's roommate, the sole current tester of the live private deployment, the project's HR / bureaucratic-navigation domain expert (a credibility pillar of the civic-commons positioning), and the named co-maintainer recruitment target. Several previously-distinct stakeholder slots collapse to one trusted long-term contributor.

This is positive for project coherence — one committed contributor rather than a recruitment pipeline of strangers — but must be acknowledged explicitly so future agents, reviewers, and any institutional partner understand the team structure honestly. Single-author concerns (R2 in `05-risks-and-stakeholders.md`) are partially but not fully mitigated by this clarification: the project has two named contributors from day one, but they are co-resident and not legally independent, so the Commons Conservancy wrapper remains the load-bearing continuity guarantee.

**Operational consequences**:

- `AUTHORS.md` ships with the maintainer's handle plus an explicit Co-maintainer placeholder for the partner; resolution per the consent-first authorship policy (see Decision 18).
- Partner does not block any individual Week 1 work item. Coordination with the partner is the maintainer's side-channel, not the executing agent's.
- The "co-maintainer recruitment" framing in Decision 15 is recast as "formalising the partner's already-existing role" — the recruitment work is documentation, not search.
- Stakeholder S3 in `05-risks-and-stakeholders.md` is refined accordingly.
- R15 (production-deployment leak) is downgraded to Low / Low in `05-risks-and-stakeholders.md` because the deployment has never been public; the partner is the only person ever to have seen it.
- The HR / bureaucratic-navigation domain-expert credential is internal to the project; this strengthens the credibility narrative without requiring an external letter of support on that dimension.

**Reversibility**: Soft. If the partner withdraws from project involvement, the recruitment-pipeline framing of Decision 15 returns to active operating mode.

#### Decision 19: Outreach send timing — defer all institutional outreach to Week 4 start

**Decided**: 2026-05-18.

**Earlier position**: outreach in Week 1 task 1.6 to maximise response-cycle buffer before the Week 4 application submission.

**Revised position**: outreach drafted but **not sent** until end of Week 3 / start of Week 4, after the project artifacts a recipient would inspect are visibly finished (README rewritten, demo deployment live at a stable URL, documentation site live, AI Act compliance pack shipped under `compliance/`, green CI badges in README).

**Reasoning**:

- First impressions are durable. A partner who clicks the README link and sees half-finished work is meaningfully harder to recover than a partner contacted later but seeing finished work. The "honest about instability" doctrine (CLAUDE.md hard rule 6) applies to *narrative*, not to a partner's first read of the README.
- The application must stand on its own without partner letters. Outreach is a strengthening signal, not a requirement. R13 (reviewer expects more institutional partners than we can secure) is already mitigated by the Commons Conservancy admission path and one letter being sufficient.
- Maintainer's 18 h/day commitment makes the Week 2–3 build pace fast enough that the buffer cost is acceptable. The hardening work happens regardless of outreach timing.
- Partner pre-check returned no warm intros; cold-contact response rate is modest regardless of buffer length. Spending 6 h of Week 1 capacity on sends that may not yield is a worse trade than spending 6 h on Week 2 verification work that strengthens the application.
- The three draft messages (AWO Charlottenburg-Wilmersdorf FIM, RINWA Berlin / La Red, TU Berlin Career Service) are saved under `docs/grant/outreach-drafts/` with explicit `STATUS: DRAFTED — NOT YET SENT` headers and last-verified dates, so re-verification before send is a 10-minute task.

**Reversibility**: soft. If during Week 2 or 3 a strong-fit partner spontaneously appears (via the maintainer's network, a community event, or a referral arising from the housing-agent collaboration), opportunistic early outreach is fine — the decision applies to the bulk-send batch, not to warm-intro singletons. Log any opportunistic send as an entry in the `11-institutional-outreach.md` tracker with the same fields as the bulk drafts.

#### Decision 18: Identity-bearing fields ship as explicit placeholders, resolved via dated follow-up commits per the consent-first authorship policy

**Decided**: 2026-05-17.

**Reasoning**: contributor identity is consent-bearing data. The project does not name a contributor in any public file (`AUTHORS.md`, `ACKNOWLEDGMENTS.md`, commit co-author trailers, governance docs) on the basis of a guess about their preference. Where a contributor has not yet explicitly consented to public attribution, the identity-bearing line ships as an explicit placeholder and is resolved in a **separate dated commit** so the consent event is visible in `git log` as its own line item. Convention: commit subject `governance: AUTHORS — add <handle> per consent dated YYYY-MM-DD`.

**Operational consequences**:

- `AUTHORS.md` ships with the maintainer's handle (already public from the repo URL — no consent needed) and an explicit Co-maintainer placeholder line for the partner. Full policy text is embedded in `AUTHORS.md` under "Consent-first authorship policy" so contributors encounter it at the same place as the contributor list.
- `.github/CODEOWNERS` and `.github/FUNDING.yml` follow the same convention; CODEOWNERS lists only the maintainer until co-maintainers consent, FUNDING.yml lists explicit TBD placeholders with a documented resolution trigger.
- The Tenzu and Redwax precedent — both projects evolved their AUTHORS / ACKNOWLEDGMENTS rosters over time as contributors joined and consented — is the cohort pattern this decision matches.

**Reversibility**: Hard (in spirit). Once shipped, the policy is the public norm for the project; rolling it back would damage credibility and would arguably violate the Contributor Covenant's contributor-autonomy stance. Soft (in mechanics): individual placeholder lines are routinely resolved as contributors consent.

#### Decision 20: Focus discipline — DirectJob Scout core is the Phase 1 deliverable; housing agent is additive only

**Decided**: 2026-05-18.

**Supersedes (partially)**: Decision 11. Where Decision 11 framed the housing-agent integration as Option B (real, via friend) preferred with Option A (mock) fallback, Decision 20 reframes the *project priority*: DirectJob Scout's core quality through Phase 1 is the criterion that matters, and the housing-agent component is at most additive evidence of MCP composition.

**Reasoning**:
- The application is reviewed against the core project's quality and cost-saving-doctrine evidence, not against the breadth of side deliverables. A single excellent civic agent with a documented composition interface is a structurally stronger pitch than two unevenly-finished agents.
- The MCP composition story is satisfied by (a) the published MCP server documentation, (b) `ARCHITECTURE.md`'s composition diagram, (c) `STANDARDS.md`'s standards alignment, and (d) *one* reference integration of any shape (mock, narrow companion, or friend-collaborated). None of those require shipping a substantial self-built second civic agent in Phase 1.
- Earlier exploration (in this planning session) of self-built housing-agent options (Option C full-scratch / Option D narrow companion) was a focus error. The capacity to build it exists; the strategic case for spending Phase 1 capacity on it does not.
- Phase 2 is the appropriate window for a serious housing agent (whether self-built or framework-extraction-driven), aligned with the second-grant arc and proper scope.

**Operational consequences**:
- Self-built housing-agent work moves to Phase 2 of the post-grant roadmap (`03-post-grant.md`), not Phase 1.
- Friend-outreach via Template F (existing friend with housing agent) and Template H (developer friends who could build one) continues — but as *additive*, not as the critical path. Positive responses produce a third civic agent in the ecosystem; non-responses produce no project change.
- §2.5 in the execution plan ships as Option A (mock stub) if no friend collaboration lands by its turn in the queue; Option B (real friend integration) if a friend says yes. Maintainer does not self-build a Phase 1 housing agent regardless.
- All Week 2 / Week 3 / Week 4 capacity that was conceptually allocated to housing-agent work returns to strengthening DirectJob Scout's quality, the AI Act compliance pack, the demo deployment, the documentation site, and the application drafting.

**Reversibility**: soft. If, between Phase 1 close and Phase 2 grant, a serious need emerges for a Phase-1-window housing-agent that the friend-collaboration path cannot meet, the decision can be reopened with explicit re-evaluation.

#### Decision 21: Positioning frame — friction-class, not migrant-class

**Decided**: 2026-05-18.

**Earlier framing**: project positioned as primarily / explicitly for migrants and EU-mobile workers.

**Revised framing**: project positioned for *anyone facing structural friction between their capability and the European labor market's ability to recognise and connect them to work*. Migrants and EU-mobile workers are the **most acute** use case — language barriers, foreign-credential opacity, residency complexities make the friction densest there — and remain the strongest specific evidence in proposal narrative and persona-anchored examples. The same friction also affects career changers, returning workers after caregiving, the long-term unemployed, returning expats, older workers, people with employment gaps, first-generation graduates without family-networked guidance, and anyone working outside their familiar bureaucratic context.

**Reasoning**:
- The architecture is friction-driven, not demographic-driven. Nothing in the codebase is migrant-restricted; every feature (Anerkennung paths, multilingual support, German-format CV templates, motivation-letter drafting) is acuity-driven and triggers for users who need it.
- Positioning as migrant-only mis-describes the architecture, narrows institutional adoption (a Jobcenter serves all Bürgergeld recipients; "the migrant tool" deploys for ~30% of caseload while "the employment-friction tool" deploys for all of it), and creates political-category friction in jurisdictions where "migrant tech" is contested.
- The cost-saving doctrine expands materially under the friction-class framing — every cost-saving mechanism applies to a larger addressable population, multiplying the institutional savings claim.
- The friction-class framing strengthens the multi-country EU positioning: migration patterns differ between countries, but bureaucratic friction is universal across the EU labor markets.

**What stays the same**:
- The five-persona panel (Aïcha, Yusuf, Olga, Mahmoud, Maria) remains the most-acute-use-case anchor and the primary narrative device in proposals and demos. The panel widens with two non-migrant personas (Käthe, Tobias) to demonstrate friction-class breadth, but does not remove the existing five.
- German-bureaucratic context (Anerkennung, Bürgergeld, Beratungsstellen, Optionskommunen, MBE / IQ-Netzwerk) stays relevant — it is the bureaucratic terrain that the most acute use case navigates, and the Week 4 institutional outreach to MBE / IQ-Netzwerk / TU Berlin Career Service stays as-is.
- The Anerkennung-friendly employer matching, ESCO mapping, EURES export, encrypted-at-rest, BYO-AI, MCP composition, AI Act compliance — all unchanged.
- The cost-saving doctrine's eight mechanisms are unchanged; only the addressable-population framing widens.

**What changes in documentation**:
- `01-project-brief.md` §1 mission and §2 positioning sentences broaden
- `07-personas.md` adds two non-migrant personas (Käthe, Tobias) and reframes the panel intro
- `08-cost-saving-doctrine.md` opens with the broader addressable-population framing
- `12-application-package.md` abstract and problem statement broaden
- `CLAUDE.md` and `00-START-HERE.md` TL;DR sections reflect the broader frame
- `README.md` opener references both the most-acute persona (Aïcha) and at least one non-migrant friction case to demonstrate breadth

**Reversibility**: hard. The positioning is the public-facing identity; reverting after public deployment would be expensive. This decision is the project's identity going forward.

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

### Open R11: Commons Conservancy application — response timing

- Application drafted 2026-05-18 (`docs/grant/commons-conservancy-application-2026-05-18.md`); pending maintainer review before send to `website@commonsconservancy.org` (or any more-specific application address Conservancy may have published).
- The Conservancy `/how/` page does not publish an explicit review SLA. Estimated response window based on observed recent admission cadences: **2–6 weeks**. Concrete data added here once a case officer responds.
- **Action**: maintainer sends the letter once reviewed; agent updates this entry with send date and case-officer assignment when the response lands; one polite nudge after 4 weeks if no reply.
- Linked decision: Decision 2 (Institutional wrapper — apply to The Commons Conservancy, 2026-05-17).

---

## How to update this document

- **New verified fact**: add to Part A with source citation
- **New strategic decision**: add to Part B with date, reasoning, and reversibility note
- **New open question**: add to Part C with required action

Append entries; do not delete (decisions can be reopened, but the original is preserved).
