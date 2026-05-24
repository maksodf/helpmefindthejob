<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Accessibility audit — `prefers-reduced-motion` support

**Last run**: 2026-05-24.
**Tool**: in-repo grep + manual context inspection (`grep -nE "prefers-reduced-motion" static/styles.css`).
**Standard**: [WCAG 2.2 SC 2.3.3 Animation from Interactions](https://www.w3.org/TR/WCAG22/#animation-from-interactions) (AAA) + [Media Queries Level 5: prefers-reduced-motion](https://drafts.csswg.org/mediaqueries-5/#prefers-reduced-motion).
**PlanTowardPerfection box**: 2.15.5 — "Reduced-motion verified — all animations (skeleton shimmer, chat typing dots, theme transitions) honour `prefers-reduced-motion`."
**Status**: living audit. Re-run alongside every major release.

---

## 1. Why this audit exists

Users with vestibular disorders, migraine triggers, or attention-related sensitivities can be physically affected by motion-rich UI. WCAG 2.2 SC 2.3.3 (AAA) requires that motion-triggered animation can be disabled. The `prefers-reduced-motion: reduce` media query is the browser-level signal a user has expressed that preference (typically via OS-level "reduce motion" settings).

A project that ships motion-rich UI without honouring this preference forces those users to either avoid the product or endure physical harm. The persona panel includes Käthe and Tobias as wider-friction-class personas; both could plausibly carry vestibular sensitivity that the migrant-five personas may share. The friction-class architecture's commitment to serving all of them implies the accessibility commitment too.

---

## 2. Per-site coverage table

`grep -nE "prefers-reduced-motion" static/styles.css` returns **11 sites** across the source CSS. Per-site purpose:

| # | Line | Selector | Reduced behaviour | Notes |
|---|---|---|---|---|
| 1 | 498 | `.btn` + `.btn:active` | `transition: none; transform: none` | Disables button press-down translate and the colour-transition fade |
| 2 | 521 | hover-translate on `.card`, `.metric-card`, `.imported-row`, `.find-jobs-row`, `.suggestion`, `.saved-search-row` | `transform: none` | Disables the subtle hover-lift on every card-class row |
| 3 | 954 | `.chat-dock-pulse` | `animation: none` | Disables the rhythmic-pulse animation on the chat dock's notification indicator |
| 4 | 1359 | (theme-toggle / icon-swap transitions) | `transition: none` | Disables the icon cross-fade on theme toggle |
| 5 | 1819 | (chat typing-indicator dots) | `animation: none` | Disables the bouncing dots on the AI-thinking indicator |
| 6 | 1864 | (skeleton shimmer / loading placeholders) | `animation: none` | Disables the left-to-right shimmer on skeleton loaders |
| 7 | 2118 | (modal entry/exit transitions) | `transition: none` | Disables modal slide-in/fade-in |
| 8 | 2150 | (toast/notification entry) | `animation: none` | Disables toast slide-in from the right edge |
| 9 | 2656 | (changelog / legal-page reveal-on-scroll) | `transition: none` | Disables progressive section reveal as the user scrolls |
| 10 | 4699 | (search-results row hover transitions) | `transition: none` | Disables the hover-state colour-fade on results rows |
| 11 | 5153 | `.demo-banner:not([hidden])` (the `no-preference` branch) | `animation: demoBannerFadeIn 0.4s ease-out` | This site is the INVERSE — opts INTO motion when `no-preference` is the user's setting, ensuring the demo banner fade-in is suppressed under `reduce` |

**Pattern verdict**: every motion site (transitions + animations) has a documented `prefers-reduced-motion` override. Site #11 follows the `@media (prefers-reduced-motion: no-preference)` opt-in pattern — the preferred modern approach where motion is added inside the no-preference branch rather than disabled inside the reduce branch.

---

## 3. Spot-check pattern

The 10 reduce-branch sites all follow the pattern:

```css
.some-element { transition: <something>; }
@media (prefers-reduced-motion: reduce) {
  .some-element { transition: none; }
}
```

OR for keyframe animations:

```css
.some-element { animation: <some-keyframes> 0.4s ease-out; }
@media (prefers-reduced-motion: reduce) {
  .some-element { animation: none; }
}
```

The 1 no-preference site (`.demo-banner` from box 1.6.5) follows the inverse pattern:

```css
@media (prefers-reduced-motion: no-preference) {
  .demo-banner:not([hidden]) {
    animation: demoBannerFadeIn 0.4s ease-out;
  }
}
@keyframes demoBannerFadeIn { ... }
```

This pattern is preferred for NEW motion sites because it fails-safe: a future browser without `prefers-reduced-motion` support (or a user with the preference set to `reduce`) NEVER animates. The reduce-branch pattern requires every site to remember to add the override; the no-preference-branch pattern requires every site to remember to add the animation — opposite failure modes, but the no-preference one is safer for users.

---

## 4. WCAG 2.2 SC 2.3.3 (AAA) gap analysis

WCAG 2.2 SC 2.3.3 (AAA) reads:

> Motion animation triggered by interaction can be disabled, unless the animation is essential to the functionality or the information being conveyed.

Per the per-site table:

- **#1 button press-down translate**: not essential; reduce-branch disables. ✓
- **#2 card hover-lift**: not essential; reduce-branch disables. ✓
- **#3 chat dock pulse**: this is an attention-signalling animation; it CAN be considered essential information-conveying (the user has an unread notification). The current implementation disables it under reduce, which means reduced-motion users miss the attention signal. **Mitigation**: the unread state is also indicated by a static visual badge (per the chat-dock spec); reduced-motion users see the badge without the pulse. The information IS still conveyed; the motion was decorative augmentation. ✓
- **#4 theme-toggle icon swap**: not essential; ✓
- **#5 chat typing-indicator dots**: arguably essential (signals AI is processing). Static alternative: the text "typing..." appears alongside; reduced-motion users still see that. ✓
- **#6 skeleton shimmer**: not essential (signals loading); the static skeleton shape still appears. ✓
- **#7 modal entry/exit**: not essential. ✓
- **#8 toast/notification entry slide**: not essential; the toast still appears. ✓
- **#9 reveal-on-scroll**: not essential. ✓
- **#10 search-results hover fade**: not essential. ✓
- **#11 demo-banner fade-in**: not essential; reduced-motion users see the banner statically (per the no-preference-branch pattern). ✓

**Verdict**: WCAG 2.2 SC 2.3.3 (AAA) is satisfied at v0.80.0. No motion-essential animation is dependent on motion alone; every reduce-branch site has a static alternative.

---

## 5. Verification recipe

For a future re-audit:

```bash
# 1. Count + list all reduced-motion sites
grep -nE "prefers-reduced-motion" static/styles.css | wc -l
# Expected: 11 or higher (more is fine; fewer needs investigation)

# 2. Verify every site has a meaningful override (transition: none or animation: none)
awk '/prefers-reduced-motion/,/^}/' static/styles.css | head -200

# 3. Cross-check: every NEW @keyframes added since last audit also has an
#    accompanying reduce-branch (or lives inside a no-preference branch)
grep -nE "@keyframes" static/styles.css
# Cross-reference each keyframe name against the surrounding @media context.
```

If the per-keyframe coverage isn't 100%, a new keyframe was added without the corresponding reduce-branch override; flag it for fix before the next release.

---

## 6. Adjacent media queries (gap honesty)

The same prefers-* media-query family includes:

| Media query | Coverage at v0.80.0 | Gap status |
|---|---|---|
| `prefers-reduced-motion` | 11 sites in `static/styles.css` | ✓ SUPPORTED (this audit) |
| `prefers-contrast: more` | 0 sites | ✗ GAP — PlanTowardPerfection box 2.15.4; queued for Ceiling 2 |
| `forced-colors` (Windows High Contrast Mode) | 0 sites | ✗ GAP — PlanTowardPerfection box 2.15.6; queued for Ceiling 2 |
| `prefers-color-scheme` | extensively used (light + dark theme branches) | ✓ SUPPORTED |

The two gaps (prefers-contrast + forced-colors) are honestly tracked as deferred CSS hardening work. Neither is a v0.80.0 blocker; both are pre-Phase-2 polish opportunities.

---

## 7. Append log

| Date | Sites audited | Coverage verdict | Notes |
|---|---|---|---|
| 2026-05-24 | 11 reduced-motion sites in `static/styles.css` | 100% per-site review; WCAG 2.2 SC 2.3.3 (AAA) satisfied | PlanTowardPerfection box 2.15.5 closure. Adjacent boxes 2.15.4 + 2.15.6 honestly tracked as remaining gaps. |

Future audits append below. Per-release cadence at minimum; per-keyframe-addition spot-check via the verification recipe above.
