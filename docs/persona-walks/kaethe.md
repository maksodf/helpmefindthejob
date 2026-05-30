<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Persona walk — Käthe (Berlin, returner)

**Persona slug**: `kaethe`
**Cohort**: wider friction-class (architectural demonstration)
**Residency status**: EU citizen (German national); residency unproblematic
**Friction notes**: 12-year career gap from clinical nursing for childcare; certified pre-gap but the entire German nursing landscape has moved on (coding moved to ICD-10-GM, documentation moved from paper to KIS systems, medication-management ladders shifted, 2026-format CV conventions differ from 2013); needs Wiedereinstiegsprogramme that bridge the currency-gap without treating her as a junior.
**Languages**: DE (native), EN (B1, reads clinical literature)
**Profession + target roles**: Registered nurse pre-gap (Krankenschwester certified in Germany 1998; practiced on a Berlin cardiology ward 1999–2013); targets `Wiedereinsteigerin Pflegefachkraft / Krankenschwester Wiedereinstieg / Pflegefachfrau (Wiedereinsteigerin)` in Berlin.

**Source-of-truth**: `company_discovery.persona_fixtures.PERSONAS[5]`. Date: 2026-05-30. Version: HEAD of `main`.

---

## 1. Sign-up + onboarding

Käthe arrives via a Berlin Wohlfahrtsverband returner-network referral. Detailed transcript: [`docs/grant/journey-walks-2026-05-20/kaethe.md`](../grant/journey-walks-2026-05-20/kaethe.md) (485 lines).

The persona-fit classifier recognises EU-citizen + 12-year-gap + native German → Wiedereinsteigerin pathway. The journey's friction-class lens for Käthe surfaces employers with documented Wiedereinstiegsprogramme (mentor pairing, current-systems training, paid-orientation-week) rather than direct-hire roles that assume continuous practice.

## 2. CV preparation

The CV's central challenge: explaining the 12-year gap without it reading as a deficiency. The cv_builder's sectional interview prompts her on:
- Continued professional learning during the gap (relevant refresher courses, voluntary clinical hours, family-caregiving-as-clinical-skill maintenance)
- Skills that endured (clinical assessment, patient communication, organisational competence — none of these decay with 12 years of caregiving)
- Skills that need refresh (KIS-system documentation, current ICD-10-GM coding, post-2020 medication-management protocols)

The cv_summary frames the gap positively: "12-year primary-caregiving sabbatical concluded; intensive 2026 update via a Berlin Pflege-Auffrischungskurs; ready for clinical re-entry with paired-mentor onboarding."

## 3. Job matching

Berlin clinical employers with Wiedereinstiegs programmes pre-seeded (Charité, Vivantes, DRK Kliniken Berlin, Helios Klinikum Berlin-Buch, …). The search prioritises:
- Wiedereinstiegs-tagged roles (filter on `Wiedereinsteigerin` / `Wiedereinstiegspflege` / `Mentor-Programm`)
- Part-time / flexible-shift roles (childcare obligations persist)
- Roles within Berlin + commute belt

The bias-comparative-report shows Käthe at mean SCORE 70.0 (deepseek) / 67.4 (ollama) — the second-highest in the cohort (after Tobias at 74.3), reflecting that Wiedereinstiegs-pathways are well-matched by the friction-fit scale.

## 4. Cover-letter drafting

The Anschreiben proactively names the 12-year gap + the refresher-course completion + the readiness for paired-mentor onboarding. The 2026-05-20 anschreiben walk at [`docs/grant/anschreiben-quality-walks-2026-05-20/kaethe.md`](../grant/anschreiben-quality-walks-2026-05-20/kaethe.md) documents the gap-reframing language.

The tone is "confident professional returning to active practice", not "anxious applicant explaining away an absence". The prompt template steers explicitly against apologetic framing.

## 5. Application tracked

Mark-applied + the Auffrischungskurs completion-date countdown shown alongside each application. Optional follow-up reminders pace against the typical Pflege Wiedereinstiegs-onboarding induction calendar.

## 6. What felt broken (residual roughness)

- **Wiedereinstiegs-employer dataset** is hand-curated for Berlin; scaling beyond requires additional sources from regional Wohlfahrtsverbände returner networks.
- **Part-time-shift filtering** is a JD-keyword scan; many roles are advertised full-time but the employer is open to part-time if asked — the system doesn't yet surface "open to part-time conversation" cues.
- **Auffrischungskurs catalogue** — Käthe must source her refresher course herself; the credentials-currency module (Section 2.6) is the long-term home for this.
- **2026-format CV conventions** — the cv_builder uses a single CV template; persona-specific templates (e.g., a Wiedereinsteigerin-formatted CV emphasising the structured gap-explanation) are a Section 2.9 (advanced operator UX) deliverable.

---

## Cross-references

- Detailed journey transcript: [`docs/grant/journey-walks-2026-05-20/kaethe.md`](../grant/journey-walks-2026-05-20/kaethe.md) (485 lines)
- Anschreiben quality walk: [`docs/grant/anschreiben-quality-walks-2026-05-20/kaethe.md`](../grant/anschreiben-quality-walks-2026-05-20/kaethe.md)
- Bias-comparative-report (Käthe row): [`docs/grant/bias-comparative-report-2026-05-21.md`](../grant/bias-comparative-report-2026-05-21.md)
- Persona fixture: [`company_discovery/persona_fixtures.py::PERSONAS[5]`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/persona_fixtures.py)
- Demo account: `kaethe@demo.helpmefindthejob.org`
