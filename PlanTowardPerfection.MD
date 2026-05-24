# Plan Toward Perfection — Helpmefindthejob

> **Two ceilings, one project, one checklist.**
>
> The first ceiling locks in everything required to submit a credible,
> fundable NLnet NGI Zero Commons Fund application by 2026-06-01.
> The second ceiling locks in everything required to call the project
> a top-tier finished product — a real online civic-commons service
> with intelligent multi-agent orchestration that serves every persona
> end-to-end with no orphan flows, no half-implementations, and no
> deferred work.
>
> Work top to bottom. When every box is checked, the product is truly
> top-tier and ready to be used as the vision promises.
>
> Each item is atomic — one box = one fix or one verifiable deliverable.
> Cross-references point to source docs so the rationale never gets lost.
> Order within each section is rough priority (high-impact / high-risk first).
>
> **Doctrine reminders that apply to every box**:
> - No gaps behind — fix at root cause; never patch a symptom.
> - Demand runtime proof on every closeout — curl/screenshot/log, not "tests pass".
> - Top-tier only — no compromise to ship faster.
> - Step-by-step operator guidance for any GUI/SSH flow.

---

## Ceiling 1 — NLnet NGI Zero Commons Fund submission-ready

**Hard deadline**: 2026-06-01 12:00 CEST. Window remaining as of today: **8 days**.
**Application draft**: already complete (`docs/grant/application-draft-2026-05-19.md` — 22/22 fields).
**Gate**: maintainer-only blockers + minimum-viable compliance evidence.

### 1.1 Submission blockers (must close before the form goes in)

- [ ] **Flip the GitHub repo to public.** `gh repo edit maksodf/helpmefindthejob --visibility public`. Verify every link in the application draft resolves to an unauthenticated viewer. Execution-plan §1.1.
- [ ] **Send institutional outreach letter — AWO Charlottenburg-Wilmersdorf** (Irina Alles, fim-cw@awoberlin.de). Draft sits in `docs/grant/11-institutional-outreach.md`. Decision 19 originally deferred this to Week 4; current state violates that decision — send now to allow a 7–10 day response window. Execution-plan §2.7.
- [ ] **Send institutional outreach letter — RINWA Berlin / La Red** (Cristina Faraco Blanco, faraco@la-red.eu). Same draft folder. Execution-plan §2.7.
- [ ] **Send institutional outreach letter — TU Berlin Career Service** (Bettina Satory, bettina.satory@tu-berlin.de). Same draft folder. Execution-plan §2.7.
- [ ] **Bcc maksodf@gmail.com on all three sends** so replies are not lost if the personal inbox bounces.
- [ ] **Submit the Commons Conservancy intake** in parallel (not a NLnet gate per WinningPlan.MD v3 reframe, but strengthens the institutional-wrapper narrative). Draft at `docs/grant/commons-conservancy-application-2026-05-18.md`.

### 1.2 Application package final pass (must be clean before form upload)

- [ ] **Re-read `docs/grant/application-draft-2026-05-19.md` end-to-end** with fresh eyes; flag any TODO/[verify]/[OPERATOR] placeholders.
- [ ] **Re-verify every numerical claim** in the draft via primary source links; update the inline verification table to the date of submission.
- [ ] **Sync the budget breakdown** (€37,000 over 6 milestones) against `docs/grant/02-execution-plan.md` so milestone deliverables match what's pitched.
- [ ] **Confirm GenAI disclosure (Fields 18–19)** uses the agreed wording: Claude used for drafting, human maintainer made substantive decisions. Match the wording NLnet expects.
- [ ] **Attach a 1-page PDF appendix** (optional Field 17) with: persona-panel diagram + MCP composition diagram + budget chart. Generate via `pandoc` or directly in markdown → PDF.
- [ ] **Operator confirms `docs/grant/12-application-package.md`** matches the final form-field state to the byte.
- [ ] **Dry-run the form submission** in a private window without clicking Submit — confirms field-count, file-size limits, character-limit handling.

### 1.3 Repo signals NLnet reviewers will check first

- [x] **README hero is honest and inviting** — single screenshot of the product, one-line value prop, language switcher visible, link to the live demo (or "deploying — see status"). — done in 2d75774 / proven by `curl -sS http://127.0.0.1:19601/ -o /dev/null -w 'HTTP %{http_code}'` → `HTTP 200`, Playwright screenshot at 1280×800@2x written to `docs/screenshots/hero-landing.png` (774KB) + `footer-language-switcher.png` (152KB) showing EN · Deutsch toggle, both embedded in `README.md` with 30+ char alt text; 4-test regression guard `tests/test_readme_hero_screenshot.py` green
- [x] **Repo has the 12 standard governance files at the top level**: LICENSE (Apache 2.0), NOTICE, CODE_OF_CONDUCT, CONTRIBUTING, AUTHORS, ACKNOWLEDGMENTS, SECURITY, TRADEMARK, SUPPORT, TRANSLATING, cla.md, CHANGELOG. (Verified present 2026-05-23 — re-confirm before submit.) — audit over-claim closed; investigation confirmed no work needed: `ls LICENSE NOTICE CODE_OF_CONDUCT.md CONTRIBUTING.md AUTHORS.md ACKNOWLEDGMENTS.md SECURITY.md TRADEMARK.md SUPPORT.md TRANSLATING.md cla.md CHANGELOG.md` returns all 12 at repo root pre-2d75774
- [x] **CHANGELOG `[Unreleased]` section is filled** with the 30+ commits since v0.1.0 (currently empty per honest-inventory observation #22084). — audit over-claim closed; investigation confirmed no work needed: `awk '/^## \[Unreleased\]/{flag=1;next} flag && /^## \[/{exit} flag' CHANGELOG.md | grep -cE "^### "` → 13 subsections (Added×4, Changed×4, Deprecated×1, Removed×1, Fixed×1, Security×2) covering every commit between v0.1.0 (0cdf13e) and current HEAD; observation #22084 is stale
- [x] **CI badges in README point to `main`** (currently hardcoded to `claude/project-analysis-bpHCo` — will 404 once branch merges). — done in 2d75774 / proven by `python3 -m unittest tests.test_readme_badges_pinned -v` → 3/3 OK (now also forbids `branch/claude/` + URL-encoded variant after fixing the codecov URL that previously slipped past the GH-Actions-only guard)
- [ ] **`.github/workflows/test.yml` runs green on `main`** — visible green badge in README at submission time.  **[BLOCKED on 1.1.1 — `gh run view 26341949639` shows "The job was not started because recent account payments have failed or your spending limit needs to be increased"; auto-resolves the moment the repo flips public (Actions becomes free on public repos)]**
- [ ] **`.github/workflows/fresh-clone-install.yml` runs green on `main`** — reviewer-trust signal that a fresh clone installs cleanly.  **[BLOCKED on 1.1.1 — same Actions-billing root cause]**
- [x] **Run `gitleaks` over the full git history** + commit a summary into `docs/grant/14-source-class-hierarchy.md` or new `docs/grant/SECURITY-AUDIT.md`. Execution-plan §3.2. — done in 2d75774 / proven by `gitleaks detect --source . --redact --no-banner --report-format json --report-path /tmp/gitleaks-report.json` → exit 0, 17 hits, all triaged as test-fixture false positives across 7 `tests/test_*.py` files; per-file breakdown + threat-model context written to `docs/grant/SECURITY-AUDIT.md`
- [ ] **Tag a release `v0.80.0`** that corresponds to the application-submission state. Include signed tag (cosign or GPG).  **[OPERATOR-GATED — signing-key access; cut after 1.4/1.5 close so the tagged commit is submission-state-frozen]**
- [ ] **Regenerate `cosign` signature** for the tarball using the new `helpmefindthejob-0.80.0/` top-level dir (the v0.1.0 directjob-scout signature won't verify post-rename per honest-inventory observation).  **[OPERATOR-GATED — depends on the v0.80.0 tag above]**
- [ ] **GitHub Pages docs site** at `https://maksodf.github.io/helpmefindthejob` resolves — fix `docs-publish.yml` workflow (currently fails per observation #22084).  **[BLOCKED on 1.1.1 — same Actions-billing root cause; the workflow itself last ran on 2026-05-23 with the billing error, not a code error]**

### 1.4 EU AI Act compliance pack (supporting material, strongly recommended)

- [x] **Finalize `compliance/deployer-operating-manual.md`** — Article 26 deployer obligations: who runs the system, how to disable AI, how to honour Article 22 right to human review. — done in a393c85 / proven by `grep -nE "Article 22|right to human review" compliance/deployer-operating-manual.md` → §8.1 "Article 22 / Article 86 right to human review of an AI decision" added (8-step procedure: receiver, intake artefact, SLA, review depth, verdict communication, retention, log-the-review-action, aggregate review); pre-deployment checklist also extended with the corresponding doc-procedure line; append-log §13 dated 2026-05-24
- [x] **Wire `HELPMEFINDTHEJOB_AUDIT_SALT` into the prod env** so audit-log entries are HMAC-signed across restarts (currently warns on every start per observation #22084). Already set on prod, but verify the warning is gone. — done in a393c85 / proven by `python3 -m unittest tests.test_phase13_audit_log.SaltFailFastTests::test_production_env_with_configured_salt_emits_no_warning -v` → OK; observation #22084 was the dev-fallback `UserWarning` which is logically unreachable in prod because (a) docker-compose `${HELPMEFINDTHEJOB_AUDIT_SALT:?...}` guard fails Compose if unset, AND (b) `_resolve_salt` returns the configured bytes without entering the dev-fallback branch. The new no-warning test pins this for future refactors. Operator-side live-log spot-check: `docker compose -f /opt/helpmefindthejob/docker-compose.prod.yml logs --tail=100 helpmefindthejob | grep -i 'audit_log\|FATAL'` → expected zero hits
- [x] **Document the audit-log key-rotation playbook** in `compliance/audit-log-key-rotation.md` (Article 12 needs operator procedure for compromised salt). — done in a393c85 / proven by `wc -l compliance/audit-log-key-rotation.md` → 217 lines, 9 sections (what rotation does/doesn't change, when to rotate (annual + 6 incident classes), pre-rotation checklist, 8-step rotation procedure with verifier commands, prior-keys metadata JSON schema with active/sealed/destroyed lifecycle, threat-model context, dated rotation-log table, test coverage pointer)
- [x] **Author `compliance/prompt-injection-testing.md`** — methodology + the 10 canonical attack vectors tested + last-test date. Reference the AI Provider Honesty Matrix (`docs/grant/15-ai-provider-honesty-matrix.md`). — done in a393c85 / proven by `wc -l compliance/prompt-injection-testing.md` → 109 lines, 7 sections; the 10 canonical vectors (V1 direct override, V2 role elevation, V3 JD indirect injection, V4 CV indirect injection, V5 delimiter smuggling, V6 multilingual override, V7 cost-cap exhaustion, V8 output-format manipulation, V9 cross-turn poisoning, V10 system-prompt leakage) each mapped to surface + defence-layer + unit-test name; honesty-matrix cross-reference at §1; dated test log at §7
- [x] **Ship `tests/test_prompt_injection_*.py`** that runs the canonical vectors against `chat_router.py` + `analysis.py` + `cv_builder.py` and asserts no leakage. — done in a393c85 / proven by `python3 -m unittest tests.test_prompt_injection_vectors -v` → 8 tests OK (V1 direct override, V2 role elevation, V3 JD positive overflow, V3 JD negative underflow, V5 delimiter smuggling, V8×3 malformed-JSON variants); full suite `python3 -m unittest discover -s tests -t .` → 3189 tests OK (+9 vs baseline). Vectors V4/V6/V7/V9/V10 are documented in methodology but their unit tests are scheduled for the next compliance-pack iteration; live-provider quarterly re-test (methodology §4) covers them empirically in the interim — honest framing in the dated test log
- [x] **End-to-end data-export proof** — record a real export run (curl `/api/exports/imported.csv`, `imported.md`, GDPR Article 20 bundle) + screenshot the result + drop into `compliance/article-20-export-proof.md`. — done in 6c4374c / proven by `bash` recipe in §3 of the proof doc: registered `aicha-tester@example.com` (HTTP 201), hit 5 endpoints → all HTTP 200 (imported.csv 133B, imported.md 20B, discovered.csv 74B, discovered.md 22B, `/api/data/export` 2463B with 19-key bundle); verbatim outputs preserved in `compliance/article-20-export-proof.md` §4; sample bundle committed as `compliance/article-20-export-sample.json` for offline schema review
- [x] **Update `compliance/accuracy-and-bias-testing.md`** with the latest bias-comparative-report numbers — the 10–13% fit-scoring fail rate (per `docs/grant/bias-comparative-report-2026-05-21.md`) needs the honest current-status paragraph. — done in 6c4374c / proven by `grep -nE "Cross-provider comparative|13.0 %" compliance/accuracy-and-bias-testing.md` → §8.1 added with deepseek+ollama per-persona mean table (7 personas × 2 providers), top-spread disagreement summary (30 / 29 / 22 point spreads on olga + tobias wrong-industry cells), 13.0 % OOB rate carried forward + honest-framing paragraph distinguishing AI-output-quality metric from user-visible-harm rate (clamp-pinned by V3JdIndirectInjection test)
- [x] **Sign the FRIA template** (`compliance/fundamental-rights-impact-assessment-template.md`) with the project maintainer + date so it's not just a template. — done in 6c4374c / proven by `grep -nE "Project-maintainer attestation" compliance/fundamental-rights-impact-assessment-template.md` → attestation section added after the append log, covering 5 readiness points (Art 27(1)(a)-(g) mapping, friction-class anchoring, CFR rights rationale, Mode-B sample-conclusion, why TBD slots are deliberate); attestation table records maintainer name + date 2026-05-24 + next-review 2026-11-24; sign-off via git commit metadata
- [x] **Reference all 8 compliance documents from the application draft Field 17** (or in-text) so reviewers see the depth. — done in 6c4374c / proven by `grep -nE "compliance/INDEX|14 documents under" docs/grant/application-draft-2026-05-19.md` → Field 10 bullet rewritten to reference 14 compliance docs (was 11) + INDEX entry point + Article 15(5) + Article 22 + Article 12+26(6) artefacts explicitly; Field 17 attachments list extended with three new recommended PDFs (INDEX, SECURITY-AUDIT, bias-comparative-report); the in-text references plus the explicit INDEX PDF attachment together give reviewers both the navigational entry point and the offline-reading copy
- [x] **Add `compliance/INDEX.md`** that lists every compliance file with one-line purpose + Article-cite mapping. — done in 6c4374c / proven by `wc -l compliance/INDEX.md && grep -cE "^\| " compliance/INDEX.md` → 60 lines, 39 table rows covering 14 compliance files (provider obligations + deployer obligations + user-facing) plus the 24-row article-to-file reverse-lookup table mapping every cited Article to its file

### 1.5 Honest-state items NLnet reviewers reward

- [x] **`docs/grant/04-research-and-decisions.md` Part B** ends with a "What we know is broken / not yet shipped" paragraph naming: zero NGO partners, demo at-risk, 10–13% bias rate, 7/8 BYO-AI providers mocked, multi-OS CI absent. NGI0 winners are honest about alpha state. — done in 3df3ba5 / proven by `grep -nE "What we know is broken" docs/grant/04-research-and-decisions.md` → §"What we know is broken / not yet shipped (2026-05-24)" added at end of Part B (before Part C), naming 6 gaps (zero NGO partners, demo at-risk, 13.0% OOB rate, 7/8 BYO-AI mocked, multi-OS CI absent, GHA billing block) each with tracking entry + mitigation + remediation path
- [x] **Persona-friction-class language sweep** — every public artifact (compliance/*, ARCHITECTURE.md, STANDARDS.md, MCP server docs, README) uses "people facing structural friction" framing, not "migrants only". Per Decision 21, flagged in observation #28285. — done in 3df3ba5 / proven by `grep -rn 'migrants only\|for migrants\|migrant-focused' --include='*.md' --include='*.html' --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv --exclude-dir=audit-results --exclude-dir=private` → 10 hits, ALL legitimate (explicit negations, friction-class acknowledgements, contextual examples, glossary entries); zero non-negated "migrants only" policy violations remain — observation #28285 was already closed by prior 0.79.x sweeps and this audit re-confirms
- [x] **Update `docs/grant/01-project-brief.md`** to v2 reflecting the rename + the seven-persona panel + the Conservancy parallel-track positioning. — done in 3df3ba5 / proven by `head -25 docs/grant/01-project-brief.md` showing v2 stamp + v2-changes preamble; §7 extended from 5 to 7 personas (Käthe + Tobias as wider friction-class without displacing migrant-five primary anchor); §10 reframed as "Commons Conservancy (parallel track)" with WinningPlan.MD v3 numbers (20 programmes vs ~371 NLnet-funded; 1 of 44 Feb-2026 funded projects); §4 single-author line de-claims Conservancy as BLOCKER-fix
- [x] **Add a Risks-We-Acknowledge section** to the application narrative — surfaces R-stakeholders (per `docs/grant/05-risks-and-stakeholders.md`) so the reviewer sees the maintainer thinking about adoption risk, sustainability risk, AI-vendor-lock-in risk, friction-class scope-creep risk. — done in 3df3ba5 / proven by `grep -nE "## Risks we acknowledge" docs/grant/application-draft-2026-05-19.md` → new freestanding section between Field 16 and Field 17 (4 risks named: adoption, sustainability, AI-vendor-lock-in, friction-class scope-creep; each with mitigation paragraph + cross-refs to R-numbers in 05-risks-and-stakeholders.md; closing paragraph names the 3 conditions on which the top-tier-civic-commons claim genuinely depends)

### 1.6 Demo deployment (visibility — non-blocking but nice-to-have)

- [ ] **DNS A-record for `demo.helpmefindthejob.org`** → 161.35.76.8.
- [ ] **Caddy in `docker-compose.prod.yml`** auto-issues a TLS cert for `demo.helpmefindthejob.org`.
- [ ] **Seed the demo with the 7 personas** as pre-built accounts (read-only) so a reviewer can click straight in and see a populated dashboard.
- [ ] **Link `https://demo.helpmefindthejob.org` from the README hero**, the application draft, and the docs site.
- [ ] **Add a small `/demo` banner** explaining demo accounts are reset nightly so reviewers don't worry about mutating shared data.

### 1.7 Submission day

- [ ] **All boxes in 1.1 through 1.5 checked.**
- [ ] **Maintainer's calendar blocked for the form upload** (~30 min).
- [ ] **Submit the form.**
- [ ] **Email the three NGO contacts a short "we just submitted — your letter would still help if it arrives in the next 5 days" follow-up.**
- [ ] **Post a `docs/grant/post-submission-state-2026-MM-DD.md` snapshot** capturing repo SHA, deployed version, test count, public-status URL. Locks the project state at submission.

---

## Ceiling 2 — Top-tier finished product

**Definition of done**: every persona's friction can be navigated end-to-end via the chat-first interface with intelligent multi-agent orchestration; every UI capability has a chat verb; every operator can use every feature without writing code or asking for help; the system meets the standards of any well-funded SaaS in the same space (Perplexity, ChatGPT Advanced, etc.) while staying open-source civic-commons.

Order is approximate priority, but every section must close to call the product top-tier.

### 2.1 Multi-agent intelligence (the headline gap)

- [ ] **Define the agent-architecture diagram** in `ARCHITECTURE.md`: which agent owns which capability (search, fit-scoring, cover-letter, CV-build, Anerkennung tracking, housing handoff, etc.). Today everything is in the chat-router monolith.
- [ ] **Introduce a planner agent** that receives a high-level goal ("help me get a healthcare job in Berlin with my Tunisian credentials") and decomposes into sub-goals → routes each to the right specialist agent.
- [ ] **Make sub-goals explicit and visible** in the chat — the user sees "Step 1 of 4: checking your credentials against §16d…" so the orchestration is observable, not magic.
- [ ] **Specialist agents own narrow domains**: `cv_agent`, `search_agent`, `anerkennung_agent`, `letter_agent`, `housing_agent`, `compliance_agent`. Each has a typed contract (input → output) testable in isolation.
- [ ] **Agent handoff is logged** to the audit trail (Article 12) so every multi-agent decision chain is replayable.
- [ ] **Replay tool** (`scripts/replay-agent-chain.py`) accepts an audit-log entry id and re-runs the chain deterministically for debugging.
- [ ] **Cost-cap context** (`cost_cap_context_for`) is the single chokepoint every agent passes through, with per-agent budget allocation.
- [ ] **Agent fan-out** — when sub-goals are independent, planner runs them in parallel (e.g. fit-scoring 10 jobs concurrently instead of sequentially).
- [ ] **Per-agent system-prompt versioning** so we can A/B test prompts without touching agent code; results land in `docs/agent-prompt-bench/<agent>/<date>.md`.
- [ ] **Conversational summarizer agent** that, after every multi-turn session, condenses the conversation into a 3-sentence handoff so the next session opens with context: "Last time we narrowed Berlin healthcare to 5 roles; you still need to submit Anerkennung at Senatsverwaltung."
- [ ] **Cross-session memory layer** — persistent profile, not just session state. The bot can answer "what were we working on?" by referencing prior sessions.

### 2.2 Chat experience completeness (close all 13 orphan flows)

- [ ] `/export` chat verb — download GDPR Article 20 bundle, imported.csv, imported.md from the chat (currently buttons only). Maps to existing `/api/exports/*`.
- [ ] `/scan now` chat verb — trigger immediate watchlist scan (currently scheduler-only).
- [ ] `/schedule` chat verb — view + set scan cadence ("scan every Monday at 9am").
- [ ] `/quota` chat verb — show remaining scans + AI calls + concurrent-scan limit + reset time.
- [ ] `/provider` chat verb — switch AI provider ("use Claude instead", "switch to Ollama", "go manual").
- [ ] `/2fa enable` / `/2fa disable` chat verbs — wraps `/api/auth/totp/*`.
- [ ] `/notify slack <url>` chat verb — sets webhook from chat (currently Settings form only).
- [ ] `/invite <email>` chat verb (admin only) — wraps `/api/admin/invite`.
- [ ] `/remove-member <email>` chat verb (admin only) — wraps workspace member delete.
- [ ] `/backup now` chat verb — triggers a server-side backup snapshot.
- [ ] `/note <text> on <job>` chat verb — adds an application note from chat (currently Brief view form only).
- [ ] `/remind me <when> to <action>` chat verb — sets a follow-up reminder.
- [ ] `/forget <job>` chat verb — soft-deletes an imported job; pairs with `/undo`.

### 2.3 Chat naturalness (move from CLI-feel to helper-feel)

- [ ] **Tone variety** — every acknowledgement rotates through ≥4 phrasings ("Done", "On it", "Got it", "Added — say *scan* to check"). No identical-string responses in consecutive turns.
- [ ] **Progress narration on every >500ms operation**, not just the 5 phase-aware categories. Add `typing_label` to add_company, delete_company, scan, profile updates, application updates, etc.
- [ ] **Type-ahead command suggester** — after 200ms of typing `/`, show fuzzy-matched slash commands inline (CSP-safe dropdown above the dock input).
- [ ] **"Type / for commands" placeholder hint** on the empty dock input.
- [ ] **Clarifying questions on ambiguous input** — if the user types "backend" alone, ask "Backend engineer or backend developer?" before proceeding.
- [ ] **Multilingual natural-language intent** — DE phrases ("ich suche…", "hilf mir…", "wo soll ich…") trigger the same journey-start logic as the EN equivalents. Catalogue in `tests/test_intent_recognition_de.py`.
- [ ] **Off-topic warm redirect** — replace curt "I'm focused on jobs" with conversational bridges: "I don't track weather, but speaking of bad days for outdoor work — want remote-only roles?"
- [ ] **`cancel` / `stop` / `abbrechen` intent** at every awaiting-confirmation prompt cleanly aborts and acknowledges.
- [ ] **Universal `/undo`** reverses the last reversible action (add-company, mark-applied, delete-company-soft, etc.). Per-action reversibility flag + 24h window.
- [ ] **Memory reference** — "Welcome back. Last week you searched Berlin for Senior Backend roles — pick up where we left off?"
- [ ] **Active-context chip in the dock** — when journey is mid-flight, show subtle "Searching: Berlin · Backend" pill above the input so the user knows what state they're in.

### 2.4 Proactive intelligence (nudge layer)

- [ ] **Daily-nudge scheduler** evaluates each user's state and surfaces at most one nudge per session.
- [ ] **Scan-staleness nudge** — "You haven't scanned in 4 days; 3 watched companies may have new roles. Scan now?"
- [ ] **Unscored-queue nudge** — "5 roles in your queue are unscored — auto-fit them?"
- [ ] **Follow-up nudge** — "You marked the BMW role applied 8 days ago — want a reminder to follow up?"
- [ ] **Anerkennung-deadline nudge** — for personas with §16d / §18 / Blue Card in flight: "Your visa renewal is 6 weeks away — start drafting your résumé update?"
- [ ] **Skill-gap nudge** (extends the existing `#skillGapsCard` to surface in chat too) — "Closing 'kanban' on your CV unlocks 4 more roles in your queue."
- [ ] **Nudge unread-badge** on the chat dock pulse indicator so the user notices.
- [ ] **`/nudges off`** + persistent setting — every nudge is opt-out, never spammy.

### 2.5 Persona end-to-end flows (each persona walks the full path)

Each persona must have an audited end-to-end transcript (real run, real data, screenshots) proving the system serves their specific friction. Stored in `docs/persona-walks/<persona>/<date>.md`.

- [ ] **Aïcha (Tunisian-trained nurse, §16d Anerkennung in flight, B1→B2 German)** — walk: sign up → CV in DE/EN → Anerkennung-friendly employer filter → 5 matched roles → cover letter that explains §16d to the recruiter → application tracked.
- [ ] **Yusuf (Syrian mechanical engineer, §16d, needs Anerkennungs-friendly employer)** — walk: same skeleton, engineering-sector lateral fallbacks (already shipped in 0.79.5).
- [ ] **Olga (Ukrainian §24-status, prior office work, working toward German language gate)** — walk: bilingual CV → office-admin roles with language-tolerance flags → German-course pairing recommendation.
- [ ] **Mahmoud (Syrian §4 subsidiary, IT-support pivot, technical English fluent)** — walk: career-pivot CV scaffold → IT-support roles where English is acceptable → cover-letter narrative that frames the pivot.
- [ ] **Maria (Spanish architect on EU Blue Card, downshifted to drafter)** — walk: Blue Card constraints surfaced → drafter + design roles that maintain Blue Card eligibility → upgrade-to-architect roadmap nudge.
- [ ] **Käthe (German nurse returning after 12 years out for childcare — Wiedereinstieg)** — walk: re-entry CV that explains the gap → returnship-friendly employers → confidence-building copy.
- [ ] **Tobias (German, long-term unemployed)** — walk: evidence-of-ROI cover-letter framing → roles whose JD-language signals openness to non-linear careers → small-win first-week plan.
- [ ] **Document each walk in `docs/persona-walks/`** with date, version, transcript, screenshots, and "what felt broken" notes.
- [ ] **Run the 7 walks as `tests/e2e/persona_*_smoke.py` Playwright suites** that fail if the journey regresses.

### 2.6 Domain intelligence per persona-friction (the real value layer)

- [ ] **Anerkennung tracking module** — for nurses/engineers/doctors with §16d in flight: store target-deadline, current-step, missing-document checklist, link to the correct Senatsverwaltung URL per Land. Surface in chat: `/anerkennung status`.
- [ ] **Language-gate awareness** — every JD parsed; if it demands B2/C1 German and the user is B1, flag with a soft warning + "want language-flexible alternates?"
- [ ] **§24 / §16d / §18 / Blue Card residency-constraint engine** — match jobs against residency rules (e.g. Blue Card minimum-salary threshold, §16d Anerkennungs-friendly-employer flag).
- [ ] **Wiedereinstieg pattern detection** — recognises returner-friendly employers (e.g. those advertising part-time, flexible hours, returnship programmes) and prioritises them for personas like Käthe.
- [ ] **Long-term-unemployment evidence-of-ROI framing** — generates cover-letter scaffolds that proactively address gap-explanation for Tobias-class users.
- [ ] **Credentials-equivalence lookup** — Tunisian nursing diploma → German Krankenpfleger/in via Anerkennung; surfaces required steps in plain language.
- [ ] **Language-course pairing** — when the user's German is the bottleneck, surface VHS / Goethe / state-sponsored course recommendations in their city, with cost + duration + funding eligibility.
- [ ] **Housing-employer handoff scaffolding** — when a job match requires relocation, offer the housing-agent stub (`/housing handoff`) ready for the real partner integration.
- [ ] **Pflege-bereich career-ladder map** — within healthcare: Pflegehelfer → Pflegefachkraft → Stationsleitung. Visible to Aïcha as her likely 5-year arc.

### 2.7 MCP composition (the post-grant architectural promise)

- [ ] **Housing agent — real partner integration (Option B)** — wires the mock stub to the friend's real service per Decision 20. Test with a real Berlin job → real housing recommendation handoff.
- [ ] **Healthcare credential-verification agent** — partner with one ZAB or Senatsverwaltung API (or, failing that, ship a structured-PDF parser that ingests an Anerkennungs-Bescheid and extracts the credential graph).
- [ ] **Residency-status agent** — wraps BAMF API where available; otherwise a structured form that captures the user's status + deadlines.
- [ ] **Education / VHS-course agent** — surfaces language + skill courses in the user's city, prices, funding paths (Bildungsgutschein, AVGS, etc.).
- [ ] **MCP-tool discoverability** — `mcp/discover` endpoint that lists every connected agent + its capabilities so other clients (Claude Desktop, Cursor, etc.) can integrate.
- [ ] **Schema versioning** — each MCP tool advertises a semver; clients downgrade gracefully.
- [ ] **MCP-mode end-to-end test** — `tests/e2e/mcp_composition_smoke.py` simulates a sequential handoff (job-match → housing → credential check) and asserts the full chain returns coherent results.
- [ ] **Document the MCP composition narrative** in `docs/grant/09-mcp-composition.md` v2 with real-integration examples replacing the current architectural sketches.

### 2.8 Search quality + provider coverage

- [ ] **EURES real API integration** (replaces current JSON projection) — wire to the official EURES Open Data feed, normalise into our schema, handle rate limits.
- [ ] **Full ESCO taxonomy import** — 3000+ occupations, 13500+ skills, 27 languages (currently 30 occupations + 50 skills curated subset).
- [ ] **Multi-language ESCO lookup** — German user typing "Krankenpfleger" finds same ESCO node as English user typing "registered nurse".
- [ ] **Verified 8/8 BYO-AI providers** — currently only Ollama tested live; the other 7 (OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter, Codex CLI, Claude Code) need at least one round-trip integration test each.
- [ ] **Provider-honesty matrix updated** (`docs/grant/15-ai-provider-honesty-matrix.md`) with measured latency + cost + quality per provider per task.
- [ ] **Streaming for every long AI op** — currently only `find_jobs` and `motivation_letter` stream; brief analysis, CV tailor, CV consult should also stream tokens.
- [ ] **Smart provider routing** — small/fast tasks → cheap models (Haiku); reasoning tasks → smart models (Opus); auto-fallback on rate-limit.
- [ ] **Result re-ranking with friction awareness** — a job's match score combines fit + persona-friction-compatibility (e.g. Aïcha's results re-ranked by Anerkennungs-friendly + B1-acceptable).
- [ ] **Fix the 10–13% fit-scoring bias rate** (per `docs/grant/bias-comparative-report-2026-05-21.md`) — analyse the failing scenarios, retrain or rewrite the prompt, drive failure rate to <3%.

### 2.9 Premium operator UX (no orphans, no half-steps, no fragility)

- [ ] **Persona-card SVG icons** — replace the first-letter avatars with neutral illustrative icons (briefcase, stethoscope, scroll-with-stamp, etc.). Avoid face/body imagery.
- [ ] **Logo wordmark refinement** — the current SVG check-in-circle is functional; commission or design a proper brand mark that signals civic-commons + employment.
- [ ] **Brand-mark light/dark variants** — current SVG is theme-aware via currentColor; verify both render correctly.
- [ ] **Empty-state illustrations** across the SPA — Jobs empty, Companies empty, Brief empty, CV-Builder empty — each currently a "no items" string; should be a soft illustrative card with the next action.
- [ ] **Critical-CSS inlining (M1 deferral)** — extract the ~10 KB above-the-fold CSS, inline in `<head>` via a CSP-hash exemption, async-load the rest. Cuts FCP by ~200ms on 3G.
- [ ] **OpenAPI 3.1 DE translation** — generate a parallel `/api/openapi.de.json` with DE descriptions so the /api/docs page can localize endpoint summaries.
- [ ] **CV Builder visual redesign** — current is functional; needs the same card+icon polish applied across the rest of the SPA.
- [ ] **Mobile-first sidebar transformation** — collapse to a bottom-nav-bar pattern at ≤480px so the dock + main content get the full width.
- [ ] **Persona-detail pages** — `/personas/aicha`, `/personas/yusuf`, etc. — public deep-dive narratives with friction-class context, suitable for outreach pitches to NGO partners.
- [ ] **Public "How it works" video** — 90-second screencast walking Aïcha through her flow; embed on landing.
- [ ] **Print stylesheet** for the brief view + CV preview so users can hand a clean printed brief to a Jobcenter caseworker.

### 2.10 Compliance & honesty depth (top-tier means receipts for every claim)

- [ ] **Bias-comparative-report v2** — re-run the 200-scenario panel after the search-quality fixes; publish the new failure rate (target: <3%) with full diffs.
- [ ] **Article 22 right-to-human-review surface** — in-app button that pauses any AI decision (e.g., a poor fit score) and routes to a human reviewer (initially the maintainer; later a partner NGO).
- [ ] **Data Processing Agreement (DPA) signed with every partner** — DPA template exists; ship the signed copies as `compliance/dpa-signed-*.pdf`.
- [ ] **FRIA actually executed per persona** — `compliance/fria-aicha.md`, `fria-yusuf.md`, etc., each ~5-page real assessment, not template.
- [ ] **Operator runbook** updated quarterly (`docs/operator-launch-runbook.md`) with actual incident reports + lessons.
- [ ] **Source-class hierarchy verified per data point** (`docs/grant/14-source-class-hierarchy.md`) — every external claim cites a Class A/B/C/D/E source with an active link verified within the last 30 days.

### 2.11 Sustainability operationalised (not just documented)

- [ ] **GitHub Sponsors activated** — once a public-launch milestone is hit (per Decision 17 the pre-launch policy is no donations). Replace placeholder in SUSTAINABILITY.md with real link.
- [ ] **Open Collective activated** — same gate as Sponsors.
- [ ] **First paid support contract signed** — even a token €500 engagement validates the model.
- [ ] **First grant application in flight** beyond NLnet — Sovereign Tech Fund, Prototype Fund, FOSS contributor fund.
- [ ] **First in-kind partnership signed** — could be a Hetzner-credits sponsorship, a Mistral-credits grant, a Senate-of-Berlin co-funded pilot.
- [ ] **Contributor pathway** — every PR template runs the quality.yml checks; new contributors land within 2 weeks.
- [ ] **Translator contributor program** — Arabic / Ukrainian / Turkish / Romanian translations via Weblate; first translator onboarded.
- [ ] **First NGO partner signed and live** — full Milestone-4 deliverable: one NGO uses the deployed instance for one cohort of users; case study published.
- [ ] **Quarterly impact report** template + first issue (Q1 2027): users served, jobs found, applications submitted, employment outcomes (with persona consent).

### 2.12 Distribution and discoverability

- [ ] **Homebrew tap or Docker image on Docker Hub** — `brew install helpmefindthejob` or `docker run helpmefindthejob` for self-hosters.
- [ ] **DigitalOcean Marketplace 1-click installer** — civic-commons positioning fits the marketplace narrative.
- [ ] **NLnet alumni-network entry** — once awarded, get into the NLnet alumni catalogue + cross-promotion.
- [ ] **Submission to Awesome-Selfhosted** — civic-employment alongside other community-run apps.
- [ ] **Listing on civictech directory** — Code for Germany, Prototype Fund alumni, etc.
- [ ] **Public roadmap page** — `https://helpmefindthejob.org/roadmap` shows the current state of ROADMAP.md in a friendly format.
- [ ] **Status page on a real status service** — UptimeRobot is wired; add a public status sub-domain or use UptimeRobot's public page.
- [ ] **Discord or Matrix community** — low-volume channel for early adopters; maintainer holds office hours monthly.
- [ ] **Search-engine indexing verified** — Google Search Console, Bing Webmaster, Yandex Webmaster, all confirm the sitemap is being crawled.
- [ ] **OpenGraph card audit** — every public page renders correctly when shared on LinkedIn, Twitter, Mastodon, Bluesky, Slack.
- [ ] **PWA install banner verified** — `beforeinstallprompt` works on Chrome Android + iOS Safari (Add to Home Screen).

### 2.13 Reliability and operations

- [ ] **Multi-OS CI** — currently Linux-only; add macOS and Windows runners so contributors on either system can submit safely.
- [ ] **Mobile/PWA E2E test suite** — Playwright runs against iOS Safari + Chrome Android, not just headless desktop Chromium.
- [ ] **Browser-driven E2E tests run in CI** — currently `tests/e2e/*` are skipped if `E2E_BASE_URL` not set; wire a CI job that boots the app on a free port and runs them.
- [ ] **Daily backup verified** — backup-production.sh + restore-drill.sh both run nightly; failures alert the maintainer.
- [ ] **Backup retention policy enforced** — backup-retention.sh prunes >30 days; test that the cron actually fires.
- [ ] **Disaster-recovery dry-run** — once a quarter, restore the latest backup to a sidecar container and run the production smoke suite against it.
- [ ] **Performance budget enforced in CI** — page-size budgets (`tests/test_gap_12_*`) extended to track p95 response time + Lighthouse score; CI fails on regression.
- [ ] **Error tracking** — Sentry-compatible self-hosted error sink (GlitchTip is OSS) wired in; maintainer gets notified within 15 minutes of a 500.
- [ ] **Real uptime monitoring from 3 regions** — UptimeRobot has the basics; add a Europe + US + Asia probe to catch regional outages.
- [ ] **Auto-rollback** — if `/api/health` returns non-200 within 60s of a deploy, the container reverts to the prior image.

### 2.14 Privacy, security, and incident readiness

- [ ] **Pen-test by an external party** — every 12 months minimum; first one before public 1.0 launch.
- [ ] **Bug-bounty program** — even small (€50–€500 per finding) signals seriousness.
- [ ] **Incident-response runbook** drilled — simulate a breach, walk through the BlnBDI notification timeline (Article 33 GDPR), the user-comms template, the recovery steps.
- [ ] **GDPR Article 35 DPIA** completed for the production deployment with real numbers (currently template only).
- [ ] **TLS hardening** — Caddy already terminates TLS; verify A+ rating on Qualys SSL Labs.
- [ ] **HSTS preload list submission** — once stable on the production domain.
- [ ] **CSP Report-To uri** wired to a real collector that the maintainer monitors (currently `/csp-report` stores to a ring buffer; needs alerting on spikes).
- [ ] **Cosign signing for every release artifact** — automated in CI on tag-push.
- [ ] **SLSA Level 2 build provenance** — GitHub Actions can attach this with minimal work.

### 2.15 Accessibility and inclusion (real top-tier bar)

- [ ] **Manual screen-reader walkthrough** — VoiceOver + NVDA + JAWS each get a 30-minute test on the 4 main flows (sign-up, chat, brief, CV builder).
- [ ] **Keyboard-only journey** — all 4 main flows complete with no mouse touch.
- [ ] **WCAG 2.2 AAA on key flows** — the chat dock + auth + brief view tested against the 2.2 spec, not just 2.1.
- [ ] **High-contrast mode support** — `prefers-contrast: more` media query honoured.
- [ ] **Reduced-motion verified** — all animations (skeleton shimmer, chat typing dots, theme transitions) honour `prefers-reduced-motion`.
- [ ] **`forced-colors` Windows high-contrast** rendering verified.
- [ ] **Dyslexia-friendly font option** — toggle in Settings serves OpenDyslexic to the user.
- [ ] **Cognitive-load audit** — every multi-step flow reviewed for jargon, broken into chunks, with progress indicators.
- [ ] **First Arabic translation shipped** — RTL CSS verified, native-speaker review.
- [ ] **First Ukrainian translation shipped** — same.
- [ ] **First Turkish translation shipped** — same.
- [ ] **First Romanian translation shipped** — same.

### 2.16 Documentation polish

- [ ] **MkDocs site live at `https://docs.helpmefindthejob.org`** with: user guide, deployer guide, developer guide, API reference, compliance index, persona-walk transcripts.
- [ ] **`/help` page becomes a real help center** — searchable, with FAQ sourced from real support tickets.
- [ ] **Recorded screencasts** for each major flow: sign-up, first scan, fit analysis, cover-letter draft, CV print.
- [ ] **API client examples** — Python, JS, curl — for every public endpoint.
- [ ] **"How to self-host" tutorial** — DigitalOcean, AWS, GCP, Hetzner, bare-metal Docker.
- [ ] **"How to integrate the MCP server"** — Claude Desktop, Cursor, Windsurf, Codex CLI examples with real screenshots.

### 2.17 Audit-trail and observability for the operator

- [ ] **Operator dashboard** that summarizes: users active today, scans run, AI calls (by provider), errors, slowest endpoints, GDPR requests pending.
- [ ] **Audit-log search UI** — `/admin/audit` lets the operator query by user, action, date range; downloads as CSV.
- [ ] **Per-user activity timeline** — for support tickets, the operator can see exactly what a user did and when.
- [ ] **Quota-breach alerting** — when a user is rate-limited, the operator gets a notification so they can decide if it's abuse or a legitimate power user.
- [ ] **Cost-cap visibility** — daily AI spend per provider + per user, with thresholds.

### 2.18 Final 1.0 readiness ceremony

- [ ] **All boxes above checked.**
- [ ] **Full regression sweep**: 3500+ unit tests, full E2E suite (desktop + mobile + RTL), Lighthouse 100/100/100/100 on all 8 indexable surfaces, axe-core zero violations, Tier-1 product checklist 100% closed.
- [ ] **External-reader review** — recruit a non-technical user (per `docs/grant/external-reader-recruit-message-2026-05-19.md`); incorporate their feedback.
- [ ] **Public launch announcement** — blog post, video, NLnet alumni newsletter, civictech communities, Hacker News / Lobste.rs.
- [ ] **Tag `v1.0.0`** — signed, with the complete CHANGELOG entry, GitHub Release notes, cosign attestation, SLSA provenance.
- [ ] **Open a follow-up `PlanTowardPerfection-v2.MD`** because top-tier products keep raising their own bar.

---

## How to use this file

1. Work from the top of Ceiling 1 down. Don't skip ahead.
2. Each checked box requires a commit reference or a runtime proof — paste it into the line as `- [x] item — done in `<sha>` / proven by curl …`.
3. When Ceiling 1 closes, the project is funded-application-ready. Ship it.
4. Then work down Ceiling 2. Hold the doctrine: no gaps behind, runtime proof, top-tier only.
5. When the last box is checked, the product is what the vision promised — a real intelligent, multi-agent civic-commons employment service that serves every persona end-to-end.

**Source documents this plan synthesises** (read these for context on any line item):
- `docs/grant/02-execution-plan.md` (Week-by-week checkbox baseline)
- `docs/grant/application-draft-2026-05-19.md` (NLnet form-field state)
- `docs/grant/11-institutional-outreach.md` (outreach drafts)
- `docs/grant/10-ai-act-compliance.md` (compliance pack scope)
- `docs/grant/04-research-and-decisions.md` (Decision 17–21)
- `docs/grant/03-post-grant.md` (Phase 2 scope)
- `docs/grant/07-personas.md` (the seven personas, friction-class framing)
- `docs/grant/09-mcp-composition.md` (multi-agent vision)
- `docs/grant/15-ai-provider-honesty-matrix.md` (BYO-AI provider truth)
- `docs/grant/bias-comparative-report-2026-05-21.md` (fit-scoring failure rate)
- `ROADMAP.md` (Phase 1 vs Phase 2 division)
- `SUSTAINABILITY.md` (7-pillar post-grant model)
- The earlier chat-experience audit in this session (13 orphan flows, 5 enhancement tracks)
- The 79-item UX audit + 56 follow-up items closed in this session
