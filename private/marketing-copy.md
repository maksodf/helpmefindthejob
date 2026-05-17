# Marketing copy — apex landing (khalo.org)

Drop-in copy for the marketing landing page once the apex domain ships (#13). The voice is set in `docs/brand-voice.md` — every sentence here was passed through that filter.

Three flows on the page: **hero** (promise + CTA), **three use-cases** (the cohorts that benefit), **pricing** (plain table). Then a small "what we don't do" block as the anti-LinkedIn positioning, and FAQ + footer.

## Hero

### English

> # A calm job tool.
>
> Watch the career pages you'd actually want to work for. Dedupe across Indeed, StepStone, Arbeitnow, Bundesagentur, and Muse. Triage with a keyboard. No LinkedIn feed. No algorithm. No surveillance.
>
> [Sign up — free] [See it live]

### German

> # Ein ruhiges Werkzeug für die Jobsuche.
>
> Beobachte die Karriereseiten, bei denen du wirklich arbeiten würdest. Dedupliziert über Indeed, StepStone, Arbeitnow, Bundesagentur und Muse. Triage mit Tastenkombinationen. Kein LinkedIn-Feed. Kein Algorithmus. Keine Überwachung.
>
> [Kostenlos starten] [Live ansehen]

### Subhero (one line, optional)

> EN: Built for serious job-seekers who don't want to grind a feed to find a role.
>
> DE: Für ernsthafte Bewerber, die keine Lust auf Feed-Grinding haben.

## Three use-case sections

Pick the three cohorts that actually use the product. Each is one paragraph + one screenshot slot.

### Use case 1 — The DACH job-seeker who hates LinkedIn

> EN: You know which 30 employers you'd take an offer from. You don't want a recruiter feed; you want to know when those 30 employers post a role. DirectJob Scout watches their direct career pages every day, dedupes against the public aggregators, and surfaces one queue you can triage in five minutes.
>
> DE: Du weißt, bei welchen 30 Arbeitgebern du anfangen würdest. Du willst keinen Recruiter-Feed; du willst wissen, wann genau diese 30 eine Stelle ausschreiben. DirectJob Scout prüft täglich deren Karriereseiten, dedupliziert gegen die öffentlichen Aggregatoren und liefert dir eine Warteschlange, die du in fünf Minuten triagieren kannst.

### Use case 2 — The healthcare-management cohort (initial pilot persona)

> EN: Public health, hospital operations, statutory insurers, digital health, market access — the German healthcare market is fragmented across employer sites that LinkedIn under-indexes. We started here for a reason: it's where the discovery gap is widest. We ship curated watchlists for the major Krankenkassen, Klinikgruppen, and digital-health employers; you can use them as-is or replace them with your own list.
>
> DE: Public Health, Krankenhausverwaltung, Krankenkassen, Digital Health, Market Access — der deutsche Gesundheitsmarkt ist über Arbeitgeberseiten verteilt, die LinkedIn schlecht abdeckt. Wir haben hier angefangen, weil die Lücke in der Auffindbarkeit hier am größten ist. Kuratierte Watchlists für die großen Krankenkassen, Klinikgruppen und Digital-Health-Arbeitgeber sind enthalten; du kannst sie übernehmen oder durch deine eigene Liste ersetzen.

### Use case 3 — The bring-your-own-AI power user

> EN: You already pay for ChatGPT or Claude. We don't make you pay twice. Manual mode prepares a tailored prompt for each role and hands it to your existing subscription tab — no API key required. Want automation? Paste an OpenAI / Anthropic / Gemini / OpenRouter / DeepSeek / Ollama key once and the auto-fit ring + cover-letter draft + CV-tailor flow run themselves.
>
> DE: Du zahlst schon für ChatGPT oder Claude. Wir lassen dich nicht doppelt zahlen. Im Manuellen Modus bereiten wir einen passgenauen Prompt vor, den du in deinem bestehenden Tab nutzt — kein API-Key nötig. Lieber automatisch? Füge einmal einen OpenAI- / Anthropic- / Gemini- / OpenRouter- / DeepSeek- / Ollama-Key ein und der Auto-Fit-Score, Anschreiben-Entwurf und CV-Tailor laufen selbständig.

## Pricing

Plain table. No "most popular" rosette. No "save 33%" sticker; the saving is implied by the annual price.

| Plan | Free | Pro |
|---|---|---|
| Saved searches | 3 | Unlimited |
| AI mode | Manual only | Manual + BYOK + Managed |
| Retention | 30 days | 90 days |
| Daily digest | — | ✓ |
| Push notifications | ✓ | ✓ |
| Export your data | ✓ | ✓ |
| Price | €0 / month | €5 / month or €40 / year |

> EN: Cancel any time from the Stripe Customer Portal. Annual gets you 8 months for the price of 12. There is no enterprise plan because we are one operator.
>
> DE: Kündbar jederzeit über das Stripe-Kundenportal. Jährlich = 8 Monate zum Preis von 12. Keinen Enterprise-Tarif gibt es deshalb nicht, weil wir genau eine Person sind.

(Operator note: the current code ships Team €79 / Org €249 multi-seat plans. The Free / Pro €5 single-user model in the tracker is a separate decision — see tracker #21.)

## "What we don't do" — anti-LinkedIn block

Place between use cases 3 and pricing. Six bullets, each a single line.

> EN:
> - No algorithmic feed. The queue is sorted by freshness + fit, deterministically.
> - No "people you may know". We are not a network.
> - No engagement metrics. Nothing rewards us for keeping you on the site longer.
> - No advertising. We don't sell ads, attribute clicks, or share data with brokers.
> - No third-party trackers. The static surface (sign-up, privacy, terms) loads only first-party assets.
> - No surveillance email. Daily digest is opt-in, capped, unsubscribable from a one-click link.
>
> DE:
> - Kein algorithmischer Feed. Die Warteschlange ist nach Aktualität + Fit deterministisch sortiert.
> - Kein „Personen, die du kennen könntest". Wir sind kein Netzwerk.
> - Keine Engagement-Metriken. Nichts belohnt uns dafür, dich länger auf der Seite zu halten.
> - Keine Werbung. Wir verkaufen keine Anzeigen, vermessen keine Klicks und teilen keine Daten mit Brokern.
> - Keine Drittanbieter-Tracker. Die statischen Seiten (Registrierung, Datenschutz, AGB) laden ausschließlich First-Party-Ressourcen.
> - Keine Überwachungsmails. Der tägliche Digest ist opt-in, gedeckelt und mit einem Klick abbestellbar.

## FAQ (collapsed `<details>`)

Five Qs. Each answer = two sentences max.

> EN:
> **What does "direct" mean?**
> We watch a company's own career page, not a third-party board. The aggregators we add (Indeed, StepStone, etc.) supplement that — they don't replace it.
>
> **Why not just LinkedIn?**
> LinkedIn under-indexes mid-market and German employer sites. Their search is also tuned for engagement, not coverage.
>
> **Is my CV stored encrypted?**
> Yes — ChaCha20-Poly1305 AEAD at rest, with the user_id as authenticated additional data. Failed-decrypt drops the field rather than corrupts.
>
> **Can I delete my account?**
> Settings → Privacy → Request deletion. We email a confirmation; after a 7-day grace window, the account hard-deletes. You can cancel any time during that window.
>
> **Is this self-hosted?**
> The operator runs the prod server. Future plan: a self-hosted single-binary release for power users — no date, no commitment.

## Footer

EN bullets to wire (matches `static/index.html` legal-links + adds /help + /changelog):

> Privacy · Terms · Data retention · Impressum · Help · Changelog · Status

## Operator hand-off list

Things the operator must supply before this copy can ship:

- [ ] Hero "See it live" video link (or remove the second CTA)
- [ ] Two screenshot slots for use-case sections (queue triage + application form)
- [ ] Operator name + bio for the FAQ "self-hosted" answer (currently anonymous)
- [ ] Status page URL (placeholder above)
- [ ] If pricing model decision (#21) lands at Team / Org instead of Free / Pro, swap the pricing table for the multi-seat version.
