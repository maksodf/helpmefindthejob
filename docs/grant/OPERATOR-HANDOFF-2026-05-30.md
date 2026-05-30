<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Operator handoff — NLnet submission readiness (2026-05-30)

This note is the single place that lists **what an autonomous agent could not
close and exactly what only you (the operator) can do** to finish the NLnet NGI
Zero Commons Fund submission. It is the honest boundary between "verified and
closed" (everything else in the repo at this point) and "genuine operator
action required" (below).

It was produced at the end of the ceiling-sprint closeout that re-audited the
application draft (M1), bug-hunted the product code (M2), proved the live demo
(M3), resolved the compliance posture (M4), and ran the final gate (M5). What
was closed in that sprint is summarised at the bottom so you do not re-do it.

---

## A. Operator-owned items (only you can close these)

### A1. Verify the exact NLnet call deadline, eligibility, and submission act
The agent cannot authoritatively read the live NLnet call page. **Before
submitting**, confirm on <https://nlnet.nl/commonsfund/> (or the current NGI
Zero Commons Fund call page):
- the exact deadline for the cycle you are targeting (the working assumption has
  been "early June 2026" — verify the real date);
- eligibility for the project as scoped (open-source, EU-relevant, civic);
- the submission mechanism (the web form fields, attachment limits, the abstract
  word cap). Cross-check the 22 fields prepared in
  [`application-draft-2026-05-19.md`](application-draft-2026-05-19.md) against
  the live form in case NLnet changed it.

### A2. Fill the maintainer-identity slots in the application draft
The application draft and parts of the compliance pack contain
`[Maintainer fills …]` / `[TBD …]` / `[Deployer …]` placeholders that hold
information only you can supply (legal name / contact / institutional
affiliation / signatures / deployment-specific FRIA + DPIA + human-oversight
appointee details). Locate them with:

```bash
git grep -nE '\[Maintainer fills?|\[TBD|\[Deployer' -- 'docs/grant/*.md' 'compliance/*.md'
```

The FRIA / DPIA / oversight `[TBD: deployer to fill]` slots are **deployment
specific by design** — they are filled by each institutional deployer, not by
the project. For the submission you only need the *maintainer-side* slots; the
deployer-side ones stay as template placeholders (that is correct and expected).

### A3. Ship path: merge → place the signed v0.80.0 tag → submit
Current working branch: `claude/ceiling-sprint`. The work is committed there,
nothing is pushed.

1. Merge `claude/ceiling-sprint` → `main` (fast-forward safe).
2. **Place the signed `v0.80.0` tag at the merged HEAD.**

   ⚠️ **Important (found during M5):** the existing `v0.80.0` tag points at
   `ed9c266` (2026-05-24) and is **80 commits behind HEAD**. The release notes
   [`docs/releases/v0.80.0.md`](../releases/v0.80.0.md) describe the tag as "the
   submission-state tag … what NLnet reviewers see," and the test-count claims
   across the repo (README, compliance pack, application draft) now say
   **3,342 tests** — the count of the *current* tree, not the 2026-05-24 tree
   (which had 3,301). So the signed `v0.80.0` tag must be (re)placed at the
   final merge commit, or the `git clone --branch v0.80.0 … # Expected: Ran 3342
   tests` verification command in the release notes will show 3,301 instead.
   - If you are comfortable moving the lightweight tag: `git tag -f -s v0.80.0`
     at the merge commit, then force-push the tag.
   - If you prefer never to move a published tag: cut the signed tag as the next
     SemVer release (e.g. `v0.81.0`) and update the version strings in
     `docs/releases/`, `CHANGELOG.md`, and `app.py:APP_VERSION` accordingly.
     The simpler, docs-consistent path is to place `v0.80.0` at the submission
     commit (the existing tag is a pre-submission placeholder).
3. Submit the application; archive the submitted text per A6.

### A4. Run the demo-login smoke against the real deployed host
The demo chat→journey flow is proven in-process and on a local boot (M3), and
the consent/export audit events are proven over a local HTTP server (M4). Only
you can confirm the **production** host. After the demo deployment is online:

```bash
python3 scripts/demo-login-smoke.py \
    --base-url https://<your-demo-host> \
    --email-domain <demo-domain> \
    --password '<the demo password you seeded with>'
```

All persona logins must pass before the demo is reviewer-ready. (TLS is always
verified — the password is transmitted on login.)

### A5. External / institutional items
- **Commons Conservancy application** — institutional, operator-submitted
  (status pending OR admitted is acceptable to state in the form).
- **Letter of support (PDF)** — collected from an NGO / TU Berlin contact.
- **Outside-reader cold read** of the proposal for clarity (one human pass).
- **Demo screenshot / GIF** of the chat journey (execution-plan task, deferred
  to coincide with the public demo deployment).

### A6. Post-submission
Archive the submitted application verbatim in
`docs/grant/submitted-application-<date>.md`, then proceed on normal SemVer
cadence from the v0.80.0 anchor (next release `v0.81.0`) per
[`03-post-grant.md`](03-post-grant.md).

---

## B. Compliance posture — your decision on what to submit

M4 returned two record-keeping mechanisms to genuinely "implemented" (proven
over HTTP, hash-chain verified, regression-tested):
- `consent_event` — emitted on AI-provider consent grant/revoke.
- `export_event` — emitted on every full personal-data export (user + admin).

The genuinely-larger AI-Act mechanisms remain **honestly documented as planned**
in the new "Runtime mechanism status" matrix in
[`compliance/INDEX.md`](../../compliance/INDEX.md):
- `override_event` / advisor-review intercept workflow (Article 14) — the
  oversight *queue* is code-wired and review-only; the edit/reject workflow is
  not built;
- automated `audit_log_self` extraction (Article 86) — manual DPO process;
- `AUDIT_RETENTION_DAYS` auto-prune (Article 12) — deployer-operated;
- a per-decision "explain this score" endpoint (Article 86) — planned.

**Decision for you:** submitting as-is is consistent with NGI0's norm of being
honest about alpha state — the compliance pack now states each mechanism's true
status in one place. Building the larger items first is a Phase-2 scope, not a
submission blocker, and would push the timeline. Recommendation: submit with the
documented posture; the matrix is the artefact a reviewer needs.

---

## C. What was verified and closed in this sprint (do not re-do)

- **M1 — application draft re-audited from scratch.** All 22 NLnet fields
  re-checked against current reality; budget sums to €37,000 across 6
  milestones; the only drift found (stale test count) is fixed in M5.
- **M2 — product-code bug hunt.** ~two dozen real defects fixed at root cause,
  each with a regression test (GDPR erasure completeness, Postgres AEAD crash,
  SSO account-takeover, 2FA slot bypass, quota TOCTOU, MCP DoS hardening, CV
  self-XSS, bootstrap race, aggregator isolation, journey input, streaming
  dispatch — see `CHANGELOG.md` `[Unreleased]` Fixed + Security).
- **M3 — live demo proven end-to-end.** The chat→journey flow advances
  GREET→discover→cv_check with coherent replies, proven both in-process and on a
  booted HTTP instance; pinned by `tests/test_chat_journey_path.py`.
- **M4 — compliance posture resolved.** consent/export audit events built +
  proven over HTTP; planned items consolidated into the status matrix.
- **M5 — final gate.** `ruff check .` clean; full suite **Ran 3342 tests in
  90.727s, OK (skipped=26)**; every live test-count reference reconciled to
  3,342; all compliance-pack file/method/endpoint references verified to
  resolve; CHANGELOG updated.
- **M5 — persona-panel residue cleared.** The panic-round bug-hunt found a
  Spine-B persona residue cluster the earlier doc-pass missed. Most important:
  the **public landing page** (`static/index.html` + `en/de.json`) described
  Maria as a "Spanish architect on EU Blue Card", Yusuf as a "Syrian … §16d"
  engineer, Mahmoud as "IT-support", and Olga as "office work" — all reconciled
  to the canonical panel (Maria = Romanian nurse / EU citizen; Yusuf = Turkish
  automotive engineer / EU Blue Card; Mahmoud = trades / Handwerk; Olga = senior
  tech / §24). The production `friction_classifier.py` SCORED_PATTERNS for Maria
  (Spain/Spanish/Bartender) and Tobias (banker) and their dependent tests, plus
  five `tests/e2e/persona_*_smoke.py` docstrings and the quarterly-impact
  template, were all reconciled to canonical and re-verified green.

## D. Known residue requiring a scoped follow-up (not a submission blocker)

One persona inconsistency is **documented rather than fixed**, because fixing it
correctly is feature work, not a label edit:

- **The `mesh/` demo models Olga as a Ukrainian general-medicine MD in Hamburg
  with a family**, wired to a `hamburg_paragraph_24_ukraine` housing cohort and
  three `tests/test_mesh_agents.py` cases. Canonical Olga is a Ukrainian **tech**
  worker (senior frontend / DevOps) in **Leipzig**. Reconciling the mesh demo
  would mean rewriting its medical-Anerkennung flow and building a Leipzig
  housing-cohort data fixture (the housing data is city-specific) — a scoped task
  with its own tests, deliberately left out of the closeout to avoid rushing a
  coupled production-demo change. It does not touch the submission surface (the
  mesh demo is internal; the public landing page and the canonical fixtures at
  `company_discovery/persona_fixtures.py` are correct). Schedule as Phase-2.

Nothing above is pushed; everything is on `claude/ceiling-sprint`. The repo is
submission-ready except for the operator-owned items in section A.
