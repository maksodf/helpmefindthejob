<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Changelog

All notable changes to **Helpmefindthejob** are documented in this file.

The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/)
and the project adheres to [Semantic Versioning 2.0.0](https://semver.org/).

Section order per release: **Added · Changed · Deprecated · Removed ·
Fixed · Security**.

---

## [Unreleased]

Tracked in `docs/grant/02-execution-plan.md` §3.4 – §4.6 plus Phase 2 cleanup
items in `docs/grant/03-post-grant.md`.

This block covers every commit landed on `claude/project-analysis-bpHCo`
between the `v0.1.0` tag (commit `0cdf13e`) and the pre-submission
scope-tightening slice. Cuts into a future v0.2.0 once the maintainer
green-lights the application + closes the maintainer-side actions
listed under "Maintainer follow-ups" in
[`docs/grant/quality-dashboard-2026-05-19.md`](docs/grant/quality-dashboard-2026-05-19.md).

### Added

- **Project renamed to Helpmefindthejob** with the canonical domain at
  `helpmefindthejob.com` ([Decision 22](docs/grant/04-research-and-decisions.md#decision-22-project-rename--directjob-scout--helpmefindthejob),
  forward-going per Decision 12). 271 files renamed; intentional
  dual-name content preserved in the identity-of-record files
  (`CHANGELOG.md`, `CONTRIBUTORS-NOTE.md`, `docs/releases/v0.1.0*`,
  `docs/grant/04-research-and-decisions.md`).
- **`company_discovery/env_compat.py`** — env-var compatibility shim
  exposing `get_env(new, legacy, default)`, `get_env_int`, and
  `get_env_bool`. Tries the canonical `HELPMEFINDTHEJOB_*` prefix
  first; falls back to `DIRECTJOB_*` and `COMPANY_DISCOVERY_*` with
  a `DeprecationWarning`. Tests in `tests/test_env_compat.py`
  (17 cases). Doctrine + migration path in
  [`docs/deployment-recipe.md`](docs/deployment-recipe.md).
- **Audit-log production fail-fast** — when the application
  environment is anything other than `development`/`dev`/`test`/
  `testing`, `_resolve_salt` refuses to start without
  `HELPMEFINDTHEJOB_AUDIT_SALT` (legacy `DIRECTJOB_AUDIT_SALT`).
  6 regression tests in
  `tests/test_phase13_audit_log.py::SaltFailFastTests`. Documented
  in [`compliance/audit-log-schema.md`](compliance/audit-log-schema.md).
- **Quality dashboard** at
  [`docs/grant/quality-dashboard-2026-05-19.md`](docs/grant/quality-dashboard-2026-05-19.md)
  capturing every PART 1–7 probe result from the pre-submission
  comprehensive QA pass (1020 / 1029 tests across Python 3.9 + 3.12,
  axe-core + axe-playwright accessibility coverage, cosign verify,
  fresh-clone Docker, ESCO/EURES surface counts).
- **Phase 2 backlog index** at
  [`docs/grant/phase2-backlog-2026-05-19.md`](docs/grant/phase2-backlog-2026-05-19.md)
  enumerating ~53 inventory items tracked for post-grant cycles
  (2026 Q3 / Q4 / 2027 Q1).
- **mkdocs-material documentation site** (§3.5) with deploy workflow
  to GitHub Pages and `mkdocs build --strict` green.
- **OpenSSF Scorecard SHA-pinning** — all 6 GitHub Actions workflows
  pinned to full 40-char commit SHAs (`scorecard.yml`, `test.yml`,
  `quality.yml`, `mcp-integration.yml`, `fresh-clone-install.yml`,
  `docs-publish.yml`).
- **`ACCESSIBILITY.md`** (§3.6) — three audit passes documenting
  the first automated WCAG 2.2 AA pass + auth-surface follow-on
  via Playwright + light-mode / dynamic-state polish; cumulative
  32 violation instances closed across 22 (later 33) audited
  captures. Fix 15 + Fix 16 from the pre-submission slice closed
  pygments-contrast + landmark-unique regressions surfaced on
  the post-rename re-audit.
- **`docs/translating.md`** (§3.7) — translator contributor
  pathway (terminology hygiene, parity test, preserved-German-
  terms lint, HTML fallback drift contract).
- **Nix flake** (§3.8) at [`flake.nix`](flake.nix) pinning
  `nixos-25.05` (commit `ac62194`); `nix flake check` and
  `nix develop --command python3 -m unittest discover -s tests`
  both green on aarch64-darwin.
- **cosign-signed v0.1.0 + CycloneDX 1.6 SBOM + RFC 9116
  security.txt** (§4.2). Cosign key model b (long-lived ECDSA
  P-256, `--insecure-ignore-tlog`); SBOM with 91 components;
  security.txt at [`static/.well-known/security.txt`](static/.well-known/security.txt)
  citing `helpmefindthejob.com` as the canonical reporting URL.
- **`SUSTAINABILITY.md`** (§4.1) — post-grant story, grant arc,
  community pathway.
- **Application draft** at
  [`docs/grant/application-draft-2026-05-19.md`](docs/grant/application-draft-2026-05-19.md)
  (22 fields, ~13.5k words); NLnet form-fields cross-reference at
  [`docs/grant/nlnet-form-fields-2026-05-19.md`](docs/grant/nlnet-form-fields-2026-05-19.md);
  outreach drafts at [`docs/grant/outreach-drafts/`](docs/grant/outreach-drafts/);
  external-reader recruit message at
  [`docs/grant/external-reader-recruit-message-2026-05-19.md`](docs/grant/external-reader-recruit-message-2026-05-19.md).
- **Bias-testing dated reports** —
  [`bias-testing-2026-05-18.md`](docs/grant/bias-testing-2026-05-18.md),
  [`bias-testing-2026-05-18-broadened.md`](docs/grant/bias-testing-2026-05-18-broadened.md),
  [`bias-testing-2026-05-18-polish.md`](docs/grant/bias-testing-2026-05-18-polish.md),
  [`bias-testing-2026-05-19.md`](docs/grant/bias-testing-2026-05-19.md).
- **`friction_keywords_for(persona_id)`** helper in
  `company_discovery/persona_fixtures.py`, wired into the production
  chat-router CV-tailoring path at `app.py:3411` + `app.py:7702`
  (closes deferred remediation #1 of the prompt-enhancement
  bias-test run; 6 regression tests in `tests/test_round4.py`).
- **`CONTRIBUTORS-NOTE.md`** rename-paragraph + git-archaeology
  guidance for the 2026-05-19 rename.

#### 13-plan + post-sprint slices (2026-05-21 → 2026-05-22)

The 13-plan was an agent-doable engineering slice tackling the most
impactful operator-independent gaps surfaced by the pre-submission
audit. Items below are commit-mapped to the working branch
`claude/project-analysis-bpHCo`.

- **Alert delivery E2E + dead-subscription pruning** (item 1/13,
  gap #9) — Web Push reliability hardened end-to-end; subscribers
  that 410/404 are auto-pruned from the database after the second
  failed delivery; classified failure modes feed observability.
  Commit `4e3a728`.
- **PWA / offline mode verified + pre-rename residue purged**
  (item 2/13, gap #2) — service-worker cache strategy validated;
  manifest icons refreshed; offline fallback shell verified
  end-to-end on a real device. Commit `3f62f86`.
- **Apply→reply→interview funnel UI** (item 3/13, gap #10) —
  outcome-tracking surface for the user-side funnel; backed by
  `record_user_outcome` MCP tool. Commit `d242e1a`.
- **Workspace admin endpoints + member-management UI** (item 4/13,
  gap #22) — invite / role-change / revoke / member list with
  guardrails on demotion of last admin. Commits `163f526` +
  `93cd0ad`.
- **Feature-flag runtime substrate** (item 5/13, gap #18) —
  per-deployer overrides via env var or admin endpoint;
  audit-logged toggles. Commit `cdaa645`.
- **A/B testing framework** (item 6/13, gap #19) — deterministic
  hash-based bucketing with sticky assignment + opt-in analytics
  events. Commit `4428c45`.
- **Public REST API mirroring the MCP catalogue** (item 7/13,
  gap #28) — `/api/public/v1/*` for the MCP tools, JSON-Schema
  validated, OpenAPI surface. Commit `0234916`.
- **Python SDK for partner agents** (item 8/13, gap #29) — small
  client library wrapping the public REST API + stdio MCP
  catalogue, Apache 2.0, single-file install. Commit `9d07ffe`.
- **Background job queue** (item 9/13, gap #14) — durable in-DB
  queue with retry + dead-letter, used for slow MCP operations
  (career-page scans, bulk dedup). Commit `7779cdf`.
- **SSR for SEO** (item 10/13, gap #14) — dynamic
  `/sitemap.xml` + `/robots.txt` (fixed Week-1 `khalo.org`
  sanitization residue at root), per-page hreflang en/de/x-default,
  JSON-LD WebPage on every static surface, Organization + WebSite
  + SoftwareApplication schemas on index.html, JSON-LD enrichment
  for SSR `/jobs/<slug>` landings, `_xss_safe_jsonld` OWASP
  defense-in-depth helper. +26 tests at `tests/test_seo_ssr.py`.
  Commit `17f7707`.
- **PostgreSQL backend for primary repository** (item 11/13,
  gap #13) — `PostgresCompanyDiscoveryRepository` opt-in via
  `HELPMEFINDTHEJOB_DATABASE_URL`; mirrors the SQLite
  repository's full save/get/list/delete surface; encryption-at-
  rest pass-through for `cv_text` + `cv_photo_data_uri`. 18 tests
  including 7 live PG against real PostgreSQL 15.18.
  Commit `6bf2988`.
- **SSO — OIDC + SAML 2.0 SP** (item 12/13, gap #21) — OpenID
  Connect (Authorization Code + PKCE, ID-token verification via
  PyJWT) and SAML 2.0 SP (signxml-backed XML-DSig with full
  defence-in-depth chain including XSW protection) with JIT user
  provisioning and HMAC-signed auth-state cookies. 82 tests.
  Commits `23cdf72` + `784707f`.
- **WCAG AAA-leaning accessibility contract tests** (item 13/13,
  gap #26) — promotes the AA-floor test suite to a stricter AAA-
  leaning surface (focus contrast, motion-pref honour, link-vs-
  surrounding-text contrast). Commit `02b3c1b`.
- **`/mcp/version` + `/mcp/schemas.json` HTTP catalogue endpoints
  + per-tool JSON Schema files in `mcp_server/schemas/`** —
  closes three deferred §2.2 follow-up items. Single-source-of-
  truth constants (`MCP_PROTOCOL_VERSION`, `MCP_SERVER_NAME`,
  `MCP_SERVER_VERSION`) drive stdio + HTTP surfaces. 13 per-tool
  files + manifest, generated by `scripts/export_mcp_schemas.py`
  (idempotent; CI-friendly drift contract). HEAD-request support
  on `/mcp/*` + `/sitemap.xml` + `/robots.txt` for MCP marketplace
  registries and search crawlers. +18 tests at
  `tests/test_mcp_catalogue_surface.py`. Commit `a49ec1b`.
- **Housing-stub-client — runnable MCP composition demo
  (Decision 20 Option A)** — self-contained Python example at
  `examples/housing-stub-client/` driving the MCP server through
  Mode 1 (sequential handoff via `propose_referral`) and Mode 2
  (profile-shared composition via `get_user_profile_for_consent`)
  end-to-end with narrated output. +16 tests at
  `tests/test_examples_housing_stub.py`. Commit `ed90258`.
- **NasserCheckList.md** — bureaucratic + vendor-relations
  checklist for partner-owned items extracted from the operator-
  dependent slice of the gap analysis. Commit `d14aca6`.
- **Post-sprint polish** — versioned migrations substrate (#20),
  threat-model document refresh (#24), Data Processing Agreement
  template (#25). Commit `11a3377`.

### Changed

- **README, STANDARDS, application-draft, 12-application-package**
  reframed with honesty caveats (pre-submission scope-tightening
  slice PART 2): ESCO described as a curated reference dataset
  (full taxonomy = Phase 2); EURES described as a projection
  contract (live API transport = Phase 2); WCAG 2.2 AA framed as
  target with axe-coverage caveat (HAN University manual review =
  next pathway); AI Act compliance described as a documented
  pack with Articles 12 + 14 wired in code and the remaining
  articles as deployer-doctrine artefacts; BYO-AI described as a
  seven-provider abstraction with Ollama exercised live and the
  cloud providers covered by mocked dispatcher tests; cost-saving
  doctrine described as a testable hypothesis pending measured
  outcomes.
- **CV-tailoring production prompt** (`company_discovery/analysis.py`
  `build_cv_tailoring_prompt`) now asks the model to acknowledge
  persona friction context — closes the polish-run criterion-(d)
  finding. Bias-test re-run at `bias-testing-2026-05-19.md`:
  criterion (d) pass-rate 43/70 → 65/70 (92.9 %); overall pass-rate
  43/70 → 61/70 (87.1 %; above the 70 % threshold).
- **README badges** + `mkdocs.yml site_url` + `static/.well-known/
  security.txt Canonical` field point at `helpmefindthejob.com`.
- **Audit-log emitter** docstring + variable references in
  `compliance/audit-log-schema.md` updated to name the
  `HELPMEFINDTHEJOB_*` prefix as canonical; legacy
  `DIRECTJOB_*` named for back-compat.
- **MCP integration test client** (`tests/test_phase12_mcp_integration_e2e.py`)
  now closes subprocess stdout/stderr pipes + tempdir in a
  `finally` block — `ResourceWarning` no longer surfaces under
  `python3 -W error::ResourceWarning`.

### Deprecated

- **`DIRECTJOB_*` environment-variable prefix** (60+ variables) —
  accepted with `DeprecationWarning` through Phase 2; removed in
  Phase 3 (see `docs/deployment-recipe.md` migration path).
- **`COMPANY_DISCOVERY_*` environment-variable prefix** (4
  variables: `_ENV`, `_DATA_DIR`, `_HOST`, `_PORT`) — same migration
  schedule.

### Added

- **Per-page meta-description regression guard (AUDIT-47)** —
  prior audit cycles authored distinct `<meta name="description">`
  strings per public page. Without a guard the next templating
  pass could quietly re-introduce the duplicate that triggered the
  original audit (Google deduplicates SERP results by description,
  so identical strings collapse multiple pages into one snippet).
  New guard in `tests/test_audit_47_meta_description_uniqueness.py`
  (+3): every public page (index, four legal × 2 languages, help,
  status, changelog, forgot-password × 2 languages = 14 surfaces)
  carries a description that is (a) present and non-empty, (b)
  within the 30-220 char band Google renders (220 leaves room for
  German translations, which run ~25 % longer than English), (c)
  carries the "Helpmefindthejob" brand, and (d) is globally
  unique across the public surface.

### Changed

- **JSON-LD `WebSite` / `Organization` centralisation (AUDIT-46)**
  — every legal page (privacy / terms / data-retention /
  impressum, EN + DE = 8 files) previously inlined a degraded
  `WebSite` definition inside `WebPage.isPartOf` and omitted any
  `publisher` field. Search engines saw two different `WebSite`
  entities for the same site (the canonical full-definition one
  on `/`, plus a name+url-only shadow on each legal page) and
  couldn't link policy pages to the canonical Organization. Both
  fields now reference the canonical `@id`s declared in the
  `index.html` `@graph` block:
  `{"@id": "https://helpmefindthejob.org/#website"}` for
  `isPartOf` and `{"@id": "https://helpmefindthejob.org/#organization"}`
  for `publisher`. Regression guard in
  `tests/test_audit_46_jsonld_centralisation.py` (+5):
  index.html carries both canonical `@id`s in its `@graph`, every
  legal page references both by `@id` (no inline `@type`/`name`/
  `url` duplication), and a textual tripwire forbids the inline
  `"@type": "WebSite"` / `"@type": "Organization"` patterns from
  ever reappearing in a legal-page source.

### Added

- **CSP violation reporting (AUDIT-37)** — the project shipped a
  strict CSP for months with no way to learn when it fired in the
  wild. A violation in a user's browser was silently dropped, making
  every CSP tightening a blind change. AUDIT-37 closes the loop:
  the main CSP header now carries `report-uri /csp-report` (legacy,
  universal browser support) and `report-to csp-endpoint` (modern
  Reporting API); a `Report-To` header registers the named group;
  a new `POST /csp-report` collector accepts both the legacy
  `application/csp-report` and the modern `application/reports+json`
  body shapes, emits a PII-safe summary (effective-directive +
  blocked-uri + document-uri; never User-Agent / Cookie / client IP)
  via the stdlib `logging` module at WARNING level, and always
  returns `204 No Content` so the endpoint can't be used as an
  oracle. Per-IP rate limit (50 / minute) and 16 KB body cap
  prevent log flooding from misbehaving extensions or hostile
  clients. Regression guard in
  `tests/test_audit_37_csp_reporting.py` (+13): summariser unit
  tests (legacy + Reporting API parsing, User-Agent PII omission,
  no-CSP-fields no-op, unparseable-body None), direct rate-limit
  test (51st claim returns False), and end-to-end live probes
  (CSP header carries both directives, Report-To group registered,
  POST returns 204 on both body shapes, invalid body still 204,
  oversize body 413).

- **Site-wide footer (AUDIT-34)** — `Handler.serve_static` now
  injects a single source-of-truth footer (`app.SITE_FOOTER_HTML`)
  into every HTML response that doesn't already carry one.
  Visitors landing on the landing page, any legal page,
  `/forgot-password`, `/help`, `/status`, or `/changelog` now see
  a consistent footer carrying: contact email
  (`support@helpmefindthejob.org`), security email
  (`security@helpmefindthejob.org`) with an RFC-9116
  `security.txt` pointer, the four legal-page nav links, an
  Apache 2.0 licence badge → LICENSE, a Commons Conservancy
  parent-org badge → commonsconservancy.org, a source-code badge
  → the GitHub repo, plus the app version (linked to
  `/changelog`) and the resolved build SHA. Build SHA resolves
  at process startup from (1) the `HELPMEFINDTHEJOB_BUILD_SHA`
  env var (Docker entrypoint), (2) `.git/HEAD` → ref →
  `packed-refs` lookup (development workflow), or (3) the
  literal `"dev"` (no git, no env). `/api/version` also exposes
  the resolved value via the new `buildSha` field so API
  integrators can correlate to the live deploy. CSS for the
  footer lives in `static/styles.css` under the
  `/* AUDIT-34 */` heading and uses the existing `--text` /
  `--text-muted` / `--text-soft` design tokens for theme
  parity. Regression guard in
  `tests/test_audit_34_site_footer.py` (+16): constant
  integrity (required markers, version + SHA presence),
  injection idempotency (re-injecting on a page that already
  has the footer must not duplicate), no-op behaviour when
  `</body>` is absent, env-var override on the SHA resolver,
  live probes against `/privacy`, `/impressum`,
  `/forgot-password`, `/`, and a negative invariant that the
  footer must NOT leak into `/api/version` JSON or
  `/forgot-password.js` source.

### Changed

- **`/admin`, `/reset-password/<token>`, `/accept-invite/<token>`
  no longer 404 (AUDIT-27)** — all three were dead URLs:
  * `/admin` had no path-to-view dispatch even though the SPA
    knows an "admin" view internally; bookmark or external link
    to `/admin` returned 404 instead of loading the admin
    surface. Now serves the SPA shell, and `static/app.js`
    `init()` sets `state.view = "admin"` for that path so a
    freshly-loaded `/admin` lands on the admin view (existing
    `isAdmin()` guard still redirects non-admin users to
    `/jobs`).
  * `/reset-password/<token>` and `/accept-invite/<token>` 404'd
    because the SPA only consumes the `?token=<token>` query
    form (the only form server-side email generation emits).
    Anyone hand-editing, generating, or being fed a path-token
    URL hit a dead end on what is one of the most-critical
    paths in the product. Both now return 303 to the canonical
    `?token=<token>` query form. Token shape is whitelisted to
    the `secrets.token_urlsafe` alphabet (`[A-Za-z0-9_-]`,
    length `[8, 256]`); anything else (length out of range,
    URL-encoded special chars, base64 padding) returns 404
    rather than bouncing arbitrary garbage paths through the
    redirect. Trailing-slash-only paths (`/reset-password/`)
    redirect to the canonical bare path.
  Regression guard in
  `tests/test_audit_27_spa_token_routes.py` (+11 tests): live
  probes for `/admin` SPA-shell rendering, valid 8-char and
  43-char token redirects, malformed-token 404s (subTest matrix
  across seven bad shapes), empty-token canonical redirect,
  invariant probe that the canonical `?token=` form still
  serves the SPA shell, and a source check that
  `static/app.js` carries the `/admin` branch.

- **`/forgot-password` is now a dedicated 3.4 KB bilingual page,
  not the 103 KB SPA shell (AUDIT-26)** — cold-loading
  `/forgot-password` (from an email link, bookmark, or post-
  timeout redirect) used to render the entire SPA chrome
  (`static/index.html`, ~103 KB) just to show a single email
  field. The dedicated page (`static/forgot-password.html` EN,
  `static/forgot-password.de.html` DE, sharing
  `static/forgot-password.js`) posts to the same
  `/api/auth/forgot-password` endpoint, lives at 3.4 KB / 3.7 KB
  respectively, and is CSP-compliant (no inline scripts). The
  in-SPA "Forgot password?" flow is unchanged — the SPA's
  client-side router still shows `forgotPasswordView` when a
  signed-out user is already in the app. Language resolution
  honours `?lang=`, the `lang` cookie, and `Accept-Language`
  (same rule as the legal pages, AUDIT-6). Robots: `noindex,
  nofollow` (the route was already in `Disallow: /forgot-password`).
  Helper rename: `Handler._BILINGUAL_LEGAL_PAGES` →
  `_BILINGUAL_PAGES` and `_bilingual_legal_path` →
  `_bilingual_page_path` (the constant now covers one non-legal
  page; existing test
  `tests/test_legal_pages_bilingual.py` updated to the new
  helper name). Regression guard in
  `tests/test_audit_26_forgot_password_minimal.py` (+13):
  size cap, SPA-marker negative checks, bilingual routing
  via `?lang=` / `Accept-Language`, JS-file reachability, and
  an invariant probe that `/reset-password` + `/accept-invite`
  still serve the SPA shell (AUDIT-27 covers extracting those).

### Removed

- **Referral-tracking cookie on `/r/<code>` (AUDIT-22)** — the
  `/r/<code>` landing redirect no longer emits a `Set-Cookie`
  header for the historical referral cookie. The cookie was
  consent-required tracking under German TTDSG §25 / ePrivacy
  Directive Article 5(3) and was set before any consent banner
  could run. It was also functionally redundant: the SPA reads
  the referral code from the `?ref=<code>` query parameter that
  the 303 redirect places in the URL and forwards it via the
  `referrerCode` JSON body field on `/api/auth/register`; the
  server never read the cookie back. Regression guard in
  `tests/test_audit_22_referral_cookie.py` (+2) — a source-grep
  tripwire that fails if the cookie name reappears in `app.py`,
  plus an end-to-end probe that boots the real handler and
  asserts the `/r/<code>` response is a 303 to `/?ref=<code>`
  with zero `Set-Cookie` headers carrying the cookie name.

### Fixed

- **Accessibility regressions** surfaced by the post-rename axe
  re-run on the 4 mkdocs surfaces (`/mcp-server/`, `/deployment-recipe/`,
  `/production-deployment/`, `/esco-integration/`): pygments
  comment/docstring/variable contrast bumped from 4.47:1 → ~6.1:1
  via scoped overrides in `docs/stylesheets/accessibility.css`
  (Fix 15); each `<nav class="md-code__nav">` copy-button container
  gets a unique aria-label via
  `docs/javascripts/accessibility.js` (Fix 16).
- **`company_discovery/audit_log.py` SPDX-License-Identifier
  header** — pre-existing gap from the Week 2 task 2.8 commit
  closed during the rename slice's no-gaps-behind sweep.
- **i18n parity test** generalisation + **preserved-German-terms
  lint** + **HTML fallback drift test** (§3.7 hardening, three
  contracts added to `tests/test_phase0_i18n_parity.py`).
- **Cosign verification post-rename** — verification commands in
  `docs/releases/v0.1.0-signing.md` + `docs/releases/v0.1.0.md`
  now download the original signed `directjob-scout-0.1.0.tar.gz`
  by `--pattern` + `--output v0.1.0-source.tar.gz` so the SHA-256
  match holds regardless of the GitHub repo's current name. The
  maintainer follow-up to attach the original tarball as a v0.1.0
  release asset is recorded in
  [`CONTRIBUTORS-NOTE.md`](CONTRIBUTORS-NOTE.md).

#### Fixed during 13-plan + post-sprint slices

- **`/api/health` storage field lied when DATABASE_URL routed to
  Postgres** — endpoint previously hardcoded `"storage":"sqlite"`
  even when the primary repository was on PG. Replaced with
  `_storage_kind()` that inspects the live repository class.
  Caught during the PG rollout runtime proof; commit `b2d7599`.
- **Week-1 `khalo.org` sanitization residue in `static/sitemap.xml`**
  — fixed at root by making `/sitemap.xml` + `/robots.txt` dynamic
  routes that pull the base URL from `APP_PUBLIC_URL` / Host
  header / X-Forwarded-Proto. URLs can never go stale or carry
  sanitization residue. Part of commit `17f7707`.
- **HEAD-request 404 on dynamic routes** — `/sitemap.xml`,
  `/robots.txt`, `/mcp/version`, `/mcp/schemas.json` previously
  fell through to `serve_static` on HEAD requests and returned
  404. Google + Bing crawlers + MCP marketplace registries
  probe with HEAD before fetching — broken before this fix.
  All four routes now respond to HEAD with the same headers as
  GET and an empty body. Part of commit `a49ec1b`.
- **index.html missing `og:site_name`** — caught by the per-page
  SEO contract test; added the tag. Part of commit `17f7707`.
- **Housing-stub filter read wrong profile field
  (`status` vs `currentStatus`)** — demo would always return
  the unknown-status branch regardless of the actual user
  state, silently masking any future protocol change. Fixed at
  root + pinned with `test_filter_reads_currentStatus_not_status`.
  Part of commit `ed90258`.
- **JSON-LD XSS vector in `_send_seo_page`** — operator-edited
  seo-pages.json containing `</script>` in title/intro would
  break out of the surrounding script tag. Routed serialisation
  through new module-level `_xss_safe_jsonld` helper that
  escapes `<`/`>`/`&` as unicode forms. Defense-in-depth even
  though the only current caller is trusted. Part of commit
  `17f7707`.
- **README CI badges hardcoded the working branch
  (`?branch=claude/project-analysis-bpHCo`)** — 5 badges now pin
  `?branch=main` so they reflect the canonical state once merged.
  Regression-guard test at `tests/test_readme_badges_pinned.py`
  (+3) prevents drift. Closes phase2-backlog item #62.

### Security

- **Audit-log production fail-fast** (see Added) materially
  hardens Article 12 record-keeping by refusing to start a
  production process whose audit-log salt is unset (which would
  silently produce uncorrelatable hashes across restarts).
- **cosign-signed source tarball** + **CycloneDX 1.6 SBOM** +
  **RFC 9116 security.txt** ship with v0.1.0 (`docs/releases/v0.1.0-*`,
  `static/.well-known/security.txt`).
- **TOTP-secret column AEAD migration** (ChaCha20-Poly1305
  AAD-bound to user_id) — already in v0.1.0; no behaviour change
  in this block.

---

## [0.1.0] — 2026-05-18

First stable pre-publication release. Closes the four-week
**NLnet NGI Zero Commons Fund grant-readiness sprint** that ran from
**2026-05-17** through this tag. The release deliberately frames the
project as a **civic commons** under Apache 2.0 + CLA, application
to The Commons Conservancy pending, EU AI Act compliant by design.

### Added

- **Apache 2.0 licensing pack** — `LICENSE`, `NOTICE`, `TRADEMARK.md`,
  `cla.md`, and SPDX-License-Identifier headers across every Python
  source file. Pre-commit hook enforces the SPDX header on every commit
  (Week 1 task 1.1).
- **Governance pack** — `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`
  (Contributor Covenant 2.1), `SECURITY.md`, `SUPPORT.md`,
  `AUTHORS.md` (consent-first authorship placeholders),
  `ACKNOWLEDGMENTS.md`, `.github/ISSUE_TEMPLATE/`,
  `.github/PULL_REQUEST_TEMPLATE.md`, `.github/CODEOWNERS`
  (Week 1 task 1.2).
- **Civic-commons-positioned README** with the persona-anchored opening
  (Aïcha + Käthe vignette), Standards we implement section, MCP
  composition section, self-hosting steps, Apache 2.0 + Commons
  Conservancy framing (Week 1 task 1.3).
- **Grant-application planning workspace** at `docs/grant/` — 14
  documents covering the project brief, decisions log, execution plan,
  research findings, risk register, stakeholder map, glossary, persona
  panel, cost-saving doctrine, MCP composition spec, EU AI Act
  compliance plan, institutional-outreach strategy, application
  package draft, behavioural rules / lessons-learned for advisory
  sessions.
- **Commons Conservancy Programme application draft** at
  `docs/grant/commons-conservancy-application-2026-05-18.md`
  (Week 2 task 2.1).
- **MCP server documentation** at `docs/mcp-server.md` + standards
  manifest at `STANDARDS.md` (Week 2 task 2.2).
- **MCP catalogue v0.2.0** — five composition-oriented tools added on
  top of the legacy 8 (`propose_referral`, `summarise_outcomes`,
  `bundle_civic_context`, `query_esco_skill`,
  `export_eures_compatible`) — 13 tools total with JSON Schema
  Draft 7 inputs documented and enforced server-side
  (Week 2 task 2.3).
- **ESCO + EURES integration** — curated reference dataset
  (30 occupations, 51 skills) under `reference/esco/`, German +
  English labels, persona-panel cross-link, with the `query_esco_skill`
  tool and the `export_eures_compatible` projection
  (Week 2 task 2.4).
- **Reference housing-agent integration scope** — `docs/grant/` Decision
  20 narrows the §2.5 deliverable to Option A (mock stub) or Option B
  (real friend collaboration), with self-built variants deferred to
  Phase 2.
- **MCP integration end-to-end CI test** —
  `tests/test_phase12_mcp_integration_e2e.py` spawns the MCP server as
  a real subprocess, drives it over JSON-RPC over stdio, asserts the
  13-tool catalogue + protocol version + happy-path tools/call +
  schema-validation failure path. README badge added
  (Week 2 task 2.6).
- **ARCHITECTURE.md** at repo root with Mermaid diagram and component
  map (Week 2 task 2.7).
- **EU AI Act compliance pack** at `/compliance/` — 11 documents
  covering Articles 9, 10, 11+AnnexIV, 12, 13 (user-facing +
  deployer-facing), 14, 15, 27 (FRIA template), 49 (EU AI database
  registration template), plus an audience-split index README.
  Friction-class framing per Decision 21 embedded in the four
  user-base-facing files (Week 2 task 2.8).
- **AI Act Article 12 audit-log emitter** at
  `company_discovery/audit_log.py` — JSONL schema v1 with seven event
  types, SHA-256 PII hashing keyed by per-deployment
  `DIRECTJOB_AUDIT_SALT`, ContextVar-based caller-context propagation,
  microsecond-precision rotation with collision nonce, plaintext-PII
  opt-in. Integrated into `mcp_server.py::_handle_tools_call` and
  `company_discovery/analysis.py::_dispatch_provider`. New
  `tests/test_phase13_audit_log.py` exercises emitter + caller-context
  + MCP integration + analysis-pipeline integration + tail helper
  (20 tests).
- **AI Act Article 14 minimum-viable human-oversight admin endpoint**
  at `/api/admin/oversight/queue` (admin-gated, controlled by
  `DIRECTJOB_HUMAN_OVERSIGHT_MODE`). Returns recent audit-log events
  for deployer review with `event_type` filter and `limit` query
  params. Tail helper `_read_ai_act_audit_tail` reads live + rotated
  siblings sorted most-recent-first.
- **Lessons-learned workspace** at `docs/grant/13-lessons-learned.md`
  — 10 behavioural rules captured from prior advisory sessions
  (Friction-driven not demographic-driven framing, verify numerical
  claims, calibrate response length, etc.).
- **Friction-class framing** (Decision 21) — public-facing artifacts
  reframed from "for migrants" to "for anyone facing structural
  labor-market friction in Europe, with migrants and EU-mobile
  workers as the most acute use case."
- **Seven-persona panel** (Decision 21) — Käthe (German nurse returning
  after 12 years caregiving) and Tobias (German backend developer
  pivoting commercial → civic-tech) added alongside the existing
  five (Aïcha, Yusuf, Olga, Mahmoud, Maria).
- **Template H** at `docs/grant/11-institutional-outreach.md` — the
  invitation-to-co-create-a-sibling-civic-agent letter for developer
  friends who could build a housing agent from scratch (German text).
- **`pyproject.toml`** — single-source-of-truth config for ruff (lint
  + format-check), mypy (permissive with strict overrides for
  audit_log + crypto_kit + mcp_server), coverage (branch coverage).
- **`requirements-dev.txt`** — pinned dev tooling: pre-commit, ruff,
  mypy, types-jsonschema, types-requests, coverage, codespell,
  pip-audit (Week 3 task 3.2).
- **`.codespellrc`** — codespell config with German-vocabulary
  ignore list and intentional-skip paths.
- **Extended `.pre-commit-config.yaml`** — ruff (lint + format-check)
  and codespell hooks alongside the SPDX-header check.
- **`renovate.json`** — Renovate dependency-automation config
  (activates on Renovate GitHub App install). Groups minor/patch
  updates weekly; major releases get explicit PRs;
  `cryptography` major releases tagged `security-review-needed`.
- **`.github/workflows/quality.yml`** — five-job quality workflow
  (ruff-lint, mypy-strict-subset, codespell, pip-audit, coverage with
  Codecov upload via `codecov-action@v5`).
- **`.github/workflows/scorecard.yml`** — OpenSSF Scorecard via
  `ossf/scorecard-action@v2.4.0` (weekly cron + push-to-main).
- **`.github/workflows/fresh-clone-install.yml`** — matrix over
  `python:3.11-slim` and `python:3.12-slim` containers; verifies fresh
  `pip install -r requirements.txt` + cryptography import +
  representative smoke-test slice (Week 3 task 3.1).
- **README badges**: tests, quality, MCP integration, fresh-clone
  install, OpenSSF Scorecard, Codecov coverage.
- **`ROADMAP.md`** at repo root — quarterly milestones 2026 Q3 → 2028
  Q2 (this release).
- **`CHANGELOG.md`** at repo root (this file).
- **994 → 1829 tests in the suite (+835)** — measured at the
  v0.1.0 tag vs `HEAD` on `claude/project-analysis-bpHCo` as of
  2026-05-21. The breakdown by sprint area (rounded to the
  nearest 10; some tests touch multiple areas — buckets are by
  primary subject):
  - **+~50 (v0.1.0 → 994)**: Week 2 baseline — MCP integration
    end-to-end path, AI Act audit-log layer, §2.3 composition
    tools, §2.4 ESCO + EURES surface, AEAD migration for TOTP
    secrets.
  - **+~410**: bias-methodology + persona accuracy gates
    (Phase 2 PART 4 + PART 5) — `test_round*`, `test_round12`,
    `test_round13`, `test_round14`, `test_bias_methodology`,
    `test_friction_class_*` family. Driving force: closing the
    +27/-70 friction-context gap in the R12-polish report.
  - **+~110**: journey + chat UX (Phase 2 PART 6 gates 6.1–6.8)
    — 7-persona × 12-phase walks, error-recovery paths, partial-
    results streaming, mobile-viewport smoke, slash-command
    intent recognition.
  - **+~100**: AI dispatch infrastructure — token-streaming
    refactor (#77), cost-cap chokepoint (#46), prompt-injection
    sanitiser (#45) — backend + frontend contract tests across
    `test_chat_*_streaming`, `test_cost_caps`, `test_cost_cap_
    integration`, `test_prompt_injection_suite`.
  - **+~50**: security audit suite — CSRF/CORS/rate-limit/SQL
    (#47), session-invalidation completeness (#48), 2FA recovery
    codes (#49), audit-log tamper-evidence (#13). Files:
    `test_security_audit_47`, `test_session_invalidation_48`,
    `test_recovery_codes_49`, `test_audit_log_tamper_evidence_13`.
  - **+~50**: GDPR + compliance — Article 20 portable export
    (#54), CV-photo encryption + WebP EXIF stripping (#32),
    Article 7 consent timestamp. Files: `test_gdpr_article_20_
    export`, `test_cv_photo_gdpr_32`.
  - **+~30**: cost-saving doctrine measurement substrate (#69),
    city-adjacency graph (#71 Phase D + #74 substrate),
    database-error policy classifier (#78 substrate), disk-full
    sessionStorage preservation.
  - **+~25**: no-AI templated-fallback verification (#57 —
    found + fixed the EURES tool's silent-failure mode);
    red-team adversarial harness as unittest target (#29).
  - **+~10**: documentation drift-guards — ESCO shortageDE
    count (#60), accessibility surface/instance counting notes
    (#39 + #40), MCP-tool count guard.
  Each test files maps 1:1 to a backlog item or sprint commit;
  the cross-reference is captured in
  `docs/grant/phase2-backlog-2026-05-19.md`.

### Changed

- **MCP catalogue version**: v0.1.0 → **v0.2.0** (8 → 13 tools); all
  inputs schema-enforced via `jsonschema.Draft7Validator` server-side
  prior to dispatch.
- **Python minimum**: explicit `requires-python = ">=3.9"` declared in
  `pyproject.toml`; CI matrix tests 3.9 + 3.12.
- **Dependency pins**: `cryptography>=42.0.0,<50.0.0` added explicitly
  to `requirements.txt` with broad-wheel coverage rationale.
- **Cost-saving doctrine mechanism 1**: "Lower advisor caseload per
  migrant served" → "Lower advisor caseload per case served," with
  inline note that the migrant subset remains the densest concentration
  per advisor visit.
- **Housing-agent integration default** (Decision 20, partially
  supersedes Decision 11): §2.5 default is now Option A (mock stub);
  Option B (real friend integration) only if a collaborator confirms;
  self-built (Option C / D) deferred to Phase 2.
- **Persona panel composition** (Decision 21): expanded from five to
  seven personas without removing any; the migrant five remain the
  primary narrative anchor.
- **Codebase format** (one-time normalisation): `ruff format` applied
  across 124 files. No semantic changes; pre-existing inconsistent
  formatting normalised.

### Removed

- **`khalo.org` references** — replaced with `directjob-scout.example`
  placeholders in code, docs, tests, and configuration
  (Week 1 task 1.4). _(Note: per [Decision 22](docs/grant/04-research-and-decisions.md#decision-22-project-rename--directjob-scout--helpmefindthejob), the `directjob-scout.example` placeholder convention was subsequently superseded on 2026-05-19 by the real domain `helpmefindthejob.com` when the project was renamed and the domain acquired; the v0.1.0 release shipped with the placeholder convention as the identity-of-record at sign time.)_
- **Tester-name leakage** in code comments and test fixtures
  (Week 1 task 1.4).
- **`keepbuildingtill100%tracker.MD`** at repo root (per Decision 14).
- **`private/` content from git tracking** — pre-sprint commercial-
  vision docs (sellable-readiness, operator-launch, marketing-copy,
  press-kit, launch-day-content, operator-package, operator-starters,
  operator-final-punchlist, legal-review-brief, deployment-handoff)
  relocated to a gitignored `private/` directory.
- **README "Pro / Free" commercial framing** — superseded by the
  civic-commons positioning (Week 1 task 1.3).
- **Outdated commercial-narrative docs from `docs/`** —
  `sellable-readiness-*.md`, `marketing-copy.md`, and related
  pre-sprint materials moved to `private/`.

### Fixed

- **TOTP-secret column AEAD migration** in `auth.py` —
  ChaCha20-Poly1305 wraps the TOTP secret at rest (was previously
  plaintext on the DB column). Migration ladder + decrypt-and-re-wrap
  on first read. Tested in
  `tests/test_phase9_totp_aead_migration.py` and the AEAD fuzz suite.
- **MCP `tools/call` inputSchema enforcement** in `mcp_server.py` —
  pre-dispatch validator returns RFC 7807 Problem Details on schema
  violations and on unknown tool names. Closes the previous gap where
  malformed payloads could reach handler code.
- **Yes/no parser locale awareness** in `company_discovery/locale_parser.py`
  — German `ja/nein` plus colloquial variants accepted; help-prompt
  escape disambiguates from yes/no commands.
- **Pre-existing `mcp-integration.yml` post-success script PYTHONPATH
  bug** — the catalogue-print step had been failing on every push
  since §2.6. `PYTHONPATH=.` env on the step fixes the import resolution.
- **B039 mutable `ContextVar` default** in `audit_log.py` — replaced
  `{}` default with `None`; call sites normalise via `ctx.get() or {}`.
- **F821 forward-reference imports** in `auth.py`,
  `tests/test_phase1_seo_pages.py`, and
  `tests/test_phase3_onboarding_drip.py` — hoisted into
  `TYPE_CHECKING` blocks so the annotations resolve for tooling
  without forcing a runtime import.
- **B005/B030 false positives** in `journey.py` and `chat_router.py`
  — annotated with `# noqa` comments explaining the intentional
  patterns (character-set strip, conditional except).
- **Mypy issues in `mcp_server.py`** — `jsonable` narrows `is_dataclass`
  to instances-only via `not isinstance(value, type)`; `build_tools`
  HTTPFetcher arg tagged with a single targeted
  `# type: ignore[arg-type]` and a follow-up note; `run_stdio` local
  `response` typed explicitly as `dict[str, Any] | None`.
- **Mypy issue in `crypto_kit.py`** — `is_aead_blob` narrows
  `Optional[str]` via `value is not None` (was `bool(value)`).
- **One real misspelling** of "download" in
  `company_discovery/journey.py` and
  `tests/test_journey_edge_cases.py` (caught by codespell on its
  first CI run).

### Security

- **AEAD-at-rest extended to TOTP secrets** — ChaCha20-Poly1305 wraps
  the TOTP-secret column with the same key derivation chain as the
  CV-text column. AAD-binds the ciphertext to the user identifier so
  a row-swap attacker cannot lift another user's TOTP secret.
- **MCP tool-input validation enforced server-side** — every
  `tools/call` dispatch is gated on schema validation prior to
  handler invocation; eliminates the previous risk that a misbehaving
  composing agent could trigger handler-side parse errors.
- **AI Act Article 12 audit-log layer** — every AI invocation, MCP
  tool invocation, and override event is recorded in JSONL with
  PII-hashed identifiers. Per-deployment salt prevents linkability
  across deployments.
- **`cryptography` explicitly pinned** in `requirements.txt`
  (`>=42.0.0,<50.0.0`) — closes the previous fragility where the
  encryption-at-rest layer relied on `pywebpush`'s transitive
  dependency.
- **`pypdf` upgraded** 5.1.0 → 6.10.2+ — closes 22 CVEs flagged by
  `pip-audit --strict` (CVE-2025-55197, CVE-2025-62707,
  CVE-2025-62708, CVE-2025-66019, CVE-2026-22690 through
  CVE-2026-41314).
- **`pip-audit --strict` runs on every push** — fails CI on any new
  vulnerability across runtime + dev dependencies.
- **OpenSSF Scorecard workflow** — weekly automated security-best-
  practices scoring; SARIF results uploaded to GitHub Security tab.
- **`.well-known/security.txt`** at repo root per [RFC 9116](https://www.rfc-editor.org/rfc/rfc9116)
  — vulnerability-reporting channel anchored.

---

## [0.0.x] — pre-2026-05-17 (pre-sprint, commercial product)

The codebase pre-dates the grant-readiness sprint as a self-hosted
commercial product with a Pro/Free tier (see Round 1–21 in the
Git log). The active project direction shifted to a **civic-employment
commons** at the start of the four-week sprint; the sanitisation pass
in Week 1 task 1.4 cleared the commercial-vision residue from the
working tree.

The full pre-sprint history is preserved in the Git log (no
history rewrite was performed — see Decision 12 in
`docs/grant/04-research-and-decisions.md`). The honest project
history including the deprecated commercial framing is documented
in [`CONTRIBUTORS-NOTE.md`](CONTRIBUTORS-NOTE.md).

This entry is deliberately brief; the pre-sprint commits are
listed individually only via `git log --before="2026-05-17"`.

---

## How to update this file

When shipping a new release:

1. Move the [Unreleased] section's bullets into a new dated section
   above this paragraph, with the version number (e.g., `[0.2.0] — YYYY-MM-DD`).
2. Re-open an empty [Unreleased] section at the top.
3. Tag the release annotated and create the GitHub Release pointing
   at the new entry plus `docs/releases/vX.Y.Z.md` for the longer-form
   public release notes.
