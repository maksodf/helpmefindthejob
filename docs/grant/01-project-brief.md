# DirectJob Scout — NGI0 Grant Project Brief

**Last updated**: 2026-05-17
**Status**: pre-application — Week 0
**Branch**: `claude/project-analysis-bpHCo`

This is the strategic context document. Everything we know, every decision we've made, and why. If you are an agent or contributor picking up this work, read this end-to-end before touching anything.

---

## Table of contents

1. Mission and vision
2. The funder: NLnet NGI Zero Commons Fund
3. Honest current state of the project (May 2026)
4. Research findings: what NGI0 winners actually look like
5. The five strategic problems
6. Strategic decisions made in this session
7. The anchor user persona
8. Where we plan to outshine the winners
9. What we are explicitly NOT doing in these 4 weeks
10. Sources and references

---

## 1. Mission and vision

### The problem

Germany has the largest labor shortage in the EU. Yet hundreds of thousands of qualified people — migrants, refugees, returnees, career-changers, people without German fluency, people with foreign credentials — cannot get hired. The blocker is rarely capability. It is **friction**:

- The system runs in a language they don't speak.
- It expects CVs in a format they've never seen.
- It demands credentials translated and recognized through opaque processes (Anerkennung).
- It scatters openings across dozens of platforms that profile and lock in their data.
- Every "AI job assistant" runs through closed commercial APIs that demand subscriptions the unemployed cannot afford.

Existing solutions fail in three specific ways:

- **LinkedIn-class platforms** are walled gardens that extract data and exclude anyone outside their commercial model.
- **Arbeitsagentur tooling** is bureaucratic, German-only, and provides no AI assistance for tailoring or coaching.
- **GPT-wrapper job assistants** are unstructured, unauditable, vendor-locked, and indifferent to the civic dimension.

None of them are commons. None of them work for the people who need them most.

### The proposed contribution

**DirectJob Scout** — a self-hostable, MCP-exposed civic-employment agent that any individual, NGO, Beratungsstelle, or public agency in Germany (or elsewhere) can deploy, fork, or compose with. Already a working chat-driven system with three independent job-discovery rails (company career pages, federated aggregators, bookmarklet capture), AI-assisted CV tailoring, motivation-letter drafting, skill-gap analysis, and application-outcome tracking, in English and German.

The grant scope hardens it from "working app" into "**reusable digital commons**."

### The technological positioning (what makes this fundable, not just another app)

Four design choices distinguish this from every commercial and open-source job assistant we have surveyed:

1. **Structured, gated conversation, not GPT-wrapper roulette.** A 12-phase deterministic journey state machine drives the user through discover → CV → search → review → tailor → letter → coaching. Every AI invocation is constrained to a specific phase with a specific output shape, every database write is confirmed by the user, every missing parameter triggers multi-turn elicitation. The agent is **auditable, debuggable, and safe** — properties no freeform LLM job-chatbot can offer.

2. **User-sovereign data and AI.** The user's CV, profile, and history are encrypted at rest (ChaCha20-Poly1305) and never leave the self-hosted instance. AI is **bring-your-own-provider** — OpenAI, Anthropic, Gemini, DeepSeek, Ollama (local), or manual handoff for users without any subscription. This removes the structural dependency on commercial AI that disqualifies most users in the target community.

3. **MCP-exposed as open civic infrastructure.** The agent already exposes its capabilities through a Model Context Protocol server. This means any other open civic agent — including a separately developed open-source housing-search agent we operate — can compose with it inside a single conversation. The grant work formalizes this MCP surface as a documented, versioned interface. **The pluggable architecture is what makes the project a commons rather than another app.** Healthcare, residency-permit, Anerkennung, and integration-course agents can attach later without forking.

4. **Multilingual and locale-aware by design.** Full English and German, including German-specific yes/no parsing, German bureaucratic context (Impressum, §5 TMG), locale-aware location matching for city aliases. The grant work adds a third language with the largest migrant-community footprint (target: Arabic or Ukrainian, selected with a community partner).

---

## 2. The funder: NLnet NGI Zero Commons Fund

### What NGI0 actually funds

Not "an app for migrants." NGI0 funds **internet commons** — reusable open-source infrastructure (libraries, protocols, schemas, frameworks, reference implementations) under recognized open licenses, with strategic value to the Next Generation Internet. Explicit preferences:

- **Open source / open standards** — outputs MUST be released under recognized free/open licenses
- **Decentralization, privacy, user sovereignty, accessibility, multilingualism** — core NGI values
- **Technical merit + frugal budgets** — €5k–€50k initial grants, then scale-up on proven delivery
- **Reusable substrate over end-user product** — they fund the protocol, library, or middleware, not the SaaS
- **Concrete deliverables** — code shipped under open license, WCAG-compliant, optional security audit
- **EU/Horizon-associated priority** — given equal proposals

### Eligible activities (NLnet's words)

Security audits, testing/CI setup, documentation, **standardization**, **understanding user requirements / inclusive design**, community/events, packaging, accessibility audits.

### Selection criteria (NLnet's own words)

> *"Projects are judged on their technical merits, strategic relevance to the Next Generation Internet and overall value for money."*

### Funding structure

- **€5k–€50k** initial. Above €50k requires prior completed milestones, WCAG conformance contractually, and a security audit contractually.
- **Up to €500k cumulative** per third party across the fund's lifetime.
- **Milestone-based, results-only payment**: divide the project into milestones with amounts; payment on delivery; no progress reports.

### Why DirectJob Scout fits NGI0's mission

- Open source AGPL-3.0 — meets the license requirement
- MCP-exposed — meets the open-standards / infrastructure requirement
- BYO-AI, self-hostable, encrypted-at-rest — meets the user-sovereignty / privacy requirements
- EN/DE → EN/DE/Arabic-or-Ukrainian — meets the multilingual / inclusion requirements
- Civic employment for migrants → strong NGI strategic relevance (digital public infrastructure)

---

## 3. Honest current state of the project (May 2026)

This is the result of a deep audit of the repo at `/home/user/directjob-scout`, branch `claude/project-analysis-bpHCo`, latest commit `5d1cb9d`.

### What's genuinely strong

- **Working multi-source job discovery**: career-page scanning + federated aggregators (Adzuna, Indeed, LinkedIn) + bookmarklet capture
- **Chat-driven UX with 12-phase journey state machine** (`company_discovery/journey.py`)
- **Structured conversation with confirmation gates** (`company_discovery/chat_router.py`)
- **BYO-AI provider abstraction** (`company_discovery/ai_providers.py`): OpenAI, Gemini, DeepSeek, OpenRouter, Ollama, manual handoff, Claude Code
- **Encrypted profile-at-rest** (ChaCha20-Poly1305)
- **CV builder, persona system (5 personas), skill-gap atlas, outcome tracking**
- **Full EN/DE i18n** with German legal pages (Impressum §5 TMG)
- **MCP server skeleton** (`mcp_server.py`) exposing 8 tools with JSON schemas
- **Self-hosting story**: Dockerfile, docker-compose.prod.yml, Caddy HTTPS, backup/restore scripts, restore-drill
- **Tests exist**: ~20 test files including i18n parity and E2E (Playwright)
- **CI runs on Python 3.9 + 3.12**

### What's missing for NGI0-credibility (BLOCKERS)

- **No LICENSE file** at repo root. This alone is rejection-level.
- **No governance files**: no CONTRIBUTING.md, no CODE_OF_CONDUCT.md, no SECURITY.md, no AUTHORS.md, no SUPPORT.md.
- **No proof of MCP composition**. The central pitch claim ("other civic agents can compose with it via MCP") has no second consumer in the repo, no integration test, no example client.
- **Narrative is "commercial SaaS that happens to be open"**, not "civic commons":
  - `docs/sellable-readiness-*.md` (3 files), `docs/marketing-copy.md`, `docs/operator-launch-*` (3 files)
  - `khalo.org` hardcoded 29 times in `app.py`
  - "Nasser's bug" / tester names in commit messages
  - `keepbuildingtill100%tracker.MD` at repo root
  - Pro/Free billing prominent in README
- **Single author, no community, no legal entity wrapper.** All 5 NGI0 winners we studied are co-ops, university labs, foundations, or 10-year community projects. None is a lone individual.

### What's missing for NGI0-credibility (MAJORS)

- No badges in README
- No screenshots or demo link
- No public ROADMAP.md
- No CHANGELOG.md
- No tagged releases
- CI has tests only — no lint, no mypy, no coverage upload, no security scan
- Tests fail to run locally (cryptography/cffi dependency issue)
- No documentation site (just markdown in `docs/`)
- No translator contributor docs
- No accessibility statement
- No security policy / responsible disclosure channel

### What's OK already

- BYO-AI abstraction is real, credible, swappable
- Docker self-hosting is solid (Caddy + healthcheck + volumes)
- Backup/restore is documented with restore-drill
- Privacy page exists, encryption at rest is documented
- i18n EN/DE is well-implemented (German Impressum present)
- 8 MCP tools have JSON schemas (just need documentation)

### Summary verdict

> A well-engineered, feature-rich MVP with solid deployment infrastructure and genuine privacy-first thinking, but fundamentally **a commercial product seeking open-source funding**, not a mature commons project. Without 60–80 hours of refocusing narrative, fixing governance, proving the MCP story, and sanitizing commercial product framing over the next 4 weeks, NLnet will reject it.

---

## 4. Research findings: what NGI0 winners actually look like

We reverse-engineered five recent NGI0 Commons Fund winners to extract the patterns that get funded.

### The 5 reference winners

| Project | Funded | Description |
|---|---|---|
| **Tenzu** (BIRU-Scop) | Apr 2026 | Open-source project management, official successor to Taiga |
| **OpenVoiceOS** | Oct 2025 | Self-hostable voice assistant, successor to Mycroft AI |
| **CityBikes / pybikes** | Jun 2024 | Open API across 700+ bike-share cities, GBFS standardization |
| **dweb-search / ipfs-search** | NGI0 Discovery | Decentralized-web search engine on IPFS |
| **QLever Similarity Search** | Mar 2026 | Graph database with SPARQL + vector + spatial in one engine |

### Patterns present in ALL or MOST winners (the bar to clear)

**P1. License at root**: AGPL-3.0 or Apache-2.0 only. Zero MIT, zero unlicensed. Tenzu separates LICENSE / NOTICE / TRADEMARK.

**P2. README opens with a quantified or continuity-anchored value prop**: "scales to more than a trillion triples" (QLever); "support for more than 700 cities" (CityBikes); "successor to Taiga" (Tenzu); "privacy-respecting voice assistant platform" (OVOS).

**P3. Standards anchoring**: every winner names a specific external spec they implement, extend, or service. SPARQL 1.1, GeoSPARQL, IPFS, GBFS 2.3/3.0, WCAG 2.2 AA. No "vaguely interoperable" winners.

**P4. Multiple install paths**: native packages + Docker + Helm + installer scripts. QLever has 5+. OVOS has 4+.

**P5. CI beyond "does it build"**: minimum is lint + test + coverage. Competitive bar is lint + test + coverage + format + dependency-audit + locale-check + multi-OS matrix.

**P6. Separate documentation site beyond README** (Docusaurus, mkdocs, sphinx, or wiki). No winner relies on README alone.

**P7. Continuity-of-project narrative**: 4 of 5 are continuations of older FOSS projects. NLnet visibly likes funding *the next chapter of something with a community*.

**P8. Institutional or legal-entity wrapper**: co-op, foundation, university lab, multi-year community. No lone individuals.

**P9. Governance files at root**: minimum CONTRIBUTING.md + CODE_OF_CONDUCT.md (Contributor Covenant) + SECURITY.md. Even projects not accepting PRs ship these.

### NLnet's selection language (key phrases that recur)

- "**Free/libre/open source**" — non-negotiable license
- "**All scientific outcomes must be published as open access**"
- "**WCAG compliant**" — contractual above €50k
- "**Strictly necessary data collection, no transmission to third parties, hosting in Europe**" (Tenzu's framing)
- "**Streamline onboarding, stabilize, expand documentation**" — they reward maturity moves
- "**Bridge gap, make available, interoperable**" — they reward standards work
- "**Powers projects such as the Royal Dutch Visio Voicelab**" (OVOS) — real-world social-impact deployments are valued

### What surprised us (counter-intuitive findings)

- Winners' READMEs are **honest about instability** (Tenzu: "main branch may be unstable"). Polish ≠ pretending to be finished.
- Governance scaffolding is **decoupled from accepting PRs**. Tenzu ships CONTRIBUTING.md whose content is "we don't currently accept PRs." Having the file matters; what it says is secondary.
- Continuity matters more than originality. 4 of 5 are explicitly continuations.
- You **don't need** CodeQL or OpenSSF Scorecard to win. None of the 5 has either.
- The **umbrella matters**: OVOS has 309 repos. Single-repo projects look smaller.
- `FUNDING.yml` is rare (only Tenzu had it). `renovate.json` over `dependabot.yml` is trending in NGI0 cohort.

### Where the winners are WEAK (our differentiation opportunities)

- Public ROADMAP.md linked from README — almost none of the 5 has this
- OpenSSF Scorecard / CodeQL workflow — zero of 5
- Reproducible builds (Nix flake, SLSA) — zero of 5
- Architecture diagrams (ARCHITECTURE.md with system overview) — zero of 5
- Explicit ACCESSIBILITY.md with WCAG version and level — only Tenzu (and theirs is in the NLnet abstract, not in the repo)
- security.txt per RFC 9116 — zero of 5
- SBOM + cosign-signed releases — zero of 5
- SUSTAINABILITY.md describing post-grant business model — almost none

**Investing ~20 hours in differentiation moves us from "competitive with the cohort" to "visibly above the cohort."**

---

## 5. The five strategic problems

These are the framing flaws that no amount of file-adding will fix without a deliberate decision.

**Strategic Problem 1: The repo's narrative is "commercial SaaS that happens to be open source," not "civic commons."**

Every artifact reinforces this: `sellable-readiness-gap-analysis.md`, `marketing-copy.md`, `operator-launch-runbook.md`, Pro/Free tiers in the README, Stripe integration prominent, `khalo.org` everywhere. NLnet does not fund projects pivoting from commercial to commons; they fund projects that are commons from day one.

**Fix**: Week 1 — move commercial docs to a private folder or separate repo, rewrite the README mission, deprioritize Pro/Free in public materials, change the GitHub repo description.

---

**Strategic Problem 2: The central technical claim ("MCP-exposed for composition") has no evidence.**

This is the worst kind of pitch failure — claiming something binary that any reviewer can verify is false in 30 seconds by reading the repo. There is no second consumer, no integration test, no docs explaining how to compose, no link to the housing agent. Without proof, reviewers will mark the entire MCP-composition framing as vaporware.

**Fix**: Week 2 — write MCP server docs with schemas + versioning, build at minimum a mock second consumer that demonstrates composition end-to-end, write an integration test.

---

**Strategic Problem 3: Single-author + no legal entity + no community.**

Every winner has institutional ballast — a French co-op (BIRU Scop), a Dutch foundation, a German university group, a community-foundation succession. NLnet reviewers ask: "If this person disappears tomorrow, what happens to the grant deliverables?"

**Fix**: Weeks 1–4 — recruit 1–2 named co-maintainers in AUTHORS.md (open-source contributors, an NGO contact, the housing-agent author); ship FUNDING.yml; explore a lightweight Verein or association as Phase 2.

---

**Strategic Problem 4: Greenfield positioning where continuity would win.**

4 of 5 winners frame themselves as successors or extensions of existing FOSS projects. We're pitching as new. We can honestly reframe as **"the first civic-services reference implementation of the MCP ecosystem"** — that's continuity-with-an-ecosystem and it lifts the project into a wider narrative.

**Fix**: Week 1 — rewrite the README opener to anchor to MCP and the civic-agent composition story; include explicit mention of the broader MCP ecosystem we extend.

---

**Strategic Problem 5: No standards anchor in the public materials.**

We *implement* MCP, we *use* schema.org JobPosting, we could *commit to* WCAG 2.2 AA. None of this is stated. Naming the standards is what makes reviewers categorize you as "infrastructure" rather than "another app."

**Fix**: Week 1 — add a "Standards we implement" section to README; Week 2 — add `STANDARDS.md` listing MCP version, schema.org JobPosting, WCAG 2.2 AA target, GDPR alignment, AGPL-3.0; Week 4 — sign releases with cosign + attach SBOM.

---

## 6. Strategic decisions made in this session

These are commitments. Do not relitigate without re-opening the discussion.

### License: **AGPL-3.0**

- Reason: defending against proprietary forks of a civic commons. If someone runs a competing paid SaaS on top of this code, AGPL requires them to release their changes.
- Pattern match: 3 of 5 NGI0 winners we studied use AGPL (Tenzu, pybikes, dweb-search).
- Action: add `LICENSE` file at repo root with full AGPL-3.0 text. Add SPDX headers in source files.

### Positioning: **civic commons, MCP-exposed, German-first, EU-exportable**

- The README must open with a commons positioning, not a SaaS positioning.
- "DirectJob Scout is an open-source civic employment agent..." not "DirectJob Scout is a self-hosted job-hunting app..."
- Pro/Free billing details move below the fold or out of public materials entirely.

### Standards we commit to

- **AGPL-3.0** (license)
- **MCP** (Model Context Protocol) as the composition surface — version pinned, schema versioned
- **schema.org JobPosting** for job data
- **WCAG 2.2 Level AA** as a *deliverable of the grant* (not pre-existing)
- **RFC 9116** (`security.txt`)
- **Keep a Changelog** format for CHANGELOG.md
- **SemVer** for releases
- **Contributor Covenant 2.1** for CODE_OF_CONDUCT
- **GDPR** alignment (statement, not certification)

### Grant target

- **NLnet NGI Zero Commons Fund** as the primary target.
- **Phase 1 ask**: €30–40k for the work scope below.
- **Phase 2 signal**: framework extraction + multi-agent composition (housing + jobs) as future grants.

### Scope discipline for the 4 weeks

- **No new product features.**
- **No framework extraction.**
- **No third-language addition** unless a native-speaker contributor is already committed.
- **No new agents.** The housing agent is referenced as future composition, not built in this scope.

---

## 7. The anchor user persona

Every public artifact (README, demo, screenshots, application narrative) must anchor to one concrete, named user persona. Vague personas dilute the pitch.

**Persona**: **a Pflegekraft (care worker) from outside the EU, navigating the German labor market.**

Why this persona:

- **Acute, named labor shortage** in Germany: 300,000+ unfilled care positions, projected to double by 2035.
- **Real foreign-credential friction** (Anerkennung): well-known, government-acknowledged, multi-year process.
- **Real language barrier**: B1/B2 German often required even though the work is hands-on.
- **NGO partners exist**: Diakonie, Caritas Migrationsberatung, ProAsyl, IQ Netzwerk, Pflege in Deutschland, Triple Win, Bayerisches Pflegehilfe-Netzwerk. Letter of support is plausibly obtainable within 4 weeks.
- **EU and German policy interest**: Pflegeberufegesetz, Fachkräfteeinwanderungsgesetz, Triple Win bilateral programmes — this persona maps directly to active government priorities.
- **Strong human-impact narrative for NLnet**: the kind of "powers projects such as the Royal Dutch Visio Voicelab" social-impact framing that OpenVoiceOS used.

**Usage**: every demo screenshot, every example user input, every narrative paragraph in the proposal references this persona. "Aïcha, a nurse trained in Tunisia, arrives in Germany with an Anerkennung process underway and B1 German. She opens DirectJob Scout..." Concrete > abstract.

---

## 8. Where we plan to outshine the winners

Differentiation moves that no winner in our 5-project sample has shipped:

| Move | Effort | Why it lands |
|---|---|---|
| Public quarterly `ROADMAP.md` linked from README | 3 h | Almost no winner has one |
| **OpenSSF Scorecard workflow + badge** | 2 h | Zero of 5 winners |
| Cosign-signed releases + SBOM (cyclonedx) | 3 h | Zero of 5. Supply-chain is hot in 2026 |
| `security.txt` per RFC 9116 | 1 h | Cites another standard |
| `ARCHITECTURE.md` with Mermaid system diagram | 4 h | None of the 5 has a clear one |
| `ACCESSIBILITY.md` with WCAG version + level + audit date | 2 h | Only Tenzu commits; even theirs is in the NLnet abstract not the repo |
| `SUSTAINABILITY.md` with post-grant business model | 3 h | Almost none address this |
| Reproducible build (Nix flake) | 6 h | None of 5. Mentioned in NLnet services page as valued |

Investing ~20–25 hours in these moves us from "competitive with the cohort" to "visibly above the cohort." That's the user's stated goal: *we are building in a time of better technology, we are expected to build much better products.*

---

## 9. What we are explicitly NOT doing in these 4 weeks

- ❌ Adding product features (no new commands, no new aggregators, no new UI screens)
- ❌ Refactoring code into a separate framework library (that's Phase 2)
- ❌ Building or publishing the housing agent code (it can be referenced as future composition; the *artifact* in this scope is a mock or stub second-consumer of the MCP server)
- ❌ Adding a third language without a committed native-speaker contributor
- ❌ Pretending to have community we don't have (fake Discord with 3 members, etc.)
- ❌ Polishing things to look finished — winners are honest about instability
- ❌ Registering a Verein / legal entity (that's Phase 2)
- ❌ Pursuing other grant programs in parallel — focus all bandwidth on NLnet

---

## 10. Sources and references

### NLnet / NGI0
- NGI Zero Commons Fund overview: https://nlnet.nl/commonsfund/
- Guide for Applicants: https://nlnet.nl/commonsfund/guideforapplicants/
- Eligibility: https://nlnet.nl/commonsfund/eligibility/
- Support services (audit, packaging, a11y): https://nlnet.nl/NGI0/services/
- Most recent selection announcements: https://nlnet.nl/news/2026/20260409-announce-commons-fund.html

### Reference winners
- Tenzu: https://nlnet.nl/project/Tenzu/ — https://github.com/BIRU-Scop
- OpenVoiceOS: https://nlnet.nl/project/OpenVoiceOS/ — https://github.com/OpenVoiceOS
- CityBikes: https://nlnet.nl/project/CityBikes/ — https://github.com/eskerda/pybikes
- dweb-search: https://nlnet.nl/project/dweb-search/ — https://github.com/ipfs-search/dweb-search-frontend
- QLever Similarity: https://nlnet.nl/project/QLever-similarity/ — https://github.com/ad-freiburg/qlever

### Standards we cite or implement
- MCP (Model Context Protocol): https://modelcontextprotocol.io
- schema.org JobPosting: https://schema.org/JobPosting
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- RFC 9116 (security.txt): https://www.rfc-editor.org/rfc/rfc9116
- Keep a Changelog: https://keepachangelog.com/en/1.1.0/
- SemVer: https://semver.org
- Contributor Covenant: https://www.contributor-covenant.org
- AGPL-3.0: https://www.gnu.org/licenses/agpl-3.0.html

### German civic-tech context
- Fachkräfteeinwanderungsgesetz (Skilled Immigration Act): https://www.bmi.bund.de
- Anerkennung (foreign credential recognition): https://www.anerkennung-in-deutschland.de
- Triple Win Programme (Pflege): https://www.giz.de
- IQ Netzwerk: https://www.netzwerk-iq.de

---

## Change log of this document

- **2026-05-17**: initial creation. Captures the strategic context, audit findings, and decisions from the planning session with the maintainer.
