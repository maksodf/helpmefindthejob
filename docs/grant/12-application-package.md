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

- **Project name**: DirectJob Scout
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
> **DirectJob Scout** is an open-source, multilingual, privacy-preserving civic employment agent that captures specialist HR and bureaucratic-navigation knowledge into a small, well-documented set of modular tools exposed through the Model Context Protocol (MCP). The first reference implementation is a conversational jobseeker copilot deployed in Germany; the same modules compose with parallel open civic agents (housing, healthcare, residency) to form a coherent multi-domain civic assistant. The codebase is Apache-2.0-licensed, self-hostable, encrypted at rest, runs on the user's choice of AI provider — including fully offline via Ollama — and ships AI Act compliance built in for the 2 August 2026 enforcement date.
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

DirectJob Scout addresses this gap as a digital commons. The technical and institutional design is deliberate and unusual; six choices distinguish it from every commercial and open-source alternative we have surveyed.

**Structured, gated conversation, not GPT-wrapper roulette.** A 12-phase deterministic journey state machine drives the user from discovery to drafted application. Every AI invocation is constrained to a specific phase with a specific output shape. Every database write is confirmed by the user. Every missing parameter triggers multi-turn elicitation. The agent is auditable, debuggable, and safe — properties no freeform LLM job-chatbot can offer, and properties directly required by the EU AI Act's transparency and human-oversight obligations.

**User-sovereign data and AI.** The user's CV, profile, and history are encrypted at rest with ChaCha20-Poly1305 and never leave the self-hosted instance. AI inference is bring-your-own-provider — OpenAI, Anthropic, Gemini, DeepSeek, Ollama (fully offline), or manual handoff for users with no AI subscription. The architectural choice removes the structural dependency on commercial AI that disqualifies most users in the target community.

**MCP-exposed as open civic infrastructure.** The agent exposes its capabilities through a Model Context Protocol server with a versioned tool catalogue, JSON Schema-defined inputs and outputs, and a documented composition pattern. Any other open civic agent — including a separately developed open-source housing-search agent operated by a partner team — can compose with DirectJob Scout inside a single conversation or as a sequential handoff. Healthcare, residency-permit, Anerkennung, and integration-course agents can attach later without forking. The MCP server is the commons interface; the modular composition pattern is the Redwax model applied to civic agents.

**Multilingual and locale-aware by design.** English and German shipped at first release with locale-aware parsing (yes/no synonyms, German bureaucratic context, RTL-readiness). Arabic, Ukrainian, Turkish, and Romanian on the post-grant roadmap with explicit translator-contributor pathways.

**AI Act compliance built in.** The project ships with a Data Protection Impact Assessment template, a transparency notice for users, a human-oversight UI for institutional deployers, audit logging compatible with Article 12 requirements, an explainability layer, and technical documentation aligned with Annex IV. Every institution deploying the agent inherits a compliant configuration, dramatically reducing the typical €30–€200k consulting cost of bringing a high-risk AI system into AI Act compliance from 2 August 2026.

**Cost-saving doctrine as project-level principle.** Every feature is evaluated against the question: does it reduce institutional operational cost while improving end-user outcomes? Eight concrete cost-saving mechanisms are built into the design: lower advisor caseload, shorter time-to-employment (Bürgergeld avoidance), zero per-seat licensing, no vendor lock-in, AI Act compliance inheritance, reproducible builds via Nix flake, multilingual without separate translation budget, and faster Anerkennung pipeline.

The reference implementation deploys in Germany first because that is where the founding maintainer is and where realistic partner pilots exist. The architecture is EU-wide from day one. Standards alignment — schema.org JobPosting, ESCO occupations and skills, EURES schema export, MCP, JSON Schema, WCAG 2.2 AA, RFC 9116 — makes cross-border deployment a localisation exercise, not a re-engineering one.

---

## E. Milestones and budget

Milestone-based payment, results-only, no progress reports — per NLnet's standard model. Each milestone is a verifiable deliverable; payment requested upon delivery.

### Milestone 1: Legal and narrative foundations

**Deliverable**: Apache 2.0 LICENSE file at repo root, Contributor License Agreement, full governance pack (CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, SUPPORT.md, AUTHORS.md, ACKNOWLEDGMENTS.md, TRADEMARK.md), `.well-known/security.txt` per RFC 9116, GitHub repository housekeeping (description, topics, Discussions enabled), zero `khalo.org` or other internal residue in code, README rewritten with civic-commons positioning.

**Cost-saving mechanism**: provides the institutional-readiness signal that deployers require to even consider adoption; eliminates the licensing-ambiguity blocker that prevents public-sector procurement engagement.

**Budget**: €4,000.

### Milestone 2: MCP composition reference

**Deliverable**: published MCP server documentation with versioned tool catalogue and JSON Schema for all 13 tools; one concrete reference integration with a parallel open civic agent (housing); cross-linked repositories; CI integration test demonstrating MCP composition; STANDARDS.md citing every standard implemented (MCP, schema.org JobPosting, ESCO, EURES schema, JSON Schema 2020-12, ISO 8601, ISO 639-1, RFC 7807, RFC 9116).

**Cost-saving mechanism**: every additional civic agent built on top of this MCP surface reuses our composition layer, avoiding duplicated engineering cost across the civic-tech ecosystem.

**Budget**: €8,000.

### Milestone 3: EU AI Act compliance pack

**Deliverable**: complete `/compliance/` directory shipping: risk management plan (Article 9), data governance documentation (Article 10), technical documentation aligned with Annex IV (Article 11), audit-log infrastructure with documented schema (Article 12), transparency notice for users and deployer operating manual (Article 13), human-oversight UI and guide (Article 14), accuracy and bias testing methodology with reproducible results (Article 15), pre-filled templates for EU AI database registration (Article 49) and Fundamental Rights Impact Assessment (Article 27).

**Cost-saving mechanism**: institutions deploying the agent inherit a compliant configuration, avoiding the €30–€200k of external consulting otherwise required to bring an employment-AI deployment into AI Act compliance for 2 August 2026.

**Budget**: €10,000.

### Milestone 4: Public demo deployment and accessibility

**Deliverable**: live public demo at stable URL (`demo.<domain>`) running the canonical reference implementation, with persona-panel pre-seeded examples covering all seven personas (Aïcha, Yusuf, Olga, Mahmoud, Maria — the five most-acute migrant cases — plus Käthe and Tobias — the two wider-friction-class cases — per Decision 21); WCAG 2.2 Level AA accessibility audit completed with results published in ACCESSIBILITY.md; documentation site (mkdocs-material) deployed at `docs.<domain>` covering architecture, deployment, MCP API, contributing.

**Cost-saving mechanism**: reduces the discovery and evaluation cost for any potential institutional adopter; the demo replaces the need for sales calls or vendor presentations entirely.

**Budget**: €6,000.

### Milestone 5: Reproducible builds and quality signalling

**Deliverable**: Nix flake (`flake.nix`) at repo root producing a reproducible build; comprehensive CI matrix with linting (ruff), type checking (mypy), test coverage upload (Codecov), CVE scanning (pip-audit), dependency automation (Renovate), codespell, locale-parity check; OpenSSF Scorecard workflow and badge; cosign-signed v0.1.0 release with CycloneDX SBOM attached.

**Cost-saving mechanism**: reproducible builds and automated supply-chain signals reduce per-deployment maintenance burden, directly addressing the EU public-sector IT-workforce shortage; signed releases with SBOM eliminate one entire category of compliance work for institutional adopters.

**Budget**: €5,000.

### Milestone 6: Institutional readiness and standards interop

**Deliverable**: at minimum one letter of support from a credible institutional partner (MBE service point, IQ-Netzwerk regional office, university career service, or Optionskommune Jobcenter) included in the application; ESCO taxonomy integration for skill and occupation mapping in user profiles; EURES schema export endpoint; admission as a Programme of The Commons Conservancy completed; documented FOSDEM 2027 talk submission plan.

**Cost-saving mechanism**: the institutional wrapper plus standards alignment opens the door to institutional adoption channels without per-deployment custom integration work; FOSDEM presence multiplies the ecosystem awareness of the project at near-zero direct cost.

**Budget**: €4,000.

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

- Tag a `v0.2.0` release reflecting all work
- Archive the submitted application text in `docs/grant/submitted-application-<date>.md`
- Continue housing-agent collaboration if not yet complete
- Continue NGO outreach (additional letters of support strengthen any future application)
- Begin Phase 2 scoping per `03-post-grant.md`
