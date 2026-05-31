# Helpmefindthejob — Project Brief

**Last updated**: 2026-05-24 (v2 revision)
**Status**: pre-submission, planning phase complete, execution in progress
**Working branch**: `claude/project-analysis-bpHCo`

This is the strategic source-of-truth document. Read end-to-end before working on anything. If anything else in the workspace contradicts this document, this document wins — and the contradiction is a bug to fix.

### v2 changes since the 2026-05-17 v1 (this revision)

- **§7 anchor persona panel** extended from five personas to **seven** per Decision 21 in `04-research-and-decisions.md`. The five most-acute migrant personas (Aïcha, Yusuf, Olga, Mahmoud, Maria) remain the primary narrative anchor; the two wider friction-class personas (Käthe, Tobias) demonstrate the friction-class claim architecturally without diluting the primary narrative.
- **§10 institutional wrapper** reframed: Commons Conservancy admission is positioned as a **parallel long-term governance track**, not as a prerequisite for the NLnet submission. Per WinningPlan.MD v3 (re-verified against primary NLnet + Conservancy sources on 2026-05-23): NLnet's eligibility page explicitly states "no categorical exclusions"; the Conservancy hosts only 20 programmes (vs ~371 NLnet-funded projects); intake is a 12–24-month process. The sustainability story now anchors on what is definitely owned by the project (Apache 2.0 + CLA + full governance pack + 7-pillar SUSTAINABILITY.md + drafted outreach) and mentions the Conservancy as a parallel track rather than the centrepiece.
- **§4 honest current state** rewording follows from the Conservancy reframe — the "single-author signal without institutional wrapper" line is no longer described as a BLOCKER fixed by Conservancy admission. It is a real residual exposure; the Commons Conservancy parallel-track plus the Phase-2 framework-extraction roadmap are the documented mitigations.

Earlier reframes (already in v1):
- Project rename Helpmefindthejob per Decision 22, sanitised in Week 1.
- Friction-class framing per Decision 21 — applies to §1 mission, §2 positioning, §6 cost-saving doctrine, §7 personas.

---

## Table of contents

1. Mission
2. Positioning
3. The funder and the application target
4. Honest current state of the project
5. The eight strategic decisions made in planning
6. The cost-saving doctrine
7. The anchor persona panel
8. Technical positioning and the MCP composition story
9. EU AI Act compliance as the institutional moat
10. The institutional wrapper — Commons Conservancy
11. Differentiation moves (where we exceed the cohort bar)
12. What we are explicitly NOT doing
13. Sources

---

## 1. Mission

Helpmefindthejob exists to **capture specialist HR and bureaucratic-navigation knowledge — currently locked in advisors' heads, HR departments, recruiter networks, and overworked employment-services case workers — and put it directly into the hands of the people who need it most**: anyone facing structural friction between their actual capability and the European labor market's ability to recognise and connect them to work.

The friction is universal across the EU labor markets; its acuity varies by user situation. Migrants and EU-mobile workers face it most acutely — language barriers, foreign-credential opacity through Anerkennung, residency-status complexities, bureaucratic fragmentation — and are the strongest single use case for the project. The same structural friction also affects career changers, workers returning after caregiving or extended absence, the long-term unemployed re-entering the system, returning expats, older workers facing implicit-bias filtering, and first-generation graduates without family-networked guidance through professional conventions. The architecture is friction-driven, not demographic-driven. Per Decision 21 in `04-research-and-decisions.md`, the migrant use case remains the strongest specific evidence and primary narrative anchor; it is not the project's hard-coded identity.

We exist as a **digital commons**: open-source under Apache 2.0, hosted by The Commons Conservancy, multilingual, privacy-preserving, EU AI Act compliant by design, self-hostable by anyone — from an individual at home to a Beratungsstelle to a Jobcenter. No vendor lock-in. No commercial gate. Free for the people who need it most; sustainable through institutional support contracts and the multi-grant arc.

The pattern is the **Redwax model applied to civic life**: small, well-documented, standards-anchored, composable modules combined into larger services. Our first reference implementation is the conversational jobseeker copilot deployed in Germany. The same modules compose with parallel open civic agents — housing, healthcare, residency, education — to form a coherent multi-domain civic assistant. The MCP server is the commons interface. The reference implementations are proof.

---

## 2. Positioning

Helpmefindthejob is **EU-wide civic-employment infrastructure** with Germany as the first reference deployment. The architecture is country-neutral; cross-border deployment is a localisation exercise, not a re-engineering effort.

### The one-sentence positioning

> **Helpmefindthejob is an open-source EU-wide civic employment commons that captures specialist HR and bureaucratic-navigation knowledge into modular, MCP-composable tools — putting agency back into the hands of anyone facing structural labor-market friction, while saving the institutions that serve them measurable operational cost. Migrants and EU-mobile workers are the most acute use case but not the only one.**

### What we are not

- Not a commercial SaaS
- Not a tool restricted to any single demographic — friction-driven, not demographic-driven
- Not LinkedIn for migrants only
- Not a generic GPT wrapper
- Not a closed-source tool with an open-source veneer
- Not a German-only product
- Not a product the user pays for
- Not a product institutions pay per-seat for
- Not vendor-locked to any one AI provider
- Not extracting user data for profiling or training
- Not making any automated decisions about employment without explicit human consent

### What we explicitly are

- Open-source under Apache 2.0 with a Contributor License Agreement
- Hosted as a Programme of The Commons Conservancy (institutional wrapper)
- Multilingual (English + German shipped; Arabic, Ukrainian, Turkish, Romanian on the roadmap)
- Privacy-preserving (encrypted at rest with ChaCha20-Poly1305, BYO-AI provider including fully offline via Ollama, no data egress beyond what the user explicitly consents to)
- EU AI Act compliant by design for the 2 August 2026 enforcement date
- Self-hostable on commodity hardware (Docker + Compose; Nix flake for reproducible builds)
- Standards-anchored (MCP, schema.org JobPosting, ESCO, EURES schema, JSON Schema, WCAG 2.2 AA, RFC 9116, GDPR-aligned)
- MCP-composable with other open civic agents
- Designed for institutional readiness, not requiring institutional adoption to function

---

## 3. The funder and the application target

The primary target is the **NLnet NGI Zero Commons Fund**, a competitive grant programme distributing €21.6 million across 2024–2027 to digital-commons projects with strategic relevance to the Next Generation Internet initiative.

| Fact | Value |
|---|---|
| Grant range | €5,000 – €50,000 first round; up to €500,000 cumulative across multiple rounds |
| Programme period | 2024-01-01 to 2027-06-30 |
| Payment model | Milestone-based, results-only, no progress reports |
| Geographic priority | EU + Horizon-associated countries |
| Open-source requirement | Recognised free/open licence, full source published, all scientific outcomes open access |
| Selection criteria | Technical merits, strategic NGI relevance, value for money |

Our ask: **€37,000 across 6 milestones**, frugal-by-default, sized to actual deliverable costs rather than to the €50k ceiling. The detailed milestone budget is in `12-application-package.md`.

The deadline target is verified at execution start (Open Research Question R1 in `04-research-and-decisions.md`). Calls run on a rolling 2-month cadence; call 13 closed 1 June 2026; call 14 expected ~1 August 2026.

Follow-on grants are anticipated in a multi-grant arc — the Redwax precedent demonstrates this is a known NLnet pattern. Phase 2 work (framework extraction, multi-agent orchestrator, second institutional pilot) is scoped for the next call cycle once Phase 1 milestones are delivered.

---

## 4. Honest current state of the project

Audit summary, May 2026. The unflinching version is documented in earlier planning iterations; this section is the synthesis we work from.

### Deployment state (clarified 2026-05-17)

The project has **never been publicly launched**. A single private-instance deployment runs for one tester — the maintainer's partner — who also serves as the project's HR / bureaucratic-navigation domain expert and named co-maintainer (see Decision 17 in `04-research-and-decisions.md`). There are no paying users, no Stripe subscriptions, no public traffic. Consequence: Week 1 sanitisation and README rewrite are unconstrained one-way operations, not coordinated migrations. R15 in `05-risks-and-stakeholders.md` is downgraded to Low / Low accordingly.

### Strong (commons-quality already)

- Working multi-source job discovery (career-page scanning + federated aggregators + bookmarklet capture)
- Chat-driven UX with a 12-phase journey state machine (`company_discovery/journey.py`)
- Structured conversation with confirmation gates (`company_discovery/chat_router.py`)
- BYO-AI provider abstraction (`company_discovery/ai_providers.py`) — OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter, Ollama, manual handoff, Claude Code
- Encrypted profile-at-rest (ChaCha20-Poly1305)
- CV builder, persona system, skill-gap atlas, application-outcome tracking
- Full EN/DE i18n with German legal pages (Impressum §5 TMG)
- MCP server (`mcp_server.py`) exposing 15 tools with JSON schemas + per-tool versioning
- Solid self-hosting story: Dockerfile, docker-compose.prod.yml, Caddy HTTPS, backup/restore scripts, restore-drill
- 220+ test files / 3,144 tests (i18n parity, journey state machine, persona ranking, encryption-at-rest including the AEAD migration, MCP catalogue input-schema enforcement, locale-aware yes/no parsing, 2FA enrollment, cross-workspace isolation, DuckDuckGo search provider, push transport, and the Playwright E2E entry point). Top-level suite verified 2026-05-29.
- CI runs on Python 3.11 + 3.12

### Missing for grant credibility (these are the Week 1–4 deliverables)

- LICENSE file at repo root (BLOCKER)
- Governance pack: CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, SUPPORT, AUTHORS, ACKNOWLEDGMENTS, TRADEMARK (BLOCKER)
- Proof of MCP composition with a second consumer (BLOCKER)
- Internal residue: `khalo.org` hardcoded ~29× in `app.py`, tester names in commit messages, `keepbuildingtill100%tracker.MD` at root, commercial-narrative `docs/sellable-readiness-*` and `docs/marketing-copy.md` (MAJOR)
- Single-author signal — partially mitigated by the Commons Conservancy parallel-track admission (not gating the NLnet submission per WinningPlan.MD v3) plus the Phase-2 framework-extraction roadmap; remains a real residual exposure named in the "Risks we acknowledge" section of the application draft
- README opens with "self-hosted chat-driven job-hunting copilot" — commercial framing rather than commons (MAJOR — Week 1 rewrite)
- No badges, no public roadmap, no CHANGELOG, no tagged releases (MAJOR)
- CI is tests-only — no lint, no mypy, no coverage upload, no security scan (MAJOR)
- The historical `cryptography` / `cffi` build issue (Linux without pre-built wheels + no rust + build-essential) is closed as of Week 3 task 3.1. Explicit `cryptography>=42.0.0,<50.0.0` pin in `requirements.txt` plus the `fresh-clone-install` CI workflow on `python:3.11-slim` and `python:3.12-slim` verify the install + a representative test slice on every push. Docker remains supported as a fallback for environments lacking pre-built wheel support on their specific platform.
- No documentation site, no translator pathway, no accessibility statement (MAJOR)
- No EU AI Act compliance pack (MAJOR — Week 2 deliverable, the moat)

### OK as it stands (no work needed)

- BYO-AI abstraction is genuinely swappable
- Docker self-hosting is solid
- Backup/restore is documented with restore-drill
- Privacy page exists, encryption is documented
- i18n EN/DE is well-implemented
- 8 MCP tools have JSON schemas (just need formal documentation)

---

## 5. The eight strategic decisions made in planning

Full reasoning in `04-research-and-decisions.md` Part B. Summary below; each is binding unless explicitly reopened with a new dated decision.

| # | Decision | Date | Reversibility |
|---|---|---|---|
| 1 | License: **Apache 2.0 + CLA** | 2026-05-17 | Hard once published |
| 2 | Institutional wrapper: **apply to The Commons Conservancy** | 2026-05-17 | Soft (can withdraw before admission) |
| 3 | TU Berlin: **defer as dependency**, single optional email | 2026-05-17 | Soft |
| 4 | Positioning: **EU-wide commons, Germany-first reference deployment** | 2026-05-17 | Strategic — major change requires re-pitching |
| 5 | Personas: **panel of seven** (five most-acute migrant + two wider friction-class per Decision 21), not single anchor | 2026-05-17 / 2026-05-18 | Soft (real testers replace fictional over time) |
| 6 | Languages: **EN + DE shipped, others post-grant** with translator pathway | 2026-05-17 | Soft (add as native speakers join) |
| 7 | Cost-saving doctrine: **project-level design principle** | 2026-05-17 | Strategic |
| 8 | AI Act compliance: **build in as deliverable** for 2 August 2026 enforcement | 2026-05-17 | Hard — this is the moat |

Additional capture from planning (not strategic-level but operational):
- Housing-agent integration via maintainer's friend (Option B; Option A as fallback)
- Repository sanitisation: do not rewrite history; sanitise current state and document the residue honestly
- Grant ask: €37,000 frugal-by-default
- Maintainer time commitment: 18 h/day available (with sustainability caveat)
- `keepbuildingtill100%tracker.MD`: delete entirely
- Co-maintainer recruitment: delegated to the maintainer's partner

---

## 6. The cost-saving doctrine

Every feature is evaluated against the question: **does it reduce institutional operational cost while improving end-user outcomes?**

Eight built-in cost-saving mechanisms documented in `08-cost-saving-doctrine.md`:

1. **Lower advisor caseload per case served** — agent handles routine queries; advisors focus on complex cases. Migrant subset is the densest concentration of cases per advisor visit; mechanism applies across the friction class (Jobcenter, university career service, Beratungsstelle, MBE)
2. **Shorter time-to-employment** — Bürgergeld avoidance, plausibly significant per case (~€1,000+/month direct + indirect)
3. **Zero per-seat licensing fees** — self-hosted; €15k–€19k/month avoided per Beratungsstelle-scale deployment vs commercial alternatives
4. **No vendor lock-in** — Apache 2.0, open standards, exportable user data
5. **AI Act compliance inherited** — deployers avoid €30–€200k of compliance consulting from 2 August 2026
6. **Reproducible builds via Nix flake** — reduces public-sector IT maintenance burden, addresses EU IT-workforce shortage
7. **Multilingual built in** — eliminates €15k–€30k/year per service point in translator-service costs
8. **Faster Anerkennung pipeline** — months of welfare expense avoided per case

This doctrine is not pitch language; it is a **design principle**. When a feature decision is ambiguous, the cost-saving frame breaks the tie. Features that improve outcomes without reducing cost are deferred or redesigned.

---

## 7. The anchor persona panel

**Seven personas** serve as the design forcing function and the public narrative (v2 expansion per Decision 21). Full profiles in `07-personas.md`.

The **five most-acute migrant personas** remain the **primary narrative anchor** — every public-facing demo, screenshot, and proposal section names one of them first. They are the strongest specific evidence the system serves the friction class.

| # | Persona | Origin | Profession | Status | German | Solves |
|---|---|---|---|---|---|---|
| 1 | Aïcha | Tunisia | Registered nurse | §16d Anerkennung | B1→B2 | Recognition-friendly employer matching + clinical-German CV |
| 2 | Yusuf | Turkey | Mechanical engineer | EU Blue Card pending | A2 | Post-arrival timeline + cross-city role comparison |
| 3 | Olga | Ukraine | Senior frontend dev | §24 protection | A2 | English-team / remote tech matching + residence-status explainer |
| 4 | Mahmoud | Syria | Trade-apprentice | Subsidiärer Schutz | B2 (trades) | Ausbildung aggregation + Handwerk-format CV |
| 5 | Maria | Romania | Care worker | EU citizen | A2 | Language-barrier-friendly Pflegedienst matching |

The **two wider friction-class personas** demonstrate the architecture is friction-driven, not demographic-driven. They appear in the persona panel diagrams + the seven-persona Playwright suite + the bias-comparative-report data; they do not displace the migrant five from the proposal narrative.

| # | Persona | Origin | Profession | Status | German | Solves |
|---|---|---|---|---|---|---|
| 6 | Käthe | Germany | Registered nurse returning after caregiving gap | EU citizen | Native | 12-year-CV-gap reframing + 2026-format CV scaffolding + Wiedereinstiegsprogramme matching |
| 7 | Tobias | Germany | Career changer, long-term unemployed | EU citizen | Native | Evidence-of-ROI cover-letter framing for non-linear careers + roles whose JD language signals openness |

Every public-facing artifact references at least one of the five primary-anchor personas concretely; the two wider personas appear in any context where the friction-class architectural claim must be visibly substantiated. The panel proves the system serves a *category* of human situations, not a single demographic. Real anonymised testers replace fictional ones over time.

---

## 8. Technical positioning and the MCP composition story

The technical contribution is **the architecture, not the application**.

Four distinguishing design choices:

1. **Structured, gated conversation** — 12-phase deterministic journey state machine, every AI invocation constrained to a phase, every database write user-confirmed. Auditable, debuggable, safe. Directly aligned with AI Act human-oversight and transparency obligations.

2. **User-sovereign data and AI** — encrypted at rest (ChaCha20-Poly1305), BYO-AI provider abstraction (including Ollama for fully-offline mode), no data egress beyond explicit consent.

3. **MCP-exposed as open civic infrastructure** — the Model Context Protocol server is the commons interface. Versioned tool catalogue with JSON Schemas, documented composition pattern (sequential handoff, profile-shared, orchestrated). Other open civic agents — housing, healthcare, residency, education — compose with Helpmefindthejob without forking. Full spec in `09-mcp-composition.md`.

4. **Multilingual and locale-aware by design** — EN + DE shipped; translator-contributor pathway documented; locale rules baked in (German yes/no synonyms, Impressum, city aliases).

The MCP composition story is **proven in Week 2** with a concrete reference integration with the maintainer's friend's housing agent. This is non-negotiable. The central pitch claim must be verifiable by a reviewer reading the repo for 5 minutes.

---

## 9. EU AI Act compliance as the institutional moat

Helpmefindthejob is squarely **high-risk AI under EU AI Act Annex III §4(a) and §4(b)** — employment-related AI. Obligations are enforceable from **2 August 2026**.

We build in compliance by design — risk management plan, data governance documentation, technical documentation aligned with Annex IV, audit logging, transparency notices, human-oversight UI, accuracy + bias testing. The full compliance pack is documented in `10-ai-act-compliance.md`.

The institutional consequence: **every institution deploying our agent inherits a compliant configuration**. They avoid the €30–€200k of external consulting otherwise needed to bring an employment-AI deployment into AI Act compliance. This is the single largest cost-saving mechanism in the project and the most durable moat against commercial competitors who are still scrambling.

---

## 10. The institutional wrapper — Commons Conservancy (parallel track)

Helpmefindthejob has applied (intake submitted) for admission as a Programme of **The Commons Conservancy** (Dutch stichting, founded 2016 by NLnet, multi-tenant legal-entity wrapper for open-source projects, free). **Admission is a parallel long-term governance track — NOT a prerequisite for the NLnet submission.** Per WinningPlan.MD v3 (re-verified against primary sources on 2026-05-23): NLnet's eligibility page explicitly states "no categorical exclusions"; only one of the 44 projects funded in the February 2026 NGI0 Commons round was an existing Conservancy programme; the Conservancy hosts only 20 programmes (vs ~371 NLnet-funded projects across 9 rounds); intake is a 12–24-month bespoke-DRACC-statutes process not designed for grant-routing speed. The sustainability story is therefore anchored on what is definitively owned by the project today (Apache 2.0 + CLA + governance pack + 7-pillar SUSTAINABILITY.md + drafted institutional outreach + multi-grant arc) and mentions the Conservancy intake as parallel evidence of long-term governance commitment.

What this solves:

- **Single-author sustainability blocker** — the project gains an institutional legal home regardless of any single contributor's availability
- **No-FOSS-track-record gap** — Commons Conservancy admission is itself a credibility signal recognised by NLnet (NLnet co-founded it)
- **Donation / funding pipeline** — Commons Conservancy Programmes can receive tax-deductible donations
- **Governance scaffolding** — IEEE-ethics-based Code of Conduct, standard organisational artifacts
- **EU-anchored institutional credibility** — strengthens the European-dimension claim

Application target: **Week 2 of execution**. Cost: free. Requirements: signed Pledge, alignment with the Commons Conservancy mission, agreement to free/open-software principles. See `02-execution-plan.md` §2.

---

## 11. Differentiation moves (where we exceed the cohort bar)

The six reference winners we studied (Tenzu, OpenVoiceOS, CityBikes, dweb-search, QLever, Redwax) have specific gaps. We close those gaps and visibly exceed the cohort bar with these moves:

| Move | Effort | What no winner ships |
|---|---|---|
| Public quarterly ROADMAP.md linked from README | 3 h | Nearly none have one |
| OpenSSF Scorecard workflow + badge | 2 h | Zero of 6 |
| Cosign-signed releases with CycloneDX SBOM | 3 h | Zero of 6 |
| RFC 9116 `/.well-known/security.txt` | 1 h | Zero of 6 |
| ARCHITECTURE.md with Mermaid system diagram | 4 h | Zero of 6 |
| Explicit ACCESSIBILITY.md with WCAG 2.2 AA, audit date | 2 h | Only Tenzu commits, in NLnet abstract not repo |
| SUSTAINABILITY.md with post-grant business model | 3 h | Almost none |
| Reproducible build via Nix flake | 6 h | Zero of 6 |
| Decisions log (`04-research-and-decisions.md` pattern) | already done | Zero of 6 |
| EU AI Act compliance pack | 3–4 days | Zero of 6 (and most need this) |

Total differentiation effort: ~25–30 hours. The first eight close the gap to "competitive"; the AI Act compliance pack and the published-decision-log move us above any of the six winners in the cohort.

---

## 12. What we are explicitly NOT doing in the 4-week window

- ❌ Adding product features
- ❌ Refactoring code into a separate framework library (Phase 2 work)
- ❌ Building or publishing the housing agent code as a major scope item — the integration is a small, focused deliverable; the housing agent itself is the friend's project
- ❌ Adding a third language without a committed native-speaker contributor
- ❌ Pretending to have community we don't have (fake Discord, etc.)
- ❌ Polishing artifacts to look finished — winners are honest about instability
- ❌ Registering a Verein / legal entity (Commons Conservancy is the wrapper)
- ❌ Pursuing other grant programs in parallel (focus all bandwidth on NLnet first)
- ❌ Federal-Jobcenter / BA / EURES integration claims (Phase 3 work; pitched as readiness only)
- ❌ Promising central-BA adoption (NLnet reviewers know German public sector)

---

## 13. Sources

### NLnet / NGI0
- NGI Zero Commons Fund: https://nlnet.nl/commonsfund/
- Guide for Applicants: https://nlnet.nl/commonsfund/guideforapplicants/
- Eligibility: https://nlnet.nl/commonsfund/eligibility/
- Support services: https://nlnet.nl/NGI0/services/
- Recent selections: https://nlnet.nl/news/2026/20260409-announce-commons-fund.html

### The Commons Conservancy
- https://commonsconservancy.org/
- Mission statement: https://commonsconservancy.org/dracc/0001/
- How to set up a Programme: https://commonsconservancy.org/how/

### Reference winners studied
- Tenzu: https://nlnet.nl/project/Tenzu/
- OpenVoiceOS: https://nlnet.nl/project/OpenVoiceOS/
- CityBikes: https://nlnet.nl/project/CityBikes/
- dweb-search: https://nlnet.nl/project/dweb-search/
- QLever Similarity: https://nlnet.nl/project/QLever-similarity/
- Redwax: https://nlnet.nl/project/Redwax-PKI/ and https://commonsconservancy.org/programmes/redwax/

### Standards we cite or implement
- MCP: https://modelcontextprotocol.io
- schema.org JobPosting: https://schema.org/JobPosting
- ESCO: https://esco.ec.europa.eu/
- EURES: https://eures.europa.eu/
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- RFC 9116 (security.txt): https://www.rfc-editor.org/rfc/rfc9116
- EU AI Act: https://eur-lex.europa.eu/eli/reg/2024/1689/oj

### German labor market context
- Bundesagentur für Arbeit shortage occupations: https://www.arbeitsagentur.de/en/press/2025-25-qualified-skilled-workers-urgently-required-shortages-in-163-occupations
- OECD Economic Surveys: Germany 2025: https://www.oecd.org/en/publications/2025/06/oecd-economic-surveys-germany-2025_b395dc9b.html
- Anerkennung-in-Deutschland: https://www.anerkennung-in-deutschland.de/
- IQ-Netzwerk: https://www.netzwerk-iq.de/

---

## Change log

- **2026-05-17**: comprehensive rewrite reflecting all planning decisions, Redwax research findings, EU AI Act enforcement timing verification, Bundesagentur für Arbeit labor-shortage primary-source data, and the cost-saving doctrine adoption. Replaces the earlier version that was based on the initial planning iteration.
