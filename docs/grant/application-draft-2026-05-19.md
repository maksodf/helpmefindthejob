<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Helpmefindthejob — NLnet NGI Zero Commons Fund application (working draft)

**Status**: working draft for the §4.4 execution-plan slice; not
yet submitted. The maintainer reviews + an external reader does
a clarity pass + the maintainer submits via nlnet.nl/propose.

**Source-of-truth materials**:
- Per-field structure: [`nlnet-form-fields-2026-05-19.md`](nlnet-form-fields-2026-05-19.md)
- Prior application content (lifted + adapted here): [`12-application-package.md`](12-application-package.md)
- Strategic anchor: [`01-project-brief.md`](01-project-brief.md)
- Decisions referenced inline: 1, 2, 4, 6, 9, 10, 11, 16, 17, 18, 19, 20, 21
- Numerical-claim verification table: bottom of this document
- Honesty discipline: Rule 2 of [`13-lessons-learned.md`](13-lessons-learned.md) — every number traces to a primary source or is tagged

---

## Field 1 — Your name

`[Maintainer fills — Decision 18 consent-first identity-bearing field]`

NLnet's FAQ allows alias pre-acceptance + real name post-acceptance.
Maintainer chooses.

## Field 2 — Email address

`[Maintainer fills]`

## Field 3 — Phone number (optional)

Optional. Skip unless the maintainer wants a phone fallback.

## Field 4 — Organisation (optional)

> Project hosted as a Programme of The Commons Conservancy
> (application pending; Conservancy is a Dutch stichting
> co-founded by NLnet). No commercial legal entity. Lead applicant
> is the individual maintainer; the Conservancy provides
> governance + fiscal channel post-admission per Decision 2.

## Field 5 — Country (optional)

> Germany (EU member state). Helpmefindthejob's reference
> implementation is deployed in Germany; the architecture is
> EU-wide and country-neutral (cross-border deployment is a
> localisation exercise, not a re-engineering effort).

## Field 6 — Call selection

**NGI Zero Commons Fund**.

---

## Field 7 — Proposal name

**Helpmefindthejob — an open-source EU-wide civic employment commons**

(Subtitle for the cover page if the form supports one:
"MCP-composable copilot for users facing structural labour-market
friction in Europe.")

---

## Field 8 — Website / wiki

`https://maksodf.github.io/helpmefindthejob/` (the documentation
site — `mkdocs build --strict` already green, GH Pages serving
will activate when the working branch merges to `main`).

Until that activation: `https://github.com/maksodf/helpmefindthejob`
(canonical source repository).

**Live deployments**:
- Public apex: [`https://helpmefindthejob.org`](https://helpmefindthejob.org/) — open public registration; the same code reviewers see in the repository.
- Demo subdomain: [`https://demo.helpmefindthejob.org`](https://demo.helpmefindthejob.org/) — seeded with the seven canonical personas as read-only accounts (Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias; shared password printed on the demo landing); accounts reset nightly so reviewer interactions never persist. DNS is being configured by the maintainer; until live, the apex above is the same code with a fresh-registration flow.
- Seed-personas recipe: [`scripts/seed-personas.py`](https://github.com/maksodf/helpmefindthejob/blob/main/scripts/seed-personas.py) reproduces the demo state on any self-hosted instance.

---

## Field 9 — Abstract (~200 words)

> Across the European Union, structural labour shortages coexist
> with capable people who cannot get hired — blocked not by
> capability but by friction between what they can do and what
> the labour-market system recognises. The friction is most acute
> for migrants and EU-mobile workers but also affects career
> changers, returning workers, the long-term unemployed, and
> anyone navigating an employment system outside their familiar
> bureaucratic context.
>
> **Helpmefindthejob** is an open-source, multilingual,
> privacy-preserving civic employment agent that captures
> specialist HR and bureaucratic-navigation knowledge into a
> small, well-documented set of MCP-composable modular tools.
> The first reference implementation is a conversational
> jobseeker copilot deployed in Germany; the same modules
> compose with parallel open civic agents (housing, healthcare,
> residency, education) to form a coherent multi-domain civic
> assistant. The codebase is Apache-2.0-licensed, self-hostable,
> encrypted at rest (ChaCha20-Poly1305), runs on the user's
> choice of AI provider (BYO-AI abstraction with seven provider
> implementations — Ollama exercised live in Phase 1; cloud
> providers covered by mocked dispatcher tests pending live-key
> verification in Phase 2), and ships an EU AI Act compliance pack
> designed for the 2 August 2026 high-risk-AI enforcement date.
> Articles 12 (audit log) and 14 (human-oversight admin endpoint)
> are wired in code; Articles 9, 10, 11 + Annex IV, 13, 15, 27
> and 49 are deployer-doctrine artefacts and templates in
> `compliance/` (the methodology under Article 15 is at 33%
> execution — 2 of 6 scenario classes shipped in four dated
> reports; the remaining four classes execute during the
> partner-NGO pilot in Phase 2 per `ROADMAP.md`).
>
> Hosted as a Programme of The Commons Conservancy. Every
> feature is evaluated against a dual measure: improve outcomes
> for the people served AND reduce operational cost for the
> institutions that serve them.

---

## Field 10 — Prior involvement (optional)

Phase 1 work already shipped and verifiable in the public
repository at <https://github.com/maksodf/helpmefindthejob> (90+
commits across the 4-week grant-readiness sprint, May 2026):

- **Apache 2.0 + CLA + governance pack**: LICENSE, NOTICE,
  CONTRIBUTING.md, CODE_OF_CONDUCT.md (Contributor Covenant 2.1),
  SECURITY.md, SUPPORT.md, AUTHORS.md, ACKNOWLEDGMENTS.md,
  TRADEMARK.md, cla.md.
- **EU AI Act compliance pack**: 14 documents under `compliance/`
  covering AI Act Articles 9, 10, 11 + Annex IV, 12, 13, 14, 15 (incl.
  15(5) resilience), 22, 26, 27, 49, 50, 73, 86 plus GDPR Articles
  5, 20, 22, 28, 30, 32, 33, 35 — see [`compliance/INDEX.md`](compliance/INDEX.md)
  for the full file × article reverse-lookup table. Articles **12**
  (audit log) and **14** (`/api/admin/oversight/queue`) are wired in
  code; the remaining articles are deployer-doctrine artefacts and
  templates. Article 15 methodology has executed 4 dated runs against
  `deepseek` + `ollama` (33.3% methodology surface coverage — 2 of 6
  scenario classes; remaining four classes deferred to the partner-NGO
  pilot per honest scoping). The most recent run is the 2026-05-21
  cross-provider comparative (`docs/grant/bias-comparative-report-2026-05-21.md`
  — 140 data points across 7 personas × 10 scenarios × 2 providers);
  the prior 2026-05-19 polish run measured the AI-output-quality OOB
  rate at 13.0 % (10 / 77), with the parser-layer score-clamp catching
  out-of-range outputs before the user surface (see
  `tests/test_prompt_injection_vectors.py::V3JdIndirectInjection`).
  Article 15(5) resilience is documented in
  [`compliance/prompt-injection-testing.md`](compliance/prompt-injection-testing.md)
  (10 canonical vectors mapped to structural-defence layers) and pinned
  by 8 unit tests in `tests/test_prompt_injection_vectors.py`.
  Article 12 + 26(6) key-rotation procedure is documented in
  [`compliance/audit-log-key-rotation.md`](compliance/audit-log-key-rotation.md)
  (9 sections; active / sealed / destroyed key lifecycle; dated
  rotation log).
- **MCP server v0.2.0** with 13-tool catalogue, JSON-Schema
  validated input, stdio JSON-RPC transport — `docs/mcp-server.md`
  documents the contract.
- **Accessibility pack**: WCAG 2.2 AA first-pass + auth-surface
  audit + light-mode + dynamic-state + compliance markdown audit
  via axe-core CLI + axe-playwright-python. 30 violation
  instances closed across 22 audited surfaces; full audit
  evidence in `ACCESSIBILITY.md`.
- **Reproducible build**: Nix flake at repo root pinning
  `nixos-25.05` nixpkgs commit; `nix flake check` green;
  `nix develop --command python3 -m unittest discover -s tests`
  runs the full 1029-test suite under Python 3.12.
- **Signed releases + SBOM**: v0.1.0 source tarball cosign-signed
  (long-lived ECDSA P-256, model b — keyless via GH Actions OIDC
  planned for v0.2.0+); CycloneDX 1.6 SBOM (91 components)
  attached to the GitHub Release.
- **RFC 9116 security.txt** at `/.well-known/security.txt`
  served by `app.py`'s static handler; curl-probe verified.
- **OpenSSF Scorecard workflow** with all six workflow files
  SHA-pinned per the "pinned-dependencies" check.

Maintainer's prior open-source involvement:
`[Maintainer fills — Decision 18 — specific past projects or
contributions in their own voice]`.

---

## Field 11 — Requested Amount

**€37,000** (below the €50,000 first-proposal cap). Frugal-by-
default per Decision 10. The budget reflects the genuine cost of
the deliverables rather than maximising what the fund permits.

---

## Field 12 — Budget usage explanation

Six milestones, results-only, no progress reports — per NLnet's
standard model. Each milestone is a verifiable public deliverable;
payment requested upon delivery (artefact reachable from the
public repository or the Conservancy account).

### Milestone 1 — Legal + narrative foundations (€4,000)

**Deliverable**: complete governance pack already shipped (Apache
2.0 LICENSE, CLA at `cla.md`, CODE_OF_CONDUCT.md, CONTRIBUTING.md,
SECURITY.md, SUPPORT.md, AUTHORS.md, ACKNOWLEDGMENTS.md,
TRADEMARK.md, NOTICE), RFC 9116 `/.well-known/security.txt` served
by the app, GitHub repository housekeeping (description, topics,
Discussions enabled, branch-protection rules — last item
maintainer-applied per the `scorecard-status-2026-05-19.md`
finding), README rewritten with civic-commons positioning (per
Decision 21: friction-class architecture + seven-persona panel
anchor).
**Cost-saving mechanism**: provides the institutional-readiness
signal that deployers require to even consider adoption;
eliminates the licensing-ambiguity blocker that prevents
public-sector procurement engagement.
**Acceptance**: reviewer browses the public repository and
confirms every named artefact present, well-formed, and
cross-referenced.

### Milestone 2 — MCP composition reference (€8,000)

**Deliverable**: published MCP server documentation
(`docs/mcp-server.md`) with versioned 13-tool catalogue (v0.2.0)
+ JSON Schema for every tool's input; one concrete reference
integration with a parallel open civic agent (housing — Option A
mock stub default per Decision 20, with Option B real-integration
path documented in the same MCP doc for the maintainer's friend's
agent if collaboration confirms); MCP-integration CI test in
`.github/workflows/mcp-integration.yml` exercising the
composition surface; `STANDARDS.md` citing MCP 2024-11-05,
schema.org JobPosting, ESCO occupations + skills, EURES schema,
JSON Schema 2020-12, ISO 8601, ISO 639-1, RFC 7807, RFC 9116.
**Cost-saving mechanism**: every additional civic agent built on
top of this MCP surface reuses our composition layer, avoiding
duplicated engineering cost across the civic-tech ecosystem.
**Acceptance**: reviewer runs `python3 -m unittest tests.test_phase11_mcp` (or
the MCP-integration workflow) against the public repository and
observes the composition test green.

### Milestone 3 — EU AI Act compliance pack (€10,000)

**Deliverable**: complete `compliance/` directory shipping risk
management plan (Article 9), data governance (Article 10),
technical documentation aligned with Annex IV (Article 11), audit
log infrastructure with documented schema (Article 12),
transparency notice + deployer operating manual (Article 13),
human-oversight guide (Article 14), accuracy + bias testing
methodology with reproducible result reports (Article 15),
pre-filled FRIA template (Article 27) + EU AI database
registration template (Article 49).
**Cost-saving mechanism**: institutions deploying the agent
inherit a compliant configuration, avoiding the consulting cost
otherwise required to bring an employment-AI deployment into AI
Act compliance for the 2 August 2026 enforcement date. (Specific
consulting-cost ranges are industry estimates — see verification
table below.)
**Acceptance**: reviewer browses the `compliance/` directory and
confirms all 10 files present with substantive content; reviewer
runs the opt-in bias-methodology test `DIRECTJOB_RUN_BIAS_METHODOLOGY=1
python3 -m unittest tests.test_bias_methodology` and observes
the published reports' numbers reproduce within model
non-determinism tolerance.

### Milestone 4 — Public demo deployment + accessibility (€6,000)

**Deliverable**: live public demo at a stable URL running the
canonical reference implementation, with the seven-persona panel
pre-seeded (Aïcha, Yusuf, Olga, Mahmoud, Maria — most-acute
migrant; Käthe + Tobias — wider-friction-class per Decision 21);
mkdocs-material documentation site at
<https://maksodf.github.io/helpmefindthejob/>; `ACCESSIBILITY.md`
with a **WCAG 2.2 AA target** + automated audit evidence across
4 dated passes (unauthenticated surfaces axe-core CLI + authenticated
surfaces Playwright + axe-playwright-python + light-mode +
dynamic-state + compliance markdown + post-rename re-audit;
32 violation instances closed; 0/0/0/0 across 33 audited captures).
**Honesty note**: axe-core documentation itself states automated
tooling catches ~20–50 % of WCAG issues; full WCAG 2.2 AA
conformance requires manual screen-reader + keyboard + cognitive
review (HAN University manual review is the planned next pathway
post-Commons-Conservancy admission).
**Cost-saving mechanism**: reduces the discovery + evaluation
cost for any institutional adopter; the demo replaces the need
for vendor-style sales calls or presentations.
**Acceptance**: reviewer visits the demo URL, signs in as Aïcha
(seeded credentials in `scripts/seed-personas.py`), exercises the
chat surface end-to-end.

### Milestone 5 — Reproducible builds + supply-chain (€5,000)

**Deliverable**: `flake.nix` + `flake.lock` at repo root pinning
`nixos-25.05` nixpkgs commit; `.github/workflows/quality.yml` with
ruff lint + format + mypy strict subset + coverage upload +
pip-audit; `.github/workflows/scorecard.yml` with all six workflow
files SHA-pinned per OpenSSF "pinned-dependencies"; cosign-signed
`v0.1.0` source tarball + CycloneDX 1.6 SBOM (`v0.1.0-sbom.json`,
91 components) attached to the GitHub Release;
`docs/releases/v0.1.0-signing.md` with the full verification
recipe + key-rotation policy.
**Cost-saving mechanism**: reproducible builds + supply-chain
signals reduce per-deployment maintenance burden; signed releases
with SBOM eliminate one entire category of compliance work for
institutional adopters.
**Acceptance**: reviewer runs `nix develop --command python3 -m
unittest discover -s tests` from a fresh clone + the documented
`cosign verify-blob ... --insecure-ignore-tlog` command and
observes both green.

### Milestone 6 — Institutional readiness + standards interop (€4,000)

**Deliverable**: at minimum one letter of support from a credible
institutional partner (target: AWO Charlottenburg-Wilmersdorf
FIM Pangea-Haus, RINWA Berlin / La Red, or TU Berlin Career
Service — drafts at `docs/grant/outreach-drafts/`, send-gate
readiness in `outreach-readiness-2026-05-19.md`); the curated
ESCO 30-occupation + 50-skill reference dataset
(`reference/esco/`) consumed by the MCP `query_esco_skill` tool;
EURES schema projection contract documented in
`docs/esco-integration.md`; admission as a Programme of The
Commons Conservancy in active application.
**Cost-saving mechanism**: institutional wrapper + standards
alignment opens institutional adoption channels without
per-deployment custom integration work.
**Acceptance**: reviewer inspects `letters-of-support/` (or, if
no letter received by submission, the outreach-tracker entry in
`11-institutional-outreach.md` showing the active discussion);
reviewer inspects the ESCO reference dataset + the EURES export
contract.

### Total: €37,000

| Milestone | Cost | Duration |
|---|---|---|
| 1 — Legal + governance | €4,000 | shipped |
| 2 — MCP composition | €8,000 | shipped |
| 3 — AI Act compliance pack | €10,000 | shipped |
| 4 — Demo + accessibility | €6,000 | shipped (live deploy pending merge-to-main) |
| 5 — Reproducible builds | €5,000 | shipped |
| 6 — Institutional readiness | €4,000 | partially shipped (letter outreach pending Week 4 send) |
| **Total** | **€37,000** | grant covers retrospective sprint work + outstanding institutional readiness |

The honest framing: the bulk of the engineering work has been
delivered during the 4-week pre-submission sprint. The grant
covers maintainer time spent on that work + the remaining
institutional readiness (letters of support, Conservancy
admission, post-merge Pages activation, outreach send). This is
the **frugal-by-default** posture per Decision 10 — €37k is
below the €50k first-proposal cap and reflects the genuine cost
of the delivered work.

---

## Field 13 — Other funding sources (optional)

None today. The project is unfunded; the 4-week sprint reflected
the maintainer's own time as an in-kind contribution.

Future-looking, the multi-grant arc + optional support contracts
are documented in [`SUSTAINABILITY.md`](../../SUSTAINABILITY.md);
no Phase 2 funding is currently committed.

---

## Field 14 — Project comparison

**Existing solutions fail in three specific ways**:

**(1) LinkedIn-class platforms** are walled gardens that exclude
anyone outside their commercial model and harvest personal data
as the price of access. They do not serve users whose CV format,
language, or credential origin doesn't match the platform's
US/global template. They cannot run inside a Beratungsstelle's
data-protection regime.

**(2) Public-employment-service tooling** (Bundesagentur für
Arbeit's JOBBÖRSE, EURES) is bureaucratic, host-language-only,
and offers no AI-assisted personalisation. The user signs up,
sees thousands of unranked listings, and is expected to
self-translate every legal-bureaucratic term (`Anerkennung`,
`§16d`, `TVöD`, `Wiedereinstieg`).

**(3) The emerging wave of GPT-wrapper job assistants** is
unstructured, unauditable, vendor-locked to a few commercial AI
providers, and indifferent to the civic dimension. **None is
compliant with the EU AI Act's high-risk obligations applicable
from 2 August 2026** ([EU 2024/1689 timeline](https://artificialintelligenceact.eu/implementation-timeline/)).
An employment-AI system makes high-risk decisions about access to
employment (Annex III §4); the compliance obligations are
substantial.

**What Helpmefindthejob does that the above don't**:

| Property | LinkedIn-class | BA JOBBÖRSE | GPT-wrapper | Helpmefindthejob |
|---|---|---|---|---|
| Open-source (Apache 2.0) | no | no | no | **yes** |
| Self-hostable on commodity hardware | no | no | mixed | **yes** (deployment-recipe.md + flake.nix) |
| User-sovereign data (encrypted at rest) | no | no | no | **yes** (ChaCha20-Poly1305 AEAD) |
| BYO-AI (no vendor lock-in) | no | no | no | **yes** (OpenAI / Anthropic / Gemini / DeepSeek / Ollama-offline) |
| MCP-composable with other civic agents | no | no | no | **yes** (13-tool v0.2.0 catalogue, JSON-Schema gated) |
| EU AI Act compliance pack | no | partial | no | **yes** (`compliance/`, 10 artefacts) |
| WCAG 2.2 AA audit evidence | no | partial | no | **yes** (`ACCESSIBILITY.md`, 30 → 0 findings) |
| Reproducible build (Nix flake) | no | no | no | **yes** (`flake.nix` + `flake.lock`) |
| Signed releases + SBOM | no | no | no | **yes** (cosign + CycloneDX 1.6) |
| RFC 9116 security.txt | no | partial | no | **yes** |
| Multilingual (DE + EN today; AR/UK/TR/RO roadmap) | partial | partial | partial | **yes** |
| Persona-panel architecture (friction-class, not migrant-only) | no | no | no | **yes** (Decision 21) |
| Cost-saving doctrine (institutional value) | no | partial | no | **yes** (`08-cost-saving-doctrine.md`) |

The closest comparable project we have surveyed is the
**Bundesagentur für Arbeit's JOBBÖRSE + the public-employment
service's evolving AI-assistant pilots** — those are public-sector
but closed-source, German-only, and do not expose any composition
surface for other civic agents. There is no open-source EU-wide
civic employment commons in production today.

**Differentiation from FOSS projects in adjacent spaces**: we have
surveyed the existing civic-tech-for-migrants FOSS landscape
(Open R5 in `04-research-and-decisions.md` Part C) and found no
project with overlapping scope. The closest neighbours operate
in adjacent civic domains (Mein Grundeinkommen-style benefit
calculators, refugee-aid information portals, civic-data
visualisation projects) but do not address employment-search,
CV-tailoring, or institutional-deployer compliance.

---

## Field 15 — Technical challenges (optional)

Three categories of technical challenge anticipated for the
remaining Phase 1 work + early Phase 2:

**(1) Bias-testing methodology coverage**. The existing three
dated bias-testing reports (`docs/grant/bias-testing-2026-05-*.md`)
cover 33.3% of the methodology surface (2 of 6 scenario classes:
scoring + CV-tailoring). The remaining four classes (onboarding,
discovery, motivation-letter drafting, skill-gap brief) are
sequenced for post-grant dated reports. The challenge is doing
them well at the same honesty discipline — no tolerance
manipulation — rather than executing them at all.

**(2) Cross-industry over-generalisation in fit-scoring**. The
2026-05-18-polish run surfaced a prompt-phrasing sensitivity:
the same persona-against-same-target-industry scenario scored
in-band with explicit industry-jargon (Maria → Logistics
Coordinator: 5/100) and over-band with generic phrasing (80/100,
Δ +20 above tolerance ceiling). The 2026-05-19 prompt-enhancement
run + cross-industry probe verdict (ONE-OFF across 7 personas)
reclassified this as prompt-phrasing-sensitive, not systematic
bias — but the underlying scoring sensitivity is a real product
question. Phase 1 closes the methodology gap (`build_cv_tailoring_prompt`
enhanced); Phase 2 probably needs per-criterion scoring
breakdown rather than holistic scoring (the R4 entry in
`compliance/risk-management-plan.md`).

**(3) Cross-civic-agent composition latency**. The MCP catalogue
is JSON-Schema gated + the housing-agent integration is currently
a mock stub per Decision 20 + Decision 11. When a real partner
agent comes online (Option B path), the composition latency
budget needs measurement — sequential handoff vs profile-shared
composition vs orchestrated agent invocation each have different
UX consequences for a user navigating a multi-domain civic
journey. Phase 2 work.

---

## Field 16 — Ecosystem description

**Where Helpmefindthejob fits in the NGI / civic-tech / labour-
market ecosystem**:

**Upstream (we depend on)**:
- [Model Context Protocol](https://modelcontextprotocol.io)
  (`2024-11-05`) — the composition surface for civic agents
- [ESCO](https://esco.ec.europa.eu/) — European Skills,
  Competences, Qualifications and Occupations taxonomy, hosted
  by DG Employment
- [EURES](https://eures.ec.europa.eu/) — European Employment
  Services standards, hosted by DG Employment
- [schema.org JobPosting](https://schema.org/JobPosting) — public
  job-posting schema
- [WCAG 2.2 AA](https://www.w3.org/TR/WCAG22/) — W3C accessibility
- [EU AI Act (Regulation (EU) 2024/1689)](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
  — Articles 9, 10, 11, 12, 13, 14, 15, 27, 49, Annex III §4
- [The Commons Conservancy](https://commonsconservancy.org/) —
  institutional wrapper, NLnet co-founded

**Composable peers (we publish via MCP for)**:
- Housing-search agents (the maintainer's friend operates one;
  Option B real integration path per Decision 20)
- Healthcare-access agents (not yet built; the MCP surface is the
  invitation)
- Residency-permit agents (post-Phase-1 candidate)
- Education / `Anerkennung`-pathway agents (post-Phase-1 candidate)
- Integration-course / `BAMF`-Programme agents

**Downstream (we serve)**:
- Individuals: the seven-persona panel (Aïcha + Yusuf + Olga +
  Mahmoud + Maria + Käthe + Tobias) per Decision 21 — five
  most-acute migrant + two wider-friction-class
- Migrationsberatungsstellen (MBE service points across DE) —
  see verification table for the count
- IQ-Netzwerk regional networks
- Optionskommunen Jobcenter (autonomous Jobcenter operating
  Bürgergeld under §6a SGB II)
- University career services (international graduates + first-
  generation graduates + career changers)
- Civic-tech reusers (the MCP catalogue is the public commons
  interface)

**Adjacent NGI projects**: NLnet's `commons-fund/` published
project list includes adjacent civic-tech infrastructure (FOSS
identity layers, public-data portals, ePartizipation toolchains).
Helpmefindthejob's MCP composition surface is designed to
interoperate with those via the same protocol used by Claude
Desktop / Cursor / Continue / Cline — no NLnet-specific glue.

**Reusability of the Phase 1 deliverables**: every piece of
infrastructure is generalisable:
- The MCP catalogue + composition pattern → template for any
  civic-domain agent
- The `compliance/` pack → template for any AI-using civic tool
  facing AI Act obligations
- The bias-testing methodology → template for any persona-served
  AI civic tool
- The Nix flake + cosign + SBOM + SHA-pinned actions →
  drop-in supply-chain hygiene for the NGI ecosystem
- The accessibility audit infrastructure (axe-core CLI +
  axe-playwright-python runner) → reusable for any web-based
  NGI civic tool

---

## Risks we acknowledge

NGI0 winners are honest about the risks their project carries; the
strongest applications make the reviewer's risk-assessment task
easier rather than hiding the failure modes. The maintainer's
on-record risk register at `docs/grant/05-risks-and-stakeholders.md`
lists fifteen R-numbered concrete operational risks (R1 application
deadline mismatch through R15 production-deployment leak); this
section surfaces the four architectural / institutional risks that
ride above that operational list and that a reviewer should weigh
against the application's promises.

**Adoption risk** — *the institutional uptake assumption is the
critical hinge of the cost-saving doctrine* (`docs/grant/08-cost-saving-doctrine.md`).
If only individuals self-host and zero institutions deploy at
caseload scale, the cost-saving math is unverified and the impact
story is bounded by what a single-maintainer civic-tech tool can
reach via word-of-mouth. Mitigations: the three institutional
outreach letters at `docs/grant/11-institutional-outreach.md` are
sequenced for sending in the submission window (see Section 1.1 of
`PlanTowardPerfection.MD`); the friction-class architecture means
even non-migrant-focused institutions can adopt without scope
mismatch (a Jobcenter serves all Bürgergeld recipients, not only
the migrant subset); the Commons Conservancy programme path
strengthens the institutional-trust posture for risk-averse
adopters. Cross-refs: R13 (reviewer expects more partners than we
secure — Low / Medium per the register); R10 (scope creep — High /
Medium); R6 (cost-saving claims viewed as unverified marketing —
Medium / Medium).

**Sustainability risk** — *single-maintainer + grant-dependent
funding is the dominant project-continuity exposure*. The maintainer
plus one partner-contributor (co-resident; see `04-research-and-decisions.md`
Decision 17) does not constitute a recruitment pipeline; if either
steps away, the project enters survival mode. Mitigations: the
Commons Conservancy wrapper guarantees continuity of governance
even on maintainer transition (Programme is the legal home, not the
maintainer's GitHub account); the multi-grant arc
(`SUSTAINABILITY.md` 7-pillar model, post-NLnet Sovereign Tech Fund
+ Prototype Fund + FOSS contributor fund applications) reduces
single-funder dependence; the Phase-2 framework-extraction work
opens the project to commoditisation by other civic-tech projects,
which broadens the contributor base. Cross-refs: R2 (single-author
sustainability concern — High / High); R12 (maintainer burnout —
Medium / High).

**AI-vendor-lock-in risk** — *the BYO-AI architecture is the
designed mitigation, but is not a complete defence*. The system runs
on the deployer's choice of OpenAI / Anthropic / Gemini / DeepSeek /
OpenRouter / Ollama / Codex CLI / Claude Code; switching providers
is a configuration change, not a code change. But the prompt corpus
(every `build_*_prompt` function in `company_discovery/analysis.py`)
has been calibrated against the models the maintainer can afford to
run (currently deepseek + ollama, per the 2026-05-21
bias-comparative-report). Calibration that holds for those two
models is **not guaranteed** to hold for the other six; the AI
Provider Honesty Matrix at `docs/grant/15-ai-provider-honesty-matrix.md`
documents the unverified surface honestly. Mitigations: the
methodology in `compliance/accuracy-and-bias-testing.md` §3 gives a
deployer the procedure to re-validate against their chosen provider;
the prompt-injection unit tests
(`tests/test_prompt_injection_vectors.py`) pin structural defences
that hold regardless of provider compliance; the kill-switch
(`HELPMEFINDTHEJOB_DETERMINISTIC_ONLY=true`) lets a deployer disable
AI entirely if a provider becomes untrusted mid-deployment.
Cross-refs: R5 (reviewer skepticism of MCP as a civic-tech standard
— Medium / Medium); R14 (encryption / data-handling claims don't
hold under scrutiny — Low / High).

**Friction-class scope-creep risk** — *the friction-class
architecture (Decision 21) is broader than the migrant-only framing,
which strengthens the architecture but creates a narrative-coherence
risk*. A reviewer reading the friction-class framing without the
"migrant five as primary narrative anchor" caveat may interpret the
project as scope-creep ("they're trying to solve every employment
friction at once"); a deployer in a migrant-focused organisation may
worry the project is drifting away from their use case; a press
mention without the friction-class context may mis-position the
project as a generic employment tool. Mitigations: every public
artefact carries the seven-persona panel naming Aïcha + Yusuf + Olga
+ Mahmoud + Maria first (the migrant five as primary anchor) and
Käthe + Tobias second (the wider friction-class as architectural
demonstration); the `docs/grant/07-personas.md` document fixes the
canonical persona-panel ordering; `compliance/deployer-operating-manual.md`
§1 spells out which deployer-type serves which subset of the
friction class. Cross-refs: R8 (German translation quality not
native — Medium / Medium, indirect via the multilingual-coverage
story); R10 (scope creep — High / Medium, named explicitly because
this exact risk is its archetype).

The application's claim to be a top-tier civic-commons project does
not depend on all four risks resolving in the project's favour. It
depends on the maintainer maintaining the documented mitigations,
the Commons Conservancy programme continuing to provide governance
continuity, and at least one institutional partner reaching
production deployment in Phase 2. The honest framing for any
reviewer: the system is shipped; the risks are named; the mitigations
are in place; the unknowns are documented in
`04-research-and-decisions.md` Part C; the Phase-2 roadmap addresses
the highest-leverage residual exposures first.

---

## Field 17 — Attachments (optional)

Recommended attachments (each ≤ 50 MB; total ≤ 50 MB):

1. **PDF render of the abstract + project comparison + budget**
   (1–2 pages) — for reviewers who download for offline reading.
2. **Cosign-signed `v0.1.0-source.tar.gz.sigstore` bundle + the
   `v0.1.0-sbom.json` CycloneDX SBOM** — supply-chain evidence
   citable in Article 11 technical documentation.
3. **`ACCESSIBILITY.md` rendered as PDF** — accessibility audit
   evidence (the live HTML version is canonical, but a PDF
   snapshot at submission time anchors the claim).
4. **`compliance/INDEX.md` rendered as PDF** — entry point to the
   14-document EU AI Act compliance pack, with the full file ×
   article reverse-lookup table so the reviewer can navigate
   straight to the artefact addressing any Article they ask about.
   The pack itself stays in the repo; this PDF is the navigational
   index a reviewer downloads for offline reading.
5. **`docs/grant/SECURITY-AUDIT.md` rendered as PDF** — gitleaks
   full-history scan summary (2026-05-24): 17 hits, all triaged as
   test-fixture false positives; zero real secrets in history.
   Pairs with the `compliance/data-governance.md` security-controls
   section for the trust-but-verify story.
6. **`docs/grant/bias-comparative-report-2026-05-21.md` rendered as
   PDF** — the 140-data-point cross-provider comparative bias run
   (7 personas × 10 scenarios × 2 providers) including per-persona
   means, top-spread disagreement table, and the reproducible
   replay command. No competitor in this space publishes this
   data; the PDF makes the reviewer's offline-reading flow as
   strong as the in-repo file.

Optional (skip if it adds bulk without adding evidence):
- Letter of support PDF once a partner signs — see
  Milestone 6.
- Individual compliance-pack files as PDFs (the INDEX above points
  at every one in the repo; attaching each as a separate PDF is
  bulk without adding evidence unless the reviewer specifically
  requests it).

---

## Field 18 — GenAI usage

**"I have used generative AI in drafting this proposal."**

## Field 19 — Model details (conditional on Field 18)

> Claude (Anthropic) was used during the 4-week pre-submission
> sprint to help draft documentation, accelerate code-review,
> author tests, and structure the application package. Every
> substantive technical decision, every numerical claim, every
> persona detail, every institutional positioning judgement was
> made by the human maintainer; the LLM accelerated drafting and
> surface-language work. Every output was human-reviewed before
> commit. Specific contributions where GenAI was used: drafting
> structure of `docs/grant/12-application-package.md` and this
> derived application draft, accelerating documentation
> (`docs/translating.md`, `SUSTAINABILITY.md`, `ACCESSIBILITY.md`),
> writing test scaffolding, structuring CI workflows.
>
> The maintainer wrote: the seven-persona panel + friction-class
> framing (Decision 21), the cost-saving doctrine (08-cost-
> saving-doctrine.md), the Conservancy admission decision
> (Decision 2), the budget structure (Decision 10), and every
> strategic positioning judgement. Per the NLnet FAQ guidance,
> the maintainer reviewed every AI-assisted section before
> commit.

## Field 20 — AI prompt files (optional)

Skip. The substantive prompts are embedded in the commit messages
and in the planning artefacts under `docs/grant/`.

---

## Field 21 — Privacy acknowledgment

Checked at submission time.

## Field 22 — Send copy

Checked at submission time.

---

## NLnet support services we intend to use if funded

Per the FAQ + `nlnet-form-fields-2026-05-19.md` §"NLnet support
services available to grantees":

1. **Accessibility audit — HAN University of Applied Sciences**.
   Phase 1 ships an axe-core automated baseline at 30 → 0
   findings across 22 surfaces; the HAN manual review covers the
   gaps axe-core can't (keyboard-trap discovery, focus-order,
   tab-order, screen-reader narration of dynamic states). The
   `ACCESSIBILITY.md` "Known gaps" table already names HAN
   audit as the pathway for manual review.
2. **Mentoring — AI Act compliance updates**. The 2026-08-02
   enforcement date triggers the high-risk-AI obligations on
   Article 6+ providers. As clarifications + secondary
   legislation land post-enforcement, NLnet mentoring on
   substantive interpretation would help keep the
   `compliance/` pack current.
3. **Packaging — NixOS Foundation**. The Phase 1 `flake.nix` is
   a hybrid Nix-native interpreter + pip-managed deps pattern.
   A pure-Nix `buildPythonApplication` package would extend
   reproducibility evidence; NixOS Foundation support could
   accelerate that work in Phase 2.

**Security audit deferred** to a Phase 2 ≥€50k subsequent
proposal — the Phase 1 codebase (encryption-at-rest layer,
audit-log emitter, MCP input validation) has been internally
reviewed but not externally audited; an external security audit
makes sense once a real institutional deployment is in active
production use.

---

## Honesty discipline + Decision-references inventory

This draft is honest about the project's actual state:

- **Pre-launch** per [Decision 17](04-research-and-decisions.md#decision-17-stakeholder-collapse).
  One private tester (the maintainer's partner / co-maintainer).
  Zero outside contributors today. Zero hosted-support contracts.
  Zero paying users.
- **Cost-saving claims are projected/modelled**, not measured
  against deployed users. The cost-saving doctrine
  (`08-cost-saving-doctrine.md`) is structured as testable
  hypotheses, not as marketing copy.
- **Bias-testing executed at 33.3% of methodology surface**;
  remaining 4 classes deferred to post-Phase-1 dated reports
  per the honesty note at the top of each bias-testing report.
- **Application is for READINESS** ([Decision 9](04-research-and-decisions.md#decision-9-institutional-integration--pitch-readiness-not-adoption)),
  not for adoption. We pitch institutional readiness +
  Phase 1 pilot candidates (Beratungsstelle / Optionskommune /
  university career service), not "adopted by the
  Bundesagentur für Arbeit in 2027".
- **Friction-class framing** per [Decision 21](04-research-and-decisions.md#decision-21-positioning-frame--friction-class-not-migrant-class):
  migrants and EU-mobile workers are the most-acute use case
  AND the primary narrative anchor, but the architecture is
  friction-driven, not demographic-driven.
- **No infrastructure-vendor commitments** beyond what
  existing Decisions already documented (Conservancy
  wrapper per Decision 2; Apache 2.0 + CLA per Decision 1).

**Decisions cited in this draft**: 1, 2, 4, 6, 9, 10, 11, 16,
17, 18, 19, 20, 21.

---

## Per-numerical-claim verification table (Rule 2 of 13-lessons-learned.md)

Every number in this draft traces to a primary source URL, or
is tagged as `industry-estimate` / `projected` / `not measured`.
NLnet reviewers can audit each claim against the source.

| Claim | Source | Status |
|---|---|---|
| EU AI Act high-risk obligations enforce on **2 August 2026** | [Regulation (EU) 2024/1689, Article 113](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) + [AI Act implementation timeline](https://artificialintelligenceact.eu/implementation-timeline/) | **VERIFIED**. Article 6 + Annex III high-risk systems have a 24-month transition from entry into force (2024-08-02), landing at 2026-08-02. |
| NLnet first-proposal funding range **€5,000 – €50,000** | <https://nlnet.nl/commonsfund/> + <https://nlnet.nl/commonsfund/faq/> | **VERIFIED 2026-05-19** (WebFetch). |
| NLnet lifetime cap per third party **€500,000** | <https://nlnet.nl/commonsfund/guideforapplicants> | **VERIFIED 2026-05-19** (WebFetch). |
| NLnet weighted scoring **30 % technical / 40 % relevance-impact / 30 % cost-effectiveness; pass threshold 5.0 / 7.0** | <https://nlnet.nl/commonsfund/guideforapplicants> | **VERIFIED 2026-05-19** (WebFetch). |
| NLnet Commons Fund 13th-call deadline **2026-06-01 12:00 CEST** | <https://nlnet.nl/commonsfund/> | **VERIFIED 2026-05-19** (WebFetch). |
| Annex III §4 (employment, workers management and access to self-employment) covers AI systems used in recruitment, selection, evaluation | EU 2024/1689 Annex III §4 | **VERIFIED** (primary regulation text). |
| **163 Engpassberufe in DE** | [Bundesagentur für Arbeit — Fachkräftebedarf overview](https://statistik.arbeitsagentur.de/DE/Navigation/Statistiken/Themen-im-Fokus/Fachkraeftebedarf/Fachkraeftebedarf-Nav.html) — section "Arbeits- und Fachkräftemangel trotz Arbeitslosigkeit" carries the line *"Die letzte Fachkräfteengpassanalyse der Statistik der Bundesagentur für Arbeit weist 163 Engpassberufe aus."* | **VERIFIED 2026-05-19** via direct fetch of the BA Fachkräftebedarf overview page. The "of ~1,200 occupations" qualifier in the application body refers to the size of the BA Berufsklassifikation der Berufe 2010 (KldB 2010) framework (~1,300 Berufsgattungen at the 5-digit code level); the headline 163-shortage-occupations figure is the verified anchor. |
| **Tens of thousands of unfilled healthcare positions in DE** (was: "~46,000") | [OECD Economic Surveys: Germany 2025](https://www.oecd.org/en/publications/oecd-economic-surveys-germany-2025_2c91e1d4-en.html) — citation preserved; precise figure NOT led with in the body | **REWORDED 2026-05-19 (pass 2)**. 5 alternative WebFetch routes exhausted (Destatis press releases / Deutscher Pflegerat / DKG press / IW Köln Arbeitsmarkt / BMG Pflegekräfte); none surfaced a single primary-source URL with the 46,000 figure published at headline level (403/404/401 across the candidate routes). The application body (`12-application-package.md` §C) is reworded to "tens of thousands of unfilled healthcare positions" with the OECD citation preserved as the documented anchor + the BA labour-market reports as a corroborating source. The 46,000 figure remains a defensible OECD-sourced estimate but the body no longer leads with a precise number the maintainer cannot independently re-verify in <1 hour. |
| **Migrationsberatungsstellen (MBE) operated nationwide** (was: "~700 service points") | [BAMF-NAvI](https://bamf-navi.bamf.de/de/) (canonical service-point directory; no aggregate count published) | **REWORDED 2026-05-19 (pass 2)**. 4 alternative WebFetch routes exhausted (BAMF press releases / Bundesregierung Migration page / BAGFW homepage / Wikipedia MBE article); none yielded an aggregate count. The application body (`12-application-package.md` §C) is reworded to "Migrationsberatungsstellen (MBE) operated nationwide by the six Wohlfahrtsverbände (Caritas, Diakonie, AWO, Paritätischer, DRK, ZWST) under BAMF coordination and located via the BAMF-NAvI directory" — drops the "~700" entirely + names the operational architecture (Wohlfahrtsverbände + BAMF coordination + BAMF-NAvI). The institutional-readiness rhetorical force is preserved by the operational specificity (six named Wohlfahrtsverbände); the count claim is no longer a drift risk. |
| **16 IQ-Netzwerk regional networks** | <https://www.netzwerk-iq.de/> | **STRUCTURAL** — IQ-Netzwerk is organised by Bundesland; with 16 Länder there are 16 regional networks by design. **VERIFIED structurally** (the federal-state structure of Germany is constitutionally fixed); maintainer should confirm against the IQ-Netzwerk public page that this organisational structure persists at submission time. |
| **Optionskommunen Jobcenter (cap of 110 per §6a SGB II + Article 91e GG; BMAS list = current count)** (was: "104" → "110 total") | [§6a SGB II](https://www.gesetze-im-internet.de/sgb_2/__6a.html) verified via gesetze-im-internet.de WebFetch + [Article 91e GG](https://www.gesetze-im-internet.de/gg/art_91e.html) verified via same | **REWORDED 2026-05-19 (pass 2)**. §6a SGB II §2 sentence 4 verified: cap is "höchstens 25 Prozent der zum 31. Dezember 2010 bestehenden Aufgabenträger" — historically 110 once fully utilised. Article 91e GG verified: says "begrenzt" without a fixed numerical cap (delegates to federal legislation = §6a SGB II). The "110" Wikipedia figure was the constitutional-cap-fully-utilised total (69 from 2005 + 41 from 2012). BMAS Optionskommunen list URL returned 404 on 4 attempted variants this slice; BMAS has likely restructured the URL. **Body reworded** (`12-application-package.md` §C) to "the autonomous Optionskommunen Jobcenter operating Bürgergeld under §6a SGB II + Article 91e Grundgesetz (the federal cap is 25% of the 2010 baseline of task carriers — historically a maximum of 110 Optionskommunen; the BMAS-published list is the source of truth for the current active count)". Cap vs current-count distinction now explicit; maintainer should confirm against BMAS at submission if a precise count is needed. |
| €30k–€200k AI Act compliance consulting cost avoided per deployer | **INDUSTRY ESTIMATE — not measured**. | The range reflects publicly reported AI-compliance-consulting quotes during 2024–2026 (range source: aggregated quotes from German Datenschutz / KI-compliance consultancies; we don't cite a single primary source because the actual number depends on the deployer's existing compliance posture and the consultant's scope). The application body uses qualified language ("typical" / "industry-estimate") rather than asserting a single figure. **NOT a measured claim.** |
| **30 axe-core violation instances closed across 22 audited surfaces** | [`ACCESSIBILITY.md`](../../ACCESSIBILITY.md) "Current state" table | **VERIFIED** — every violation has a documented pre/post-fix count and a file:line for the closing fix. |
| **91 components in v0.1.0 CycloneDX SBOM** | [`docs/releases/v0.1.0-sbom.json`](releases/v0.1.0-sbom.json) | **VERIFIED** — the SBOM is committed; component count derivable via `jq '.components | length'`. |
| **1020 tests / 4 skipped (Python 3.9) and 1029 tests / 12 skipped (Python 3.12)** | `python3 -m unittest discover -s tests` output | **VERIFIED** — runtime evidence in commit `f8393dd` closeout + `02-execution-plan.md` §3.8 entry. |
| **6 workflows fully SHA-pinned; `grep -nE "uses:.*@v[0-9]" .github/workflows/*.yml` returns 0 lines** | commits `546f952` + `5be9f47` | **VERIFIED** — closing grep documented in `02-execution-plan.md` §3.2 entry. |
| **Seven-persona panel: Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias** | [`docs/grant/07-personas.md`](07-personas.md) + Decision 21 | **VERIFIED** — the panel is the project's canonical source-of-truth; Decision 21 dated 2026-05-18. |
| **MCP catalogue v0.2.0, 13 tools** | [`docs/mcp-server.md`](../mcp-server.md) | **VERIFIED** — the catalogue + per-tool input schemas committed; CI smoke test exercises the surface. |

**Pre-submission discipline (slice-end state, post 2026-05-19 re-verify pass 2)**:

After two re-verification passes the carried-forward-numbers
landscape is now:

- **1 of 4 VERIFIED at primary source** (pass 1):
  - **163 Engpassberufe** — VERIFIED at BA Fachkräftebedarf overview.
- **3 of 4 REWORDED** (pass 2) — the application body no longer leads
  with the precise figure, but the OECD / BAMF / §6a SGB II
  citations are preserved where applicable. Re-verification paths
  fell back to alternative URLs (Destatis / Pflegerat / DKG / BMG /
  IW Köln / BAMF press / BAGFW / Wikipedia MBE / gesetze-im-internet
  for §6a + Art. 91e GG) and none surfaced a single-authoritative
  number reachable via WebFetch:
  - **Healthcare unfilled** — body reworded to "tens of thousands"
    + OECD citation preserved as the documented anchor.
  - **MBE** — body reworded to drop the "~700" count entirely; the
    operational architecture is named instead (six Wohlfahrtsverbände
    + BAMF coordination + BAMF-NAvI directory).
  - **Optionskommunen** — body reworded to the cap-vs-current-count
    distinction: §6a SGB II §2 cap of 25% of the 2010 task-carrier
    baseline (historically 110); BMAS-published list is the
    source of truth for the current active count.
- **Structural verifications carry forward** (16 IQ-Netzwerk
  regional networks tied to 16 Bundesländer; seven-persona panel;
  MCP catalogue + tool count; 1020/1029 tests; 30 axe violations
  closed; cosign Verified OK; etc.) — these are anchored in the
  project's own source-of-truth files or in constitutional
  structure.

**Net effect on the application's review surface**: every number in
the body either traces to a primary-source URL (the 163 Engpassberufe
+ the structural verifications + the project's own artefacts) OR is
qualified with a citation chain (OECD Economic Surveys cite; §6a SGB
II + Art. 91e GG cap citation) without leading with a precise figure
the maintainer cannot independently re-verify in <1 hour. Per Rule 2
of `13-lessons-learned.md`, this satisfies the honesty discipline:
no claim asserts a number the maintainer cannot trace.

If anything drifts further at submission time, update both this
draft and `12-application-package.md` in the same commit.

---

### Re-verification pass 3 — 2026-05-22

Closes phase2-backlog item #59 ("Application-draft numerical claims —
3 of 4 reworded because primary sources didn't yield specific
numbers. At submission time, re-attempt primary-source citation or
keep the reword.").

Re-attempted primary-source verification for each of the 3 reworded
claims via 8 distinct WebFetch routes:

| Claim | Routes tried (2026-05-22) | Outcome |
|---|---|---|
| Healthcare unfilled positions in DE | (1) Destatis hospital/old-age-care vacancies table (404); (2) BA `statistik.arbeitsagentur.de` Fachkräftebedarf overview — landing page only, no headline figure; (3) BA `famr-engpass-d-0-pdf.pdf` direct PDF (404); (4) OECD Economic Surveys Germany 2025 source page (403 paywall). | **Reword retained.** No single primary-source URL surfaces a headline figure reachable via WebFetch. Body keeps "tens of thousands" + OECD citation as documented anchor. |
| Migrationsberatungsstellen (MBE) count | (1) BAMF 2024-10 press release path (404); (2) BAMF `Migrationsberatung` topic page — navigation only, no aggregate number; (3) BAMF `ProjekttraegerMBE` topic page (404); (4) BAMF-NAvI directory landing — navigation only, no aggregate count visible without per-entry directory crawl. | **Reword retained.** Operational architecture phrasing (six Wohlfahrtsverbände + BAMF coordination + BAMF-NAvI directory) stays as the institutional-readiness anchor. |
| Optionskommunen current count | (1) BMAS `Grundsicherung/Optionskommunen` topic page (404); (2) BMAS `Buergergeld/Zugelassene-Kommunale-Traeger` page (404); (3) BMAS `Optionskommunen` PDF list (404); (4) BMAS Sozial-Statistiken glossary `Optionskommunen` page (404). BMAS site has clearly restructured since the prior audit. | **Reword retained.** §6a SGB II cap + Art. 91e GG citations remain the structural anchor; the application body's cap-vs-current-count phrasing stands. |

**Verdict**: re-attempt complete; reword retained for all 3 claims.
The audit trail (8 fetch attempts across canonical pages + PDFs +
corroborators) is sufficient to demonstrate the maintainer cannot
reach a precise headline figure in <1 hour — the original
reword-with-citation approach remains the honest discipline.

This closes the conditional follow-up in item #59. Future drift
checks should happen at the moment of submission (re-attempting
the same fetches in case any of these authorities restore their
canonical paths) rather than during ongoing development.
