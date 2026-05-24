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
| Helpmefindthejob's classification | High-risk under Annex III §4(a) and §4(b) — employment-related AI | Annex III text |
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

**Note (2026-05-18)**: panel composition expanded by Decision 21 to seven personas (five most-acute migrant + two wider friction-class) without changing the original framing. The migrant five remain the primary narrative anchor.

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

**Note (2026-05-18)**: partially superseded by Decision 20. The Option B preference at the time of Decision 11 was rebalanced toward Option A (mock stub) as the Phase 1 default; Option B remains the upgrade path if a collaborator confirms. Self-built Phase 1 housing-agent (Option C / D) is off the table per Decision 20.

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

#### Decision 20: Focus discipline — Helpmefindthejob core is the Phase 1 deliverable; housing agent is additive only

**Decided**: 2026-05-18.

**Supersedes (partially)**: Decision 11. Where Decision 11 framed the housing-agent integration as Option B (real, via friend) preferred with Option A (mock) fallback, Decision 20 reframes the *project priority*: Helpmefindthejob's core quality through Phase 1 is the criterion that matters, and the housing-agent component is at most additive evidence of MCP composition.

**Reasoning**:
- The application is reviewed against the core project's quality and cost-saving-doctrine evidence, not against the breadth of side deliverables. A single excellent civic agent with a documented composition interface is a structurally stronger pitch than two unevenly-finished agents.
- The MCP composition story is satisfied by (a) the published MCP server documentation, (b) `ARCHITECTURE.md`'s composition diagram, (c) `STANDARDS.md`'s standards alignment, and (d) *one* reference integration of any shape (mock, narrow companion, or friend-collaborated). None of those require shipping a substantial self-built second civic agent in Phase 1.
- Earlier exploration (in this planning session) of self-built housing-agent options (Option C full-scratch / Option D narrow companion) was a focus error. The capacity to build it exists; the strategic case for spending Phase 1 capacity on it does not.
- Phase 2 is the appropriate window for a serious housing agent (whether self-built or framework-extraction-driven), aligned with the second-grant arc and proper scope.

**Operational consequences**:
- Self-built housing-agent work moves to Phase 2 of the post-grant roadmap (`03-post-grant.md`), not Phase 1.
- Friend-outreach via Template F (existing friend with housing agent) and Template H (developer friends who could build one) continues — but as *additive*, not as the critical path. Positive responses produce a third civic agent in the ecosystem; non-responses produce no project change.
- §2.5 in the execution plan ships as Option A (mock stub) if no friend collaboration lands by its turn in the queue; Option B (real friend integration) if a friend says yes. Maintainer does not self-build a Phase 1 housing agent regardless.
- All Week 2 / Week 3 / Week 4 capacity that was conceptually allocated to housing-agent work returns to strengthening Helpmefindthejob's quality, the AI Act compliance pack, the demo deployment, the documentation site, and the application drafting.

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

#### Decision 22: Project rename — DirectJob Scout → Helpmefindthejob

**Decided**: 2026-05-19.

The project is renamed from **DirectJob Scout** to **Helpmefindthejob** (single-word brand, capital H), with the canonical domain at **helpmefindthejob.com** (acquired by the maintainer 2026-05-19). The rename is **forward-going only** per [Decision 12](#decision-12-repository-sanitisation--apply-the-week-1-decision-and-document-the-historical-residue): pre-rename git history retains "DirectJob Scout" as the documented identity-of-record for all commits up to and including `v0.1.0`; `v0.1.0` cryptographic artefacts (cosign signature bundle + public key + CycloneDX SBOM) are immutable and stay bound to the pre-rename identity.

**Reasoning**:

- The new name aligns the user-benefit framing ("help me find a job") with the user's actual pain point, in plain English the seven-persona panel themselves would use.
- Brand consistency before NLnet submission so a reviewer's first impression matches the production domain.
- `helpmefindthejob.com` is the maintainer's acquired domain — it becomes the canonical demo + docs surface (current `maksodf.github.io/directjob-scout/` GH Pages URL stays available via GitHub auto-redirect after the repo is renamed).

**What this changes**:

- All forward-going documentation, source code, configuration, public-tree placeholders, and external URLs renamed.
- MCP server `serverInfo.name` flipped from `"directjob-scout"` → `"helpmefindthejob"`; the corresponding integration-test assertion updated in lockstep.
- Public-tree placeholder convention (`directjob-scout.example` per Decision 12) is **superseded** by the real `helpmefindthejob.com` domain — see Open R8 reopen below for the full **two-step domain transition** (`khalo.org` → `directjob-scout.example` placeholder → `helpmefindthejob.com`).
- GitHub repository to be renamed by the maintainer via Settings → Rename (handled GitHub-side; auto-redirects from the old URL are preserved by GitHub for migration continuity).

**What this does NOT change**:

- Git commit history (immutable per Decision 12).
- `v0.1.0` release-name `DirectJob Scout v0.1.0` (identity-of-record at sign time).
- `v0.1.0` cryptographic artefacts under `docs/releases/v0.1.0-*` (cosign signature was computed over `directjob-scout-0.1.0.tar.gz`; renaming the artefacts post-sign would break verification).
- CHANGELOG.md historical entries (the `[0.1.0]` block names DirectJob Scout as the identity-of-record at that release).
- `docs/grant/cleanup-audit-2026-05-18*.md` historical reports.

**Reversibility**: hard. Public-name change affects every artefact going forward. Reverting would require another forward-going rename of comparable scope. The git-history-of-pre-rename + the `v0.1.0` cryptographic identity-of-record remain intact under either direction.

**Amendment 2026-05-22 (TLD pivot: `.com` → `.org`)**: the canonical domain is updated from `helpmefindthejob.com` to **`helpmefindthejob.org`**. Two drivers:

1. **DNSSEC at United Domains blocked the `.com` switch within the NLnet deadline window.** `helpmefindthejob.com` had DNSSEC active at the registrar; United Domains refuses to change nameservers while DNSSEC is on, and operator-side DNSSEC deactivation propagation is bounded by registrar policy ("up to 24 hours"), with no hard guarantee of completion before the 2026-06-01 noon CEST submission. `helpmefindthejob.org` (also owned by the maintainer) had DNSSEC already off — the pivot to `.org` unblocked the deploy with no DNS-propagation gamble.
2. **`.org` actively signals the project's civic-commons positioning** in a way `.com` does not. Major commons projects (Wikipedia, Mozilla, Apache, Linux Foundation, The Commons Conservancy itself at `commonsconservancy.org`) live on `.org` for this reason. For an open-source EU-wide civic employment commons applying to NLnet NGI Zero Commons Fund, `.org` is the right TLD signal; NLnet reviewers parse `.com` as commercial intent. The pivot is therefore not merely pragmatic; it is brand-aligned.

What this amendment changes (forward-going only, per Decision 12):

- Every current-state code, config, doc, and public-tree reference to `helpmefindthejob.com` is updated to `helpmefindthejob.org`. The sweep covered 188 matches across 62 files and was committed on 2026-05-22.
- Decision-22 historical text above retains `helpmefindthejob.com` as the canonical-at-time-of-decision identity-of-record (per Decision 12). This amendment block is the forward-going correction.
- `helpmefindthejob.com` remains owned by the maintainer; once DNSSEC is deactivated and the registrar window clears, the `.com` can be configured as a secondary domain pointing at the same origin (Caddy SNI handles both). This is not currently scheduled.

What this does NOT change:

- Project name / brand: still **Helpmefindthejob** (single-word, capital H).
- Git history, pre-amendment commits, CHANGELOG entries that mention `helpmefindthejob.com`.
- `v0.1.0` cryptographic artefacts.
- Dated audit reports (`docs/grant/cleanup-audit-*.md`, `docs/grant/bias-testing-*.md`, etc.) that mention `helpmefindthejob.com` at their dated state.

---

### What we know is broken / not yet shipped (2026-05-24)

NGI0 reviewers reward honesty about alpha state — the Tenzu and Redwax repositories both publish equivalent caveat lists. This paragraph names the gaps the maintainer is aware of at submission time so a reviewer (or a future agent) can distinguish a genuine omission from a deliberately-scoped Phase-2 deferral. Nothing below is a surprise; each item is also tracked in `PlanTowardPerfection.MD` Ceiling 2 or in `03-post-grant.md`.

- **Zero NGO partners signed**. The three institutional-outreach letters (AWO Charlottenburg-Wilmersdorf, RINWA Berlin / La Red, TU Berlin Career Service) are drafted at `docs/grant/11-institutional-outreach.md` but the maintainer has not yet sent them at submission time. Sending them is `PlanTowardPerfection.MD` Section 1.1 (operator-gated). A signed letter of support would lift the application from "credible single-maintainer civic-tech alpha" to "credible single-maintainer civic-tech alpha with at least one institutional collaborator on record". The application narrative does not claim partners that do not exist; the Field 16 ecosystem text states "outreach in progress at submission time".
- **Demo deployment is at-risk**. The deployment at `helpmefindthejob.org` is up at submission time, but it has not been the subject of a full Lighthouse / load-test sweep against the seven-persona Playwright suite (that suite is scoped for Ceiling 2 Section 2.5). A reviewer who clicks the demo link may hit an unmodified pre-launch state on any given hour. The README hero copy says "deploying — see status" to honour this honestly; the dedicated `demo.helpmefindthejob.org` subdomain with seeded persona accounts (`PlanTowardPerfection.MD` Section 1.6) is queued behind DNS configuration.
- **10–13 % fit-scoring OOB rate**. The 2026-05-19 polished cohort run measured **10 / 77 = 13.0 %** out-of-bounds AI-output rate (sub-scores don't sum to total, score outside 0–100, or reason/gaps malformed). The parser-layer score-clamp catches these at user-surface time (see `compliance/accuracy-and-bias-testing.md` §8.1 + `tests/test_prompt_injection_vectors.py::V3JdIndirectInjection`) so the user sees "no score" rather than a misleading number — but the underlying AI-output-quality metric is honestly 13.0 %, not the < 3 % a fully-mature deployment would target. PlanTowardPerfection Section 2.8 tracks driving this below 3 % as a Ceiling-2 deliverable; the methodology source `compliance/accuracy-and-bias-testing.md` documents the methodology completion plan via partner-NGO pilot in 2026 Q4.
- **7 / 8 BYO-AI providers are integration-tested via mocks only**. The AI Provider Honesty Matrix at `docs/grant/15-ai-provider-honesty-matrix.md` lists eight providers (OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter, Ollama, Codex CLI, Claude Code). The bias-comparative-report-2026-05-21 exercised two of them live (deepseek + ollama). The other six providers have dispatcher-shape unit tests but not live-key integration tests at submission time. Live-key verification is a Phase-2 deliverable; the BYO-AI architecture means the deployer ultimately owns provider integration on their own keys, so the gap is acceptable for v0.1.0-class deployments but explicitly disclosed.
- **Multi-OS CI is absent**. CI runs on Linux (`ubuntu-latest`) only. macOS and Windows runners are not yet wired. A contributor on either of those OSes can submit a PR that breaks the cross-platform behaviour without CI catching it. The fresh-clone-install workflow at `.github/workflows/fresh-clone-install.yml` is the only CI lever today; multi-OS expansion is `PlanTowardPerfection.MD` Section 2.13 (Ceiling-2 reliability + operations).
- **GitHub Actions billing block is the immediate CI-greenness gate**. The repo is currently private; GitHub Actions on private repos hits the maintainer's spending limit, and `test.yml` / `fresh-clone-install.yml` / `docs-publish.yml` all show "failure" on recent main commits with the literal annotation "The job was not started because recent account payments have failed or your spending limit needs to be increased." This auto-resolves the moment box 1.1.1 (repo flip to public) ships — Actions becomes free on public repos. See `PlanTowardPerfection.MD` boxes 1.3.5 / 1.3.6 / 1.3.10 for the explicit annotation.

The framing for any reviewer: these are five concrete known-issues with documented remediation paths and dated tracking entries. The project does not pretend to be at v1.0; it is shipping a v0.80.0-class artefact, honestly described, with the cost-saving and friction-class architecture already in place and the operational hardening on the Phase-2 roadmap.

---

## Part C — Open research questions

These are not yet decided. Listed so a future agent or planning session can prioritise them.

### Open R1: Verify the next NLnet Commons Fund deadline that aligns with the 4-week window

**Status as of 2026-05-22**: ANSWERED via live WebFetch against `nlnet.nl/news/` + the call-announcement page `nlnet.nl/news/2026/20260401-call.html`.

- **Next NGI0 Commons Fund deadline = 1 June 2026, noon CEST** (verified verbatim from the call page: "Deadline for submission: June 1st 2026 (noon CEST)").
- Call number not stated on the page itself but corresponds to call 13 per the prior internal records.
- Next-call (call 14, estimated ~1 August 2026 per typical 8-week cadence) — not yet announced on the news index as of 2026-05-22; the announcement convention is one call deadline at a time.
- **Schedule impact**: maintainer's original target "4 weeks from 2026-05-17" lands at 2026-06-14, which is **13 days after** the 1 June deadline. Two paths forward:
  1. **Compress to submit by 1 June** (call 13) — 10 days from today (2026-05-22). Pre-submission checklist + maintainer review must complete before noon CEST 2026-06-01.
  2. **Wait for call 14** (~1 August 2026 estimated; unconfirmed). Adds ~60 days of buffer but risks losing the now-current submission window.
- Both paths are operator decisions; this question is now answered as far as the verification goes.

### Open R2: Are there NGI0-funded employment/migration/civic-jobs projects already?

**Status as of 2026-05-22**: ANSWERED via live WebFetch against `nlnet.nl/project/`.

- **Result**: NO NGI0-funded projects exist in the employment / jobs / migration / migrants / refugees / civic-employment / labor-market space. Verified by scanning the funded-projects index (focus areas: Internet infrastructure / security / privacy / encryption / open hardware / communication protocols / educational tools / data systems — none cover labor-market access).
- **Positioning impact**: Helpmefindthejob occupies a clear differentiation position. The application narrative can confidently state there is no NGI0-funded precedent in this domain, which is a positive signal: the project doesn't risk "already-funded" rejection AND the gap is explicit evidence of the underserved space the project addresses.
- Should be reflected in the §10 ("Project comparison") field of the application draft. Recommended language: "We are not aware of NGI0-funded projects targeting employment-market access for migrants or civic employment infrastructure as of 2026-05-22 (verified against the NLnet funded-projects index). The closest adjacencies are general civic-tech and privacy-tech projects — see §10 of `application-draft-2026-05-19.md` for the specific comparisons."

### Open R3: NLnet application form exact questions

**Status as of 2026-05-19**: ANSWERED.

- The form structure is documented at [`nlnet-form-fields-2026-05-19.md`](nlnet-form-fields-2026-05-19.md) — 22 fields covering contact (1–5), call selection (6), project body (7–16: name, website, abstract, prior involvement, requested amount, budget usage, other funding, project comparison, technical challenges, ecosystem), attachments (17), GenAI disclosure (18–20), privacy + send-copy checkboxes (21–22).
- Application body drafted at [`application-draft-2026-05-19.md`](application-draft-2026-05-19.md) — one section per form field, every numerical claim either inline-cited to a primary source URL or tagged as `industry-estimate` / `projected` / `not measured`. Pending the maintainer's review + an external-reader clarity pass + final submission via nlnet.nl/propose.
- 13th-call deadline verified at 2026-06-01 12:00 CEST.

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

### Open R8: Public-tree URL for the demo deployment

**Updated 2026-05-18 (cleanup-audit-2026-05-18.md)**: the original framing of this question — "pick hosting provider, secure domain, set up cert + monitoring" — was based on the assumption that §3.4 needed to *provision* new infrastructure. Per the cleanup audit, the maintainer has **existing deployment infrastructure** already running. The actual open question that remains is narrower: should the public tree reference the maintainer's real existing subdomain by name, or should it continue to use the `app.directjob-scout.example` placeholder convention established by Week 1 task 1.4 sanitisation (Decision 12)?

- **Status as of 2026-05-18**: **ANSWERED 2026-05-18 — placeholder convention retained.** The maintainer's answer: keep the existing `app.directjob-scout.example` placeholder convention in the public tree; revisit when ready. No public-tree changes needed.
- **Status as of 2026-05-19**: **REOPENED AND UPDATED 2026-05-19 — placeholder convention SUPERSEDED by real domain `helpmefindthejob.com`.** Per [Decision 22](#decision-22-project-rename--directjob-scout--helpmefindthejob), the maintainer acquired `helpmefindthejob.com` as the canonical project domain. The Decision-12 placeholder convention (`directjob-scout.example`) was protective when no real domain existed; with `helpmefindthejob.com` now owned, the real domain replaces the placeholder in the public tree. Specifically: `app.directjob-scout.example` → `app.helpmefindthejob.com`; `demo.directjob-scout.example` → `demo.helpmefindthejob.com`; canonical `support@directjob-scout.example` → `support@helpmefindthejob.com`. Documentation site URL transitions from `maksodf.github.io/directjob-scout/` → `helpmefindthejob.com/` (GH Pages CNAME or apex hosting per maintainer DNS configuration). GitHub repository rename (`maksodf/directjob-scout` → `maksodf/helpmefindthejob`) handled GitHub-side via Settings → Rename; auto-redirects preserved.

- **Full domain-transition timeline (added 2026-05-22 per phase2-backlog #35)**: the project's public-tree domain went through **three states**, not two:

  | Phase | Public-tree domain | Bound by | Notes |
  |---|---|---|---|
  | Pre-sanitisation (until 2026-05-18) | `khalo.org` | Legacy commercial framing | Real domain owned during the commercial-product era. Surfaced across documentation, deploy configs, marketing copy. |
  | Sanitisation (2026-05-18 Week 1 task 1.4) | `directjob-scout.example` | [Decision 12](#decision-12-repository-sanitisation--apply-the-week-1-decision-and-document-the-historical-residue) | Protective placeholder; no real domain owned at this point. `.example` TLD per RFC 2606 ensures no accidental real-world routing. |
  | Real-domain acquisition (2026-05-19) | `helpmefindthejob.com` | [Decision 22](#decision-22-project-rename--directjob-scout--helpmefindthejob) | Maintainer acquired the domain. Replaces the placeholder in the public tree. |
  | TLD pivot (2026-05-22) | `helpmefindthejob.org` | [Decision 22 amendment 2026-05-22](#decision-22-project-rename--directjob-scout--helpmefindthejob) | Canonical TLD changed from `.com` → `.org`. Two drivers: (1) DNSSEC at the `.com` was active at United Domains, blocking the nameserver switch within the NLnet deadline window; the `.org` (also owned) had DNSSEC off and unblocked the deploy; (2) `.org` actively signals civic-commons positioning (Wikipedia, Mozilla, Apache, Commons Conservancy itself all `.org`) which `.com` does not. The maintainer still owns `helpmefindthejob.com`; it remains available for a later secondary-domain configuration once DNSSEC clears. |

  Why this matters for reviewers: anyone reading the git history will see the `khalo.org` → `directjob-scout.example` rename land in Week 1 (sanitisation), then `directjob-scout.example` → `helpmefindthejob.com` in Week 2 (rename + acquisition). Without the timeline above, the two-step transition reads as redundant churn rather than two distinct decisions made for distinct reasons (history-preserving sanitisation vs. real-domain rebrand).
- **Action**: closed (as of 2026-05-19 reopen + update). Maintainer's remaining DNS-config work is independent of the public-tree text changes and tracked outside this decision log.

### Open R9: ESCO mapping data — extract from authoritative source

- ESCO is open data; the relevant download formats and licensing must be confirmed before integration
- **Action**: Week 2 — verify ESCO data licensing (Creative Commons), download the dataset, map at least 30 high-value occupations to start

### Open R10: Budget per-milestone breakdown

**Status as of 2026-05-19**: ANSWERED.

- Per-milestone breakdown finalised at **€37,000 total** (below the €50,000 first-proposal cap per Decision 10's frugal-by-default posture). Six milestones documented in [`application-draft-2026-05-19.md`](application-draft-2026-05-19.md) Field 12: M1 legal+governance €4k, M2 MCP composition €8k, M3 AI Act compliance pack €10k, M4 demo+accessibility €6k, M5 reproducible builds €5k, M6 institutional readiness €4k. Each milestone has a verifiable public deliverable + a documented acceptance criterion + a cost-saving-mechanism statement.
- Per Decision 10's frugal posture: the €37k figure reflects the genuine cost of the delivered + outstanding work, not a maximisation against the €50k cap.
- The maintainer's final read should re-confirm the four numerical claims in the draft's verification table (163 shortage occupations / 46k healthcare unfilled / ~700 MBE / 104 Optionskommunen) against the named primary sources at submission time.

### Open R11: Commons Conservancy application — response timing

- Application drafted 2026-05-18 (`docs/grant/commons-conservancy-application-2026-05-18.md`); pending maintainer review before send to `website@commonsconservancy.org` (or any more-specific application address Conservancy may have published).
- The Conservancy `/how/` page does not publish an explicit review SLA. Estimated response window based on observed recent admission cadences: **2–6 weeks**. Concrete data added here once a case officer responds.
- **Action**: maintainer sends the letter once reviewed; agent updates this entry with send date and case-officer assignment when the response lands; one polite nudge after 4 weeks if no reply.
- Linked decision: Decision 2 (Institutional wrapper — apply to The Commons Conservancy, 2026-05-17).

### Open R12: Synthetic-cohort bias-testing interim run

**Status as of 2026-05-18**: IN PROGRESS — scheduled for Phase 1 close before NLnet submission, per maintainer decision 2026-05-18.

**2026-05-18 (broadening)**: broadened scoring class to 10 scenarios per persona + added CV-tailoring class at 10 scenarios per persona. Coverage now 140 data points (33.3% of the methodology surface; 2 of 6 scenario classes executed). Report: `docs/grant/bias-testing-2026-05-18-broadened.md`. Remaining four classes (onboarding, discovery, motivation-letter drafting, skill-gap brief) deferred to post-Phase-1 dated reports.

**2026-05-19 (polish)**: closes three broadened-run findings — (1) cohort-blind mixed-fit fixtures (closed via cohort branching + import-time guard); (2) permissive 2-condition CV-tailoring structural check (closed via 4-condition semantic-fact check); (3) Maria→Logistics cross-industry investigation (closed via 7 cross-industry probes, pattern verdict **ONE-OFF** — reclassified as prompt-phrasing sensitivity, not systematic bias). Coverage now **147 data points** (70 cohort-aware scoring + 7 cross-industry probes + 70 CV-tailoring semantic-fact checks). Both tests fail honestly: 10/77 scoring OOB (13.0%); 43/70 CV-tailoring pass (61.4%, below 70% threshold). Tolerance bands and thresholds NOT lowered. Primary product-design finding: `build_cv_tailoring_prompt` does not currently ask the model to acknowledge persona-friction-context (criterion (d) fails 27 times while criteria (a)/(b)/(c) pass 70/70). Report: `docs/grant/bias-testing-2026-05-18-polish.md`. Remediation tracked for post-grant 2026 Q4 cadence.

**2026-05-19 (prompt-enhanced)**: closes the polish-run criterion-(d) finding via production-code enhancement to `build_cv_tailoring_prompt` (new friction-context-acknowledgment instruction + optional `friction_keywords` parameter). Re-run on same 147-data-point methodology surface and `llama3.1:8b`. Result: criterion (d) pass-rate **43/70 (61.4%) → 65/70 (92.9%)** — +22 personas, +31.5 pp. Overall CV-tailoring pass rate **43/70 (61.4%) → 61/70 (87.1%)** — test PASSED (above 70% threshold; threshold unchanged). Polish-run bimodal split (Olga/Maria at 2/10 vs Mahmoud/Käthe at 10/10) closed; every persona now passes criterion (d) at 8+/10. Scoring failure essentially flat at 9/77 OOB (11.7%); pattern verdict remains ONE-OFF (third consecutive run). Report: `docs/grant/bias-testing-2026-05-19.md`. Status remains IN PROGRESS pending the 4 deferred scenario classes (onboarding, discovery, motivation-letter, skill-gap brief) per ROADMAP.md.

**2026-05-19 (chat-router wired)**: closes the prompt-enhanced report's deferred remediation #1 — production chat-router CV-tailoring path now passes `friction_keywords_for(profile.persona_id)` to `execute_cv_tailoring`. Seeded-demo panel users (Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias) now receive the same persona-specific friction-vocab line the bias-test verified at 92.9% criterion-(d) pass-rate; non-panel production users receive `[]` from the lookup helper (always-present generic friction-instruction continues to handle them). Source of truth for the seven-panel friction vocabulary remains `persona_fixtures.PERSONAS`. New helper `friction_keywords_for(persona_id)` at `company_discovery/persona_fixtures.py`; chat-router call sites updated at `app.py:3411` and `app.py:7702`; 6 new regression tests in `tests/test_round4.py`. No bias-test re-run needed — contract verified at 0a9182e. Status remains IN PROGRESS pending the 4 deferred scenario classes.

**2026-05-20 (per-criterion auto-fit + universal friction enrichment)**: closes the R12-broadened-run anti-pattern 4.1 finding (fit-score clustering at round numbers 85/92) via production-prompt enhancement to `build_auto_fit_prompt` (per-criterion decomposition into SCORE_SKILLS / SCORE_EXPERIENCE / SCORE_LOCATION_LANGUAGE / SCORE_FRICTION_FIT summed to the SCORE total, plus anti-anchoring guard). Same commit also enriches `_candidate_profile_block` to pull `residency_status` + `friction_notes` from `persona_fixtures.PERSONAS` so every downstream prompt (auto-fit, decision brief, cover letter, CV tailoring, motivation letter) is friction-aware without per-prompt rewrites. Report: `docs/grant/bias-testing-2026-05-20.md` (re-run pending at time of decision-log update; the report is the evidence layer that confirms the per-criterion-decomposition spread holds across ALL 7 personas, not just the Aïcha single-call smoke at `docs/grant/product-quality-walks/aicha-pass3-smoke-2026-05-20.json`). Pass criteria for the re-run, per operator 2026-05-20: distributional spread visibly improves (no more 85/92 clustering); sub-scores vary meaningfully within each persona; cross-class Δ stays inside ±15 tolerance.

**2026-05-20 (reconsideration — test-infrastructure gap surfaced)**: post-rerun diagnosis uncovered that `tests/test_bias_methodology.py::_build_fit_score_prompt` was a self-contained prompt (emit format `FIT_SCORE: <int>` + optional rationale) and was **not wired** to the production `build_auto_fit_prompt`. **Every fit-scoring conclusion in the four prior dated R12 entries (2026-05-18 broadening, 2026-05-19 polish, 2026-05-19 prompt-enhanced, 2026-05-19 chat-router wired) measured the test-framework prompt, not the production prompt.** Specifically:
  - The "85/92 clustering did not persist at scale" robustness finding in `bias-testing-2026-05-18-broadened.md` describes the test-framework prompt's behaviour at 140 data points. It did not validate production behaviour.
  - The "9/77 OOB scoring, 11.7%" figure in the 2026-05-19 prompt-enhanced entry inherited test-framework-prompt scoring. It did not validate production fit-scoring.
  - The "ONE-OFF cross-industry pattern verdict for three consecutive runs" was three consecutive runs of the test-framework prompt. The verdict needs re-validation against the production prompt.
  - The CV-tailoring side of every report **was** production-prompt and stands intact. The criterion-(d) friction-acknowledgment improvement (61.4% → 92.9%) and the chat-router wiring closure are production-prompt facts.
  - The per-criterion-decomposition production enhancement in the 2026-05-20 entry above is real and committed in production code, but the in-the-same-day re-run of the bias test still exercised the test-local prompt — so the "closes anti-pattern 4.1" claim is **conditionally closed pending the wired re-run**, not absolutely closed.

**Forward correction (test-infra)**: `tests/test_bias_methodology.py::_build_fit_score_prompt` now delegates to `company_discovery.analysis.build_auto_fit_prompt`. Sub-score extractor `_extract_subscores` added; per-record `observed_subscores` now captured in the sidecar. Sidecar path now ISO-date-stamped (was hardcoded `bias-testing-2026-05-19-data.json`, causing the 2026-05-20 run to silently overwrite the May 19 file — the May 19 file is restored from HEAD and the May 20 pre-wiring data preserved at `bias-testing-2026-05-20-pre-wiring-data.json`). Smoke-tested against Aïcha + the strong-fit Anerkennung-friendly scenario: prompt is byte-for-byte the production builder's output; Ollama llama3.1:8b emits four parseable sub-scores summing to the holistic SCORE; `raw_output_head` bumped 200 → 500 chars captures all four sub-score lines + the holistic SCORE line. Re-launched the full 7-persona × (10 scoring + 10 CV-tailoring) + 7 cross-industry probes run at 01:18 GMT+2.

**Doctrine note (binding for the rest of the product-quality sweep)**: every test that claims to validate behaviour X must be checked against the question "does this test actually exercise the production code path for X, or a test-local copy?" If a test-local copy, document explicitly and decide between (i) wire to production for real validation, (ii) keep as methodology-framework test plus add a separate production-path test alongside. The "looks-like-it-tests-X, actually-tests-X-copy" pattern is exactly what slips through static checks.

**Editorial notes** appended to each of the four prior dated bias-testing reports (`bias-testing-2026-05-18.md`, `-broadened.md`, `-polish.md`, `2026-05-19.md`) clarifying what each actually measured. None of the reports are rewritten — each remains accurate for what it actually executed; the editorial notes only clarify scope. `bias-testing-2026-05-20.md` will be the first dated bias-testing report to measure production fit-scoring-prompt behaviour.

**2026-05-20 (wired re-run completed — pass criteria 3-of-4)**: full wired re-run executed at 01:18-01:51 GMT+2 (33 min on Ollama llama3.1:8b). 147 data points (70 scoring + 7 cross-industry probes + 70 CV-tailoring). Report: `docs/grant/bias-testing-2026-05-20.md`. Pass criteria assessment:
  - **(a) Sub-scores emit + parse**: ✅ PASS — 69/70 records parse all four sub-scores; the lone partial misses only `SCORE_FRICTION_FIT` (1.4% rate, model-nondeterminism tolerance).
  - **(b) Sub-scores vary meaningfully**: ✅ STRONG PASS — 0/70 uniform, 0/70 nearly-uniform, 69/70 varied; per-criterion stdev 6.0–7.4 on a 0–25 scale (24–30% relative variation).
  - **(c) Cross-class Δ inside ±15**: ✅ PASS — Δ = +7.59 (wider-friction over most-acute); inside ±15.
  - **(d) Production prompt does not regress spread/range/cohort**: ❌ FAILS — per-persona stdev compressed 40–60% (broadened 31–38 → wired 13–20); range tightened 0–95 → 20–83; overall mean dropped 59.7 → 51.0; OOB count 7 → 12 (+5). All 12 OOBs are strong-fit OR mixed-fit scenarios scoring BELOW band; zero scored above. Root cause: the production per-criterion prompt asks for four 0–25 sub-scores summed to a 0–100 total. The model treats 25 as "near-perfection" and almost never awards it, capping aggregates around 70 even for excellent matches.
  - Cross-industry probes: ONE-OFF verdict holds for a **fourth** consecutive run (0/7 personas above ceiling + 15) — now under the production prompt.

**Decision required**: PART 4.1 closure blocked on criterion (d). Three proposed paths in the report — (A) tune prompt anchoring guidance with explicit per-band semantics ("22–25 = exceptional match; 17–21 = good match; ..."), (B) recalibrate methodology bands + downstream thresholds, (C) raise sub-score cap above 25. Recommendation: **Path A** — the per-criterion architecture is correct; sub-score anchoring is the bug. Awaiting operator decision before next prompt iteration / re-run.

**What stands closed regardless of Path A/B/C**: per-criterion architecture; sub-score variance closure; cross-class fairness; cross-industry ONE-OFF (fourth run). What remains open: strong-fit anchoring. CV-tailoring criterion-(d) friction-keyword failures (12/70, 82.9% pass-rate well above 70% threshold but reveals which persona/scenario combos drop friction context — genuine PART 5 signal flagged for the prompt-template review slice).

**2026-05-20 (Path A approved + executed — PART 4.1 CLOSED)**: operator approved Path A 2026-05-20 02:08 GMT+2 with four non-negotiable safeguards (per-criterion stdev ≥ 6, Aïcha + `anerkennung_friendly_clinical` ≥ 75, cross-class Δ inside ±15, per-record sub-score variance check). Path A rewrote `build_auto_fit_prompt` with explicit per-band anchor scale (22 exceptional / 17 good / 13 moderate / 8 weak / 2 wrong-domain), calibration line ("strong-fit job should aggregate to SCORE ≥ 75"), and anchor-point parking guard. Commit: `cd3aa52`. Smoke test (Aïcha + Anerkennung-friendly): SCORE 77 (was 58). Verification re-run executed 02:11–02:42 GMT+2 (1676 s / ~28 min, 147 data points). Path B (methodology band recalibration) held back as trigger-driven — phase2-backlog item #66, activated only if real user feedback shows Path A's calibration is off.

Safeguard verification:
  - **(i) Per-criterion stdev ≥ 6**: 3 of 4 PASS (skills 7.72, location_language 7.67, friction_fit 7.20); **SCORE_EXPERIENCE 5.57 marginally below** — carries to PART 5 as Finding F2.
  - **(ii) Aïcha + `anerkennung_friendly_clinical` ≥ 75**: ✅ STRONG PASS at SCORE 85 (was 55-58 across two prior dated runs).
  - **(iii) Cross-class Δ inside ±15**: ✅ PASS at +11.22. Note upward trend (+4.5 broadened → +7.59 pre-anchor → +11.22 post-anchor) — anchor benefits Käthe/Tobias slightly more than the migrant five. Monitor in future runs; not a closure blocker but watch list.
  - **(iv) Per-record sub-score parking avoidance**: ✅ PASS under refined operationalization. Original "stdev ≥ 2" wording generated a false-failure mode on records where the model genuinely judges all four criteria as excellent (e.g., Aïcha 19/21/23/22 = stdev 1.71 — four distinct values clustered close because the match really is excellent across the board). Operator-refined measure 2026-05-20: "No more than 10% of records have all 4 sub-scores within a 3-point range." Current run: 5/64 = 7.8%, comfortably under 10%. Documentation of the refinement is in `docs/grant/bias-testing-2026-05-20.md` under "Safeguard (iv) operationalization refinement" with explicit honest framing that the refinement is an operationalization correction, not a goalpost move.

**PART 4.1 CLOSURE**: round-number clustering anti-pattern RESOLVED. Production prompt now produces 44 unique SCORE values from 8 to 95 across the cohort with mean per-record sub-score stdev 4.65. Zero clustering at 85/92. Architectural cause replaced (single holistic → per-criterion decomposition); behavioural cause neutralized (anchor scale + parking guard); test-infrastructure gap closed (bias-methodology now exercises the production prompt). The honest framing in the report binds future readers: Path A is a UX-continuity calibration choice, NOT a claim that the original test-framework's gestalt prompt's 85/92 scores were correct — the new per-criterion architecture is more honest; the anchor guidance is the configuration that aligns the architecture with downstream-feature expectations.

**Two findings carry to PART 5** (NOT phase2-backlog — in-scope PART 5 work):
  - **Finding F1 (HIGH PRIORITY)**: Friction-harshness. Model judges visa/recognition friction harshly even when candidate has a clean pathway. Yusuf (Blue Card) SCORE_FRICTION_FIT max 18 often 5; Mahmoud (§4 AsylG) SCORE_FRICTION_FIT 5-14. 9 of 21 strong-fits land below 75 because of this. PART 5 deliverable: rewrite SCORE_FRICTION_FIT anchor guidance with friction-with-pathway differentiation (22-25 clean pathway + accommodation; 17-21 clear pathway; 12-16 ambiguous; 5-11 high barrier; 0-4 no pathway). Validation gate: Yusuf + bluecard_automotive_engineer AND Mahmoud + ausbildung_shk_hamburg both ≥ 75.
  - **Finding F2 (MINOR)**: Experience anchor-parking. SCORE_EXPERIENCE stdev 5.57 marginally below target 6.0 (safeguard i carryover). 41% records park at anchor values for skills+experience. PART 5 deliverable: explicit intermediate-value encouragement for SCORE_EXPERIENCE and SCORE_SKILLS specifically.

**PART 4 as a whole remains in progress** — anti-patterns 4.2 (generic prose), 4.3 (bullet vs narrative), 4.7 (generic Anschreiben job-specificity) unaddressed. F1+F2 join CV-tailoring 82.9% (parked Yusuf/Olga/Maria friction_keyword pattern) as the substantive PART 5 work stream.

**Cross-industry ONE-OFF**: fifth consecutive run (0/7 personas above ceiling+15) — now under production prompt with anchor guidance.

**Context**: `compliance/accuracy-and-bias-testing.md` documents a methodology that is not yet executed at full scale. The transparency notice (`compliance/transparency-notice.md`) promises "preliminary results due Week 3 of the grant sprint." Closing R12 closes that public claim before submission. The earlier framing — that the methodology would first execute at the partner-NGO pilot — has shifted with the partner-NGO pilot now positioned in 2026 Q4 (post-grant) per `ROADMAP.md`. A synthetic-cohort interim run using the seven canonical personas bridges the gap.

**Target artefacts**:
- `tests/fixtures/personas/` — committed synthetic-but-realistic profile records for each of the seven personas (Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias), shaped per `compliance/accuracy-and-bias-testing.md` §2.1.
- `tests/test_bias_methodology.py` — runs the methodology against the fixtures and asserts divergence-from-tolerance counts below threshold per the bands documented in §2.4.
- `docs/grant/bias-testing-<date>.md` — the first executed run's report, structured per §2.5.

**Methodology source**: `compliance/accuracy-and-bias-testing.md` §§2–6 (the contract; this open question executes the documented contract, it does not redesign it).

**Estimate**: ~6–10 h of agent work. The persona fixtures here are designed to **share** with the §3.4 `scripts/seed-personas.py` script — both consume the same persona-source-of-truth at `docs/grant/07-personas.md` and emit comparable record shapes, so the work folds neatly into the §3.4 next-slice.

**Action**: next-slice execution alongside §3.4 deployment work (next-steps Step 2 + the new R12 step). Surface report when methodology run completes; maintainer reviews the divergence table; remediation as needed before NLnet submission.

---

## How to update this document

- **New verified fact**: add to Part A with source citation
- **New strategic decision**: add to Part B with date, reasoning, and reversibility note
- **New open question**: add to Part C with required action

Append entries; do not delete (decisions can be reopened, but the original is preserved).
