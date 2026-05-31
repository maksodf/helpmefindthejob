# Application Package — NLnet NGI Zero Commons Fund

**Status**: working draft of the actual application. Finalised in Week 4 of execution.

This document holds:
1. The submission form sections, mapped to NLnet's known application questions
2. The full draft text for each section
3. The milestone breakdown with deliverables and budget
4. The application checklist for submission day

**Important**: NLnet's exact form layout must be verified against their live portal in Week 3 (Open Research Question R3 in `04-research-and-decisions.md`). This draft is structured against the publicly documented questions and may need light reformatting after that verification.

---

## A. Project metadata

- **Project name**: Helpmefindthejob
- **One-line summary**: An open-source EU-wide civic employment commons that captures specialist HR and bureaucratic-navigation knowledge into modular, MCP-composable tools, putting agency in the hands of anyone facing structural labor-market friction in Europe — migrants and EU-mobile workers most acutely — with first reference deployment in Germany.
- **Project website**: [TBD — set up Week 3 demo deployment]
- **Source repository**: [TBD — final repo URL after Commons Conservancy onboarding]
- **License**: Apache License 2.0 with Contributor License Agreement
- **Lead applicant**: [maintainer name]
- **Country of residence**: Germany (EU member state)
- **Institutional wrapper**: Programme of The Commons Conservancy (application pending)
- **Theme alignment**: NGI Zero Commons Fund — building digital commons for civic life and the next-generation internet

---

## B. Abstract (≈200 words)

> Across the European Union, structural labor shortages coexist with hundreds of thousands of capable people who cannot get hired — blocked not by capability but by structural friction between what they can do and what the labor-market system recognises. The friction is most acute for migrants and EU-mobile workers (language barriers, opaque foreign-credential recognition, residency complexities) but also affects career changers, workers returning after caregiving or extended absence, the long-term unemployed re-entering, and anyone navigating an employment system outside their familiar bureaucratic context.
>
> **Helpmefindthejob** is an open-source, multilingual, privacy-preserving civic employment agent that captures specialist HR and bureaucratic-navigation knowledge into a small, well-documented set of modular tools exposed through the Model Context Protocol (MCP). The first reference implementation is a conversational jobseeker copilot deployed in Germany; the same modules compose with parallel open civic agents (housing, healthcare, residency) to form a coherent multi-domain civic assistant. The codebase is Apache-2.0-licensed, self-hostable, encrypted at rest, runs on the user's choice of AI provider — including fully offline via Ollama — and ships AI Act compliance built in for the 2 August 2026 enforcement date.
>
> The project is hosted as a Programme of The Commons Conservancy. By design, every feature is evaluated against a dual measure: it must improve outcomes for the people served and reduce operational cost for the institutions that serve them.

---

## C. Problem statement (≈400 words)

The EU faces a structural labor-market paradox. The Bundesagentur für Arbeit's Fachkräfteengpassanalyse identifies **163 occupations** currently classified as in shortage (Engpassberufe) out of the ~1,200-occupation Berufsklassifikation framework, with tens of thousands of unfilled healthcare positions documented across multiple authoritative sources (OECD Economic Surveys: Germany 2025; BA labour-market reports). Comparable shortages exist across the EU. In parallel, hundreds of thousands of capable people cannot get hired — blocked not by capability but by structural friction between what they can do and what the labor-market system recognises.

The friction is most acute for migrants and EU-mobile workers — including all EU citizens with limited host-language fluency, Ukrainian refugees under the Temporary Protection Directive (whose job-finding rate has dropped since 2022 specifically due to language barriers, per OECD 2025), Triple Win programme participants (nurses recruited from Tunisia, Philippines, Vietnam, Bosnia), subsidiary-protection holders from Syria seeking Ausbildung placements, and EU-mobile Romanian and Bulgarian workers — and this is the strongest specific evidence of where the friction is densest per user. The same architectural friction also affects non-migrant users in structurally similar ways: a German nurse like our anchor persona Käthe, returning to clinical work after twelve years out for childcare, faces the same CV-reframing, system-reorientation, and credential-currency friction that a foreign-trained nurse faces, in a different surface vocabulary; a German backend developer like Tobias, pivoting from commercial tech to public-sector civic-tech, faces TVöD-aware CV-reframing friction analogous to the credential-translation friction a foreign-trained engineer faces. The architecture is friction-driven, not demographic-driven (see Decision 21 in `04-research-and-decisions.md`).

The blocker is rarely capability. The blocker is friction. Bureaucratic systems run in a language the user does not speak. Foreign credentials require Anerkennung through processes that vary by Bundesland and profession. Application formats and CV conventions differ from those the user has learned. The job market is fragmented across platforms (LinkedIn, Indeed, Bundesagentur's JOBBÖRSE, sector-specific portals) — each requires its own account, profile, and learning curve. Each platform extracts personal data and locks the user in.

Existing solutions fail in three specific ways. **LinkedIn-class platforms** are walled gardens that exclude anyone outside their commercial model and harvest personal data as the price of access. **Public-employment-service tooling** (Bundesagentur für Arbeit, EURES) is bureaucratic, host-language-only, and offers no AI-assisted personalisation. **The emerging wave of GPT-wrapper job assistants** is unstructured, unauditable, vendor-locked to a few commercial AI providers, and indifferent to the civic dimension — and most are not compliant with the EU AI Act's high-risk-AI obligations applicable from 2 August 2026.

None of these alternatives is a commons. None works for the people who need them most.

Meanwhile, the institutions that serve users facing this friction — **Migrationsberatungsstellen (MBE) operated nationwide by the six Wohlfahrtsverbände (Caritas, Diakonie, AWO, Paritätischer, DRK, ZWST) under BAMF coordination and located via the BAMF-NAvI directory**; IQ-Netzwerk's 16 regional networks (one per Bundesland); **the autonomous Optionskommunen Jobcenter operating Bürgergeld under §6a SGB II + Article 91e Grundgesetz** (the federal cap is 25% of the 2010 baseline of task carriers — historically a maximum of 110 Optionskommunen; the BMAS-published list is the source of truth for the current active count); and university career services (international graduates plus first-generation graduates and career changers) — operate under acute capacity constraints. Advisor time is the bottleneck. Translation services are expensive. AI tooling that could help is gated behind commercial pricing or compliance risk most institutions cannot absorb.

The opportunity is to build the missing layer: an open-source, multilingual, privacy-preserving civic employment agent that is **both** usable directly by users facing structural labor-market friction **and** deployable by the institutions that serve them — reducing institutional operational cost while improving end-user outcomes, simultaneously.

---

## D. Proposed contribution (≈500 words)

Helpmefindthejob addresses this gap as a digital commons. The technical and institutional design is deliberate and unusual; six choices distinguish it from every commercial and open-source alternative we have surveyed.

**Structured, gated conversation, not GPT-wrapper roulette.** A 12-phase deterministic journey state machine drives the user from discovery to drafted application. Every AI invocation is constrained to a specific phase with a specific output shape. Every database write is confirmed by the user. Every missing parameter triggers multi-turn elicitation. The agent is auditable, debuggable, and safe — properties no freeform LLM job-chatbot can offer, and properties directly required by the EU AI Act's transparency and human-oversight obligations.

**User-sovereign data and AI.** The user's CV, profile, and history are encrypted at rest with ChaCha20-Poly1305 and never leave the self-hosted instance. AI inference is bring-your-own-provider — OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter, Ollama (fully offline), or manual handoff for users with no AI subscription. The architectural choice removes the structural dependency on commercial AI that disqualifies most users in the target community.

**MCP-exposed as open civic infrastructure.** The agent exposes its capabilities through a Model Context Protocol server with a versioned tool catalogue, JSON Schema-defined inputs and outputs, and a documented composition pattern. Any other open civic agent — including a separately developed open-source housing-search agent operated by a partner team — can compose with Helpmefindthejob inside a single conversation or as a sequential handoff. Healthcare, residency-permit, Anerkennung, and integration-course agents can attach later without forking. The MCP server is the commons interface; the modular composition pattern is the Redwax model applied to civic agents.

**Multilingual and locale-aware by design.** English and German shipped at first release with locale-aware parsing (yes/no synonyms, German bureaucratic context, RTL-readiness). Arabic, Ukrainian, Turkish, and Romanian on the post-grant roadmap with explicit translator-contributor pathways.

**AI Act compliance built in.** The project ships with a Data Protection Impact Assessment template, a transparency notice for users, a human-oversight UI for institutional deployers, audit logging compatible with Article 12 requirements, an explainability layer, and technical documentation aligned with Annex IV. Every institution deploying the agent inherits a compliant configuration, dramatically reducing the typical €30–€200k consulting cost of bringing a high-risk AI system into AI Act compliance from 2 August 2026.

**Cost-saving doctrine as project-level principle.** Every feature is evaluated against a testable hypothesis: does it reduce institutional operational cost while improving end-user outcomes? The doctrine documents eight mechanisms (lower advisor caseload, shorter time-to-employment via Bürgergeld avoidance, zero per-seat licensing, no vendor lock-in, AI Act compliance inheritance, reproducible builds via Nix flake, multilingual without separate translation budget, and faster Anerkennung pipeline). The mechanisms are the contract; **measured outcomes are pending the first institutional deployment** — the doctrine is honest design intent, not a measured claim.

The reference implementation deploys in Germany first because that is where the founding maintainer is and where realistic partner pilots exist. The architecture is EU-wide from day one. Standards alignment — schema.org JobPosting, ESCO occupations and skills, EURES schema export, MCP, JSON Schema, WCAG 2.2 AA, RFC 9116 — makes cross-border deployment a localisation exercise, not a re-engineering one.

---

## E. Milestones and budget

Milestone-based payment, results-only, no progress reports — per NLnet's standard model. Each milestone is a verifiable deliverable; payment requested upon delivery. Blended rate €60/hour; €37,000 ≈ 617 developer-hours across a 9-month execution window measured from grant/MoU signature, part-time alongside existing obligations. The kernel already exists (see §A–§D and the public repository); the milestones take it from working prototype to institution-ready, pilot-deployable assistant.

### Milestone 1: Legal, governance, and compliance trust package

**Deliverable**: license / NOTICE / CLA consistency; security-disclosure process (RFC 9116 `security.txt` + SECURITY.md); privacy and support documentation; a Data Processing Agreement template; a documented human-review pathway; and a compliance index tying each artefact to its legal basis.

**Current state**: Apache-2.0 LICENSE, CLA, governance pack, and security.txt already ship; the funded work is verifying, aligning, and packaging the legal/compliance layer for institutional review without external counsel.

**Cost-saving mechanism**: provides the institutional-readiness signal deployers require even to consider adoption; eliminates the licensing-ambiguity blocker that stalls public-sector procurement.

**Budget**: €5,000.

### Milestone 2: MCP composition and agent handoff

**Deliverable**: the Helpmefindthejob-side MCP composition layer — versioned tool catalogue, JSON Schemas for every tool input, an `mcp/discover` capability listing, consent-aware profile and handoff payloads, sequential-handoff tests, and documented MCP-client examples calling Helpmefindthejob employment tools.

**Current state**: a 15-tool stdio JSON-RPC catalogue (SemVer v0.2.0) with JSON-Schema-validated input and a reference housing-agent composition already ship; the funded work is the discovery capability, consent-bound handoff payloads, and the conformance/handoff test surface.

**Cost-saving mechanism**: every additional civic agent built on this MCP surface reuses the composition layer, avoiding duplicated engineering cost across the civic-tech ecosystem.

**Budget**: €8,000.

### Milestone 3: Guided chat workflow and priority commands

**Deliverable**: turn the chat into a guided workflow surface for the highest-value user actions — visible in-chat sub-goals plus the priority commands `/export`, `/scan now`, `/schedule`, `/quota`, `/provider`, `/undo`.

**Current state**: the multi-turn chat router and the 12-phase journey state machine already ship; the funded work is the guided sub-goal surface and the six priority commands wired end-to-end.

**Cost-saving mechanism**: a user who can export data, trigger a scan, manage cadence, check quota, switch provider, and undo mistakes directly from chat needs no advisor hand-holding for routine actions.

**Budget**: €6,000.

### Milestone 4: Employment-friction intelligence and matching quality

**Deliverable**: German-language-requirement warnings, recognition-status checklist, informational §24 / §16d / §18 / Blue-Card work-status flags, credential-equivalence hints, Wiedereinstieg support, long-term-unemployment cover-letter framing, ESCO-lookup improvements, a EURES-compatible export/import shape, friction-aware re-ranking, and fit-scoring regression tests.

**Current state**: the persona system, AI fit-scoring, and a curated ESCO subset ship; the funded work is the friction-class intelligence layer and the matching-quality regression suite.

**Cost-saving mechanism**: users see which jobs are realistically reachable for their language level, documents, recognition status, and work status — reducing repeated advisor explanations.

**Budget**: €7,000.

### Milestone 5: Search quality, accessibility, and persona proof

**Deliverable**: verify the core journeys (sign-up, chat, job brief, CV builder, cover-letter generation, data export) across the seven-persona panel; plus keyboard-only checks, screen-reader review, reduced-motion support, mobile-flow fixes, and accessibility regression tests.

**Current state**: automated axe-core audits (30 violation instances closed) and ACCESSIBILITY.md ship, with manual screen-reader testing deferred; the funded work is the manual screen-reader/keyboard pass and the seven-persona end-to-end journey proof.

**Cost-saving mechanism**: reviewers and pilot partners see evidence the app works for realistic users — reducing discovery and evaluation cost for institutional adopters.

**Budget**: €6,000.

### Milestone 6: Operator readiness and first-pilot package

**Deliverable**: backup/restore verification, basic uptime/error monitoring, audit-log search/export, a simple operator dashboard, a Docker / self-hosting package, a partner onboarding guide, and an impact-report template.

**Current state**: docker-compose, reproducible Nix builds, an HMAC-chained audit log, and cosign-signed releases ship; the funded work is the operator dashboard, monitoring, onboarding guide, and pilot package.

**Cost-saving mechanism**: a pilot partner can deploy, monitor, recover, review actions, and report outcomes without a dedicated DevOps team — the operational readiness an NGO needs to adopt.

**Budget**: €5,000.

### Total budget

**€37,000.**

Below the €50,000 first-round cap. Frugal-by-default per the maintainer's explicit instruction; the budget reflects the genuine cost of the deliverables rather than maximising what the fund permits.

---

## F. Why this project is a commons

- **Licence**: Apache 2.0 + CLA. OSI-recognised. NLnet-acceptable. Compatible with institutional and public-sector adoption.
- **Standards**: every external interface aligns with an open standard or specification. MCP (open protocol), schema.org JobPosting (open vocabulary), ESCO (EU open taxonomy), EURES schema (EU open spec), JSON Schema (open spec), RFC 9116 (IETF spec).
- **Hosting**: source on a public repository, mirrored to Codeberg for European-sovereignty resilience; project home at The Commons Conservancy.
- **Sustainability**: no commercial gate, no vendor lock-in, no per-user fees. Free for individuals, free for NGOs, free for institutions. Optional support contracts for institutional deployers fund maintenance; future grant arc through NLnet's multi-round model, Sovereign Tech Fund, and EU NGI tracks.
- **Governance**: institutional wrapper at The Commons Conservancy; multi-maintainer recruitment in progress; transparent decision log in `docs/grant/`; Contributor Covenant 2.1 Code of Conduct.

---

## G. Risks and mitigations (summary)

The full register is in `05-risks-and-stakeholders.md`. The most material to NLnet reviewers:

- **Single-author sustainability**: mitigated by Commons Conservancy admission and active co-maintainer recruitment.
- **Reviewer skepticism of MCP as commons infrastructure**: mitigated by explicit framing of MCP as JSON-RPC + JSON Schema (mature standards combination) and contribution to multi-vendor MCP ecosystem.
- **MCP composition claim unproven**: mitigated by the housing-agent reference integration shipped as Milestone 2 deliverable.
- **Cost-saving claims as marketing language**: mitigated by explicit tagging of every numerical claim as proven / plausible / aspirational with cited methodology.
- **AI Act compliance correctness**: mitigated by alignment with Annex IV section structure and Article 9–15 obligations with cited reference text; institutions remain responsible for their specific deployment context.

---

## H. NLnet support services we intend to use if funded

(Per the pre-emption principle: explicitly naming the support services signals familiarity with NLnet's process.)

- **Accessibility audit by HAN University**: scheduled within Milestone 4 (WCAG 2.2 AA).
- **Packaging support by NixOS Foundation**: aligned with Milestone 5 (Nix flake delivery).
- **Security audit**: optional; pursued for follow-on Phase 2 grant once the codebase is in Apache-2.0-with-CLA stable form.
- **Mentoring on governance and sustainability**: pursued during the project execution period to inform the Phase 2 application.

---

## I. Submission checklist (final 24 hours)

> The operator-owned items that only the maintainer can close (deadline
> verification, maintainer-identity slots, the release-tag step, demo smoke
> against the real host, compliance-posture decision) are tracked in the
> maintainer's private submission notes.

- [ ] Application form completed end-to-end
- [ ] All NLnet form questions answered with content drawn from sections A–H of this document
- [ ] Repository at submitted URL is publicly accessible
- [ ] LICENSE, CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md present at root
- [ ] README opens with civic-commons positioning
- [ ] At least one badge in README (license at minimum)
- [ ] CI green on `main` branch
- [ ] MCP integration test passing
- [ ] Demo deployment online and reachable
- [ ] Documentation site deployed and reachable
- [ ] Letter of support attached (PDF)
- [ ] Commons Conservancy application submitted (status: pending OR admitted)
- [ ] Anchor persona panel referenced consistently throughout application
- [ ] All numerical claims sourced or tagged as plausible / aspirational
- [ ] AI Act compliance pack visible in `/compliance/`
- [ ] Budget breakdown matches the milestone deliverables
- [ ] Application proposal reviewed by one outside reader (cold read for clarity)
- [ ] Submission confirmation received and archived in `docs/grant/submitted-application-<date>.md`

---

## J. Post-submission immediate actions

- Confirm the `v0.80.0` submission tag (annotated; the release tarball is cosign-signed via CI) sits at the merged HEAD, then continue on SemVer from that anchor (next `v0.81.0`)
- Archive the submitted application text in `docs/grant/submitted-application-<date>.md`
- Continue housing-agent collaboration if not yet complete
- Continue NGO outreach (additional letters of support strengthen any future application)
- Begin Phase 2 scoping per `03-post-grant.md`
