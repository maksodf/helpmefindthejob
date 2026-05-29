<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Persona walk — Yusuf (Turkey → Stuttgart)

**Persona slug**: `yusuf`
**Cohort**: most-acute migrant (primary anchor)
**Residency status**: EU Blue Card pending (mechanical engineer, qualifies under §18b AufenthG; salary-threshold gate)
**Friction notes**: Blue Card requires a qualifying job offer ≥ the BMI Blue-Card salary threshold; needs lateral-engineering fallbacks visible alongside specialist-track roles so he doesn't lock onto a single sub-domain prematurely.
**Languages**: TR (native), EN (C1), DE (A2 climbing toward B1)
**Profession + target roles**: Mechanical engineer, 9 years in automotive R&D + manufacturing; targets `Mechanical engineer / Maschinenbauingenieur / Automotive engineer / Manufacturing engineer` in Stuttgart.

**Source-of-truth**: `company_discovery.persona_fixtures.PERSONAS[1]`. Date: 2026-05-24. Version: HEAD of `main`.

---

## 1. Sign-up + onboarding

Yusuf arrives via the apex with a clear "Blue Card before this contract expires" frame. The journey's discover phase captures role, location, experience, languages — and the persona-fit classifier recognises EU-Blue-Card-pathway-likely. Detailed transcript: [`docs/grant/journey-walks-2026-05-20/yusuf.md`](../grant/journey-walks-2026-05-20/yusuf.md).

The friction-class lens for Yusuf surfaces the **lateral-engineering fallback** path that landed in 0.79.5 (per the wider-class implementation): if a specialist-track Maschinenbauingenieur role doesn't match Yusuf's CV closely enough, the journey suggests adjacent roles (Manufacturing engineer / Process engineer / Production engineer) that satisfy the Blue Card salary threshold while broadening the matched-jobs pool.

## 2. CV preparation

EN as the primary CV language; DE secondary because his German is A2. The cv_builder captures the Blue Card context as a structured field (years-of-experience tied to the recognised foreign degree). The cv_summary field carries "EU Blue Card pending" so the fit-scoring prompt's `SCORE_FRICTION_FIT` criterion recognises Blue-Card-pathway language in JDs and awards 22+ when JDs name "Blaue Karte" / "Blue Card sponsorship" / "international relocation supported".

## 3. Job matching

The Stuttgart automotive ecosystem (Daimler / Porsche / Bosch / ZF / Mahle) is pre-seeded in `aicha.saved_searches` — apologies, in `yusuf.saved_searches` per the persona-fixture file. The search fan-out returns a mix of specialist + lateral roles; the discover-review screen surfaces both sets explicitly so Yusuf sees the trade-off rather than only the specialist subset.

The bias-comparative-report verified `yusuf + bluecard_automotive_engineer` at SCORE 90 (deepseek) / 75 (ollama) — comfortably above the 75 verification gate. See `docs/grant/bias-comparative-report-2026-05-21.md` row 18.

## 4. Cover-letter drafting

The Anschreiben proactively names the Blue Card application timeline ("contract start contingent on Blue Card processing, expected ~6 weeks") so the recruiter doesn't have to ask. The 2026-05-20 anschreiben quality walk at [`docs/grant/anschreiben-quality-walks-2026-05-20/yusuf.md`](../grant/anschreiben-quality-walks-2026-05-20/yusuf.md) documents the maintainer-graded output.

For lateral fallback roles, the letter scaffolding pivots to "transferable manufacturing-process expertise" framing rather than the deep-specialist framing — the prompt template branches on the target role's distance from the persona's deepest expertise.

## 5. Application tracked

Mark-applied + the Blue-Card-deadline countdown shown alongside each application. The application-tracker doubles as Yusuf's Blue-Card-application calendar pacer (applications batched in the first 3 weeks of the deadline window so any one of them maturing into an offer gives him enough Blue-Card-processing buffer).

## 6. What felt broken (residual roughness)

- **Salary-threshold filter** is not yet integrated. The Blue Card minimum salary (€48,300 in 2025; €58,400 for shortage occupations) is not surfaced as a filter on discovered roles; Yusuf has to manually screen each role for salary alignment. Tracked as a Phase-2 item.
- **Lateral fallback toggling** is a one-shot suggestion at journey-time, not a persistent filter. A future iteration should let Yusuf toggle "show me adjacent roles too" / "show me only specialist roles" across his queue.
- **Stuttgart watchlist** is automotive-heavy (Daimler / Porsche / Bosch / ZF / Mahle); Yusuf's CV may also fit aerospace (Airbus Stuttgart, Liebherr-Aerospace Lindenberg) but those employers are not in his seed watchlist.
- **Blue Card application timeline copy** in the Anschreiben prompt is fixed at "~6 weeks"; in practice processing time varies materially by Auslandvertretung. The copy should pull from a maintained jurisdictional lookup table, not be hard-coded.

---

## Cross-references

- Detailed journey transcript: [`docs/grant/journey-walks-2026-05-20/yusuf.md`](../grant/journey-walks-2026-05-20/yusuf.md) (485 lines)
- Anschreiben quality walk: [`docs/grant/anschreiben-quality-walks-2026-05-20/yusuf.md`](../grant/anschreiben-quality-walks-2026-05-20/yusuf.md)
- Bias-comparative-report (Yusuf row): [`docs/grant/bias-comparative-report-2026-05-21.md`](../grant/bias-comparative-report-2026-05-21.md)
- Persona fixture: [`company_discovery/persona_fixtures.py::PERSONAS[1]`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/persona_fixtures.py)
- Demo account: `persona-yusuf@demo.helpmefindthejob.org` (via `scripts/seed-personas.py`)
