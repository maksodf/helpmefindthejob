# Cookie + tracker audit

Last verified: 2026-05-10. App version 0.73.0.

This audit answers tracker item #11: **do we need a DSGVO consent banner?**
The short answer is **no** — but the full analysis is below so the next reviewer can re-derive the same conclusion.

## What the app sets in the browser

| Mechanism | Name | Purpose | First-party? | Lifetime |
|---|---|---|---|---|
| Cookie | `directjob_session` | Session token, signed | Yes | 14 days, HttpOnly, Secure (prod), SameSite=Lax |
| Cookie | `csrf_token` (header double-submit) | CSRF defense | Yes | Same as session |
| localStorage | `directjob.locale` | Language preference (en/de) | n/a | Until user clears |
| localStorage | `directjob.cmdkSeen` | "Have you seen the command palette" hint | n/a | Until user clears |
| localStorage | `directjob.lastSettingsTab` | Settings tab persistence | n/a | Until user clears |

There are **zero third-party cookies, zero analytics, zero ad-network beacons, zero tracker scripts**. The static surface (`index.html`, `privacy.html`, `terms.html`, `data-retention.html`, `impressum.html`) loads CSS from the same origin only.

Service worker (`sw.js`) caches assets for offline UX. It is first-party, exposes nothing to third parties, and obeys SameOrigin.

## DSGVO / TTDSG analysis

§ 25 Abs. 2 Nr. 2 TTDSG (the German implementation of EU Cookie Directive Art. 5(3)) exempts **strictly necessary** technical storage from consent: "wenn die Speicherung von Informationen … unbedingt erforderlich ist, damit der Anbieter eines Telemediendienstes einen vom Nutzer ausdrücklich gewünschten Telemediendienst zur Verfügung stellen kann."

Both cookies and all three localStorage keys fall squarely within this exception:

- **Session cookie**: required to deliver the authenticated experience the user signed in for.
- **CSRF cookie**: required to protect the user against cross-site forgery.
- **`directjob.locale`**: the user explicitly switched language; storing that choice is required to honour it.
- **`directjob.cmdkSeen`**, **`directjob.lastSettingsTab`**: UI preferences set by user action; required to deliver the consistent UX the user requested.

No marketing, retargeting, profiling, or fingerprinting storage exists.

**Conclusion: no consent banner is required under DSGVO / TTDSG.** A banner would be misleading — it would imply we set non-essential storage when we don't.

## Third-party requests at load time

| Request | When | Status |
|---|---|---|
| Google Fonts CSS / WOFF2 | Page load | **Removed 2026-05-10** (commit pending). Reason: served Inter from Google's CDN, which transmits IP + User-Agent to Google. Mehrere deutsche Gerichte (z. B. LG München I, 20.01.2022 — 3 O 17493/20) haben die unconsented Übertragung von IP-Adressen über Google Fonts CDN als DSGVO-Verstoß eingestuft. The font stack now resolves to system fonts via the existing fallback chain (`ui-sans-serif`, `system-ui`, `-apple-system`, `BlinkMacSystemFont`, `"Segoe UI"`, `Roboto`). |
| Anything else | n/a | No other third-party request originates from the static surface. |

If Inter ends up needed for visual fidelity on a later marketing pass, self-host the .woff2 files under `/static/fonts/` and serve via `@font-face` from same-origin. Do **not** re-introduce the CDN link.

## Re-audit triggers

Re-run this audit when any of the following ships:

- A third-party script tag (e.g. Stripe.js, Plausible, Sentry browser SDK).
- An analytics tool, even self-hosted (Plausible/Umami add cookies in some configs).
- An external font / icon CDN.
- Any iframe whose `src` is off-origin.
- A `localStorage` key that persists data not directly tied to a user-requested feature.

When you re-audit: update the table above and the date at the top, and either re-confirm "no banner" or add one. The banner module path is reserved at `static/cookie-banner.js` — it does not exist today and should remain absent unless re-audit demands it.
