<!--
Thank you for contributing to Helpmefindthejob.

Before you submit, please read CONTRIBUTING.md and cla.md if you have
not already. Anything beyond a trivial fix requires a CLA assent line
in the PR comments (template provided below).
-->

## What changed

<!-- One-paragraph summary of the change in plain language. What does
the user, deployer, or contributor see differently after this PR? -->

## Why

<!-- Motivation. If this fixes a bug, describe the bug. If this adds a
capability, explain why it belongs in Helpmefindthejob (ideally with a
nod to the cost-saving doctrine in docs/grant/08-cost-saving-doctrine.md:
does this reduce institutional cost while improving end-user outcomes?). -->

## Linked issue

<!-- Use "Closes #NNN" or "Refs #NNN". If no issue exists, briefly
explain why this PR can stand on its own. -->

## How to verify

<!-- Concrete steps a reviewer can run to verify the change. Include
any new tests added, the commands to run them, and any manual flow
that should be exercised. -->

## Checklist

- [ ] I have read [CONTRIBUTING.md](../CONTRIBUTING.md) and
      [cla.md](../cla.md).
- [ ] Non-trivial PR: I have added the CLA assent line in a comment on
      this PR (see CONTRIBUTING.md for the exact wording). *Trivial PRs
      may skip this at maintainer discretion.*
- [ ] New Python files include the SPDX header from
      [`.license-header-template.txt`](../.license-header-template.txt).
      `python3 scripts/check_spdx_headers.py` passes locally.
- [ ] Tests pass locally: `python3 -m unittest discover -s tests`
      (the bare `discover` invocation collects zero tests because the
      project's tests live under `tests/`). If you hit any install or
      runtime friction, see `CONTRIBUTING.md` "Development Setup" for
      the supported install path.
- [ ] User-facing strings exist in both `static/i18n/en.json` and
      `static/i18n/de.json`. (i18n parity tests will fail otherwise.)
- [ ] Documentation updated where behavior or interface changed
      (README, ARCHITECTURE.md, MCP catalogue, CHANGELOG once it
      exists, locale bundles).
- [ ] Commit messages follow the convention in CONTRIBUTING.md.

## Notes for the reviewer

<!-- Anything else the reviewer should know: trade-offs you considered,
alternatives you tried and rejected, areas you would like a closer look
at, open follow-up work. -->
