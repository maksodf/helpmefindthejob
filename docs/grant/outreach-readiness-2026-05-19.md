<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 DirectJob Scout contributors -->

# Outreach send-gate readiness — 2026-05-19

This document is the §4.0 send-gate audit per
[Decision 19](04-research-and-decisions.md) (defer all
institutional outreach to Week 4 start, gated on visible
Phase 1 deliverables). Each criterion in the gate is checked
against the actual state of the repo at slice time.

## Send-gate criterion (Decision 19)

The three outreach emails ([01-AWO-FIM-CW](outreach-drafts/01-awo-fim-cw.md),
[02-RINWA-Berlin](outreach-drafts/02-rinwa-berlin.md),
[03-TU-Berlin-Career-Service](outreach-drafts/03-tu-berlin-career-service.md))
do NOT go out until every line below shows ✅ at the moment of
sending. Today (2026-05-19) most lines are green; one is amber
pending the working-branch-to-main merge.

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | README opens with persona vignette per Decision 21 | ✅ | `README.md:13-21` — Aïcha (most-acute migrant) + Käthe (wider-friction-class) vignettes |
| 2 | Demo deployment recipe documented | ✅ | [`docs/deployment-recipe.md`](deployment-recipe.md) — full parallel-public-instance recipe with Docker compose, Caddy TLS, backup procedure |
| 3 | Docs site contract shipped | ✅ (code) / 🟡 (live deploy) | [`mkdocs.yml`](../../mkdocs.yml) + [`.github/workflows/docs-publish.yml`](../../.github/workflows/docs-publish.yml). GH Pages flipped on by maintainer (per the §3.6 polish-trio closeout note). The actual deploy fires on push to `main`; **on the working branch the docs URL referenced in the outreach emails will 404 until merge-to-main**. See "Recommendation: send AFTER merge" below. |
| 4 | EU AI Act compliance pack shipped | ✅ | [`compliance/`](../../compliance/) — 10 files covering transparency notice, risk-management plan, FRIA template, technical documentation, accuracy + bias testing, audit-log schema, data governance, human-oversight guide, deployer operating manual, EU database registration template |
| 5 | Green CI badges visible | ✅ | `README.md:4-11` — Tests / Quality / MCP integration / Fresh-clone install / OpenSSF Scorecard / Codecov / MCP version / Docs (the Docs badge will be green once Pages serves the workflow output) |
| 6 | §4.2 differentiation moves (cosign + SBOM + RFC 9116) | ✅ | [`docs/releases/v0.1.0-signing.md`](releases/v0.1.0-signing.md) + [`docs/releases/v0.1.0-sbom.json`](releases/v0.1.0-sbom.json) + [`static/.well-known/security.txt`](../../static/.well-known/security.txt). All three attached to GitHub Release v0.1.0. |
| 7 | §3.6 accessibility audit (three-pass) | ✅ | [`ACCESSIBILITY.md`](../../ACCESSIBILITY.md) — 30 violations closed across 22 audited surfaces (unauthenticated + authenticated + dynamic + light-mode + compliance pages). All three audit passes documented. |
| 8 | §3.8 Nix flake reproducible build | ✅ | [`flake.nix`](../../flake.nix) + [`flake.lock`](../../flake.lock) — pins nixos-25.05 nixpkgs commit; `nix flake check` green; `nix develop --command python3 -m unittest discover -s tests` runs 1029 OK / 12 skipped |
| 9 | §4.1 SUSTAINABILITY.md | ✅ | [`SUSTAINABILITY.md`](../../SUSTAINABILITY.md) — multi-grant arc, Conservancy wrapper, optional support contracts carefully framed, honest pre-launch state |
| 10 | Test suite green | ✅ | 1020 tests OK / 4 skipped (the 4 skips are opt-in bias-methodology + opt-in admin tests; not a regression) |
| 11 | Lint clean (ruff + format + mypy strict + codespell + residue gate) | ✅ | All exits 0 at slice time |
| 12 | `mkdocs build --strict` green | ✅ | Green at slice time |

## Recommendation: send AFTER branch-to-main merge

The outreach drafts reference (or will, after personalisation by
the maintainer) the docs site URL
`https://maksodf.github.io/directjob-scout/`. That URL becomes live
once the docs-publish workflow runs against `main` (the workflow's
own trigger). On the working branch `claude/project-analysis-bpHCo`
the docs build runs and uploads the artefact, but Pages serves from
the main-branch deploy.

**Send sequence**:

1. Maintainer reviews this slice + the §4.4 application draft.
2. Maintainer merges the working branch into `main`.
3. The docs-publish workflow fires automatically; verify the live
   docs site at `https://maksodf.github.io/directjob-scout/` returns
   200 + the Aïcha + Käthe vignette landing.
4. Maintainer personalises the three outreach drafts (fills in
   `[Maintainer]` name, `[Kontakt-Email]`, `[Studienprogramm]`,
   `[Matrikelnummer]` per Decision 18 consent-first identity-bearing
   fields).
5. Maintainer sends the three emails.
6. Update [`11-institutional-outreach.md`](11-institutional-outreach.md)
   with send dates + reply/outcome notes (a tracker entry per
   contact).

Sending **before** merge is also tolerable — the docs URL in the
email body resolves on the maintainer's first `git push origin main`
after send. But the Pages-deploy delay can be 1–2 minutes, and a
contact who clicks the link in the first minute would land on a
404, making the email look amateur. **Recommended order: merge
first, verify URL, then send.**

## Maintainer-side fills retained (Decision 18 consent-first)

Per [Decision 18](04-research-and-decisions.md) (consent-first
authorship for identity-bearing fields), the agent does NOT fill in
the maintainer's name, email, or student-programme details. The
following placeholders in the three drafts are intentionally
preserved for maintainer fill-in:

- `[Maintainer]` — preferred display name (all three drafts)
- `[Kontakt-Email]` — direct reply-to email (all three drafts)
- `[Link zum Projekt-README / Demo]` — single project URL (all
  three drafts; recommended: `https://maksodf.github.io/directjob-scout/`
  once Pages serves the main-branch deploy)
- `[Studienprogramm]` + `[Matrikelnummer]` — TU Berlin-only fields
  (draft 03)

All four are flagged inline in each draft's "Send-fill checklist"
footer.

## Send-day script for the maintainer

```bash
# 1. Pull the latest main + verify Pages is live.
git checkout main
git pull
curl -sI https://maksodf.github.io/directjob-scout/ | head -1
# Expected: HTTP/2 200

# 2. Open each draft, fill the four placeholders, save outside the
#    repo (or in a maintainer-private branch — do NOT commit
#    identity-bearing fills to the public repo per Decision 18).
$EDITOR docs/grant/outreach-drafts/01-awo-fim-cw.md
$EDITOR docs/grant/outreach-drafts/02-rinwa-berlin.md
$EDITOR docs/grant/outreach-drafts/03-tu-berlin-career-service.md

# 3. Re-verify each contact email + role on the day of sending.
#    The drafts list the canonical URL for each.

# 4. Send via your usual mail client (the drafts are German-only;
#    keep the German wording — the audience is German-domain).

# 5. Update the outreach tracker.
$EDITOR docs/grant/11-institutional-outreach.md
# Add: send date, send-from email, subject, body version (commit
# hash that personalisation came from).
```

## Honesty note

This document is a send-gate audit, NOT a commitment to send. The
maintainer chooses when to send + whether to send each draft
individually. Per [Decision 19](04-research-and-decisions.md), the
gate exists because pre-Phase-1-readiness outreach would have been
premature; the gate satisfied today does not obligate sending
today.
