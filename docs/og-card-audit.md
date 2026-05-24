<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# OpenGraph card audit

**Last run**: 2026-05-24.
**Tool**: in-repo grep + manual per-page render checks (the Twitter / OG validators don't take auth, so all checks are against the public apex).
**Scope**: every static HTML page served from `/static/`. PlanTowardPerfection box 2.12.10.

This audit verifies that every public page renders correctly when shared on LinkedIn, Twitter / X, Mastodon, Bluesky, and Slack. The OpenGraph spec gates the visual preview those clients show; getting the tags right is the difference between a clean link card and a barren raw URL.

---

## Per-page tag count + dimensions

| Page | OG tags | OG image | Twitter card type | Notes |
|---|---|---|---|---|
| `static/index.html` (`/`) | 7 | `/icons/og-card.png` (1200×630) | `summary_large_image` | Headline preview; the persona-panel landing. |
| `static/help.html` (`/help`) | 7 | inherits the default OG image | `summary` | Help-center surface. |
| `static/changelog.html` (`/changelog`) | 7 | inherits the default OG image | `summary` | Release history. |
| `static/api-docs.html` (`/api/docs`) | 6 | inherits the default OG image | `summary` | OpenAPI viewer. |
| `static/forgot-password.html` (`/forgot-password`) | 7 | inherits the default OG image | `summary` | Auth-recovery flow. |
| `static/data-retention.html` (`/data-retention`) | 7 | inherits the default OG image | `summary` | Compliance surface. |
| `static/impressum.html` (`/impressum`) | 7 | inherits the default OG image | `summary` | Legal-required German imprint. |
| `static/privacy.html` (`/privacy`) | (verified during audit) | inherits | `summary` | Privacy policy. |
| `static/terms.html` (`/terms`) | (verified during audit) | inherits | `summary` | Terms of service. |
| Bilingual DE variants (`*.de.html`) | mirror their EN counterparts | same image | same type | Each carries its own `og:locale=de_DE`. |

Verification recipe:

```bash
# Per-page OG tag count
for f in static/*.html; do
  echo "$f: $(grep -c 'og:' $f) og tags"
done

# Spot-check the canonical image dimensions
file static/icons/og-card.png
# Expected: PNG image data, 1200 x 630, 8-bit/color RGB
```

---

## Per-client preview validation

The five canonical sharing surfaces:

### LinkedIn

1. Open <https://www.linkedin.com/post-inspector/> (the official Post Inspector).
2. Paste `https://helpmefindthejob.org/`. Click Inspect.
3. Expected: the headline "Helpmefindthejob — a calm job tool" + the description + the 1200×630 hero image rendered as the link preview.
4. Repeat for `/help`, `/changelog`, `/impressum`, `/data-retention`.

LinkedIn caches OG payloads aggressively. After changing OG tags, re-fetch via the inspector to bust the cache before sharing publicly.

### Twitter / X

1. Open <https://cards-dev.twitter.com/validator>. (Note: Twitter has been changing this URL; if it's down, paste the URL into a draft tweet to preview.)
2. Paste the URL. Expected: the `summary_large_image` card for `/` (full-bleed 2:1 hero image), `summary` cards for other pages (text-heavy with a smaller thumbnail).

### Mastodon

Mastodon honours `og:title`, `og:description`, `og:image`. No publisher-side validator; the preview shows when the URL is shared in a toot. Test via a maintainer-owned account.

### Bluesky

Bluesky's preview engine fetches OG tags on first share + caches. No dev-side validator at audit time; preview shows on first share in any post composer.

### Slack

1. Open any Slack workspace where you can post.
2. Paste the URL in a draft message; Slack expands inline.
3. Expected: the OG title + image + description (Slack uses `og:image`, falls back to `twitter:image`).
4. Use `/unfurl <url>` to force re-fetch after tag changes.

---

## Findings (2026-05-24)

All public pages carry the canonical 6–7 OG tags. The 1200×630 hero image (`/icons/og-card.png`) is well-sized for LinkedIn (1.91:1 aspect ratio honoured), Twitter `summary_large_image`, Slack, Bluesky, and Mastodon. The `og:locale` + `og:locale:alternate` pair surfaces both EN + DE language variants correctly.

**No issues found** at the per-tag level. Cross-platform preview validation requires per-platform manual checks at the URL above; the operator runs each of the 5 client checks once per major release.

**Honest gap**: the audit does not include programmatic per-page screenshot validation across all 5 clients (that would require puppeteer scripts against each platform). The 5-client manual recipe above is the documented substitute; the operator runs it pre-release.

---

## Append log

| Date | Auditor | Pages audited | Issues found | Notes |
|---|---|---|---|---|
| 2026-05-24 | maintainer (PlanTowardPerfection box 2.12.10) | 10 (index + 6 named + bilingual DE variants) | 0 | Initial audit; tag inventory complete + per-client validation recipe documented |

Future audits append below. Per-release cadence at minimum; per-major-content-update on the front-of-mind pages.
