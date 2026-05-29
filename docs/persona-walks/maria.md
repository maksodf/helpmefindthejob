<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Persona walk — Maria (Spain → Munich)

**Persona slug**: `maria`
**Cohort**: most-acute migrant (primary anchor) — note: previously described in some earlier docs as Romanian care worker; the canonical persona is now the EU-Blue-Card-downshifted-architect. The Romanian care-worker scenario remains in the bias corpus as an extension scenario.
**Residency status**: EU citizen → EU Blue Card downshifted to Drafter role (Tekla / AutoCAD); architect-by-training operating below licence-level.
**Friction notes**: under-employment friction. Licensed architect in Spain, working as drafter in Germany because (a) Architektenkammer registration takes months and (b) German firms favour Architekt-im-Praktikum entry path. Needs roles that preserve Blue Card eligibility (salary threshold) while building toward eventual licensure.
**Languages**: ES (native), CA (native), EN (B2), DE (A2)
**Profession + target roles**: Architect-by-training; drafter / Bauzeichner / Tekla operator / CAD coordinator currently; targets `Architekt-im-Praktikum / Bauzeichner / Architecture coordinator` in Munich + remote.

**Source-of-truth**: `company_discovery.persona_fixtures.PERSONAS[4]`. Date: 2026-05-24. Version: HEAD of `main`.

---

## 1. Sign-up + onboarding

Maria arrives with the underemployment story already painful — she's been drafter for 18 months while her Architektenkammer registration crawls forward. The journey's discover phase needs to capture both the current role (drafter, paying the rent) and the target trajectory (architect-licensure within 36 months). Detailed transcript: [`docs/grant/journey-walks-2026-05-20/maria.md`](../grant/journey-walks-2026-05-20/maria.md) (485 lines).

The friction-class lens here is **Blue-Card-preservation while building toward licensure**. The persona-fit classifier surfaces roles that satisfy the Blue Card salary threshold AND have a documented Architekt-im-Praktikum (AiP) path or accept Tekla / AutoCAD specialists on the architect-track.

## 2. CV preparation

EN-primary CV with DE-A2 → B1 progression noted. The cv_summary explicitly names the Spanish architectural credentials + the in-flight Architektenkammer registration so a German employer doesn't read her as "just a drafter".

## 3. Job matching

Munich + remote-EU architecture employers. The search prioritises:
- Larger firms with documented AiP programmes (Auer Weber, Henn, Allmann Sattler Wappner, …)
- Roles that explicitly mention Tekla / BIM coordination (preserves Maria's existing market value)
- Blue Card salary-threshold-compliant roles (preserves her Blue Card status while she progresses to architect)

The bias-comparative-report verified Maria's adjacency cases at mid-60s SCORE (deepseek 58.9 / ollama 60.1 mean across 10 scenarios; see row 4).

## 4. Cover-letter drafting

The Anschreiben names the Spanish credentials + the Architektenkammer-registration-in-flight status proactively. The 2026-05-20 anschreiben walk at [`docs/grant/anschreiben-quality-walks-2026-05-20/maria.md`](../grant/anschreiben-quality-walks-2026-05-20/maria.md) documents the cross-credential framing.

For pure-drafter roles she applies to as Blue-Card-stability moves, the letter pivots to "deep Tekla + AutoCAD specialist with architect-class spatial reasoning" framing — preserves her dignity while honestly describing the current scope.

## 5. Application tracked

Mark-applied + the Architektenkammer-registration-progress tracker (the licence is the gating dependency for the architect-trajectory roles). Optional integration with the Bayerische Architektenkammer registration-status portal (Section 2.6 deliverable).

## 6. What felt broken (residual roughness)

- **Architektenkammer-registration tracking** is a planned post-grant integration (Section 2.6 — the credentials-equivalence lookup deliverable). Currently Maria tracks her registration progress manually outside the system.
- **AiP-programme employer dataset** is hand-curated for Munich; scaling to other DACH architecture markets (Berlin, Hamburg, Frankfurt, Zurich) requires sourcing additional per-city employer lists.
- **Blue-Card salary-threshold filter** absent (same gap as Yusuf's walk). Salary-aware filtering is Section 2.6.
- **Spanish-architecture-school equivalence** — the system doesn't yet pre-compute which Spanish universities' architecture degrees are most likely to clear Architektenkammer review without supplementary coursework. Section 2.6.

---

## Cross-references

- Detailed journey transcript: [`docs/grant/journey-walks-2026-05-20/maria.md`](../grant/journey-walks-2026-05-20/maria.md) (485 lines)
- Anschreiben quality walk: [`docs/grant/anschreiben-quality-walks-2026-05-20/maria.md`](../grant/anschreiben-quality-walks-2026-05-20/maria.md)
- Bias-comparative-report (Maria row): [`docs/grant/bias-comparative-report-2026-05-21.md`](../grant/bias-comparative-report-2026-05-21.md)
- Persona fixture: [`company_discovery/persona_fixtures.py::PERSONAS[4]`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/persona_fixtures.py)
- Demo account: `persona-maria@demo.helpmefindthejob.org`
