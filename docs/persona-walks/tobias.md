<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Persona walk — Tobias (Berlin, long-term unemployed career changer)

**Persona slug**: `tobias`
**Cohort**: wider friction-class (architectural demonstration per Decision 21)
**Residency status**: EU citizen (German national); residency unproblematic
**Friction notes**: 14 months out of work after a B2B SaaS startup folded; pivoting from commercial product / growth to public-sector civic-tech (TVöD-paid) work; the unemployment-gap is the visible CV scar, but the actual friction is the language-and-format gap between Berlin startup CV conventions and TVöD-aware civic-tech employer conventions.
**Languages**: DE (native), EN (C1)
**Profession + target roles**: Senior product / growth (10 years; mid + senior IC + tech-lead); targets `Senior product manager / Innovation manager / Digitalisierungsbeauftragter / Civic-tech product lead` in Berlin public sector + civic-tech startups.

**Source-of-truth**: `company_discovery.persona_fixtures.PERSONAS[6]`. Date: 2026-05-24. Version: HEAD of `main`.

---

## 1. Sign-up + onboarding

Tobias arrives via word-of-mouth from a civic-tech community Slack. The journey's discover phase captures the dual-track ambition: TVöD-aware civic-tech roles AND startup-style civic-tech roles that pay TVöD-equivalent. Detailed transcript: [`docs/grant/journey-walks-2026-05-20/tobias.md`](../grant/journey-walks-2026-05-20/tobias.md) (587 lines — the most thorough of the seven).

The persona-fit classifier recognises EU-citizen + 14-month-gap + native-DE + senior-IC profile → long-term-unemployment-recovery + career-pivot pathway. The friction-class lens surfaces civic-tech employers + TVöD-aware language framing rather than pure-commercial growth-PM roles.

## 2. CV preparation

The CV's challenge is dual: the gap (a CV scar) AND the format pivot (Berlin startup CV reads as foreign in TVöD-aware procurement processes). The cv_builder walks Tobias through:
- Honest gap-explanation (the startup folded; he chose to take time to reflect on next-chapter rather than jump to the nearest growth-PM role)
- Civic-tech context translation (B2B SaaS "growth" reframes as "user-research-driven product-market-fit work"; "metrics-driven" reframes as "outcome-evidence work")
- TVöD-aware framing (E13 / E14 grade alignment, public-sector procurement-cycle awareness, GG / SGB knowledge)

The cv_summary names the pivot intentionally: "Senior product professional pivoting commercial → civic-tech after a startup-end transition window. Evidence-of-ROI orientation, TVöD-grade-aware, fluent in both commercial OKR metrics and public-sector evaluation frameworks."

## 3. Job matching

Berlin civic-tech + public-sector employers pre-seeded (CityLAB Berlin, Senatskanzlei Berlin digital, BBSR DLZ-IT, Bundesdruckerei innovation, Code for Germany alumni network …). The search prioritises:
- Roles whose JD language explicitly signals openness to non-linear careers ("Quereinsteiger", "career changer welcome", "diverse Hintergründe willkommen")
- Civic-tech employers with documented Wiedereinstiegs / career-change tracks
- TVöD-aware roles within Berlin commute belt

The bias-comparative-report shows Tobias at mean SCORE 74.3 (deepseek) / 67.0 (ollama) — second-highest of the cohort, reflecting good architectural fit for the role-language-alignment work.

## 4. Cover-letter drafting

The Anschreiben proactively addresses both the gap and the pivot. The 2026-05-20 anschreiben walk at [`docs/grant/anschreiben-quality-walks-2026-05-20/tobias.md`](../grant/anschreiben-quality-walks-2026-05-20/tobias.md) documents the evidence-of-ROI framing for non-linear careers.

The letter scaffolding pivots to:
- A single sentence on the gap (honest, brief, not apologetic)
- Two paragraphs on the career-pivot rationale (why civic-tech now, what the transferable skills are)
- A specific named-project paragraph (where Tobias names a TVöD-equivalent civic-tech project he's worked on as a volunteer to bridge the gap)
- A small-win first-week plan (what he'd ship in week 1 if hired — proves the pivot is operationally real)

## 5. Application tracked

Mark-applied + a parallel civic-tech-volunteer-project tracker (the volunteer projects double as live-portfolio evidence for the pivot). Optional follow-up reminders pace against the typical public-sector hiring window (often 3-6 months from posting to offer).

## 6. What felt broken (residual roughness)

- **TVöD-grade calibration** in the fit-score is keyword-aware ("E13", "E14", "TVöD") but doesn't model the actual pay-band → seniority alignment. A Tobias-fit E13 role might be salary-wrong for his level; a Tobias-fit E14 role might be over-asking against the civic-tech employer's actual hiring band.
- **Civic-tech employer dataset** is heavily Berlin-centric; scaling to Hamburg / Munich / Stuttgart civic-tech ecosystems requires additional seeding.
- **Gap-explanation prompt** assumes a single coherent gap reason; for some users the gap may have multiple overlapping reasons (startup fold + family caregiving + career reflection). The CV template currently encourages a single primary framing.
- **Public-sector procurement-cycle awareness** — the system doesn't yet surface which Bundesländer / Bundesländer-equivalent procurement windows align with Tobias's earliest-start preferences.

---

## Cross-references

- Detailed journey transcript: [`docs/grant/journey-walks-2026-05-20/tobias.md`](../grant/journey-walks-2026-05-20/tobias.md) (587 lines)
- Anschreiben quality walk: [`docs/grant/anschreiben-quality-walks-2026-05-20/tobias.md`](../grant/anschreiben-quality-walks-2026-05-20/tobias.md)
- Bias-comparative-report (Tobias row): [`docs/grant/bias-comparative-report-2026-05-21.md`](../grant/bias-comparative-report-2026-05-21.md)
- Persona fixture: [`company_discovery/persona_fixtures.py::PERSONAS[6]`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/persona_fixtures.py)
- Demo account: `persona-tobias@demo.helpmefindthejob.org`
