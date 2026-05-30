<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Persona walk — Olga (Ukraine → Leipzig)

**Persona slug**: `olga`
**Cohort**: most-acute migrant (primary anchor)
**Residency status**: §24 AufenthG (temporary protection, Ukraine displaced-persons directive)
**Friction notes**: clean residency + work-permit but the host-language gate is the dominant friction; senior frontend developer career trajectory; needs English-team or hybrid-remote tech employers that pair with a Goethe / VHS German-course track.
**Languages**: UK (native), RU (native), EN (C1), DE (A2-conversational)
**Profession + target roles**: Senior frontend developer (React, TypeScript), 9 years at a Kyiv startup; targets `Senior frontend developer / Senior React developer / Software engineer (frontend)` in Leipzig + remote-EU.

**Source-of-truth**: `company_discovery.persona_fixtures.PERSONAS[2]`. Date: 2026-05-30. Version: HEAD of `main`.

---

## 1. Sign-up + onboarding

Olga arrives with the §24 residency story handled (her status doesn't gate the work-permit) — the friction is the host-language gate against German tech employers' historical default of German-only working language. The chat journey's discover phase captures this: when she enters `Senior frontend developer` + `Leipzig` + DE-A2, the persona-fit classifier flags English-team-pathway-likely. Detailed transcript: [`docs/grant/journey-walks-2026-05-20/olga.md`](../grant/journey-walks-2026-05-20/olga.md) (560 lines).

The Leipzig English-team watchlist is pre-seeded with the city's English-first / remote-friendly tech employers. (The bias scenarios flag that distant-city variants are penalised harshly — see `docs/grant/bias-comparative-report-2026-05-21.md` row 1, `olga_mixed_distant_city`, spread 30.)

## 2. CV preparation

EN-primary CV with explicit DE-A2 → B1 language-progression timeline. The cv_builder captures Olga's prior cohort (senior IC + tech-lead-adjacent) so the seniority calibration doesn't downgrade her to a mid-level role.

## 3. Job matching

The search fan-out returns Leipzig + remote-EU roles. Two signal layers fire:
- **JD language-policy parsing**: roles that explicitly name "English-speaking team" / "international working language" / "EN-first engineering org" are flagged with a friction-fit boost.
- **Remote-EU compatibility**: the §24 protection applies EU-wide; remote-EU employers can hire her under host-country contract terms (with documented payroll-provider routing).

## 4. Cover-letter drafting

The Anschreiben names the §24 status plainly (so the recruiter doesn't worry about visa-sponsorship overhead) and frames the German-language progression positively ("currently A2, enrolled in B1 Goethe Institut intensive — passed by Q3 2026").

## 5. Application tracked

Mark-applied + a parallel German-course progress tracker (the language-bottleneck is dominant friction, so closing it accelerates the job-search outcome). Optional integration with the VHS / Goethe course catalogue surface (a Phase-2 item).

## 6. What felt broken (residual roughness)

- **English-team detection** in JD parsing is keyword-based ("English-speaking team", "international working language"). A JD that says "team language is English in practice but we sometimes do meetings in German" wouldn't trip the boost. Tracked for Section 2.8 search quality.
- **VHS / Goethe pairing** is a planned post-Phase-2 module (Section 2.7 education-agent). Currently a documentation recommendation, not a wired flow.
- **Remote-EU compliance** is well-handled at the residency-status layer but the payroll-provider matching (Remote, Deel, Multiplier) is not surfaced; Olga must research these herself.
- **§24 → permanent residency timeline** is the dominant background concern; the application tracker should surface the time-to-Niederlassungserlaubnis countdown so she paces her career-step decisions accordingly. Tracked for Section 2.6.

---

## Cross-references

- Detailed journey transcript: [`docs/grant/journey-walks-2026-05-20/olga.md`](../grant/journey-walks-2026-05-20/olga.md) (560 lines)
- Anschreiben quality walk: [`docs/grant/anschreiben-quality-walks-2026-05-20/olga.md`](../grant/anschreiben-quality-walks-2026-05-20/olga.md)
- Bias-comparative-report (Olga row): [`docs/grant/bias-comparative-report-2026-05-21.md`](../grant/bias-comparative-report-2026-05-21.md)
- Persona fixture: [`company_discovery/persona_fixtures.py::PERSONAS[2]`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/persona_fixtures.py)
- Demo account: `olga@demo.helpmefindthejob.org`
