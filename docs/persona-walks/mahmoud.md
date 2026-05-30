<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Persona walk — Mahmoud (Syria → Hamburg)

**Persona slug**: `mahmoud`
**Cohort**: most-acute migrant (primary anchor)
**Residency status**: §4 AsylG Subsidiärer Schutz (subsidiary protection holder)
**Friction notes**: trade apprenticeship pathway (Ausbildung) rather than direct hire; HVAC + plumbing background pre-flight; technical German is conversational (workshop-floor B2) but admin-form German remains the recurring blocker.
**Languages**: AR (native), DE (B2 trades-context; B1 admin-form-context)
**Profession + target roles**: Pre-flight HVAC/plumbing background; targets `Sanitär-Heizung-Klima Auszubildender / Anlagenmechaniker SHK Ausbildung / Quereinsteiger SHK` in Hamburg.

**Source-of-truth**: `company_discovery.persona_fixtures.PERSONAS[3]`. Date: 2026-05-24. Version: HEAD of `main`.

---

## 1. Sign-up + onboarding

Mahmoud arrives via a Beratungsstelle referral — the discover phase needs to recognise that he's seeking an Ausbildung path, not a direct hire. The journey accommodates this: when the persona-fit classifier sees `Trade apprentice` + `Subsidiärer Schutz` + workshop-context German, it surfaces Ausbildung-friendly employers + Berufsschule-aligned scheduling. Detailed transcript: [`docs/grant/journey-walks-2026-05-20/mahmoud.md`](../grant/journey-walks-2026-05-20/mahmoud.md) (487 lines).

The Ausbildung filter is critical: a direct-hire Anlagenmechaniker role expects an existing Geselle / Meister certificate; an Ausbildung role accepts foundational competence + motivation. The `SCORE_FRICTION_FIT` criterion's entry-level / training-program calibration (per `build_auto_fit_prompt`'s anchor scale) recognises this distinction.

## 2. CV preparation

The CV format pivots: rather than a chronological work-history CV, Mahmoud's CV emphasises Praktikum + workshop experience + completed German integration course (with the BAMF certificate as an attached anchor). The cv_summary names the §4 AsylG status and the pre-flight workshop background; the cv_text references skills (`Werkstattorganisation`, `Material handling`, `Customer interaction in trade context`) translated into German trade-school terminology.

## 3. Job matching

Hamburg HVAC + plumbing Ausbildung positions are pre-seeded. The search prioritises:
- Employers with documented Quereinsteiger / Geflüchtete onboarding programmes
- Roles within Berufsschule-commutable distance (Hamburg has 3 SHK Berufsschulen)
- IHK-recognised Ausbildung-providers (eliminates roles that wouldn't lead to a recognised certificate)

The bias-comparative-report verified `mahmoud + ausbildung_shk_hamburg` at SCORE 90 (deepseek) / 73 (ollama), a 17-point cross-provider spread: deepseek clears the 75 verification gate, ollama falls just below it.

## 4. Cover-letter drafting

The Anschreiben explicitly addresses the §4 status (Subsidiärer Schutz → work-permit granted at the same legal class as German citizens for Ausbildung) so the employer doesn't have to research the status themselves. The 2026-05-20 anschreiben walk at [`docs/grant/anschreiben-quality-walks-2026-05-20/mahmoud.md`](../grant/anschreiben-quality-walks-2026-05-20/mahmoud.md) documents the trade-context framing.

The letter also names the Berufsschule attendance commitment plainly so the employer knows the apprentice's weekly rhythm is school + workshop, not 5-day full workshop.

## 5. Application tracked

Mark-applied + the Ausbildung-start-date calendar (most Ausbildung positions start 1 August or 1 September). Follow-up reminders pace against the Berufsschule application deadline (different per Bundesland).

## 6. What felt broken (residual roughness)

- **Ausbildung-aware filter** is JD-keyword-based ("Ausbildung", "Auszubildender", "Quereinsteiger willkommen"). JDs that bury the Ausbildung framing in body text rather than the title slip past. Tracked for Section 2.8.
- **Berufsschule pairing** — the employer + Berufsschule combination is critical (the apprentice attends both); the system doesn't yet surface which Berufsschulen each employer's Ausbildung programme is paired with.
- **IHK certificate-recognition path** — the eventual Geselle exam is administered by the IHK; the system doesn't yet surface the exam window or the prerequisite documentation. Section 2.6 deliverable.
- **Pre-Ausbildung integration courses** — many Hamburg HVAC employers want EQ (Einstiegsqualifizierung) before a full Ausbildung; the EQ pathway is not surfaced.

---

## Cross-references

- Detailed journey transcript: [`docs/grant/journey-walks-2026-05-20/mahmoud.md`](../grant/journey-walks-2026-05-20/mahmoud.md) (487 lines)
- Anschreiben quality walk: [`docs/grant/anschreiben-quality-walks-2026-05-20/mahmoud.md`](../grant/anschreiben-quality-walks-2026-05-20/mahmoud.md)
- Bias-comparative-report (Mahmoud row): [`docs/grant/bias-comparative-report-2026-05-21.md`](../grant/bias-comparative-report-2026-05-21.md)
- Persona fixture: [`company_discovery/persona_fixtures.py::PERSONAS[3]`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/persona_fixtures.py)
- Demo account: `persona-mahmoud@demo.helpmefindthejob.org`
