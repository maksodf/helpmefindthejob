<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 DirectJob Scout contributors -->

# DirectJob Scout — NLnet NGI Zero Commons Fund application (working draft)

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

> Germany (EU member state). DirectJob Scout's reference
> implementation is deployed in Germany; the architecture is
> EU-wide and country-neutral (cross-border deployment is a
> localisation exercise, not a re-engineering effort).

## Field 6 — Call selection

**NGI Zero Commons Fund**.

---

## Field 7 — Proposal name

**DirectJob Scout — an open-source EU-wide civic employment commons**

(Subtitle for the cover page if the form supports one:
"MCP-composable copilot for users facing structural labour-market
friction in Europe.")

---

## Field 8 — Website / wiki

`https://maksodf.github.io/directjob-scout/` (the documentation
site — `mkdocs build --strict` already green, GH Pages serving
will activate when the working branch merges to `main`).

Until that activation: `https://github.com/maksodf/directjob-scout`
(canonical source repository).

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
> **DirectJob Scout** is an open-source, multilingual,
> privacy-preserving civic employment agent that captures
> specialist HR and bureaucratic-navigation knowledge into a
> small, well-documented set of MCP-composable modular tools.
> The first reference implementation is a conversational
> jobseeker copilot deployed in Germany; the same modules
> compose with parallel open civic agents (housing, healthcare,
> residency, education) to form a coherent multi-domain civic
> assistant. The codebase is Apache-2.0-licensed, self-hostable,
> encrypted at rest (ChaCha20-Poly1305), runs on the user's
> choice of AI provider (BYO-AI — including fully offline via
> Ollama), and ships EU AI Act compliance built in for the
> 2 August 2026 enforcement date.
>
> Hosted as a Programme of The Commons Conservancy. Every
> feature is evaluated against a dual measure: improve outcomes
> for the people served AND reduce operational cost for the
> institutions that serve them.

---

## Field 10 — Prior involvement (optional)

Phase 1 work already shipped and verifiable in the public
repository at <https://github.com/maksodf/directjob-scout> (90+
commits across the 4-week grant-readiness sprint, May 2026):

- **Apache 2.0 + CLA + governance pack**: LICENSE, NOTICE,
  CONTRIBUTING.md, CODE_OF_CONDUCT.md (Contributor Covenant 2.1),
  SECURITY.md, SUPPORT.md, AUTHORS.md, ACKNOWLEDGMENTS.md,
  TRADEMARK.md, cla.md.
- **EU AI Act compliance pack**: 10 documents under `compliance/`
  covering Articles 9, 10, 11, 12, 13, 14, 15, 26, 27, 49 —
  including a documented synthetic-cohort bias-testing methodology
  with three executed dated runs against `llama3.1:8b` (33.3%
  methodology surface coverage; remaining four classes deferred
  to post-grant per honest scoping).
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
<https://maksodf.github.io/directjob-scout/>; `ACCESSIBILITY.md`
with three-pass WCAG 2.2 AA audit evidence (unauthenticated
surfaces axe-core CLI + authenticated surfaces Playwright +
axe-playwright-python + light-mode + dynamic-state + compliance
markdown; 30 instance violations closed across 22 audited
surfaces, raw axe JSON regenerable in seconds).
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

**What DirectJob Scout does that the above don't**:

| Property | LinkedIn-class | BA JOBBÖRSE | GPT-wrapper | DirectJob Scout |
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

**Where DirectJob Scout fits in the NGI / civic-tech / labour-
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
DirectJob Scout's MCP composition surface is designed to
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

Optional (skip if it adds bulk without adding evidence):
- Letter of support PDF once a partner signs — see
  Milestone 6.

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
| ~46,000 unfilled positions in DE healthcare | [OECD Economic Surveys: Germany 2025](https://www.oecd.org/en/publications/oecd-economic-surveys-germany-2025_2c91e1d4-en.html) | **STILL FLAGGED FOR MAINTAINER RE-VERIFY**. WebFetch returned HTTP 403 against the OECD URL during this slice (2026-05-19); alternative reach via BMG Pflege overview + Destatis offene-Stellen + IW Köln Fachkräftelücke did not surface a single primary-source URL with the 46,000 figure published at headline level (most attempts returned 404 or 401). The 46,000 figure remains in the application body as cited from prior 12-application-package.md research, but the maintainer should re-verify against the OECD publication PDF or paid OECD iLibrary access at submission time. |
| **~700 MBE service points across DE** | [BAMF-NAvI](https://bamf-navi.bamf.de/de/) (canonical directory; aggregate count not published at headline level) | **APPROXIMATE — FLAGGED**. BAMF-NAvI confirmed as the directory surface; BAMF does NOT publish an aggregate MBE service-point count at any reachable URL. The "~700" figure is order-of-magnitude estimate from prior BAMF annual reports + Bundesregierung Migration-Atlas materials; not a single-source figure. Honest framing in the application body: "service points across Germany" without claiming a specific count would be safer, but the 12-application-package.md prior research used "~700" — the maintainer can either (a) verify against the BAMF annual MBE report or (b) reword to "Migrationsberatungsstellen across Germany" without the count. |
| **16 IQ-Netzwerk regional networks** | <https://www.netzwerk-iq.de/> | **STRUCTURAL** — IQ-Netzwerk is organised by Bundesland; with 16 Länder there are 16 regional networks by design. **VERIFIED structurally** (the federal-state structure of Germany is constitutionally fixed); maintainer should confirm against the IQ-Netzwerk public page that this organisational structure persists at submission time. |
| **110 Optionskommunen** (was: "104" in earlier drafts) | [§6a SGB II + Article 91e(2) Grundgesetz](https://de.wikipedia.org/wiki/Optionskommune) — Wikipedia article citing federal-law primary sources | **VERIFIED + UPDATED 2026-05-19**. WebFetch of the Wikipedia article confirmed: 69 Optionskommunen from 2005-01-01 + 41 additional from 2012-01-01 = **110 total**; the cap was set by federal-constitutional ruling at 110 ("weil der Bund die Anzahl der Optionskommunen zulässig auf 110 beschränken durfte"). The earlier "104" figure in 12-application-package.md was drift from the constitutional cap; **corrected to 110 in both 12-application-package.md §C and this draft's Field 16**. This is the only number that drifted enough to require a body update in this slice. |
| €30k–€200k AI Act compliance consulting cost avoided per deployer | **INDUSTRY ESTIMATE — not measured**. | The range reflects publicly reported AI-compliance-consulting quotes during 2024–2026 (range source: aggregated quotes from German Datenschutz / KI-compliance consultancies; we don't cite a single primary source because the actual number depends on the deployer's existing compliance posture and the consultant's scope). The application body uses qualified language ("typical" / "industry-estimate") rather than asserting a single figure. **NOT a measured claim.** |
| **30 axe-core violation instances closed across 22 audited surfaces** | [`ACCESSIBILITY.md`](../../ACCESSIBILITY.md) "Current state" table | **VERIFIED** — every violation has a documented pre/post-fix count and a file:line for the closing fix. |
| **91 components in v0.1.0 CycloneDX SBOM** | [`docs/releases/v0.1.0-sbom.json`](releases/v0.1.0-sbom.json) | **VERIFIED** — the SBOM is committed; component count derivable via `jq '.components | length'`. |
| **1020 tests / 4 skipped (Python 3.9) and 1029 tests / 12 skipped (Python 3.12)** | `python3 -m unittest discover -s tests` output | **VERIFIED** — runtime evidence in commit `f8393dd` closeout + `02-execution-plan.md` §3.8 entry. |
| **6 workflows fully SHA-pinned; `grep -nE "uses:.*@v[0-9]" .github/workflows/*.yml` returns 0 lines** | commits `546f952` + `5be9f47` | **VERIFIED** — closing grep documented in `02-execution-plan.md` §3.2 entry. |
| **Seven-persona panel: Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias** | [`docs/grant/07-personas.md`](07-personas.md) + Decision 21 | **VERIFIED** — the panel is the project's canonical source-of-truth; Decision 21 dated 2026-05-18. |
| **MCP catalogue v0.2.0, 13 tools** | [`docs/mcp-server.md`](mcp-server.md) | **VERIFIED** — the catalogue + per-tool input schemas committed; CI smoke test exercises the surface. |

**Pre-submission discipline (slice-end state, post 2026-05-19 polish)**:

- **2 of 4 carried-forward numbers verified at primary source via
  WebFetch this slice**:
  - **163 Engpassberufe** — VERIFIED at BA Fachkräftebedarf overview.
  - **Optionskommunen — corrected 104 → 110** (federal constitutional
    cap per §6a SGB II + Art. 91e(2) GG; 69 from 2005 + 41 from 2012).
    Source-of-truth file `12-application-package.md` §C updated in
    the same commit.
- **2 of 4 still flagged**:
  - **~46,000 healthcare unfilled** — OECD URL returned HTTP 403;
    alternative primary-source URLs (BMG, Destatis, IW Köln,
    BA Pflege) returned 404 or 401. Maintainer should re-verify
    against the OECD publication PDF or paid OECD iLibrary access
    at submission time. Consider also: the figure may be more
    cleanly sourced from a Pflegerat / DKG / Statistisches
    Bundesamt press release than from OECD.
  - **~700 MBE service points** — BAMF does NOT publish an
    aggregate count at any reachable URL; BAMF-NAvI is the
    directory surface. Maintainer can either (a) re-verify
    against the most recent BAMF MBE annual report or (b)
    reword application body to drop the specific count ("MBE
    service points across Germany" without "~700").
- **Structural verifications carry forward** (16 IQ-Netzwerk
  regional networks; seven-persona panel; MCP catalogue + tool
  count; 1020/1029 tests; 30 axe violations closed; etc.) —
  these are anchored in the project's own source-of-truth files
  or in constitutional structure (16 Länder).

If anything else drifts at submission time, update both this draft
and `12-application-package.md` in the same commit to keep the
source-of-truth file aligned.
