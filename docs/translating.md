<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 DirectJob Scout contributors -->

# Translating DirectJob Scout

DirectJob Scout is a civic employment commons for the European
labour market. It ships **English + German** today and grows by
locale as native-speaker contributors join. This page is the
contributor pathway: how locale bundles are structured, how to
add a new one, the German-bureaucratic-conventions preservation
rule, and how the translation-review process works.

## Goal

The shipped locales are **English (`en`) and German (`de`)** per
the project's
[Decision 6](https://github.com/maksodf/directjob-scout/blob/main/docs/grant/04-research-and-decisions.md#decision-6).
The post-grant target locales — **Arabic, Ukrainian, Turkish,
Romanian** — map to the seven-persona panel's friction
geography:

- **Arabic** → Aïcha (Tunisia → Berlin nurse, §16d Anerkennung)
- **Ukrainian** → Olga (Ukraine → Leipzig frontend developer, §24)
- **Turkish** → Yusuf (Turkey → Munich mechanical engineer, Blue Card)
- **Romanian** → Maria (Romania → Stuttgart care worker, EU
  citizen)

The friction-class architecture (Decision 21) means these locales
serve their named personas as the most-acute use case AND any
user from the same language community who faces the same
friction. They land as native-speaker contributors join — Phase 2
on `ROADMAP.md`.

## Locale bundle structure

| Field | Value |
|---|---|
| Location | `static/i18n/<locale>.json` |
| Format | One flat JSON object per locale; keys + string values |
| Encoding | UTF-8 |
| Total keys today | 519 (en) + 519 (de) — pinned-equal by the parity test |
| Source of truth | `static/i18n/en.json` — every new key lands here first |

### Schema convention

Keys are **dot-namespaced**:

```json
{
  "nav.dashboard": "Today",
  "nav.companies": "Companies",
  "queue.foundInN": "Found in {count} more",
  "settings.persona.suggested": "Best fit from your CV: {label}. Apply?"
}
```

Top-level namespaces in use today (sample):

- `nav.*` — sidebar navigation items
- `auth.*` — sign-in / register / password-reset surfaces
- `queue.*` — job-queue (Discovered jobs) surface
- `companies.*` — Companies view
- `cv.*` / `cvBuilder.*` — CV-builder surfaces
- `settings.*` — Settings surface
- `wizard.*` — first-run onboarding wizard
- `errors.*` — error-state messages

### Interpolation placeholders

Values may include `{name}` placeholders that the app replaces at
render time:

| Example en value | de value | Variable |
|---|---|---|
| `"Found in {count} more"` | `"In {count} weiteren gefunden"` | `count` |
| `"{n} selected"` | `"{n} ausgewählt"` | `n` |
| `"Imported {ok} of {total}. {err} skipped."` | `"{ok} von {total} importiert. {err} übersprungen."` | `ok`, `total`, `err` |

**Preserve every `{placeholder}` exactly** — same name, same
braces. The app passes data into them at runtime; renaming or
removing a placeholder breaks the surface that key feeds.

### HTML data-i18n binding

The HTML uses `data-i18n="key.path"` attributes to bind elements
to translated strings:

```html
<h1 data-i18n="nav.dashboard">Today</h1>
<button data-i18n="queue.toolbar.autoFitAll">Auto-fit unscored</button>
```

The fallback text inside the element (`Today`, `Auto-fit
unscored`) is the **last-resort fallback** if the i18n bundle is
missing the key — it is NOT the source of truth. `en.json` is
the source of truth.

## How to add a new locale

The contributor flow is four steps. Plain `git`, no extra
tooling.

```bash
# 1. Copy the en.json bundle as a starting point.
cp static/i18n/en.json static/i18n/<your-locale>.json

# 2. Translate values in place. Preserve keys (left side of ":")
#    and any "{placeholder}" tokens exactly. Save UTF-8.

# 3. Run the parity test locally. It catches key drift between
#    your new locale and en.json.
python3 -m unittest tests.test_phase0_i18n_parity

# 4. Submit the PR with CLA assent per CONTRIBUTING.md.
```

The parity test (`tests/test_phase0_i18n_parity.py`) is also
run in CI by `.github/workflows/test.yml` on every push. It
enforces three contracts:

1. `test_en_and_de_have_identical_key_sets` — every locale bundle
   has the same key set as `en.json`.
2. `test_every_html_reference_resolves_in_both_bundles` — every
   `data-i18n="..."` reference in `static/index.html` resolves in
   both bundles.
3. `test_no_blank_translations` — no empty values; missing
   translations must be deliberate (copy the English string
   verbatim when unsure rather than leaving blank).

A failing parity test in CI blocks the PR. The reviewer can
re-run after the locale bundle is updated to close the gap.

When adding a third+ locale, the parity test itself currently
asserts only en/de equivalence — the next contributor adding a
locale should extend the test to include their new bundle.
Filing a small PR that generalises the test to walk every
`static/i18n/*.json` is welcome and tracked in `ROADMAP.md`.

## German-bureaucratic-conventions preservation rule

When a string contains a **German legal, bureaucratic, or
labour-administration term**, do NOT translate the term. Keep it
verbatim. These terms have legal-specific meaning that doesn't
translate cleanly and changing them would mislead the user.

Examples that stay German in every locale:

- **Residency / work-rights**: `Aufenthaltstitel`, `§16d`, `§24`,
  `Blue Card / Blaue Karte`, `Freizügigkeit`, `Anmeldung`
- **Qualification recognition**: `Anerkennung`, `Anabin`, `BIBB`,
  `Approbation`, `Zeugnisbewertung`
- **Career-shift context**: `Wiedereinstieg`, `Familienpause`,
  `Auffrischung`
- **Employment framework**: `TVöD`, `Ausbildung`,
  `Bewerbungsmappe`, `Lebenslauf`, `Tarifvertrag`, `Beamtenstatus`
- **Social-benefit framework**: `Bürgergeld`, `ALG I/II`,
  `Optionskommune`
- **Industry-specific qualifiers**: `Handwerk`, `Krankenpfleger`,
  `Pflegefachkraft`, `Altenpflegerin`, `Anlagenmechaniker SHK`

The English bundle already follows this rule (see `en.json` for
examples — strings like `"Anerkennung-friendly employer"`
already keep the German term and translate only the surrounding
English text). Other locale bundles do the same against their
own native vocabulary.

This rule matters for the persona panel: Aïcha's pathway is
defined by §16d and Anerkennung; rendering those as "Section 16d
visa" or "qualification recognition" in Arabic strips the legal
signal that connects her to her actual administrative situation.

## Translation review process

Per **Decision 18** (consent-first authorship), every translation
review goes through this flow:

1. **Native-speaker review** — the maintainer recruits a native
   speaker of the target locale (friend, fellow student, social
   circle, public outreach if needed). The review is a ~2 h
   first-pass against the locale bundle:
   - flag mistranslations
   - flag German-bureaucratic terms that should have been
     preserved verbatim but weren't
   - flag interpolation-placeholder corruption (`{count}` → `{Anzahl}`)
   - flag tone mismatches (formal vs. informal "you" — German
     `Sie` vs. `du` is the canonical case)

2. **Reviewer changes land via PR** — small, scoped commits with
   the reviewer's name/handle in the commit message.

3. **Credit in `AUTHORS.md`** — once the reviewer explicitly
   consents (Decision 18: consent-first authorship), the
   maintainer adds them to `AUTHORS.md` in a separate dated
   commit. Reviewer name appears as they wish to be credited;
   pseudonymous and "anonymous reviewer" entries are valid.

The first DE-bundle review is open for Phase 1 — the maintainer
is recruiting a native German speaker. Status tracked in the
per-language table below.

## Per-language status

| Locale | Status | Native reviewer | Coverage | Primary persona |
|---|---|---|---|---|
| **English (`en`)** | shipped | maintainer (self) | 100% (519/519) | (all) |
| **German (`de`)** | shipped | TBD — Phase 1 outreach in progress | 100% (519/519) | (all) |
| **Arabic (`ar`)** | post-grant | needs contributor | 0% | Aïcha |
| **Ukrainian (`uk`)** | post-grant | needs contributor | 0% | Olga |
| **Turkish (`tr`)** | post-grant | needs contributor | 0% | Yusuf |
| **Romanian (`ro`)** | post-grant | needs contributor | 0% | Maria |

Other locales (French for Aïcha's source-language Arabic-French
bilingual context; further EU languages as the friction class
expands) are welcomed as native-speaker contributors arrive.

## Getting in touch

If you'd like to translate a locale and you're not sure where to
start, the friendliest path is:

1. Open a GitHub Discussion or Issue describing the locale +
   your context (native speaker yes/no, language community
   you're connected to, time you can offer).
2. The maintainer responds within ~1 week and either accepts the
   contribution or surfaces any constraints.
3. Once accepted, follow the four-step contributor flow above.

The full contributor protocol (CLA, code of conduct, review
expectations) lives in
[`CONTRIBUTING.md`](https://github.com/maksodf/directjob-scout/blob/main/CONTRIBUTING.md).
