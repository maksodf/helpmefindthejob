<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Phase 2 backlog — items tracked for post-grant cycles

**Source**: 2026-05-19 pre-submission honest-inventory follow-up
(items numbered as in the original inventory). This file is the
durable index of "what is tracked but deferred" so future agents
and contributors do not lose sight of these items between sprints.

Each row carries: brief description, originating inventory `#`,
rough effort, and a target Phase 2 quarter (`2026 Q3` / `2026 Q4` /
`2027 Q1`). Targets are best-effort scoping anchors, not promises.

The pre-submission scope-tightening slice (this slice) closed 12 of
the 65 inventory items. The 53 remaining items are catalogued below.

---

## Unbuilt — promised in docs, not implemented (#21–#32)

| # | Item | Effort | Target |
|---|---|---|---|
| 21 | Public demo deployment at `demo.helpmefindthejob.com` — provision host, wire DNS, deploy `docker-compose.prod.yml`, configure TLS + Caddy, seed the seven personas, verify journey end-to-end through the chat surface. | 1–2 d | 2026 Q3 |
| 22 | Real partner-NGO pilot — send the 8 institutional-outreach templates from `docs/grant/11-institutional-outreach.md`; secure at minimum one letter of support; convert one of those into a pilot deployment. | 4 wk wall | 2026 Q4 |
| 23 | TU Berlin affiliation email — Decision 17's "optional 1-hour email"; either send it or formally close the dependency. | 1 h | 2026 Q3 |
| 24 | Commons Conservancy Programme application submission — currently drafted at `docs/grant/commons-conservancy-application-2026-05-18.md`; send to `website@commonsconservancy.org`. | 1 h + 2–6 wk review | 2026 Q3 |
| 25 | NLnet NGI Zero Commons Fund submission — currently drafted at `docs/grant/application-draft-2026-05-19.md`; submit at the 2026-06-01 deadline (or next call). | 2 h + maintainer-side fill-in identity fields | 2026 Q3 |
| 26 | Additional translations: Arabic, Ukrainian, Turkish, Romanian. EN + DE shipped today; the four post-grant languages have no current translator. | 1 wk per locale | 2026 Q4 onward |
| 27 | Multi-OS CI matrix (macOS + Windows in `.github/workflows/test.yml`). Pre-existing Linux-isms surfaced during §3.2: cp1252 vs UTF-8 file IO; subprocess timing on macOS. Remediate then enable the matrix. | 1 wk | 2026 Q4 |
| 28 | Multi-system Nix flake check (`--all-systems`). Today `nix flake check` only covers `aarch64-darwin`; the other three (`aarch64-linux`, `x86_64-linux`, `x86_64-darwin`) require `--all-systems` + a CI matrix. | 0.5 wk | 2026 Q4 |
| 29 | Red-team harness packaged as a `tests/test_round20*` unittest target. Ad-hoc agents live at `tests/e2e/red_team/` today; package them as a single-command opt-in run. | 0.5 wk | 2026 Q3 |
| 30 | Self-service CLA tool (CLA Assistant or equivalent). Today CLA assent is via PR-comment mechanism. | 0.5 d setup | 2026 Q3 |
| 31 | Mobile + PWA verification: real-phone responsive check, service-worker cache strategy verification, offline-mode behaviour audit. | 2–3 d | 2026 Q4 |
| 32 | CV-photo (`company_discovery/cv_photo.py`) GDPR review — consent flow, on-device vs server-side processing, image-storage encryption-at-rest, retention + deletion. | 1 wk | 2026 Q3 |

## Test-quality gaps (#41–#46)

| # | Item | Effort | Target |
|---|---|---|---|
| 41 | The 4 skipped tests on bare-host are the only real E2E + bias surface. Wire them into a separate CI workflow that runs nightly with the required env vars. | 0.5 d | 2026 Q4 |
| 42 | Tests that finish in 0.002 s for 36 cases are mocking everything. Add a smoke layer that hits at least one provider live (test API key, OpenAI sandbox). | 1 d | 2026 Q4 |
| 43 | No mutation testing, no property-based testing, no fuzzing beyond AEAD. Add Hypothesis-based property tests for the locale parser, chat-router, journey state machine. | 1 wk | 2027 Q1 |
| 44 | No load / perf / concurrency testing. Add a small `locust` or `vegeta` suite measuring p50 / p95 / p99 across the journey + MCP `tools/call`. | 1 wk | 2027 Q1 |
| 45 | Prompt-injection test suite — adversarial CV text + chat input. No coverage today. | 1 wk | 2026 Q4 |
| 46 | BYO-AI cost-cap — per-session or per-user spend limit when the user provides their own API key. | 3 d | 2026 Q4 |

## Security audits to run (#47–#50)

| # | Item | Effort | Target |
|---|---|---|---|
| 47 | CSRF, CORS, rate-limit specifics, SQL-injection audit of `app.py` + repository layer. | 1 wk | 2026 Q3 |
| 48 | Session-invalidation completeness — does 2FA enrollment / email change / role change / account deletion invalidate active sessions? | 0.5 wk | 2026 Q3 |
| 49 | 2FA recovery codes path — implement (if missing) and test. | 3 d | 2026 Q4 |
| 50 | Backup restore drill — `scripts/backup-production.sh` exists; verify backup decrypts + restore succeeds against a representative dataset, not just dry-run. | 0.5 d | 2026 Q3 |

## Deployment / operational (#51–#54)

| # | Item | Effort | Target |
|---|---|---|---|
| 51 | Existing maintainer Docker containers running with `directjob-scout` project name need explicit `docker compose -p directjob-scout down` before the new `helpmefindthejob` containers start. Document this as a one-time maintainer pre-flight. | 0.5 h | 2026 Q3 |
| 52 | Caddyfile reverse-proxy directive renamed to `helpmefindthejob:8765`. Confirm + redeploy in lockstep with the compose rename on the production host. | 0.5 h | 2026 Q3 |
| 53 | Env-var rename migration is supported by the `env_compat` shim (this slice's PART 3) with `DeprecationWarning`. Phase 3 removes the legacy prefix entirely — schedule the cutover after one major version of soak. | 1 d | 2027 Q1 |
| 54 | GDPR Article 20 data-portability `/api/account/export` endpoint — implement (if missing) and confirm Article 17 right-of-erasure path also covers all encrypted-at-rest columns. | 1 wk | 2026 Q4 |

## UX / product (#55–#58)

| # | Item | Effort | Target |
|---|---|---|---|
| 55 | Persona panel — at least one real-world user interview per persona to validate the synthesised friction patterns. | 4 wk wall | 2026 Q4 |
| 56 | Persona localisation: normalise content depth across the panel; render path for non-EN/DE locales when those translations land. | 1 wk | 2026 Q4 |
| 57 | No-AI templated-fallback verification: confirm every one of the 13 MCP tools has a meaningful templated fallback when no AI provider is configured (rather than erroring out). | 0.5 wk | 2026 Q4 |
| 69 | Cost-saving doctrine measured-outcome instrumentation — design the metric collection (with deployer consent) that turns the doctrine into a measured claim. | 1 wk | 2027 Q1 |

## Documentation drift (#33–#40)

| # | Item | Effort | Target |
|---|---|---|---|
| 33 | `docs/releases/v0.1.0.md` "What's not yet shipped" list — items have shipped since 2026-05-18. Either freeze the file as a historical snapshot with a clear "as of v0.1.0 release date" note, or add a "since v0.1.0" addendum mirroring CHANGELOG `[Unreleased]`. | 0.5 d | 2026 Q3 |
| 34 | ~~CHANGELOG `[Unreleased]` empty.~~ **CLOSED** in PART 4 of this slice. | — | — |
| 35 | Decision 22 narrative skips the `khalo.org → directjob-scout.example → helpmefindthejob.com` two-step transition. Could be folded into the Open R8 reopen for clarity. | 0.5 h | 2026 Q3 |
| 36 | Open R-question log: confirm Open R1 (NLnet deadline) against the live NLnet call page at submission time; resolve Open R2 (NGI0-funded employment / migration projects). | 1 h | 2026 Q3 |
| 37 | ~~STANDARDS row-by-row audit.~~ **CLOSED** in PART 5 of this slice. | — | — |
| 38 | Document the test-count growth from 994 (v0.1.0) → 1043 (HEAD post-slice). Currently no entry breaks down the +49 by area. | 0.5 d | 2026 Q3 |
| 39 | "33 audited surfaces" double-counts colour-scheme variants — true unique surface count is ~25. Reconcile in `ACCESSIBILITY.md`. | 1 h | 2026 Q3 |
| 40 | "16 fixes" count vs "32 violation instances closed" — the two numbers measure different things; document the distinction in `ACCESSIBILITY.md`. | 0.5 h | 2026 Q3 |

## Audit-log hardening (#13)

| # | Item | Effort | Target |
|---|---|---|---|
| 13 | Audit-log tamper-evidence: line-level signing (monotonic-sequence + HMAC-chain or sigstore-style append-only ledger); centralised log forwarding; provable-completeness signal so a regulator can detect deletion. | 2 wk | 2027 Q1 |

## Cosign keyless transition (#14)

| # | Item | Effort | Target |
|---|---|---|---|
| 14 | Cosign keyless via GitHub Actions OIDC (cosign model a). Removes the `--insecure-ignore-tlog` flag and the long-lived private key. Planned for v0.2.0+. | 1 d | 2026 Q4 |

## Other items the inventory surfaced

| # | Item | Effort | Target |
|---|---|---|---|
| 1 | GitHub repository visibility — currently private (HTTP 404 to unauthenticated readers). Maintainer-side action: Settings → Change visibility → Public. | 5 min | 2026 Q3 (pre-NLnet submission) |
| 2 | GitHub Pages docs site — currently 404 at `maksodf.github.io/helpmefindthejob/`. Activates after merge to `main` + GH Pages source = `gh-pages` branch (the docs-publish workflow target). | 1 h | 2026 Q3 |
| 3 | `helpmefindthejob.com` HTTPS + canonical landing page. DNS resolves to a maintainer IP; HTTP returns 405 (no project served). | 0.5 d | 2026 Q3 |
| 4 | ~~Cosign verification doc fix.~~ **CLOSED** in PART 1.2 of this slice. | — | — |
| 5 | ~~Audit-log salt fail-fast.~~ **CLOSED** in PART 1.1 of this slice. | — | — |
| 6 | ~~`DIRECTJOB_*` env-var prefix — env_compat shim with deprecation warnings.~~ **CLOSED** in PART 3 of this slice. | — | — |
| 7 | ~~`COMPANY_DISCOVERY_*` env-var prefix — same shim.~~ **CLOSED** in PART 3 of this slice. | — | — |
| 8 | "30 occupations + 51 skills" doc drift — actual file has **30 + 50**. Fix in CHANGELOG + v0.1.0 release notes references. | 0.5 h | 2026 Q3 |
| 9 | ~~ESCO claim re-framed.~~ **CLOSED** in PART 2 of this slice. | — | — |
| 10 | ~~EURES claim re-framed.~~ **CLOSED** in PART 2 of this slice. | — | — |
| 11 | ~~Accessibility WCAG 2.2 AA claim re-framed.~~ **CLOSED** in PART 2 of this slice. | — | — |
| 12 | ~~AI Act compliance claim re-framed.~~ **CLOSED** in PART 2 of this slice. | — | — |
| 15 | ~~BYO-AI claim re-framed.~~ **CLOSED** in PART 2 of this slice. | — | — |
| 16 | Browser-driven journey walk-through with screenshots at each state transition — manual maintainer activity that complements the automated suite. | 0.5 d | 2026 Q3 |
| 17 | Stripe webhook end-to-end test with real Stripe sandbox webhook. | 0.5 d | 2026 Q4 |
| 18 | Email transport (SMTP) live verification — drip campaigns, signup confirmation, 2FA recovery. | 0.5 d | 2026 Q3 |
| 19 | ~~MCP subprocess ResourceWarning.~~ **CLOSED** in PART 6 of this slice. | — | — |
| 20 | Bias-testing fit-scoring ONE-OFF divergence pattern — remediation is prompt engineering for variance reduction (untried) or model selection (changes the BYO-AI offline-Ollama story). | 2 wk | 2027 Q1 |
| 58 | ~~Cost-saving claim re-framed.~~ **CLOSED** in PART 2 of this slice. | — | — |
| 59 | Application-draft numerical claims — 3 of 4 reworded because primary sources didn't yield specific numbers. At submission time, re-attempt primary-source citation or keep the reword. | 1 h | 2026 Q3 |
| 60 | `docs/esco-integration.md` line 117 claim "21 of the 30 occupations" carry the `shortageDE2024: true` flag — verify the actual count in the JSON. | 10 min | 2026 Q3 |
| 61 | CHANGELOG-style summaries currently live in commit bodies, not in `CHANGELOG.md`. **Partly closed in PART 4 of this slice** (CHANGELOG `[Unreleased]` now backfilled); doctrine for future slices: every slice updates CHANGELOG before committing. | — | doctrine, ongoing |
| 62 | Branch-name in README badges hardcoded to `branch=claude/project-analysis-bpHCo`. Once the working branch merges to `main` the badges should be updated to `branch=main`. **Conditional follow-up** — 5-min fix after merge. | 5 min | 2026 Q3 |
| 63 | Formal pre-submission checklist that walks every NLnet form-field one-by-one against `application-draft-2026-05-19.md`. | 2 h | 2026 Q3 |
| 64 | Open the live NLnet submission form to cross-check question wording + word limits against the draft. | 1 h | 2026 Q3 |
| 65 | External-reader recruit — at minimum one human read of the application before submission. | 1 wk wall | 2026 Q3 |
| 66 | **Methodology band recalibration (Path B reserve)** — if real user feedback post-deployment shows the post-Path-A fit-score calibration is off (e.g., users perceive "Fit: 78%" as undersold for jobs that match them perfectly, or "Fit: 45%" as oversold for jobs they consider weak), recalibrate the methodology's `expected_score_min` / `expected_score_max` bands per persona in `persona_fixtures.PERSONAS` and the corresponding ranges in `compliance/accuracy-and-bias-testing.md` §2.4. **Cross-surface dependency note**: downstream features depend on this calibration — (a) Slack notification threshold (`UserProfile.slack_fit_threshold`, default 0.70); (b) "high fit" UX labels in the queue; (c) queue ranking by fit score; (d) Pro+ auto-fit-on-discovery threshold. Any recalibration is a coordinated cross-surface change — re-evaluate all four downstream thresholds + the seven persona fixtures + the methodology doc in one slice. Reserved as Path B per operator decision 2026-05-20 (Path A approved as the calibration-preserves-UX-continuity move; Path B held back for if real-world data contradicts Path A's outcome). | 1 day (recalibration) + 0.5 day (downstream audit) | unscheduled (trigger-driven) |
| 67 | **Cloud-AI re-validation of PART 5 F1/F2 gates post-deployment** — PART 5 iter#3 closed under "top-tier within open-source-AI scope" per the operator's hard-convergence rule (2026-05-20). Strict residual margins on Ollama `llama3.1:8b`: (a) Mahmoud + `ausbildung_shk_hamburg` margin fail at 72 (sample variance 56→81→80→72 across 4 dated runs; capability ceiling); (b) skills+exp anchor parking exactly at 30% boundary (improved 46% → 36% → 30% across iterations 1/2/3). Once the first deployer configures a cloud-AI provider (GPT-4 / Claude / Gemini Pro) in production telemetry, re-run `tests.test_bias_methodology` against that provider + verify Mahmoud ausbildung ≥75 reliably + skills+exp parking <25% reliably. Expected outcome: cloud-AI closes both margins without prompt changes — that's the cloud-AI capability premium documented in PART 10 honesty matrix. Trigger: first cloud-AI-provider deployment with telemetry consent. Effort: 1 day (re-run + analysis + update PART 10 entry). | 1 day | unscheduled (trigger-driven) |
| 80 | **Cover-letter section UI split — separate fields per section + interactive citation verifier** — surfaced during PART 8 Loop 25 (citation markers shipped at prompt level). Today the AI cover-letter draft returns 5 sections concatenated into the `#applicationCoverLetter` textarea: (1) subject + opening, (2) letter body, (3) editing notes, (4) draft assumptions, (5) Source citations (Quellen) trace. The user has to mentally parse + manually strip non-letter sections before sending. Phase 2 UX upgrade: split the textarea into per-section read-only fields with an explicit "Send body only" copy button; render the citations section as an interactive verifier where each citation can be expanded to show the quoted CV/JD excerpt highlighted in-context against the source. Effort: ~4-6 h (frontend section parser + per-field rendering + citation expander + tests). Schedule: 2026 Q3. Trigger: post-grant UX polish. Cross-references: docs/grant/14-source-class-hierarchy.md doctrine; Loop 25 prompt change in analysis.py + motivation_letter.py. | 4-6 h | 2026 Q3 |
| 79 | **Claude Desktop manual-walk automation via Ghost-OS MCP** — surfaced during PART 7 Loop 23 (Claude Desktop walk documentation). Today the Claude Desktop walk at `docs/grant/mcp-walks-2026-05-21/claude-desktop-walk.md` is a manual operator procedure: open Claude Desktop, type a prompt, screenshot the tool panel, export the transcript. Phase 2 automates this via Ghost-OS MCP (`mcp__ghost-os__*`) which drives the macOS accessibility tree programmatically. Concrete deliverables: (a) `scripts/run-claude-desktop-walk.sh` Ghost-OS driver that launches Claude Desktop, sends the canonical prompt, waits for the response, screenshots the tool panel + final chat state, exports the transcript via the Claude Desktop file menu; (b) `scripts/format_claude_transcript.py` JSON-to-markdown converter (Claude Desktop exports JSON; the grant pack wants markdown); (c) golden-output diff so a regression in tool descriptions or schemas fails CI; (d) screenshot baseline in `docs/grant/mcp-walks-<release>/claude-desktop-artifacts/`. Effort: ~3-4 h (Ghost-OS recipe + driver script + golden-output diff). Schedule: 2026 Q3. Trigger: post-grant operational hardening. **Out of scope for the NLnet submission**: the manual procedure + automated harness (Loops 20-22) together are sufficient for the grant narrative; full automation is operational polish. | 3-4 h | 2026 Q3 |
| 78 | **Database-error surfacing UX (cross-cutting policy)** — surfaced during PART 6 Loop 16 (Gate 6.5) error-layer audit as Layer 11. Today's behavior is inconsistent: some database errors propagate as friendly messages (e.g., profile-update validation failures return 400 JSON), others as generic 500s with no recovery guidance, others are silently swallowed in best-effort `except Exception` blocks. Phase 2 design: coherent policy for which database-layer failures surface to users with what messaging. Concrete cases needing distinct handling: (a) **sqlite lock during high concurrency** — retry-with-backoff + user-friendly "saving…" indicator; (b) **disk-full / quota exceeded** — admin alert path + user-friendly "save unavailable, contact admin" message; (c) **orphaned-foreign-key / referential-integrity** — surface as "record no longer exists, refresh and try again"; (d) **schema-migration drift** — diagnostic-only; should be impossible in production but worth a guard; (e) **best-effort writes that genuinely don't need to surface** — analytics events, audit logs — explicitly documented as silent. Effort: 1-2 d (policy doc + audit pass over sqlite write sites + standardise error-handling pattern + tests). Schedule: 2026 Q3-Q4. Operator decision 2026-05-20 (Loop 16 read-through): cross-cutting design decision, not a code-level fix; deferred from PART 6 closure. | 1-2 d | 2026 Q3-Q4 |
| 77 | ~~**Streaming refactor for chat-message endpoint**~~ — **CLOSED 2026-05-21**. All four sub-pieces shipped: (a) `/api/chat/message/stream` SSE endpoint with hand-rolled `text/event-stream` writer on `BaseHTTPRequestHandler`; (b) `JobAggregationEngine.search_streaming()` generator via `ThreadPoolExecutor + as_completed`, existing `search()` reimplemented as a synchronous drain wrapper; (c) `_dispatch_provider_streaming` token-streaming layer with Ollama (NDJSON) / OpenAI-compatible (SSE) / Google Gemini (SSE) variants + CLI fall-back wrapping; (d) frontend `chatSendStreaming` generic SSE consumer + `chatSendFindStreaming` / `chatSendLetterStreaming` wrappers with in-place bubble mutation. Closes Gate 6.7 (partial results streaming) and unlocks server-pushed progress narration (PART 9's client-side rotation now layers on top of real events for find_jobs + draft_motivation_letter). Tailor / consult intents continue on the JSON endpoint (which still benefits from the parallel fan-out underneath) — extending those to streaming follows the same pattern but is not in the original #77 spec. Commits: `13e6b05` (b), `38e47c0` (refactor prep), `168e251` (a), `27cfbd4` (d find), `7d98011` (c dispatch), `4821b81` (c+d letter integration). Tests: +20 new contract tests across `tests/test_chat_find_jobs_streaming.py`, `tests/test_dispatch_provider_streaming.py`, `tests/test_chat_letter_streaming.py`; 1488 total in repo. | 2-3 d | shipped 2026-05-21 |
| 76 | **Friction-class classification UX polish** — Phase 1 (Bug F Option B, Loops 10.1 + 10.2 + 10.3, 2026-05-20) shipped the deterministic-classifier substrate end-to-end: `friction_classifier.py` (STRONG_MARKERS + SCORED_PATTERNS), `UserProfile.friction_class` field with re-classification semantics (unconditional overwrite on every CV paste so stale values clear), cv_check paste-branch classification hook, Bug C piece-3 + piece-4 dispatcher reads `friction_class`, `analysis.py` friction-context wiring for AI prompts, internal telemetry event (`friction_class_classified` with resolved/confidence/match_count), privacy-notes baseline section in `transparency-notice.md`. Phase 2 remaining: (a) **user-confirmation flow** at classification time — surface "Looks like you're in the X process — is that right?" UI with 7-persona cards + "different one" path + "skip" option, designed using real-world telemetry from Phase 1 to inform defaults (single-suggestion vs multi-card layout, etc.); (b) **advanced edge cases** — multi-match disambiguation UX (when two personas tie at scored), user-correction-after-classification flow (Settings UI to change friction_class), persona-vs-industry mismatch reconciliation; (c) **pattern refinement from telemetry** — analyze production classification accuracy + colloquial-CV vocabulary gaps; refine STRONG_MARKERS + SCORED_PATTERNS tables (current Phase 1 seeded from regulatory citations + persona_fixtures.friction_keywords_for; real users may not write precise statute citations, so Phase 2 refines from actual usage data); (d) **user-visible classification surface** — Settings page shows friction_class with explanation + opt-out + re-classify button; (e) **CV-build-via-chat classification path** — Phase 1 only handles paste-branch; users who build their CV via the 5-question chat flow don't trigger classification — Phase 2 hook for that path runs the classifier on the assembled CV text at build completion; (f) **DPIA-equivalent privacy review** — full data-protection impact assessment beyond GDPR baseline. Effort: ~6h (operator estimate; ~1-2h confirmation UX + ~1-2h pattern refinement + ~1h Settings + ~1h CV-build hook + ~1h DPIA). Schedule: 2026 Q3-Q4. Trigger: post-grant Phase 2 kickoff. | 6 h | 2026 Q3-Q4 |
| 75 | **DE bundle wiring for empty-state recovery affordance labels + Loop 14.1 typing labels** — surface ALL of: "Try lateral roles" / "Drop seniority qualifier" / "Widen location" / Ausländerbehörde caveat / "Auto-relax" / "Retry" / "Give up" / "Start fresh" / "Widened location" / "Dropped seniority qualifier" / "Tried lateral roles" / per-affordance descriptions in `static/i18n/de.json` (and any other languages added between now and Phase 2). **Loop 14.1 expansion (2026-05-20)**: ALSO covers the 6 phase-aware typing labels added in `static/app.js::TYPING_LABELS` (search / tailor / letter / consult / inspire / default "Thinking…"). Currently hard-coded English regardless of user locale across `company_discovery/widening.py` (label strings, `WIDENING_LABEL` dict, `_AUTO_RELAX_*` token tail rendering, `format_auto_relax_suggestion` action prompt strings), `company_discovery/journey.py` (bridge messages, summary block headers, menu line text), and `static/app.js` (TYPING_LABELS). One coherent i18n slice covers all hard-coded EN UI strings — operator decision 2026-05-20 (Loops 8 + 14.1). Effort: ~1-2 h. Schedule: 2026 Q3. | 1-2 h | 2026 Q3 |
| 74 | **Adjacent-cities commute-range search + counts** — extends the Bug C piece 5 (adjacent-criterion counts) work to surface "X postings in <city> AND <adjacent city> within commute range." Currently piece 5 ships per-affordance counts for the 3 shipped widening affordances (widen_location, drop_seniority, try_laterals) but NOT for adjacent cities, because the aggregator layer has no city↔city adjacency graph (`job_type_filter._GERMAN_CITIES` is a flat list of city names; no edges). Shipping the spec example "47 postings exist in Berlin and Halle (within commute range)" requires: (a) a curated city-adjacency table with commute-range edges (Berlin↔Halle, Leipzig↔Halle, Hamburg↔Lübeck, München↔Augsburg, München↔Ingolstadt, etc.); (b) parallel multi-city searches against those adjacent cities; (c) aggregated count surfacing separately from same-location relaxation counts. Effort: 1-1.5 d (adjacency table curation + parallel fan-out + count aggregation + tests). Schedule: 2026 Q3-Q4. **Cross-surface dependency**: depends on #71 (persistent index) for efficient adjacency lookups + #72/#73 (post-fetch annotations) for cross-criterion compatible filtering. Operator decision 2026-05-20 (Loop 7 read-through): scoped OUT of piece 5; shipping adjacent-city counts as theatrical without real adjacency data would be the same doctrine violation as omitting the "loosen language" / "loosen visa-status" affordances. | 1-1.5 d | 2026 Q3-Q4 |
| 72 | **Language-detection heuristic on JD description text + post-fetch language filter** — Powers the "loosen language requirement" affordance in empty-state widening (PART 6 Bug C piece 3), which is currently omitted as theatrical (aggregator layer has no native language field). Effort: 1-2 d (heuristic development + accuracy validation against persona panel — German B1+ / B2+ / C1+ / native-only distinctions, English C1+ acceptable). Schedule: 2026 Q3-Q4. **Architecture**: post-fetch annotator that runs over `AggregatedJob.description` text + caches detected language(s) on `AggregatedJob.raw`. Powers a new `loosen_language` widening affordance once shippable. **Doctrine constraint**: the heuristic must be evidence-backed — surface "detected language: German B1+ (matched: 'B1-Deutsch erforderlich')" with the supporting evidence, not pure inference. **Cross-surface dependency**: depends on #71 (persistent index) for fast filtering at scale. | 1-2 d | 2026 Q3-Q4 |
| 73 | **Visa-status flag detection from JD text + post-fetch annotation** — Powers the "loosen visa-status preference" affordance in empty-state widening (PART 6 Bug C piece 3), currently omitted as theatrical. Effort: 1-2 d. Schedule: 2026 Q3-Q4. **Architecture**: regex + heuristic over `AggregatedJob.description` to detect flags like `Anerkennung-friendly`, `Blue-Card-OK`, `Wiedereinstieg-accepting`, `Ausbildung-class`, `§16d-recognised`, `EU-citizens-only`, `permanent-residence-required`. Annotates `AggregatedJob.raw` with structured flags. Powers a new `loosen_visa_status` widening affordance once shippable. **Cross-surface dependency**: depends on #71 (persistent index) for fast filtering. **Coupling note**: many flags overlap with the SCORE_FRICTION_FIT taxonomy from PART 5 F1 — re-use the existing pathway-quality classifier rather than re-invent. | 1-2 d | 2026 Q3-Q4 |
| 71 | **Persistent job-index for analytics** — build a long-lived facet-indexed sqlite (`location`, `role-bucket`, `seniority-class` derived via title-pattern heuristic, `language-detected` via description heuristic) maintained at search-fan-out time. Powers Bug C piece 2's `DiagnosticEngine` with substantive evidence-backed explanations (e.g., *"47 Senior frontend postings in Berlin and Halle within commute range of Leipzig"*) instead of the current cache-only / cold-cache-fallback pattern. **Includes**: storage growth model (TTL + dedup + GDPR retention), commute-range adjacency table for major DE cities, seniority/language classification heuristics, schema migration. **Cross-surface dependency**: `DiagnosticEngine.generate()` already pluggable via the `cache` parameter — swap in an index-backed implementation without restructuring. **Closes** the cross-class skew structural concern documented in `docs/grant/data-layer-coverage-honesty-note-2026-05-20.md` (free-tier providers under-represent Pflege / Krankenschwester / Anlagenmechaniker SHK / German-civic-tech postings). Effort: 1-2 days. Schedule: 2026 Q3-Q4. Trigger: data-layer expansion or grant-funded infra slice. | 1-2 days | 2026 Q3-Q4 |
| 70 | **Help-surface for clarifying questions in journey phases** — every interactive journey phase should route help-seeking inputs ("?" / "huh" / "what" / "help" / "hilfe" / "?!" / equivalent) to phase-specific HELP TEXT instead of a generic re-ask. Today (post-Bug-B) those inputs land in the re-ask branch with the prompt re-shown verbatim, which is correct guard behaviour but UX-flat. Top-tier UX shape: detect help-seeking, emit a phase-tailored explanation ("preferences are optional filters: 'remote' if you'd only consider remote roles; 'min 50k' if you have a salary floor; 'none' or 'skip' to move on without filters"), then re-prompt. Applies to: discover sub-questions, cv_check, inspire, preferences, review, drill, tailor / letter / consult choice. Not blocking PART 6 closure. Effort: ~2-3 h. | 2-3 h | 2026 Q3 |
| 68 | **Bucket taxonomy expansion for migrant + friction-class persona coverage** — PART 6 walk #3 (2026-05-20, Olga "Senior frontend developer") surfaced that the bucket taxonomy at `company_discovery/job_type_filter.py::TAXONOMY` does not currently include canonical roles for several panel personas. Verified gaps: Aïcha → `Krankenschwester` / `Pflegehelferin` / `Pflegefachkraft` (no bucket match); Mahmoud → `Anlagenmechaniker SHK` / `Auszubildender SHK` (no bucket match); Käthe → `Krankenschwester (Wiedereinstieg)` (no bucket match); Maria → `Altenpflegerin` (no bucket match). Today these personas pass through the journey because role_text falls through to `msg` when no bucket matches — but persona-based categorization / filtering / ranking is missing for them downstream (aggregator job_type_filter is empty, queue ranking can't group by bucket). Add the missing buckets to TAXONOMY with German + English label aliases; verify all 7 panel personas have a bucket entry matching their canonical role. **Cross-surface dependency**: persona_fixtures.PERSONAS canonical roles, ESCO-skills reference data (`docs/esco-integration.md`), aggregator job_type_filter, queue ranking groupings. Effort: 0.5 day (taxonomy curation + tests). **Out of scope for PART 6** per operator decision 2026-05-20 — this is taxonomy curation separate from the intent-extraction-quality fix that's landing in PART 6. | 0.5 day | 2026 Q3 |

---

## Closure summary

- **Items closed in this slice (pre-submission scope-tightening)**: 12
  (#4, #5, #6, #7, #9, #10, #11, #12, #15, #19, #34, #37, #58, #61
  partly — counted as 12 distinct closures by inventory number).
- **Items remaining**: 65.
- **Targets**: 2026 Q3 = 31 items; 2026 Q4 = 20 items; 2027 Q1 = 12 items; trigger-driven = 2.

This backlog is the contract: every item here is tracked, with an
owner-rough effort estimate, and an honest quarter target. Items that
shift quarter get a dated note appended below.

## Items deferred to non-coding actors (operator-side)

These three items are formally deferred from the in-flight "items #4–7 to 100%" execution because they structurally require resources outside the coding-agent loop. The operator engages them in parallel; they converge into 100% completion alongside the code work.

| # | Title | Why deferred | Operator action |
|---|---|---|---|
| D1 | **Translate 4 new language bundles** (Arabic, Ukrainian, Turkish, Romanian) | Auto-translation via DeepL / Google would compromise the project's stated accuracy bar (PART 5 + PART 8 doctrines require source-grounded language); human translators are the right path. The Arabic translation also needs careful RTL-aware copywriting (UI hint paragraphs, button labels, regulatory citations like §16d AufenthG translated into culturally-appropriate phrasing). | Operator engages 4 translators (one per language) ideally with civic / employment / migration domain familiarity. Coding agent ships RTL CSS + i18n bundle scaffolding + AI quality parity testing against whatever translations arrive. |
| D2 | **Native iOS (Swift) + Android (Kotlin) mobile apps** | Coding agent's Python + JS stack doesn't cover native Swift / Kotlin development. Cross-platform alternatives (Flutter, React Native) are possible fallbacks but compromise on platform-native UX patterns; native is the higher bar. | Operator engages mobile developers OR confirms cross-platform Flutter/RN is acceptable. Coding agent ships PWA (Progressive Web App) variant + responsive web in the meantime — PWA covers most native-app affordances (offline, install-to-home-screen, push notifications) without platform-specific code. |
| D3 | **External penetration test by an accredited security firm** | The coding agent can ship an internal security review (code audit, threat-model document, dependency-vulnerability scan, authn/authz audit) but a real third-party pentest requires a contracted firm with offensive-security credentials (ideally one that's worked with EU civic-tech projects so they understand the threat model). | Operator contracts a security firm (suggestions: Cure53, Trail of Bits, NCC Group, ProtectInfo for EU coverage) for a formal pentest. Coding agent ships the internal review + scope-of-work template the firm can quote against. |

These three deferrals do NOT block grant submission readiness. They're the items where money / human time / external contracting is the rate-limiting resource, not coding hours.

## Append log

- **2026-05-19**: file created during the pre-submission
  scope-tightening slice (PART 8). 53 items catalogued; 12 marked
  closed in-slice.
- **2026-05-20**: item #66 added — Methodology band recalibration
  (Path B reserve). Trigger-driven. Operator decision after Path A
  approval (anchor guidance in `build_auto_fit_prompt`): if real user
  feedback shows the post-Path-A calibration is off, this item gets
  scheduled with the cross-surface downstream audit. Currently
  reserved; no quarter assigned.
- **2026-05-20**: item #67 added — Cloud-AI re-validation of PART 5
  F1/F2 gates. Trigger-driven (first cloud-AI deployer with
  telemetry consent). Captures the open-source-AI ceiling margins
  documented in PART 5 closure: Mahmoud ausbildung ≥75 sample
  variance on llama3.1:8b + parking 30% boundary residual. Expected
  outcome: cloud-AI closes both margins without prompt changes;
  becomes a PART 10 honesty-matrix entry.
- **2026-05-20**: item #68 added — Bucket taxonomy expansion for
  migrant + friction-class persona coverage. PART 6 walk #3
  surfaced the gap during the Olga "Senior frontend developer"
  investigation: canonical roles for Aïcha, Mahmoud, Käthe, Maria
  not in TAXONOMY. Out of scope for PART 6's intent-extraction
  fix; scheduled for 2026 Q3 taxonomy-curation slice.
- **2026-05-21**: item #78 added — Database-error surfacing UX.
- **2026-05-21**: item #79 added — Claude Desktop manual-walk automation via Ghost-OS MCP (PART 7 Loop 23).
- **2026-05-21**: item #80 added — Cover-letter section UI split + interactive citation verifier (PART 8 Loop 25).
- **2026-05-21**: PART 11 Loop 36 audit — duplicate #58 renumbered. The active "Cost-saving doctrine measured-outcome instrumentation" item was re-using #58 (which had already been used by a CLOSED historical entry). Renumbered the active item to #69 (the only unused slot in the 50-79 range) so each line has a unique number. Historical CLOSED #58 entry preserved verbatim.
- **2026-05-21**: item #77 (streaming refactor) CLOSED — all four sub-pieces (SSE endpoint, parallel fan-out, dispatch-layer token streaming, frontend SSE consumer) shipped + runtime-proven end-to-end against live aggregators on a real dev server. Tests at `tests/test_chat_find_jobs_streaming.py`, `tests/test_dispatch_provider_streaming.py`, `tests/test_chat_letter_streaming.py` (+20 contract tests; 1488 total in repo).
  Surfaced during PART 6 Loop 16 (Gate 6.5) as Layer 11 of the
  14-error-layer audit. Cross-cutting design decision (which
  database-write failures should surface to users with what
  messaging) rather than code-level fix; deferred from PART 6
  closure per operator decision 2026-05-20.
- **2026-05-20**: item #77 added — Streaming refactor for chat-
  message endpoint. Surfaced during Loop 14 read-through (Gates
  6.6 + 6.7): zero streaming infrastructure today; Loop 14.1
  ships static phase-aware typing labels (Gate 6.6 close) but
  Gate 6.7 (partial results streaming) cannot close without
  architectural refactor. Combined slice: SSE + concurrent
  aggregator fan-out + token-streamed AI + frontend in-place
  bubble mutation. Operator decision 2026-05-20: don't ship in
  pieces (intermediate states worse than today). Schedule
  2026 Q3-Q4, trigger post-grant kickoff.
- **2026-05-20**: item #75 expanded — Loop 14.1 added the 6
  phase-aware typing labels in `static/app.js::TYPING_LABELS`
  (search / tailor / letter / consult / inspire / default) to
  the Phase 1 EN-only UI string surface. Same DE bundle slice
  now covers BOTH the empty-state recovery affordance labels
  AND the typing labels. One coherent i18n slice.
- **2026-05-20**: item #76 added — Friction-class classification
  UX polish. Phase 1 substrate (deterministic classifier + field
  + cv_check hook + dispatcher rewiring + AI prompt wiring +
  telemetry + privacy notes) shipped across Loops 10.1-10.3.
  Phase 2 layers user-confirmation flow, pattern refinement from
  telemetry, Settings UI, CV-build-via-chat hook, full DPIA on
  top of the working substrate. Operator decision 2026-05-20
  (Loop 10 verdict): Option B picked on DESIGN-QUALITY grounds —
  Phase 2 work benefits from real-user telemetry data to inform
  the UX (single-suggestion vs multi-card defaults, etc.) before
  designing.
- **2026-05-20**: item #75 added — DE bundle wiring for empty-
  state recovery affordance labels. Surfaced during Bug C piece 6
  (Loop 8): the new "Start fresh" affordance + the static
  WIDENING_LABEL dict + the start-fresh bridge message ship EN-
  only, consistent with the EN-only rendering across pieces 1-5.
  Operator-approved scope choice: single Phase 2 slice covering
  the whole affordance-label set (manual menu + auto-relax +
  summary block + bridge messages) over per-piece partial DE
  coverage.
- **2026-05-20**: item #74 added — Adjacent-cities commute-range
  search + counts. Surfaced during Bug C piece 5 read-through
  (Loop 7): the aggregator has no city↔city adjacency graph,
  so shipping "X postings in Berlin AND Halle (within commute
  range)" would be theatrical. Operator-approved scope split:
  piece 5 ships per-affordance counts for the 3 shipped
  widenings; adjacent-cities work moves to Phase 2. Coupled
  with #71 + #72 + #73.
- **2026-05-20**: items #72 + #73 added — Language-detection
  heuristic + visa-status-flag detection. Surfaced during Bug C
  piece 3 affordance audit: the operator's spec included "loosen
  language requirement" + "loosen visa-status preference"
  affordances, but the aggregator layer has no native language
  or visa-status field on AggregatedJob or in any provider's
  .search() params. Shipping them as widening affordances would
  be theatrical (selecting them would change nothing). Omitted
  for piece 3; #72 + #73 capture the post-fetch annotation work
  to make them real. Both depend on #71 (persistent index) for
  fast filtering. Scheduled 2026 Q3-Q4.
- **2026-05-20**: item #71 added — Persistent job-index for
  analytics. Surfaced during Bug C piece 2 read-through: the
  current aggregator architecture is a real-time broker, not an
  analytics database. Cache TTL = 1h with no facet access; on
  cold-cache deploys the diagnostic engine hits the strict-fact
  fallback frequently. A persistent facet-indexed sqlite would
  unlock substantive evidence-backed diagnostics. Operator
  decision 2026-05-20: defer to Phase 2 — current cache-only seam
  is doctrine-correct and forward-compatible. Scheduled 2026 Q3-Q4.
- **2026-05-20**: item #70 added — Help-surface for clarifying
  questions in journey phases. Surfaced during PART 6 Bug B fix:
  the new re-ask branch handles unrecognised input by re-showing
  the prompt, but inputs like "?" / "huh" / "what" / "help" deserve
  a phase-tailored explanation, not just a re-prompt. Top-tier UX
  enhancement spanning every interactive journey phase. Effort
  ~2-3 h; scheduled 2026 Q3.
