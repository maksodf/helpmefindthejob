<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# OpenSSF Scorecard status — 2026-05-19

This page is the project's snapshot of expected Scorecard
behaviour at the time the Week 4 §4.2 slice landed. The actual
public-score-feed at
<https://scorecard.dev/viewer/?uri=github.com/maksodf/helpmefindthejob>
will pick up the improvements documented here on the next
weekly cron run (the `.github/workflows/scorecard.yml` workflow
fires at `32 5 * * 1` and on `push` to `main`).

## Why no live score yet

The Scorecard workflow's trigger is `push` to `main` + weekly
cron. All current sprint work has happened on
`claude/project-analysis-bpHCo`; the workflow has never run
against the published-score-feed-eligible main branch:

```
$ gh run list --workflow=scorecard.yml --limit 3
HTTP 404: workflow scorecard.yml not found on the default branch
```

This is the **expected** state pre-merge. When the working
branch merges to main, the first scheduled or push-triggered
Scorecard run will populate the public score.

## Expected per-check outcomes

| Check | Expected score | Source of evidence |
|---|---|---|
| Pinned-Dependencies | 10/10 | All six workflows SHA-pinned (commits 546f952 + 5be9f47). `grep -nE "uses:.*@v[0-9]" .github/workflows/*.yml` returns 0 lines. |
| Token-Permissions | 10/10 | Every workflow declares top-level `permissions: contents: read`. Job-level escalations (e.g., docs-publish's deploy job has `pages: write` + `id-token: write`) are correctly scoped per-job. |
| Security-Policy | 10/10 | `SECURITY.md` at repo root + RFC 9116 `/.well-known/security.txt` served by the app (this slice). |
| SBOM | 10/10 | `docs/releases/v0.1.0-sbom.json` (CycloneDX 1.6, 91 components) committed AND attached to the v0.1.0 GitHub Release (this slice). |
| Signed-Releases | 10/10 | v0.1.0 source tarball cosign-signed; `v0.1.0-cosign.pub` + `v0.1.0-source.tar.gz.sigstore` committed AND attached to the v0.1.0 release (this slice). |
| Dangerous-Workflow | 10/10 | No `pull_request_target` + no untrusted-input → run patterns. |
| Maintained | 10/10 | Recent commit cadence; 90+ commits over the 4-week sprint. |
| License | 10/10 | Apache 2.0 + LICENSE + NOTICE + SPDX headers on every source file. |
| CII-Best-Practices | n/a | Optional badge — not pursued in Phase 1. |
| Code-Review | depends | Single-maintainer project today; the Scorecard rule rewards 2-reviewer PRs. Will improve when collaborators land in Phase 2. |
| CI-Tests | 10/10 | `.github/workflows/test.yml` + `quality.yml` + `mcp-integration.yml` + `fresh-clone-install.yml` + `docs-publish.yml` run on every push. |
| Branch-Protection | depends | Maintainer-side action: GitHub Settings → Branches → require PR + require status checks on `main`. Surfaced as the only Scorecard finding the agent cannot apply directly. |
| Contributors | depends | Reflects unique contributor count; single-maintainer today. |
| Vulnerabilities | depends | Reflects OSV reports against the project's pinned deps; pip-audit in `quality.yml` provides an early-warning equivalent. |

## Maintainer-action items

The only Scorecard finding the agent cannot apply directly is
**Branch-Protection**:

- GitHub repository → Settings → Branches → "Add branch
  protection rule" for `main` with at least:
  - Require pull request before merging
  - Require status checks to pass (select `tests`, `quality`,
    `mcp-integration`, `fresh-clone-install`, `docs-publish`)
  - Require linear history
  - Optionally: require signed commits + restrict pushes to
    administrators

Once that's done, Scorecard's Branch-Protection check moves to
10/10 in the next weekly run.

## Verification

After the working branch merges to main + the first Scorecard
run completes:

```bash
gh api /repos/maksodf/helpmefindthejob/actions/workflows/scorecard.yml/runs \
  --jq '.workflow_runs[0] | {created_at, conclusion}'
curl -sL "https://api.securityscorecards.dev/projects/github.com/maksodf/helpmefindthejob" \
  | python3 -m json.tool
```

The expected outputs are:
- A `success` Scorecard workflow run dated within the past week
- A populated `/projects/...` JSON with `score` near or at 10
  (depending on Branch-Protection landing)
