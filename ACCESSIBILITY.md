<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Accessibility

## Stated target

Helpmefindthejob targets **WCAG 2.2 Level AA** ([W3C
specification](https://www.w3.org/TR/WCAG22/)). Conformance is
iterative; this document is the project's honest record of the
state of that work — what's been audited, what's been fixed, what
remains, and how a contributor can re-run the audit themselves.

The project's standing accessibility doctrine is the same as the
bias-testing doctrine: **no tolerance manipulation**. If axe-core
says it's a violation, it's a violation. The remediation surface is
documented honestly here even when a fix is deferred.

## Honesty note (top of document)

This document is the project's running record of automated
accessibility audits. Three passes have run so far (all 2026-05-19):

1. **First pass — public unauthenticated surfaces** (§3.6 ce48ba5):
   axe-core CLI 4.11 against 8 web-app HTML pages on local
   `python3 app.py` and 5 mkdocs-material docs pages on local
   `mkdocs serve`. 8 violations / 17 nodes pre-fix → 0 / 0 post-fix.
2. **Second pass — authenticated surfaces** (auth-surface slice
   17712ad): Playwright + axe-playwright-python 0.1.7 (bundling
   axe-core 4.10) against 8 authenticated UI states reached by
   logging in as the seeded Aïcha persona. 14 violations pre-fix
   → 0 post-fix.
3. **Third pass — polish trio** (this slice): closes the three
   known gaps the second pass left open.
   - **Sub-slice A: light-mode auth-surface re-run** — runner now
     accepts `--color-scheme {dark,light,both}`; 8 light-mode auth
     states audited. 7 violations pre-fix → 0 post-fix.
   - **Sub-slice B: compliance markdown audit** — `compliance/
     transparency-notice.md` + `compliance/deployer-operating-
     manual.md` brought into the mkdocs nav via a build-hook
     mirror; audited via axe-core CLI. 0 violations on both.
   - **Sub-slice C: dynamic-state coverage** — runner extended
     with 4 dynamic-state audits (cmdk dialog open, disclosure
     expanded, settings rendered, login error state). 1 violation
     pre-fix (cmdk results listbox lacked accessible name) → 0
     post-fix.

**Still not covered** (tracked in "Known gaps" with planned timeline):

- Manual / keyboard-navigation review across the full user journey
  (axe surfaces structural issues but cannot exercise focus-order,
  tab-trap, or keyboard-only-flow questions).
- Screen-reader testing (VoiceOver, NVDA, Orca) of real-world
  flows.
- Mobile / responsive accessibility (touch targets, zoom).
- Light-mode dynamic-state audit (sub-slice C ran dynamic states
  in dark mode only; light-mode preventative fixes were applied
  via the same code paths).

The full conformance bar is a long-term project. This audit pass
establishes the floor + a remediation surface for incremental work.

## Audit methodology

### First pass — public unauthenticated surfaces

| Field | Value |
|---|---|
| Date | 2026-05-19 (§3.6 / ce48ba5) |
| Tool | [axe-core CLI](https://github.com/dequelabs/axe-core-npm) v4.11.4 (axe-core 4.11) |
| Browser | Chrome headless (via axe-core CLI's bundled Chromium driver) |
| Rules | axe-core's default `wcag2a, wcag2aa, wcag21a, wcag21aa, best-practice` set |
| Tolerance manipulation | **None.** axe defaults preserved. |
| Reproduction | See "How to reproduce" below. |

### Second pass — authenticated surfaces

| Field | Value |
|---|---|
| Date | 2026-05-19 (auth-surface slice, follow-on to §3.6) |
| Tool | [axe-playwright-python](https://pypi.org/project/axe-playwright-python/) v0.1.7 + [Playwright](https://playwright.dev/python/) v1.60.0 |
| Browser | Chromium (Playwright's bundled chrome-headless-shell) |
| axe-core version | 4.10 (bundled inside axe-playwright-python 0.1.7) |
| Rules | axe-core's default rule set, same as first pass |
| Tolerance manipulation | **None.** axe defaults preserved. |
| Auth | Aïcha persona seeded via `scripts/seed-personas.py`; sign-in form filled via Playwright |
| Reproduction | `python3 scripts/accessibility-audit-auth-surfaces.py` (see "How to reproduce" below) |

### Third pass — polish trio (light-mode + compliance + dynamic states)

| Field | Value |
|---|---|
| Date | 2026-05-19 (polish-trio slice, follow-on to 17712ad) |
| Tools | axe-playwright-python 0.1.7 (auth + dynamic) + axe-core CLI 4.11 (compliance mkdocs pages) |
| New runner flag | `--color-scheme {dark,light,both}` — Playwright `prefers-color-scheme` emulation + explicit in-app `applyTheme()` call so the project's `[data-theme]` CSS variables resolve to the requested scheme |
| Dynamic states added | (i) cmdk command-palette dialog open; (ii) Suggestions `<details>` disclosure expanded; (iii) settings view with form controls rendered; (iv) sign-in form error state (bad-password submit) |
| Compliance markdown surface | `compliance/transparency-notice.md` + `compliance/deployer-operating-manual.md` mirrored into the mkdocs docs tree via a build hook (`docs/hooks/compliance_mirror.py`) so the canonical compliance files at the repo root stay the single source of truth |
| Tolerance manipulation | **None.** Same discipline as passes 1 + 2. |
| Reproduction | See "How to reproduce" below. |

URLs audited:

**Public web-app surfaces (first pass — served by `app.py` on
localhost:8765):**
- `/` — landing / sign-in
- `/impressum`
- `/privacy`
- `/help`
- `/status`
- `/changelog`
- `/data-retention`
- `/terms`

**Documentation-site surfaces (first pass — served by `mkdocs serve`
on localhost:8001, identical to what GitHub Pages will serve once
`Settings → Pages → Source: GitHub Actions` is flipped — Pages is
still off at audit time, HTTP 404):**
- `/` — `docs/index.md` landing (Aïcha + Käthe friction-class
  vignettes)
- `/mcp-server/`
- `/deployment-recipe/`
- `/production-deployment/`
- `/esco-integration/`

**Authenticated UI states (second pass — Aïcha persona logged in
via Playwright + form-fill on the sign-in form):**
- `01-signin-landing` — pre-login landing (regression check)
- `02-post-login` — immediately after authentication
- `03-jobs` — Jobs view (discovered-jobs queue)
- `04-assistant` — Assistant chat view
- `05-companies` — Companies view (watchlist + suggestions + saved
  searches)
- `06-cv-builder` — CV Builder view (sidebar + section host)
- `07-settings` — Settings view
- `08-dashboard` — Dashboard view

**Third-pass additions — dynamic-state surfaces (Aïcha persona,
dark scheme only; light-mode dynamic-state audit tracked as
known gap):**
- `09-dynamic-cmdk-dialog` — `<dialog id="cmdkDialog">` open
- `10-dynamic-disclosure-open` — companies-view Suggestions
  `<details>` expanded
- `11-dynamic-login-error` — sign-in form after bad-password
  submission (cookies cleared first to reach the sign-in form)
- `12-dynamic-settings-loaded` — settings view with form controls
  rendered

**Third-pass additions — compliance pages (via mkdocs hook
mirror; canonical source remains `compliance/*.md` at repo root):**
- `/compliance/transparency-notice/`
- `/compliance/deployer-operating-manual/`

**Third-pass additions — light-mode auth-surface re-runs:**
- `01-signin-landing-light` through `08-dashboard-light` (the same
  8 auth states as the second pass, audited with the in-app theme
  flipped to light via Playwright's `color_scheme="light"` +
  `applyTheme('light')` JS call after login)

## Current state — verified clean across all audited surfaces

**Every audited surface passes axe-core with zero violations.**

### First-pass surfaces (unauthenticated)

| Surface | Pre-fix violations | Post-fix violations |
|---|---|---|
| App `/` (landing) | 2 (5 nodes) | **0** |
| App `/impressum` | 0 | 0 |
| App `/privacy` | 0 | 0 |
| App `/help` | 0 | 0 |
| App `/status` | 0 | 0 |
| App `/changelog` | 0 | 0 |
| App `/data-retention` | 0 | 0 |
| App `/terms` | 0 | 0 |
| Docs `/` (landing) | 2 (4 nodes) | **0** |
| Docs `/mcp-server/` | 1 | **0** |
| Docs `/deployment-recipe/` | 1 | **0** |
| Docs `/production-deployment/` | 1 | **0** |
| Docs `/esco-integration/` | 1 | **0** |
| **First-pass totals** | **8 violations / 17 nodes** | **0 / 0** |

### Second-pass surfaces (authenticated)

| Authenticated state | Pre-fix critical | Pre-fix serious | Pre-fix moderate | Post-fix |
|---|---|---|---|---|
| `01-signin-landing` | 0 | 0 | 0 | **0** |
| `02-post-login` | 0 | 1 | 1 | **0** |
| `03-jobs` | 0 | 1 | 1 | **0** |
| `04-assistant` | 0 | 1 | 1 | **0** |
| `05-companies` | 0 | 2 | 1 | **0** |
| `06-cv-builder` | 0 | 1 | 2 | **0** |
| `07-settings` | 0 | 1 | 0 | **0** |
| `08-dashboard` | 0 | 1 | 0 | **0** |
| **Second-pass totals** | **0** | **8** | **6** | **0** |

Combined across both passes: **22 violation instances pre-fix → 0
post-fix** in the §3.6 + auth-surface slices. Thresholds NOT
manipulated. axe-core's default rule set preserved.

### Third-pass surfaces — polish trio

**Sub-slice A — light-mode auth-surface re-run:**

| Authenticated state (light) | Pre-fix critical | Pre-fix serious | Pre-fix moderate | Post-fix |
|---|---|---|---|---|
| `01-signin-landing-light` | 0 | 0 | 0 | **0** |
| `02-post-login-light` | 0 | 1 | 0 | **0** |
| `03-jobs-light` | 0 | 1 | 0 | **0** |
| `04-assistant-light` | 0 | 1 | 0 | **0** |
| `05-companies-light` | 0 | 1 | 0 | **0** |
| `06-cv-builder-light` | 0 | 1 | 0 | **0** |
| `07-settings-light` | 0 | 1 | 0 | **0** |
| `08-dashboard-light` | 0 | 1 | 0 | **0** |
| **Sub-slice A totals** | **0** | **7** | **0** | **0** |

**Sub-slice B — compliance markdown:**

| Compliance page | Pre-fix violations | Post-fix |
|---|---|---|
| `/compliance/transparency-notice/` | 0 | **0** |
| `/compliance/deployer-operating-manual/` | 0 | **0** |

(After 6 cross-tree-link warnings in `mkdocs build --strict` were
closed by rewriting the source links to absolute GitHub URLs.)

**Sub-slice C — dynamic states (dark scheme):**

| Dynamic state | Pre-fix critical | Pre-fix serious | Pre-fix moderate | Post-fix |
|---|---|---|---|---|
| `09-dynamic-cmdk-dialog-dark` | 0 | 1 | 0 | **0** |
| `10-dynamic-disclosure-open-dark` | 0 | 0 | 0 | **0** |
| `11-dynamic-login-error-dark` | 0 | 0 | 0 | **0** |
| `12-dynamic-settings-loaded-dark` | 0 | 0 | 0 | **0** |
| **Sub-slice C totals** | **0** | **1** | **0** | **0** |

Combined across all three passes: **30 violation instances pre-fix
→ 0 post-fix**. Thresholds NOT manipulated. axe-core's default
rule set preserved.

## Fixes shipped in the §3.6 first-pass slice

### Fix 1 — App landing page `<main>` landmark

**File**: `static/index.html:30,83` (open + close tags).

**Issue**: `landmark-one-main` (moderate, WCAG 1.3.1 Level A) — the
landing page had no `<main>` landmark. `region` (moderate,
WCAG 1.3.1) — four content blocks (`.auth-brand > div`, the two
form fields, `.legal-links`) lived inside a `<section>` without an
accessible name, so they weren't part of any landmark.

**Fix**: converted `<section id="authGate" class="auth-gate" hidden>`
to `<main id="authGate" class="auth-gate" aria-labelledby="authGateHeading" hidden>`,
and added `id="authGateHeading"` to the `<h1>Helpmefindthejob</h1>`
inside it. The auth-gate is now a properly named `main` landmark.
The auxiliary auth views (forgot-password, reset-password,
accept-invite) were already labelled via `aria-labelledby`; the
inner `<main id="mainContent">` inside `<div id="appShell" hidden>`
continues to be the main landmark for the authenticated state
(only one `<main>` is visible at a time).

**Re-audit verification**: 2 violations / 5 nodes → 0.

### Fix 2 — Docs site inline-link distinguishability

**File**: `docs/stylesheets/accessibility.css` (new).

**Issue**: `link-in-text-block` (serious, WCAG 1.4.1 Level A — Use
of Color) — mkdocs-material's default body-content link styling
relies on color alone to distinguish links from surrounding text.
3 instances on the docs landing page.

**Fix**: added a scoped CSS rule underlining inline body links
inside `.md-content`, excluding theme-managed link classes (any
class starting with `md-` such as `md-button`). The rule does not
touch the theme chrome's link styling.

**Re-audit verification**: 3 nodes → 0.

### Fix 3 — Docs search dialog accessible name

**File**: `docs/javascripts/accessibility.js` (new).

**Issue**: `aria-dialog-name` (serious, WCAG 4.1.2 Level A — Name,
Role, Value) — mkdocs-material renders its search dialog as
`<div class="md-search" data-md-component="search" role="dialog">`
with no `aria-label`, `aria-labelledby`, or `title`. Appears on
every docs-site page (5 instances in this audit).

**Fix**: a small client-side script that, on `DOMContentLoaded`,
sets `aria-label="Site search"` on any `.md-search[role="dialog"]`
that lacks an accessible name. Idempotent. The fix is a workaround
for an upstream theme issue; removing the override is safe when
mkdocs-material ships the fix upstream.

**Re-audit verification**: 5 violations → 0.

## Fixes shipped in the auth-surface follow-on slice

### Fix 4 — `--text-soft` palette colour contrast

**Files**: `static/styles.css:13-20` (dark theme), `:64-70` (light
theme).

**Issue**: `color-contrast` (serious, WCAG 1.4.3 Level AA — Contrast
Minimum). The `--text-soft` palette colour computed to 3.0–3.3:1
against several surface backgrounds in dark mode and 3.56:1 in
light mode — below the required 4.5:1 for normal text. Affected
7 of 8 authenticated states (sidebar workspace label, cmdk-launcher
kbd, segmented-button tab labels, queue.lead description, queue
toolbar text).

**Fix**: bumped dark-mode `--text-soft` from `#6c7587` to `#a0a6b6`
(≈4.8:1 vs surface-2) and light-mode `--text-soft` from `#7a8783`
to `#5a6863` (≈5.5:1 vs bg). Visual hierarchy preserved — text-soft
is still distinct from text + text-muted in both modes, just at a
contrast level that clears WCAG.

**Re-audit verification**: 7 → 0 across the authenticated states.

### Fix 5 — `aria-labelledby="viewTitle"` removed from view sections

**File**: `static/index.html` — 8 `<section>` elements: `#view-dashboard`,
`#view-companies`, `#view-jobs`, `#view-brief`, `#view-settings`,
`#view-assistant`, `#view-cvBuilder`, `#view-searchResults`.

**Issue**: `landmark-unique` (moderate). All 8 view sections shared
the same accessible name via `aria-labelledby="viewTitle"`, and the
visible view's inner `<section class="card" aria-label="Discovered
jobs">` (and similar) created a same-role landmark-collision. axe
flagged the outer view sections as not-uniquely-identifiable.

**Fix**: removed `aria-labelledby="viewTitle"` from all 8 view
sections, demoting them from region landmarks to plain content
containers. The view's `<h1 id="viewTitle">` heading still
identifies the active view; the inner labelled cards remain as
named regions in their own right.

**Re-audit verification**: 4 states (post-login, jobs, assistant,
cv-builder) cleared landmark-unique.

### Fix 6 — Nested complementary landmarks demoted

**Files**: `static/index.html:397` (`.watchlist`), `:1160`
(`#cvBuilderSidebar`).

**Issue**: `landmark-complementary-is-top-level` (moderate, axe best
practice). `<aside class="card watchlist">` was nested inside
`<main>` via the companies view; `<aside id="cvBuilderSidebar">`
was nested similarly inside the CV-builder view. Complementary
landmarks should be top-level (sibling to main), not nested inside
it.

**Fix**: changed the watchlist `<aside>` to a `<section
aria-label="Company watchlist">` (region landmark, allowed inside
main). Changed the CV-builder sidebar from `<aside aria-label="Sections">`
to `<nav aria-label="CV builder sections">` (navigation landmark
for the list of section nav-buttons; nav landmarks are allowed
inside main).

**Re-audit verification**: 2 states (companies, cv-builder) cleared
the nested-complementary finding.

### Fix 7 — View-enter animation no longer dips text contrast

**File**: `static/styles.css:1639-1660`.

**Issue**: `color-contrast` (serious) — every navigation between
views triggered a 220 ms `view-enter` animation that faded the
target view from `opacity: 0` to `opacity: 1`. axe's audit snapshot
could land mid-fade, capturing text at <100% opacity which
composited to below-threshold contrast. Affected the queue.lead +
queue.toolbar.sources lines in `02-post-login`.

**Fix**: removed the `opacity` from the `view-enter` keyframe,
keeping only the `transform: translateY(4px) → none` slide-up. Also
added a `@media (prefers-reduced-motion: reduce)` rule disabling
the animation entirely for users who request reduced motion.

**Re-audit verification**: the queue.lead + queue.toolbar.sources
contrast failures cleared.

### Fix 8 — CV-builder section sidebar uses colour, not opacity

**File**: `static/app.js:4505-4515` (in `_renderCvBuilder`).

**Issue**: `color-contrast` (serious) — the JS that renders the
CV-builder section sidebar set `button.style.opacity` to `"0.5"`
for empty sections and `"0.85"` for filled-but-not-current
sections. The 0.5 opacity computed to ~2.7:1 contrast — below
WCAG 1.4.3.

**Fix**: replaced the inline opacity with explicit colour
hierarchy. The button now uses `var(--text)` when current,
`var(--text-muted)` when filled, or `var(--text-soft)` when empty.
All three tiers clear 4.5:1 against the surface, and the visual
hierarchy is preserved through colour rather than alpha
compositing.

**Re-audit verification**: 9 CV-builder buttons cleared the
color-contrast finding.

### Fix 9 — Two forms labelled "Send a chat message" disambiguated

**File**: `static/index.html:223`.

**Issue**: `landmark-unique` (moderate) — both `#dockChatForm`
(the persistent docked chat input) and `#chatForm` (the main
chat-view input) had `aria-label="Send a chat message"`. Two form
landmarks with the same accessible name on the same page is an
ambiguous AT experience.

**Fix**: renamed `#dockChatForm`'s aria-label to "Quick chat
(docked)". `#chatForm` retains "Send a chat message". The two
forms are now uniquely identifiable to AT.

**Re-audit verification**: assistant state cleared landmark-unique.

### Fix 10 — Refresh button moved out of `<summary>`

**File**: `static/index.html:550-558`.

**Issue**: `nested-interactive` (serious, WCAG 4.1.2) — a focusable
`<button id="suggestBtn">Refresh</button>` was nested inside the
focusable `<summary>` of the Suggestions disclosure widget. Two
stacked focusable controls in the same header region confuse
keyboard + screen-reader users (Enter on summary toggles the
disclosure; Enter on the inner button clicks Refresh — the user
must track focus to know which fires).

**Fix**: moved the Refresh button out of `<summary>` to be the
first child of the disclosure body (inside `<details>` but
outside `<summary>`). The button is still right next to the
heading when the section is expanded; the disclosure-widget
semantic is now clean.

**Re-audit verification**: companies state cleared nested-interactive.

## Fixes shipped in the polish-trio slice

### Fix 11 — Light-mode `--accent` colour contrast

**File**: `static/styles.css:70-76`.

**Issue**: `color-contrast` (serious, WCAG 1.4.3 Level AA) —
the light-mode `--accent: #0d9488` (mint, used as primary-button
background) against white text computed to 3.74:1 — below the
required 4.5:1 for normal text. Affected every primary button
across all 7 auth states (Auto-fit unscored, Send, Find me jobs,
Save, etc.).

**Fix**: darkened light-mode `--accent` from `#0d9488` to
`#0a766b` (≈5.2:1 vs white text). The hover variant + accent-text
+ accent-weak track the same darker base. Dark-mode `--accent`
(`#5eead4`) was already passing and is unchanged.

**Re-audit verification**: 12 primary-button instances cleared
across the 7 light-mode auth states.

### Fix 12 — Chat transcript + input theme-aware shells

**Files**: `static/index.html:1148-1152`, `static/styles.css`
(new `.chat-transcript` + `.chat-input` rules).

**Issue**: `color-contrast` (serious) — `<div id="chatTranscript"
style="background:#13141c;...">` and `<input id="chatInput"
style="background:#1c1c24;border:1px solid #2a2b36;...">` had
hardcoded dark-mode hex colours in their inline styles. In light
mode the body's text colour is `--text: #14201d` (dark), but the
transcript background stayed `#13141c` (also dark) — ~1:1 contrast
on the assistant chat bubbles, effectively invisible text.

**Fix**: replaced inline styles with `.chat-transcript` and
`.chat-input` CSS classes that use `var(--surface)` + `var(--text)`
+ `var(--border)`. Both modes now resolve to high-contrast
combinations.

**Re-audit verification**: assistant state's chat bubbles cleared
in light mode.

### Fix 13 — cmdk results listbox accessible name

**File**: `static/index.html:1396`.

**Issue**: `aria-input-field-name` (serious, WCAG 4.1.2 Level A) —
the `<ul id="cmdkResults" role="listbox">` inside the cmdk dialog
had no `aria-label`, `aria-labelledby`, or `title`. axe surfaced
this only when the dialog was open (dynamic-state audit).

**Fix**: added `aria-label="Command palette results"` to the
listbox.

**Re-audit verification**: dynamic-state-09 cleared.

### Fix 14 — Compliance markdown cross-tree links rewritten

**Files**: `compliance/transparency-notice.md` (1 link),
`compliance/deployer-operating-manual.md` (5 links).

**Issue**: not an axe violation; surfaced by `mkdocs build
--strict` when the two compliance pages were brought into the
docs site. Cross-tree relative links (`../SECURITY.md`,
`../.env.example`, `human-oversight-guide.md` etc.) couldn't be
resolved by mkdocs because the targets live outside the rendered
docs tree.

**Fix**: rewrote 6 relative cross-tree links to absolute GitHub
URLs (`https://github.com/maksodf/helpmefindthejob/blob/main/...`).
The canonical compliance files now render correctly in both the
GitHub UI and the mkdocs site without ambiguity.

**Re-audit verification**: `mkdocs build --strict` green; both
compliance pages cleared with 0 axe violations.

## Fixes shipped in the pre-submission QA pass

### Fix 15 — Pygments code-comment + docstring contrast (light mode)

**File**: `docs/stylesheets/accessibility.css` (new pygments
override block).

**Issue**: `color-contrast` (serious, WCAG 1.4.3 Level AA) —
re-surfaced 2026-05-19 in the pre-submission post-rename axe
re-run across the 5 mkdocs surfaces (root, mcp-server,
deployment-recipe, production-deployment, esco-integration). The
default mkdocs-material pygments theme paints `.c1` (comments),
`.sd` (docstrings), and `.nv` (variable names) at `#717171` on
the `#f5f5f5` code-block background — a contrast ratio of
**4.47:1**, just below the WCAG 2.2 AA 4.5:1 floor. Affected
4 of the 5 mkdocs pages (every page that had a code block with
these pygments classes).

**Fix**: scoped overrides for `.c, .c1, .cm, .cp, .cs, .sd, .nv`
inside `.md-typeset .highlight` under
`[data-md-color-scheme="default"]`, setting `color: #595959`
(~6.1:1 vs `#f5f5f5` — comfortably above the floor with margin
for future palette tweaks). Dark-mode (`scheme="slate"`) was
already passing and is unchanged. The override is light-mode-only.

**Re-audit verification**: all 4 affected mkdocs surfaces
cleared (serious=0).

### Fix 16 — Code-block copy-button nav landmark-uniqueness

**File**: `docs/javascripts/accessibility.js` (new
`patchCodeBlockNavs` function added alongside the existing
`patchSearchDialog`).

**Issue**: `landmark-unique` (moderate, WCAG 1.3.1) — re-surfaced
2026-05-19 in the pre-submission post-rename axe re-run.
mkdocs-material's `content.code.copy` feature wraps each
code-block copy button in `<nav class="md-code__nav">`. When a
page contains more than one code block, axe's `landmark-unique`
rule flags every nav after the first because they all share the
same implicit "navigation" landmark name. Affected the same 4
mkdocs surfaces as Fix 15.

**Fix**: extended `accessibility.js` at DOMContentLoaded to
attach a unique `aria-label` to every `nav.md-code__nav` lacking
one. The label derives from the parent's `id` (`Code block actions
for <id>`) or falls back to a positional counter (`Code block
actions <N>`). Idempotent and safe to remove when mkdocs-material
ships the fix upstream.

**Re-audit verification**: all 4 affected mkdocs surfaces
cleared (moderate=0).

## Append log — confirmation re-runs

| Date | Slice | Surfaces re-audited | Result |
|---|---|---|---|
| 2026-05-19 | Pre-submission QA sweep (post-rename) | 8 app + 5 docs (unauth via axe-core CLI) + 8 auth states × 2 schemes + 4 dynamic states (auth via Playwright) | 0/0/0/0 across all 33 captures after Fix 15 + Fix 16 landed; raw evidence in `audit-results/post-rename-2026-05-19/` (gitignored) and `audit-results/auth-surfaces/`. |

## Known gaps + remediation plan

| Gap | Severity | Where | Why deferred | Planned timeline |
|---|---|---|---|---|
| ~~Authenticated app surfaces (chat, settings, journey, CV builder) not yet axe-audited~~ | — | — | **CLOSED 2026-05-19** by the auth-surface follow-on slice. | — |
| ~~Compliance markdown files not yet in the docs site~~ | — | — | **CLOSED 2026-05-19** by the polish-trio sub-slice B. `compliance/transparency-notice.md` + `compliance/deployer-operating-manual.md` mirrored into the mkdocs site via `docs/hooks/compliance_mirror.py`; both audited at 0 violations. Other compliance/*.md files remain GitHub-rendered (technical artefacts, not user-facing). | — |
| ~~Dynamic-state coverage gaps in the auth-surface runner~~ | — | — | **CLOSED 2026-05-19** by the polish-trio sub-slice C. Runner extended with 4 dynamic-state audits (cmdk dialog, disclosure expanded, settings rendered, login error). | — |
| ~~Auth-surface contrast verified in dark mode only~~ | — | — | **CLOSED 2026-05-19** by the polish-trio sub-slice A. Runner now accepts `--color-scheme {dark,light,both}`; light-mode auth surfaces audited at 0 violations after fixes. | — |
| Manual / keyboard-navigation review | medium | Full app + docs | Automated axe catches structural issues but not all keyboard-trap / focus-order / tab-order issues | NLnet HAN University audit (post-Commons-Conservancy admission) |
| Screen-reader testing (VoiceOver, NVDA, Orca) | medium | Full app | Requires manual testing; not automatable | NLnet HAN University audit (post-Commons-Conservancy admission) |
| Mobile / responsive accessibility (touch targets, zoom) | low | Full app | axe-core CLI tests desktop viewport only; the Playwright runner also tested 1280×800 only | Phase 2 |
| Light-mode dynamic-state coverage | low | Dynamic states under light scheme | Sub-slice C ran dynamic states in dark mode only; the light-mode fixes from sub-slice A propagate to the same code paths but the explicit verification deferred to keep the runner's wall-clock budget reasonable | Phase 2 (extend runner to run dynamic states in both schemes) |
| Other compliance/*.md files not in mkdocs site | low | `compliance/{risk-management-plan,data-governance,technical-documentation,audit-log-schema,human-oversight-guide,accuracy-and-bias-testing,fundamental-rights-impact-assessment-template,eu-database-registration-template,README}.md` | Technical compliance artefacts, not user-facing surfaces; GitHub-rendered. Sub-slice B intentionally scoped to the two user-facing files per the maintainer's §3.6 framing. Adding more would require rewriting their cross-tree links (compliance/technical-documentation alone has 8) | Phase 2 (if any becomes user-facing) |

## NLnet support services (post-Commons-Conservancy admission)

NLnet supports its grantees via a partner ecosystem that includes
**HAN University of Applied Sciences** for accessibility audits. The
HAN audit is available to NGI0-funded projects after Commons
Conservancy programme admission. The project's planning surface
(`docs/grant/04-research-and-decisions.md`) flags the HAN audit as
**conditional on Conservancy admission**; this document is the
canonical record of the project-side accessibility surface that the
HAN audit would build on.

## STANDARDS.md alignment

The WCAG 2.2 AA citation in [STANDARDS.md](STANDARDS.md) names the
target. This document is the operational evidence that the target
is being worked toward, not asserted as already-achieved.

## How to reproduce

### First pass — unauthenticated surfaces (axe-core CLI)

```bash
# 1. Install axe-core CLI (Node 18+ required).
npm install -g @axe-core/cli
axe --version  # expect 4.11.x or later

# 2. Spin up the app locally on 127.0.0.1:8765.
COMPANY_DISCOVERY_HOST=127.0.0.1 \
COMPANY_DISCOVERY_PORT=8765 \
  python3 app.py &

# 3. Build + serve the docs site locally on 127.0.0.1:8001.
pip install -r requirements-dev.txt
mkdocs serve --dev-addr 127.0.0.1:8001 &

# 4. Audit the public app surfaces.
mkdir -p audit-results
for path in / /impressum /privacy /help /status /changelog /data-retention /terms; do
  slug=$(echo "$path" | sed 's|^/||; s|/|-|g')
  [ -z "$slug" ] && slug="root"
  axe "http://127.0.0.1:8765${path}" --save "audit-results/app-${slug}.json"
done

# 5. Audit the docs-site surfaces.
for path in / /mcp-server/ /deployment-recipe/ /production-deployment/ /esco-integration/; do
  slug=$(echo "$path" | sed 's|^/||; s|/$||; s|/|-|g')
  [ -z "$slug" ] && slug="root"
  axe "http://127.0.0.1:8001${path}" --save "audit-results/docs-${slug}.json"
done
```

### Second + third pass — authenticated + dynamic + compliance + light-mode (Playwright + axe-playwright-python + axe-core CLI)

```bash
# 1. Install Playwright + axe-playwright-python (NOT in
#    requirements-dev.txt because the Chromium binary is ~200 MB
#    and would dominate the main dev install).
pip install playwright axe-playwright-python
python3 -m playwright install chromium

# 2. Run the auth-surface audit. The runner spins up its own
#    app.py instance in a tmp data dir, seeds the Aïcha persona,
#    logs in via the sign-in form, walks through 8 authenticated
#    UI states + 4 dynamic states (cmdk, disclosure, login error,
#    settings), in both dark and light colour schemes (12 + 12 =
#    24 axe runs total; default is --color-scheme both). Saves
#    per-state screenshot + axe JSON + violation-summary text to
#    audit-results/auth-surfaces/.
python3 scripts/accessibility-audit-auth-surfaces.py
# Optionally restrict to one scheme:
python3 scripts/accessibility-audit-auth-surfaces.py --color-scheme dark
python3 scripts/accessibility-audit-auth-surfaces.py --color-scheme light

# 3. Audit the compliance pages (require mkdocs serve running):
mkdocs serve --dev-addr 127.0.0.1:8001 &
mkdir -p audit-results/compliance
axe http://127.0.0.1:8001/compliance/transparency-notice/ \
  --save audit-results/compliance/transparency-notice.json
axe http://127.0.0.1:8001/compliance/deployer-operating-manual/ \
  --save audit-results/compliance/deployer-operating-manual.json

# 4. Read the auth-surface summary.
cat audit-results/auth-surfaces/summary.txt
```

The Playwright runner is documented in
[`scripts/accessibility-audit-auth-surfaces.py`](scripts/accessibility-audit-auth-surfaces.py)'s
module docstring. It exits 0 when the audit completes successfully
(regardless of whether violations were found — `summary.txt` is the
answer to "did anything fail").

A `python3 -c` parser reading each JSON file lists violations:

```python
import json
data = json.load(open("audit-results/app-root.json"))
if isinstance(data, list):
    data = data[0]
for v in data.get("violations", []):
    print(f"[{v['impact']}] {v['id']}: {len(v['nodes'])} nodes")
```

## Audit evidence

Raw axe-core JSON output is **not committed to git** — each file is
100–400 KB of axe-core's full rule trace (passes + violations +
incomplete + inapplicable arrays) and would dwarf the source it
audits. `audit-results/` is in `.gitignore`. The audited surfaces +
violation counts are summarised in the "Current state" tables above
(the part that actually matters for review).

Regenerate the JSON locally via the "How to reproduce" commands
above; the files land back in `audit-results/`.

**First-pass (unauthenticated) filenames:**

- App pre-fix: `audit-results/01-root.json` (only the landing page
  showed violations pre-fix; the 7 static legal pages were already 0).
- Docs pre-fix: `audit-results/10-docs-docs-root.json` through
  `14-docs-esco-integration.json`.
- All surfaces post-fix: `audit-results/after-fix-01-landing.json`
  + `after-fix-02-docs-landing.json` through `after-fix-06-docs-esco.json`.

**Second + third-pass filenames** — written by
`scripts/accessibility-audit-auth-surfaces.py` into
`audit-results/auth-surfaces/`. The runner now produces a
`<state>-<scheme>` suffix; the same 12 state IDs are audited per
scheme:

- Base states (1–8): `01-signin-landing-<scheme>` through
  `08-dashboard-<scheme>`
- Dynamic states (9–12, dark only by default):
  `09-dynamic-cmdk-dialog-dark`,
  `10-dynamic-disclosure-open-dark`,
  `11-dynamic-login-error-dark`,
  `12-dynamic-settings-loaded-dark`
- `summary.txt` — per-state + per-scheme + grand-total counts.

**Compliance-page filenames** — written by axe-core CLI into
`audit-results/compliance/`:

- `transparency-notice.json`
- `deployer-operating-manual.json`

The two slice commit messages — §3.6 (`§3.6 accessibility audit +
ACCESSIBILITY.md (first automated pass + remediation plan)`) and
the auth-surface follow-on — capture the violation counts at
commit time. Each subsequent dated audit appends its own counts
to the "Current state" tables.

## Future-runs procedure

The next dated accessibility audit should:

1. Re-run the public-surface sweep above on the new state of the
   code; surface any regressions.
2. Bring authenticated surfaces into scope (puppeteer-based
   runner with form-fill).
3. Bring compliance markdown into scope (either as mkdocs pages
   or as a separate audit pipeline that lints the source markdown
   for heading hierarchy + alt text on any embedded images).
4. Track the running diff: how many new violations did this commit
   introduce vs how many were closed.
