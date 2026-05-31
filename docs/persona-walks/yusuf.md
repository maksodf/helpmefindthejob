<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Persona walk — Yusuf (Turkey → Munich)

**Persona slug**: `yusuf`
**Cohort**: most-acute migrant (primary anchor)
**Residency status**: EU Blue Card application in progress, supported by an employer offer at a Munich engineering firm (salary-threshold gated)
**Friction notes**: the offer is in hand; the friction is the adjacent navigation — comparing equivalent automotive-engineering roles across Munich / Stuttgart / Ingolstadt, and needing lateral-engineering fallbacks visible alongside specialist-track roles so he doesn't lock onto a single sub-domain prematurely.
**Languages**: TR (native), EN (B2-business), DE (A2, learning)
**Profession + target roles**: Mechanical engineer, 13 years in automotive supplier work (Bursa Tier-2 supplier to VW/Mercedes plants); targets `Mechanical engineer / Maschinenbauingenieur / Automotive engineer / Manufacturing engineer` in Munich.

**Source-of-truth**: `company_discovery.persona_fixtures.PERSONAS[1]`. Date: 2026-05-30. Version: HEAD of `main`.

---

## 1. Sign-up + onboarding

Yusuf arrives via the apex with a clear "compare options before the Blue Card start date" frame. The journey's discover phase captures role, location, experience, languages — and the persona-fit classifier recognises EU-Blue-Card-pathway-likely. Detailed transcript: [`docs/grant/journey-walks-2026-05-20/yusuf.md`](../grant/journey-walks-2026-05-20/yusuf.md).

The friction-class lens for Yusuf surfaces the **lateral-engineering fallback** path that landed in 0.79.5 (per the wider-class implementation): if a specialist-track Maschinenbauingenieur role doesn't match Yusuf's CV closely enough, the journey suggests adjacent roles (Manufacturing engineer / Process engineer / Production engineer) that satisfy the Blue Card salary threshold while broadening the matched-jobs pool.

## 2. CV preparation

EN as the primary CV language; DE secondary because his German is A2. The cv_builder captures the Blue Card context as a structured field (years-of-experience tied to the recognised foreign degree). The cv_summary field carries "EU Blue Card pending" so the fit-scoring prompt's `SCORE_FRICTION_FIT` criterion recognises Blue-Card-pathway language in JDs and awards 22+ when JDs name "Blaue Karte" / "Blue Card sponsorship" / "international relocation supported".

## 3. Job matching

The Munich + Ingolstadt automotive ecosystem (BMW, MAN, Audi Ingolstadt, plus Bosch / ZF regional sites) is pre-seeded in `yusuf.saved_searches` per the persona-fixture file. The search fan-out returns a mix of specialist + lateral roles; the discover-review screen surfaces both sets explicitly so Yusuf sees the trade-off rather than only the specialist subset.

The bias-comparative-report verified `yusuf + bluecard_automotive_engineer` at SCORE 90 (deepseek) / 75 (ollama) — comfortably above the 75 verification gate. See `docs/grant/bias-comparative-report-2026-05-21.md` row 18.

## 4. Cover-letter drafting

The Anschreiben proactively names the Blue Card application status so the recruiter doesn't have to ask. The 2026-05-20 anschreiben quality walk at [`docs/grant/anschreiben-quality-walks-2026-05-20/yusuf.md`](../grant/anschreiben-quality-walks-2026-05-20/yusuf.md) documents the maintainer-graded output.

For lateral fallback roles, the letter scaffolding pivots to "transferable manufacturing-process expertise" framing rather than the deep-specialist framing — the prompt template branches on the target role's distance from the persona's deepest expertise.

## 5. Application tracked

Mark-applied + the post-arrival timeline (Anmeldung / Steuer-ID / Krankenkasse) shown alongside the application queue. The application-tracker doubles as Yusuf's first-months pacer (applications batched so any one of them maturing into an offer gives him a workable Blue-Card-start runway).

## 6. What felt broken (residual roughness)

- **Salary-threshold filter** is not yet integrated. The Blue Card minimum salary threshold (lower for shortage occupations such as engineering) is not surfaced as a filter on discovered roles; Yusuf has to manually screen each role for salary alignment. Tracked as a Phase-2 item.
- **Lateral fallback toggling** is a one-shot suggestion at journey-time, not a persistent filter. A future iteration should let Yusuf toggle "show me adjacent roles too" / "show me only specialist roles" across his queue.
- **Munich watchlist** is automotive-heavy (BMW / MAN / Audi / Bosch / ZF); Yusuf's CV may also fit aerospace (MTU Aero Engines Munich, Airbus Ottobrunn, Liebherr-Aerospace Lindenberg) but those employers are not in his seed watchlist.
- **Blue Card timeline copy** in the Anschreiben prompt is fixed; in practice processing time varies materially by Auslandsvertretung. The copy should pull from a maintained jurisdictional lookup table, not be hard-coded.

---

## Cross-references

- Detailed journey transcript: [`docs/grant/journey-walks-2026-05-20/yusuf.md`](../grant/journey-walks-2026-05-20/yusuf.md) (485 lines)
- Anschreiben quality walk: [`docs/grant/anschreiben-quality-walks-2026-05-20/yusuf.md`](../grant/anschreiben-quality-walks-2026-05-20/yusuf.md)
- Bias-comparative-report (Yusuf row): [`docs/grant/bias-comparative-report-2026-05-21.md`](../grant/bias-comparative-report-2026-05-21.md)
- Persona fixture: [`company_discovery/persona_fixtures.py::PERSONAS[1]`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/persona_fixtures.py)
- Demo account: `yusuf@demo.helpmefindthejob.org` (via `scripts/seed-personas.py`)
