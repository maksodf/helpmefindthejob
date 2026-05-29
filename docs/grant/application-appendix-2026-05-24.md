<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

---
title: "Helpmefindthejob — NLnet NGI Zero Commons Fund Application Appendix"
subtitle: "Persona panel · MCP composition · Budget breakdown"
author: "Project maintainer (Fouad)"
date: "2026-05-24"
geometry: "margin=2cm"
papersize: a4
fontsize: 10pt
linkcolor: blue
---

# Helpmefindthejob — Application appendix (one page)

Optional Field 17 attachment.

## 1. Persona panel (Decision 21, seven personas)

The system is designed against seven concrete personas. The five most-acute migrant personas (rows 1–5) are the **primary narrative anchor** — every demo, screenshot, and proposal section names one of them first. The two wider friction-class personas (rows 6–7) demonstrate the architecture is friction-driven, not demographic-driven.

| # | Persona | Origin | Profession + Status | Lang. | Solves |
|---|---|---|---|---|---|
| 1 | Aïcha | Tunisia | Registered nurse, §16d Anerkennung | B1→B2 DE | Recognition-friendly employer matching + clinical-German CV |
| 2 | Yusuf | Turkey | Mechanical engineer, EU Blue Card pending | A2 DE | Post-arrival timeline + cross-city role comparison |
| 3 | Olga | Ukraine | Senior frontend dev, §24 protection | A2 DE | English-team / remote tech + residence explainer |
| 4 | Mahmoud | Syria | Trade apprentice, Subsidiärer Schutz | B2 DE | Ausbildung aggregation + Handwerk-format CV |
| 5 | Maria | Romania | Care worker, EU citizen | A2 DE | Language-tolerant Pflegedienst matching |
| 6 | Käthe | Germany | Returning nurse, 12-yr caregiving gap | Native DE | 12-year-gap CV reframing + Wiedereinstiegsprogramme matching |
| 7 | Tobias | Germany | Career changer, long-term unemployed | Native DE | Evidence-of-ROI cover-letter framing for non-linear careers |

Source-of-truth: `docs/grant/07-personas.md` + Decision 21 in `docs/grant/04-research-and-decisions.md`. Persona records encoded in `company_discovery/persona_fixtures.py` and consumed by both `tests/test_bias_methodology.py` (bias re-test) and `scripts/seed-personas.py` (demo deployment seed).

## 2. MCP composition diagram (Article 11 + Annex IV positioning)

```
                  ┌─────────────────────────────────────────────────────────┐
                  │       USER (job-seeker via chat-router interface)        │
                  └─────────────────────────────────────────────────────────┘
                                            │
                                            ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │             HELPMEFINDTHEJOB (this project)              │
                  │   chat_router · journey · cv_builder · analysis ·        │
                  │   aggregators (Adzuna · Indeed · LinkedIn public ·       │
                  │   EURES) · MCP server v0.2.0 (15-tool catalogue)         │
                  └─────────────────────────────────────────────────────────┘
                          │ MCP 2024-11-05    │ MCP 2024-11-05
                          ▼ (Option B)        ▼ (post-grant)
        ┌────────────────────────┐    ┌──────────────────────────────────┐
        │   Housing-search       │    │  Healthcare / Anerkennung /      │
        │   civic agent          │    │  Residency / Education civic     │
        │   (partner, Decision   │    │  agents (post-grant cohort —     │
        │    20 Option B path)   │    │  MCP surface = the invitation)   │
        └────────────────────────┘    └──────────────────────────────────┘
                          │                          │
                          ▼                          ▼
                  ┌────────────────────────────────────────────────────┐
                  │  COMPOSED CIVIC ASSISTANT (multi-domain handoffs)   │
                  │  e.g. job-match → housing handoff → credential      │
                  │  verification → language-course pairing             │
                  └────────────────────────────────────────────────────┘
```

Standards anchored: ESCO (occupations + skills), EURES (schema), schema.org/JobPosting, MCP 2024-11-05, JSON Schema 2020-12, WCAG 2.2 AA target, RFC 9116 security.txt, GDPR + EU AI Act Article 12 audit-log spec, Apache 2.0 licence + CLA.

## 3. Budget breakdown (€37,000 across 6 milestones)

| # | Milestone | Cost | Article(s) addressed | Status |
|---|---|---|---|---|
| 1 | Legal + governance pack (Apache 2.0, CLA, NOTICE, TRADEMARK, governance files) | €4,000 | Apache 2.0 + DCO + CC compliance | Shipped |
| 2 | MCP composition reference (15-tool catalogue + JSON schemas + CI test) | €8,000 | MCP 2024-11-05 | Shipped |
| 3 | EU AI Act compliance pack (14 documents in `compliance/`) | €10,000 | Art. 9 · 10 · 11+Annex IV · 12 · 13 · 14 · 15 · 22 · 26 · 27 · 49 · 50 · 73 · 86 + GDPR Art. 5 · 20 · 22 · 28 · 30 · 32 · 33 · 35 | Shipped (this slice 2026-05-24) |
| 4 | Public demo + accessibility (mkdocs site + WCAG 2.2 AA evidence + persona-seeded demo) | €6,000 | WCAG 2.2 AA + Article 49 EU AI database | Demo deployment in flight (DNS gated); accessibility evidence shipped |
| 5 | Reproducible builds + supply-chain (Nix flake + cosign + SBOM + Scorecard) | €5,000 | SLSA Level 2 (planned) + RFC 9116 | Shipped |
| 6 | Institutional readiness + standards interop (ESCO 30-occupation / 50-skill reference + EURES projection + ≥1 letter of support + Commons Conservancy admission) | €4,000 | Cross-references all of the above | Conservancy intake submitted (parallel track); outreach drafted, send-gate at submission window |
| **TOTAL** | | **€37,000** | (≤ €50,000 first-proposal cap; frugal-by-default per Decision 10) | |

Cost-saving doctrine: every milestone is evaluated against "does it reduce institutional operational cost while improving end-user outcomes?". The Milestone-3 compliance pack alone is documented to avoid €30,000–€200,000 of AI-Act-consulting cost per deployer (industry estimate; see verification table in the application body for the honest framing).

## 4. Cross-references

- Application body: `docs/grant/application-draft-2026-05-19.md` (22 of 22 fields filled)
- Verification table: same file, "Per-numerical-claim verification table" section
- Decisions log: `docs/grant/04-research-and-decisions.md` Part B
- Compliance INDEX: `compliance/INDEX.md`
- Risks the project acknowledges: same body, "Risks we acknowledge" section between Field 16 and Field 17
- Honest-state paragraph: `docs/grant/04-research-and-decisions.md` Part B "What we know is broken / not yet shipped (2026-05-24)"

This appendix is rendered into a PDF via:

```bash
pandoc docs/grant/application-appendix-2026-05-24.md \
  -o docs/grant/application-appendix-2026-05-24.pdf \
  --pdf-engine=xelatex \
  -V mainfont="Helvetica" \
  -V geometry:margin=2cm
```

If the operator's environment lacks `pandoc` / `xelatex`, the markdown source above is itself a usable reviewer artefact — every claim is hyperlinked into the repository structure.
