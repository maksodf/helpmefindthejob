<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 DirectJob Scout contributors -->

# Accessibility

## Stated target

DirectJob Scout targets **WCAG 2.2 Level AA** ([W3C
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
accessibility audits. Two passes have run so far (both 2026-05-19):

1. **First pass — public unauthenticated surfaces** (§3.6 ce48ba5):
   axe-core CLI 4.11 against 8 web-app HTML pages on local
   `python3 app.py` and 5 mkdocs-material docs pages on local
   `mkdocs serve`. 8 violations / 17 nodes pre-fix → 0 / 0 post-fix.
2. **Second pass — authenticated surfaces** (auth-surface slice,
   below): Playwright + axe-playwright-python 0.1.7 (bundling
   axe-core 4.10) against 8 authenticated UI states (sign-in
   landing, post-login, jobs, assistant, companies, CV builder,
   settings, dashboard) reached by logging in as the seeded Aïcha
   persona. 14 violations pre-fix → 0 post-fix.

**Still not covered** (tracked in "Known gaps" with planned timeline):

- Compliance markdown files (`compliance/*.md`) — currently
  GitHub-rendered, not served by mkdocs or the app; GitHub-rendered
  markdown accessibility depends on GitHub's stylesheets which are
  outside the project's control. A follow-on slice can bring these
  into the mkdocs site for native auditing.
- Manual / keyboard-navigation review across the full user journey
  (axe-core surfaces structural issues but cannot exercise focus-
  order, tab-trap, or keyboard-only-flow questions).
- Screen-reader testing (VoiceOver, NVDA, Orca) of real-world
  flows.
- Mobile / responsive accessibility (touch targets, zoom).

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
and added `id="authGateHeading"` to the `<h1>DirectJob Scout</h1>`
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

## Known gaps + remediation plan

| Gap | Severity | Where | Why deferred | Planned timeline |
|---|---|---|---|---|
| ~~Authenticated app surfaces (chat, settings, journey, CV builder) not yet axe-audited~~ | — | — | **CLOSED 2026-05-19** by the auth-surface follow-on slice (Playwright + axe-playwright-python runner at `scripts/accessibility-audit-auth-surfaces.py`). 8 authenticated states now audited at 0 violations each. | — |
| Compliance markdown files not yet in the docs site | medium | `compliance/*.md` (12 files) | The §3.6 mkdocs site links to GitHub-rendered compliance files; native auditing would require including them in the site | Phase 2 |
| Manual / keyboard-navigation review | medium | Full app + docs | Automated axe catches many issues but not all keyboard-trap / focus-order / tab-order issues | Phase 1 close if time, else NLnet HAN University audit |
| Screen-reader testing (VoiceOver, NVDA, Orca) | medium | Full app | Requires manual testing; not automatable | NLnet HAN University audit (post-Commons-Conservancy admission) |
| Mobile / responsive accessibility (touch targets, zoom) | low | Full app | axe-core CLI tests desktop viewport only; the Playwright runner also tested 1280×800 only | Phase 2 |
| Dynamic-state coverage gaps in the auth-surface runner | low | Authenticated app | The runner audits each view's initial-render state; modal dialogs, expanded disclosures, error states, post-form-submit states are NOT covered yet | Phase 2 (extend runner with more state transitions) |
| Auth-surface contrast verified in dark mode only | low | Light-mode theme | The Playwright runner inherited Chromium's default colour scheme (dark). The light-mode `--text-soft` was bumped to clear 4.5:1 as a preventative fix, but light-mode runs against the auth surfaces have not been verified | Phase 2 (add a `--theme=light` Playwright run) |

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

### Second pass — authenticated surfaces (Playwright + axe-playwright-python)

```bash
# 1. Install Playwright + axe-playwright-python (NOT in
#    requirements-dev.txt because the Chromium binary is ~200 MB
#    and would dominate the main dev install).
pip install playwright axe-playwright-python
python3 -m playwright install chromium

# 2. Run the audit. The runner spins up its own app.py instance in
#    a tmp data dir, seeds the Aïcha persona, logs in via the
#    sign-in form, walks through 8 authenticated UI states, and
#    saves per-state screenshot + axe JSON + violation-summary text
#    to audit-results/auth-surfaces/.
python3 scripts/accessibility-audit-auth-surfaces.py

# 3. Read the summary.
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

**Second-pass (authenticated) filenames** — written by
`scripts/accessibility-audit-auth-surfaces.py` into
`audit-results/auth-surfaces/`:

- `01-signin-landing.{png,json,txt}` — pre-login regression check
- `02-post-login.{png,json,txt}`
- `03-jobs.{png,json,txt}`
- `04-assistant.{png,json,txt}`
- `05-companies.{png,json,txt}`
- `06-cv-builder.{png,json,txt}`
- `07-settings.{png,json,txt}`
- `08-dashboard.{png,json,txt}`
- `summary.txt` — per-state violation counts in one file.

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
