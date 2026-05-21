# Translating helpmefindthejob

This project is built for people facing structural friction in the
European labour market. The most-acute persona panel (Aïcha, Yusuf,
Olga, Mahmoud, Maria) speaks Arabic, Turkish, Ukrainian, Romanian
natively. Shipping the app only in English and German fails them.

**Translators are first-class contributors.** No git, no JSON
editing, no engineering background required.

## Quickest path: Weblate

We use [Weblate](https://weblate.org), the leading FLOSS community
translation platform. Once the maintainer wires the project at
`hosted.weblate.org/projects/helpmefindthejob/`:

1. Sign up at <https://hosted.weblate.org>
2. Pick a language
3. Translate strings inline — Weblate's editor validates the JSON,
   shows context (which screen the string appears on), and tracks
   plural forms automatically.
4. Your contributions land as pull requests against this repository
   after review.

**Glossary, screenshots, and translation memory** all live in
Weblate. You don't have to invent terminology from scratch — the
glossary pins how key terms (Anerkennung, Aufenthaltstitel,
Wiedereinstieg, Quereinstieg) are translated per locale.

## Or directly via git

If you prefer git:

1. Fork this repo.
2. Copy `static/i18n/en.json` to `static/i18n/<your-locale-code>.json`.
3. Translate the values (keep the keys identical).
4. Add an entry to `static/i18n/locales.json` describing your
   locale (name, endonym, direction, status). Mark `status: "shipped"`
   when coverage is ≥ 95%.
5. Open a PR.

## Priority locales

The Phase 1 locales (already shipped):

| Code | Language | Direction |
|------|----------|-----------|
| `en` | English  | LTR       |
| `de` | Deutsch  | LTR       |

The Phase 2 locales (scaffolding ready, translations needed):

| Code | Language    | Direction | Persona tie-in |
|------|-------------|-----------|----------------|
| `ar` | العربية      | **RTL**   | Aïcha (§16d) — highest priority |
| `uk` | Українська  | LTR       | Olga (§24 Ukraine) |
| `tr` | Türkçe      | LTR       | Yusuf (Blue Card from Türkiye) |
| `ro` | Română      | LTR       | Maria (intra-EU mobility) |

Adding any other locale: open an issue first so the locale registry
can be discussed (right-to-left support, plural forms, fallback
chain).

## RTL (Arabic, Hebrew, Persian, Urdu, …)

The app's RTL infrastructure landed in W3 D15 of the 4-week sprint:

- The locale registry (`static/i18n/locales.json`) carries a
  `direction: "rtl"` flag per locale.
- The frontend sets `html[dir="rtl"]` automatically when an RTL
  locale is active.
- The CSS at the bottom of `static/styles.css` flips text-align,
  flex direction, list indentation, sidebar position, and toast
  anchoring for `html[dir="rtl"]`.

If you find a UI element that misrenders in your RTL locale, file
an issue with a screenshot — we'll add a targeted RTL override.

## Plurals

The app supports CLDR plural categories (`zero`, `one`, `two`,
`few`, `many`, `other`) via `Intl.PluralRules`. Some languages
(Polish, Ukrainian, Russian, Arabic) need multiple plural forms.

In a translation JSON, a plural-aware key looks like:

```json
{
  "scan.jobsFound": {
    "one":   "{{count}} stelle gefunden",
    "other": "{{count}} stellen gefunden"
  }
}
```

The JS layer picks the right form via `Intl.PluralRules` based on
the active locale. Translators don't need to know the per-language
rule — Weblate shows you which forms your language needs.

## Style + tone

- **Address the user directly** (`du` in German, second-person
  informal where the locale supports it). The project is built
  for people in stressful situations; formal address creates
  distance.
- **Avoid jargon.** When a German term has no equivalent (e.g.
  "Anerkennung", "Wiedereinstieg"), keep the German term and add
  a short parenthetical gloss the first time it appears.
- **Be honest about uncertainty.** When the AI suggests something,
  the UI surfaces it as a suggestion, not a verdict. Translations
  must preserve that hedging.

## Questions

Open an issue tagged `translation` — the maintainer + active
translators monitor those weekly.

## License

By contributing translations you agree they are released under
Apache 2.0 (same as the rest of the project) per the
[Contributor License Agreement](CLA.md).
