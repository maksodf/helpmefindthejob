<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Persona walk — Maria (Romania → Stuttgart)

**Persona slug**: `maria`
**Cohort**: most-acute migrant / EU-mobile (primary anchor)
**Residency status**: EU citizen (Freizügigkeitsrecht under §2 FreizügG/EU); no permit needed
**Friction notes**: persistent language barrier despite full work rights. Most home-care employers want B1 minimum formally; Maria's care quality is excellent but cannot be demonstrated through a German-language interview. Needs Pflegedienst employers who integrate non-fluent care workers (audio-prep / buddy systems).
**Languages**: RO (native), HU (native), IT (B1), DE (A2)
**Profession + target roles**: Krankenschwester (registered nurse), trained Romania 1991, 28 years hospital + elderly home-care; targets `Altenpflege / Pflegefachkraft / Pflegehelfer:in / Krankenschwester` in Stuttgart.

**Source-of-truth**: `company_discovery.persona_fixtures.PERSONAS[4]`. Date: 2026-05-30. Version: HEAD of `main`.

---

## 1. Sign-up + onboarding

Maria arrives with full legal work rights but a hard language gate: home-care employers formally demand B1, and her German is A2 despite 28 years of clinical competence. The journey's discover phase captures both the deep experience and the language friction. Detailed transcript: [`docs/grant/journey-walks-2026-05-20/maria.md`](../grant/journey-walks-2026-05-20/maria.md) (485 lines).

The friction-class lens here is **language-integration-friendly Pflegedienst matching**: the persona-fit classifier surfaces care employers who explicitly integrate non-fluent carers (audio-onboarding, buddy systems, German-course pairing) rather than employers that gate on a B1/C1 interview.

## 2. CV preparation

DE/EN CV foregrounding 28 years of clinical experience in terms an Altenpflegedienst Pflegedienstleiter will understand. The cv_summary names the Romanian RN training (1991) and the long elderly-care record, so the fit-scoring prompt reads her as a deeply experienced nurse held back by language, not as an entry-level applicant.

## 3. Job matching

Stuttgart + regional Pflegedienst / Altenpflege employers. The search prioritises:
- Employers whose JD language signals language integration ("Deutschkurs gestellt", "mehrsprachiges Team", "Quereinstieg / Wiedereinstieg willkommen")
- Roles that weight clinical experience over formal language certificates
- Both full-Pflegefachkraft and Altenpflegehelfer:in entry roles, so the choice stays hers

The bias-comparative-report measured Maria's per-persona mean at 58.9 (deepseek) / 60.1 (ollama) across her 10 scenarios; the language-friendly scenario `language_friendly_pflegedienst` scored 86 (deepseek) while the gate scenario `maria_mixed_language_barrier` scored 53 (deepseek; "C1 required vs A2 actual") — the spread the deployer monitors. See `docs/grant/bias-comparative-report-2026-05-21.md` (per-persona mean table).

## 4. Cover-letter drafting

The Anschreiben names the language situation honestly while foregrounding the clinical record and the willingness to continue German study. The 2026-05-20 anschreiben walk at [`docs/grant/anschreiben-quality-walks-2026-05-20/maria.md`](../grant/anschreiben-quality-walks-2026-05-20/maria.md) documents the experience-forward framing.

For Altenpflegehelfer:in entry roles she applies to as a foothold, the letter pivots to "28 years of patient-care experience, German improving" framing — preserves her dignity while honestly describing the entry scope.

## 5. Application tracked

Mark-applied + a parallel German-course progress tracker (the language gate is the dominant friction, so closing it widens the employer set). Optional integration with the VHS / Goethe course catalogue surface (a Phase-2 item).

## 6. What felt broken (residual roughness)

- **Anerkennung tracking** is a planned post-grant integration (Section 2.6 — the credentials-equivalence lookup). Recognition of Maria's Romanian nursing diploma for full Krankenpflege (vs. the easier Altenpflegehelfer:in track) is currently tracked manually outside the system.
- **Audio interview-prep** (rehearsable German prompts) is described in the persona narrative but not yet a wired in-app flow; it is a Phase-2 accessibility deliverable.
- **Language-integration JD detection** is keyword-based ("Deutschkurs gestellt", "mehrsprachiges Team"); an employer who integrates non-fluent carers in practice but doesn't say so in the JD won't trip the boost. Tracked for Section 2.8 search quality.
- **RO/DE pension coordination** is a real background concern for a 52-year-old EU-mobile worker; the system refers it rather than handling it.

---

## Cross-references

- Detailed journey transcript: [`docs/grant/journey-walks-2026-05-20/maria.md`](../grant/journey-walks-2026-05-20/maria.md) (485 lines)
- Anschreiben quality walk: [`docs/grant/anschreiben-quality-walks-2026-05-20/maria.md`](../grant/anschreiben-quality-walks-2026-05-20/maria.md)
- Bias-comparative-report (Maria row): [`docs/grant/bias-comparative-report-2026-05-21.md`](../grant/bias-comparative-report-2026-05-21.md)
- Persona fixture: [`company_discovery/persona_fixtures.py::PERSONAS[4]`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/persona_fixtures.py)
- Demo account: `persona-maria@demo.helpmefindthejob.org`
