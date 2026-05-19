# Contributors' Note on Repository History

Helpmefindthejob is being prepared as an open-source civic-employment commons in May 2026, ahead of an application to the NLnet NGI Zero Commons Fund. The project was originally developed in private as a commercial-product prototype before its direction was changed to a civic-commons positioning. This note documents that transition honestly so future contributors and reviewers can interpret the git history correctly.

## What changed

The current working tree no longer contains the residue of the original commercial framing. Specifically, the Week 1 sanitisation pass (recorded in `docs/grant/02-execution-plan.md` task 1.4) did the following:

- Replaced every hardcoded reference to the old commercial domain (`<khalo.org>`) with the placeholder domain `helpmefindthejob.com` (an [RFC 2606](https://www.rfc-editor.org/rfc/rfc2606) reserved-for-documentation TLD). The placeholder is unambiguous and signals that the real public domain will be registered before the project moves out of alpha. Where a sensible environment-variable fallback already existed (e.g. `DIRECTJOB_PUBLIC_URL`), the hardcoded fallback string was sanitised but the env-var indirection was kept.
- Replaced internal-tester-name references in code and test comments (one tester's first name appeared in `company_discovery/journey.py` and `tests/test_journey_edge_cases.py`, both as humanising context for two bug-history comments and as a Python identifier `NASSER_COMPLAINT`). The comments now refer to "an early tester" generically; the identifier was renamed to `EARLY_TESTER_COMPLAINT`. The bug-history context is preserved; the personal name is not.
- Pinned the local Docker project name to `helpmefindthejob` in `docker-compose.yml` and `docker-compose.prod.yml` so that the generated image name (`helpmefindthejob:latest`) no longer depends on the developer's local filesystem directory name. The previous name leaked the original local repository directory.
- Relocated all commercial-vision documents (sellable-readiness, operator-launch, marketing-copy, press-kit, launch-day-content, operator-package, operator-starters, operator-final-punchlist) plus two documents containing real personal contact details (`legal-review-brief.md`, `deployment-handoff.md`) into a `private/` directory that is now in `.gitignore`. They remain on the maintainer's local machine but are not part of the public commons project. New private-only documentation lands under `private/` rather than `docs/`.
- Deleted `keepbuildingtill100%tracker.MD` from the repo root in line with Decision 14 in `docs/grant/04-research-and-decisions.md`.

## What was deliberately not changed

The project's **git history is not rewritten**. Older commits — including commit messages and committed file contents at the time of those commits — may still reference legacy commercial framing, the old `<khalo.org>` domain, internal tester names, the original local directory name, and the relocated commercial-vision documents. This is a deliberate choice made on 2026-05-17 (recorded as Decision 12 in `docs/grant/04-research-and-decisions.md`). The reasons:

- **Integrity of signed commits**: rewriting history would invalidate any signed-commit verification and break any existing checkouts or forks.
- **Honest provenance**: NGI0 reviewers and the open-source community can trace exactly when the project changed direction. Pretending the commercial phase never happened would be a more damaging signal than acknowledging it.
- **Tooling cost**: history rewrites in a busy repository are expensive and error-prone; the value-to-risk ratio of doing so for a personal-scale project's early history is poor.

Reviewers and new contributors should treat any pre-2026-05-18 commit as part of the project's early-phase history. Anything in the **current working tree** is authoritative for the civic-commons positioning; anything in **historical commits** is not.

## What this means for new contributors

You do not need to read the pre-grant-sprint commits to contribute. Read `README.md`, `CONTRIBUTING.md`, `docs/grant/01-project-brief.md`, and `docs/grant/02-execution-plan.md`, and you will have the full current-state picture. If a `git log` or `git blame` surfaces a legacy reference, treat it as historical context and do not propagate the legacy framing into new work.

If you discover a residue we missed, please open an issue (or a pull request) and we will sanitise it in the same forward-only way. We do not rewrite history retroactively even for newly-discovered residue.

## 2026-05-19 — project rename (forward-going per Decision 12)

On 2026-05-19 the project was renamed from **DirectJob Scout** to **Helpmefindthejob** ([Decision 22](docs/grant/04-research-and-decisions.md#decision-22-project-rename--directjob-scout--helpmefindthejob)), with the canonical domain at **helpmefindthejob.com**. The rename was applied **forward-going only**, consistent with Decision 12's history-preservation discipline.

What this means for git archaeology:

- Commits dated up to and including the rename commit reference the project as "DirectJob Scout". This is the identity-of-record at the time those commits were authored.
- The `v0.1.0` release (tag, release notes, cryptographic artefacts under `docs/releases/v0.1.0-*`) remains named "DirectJob Scout v0.1.0". The cosign signature was computed over the `directjob-scout-0.1.0.tar.gz` tarball; renaming the artefacts post-sign would break verification.
- `CHANGELOG.md` historical `[0.1.0] — 2026-05-18` entries name "DirectJob Scout" as the identity-of-record at that release.
- `docs/grant/cleanup-audit-2026-05-18*.md` and other dated audit reports preserve the project's pre-rename name as historical fact.

Going forward (any commit dated 2026-05-19 or later), the project is "Helpmefindthejob" and the public canonical URL is `https://helpmefindthejob.com/`. If a `git log` / `git blame` / `git show` surfaces the old name, treat it as the documented identity-of-record at that point in time; do not propagate the old name into new work.

## Acknowledgments

The honest-instability and history-preservation patterns documented here are inspired by the way Tenzu, Redwax, and other NGI0-funded projects publicly acknowledge early-stage state instead of over-polishing it. Pretending to be polished from day one is, in our view, the worse signal to reviewers and to the wider open-source community than naming what is still rough and what has changed.
