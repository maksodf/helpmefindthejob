<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Persona walk — Aïcha (Tunisia → Berlin)

**Persona slug**: `aicha`
**Cohort**: most-acute migrant (primary anchor)
**Residency status**: §16d AufenthG (visa for purpose of recognition of foreign qualification)
**Friction notes**: recognition decision letter expected in ~4 months; needs Anerkennung-friendly employers willing to begin onboarding before the letter lands.
**Languages**: FR (native), AR (native), EN (B2), DE (B1 working toward B2)
**Profession + target roles**: Registered nurse, 7 years hospital experience including 2 years geriatric care; targets `Registered nurse / Krankenpfleger / Pflegefachkraft` in Berlin.

**Source-of-truth**: `company_discovery.persona_fixtures.PERSONAS[0]`. Date: 2026-05-24. Version: HEAD of `main` at commit time.

---

## 1. Sign-up + onboarding

Aïcha arrives via the apex (or the demo subdomain with the seeded `persona-aicha@demo.helpmefindthejob.org` account, per `scripts/seed-personas.py`). The landing page shows the seven-persona panel; Aïcha's card names her concrete situation in plain language so she recognises herself immediately.

After registration, the chat journey opens with `/start`. The chat-router (`company_discovery/chat_router.py`) walks her through the 12-phase journey: greet → discover → cv_check → search_setup → search_run → discover_review → import → analyze → letter → apply → track → done. The discover phase asks four questions: role, location, experience, languages. Aïcha's input shape is documented turn-by-turn in [`docs/grant/journey-walks-2026-05-20/aicha.md`](../grant/journey-walks-2026-05-20/aicha.md).

The friction-class lens kicks in immediately: when Aïcha enters `Registered nurse` + `Berlin` + `B1` German, the journey's persona-fit classifier identifies §16d-pathway-likely and the downstream search prioritises Anerkennungs-friendly employers (Vivantes, Helios, Charité have been pre-tagged in the watchlist template at `company_discovery/persona_fixtures.py::aicha.saved_searches`).

## 2. CV preparation

Aïcha's CV is bilingual (EN draft → DE final). The cv_builder (`company_discovery/cv_builder.py`) walks the sectional interview pattern: personal data, summary, work history (2 entries), qualifications (the Anerkennung context is captured here as a structured field, not free text), languages, skills, references. Each section persists encrypted-at-rest under ChaCha20-Poly1305 via the AEAD wrapper.

The CV emits to two formats:
- **PDF** for the application packet (DACH-style)
- **Plain-text** for AI ingestion (the cv_text field feeds into `build_cv_tailoring_prompt`)

For Aïcha specifically, the `cv_summary` field carries the §16d context explicitly: "Currently in §16d Anerkennung process with BIBB / Anabin." This is the structured data the fit-scoring prompt's `SCORE_FRICTION_FIT` criterion reads to decide whether a JD's pathway language matches.

## 3. Job matching

`/find` triggers the aggregator fan-out (Adzuna + Indeed + LinkedIn public + EURES + the per-company watchlist scans). Results are normalised into `DiscoveredJob` records and queued for `auto-fit` scoring.

The `build_auto_fit_prompt` (per-criterion decomposition added in commit `cd3aa52`, see `04-research-and-decisions.md` PART 4.1) scores each role across four axes: skills + experience + location/language + friction-fit. For Aïcha + an Anerkennungs-friendly clinical role, the friction-fit decision rule awards 22+ when the JD names "§16d" / "Anerkennungs-freundlich" / "supports Anerkennung process" and the candidate's friction matches (per `build_auto_fit_prompt`'s anchor scale). The canonical smoke run (`docs/grant/product-quality-walks/aicha-pass3-smoke-2026-05-20.json`) produced a granular SCORE of 66 (per-criterion 18+13+20+15; friction-fit 15/25) — a non-round-anchor result demonstrating the per-criterion decomposition.

The top-5 matched roles surface on the discover_review screen with the friction-fit chip badge visible alongside the overall score. Aïcha can drill into any role and see the per-criterion breakdown.

## 4. Cover-letter drafting

`/letter` on an imported role triggers `build_cover_letter_brief_prompt`. The prompt is persona-aware (Aïcha's residency_status flows into the prompt template) so the generated Anschreiben proactively explains §16d to the recruiter in a single sentence early in the letter rather than leaving the recruiter to guess. The 2026-05-20 anschreiben-quality walk at [`docs/grant/anschreiben-quality-walks-2026-05-20/aicha.md`](../grant/anschreiben-quality-walks-2026-05-20/aicha.md) documents the exact prompt → AI output → maintainer-graded result for the Anerkennung context.

The letter draft surfaces in the brief view with the same per-paragraph editing surface as the rest of the SPA. Aïcha can hand-edit any sentence, regenerate any paragraph, or accept the draft verbatim.

## 5. Application tracked

Mark-applied flips the imported_job state. The application timeline at `/today` shows the new entry alongside any prior applications. Optional follow-up reminders (via `/remind`) close the loop.

For Aïcha specifically, the application-tracker doubles as the Anerkennung-deadline anchor: she sees alongside each application the time-to-recognition-decision countdown and can pace her applications against the §16d window.

## 6. What felt broken (residual roughness; honesty discipline)

- **Bilingual CV export** is still a manual switch; the cv_builder doesn't yet auto-mirror the EN draft into a DE production version. Tracked as a Phase-2 domain-intelligence item.
- **Anerkennungs-friendly employer dataset** is curated by hand at `company_discovery/persona_fixtures.py::aicha.saved_searches` (Vivantes / Helios / Charité). Scaling beyond Berlin requires sourcing additional Anerkennungs-friendly employer lists from IQ-Netzwerk regional networks. Tracked for Section 2.6.
- **`SCORE_FRICTION_FIT` anchor scale** still parks at exact anchor values 18 % of the time across the bias-comparative-report (per the bias-comparative-report closure note, Finding F2). Sub-3 % is the target.
- **AI-detected §16d phrasing** is matched against a hand-curated keyword list (`§16d`, `Anerkennungs-freundlich`, etc.). Robustness to phrasing drift across JDs is a Phase-2 ML-classification deliverable.
- **CV photo handling** is consent-gated and encrypted-at-rest, but the upload UI does not yet honour the Aïcha-specific "DACH-norm professional photo" guidance (head-and-shoulders, neutral background). Documentation gap.

---

## Cross-references

- Detailed turn-by-turn journey transcript: [`docs/grant/journey-walks-2026-05-20/aicha.md`](../grant/journey-walks-2026-05-20/aicha.md)
- Anschreiben quality walk: [`docs/grant/anschreiben-quality-walks-2026-05-20/aicha.md`](../grant/anschreiben-quality-walks-2026-05-20/aicha.md)
- Pass-3 smoke harness output: [`docs/grant/product-quality-walks/aicha-pass3-smoke-2026-05-20.json`](../grant/product-quality-walks/aicha-pass3-smoke-2026-05-20.json)
- Bias-comparative-report (Aïcha row): [`docs/grant/bias-comparative-report-2026-05-21.md`](../grant/bias-comparative-report-2026-05-21.md)
- Persona fixture: [`company_discovery/persona_fixtures.py::PERSONAS[0]`](https://github.com/maksodf/helpmefindthejob/blob/main/company_discovery/persona_fixtures.py)
- Demo account: `persona-aicha@demo.helpmefindthejob.org` (via `scripts/seed-personas.py`)
