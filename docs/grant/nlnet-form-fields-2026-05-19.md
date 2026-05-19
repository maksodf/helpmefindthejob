<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# NLnet NGI Zero Commons Fund — application form structure

**Verified**: 2026-05-19 via direct fetch of:
- <https://nlnet.nl/propose/> (the canonical proposal form)
- <https://nlnet.nl/commonsfund/> (the call page)
- <https://nlnet.nl/commonsfund/guideforapplicants> (assessment criteria)
- <https://nlnet.nl/commonsfund/faq/> (rules + services)

**Closes**: [Open R3](04-research-and-decisions.md) in
`04-research-and-decisions.md` Part C.

---

## Call metadata

| Field | Value |
|---|---|
| Call name | NGI Zero Commons Fund — 13th call |
| Call window | Opened 2026-04-01 |
| Submission deadline | **2026-06-01 12:00 CEST** (12 calendar days from today, 2026-05-19) |
| Funding band | **€5,000 – €50,000** (first proposal) |
| Subsequent proposal cap | €150,000 |
| Lifetime cap per third party | €500,000 |
| Decision turnaround | 3–5 months from the deadline |
| Programme end | 2027-06 (NGI0 Commons Fund) |
| Default project duration | 12 months (negotiable) |
| F&A overhead cap | 25% (exceptional cases only; generally not eligible) |
| Assessment criteria (weight) | Technical excellence/feasibility 30% · Relevance/Impact/Strategic potential 40% · Cost effectiveness/Value for money 30% |
| Pass threshold | 5.0 / 7.0 weighted total |
| Genealogy | If first proposal scores below threshold, applicant can resubmit in the next bimonthly cycle |

---

## Form fields (canonical structure at nlnet.nl/propose)

### Contact section

| # | Field | Type | Required | Limit | Guidance |
|---|---|---|---|---|---|
| 1 | Your name | text | yes | — | Applicant's name (real name required post-acceptance; alias acceptable pre-acceptance) |
| 2 | Email address | text | yes | — | Reply-to |
| 3 | Phone number | text | no | — | Optional |
| 4 | Organisation | text | no | — | Legal entity not required; individuals, informal groups, and unincorporated collectives are all eligible |
| 5 | Country | text | no | — | European dimension required (either European contributors OR substantial NGI-vision contribution) |

### Call selection

| # | Field | Type | Required | Options |
|---|---|---|---|---|
| 6 | Please select a call | dropdown | yes | "NGI Zero Commons Fund" / "NGI TALER" / "NGI Fediversity" / "Research & Higher Education Technology Fund" / "Open Call" / "Other" |

Helpmefindthejob selects **"NGI Zero Commons Fund"**.

### Project body

| # | Field | Type | Required | Limit | Guidance |
|---|---|---|---|---|---|
| 7 | Proposal name | text | yes | — | Concise title |
| 8 | Website / wiki | text | no | — | The project's canonical URL (we cite `https://maksodf.github.io/helpmefindthejob/` once Pages is live; until then, the GitHub repo URL) |
| 9 | **Abstract** | textarea | yes | not enforced (NLnet recommends ~200 words) | "Explain the whole project and its expected outcome(s)" |
| 10 | Prior involvement | textarea | no | — | Previous relevant projects or contributions by the applicant |
| 11 | **Requested Amount** (€) | numeric | yes | 5,000 – 50,000 (first proposal) | Whole euros |
| 12 | **Budget usage explanation** | textarea | yes | not enforced | Per-milestone breakdown of how the money is spent |
| 13 | Other funding sources | textarea | no | — | Co-funders, in-kind contributions, prior grants |
| 14 | **Project comparison** | textarea | yes | not enforced | Differentiation from existing projects — what we do that incumbents don't |
| 15 | Technical challenges | textarea | no | — | Hard problems anticipated |
| 16 | **Ecosystem description** | textarea | yes | not enforced | Where Helpmefindthejob fits in the NGI / civic-tech / labour-market ecosystem; what we build on, what we compose with |

### Attachments

| # | Field | Type | Required | Limit |
|---|---|---|---|---|
| 17 | Attachments | file upload | no | 50 MB total; HTML / PDF / OpenDocument / plain text |

### Generative-AI disclosure

| # | Field | Type | Required | Limit | Guidance |
|---|---|---|---|---|---|
| 18 | GenAI usage | dropdown | no | — | "I did not use generative AI…" / "I have used generative AI…" — **disclose honestly**; failure to disclose results in rejection per the FAQ |
| 19 | Model details | textarea | conditional | — | Required if applicant selected "I have used"; describe model + role in drafting |
| 20 | AI prompt files | file upload | no | 50 MB | Optional; transparency artefact |

### Privacy

| # | Field | Type | Required | |
|---|---|---|---|---|
| 21 | Privacy acknowledgment | checkbox | yes | Per NLnet's privacy policy |
| 22 | Send copy | checkbox | no | Email a copy of the submission to the applicant |

---

## Fund-specific notes (NGI Zero Commons Fund)

The `/propose` form does not branch fund-specific questions at the
field level — the same 22 fields apply to every NLnet call. **The
NGI Zero Commons Fund context** (selected via Field 6) shapes how
the abstract / project comparison / ecosystem description are
interpreted by reviewers:

- **Commons-aligned framing**: the project's value as a digital
  commons (Apache 2.0, Conservancy wrapper, self-hostable, no
  vendor lock-in) is a primary review axis under
  "Relevance/Impact/Strategic potential" (40% weight).
- **European dimension**: required. Helpmefindthejob's
  EU-wide-civic-employment positioning + DE-first reference
  deployment + Conservancy-stichting host directly satisfies.
- **Standards interop**: NLnet's Commons Fund values projects
  that compose via open standards. Our MCP catalogue + ESCO +
  EURES + schema.org JobPosting + WCAG 2.2 AA stack is the
  evidence.
- **Privacy + trust**: BYO-AI architecture + ChaCha20-Poly1305
  AEAD at rest + EU AI Act compliance pack + RFC 9116
  security.txt + cosign-signed releases all map to NLnet's
  Next-Generation-Internet vision.

---

## NLnet support services available to grantees

Per the FAQ, NLnet offers these **non-monetary** services we can
request as part of the grant relationship:

| Service | Provider | Phase 1 relevance for Helpmefindthejob |
|---|---|---|
| **Accessibility audit** | HAN University of Applied Sciences | Manual keyboard + screen-reader review beyond the axe-core automated baseline shipped in `ACCESSIBILITY.md`. Anticipated as a Phase 2 service after Conservancy admission lands. |
| **Security audit** | NLnet's partner network | Out of scope for first €5k–€50k grant (security audits typically engage at the >€50k subsequent-proposal tier). |
| **Licensing advice** | NLnet legal mentors | Apache 2.0 + CLA is settled per Decision 1; would consult if a relicensing decision ever surfaces. |
| **Packaging** | NixOS Foundation | The flake.nix is Phase 1's reproducibility-build evidence; future pure-Nix `buildPythonApplication` packaging is a Phase 2 candidate that NixOS Foundation support could accelerate. |
| **Mentoring** | NLnet network | Useful for AI Act compliance updates as the August 2026 enforcement date approaches + post-enforcement clarifications. |
| **Localization** | NLnet network | Relevant for Arabic / Ukrainian / Turkish / Romanian locale-bundle rollout (Decision 6 + Decision 21 friction-class architecture). |
| **Community building** | NLnet network | Helpful for activating the GitHub Sponsors + Open Collective channels per `SUSTAINABILITY.md` once we are past the Decision 17 pre-launch posture. |
| **Responsible-disclosure guidance** | NLnet network | SECURITY.md + RFC 9116 `security.txt` are the contracts; ongoing operator-side response is where mentoring would help. |

Helpmefindthejob's application package explicitly names
**accessibility audit (HAN University) + mentoring on AI Act
compliance + packaging (NixOS Foundation)** as the three Phase 1
services we intend to use. Security audit deferred to Phase 2.

---

## What makes a strong application (per the Guide for Applicants)

NLnet's per-criterion weighting:

1. **Relevance / Impact / Strategic potential — 40%**.
   Highest-weight criterion. Reviewers ask: does this advance the
   NGI vision? Does the project serve real users? Is the
   strategic dimension (commons-architecture, friction-class
   addressable population, EU AI Act-aligned compliance posture)
   clearly defensible?
2. **Technical excellence / feasibility — 30%**. Reviewers ask:
   is the team capable of executing? Are the milestones credible?
   Is the architecture well-thought-through?
3. **Cost effectiveness / Value for money — 30%**. Reviewers ask:
   is the budget defensible per milestone? Could the same outcome
   come at lower cost? Is the project's value-per-euro competitive?

**Pass threshold**: 5.0 / 7.0 weighted total. Below 5.0 → next
cycle resubmission encouraged.

**Second-stage review** (after pass): reviewers may ask follow-up
questions about differentiation, claim validation, sustainability,
upstream alignment, and rate justification. The application body
should pre-answer the obvious ones.

---

## Status of Open R3

**Status**: ANSWERED (2026-05-19) by this document. The form
structure was previously documented at a less granular level in
[`12-application-package.md`](12-application-package.md); this
document is the canonical per-field map used to author the
working draft.

**Next step**: per `02-execution-plan.md` §4.4 sub-task 2, adapt
the existing application-package content into one section per
form field — see
[`application-draft-2026-05-19.md`](application-draft-2026-05-19.md).
