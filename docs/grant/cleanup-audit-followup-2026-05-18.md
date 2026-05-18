<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 DirectJob Scout contributors -->

# Cleanup audit follow-up — adversarial review of commit 8ae169f

**Date**: 2026-05-18.
**Scope**: commit `8ae169f` only ("cleanup: remove advisory-introduced false dependencies and re-anchor §3.4 to existing infrastructure"). Five files changed.
**Mode**: adversarial — try to break the slice, not defend it. Time-boxed 90 min.
**Status**: this report is the maintainer-facing audit deliverable. It is **not committed** to git (per the maintainer's instruction). The fix commit that follows is separate from this report.

---

## 1. Runtime-proof gap closure for test/lint claims

### Result — finding, not no-finding

| Pass | Command | Outcome |
|---|---|---|
| 1.1 | `python3 -m unittest discover -v 2>&1 \| tail -20` | `Ran 0 tests in 0.000s` — **OK with zero tests collected** |
| 1.2 | `ruff check 2>&1 \| tail -5; echo exit=$?` | `All checks passed!` / `exit=0` |
| 1.3 | `ruff format --check 2>&1 \| tail -5; echo exit=$?` | `148 files already formatted` / `exit=0` |
| 1.4 | `mypy --config-file pyproject.toml company_discovery/audit_log.py company_discovery/crypto_kit.py mcp_server.py 2>&1 \| tail -5; echo exit=$?` | `Success: no issues found in 3 source files` / `exit=0` |
| 1.5 | `codespell --config .codespellrc 2>&1 \| tail -5; echo exit=$?` | clean / `exit=0` |

**Finding for 1.1**: the bare `python3 -m unittest discover -v` collects **zero tests** from repo root because Python's unittest discovery walks the current directory (no `test_*.py` files at root) and the tests live under `tests/`. The "994 tests green" claim in cleanup commit 8ae169f is real **only** under the explicit `-s tests` invocation:

```
$ python3 -m unittest discover -s tests -v 2>&1 | tail -8
----------------------------------------------------------------------
Ran 994 tests in 21.166s
OK (skipped=2)
sys:1: ResourceWarning: unclosed file <_io.TextIOWrapper name=22 encoding='UTF-8'>
[...3 more ResourceWarnings...]
exit=0
```

**Gap**: the cleanup commit's claim was correct in spirit (994 green) but the bare `unittest discover` command does not reproduce the figure. The lint claims (1.2–1.5) all reproduce cleanly.

**Recommendation**: the project's `.github/workflows/test.yml` already uses `python -m unittest discover -s tests` so CI is unaffected. The cleanup commit's claim wording should have said "994 tests on `tests/`" rather than "the bare `discover`." This is a documentation precision issue, not a regression.

---

## 2. Concern 2 — Week 2 DoD line 309 inconsistency with Decision 20

### Result — finding confirmed

`docs/grant/02-execution-plan.md` line 309:

```
- Reference integration with housing agent (Option B preferred, Option A fallback acceptable) — shipped in `examples/`
```

This directly contradicts **Decision 20** (2026-05-18) which reversed the §2.5 default: Option A (mock stub) is the default; Option B (real friend integration) is only on explicit collaborator confirmation; self-built (Option C / D) deferred to Phase 2.

The §2.5 body at lines 246–262 has the correct **Decision 20 guardrail** ("Per Decision 20 […], the maintainer does not self-build a Phase 1 housing agent regardless of friend response; default is Option A (mock stub), upgrade to Option B only on explicit collaborator confirmation"). The Week 2 DoD bullet at line 309 was missed — it predates Decision 20 and was not updated by the consolidation-followup commit (`68ab6bb`) that aligned downstream artifacts with Decision 20 + 21.

### DoD-bullet sweep — Weeks 1–4

I re-read every DoD section (`grep "^### Week .* Definition of Done"`):

- **Week 1 DoD** (lines 164–175): no stale-decision references. One adjacent concern: line 173 says `Production-deployment alignment closed — mitigated by Decision 17, no public deployment exists`, which is consistent with Decision 17 (private deployment for one tester) — but see Pass 7 finding A below for an interaction with the §3.4 re-anchor framing.
- **Week 2 DoD** (line 309): **stale** — the only finding.
- **Week 3 DoD** (lines 395–404): no stale-decision references. The "Public demo deployed at stable URL with pre-seeded persona-panel content" bullet is generic (does not name a count); does not need a five→seven update.
- **Week 4 DoD** (lines 474–482): no stale-decision references.

### Fix action

The follow-up commit (described in §8 of this report) rewrites line 309 to match the §2.5 body framing.

---

## 3. Persona-list 5→7 sweep across the workspace

### Method

`grep -rnE "panel of five|five-persona panel|five personas|five most-acute|Aïcha, Yusuf, Olga, Mahmoud, Maria"` across `docs/`, `compliance/`, `*.md` at repo root.

### Findings

| File:Line | Current text | Verdict | Reason |
|---|---|---|---|
| `next-steps-2026-05-18.md:28` | "seven demo accounts (Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias)" | **Correct** | Explicit seven |
| `docs/releases/v0.1.0.md:29` | "Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias" | **Correct** | Explicit seven |
| `docs/grant/07-personas.md:6, 23, 120` | "the most acute use case (five personas)" / "five most-acute-use-case personas" / "Käthe, Tobias, Aïcha, Yusuf, Olga, Mahmoud, Maria" | **Correct as-is** | Decision 21 framing: five-most-acute + two-wider |
| **`docs/grant/06-glossary.md:78`** | "**Persona panel** — The set of fictional users (Aïcha, Yusuf, Olga, Mahmoud, Maria) used in proposal narrative, demos, and documentation." | **STALE** | Glossary entry lists only five; needs to reflect seven per Decision 21 |
| `docs/grant/01-project-brief.md:155` | "panel of seven (five most-acute migrant + two wider friction-class per Decision 21)" | **Correct** | Already reflects seven |
| `docs/grant/00-START-HERE.md:18, 56` | seven-persona references | **Correct** | |
| `docs/grant/02-execution-plan.md:357` (§3.4) | "seven-persona panel (Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias)" | **Correct** | Cleanup commit 8ae169f updated this |
| `docs/grant/13-lessons-learned.md:97` | "five most-acute migrant personas, two wider-friction-class personas" | **Correct as-is** | Rule 7 framing |
| `docs/grant/04-research-and-decisions.md:172, 186, 381` | Decision 5 + 2026-05-18 note + Decision 21 body | **Correct** | Append-only log; the note expands the panel to seven |
| **`docs/grant/12-application-package.md:107`** (Milestone 4 deliverable) | "persona-panel pre-seeded examples (Aïcha, Yusuf, Olga, Mahmoud, Maria)" | **STALE** | NLnet application text — high priority. Missing Käthe + Tobias. |
| `compliance/data-governance.md:87` | "seven-persona panel (Aïcha, Yusuf, Olga, Mahmoud, Maria, Käthe, Tobias)" | **Correct** | |
| `compliance/accuracy-and-bias-testing.md:18, 52` | "five most-acute-use-case personas (Aïcha, Yusuf, Olga, Mahmoud, Maria)" alongside "two wider-friction-class personas (Käthe, Tobias)" | **Correct as-is** | Decision 21 framing |
| `compliance/deployer-operating-manual.md:26` | "(Aïcha, Yusuf, Olga, Mahmoud, Maria)" inside the section addressing MBE / IQ-Netzwerk / JMD deployers | **Correct as-is** | Section scoped to migrant-services deployers whose mandate is the migrant subset |
| `docs/grant/cleanup-audit-2026-05-18.md:65, 75` | Audit-trail describing the §3.4 staleness that the cleanup fixed | **Correct** | Audit-trail context |
| `CLAUDE.md:49, 63` | Seven-persona references | **Correct** | |
| `README.md:132` | "The five most-acute-use-case personas" (table header) | **Correct as-is** | Heading for the migrant-five sub-table; the panel structure shows the wider two in the adjacent sub-table |
| `CHANGELOG.md:115` | "Käthe (...) and Tobias (...) added alongside the existing five (Aïcha, Yusuf, Olga, Mahmoud, Maria)" | **Correct as-is** | Changelog entry describing the Decision-21 expansion; naming the existing-five is appropriate descriptive context |

### Two stale entries to fix in the follow-up commit

1. `docs/grant/06-glossary.md:78` — glossary entry.
2. `docs/grant/12-application-package.md:107` — NLnet Milestone 4 deliverable text (public-facing).

---

## 4. Anti-defensive sweep of the cleanup audit itself

Re-graded the three specific callouts the maintainer flagged. **No findings** — all three pass adversarial re-read.

### 4.1 `docs/production-deployment.md:135` (UptimeRobot / Better Stack / Pingdom)

> "External uptime + TLS monitoring is intentionally provider-neutral. We recommend hitting `https://YOUR_DOMAIN/api/health` every 5 minutes from UptimeRobot, Better Stack, Pingdom, or the operator's own probe."

**Verdict**: genuinely provider-neutral. Lists four options, one of which is "operator's own probe" (no external service). The text explicitly says "intentionally provider-neutral." The prior advisory prompt's promotion of UptimeRobot to a commitment was the advisory failure, not the documentation. **Acceptable as-is** under adversarial re-read.

### 4.2 `scripts/pre-deploy-snapshot.sh:133` (B2 / R2 / S3 / DO Spaces enumeration)

> "Off-host backup (optional). Operator sets these env vars to enable upload to any S3-compatible target (DigitalOcean Spaces, Backblaze B2, Cloudflare R2, AWS S3). Uses awscli inside the container so we don't add a dependency to the host."

**Verdict**: genuinely multi-vendor at both the documentation and implementation layers. The script uses `aws s3 cp` against `DIRECTJOB_BACKUP_S3_ENDPOINT` (overridable to any S3-compatible endpoint). The four examples reinforce the multi-vendor reality rather than commit to one. **Acceptable as-is.**

The one technical commitment that *is* made: **S3 API compatibility as the protocol**. That is a standard-interface commitment, not a vendor commitment, and is acceptable.

### 4.3 `docs/threat-model.md:74` (Cloudflare / ALB DDoS-mitigation residual)

> "Per-IP login rate limit | Medium — distributed attacks unhandled, document Cloudflare/ALB integration"

**Verdict**: documented **residual risk** with two example integrations the deployer would consider. Not a project commitment to either. The framing — `Residual: Medium — distributed attacks unhandled` — is honest about the gap. **Acceptable as-is.**

---

## 5. Open R12 — technical reality check

### Result — Phase 1 gap confirmed; R12 is real, not advisory speculation

`compliance/accuracy-and-bias-testing.md` is the methodology document. Read end-to-end, the methodology calls for three concrete artifacts:

1. Synthetic persona fixtures at `tests/fixtures/personas/` (§2.1 — "committed to … and re-used across test runs to make changes detectable")
2. A `tests/test_bias_methodology.py` test that runs the methodology and asserts divergence-from-tolerance below threshold (§3)
3. A first dated run report at `docs/grant/bias-testing-<date>.md` (§2.5)

**None of these three artifacts exist today.** §8 ("Current results") explicitly states: "the methodology is documented but not yet executed at full scale. […] The AI-component bias-testing methodology is scheduled for execution as part of Week-3 partner-NGO pilot collaboration; results land in `docs/grant/bias-testing-<date>.md` reports."

With the partner-NGO pilot now post-grant (per the maintainer's earlier ROADMAP framing: "first NGO pilot deployment" in 2026 Q4), the v0.1.0 release leaves the bias-testing methodology documented-but-unexecuted, with the transparency notice's promised "preliminary results due Week 3 of the grant sprint" unfulfilled.

R12 (synthetic-cohort interim run using the seven personas) **IS the gap-closing deliverable** — not advisory speculation. It would produce all three missing artifacts above, plus the first executed bias-testing report.

**Maintainer call**: do this in Phase 1 (closes the gap before NLnet submission; ~6–10 hours of agent work) or accept the unfulfilled-claim risk and defer to Phase 2.

---

## 6. Prerequisite status for next-steps Steps 2 and 3

### 6.1 Step 2 demo password

**Result**: zero references to a chosen demo password anywhere in the repo (`grep -nE "demoaccess|demo password|demo-password|demo_password"` returns empty). Confirmed open — one-line maintainer input required.

**Reminder**: do nothing autonomously. The seed script in Step 2 takes the password as a CLI arg or env var; the maintainer supplies it at run time.

### 6.2 Step 3 GitHub Pages status

**Result**: `gh api /repos/maksodf/directjob-scout/pages` returns:

```
{"message":"Not Found","documentation_url":"https://docs.github.com/rest/pages/pages#get-a-apiname-pages-site","status":"404"}
gh: Not Found (HTTP 404)
```

**Pages is OFF.** Maintainer action required: *Settings → Pages → Source: GitHub Actions* (~30 sec). Without this flip, the mkdocs-material workflow has no deploy target.

---

## 7. No-gaps-behind sweep — what was noticed but not surfaced?

The cleanup commit + the audit it produced were over-confident. The adversarial sweep surfaces five gaps I noticed during the cleanup but did not surface in either the commit message or the audit report:

### Finding A — Public vs private deployment ambiguity in §3.4 re-anchor

The cleanup commit's §3.4 re-anchor says: "§3.4 uses the existing deployment infrastructure the maintainer already operates." Per Decision 17, the existing deployment is **private** (only the maintainer's partner has access; no public traffic). For a public demo, this requires clarification: does the maintainer want to (a) repurpose the existing private deployment as the public demo by routing a new subdomain at it, (b) stand up a parallel public instance using the same scripts, or (c) keep them separate? This is a real maintainer-input question that the re-anchor smuggles past.

### Finding B — Week 1 DoD vs §3.4 re-anchor surface tension

`docs/grant/02-execution-plan.md:173` says `Production-deployment alignment closed — mitigated by Decision 17, no public deployment exists`. The §3.4 re-anchor at line 354 says `the maintainer has existing deployment infrastructure already running`. Both can be true (existing infrastructure runs the private deployment; public does not yet exist), but the surface tension is unstated. A future contributor reading both passages out-of-order would be confused.

### Finding C — `12-application-package.md:107` is the NLnet-reviewer-facing text

The Milestone 4 deliverable in the NLnet application text still lists only the five most-acute personas. This is the document a reviewer reads in depth; the friction-class evidence (Käthe + Tobias) should appear here per Decision 21. I missed this in the original cleanup audit (which scoped to §3.4 + risks + Open R8). Same family of concern — Decision 21 sweep — but a higher-priority artifact.

### Finding D — R12 categorisation was over-cautious

The next-steps report at `docs/grant/next-steps-2026-05-18.md` flagged R12 as "possible-advisory-artifact that needs the maintainer's call before becoming a real open question." Pass 5 of this audit confirms R12 is a **real Phase 1 gap** (the methodology doc has documented-but-unexecuted scope). The cautious framing was correct in spirit (Rule 5 — don't pre-decide) but reads as if R12 might be speculative; it isn't.

### Finding E — Original-audit "no findings" was over-confident

The cleanup audit at `docs/grant/cleanup-audit-2026-05-18.md` was scoped narrowly to the maintainer's seven enumerated categories. The maintainer's adversarial follow-up surfaced two additional categories the original audit should have caught:

- Persona-list staleness in `06-glossary.md` and `12-application-package.md` (Decision 21 sweep)
- Stale DoD bullet at `02-execution-plan.md:309` (Decision 20 sweep)

Per global CLAUDE.md "no gaps behind": both of these were sitting in the workspace at audit time and were not surfaced. The original audit's "zero artifacts created" framing was correct for the false-dependency-introduction concern but missed the broader Decision-21-and-20 sweep that was already overdue.

---

## 8. Follow-up commit (proposed)

The maintainer's instruction was to land **one** follow-up commit (not amending `8ae169f`) covering:

1. Rewrite Week 2 DoD line 309 to match the §2.5 body framing.
2. Reconcile any other stale DoD bullets surfaced in the sweep — **none in Weeks 1, 3, 4**.
3. Update `04-research-and-decisions.md` Open R8: status `ANSWERED 2026-05-18 — placeholder convention retained`; remove the "pending one-line maintainer answer" line.

Additionally, this audit's Pass 3 surfaces two persona-list stales that fall under the same Decision-21-sweep family:

4. `docs/grant/06-glossary.md:78` — glossary entry naming only the original five.
5. `docs/grant/12-application-package.md:107` — Milestone 4 NLnet-reviewer-facing text.

Both are documentation-only, single-line fixes consistent with the §3.4 cleanup direction. Folding them into the same commit is in the spirit of "no gaps behind" — leaving them for a later sweep risks them being missed when the application package is finalised in Week 4.

**Findings A, B (deployment public-vs-private) and D, E (advisory-discipline reflection)** are **not** in the follow-up commit. They are surfaced to the maintainer for sign-off before any further action.

---

## Verdict

**Audit found gaps — escalating to maintainer.**

The cleanup commit `8ae169f` itself is sound (zero false-dependency code or scripts shipped). The adversarial sweep nevertheless surfaces:

- Two persona-list stales the original audit missed (`06-glossary.md:78`, `12-application-package.md:107`).
- The Week 2 DoD bullet (line 309) the maintainer pre-flagged as Concern 2.
- A real Phase 1 gap behind Open R12 that the next-steps file under-graded.
- A public-vs-private deployment ambiguity in the §3.4 re-anchor framing.
- A Week 1 DoD vs §3.4 framing tension.

The first three are addressable in the follow-up commit described in §8. The last two require maintainer sign-off before any further re-anchoring.
