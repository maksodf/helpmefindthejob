<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Persona walk — Tobias (Hamburg, commercial → civic-tech pivot)

**Persona slug**: `tobias`
**Cohort**: wider friction-class (architectural demonstration)
**Residency status**: EU citizen (German national); residency unproblematic
**Friction notes**: pivoting from commercial fintech to public-sector / civic-tech (TVöD-paid) work; the friction is the language-and-format gap between commercial-tech CV conventions and TVöD-aware public-sector hiring conventions (pay grades, formal Bewerbungsmappen, civic-service vocabulary), not residency or credentials.
**Languages**: DE (native), EN (C1-business)
**Profession + target roles**: Senior backend developer (Python, Go, distributed systems), 11 years at a Hamburg fintech startup, led a team of four; targets `Backend developer / Software engineer (public sector) / Civic-tech engineer / Digitalisierung (öffentlicher Dienst)` in Hamburg + national public-sector / civic-tech.

**Source-of-truth**: `company_discovery.persona_fixtures.PERSONAS[6]`. Date: 2026-05-30. Version: HEAD of `main`.

---

## 1. Sign-up + onboarding

Tobias arrives via word-of-mouth from a civic-tech community. The journey's discover phase captures the dual-track ambition: TVöD-graded public-sector engineering roles AND civic-tech roles that pay TVöD-equivalent. Detailed transcript: [`docs/grant/journey-walks-2026-05-20/tobias.md`](../grant/journey-walks-2026-05-20/tobias.md) (587 lines — the most thorough of the seven).

The persona-fit classifier recognises EU-citizen + native-DE + senior-IC-engineer + commercial→civic intent → career-pivot pathway. The friction-class lens surfaces civic-tech / public-sector employers + TVöD-aware language framing rather than pure-commercial engineering roles.

## 2. CV preparation

The CV's challenge is the format pivot: a commercial-tech CV reads as foreign in TVöD-aware procurement processes. The cv_builder walks Tobias through:
- Civic-tech context translation (commercial backend impact reframes as public-good infrastructure delivery; "metrics-driven" reframes as "outcome-evidence work")
- TVöD-aware framing (E13 / E14 grade alignment, public-sector procurement-cycle awareness)
- Concrete impact translation ("led the migration of our payment-processing layer" → the language a public-sector hiring committee evaluates)

The cv_summary names the pivot intentionally: "Senior backend developer pivoting commercial → civic-tech; evidence-of-ROI orientation, TVöD-grade-aware, fluent in both commercial engineering practice and public-sector evaluation frameworks."

## 3. Job matching

Public-sector + civic-tech employers pre-seeded from the canonical landscape (GovTech Campus, Sovereign Tech Fund-affiliated projects, Code for Germany, Prototype Fund-adjacent organisations, federal IT roles, civic-NGO digital teams). The search prioritises:
- Roles whose JD language explicitly signals openness to non-linear careers ("Quereinsteiger", "career changer welcome", "diverse Hintergründe willkommen")
- Civic-tech / public-sector employers with documented career-change tracks
- TVöD-aware roles in Hamburg + remote-friendly national postings

The bias-comparative-report shows Tobias at mean SCORE 74.3 (deepseek) / 67.0 (ollama) — the highest of the cohort, reflecting good architectural fit for the role-language-alignment work.

## 4. Cover-letter drafting

The Anschreiben addresses the pivot directly. The 2026-05-20 anschreiben walk at [`docs/grant/anschreiben-quality-walks-2026-05-20/tobias.md`](../grant/anschreiben-quality-walks-2026-05-20/tobias.md) documents the evidence-of-ROI framing for non-linear careers.

The letter scaffolding pivots to:
- Two paragraphs on the career-pivot rationale (why civic-tech now, what the transferable engineering skills are)
- A specific named-project paragraph (where Tobias names a civic-tech project he's contributed to as a volunteer to evidence the pivot)
- A small-win first-week plan (what he'd ship in week 1 if hired — proves the pivot is operationally real)

## 5. Application tracked

Mark-applied + a parallel civic-tech-volunteer-project tracker (the volunteer projects double as live-portfolio evidence for the pivot). Optional follow-up reminders pace against the typical public-sector hiring window (often 3–6 months from posting to offer).

## 6. What felt broken (residual roughness)

- **TVöD-grade calibration** in the fit-score is keyword-aware ("E13", "E14", "TVöD") but doesn't model the actual pay-band → seniority alignment. A Tobias-fit E13 role might be salary-wrong for his level; a Tobias-fit E14 role might be over-asking against the civic-tech employer's actual hiring band.
- **Civic-tech employer dataset** leans toward federal / Berlin-based organisations (GovTech Campus, federal IT); scaling to Hamburg-local and other-Land civic-tech ecosystems requires additional seeding.
- **Pivot-narrative prompt** assumes a single coherent pivot rationale; for some users the transition may have multiple overlapping reasons. The CV template currently encourages a single primary framing.
- **Public-sector procurement-cycle awareness** — the system doesn't yet surface which agency procurement / hiring windows align with Tobias's earliest-start preferences.

---

## Cross-references

- Detailed journey transcript: [`docs/grant/journey-walks-2026-05-20/tobias.md`](../grant/journey-walks-2026-05-20/tobias.md) (587 lines)
- Anschreiben quality walk: [`docs/grant/anschreiben-quality-walks-2026-05-20/tobias.md`](../grant/anschreiben-quality-walks-2026-05-20/tobias.md)
- Bias-comparative-report (Tobias row): [`docs/grant/bias-comparative-report-2026-05-21.md`](../grant/bias-comparative-report-2026-05-21.md)
- Persona fixture: [`company_discovery/persona_fixtures.py::PERSONAS[6]`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/persona_fixtures.py)
- Demo account: `tobias@demo.helpmefindthejob.org`
