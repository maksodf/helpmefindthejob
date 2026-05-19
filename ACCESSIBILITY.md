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

This is the **first** automated accessibility audit pass executed
against the project (2026-05-19, execution-plan §3.6). It covers
the public unauthenticated HTML surfaces of the web app + the
mkdocs-material documentation site. **It does NOT yet cover**:

- Authenticated app surfaces (chat, settings, journey state machine,
  CV builder) — axe-core CLI doesn't natively handle session-based
  auth; deferred to a follow-on slice that adds a puppeteer-based
  axe runner.
- Compliance markdown files (`compliance/*.md`) — currently
  GitHub-rendered, not served by mkdocs or the app; GitHub-rendered
  markdown accessibility depends on GitHub's stylesheets which are
  outside the project's control. A follow-on slice can bring these
  into the mkdocs site for native auditing.
- Manual / keyboard-navigation review across the full user journey.
- Screen-reader testing (VoiceOver, NVDA, Orca) of real-world flows.

The full conformance bar is a long-term project. This audit pass
establishes the floor + a remediation surface for incremental work.

## Audit methodology

| Field | Value |
|---|---|
| Date | 2026-05-19 |
| Tool | [axe-core CLI](https://github.com/dequelabs/axe-core-npm) v4.11.4 (axe-core 4.11) |
| Browser | Chrome headless (via axe-core CLI's bundled Chromium driver) |
| Rules | axe-core's default `wcag2a, wcag2aa, wcag21a, wcag21aa, best-practice` set |
| Tolerance manipulation | **None.** axe defaults preserved. |
| Reproduction commands | See "How to reproduce" below. |

URLs audited:

**Public web-app surfaces (served by `app.py` on localhost:8765):**
- `/` — landing / sign-in
- `/impressum`
- `/privacy`
- `/help`
- `/status`
- `/changelog`
- `/data-retention`
- `/terms`

**Documentation-site surfaces (served by `mkdocs serve` on
localhost:8001, identical to what GitHub Pages will serve once
`Settings → Pages → Source: GitHub Actions` is flipped — Pages is
still off at audit time, HTTP 404):**
- `/` — `docs/index.md` landing (Aïcha + Käthe friction-class
  vignettes)
- `/mcp-server/`
- `/deployment-recipe/`
- `/production-deployment/`
- `/esco-integration/`

## Current state — verified clean

**Every audited surface now passes axe-core with zero violations.**

| Surface | First-pass violations | After-fix violations |
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
| **TOTAL** | **8 violations / 17 nodes** | **0 violations / 0 nodes** |

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

## Known gaps + remediation plan

| Gap | Severity | Where | Why deferred | Planned timeline |
|---|---|---|---|---|
| Authenticated app surfaces (chat, settings, journey, CV builder) not yet axe-audited | medium | Web app behind session auth | axe-core CLI doesn't natively do form-fill / cookie-injection; needs a puppeteer-based runner | Phase 1 close if time, else Phase 2 |
| Compliance markdown files not yet in the docs site | medium | `compliance/*.md` (12 files) | This slice's mkdocs site links to GitHub-rendered compliance files; native auditing would require including them in the site | Phase 2 |
| Manual / keyboard-navigation review | medium | Full app + docs | Automated axe catches many issues but not all keyboard-trap / focus-order issues | Phase 1 close if time, else NLnet HAN University audit |
| Screen-reader testing (VoiceOver, NVDA, Orca) | medium | Full app | Requires manual testing; not automatable | NLnet HAN University audit (post-Commons-Conservancy admission) |
| Mobile / responsive accessibility (touch targets, zoom) | low | Full app | axe-core CLI tests desktop viewport only | Phase 2 |
| Color contrast on dark + light themes — full sweep | low | Static CSS | Initial axe passes did not flag color-contrast issues but the audit ran in light-mode default; dark-mode sweep TBD | Phase 1 close if time |

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
violation counts are summarised in the "Current state" table above
(the part that actually matters for review).

Regenerate the JSON locally via the "How to reproduce" commands
below; the files land back in `audit-results/`. Filenames the
§3.6 first-pass slice produced (regeneration overwrites them):

- App pre-fix: `audit-results/01-root.json` (only the landing page
  showed violations pre-fix — the 7 static legal pages /impressum
  /privacy /help /status /changelog /data-retention /terms were
  already 0 violations).
- Docs pre-fix: `audit-results/10-docs-docs-root.json` through
  `audit-results/14-docs-esco-integration.json` (one file per docs
  page).
- All surfaces post-fix: `audit-results/after-fix-01-landing.json`
  + `audit-results/after-fix-02-docs-landing.json` through
  `audit-results/after-fix-06-docs-esco.json`.

The §3.6-slice commit message (`§3.6 accessibility audit +
ACCESSIBILITY.md (first automated pass + remediation plan)`)
captures the violation counts at commit time. Each subsequent
dated audit appends its own counts to the "Current state" table.

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
