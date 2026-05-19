# Contributing to Helpmefindthejob

Thank you for considering a contribution. Helpmefindthejob is an open
civic-employment commons — a small focused codebase that aims to put
specialist HR and bureaucratic-navigation knowledge directly into the
hands of anyone facing structural labor-market friction in Europe, with
migrants and EU-mobile workers as the most acute use case (see
Decision 21 in `docs/grant/04-research-and-decisions.md`). Contributors
are welcome from any background, and especially from people with direct
lived experience of the problems the project tries to address.

This document covers: how to set up a development environment, how to
propose changes, the commit and pull-request conventions we follow, and
the contributor-license-agreement step that every non-trivial contribution
goes through. If any of the steps below are unclear, open an issue and a
maintainer will help.

For social conventions please read [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
For how to report a security issue please read
[`SECURITY.md`](SECURITY.md). For where to ask general questions please
read [`SUPPORT.md`](SUPPORT.md).

---

## Project state

The project is in early alpha. The main branch is intended to stay
buildable but may include unfinished work. The fresh-clone install
(`pip install -r requirements.txt && pip install -r requirements-dev.txt`)
is verified on every push by the `fresh-clone-install` CI workflow
(`.github/workflows/fresh-clone-install.yml`) on `python:3.11-slim`
and `python:3.12-slim` containers. The historical
`cryptography` / `cffi` build issue is closed (see Week 3 task 3.1
in `docs/grant/02-execution-plan.md`). If you still hit setup
friction on a specific platform, please open an issue — fixing
onboarding paper-cuts is itself a valuable contribution.

## Before You Start

1. Read this file in full.
2. Read [`cla.md`](cla.md). Every non-trivial contribution requires a
   one-line CLA assent on the pull request (see [Contributor License
   Agreement](#contributor-license-agreement) below).
3. Check the [issue
   tracker](https://github.com/maksodf/helpmefindthejob/issues) to see
   whether someone is already working on the same thing.
4. For larger changes (anything beyond a typo, a one-line fix, or a clear
   bug), open an issue first so we can agree on the approach before you
   spend hours.

## Development Setup

Requirements: Python 3.11+ and (optionally but recommended) Docker.

```bash
git clone https://github.com/maksodf/helpmefindthejob.git
cd helpmefindthejob

# 1. Install runtime dependencies (cryptography is pinned with broad
#    wheel coverage — no rust or C build toolchain needed on most
#    platforms).
pip install -r requirements.txt

# 2. Install development dependencies (pre-commit and friends; ruff /
#    mypy / coverage land alongside Week 3 task 3.2).
pip install -r requirements-dev.txt

# 3. Activate the git pre-commit hook.
pre-commit install

# 4. Run the app locally.
python3 app.py
# Open http://127.0.0.1:8765
```

The pre-commit hook currently runs the SPDX-header check on every Python
file you stage. It is intentionally minimal during the Week 1 phase of
the grant sprint; lint, format, and type-check hooks (ruff, black, mypy)
will be added in Week 3 (`docs/grant/02-execution-plan.md` §3.2).

### Nix workflow (optional, reproducible)

The pip-based setup above is the supported default. If you already use
Nix (or want a byte-identical dev environment for AI Act build
provenance), a `flake.nix` at the repo root provides the same setup
pinned against a specific `nixpkgs` commit:

```bash
nix develop       # bootstrap .venv from pinned Python; subsequent
                  # entries are instant
nix run           # launch the app via the flake (same env)
nix flake check   # verify the flake's contract
```

First-build wall-clock is ~50 seconds (Determinate Nix 3.20 on
aarch64-darwin); subsequent entries are instant thanks to the
`.venv/.deps_installed` sentinel. Full reproducibility commands +
hybrid Nix-native + pip-managed rationale live in
[`docs/deployment-recipe.md`](docs/deployment-recipe.md) §12.

### Running Tests

```bash
python3 -m unittest discover -s tests -v
```

The suite passes natively on Python 3.11 + 3.12 across macOS, Linux,
and minimal slim Docker containers — the `fresh-clone-install` CI
workflow (`.github/workflows/fresh-clone-install.yml`) verifies this
on every push. If your specific environment still has issues with
cryptography wheels (extremely rare with the pinning landed in §3.1),
run inside Docker as a fallback:

```bash
docker compose up --build
docker compose exec app python3 -m unittest discover -s tests -v
```

The Playwright browser-flow tests have a one-time setup:

```bash
pip install playwright
playwright install chromium
./scripts/run-e2e.sh
```

## Code Style

- **Language**: Python 3.11+ with type hints. New code should be type-
  annotated; modernising legacy code is welcome.
- **Formatting**: PEP 8 and the de-facto Black style (88-character line
  length). Until the Week 3 CI hooks land, `python3 -m black --check .`
  passes for new code in your PR is enough.
- **Imports**: stdlib first, third-party second, local third, each block
  alphabetised.
- **Module size**: prefer cohesive modules; if a file passes roughly 500
  lines, consider whether it should split.
- **i18n**: any user-facing string must be added to `static/i18n/en.json`
  and `static/i18n/de.json`. Tests under `tests/` verify key parity
  between locales; do not skip that. The full contributor pathway for
  adding a new locale, the German-bureaucratic-conventions preservation
  rule, and the translation-review process live in
  [`docs/translating.md`](docs/translating.md).
- **SPDX header**: every new Python file starts with the SPDX header
  from [`.license-header-template.txt`](.license-header-template.txt).
  `scripts/add_spdx_headers.py` can apply it for you; the pre-commit
  hook will reject staged files that miss it.
- **Comments**: write a comment only where the WHY is non-obvious. Do
  not narrate WHAT the code does. Do not reference task numbers,
  reviewers, or transient context; those belong in the PR description.

## Commit Message Convention

Use conventional commits with a clear scope:

```
<type>(<scope>): <imperative subject under 70 chars>

<optional body that explains the why, the trade-offs, and any non-
obvious consequence. Wrap at 72 columns. Reference issues or planning
docs by relative path, e.g. docs/grant/02-execution-plan.md §1.2.>
```

Types we use:

- `feat`     — a new feature visible to end users or deployers
- `fix`      — a bug fix
- `refactor` — a code rearrangement that does not change behavior
- `docs`     — documentation only
- `test`     — adding or fixing tests
- `chore`    — tooling, build, infra
- `ci`       — CI configuration
- `i18n`     — translation-bundle changes
- `compliance` — EU AI Act compliance pack changes (Week 2+)
- `mcp`      — MCP server / tool catalogue changes
- `governance` — CODEOWNERS, AUTHORS, ACKNOWLEDGMENTS, CODE_OF_CONDUCT,
  SUPPORT, SECURITY, TRADEMARK, CLA, this file
- `planning` — `docs/grant/` strategic documents

Subjects are imperative ("Add", not "Added"). Avoid trailing periods. The
body is optional but encouraged for anything non-trivial.

## Translations

Helpmefindthejob ships English + German today and grows by locale as
native-speaker contributors join. If you'd like to add a locale —
Arabic, Ukrainian, Turkish, Romanian are the post-grant targets per
[Decision 6](docs/grant/04-research-and-decisions.md) — see
[`docs/translating.md`](docs/translating.md) for the full pathway:

- Locale-bundle structure (`static/i18n/<locale>.json`)
- The four-step contributor flow (copy `en.json` → translate →
  parity-test → PR)
- The **German-bureaucratic-conventions preservation rule**
  (terms like `Anerkennung`, `§16d`, `TVöD`, `Wiedereinstieg`,
  `Ausbildung` stay German in every locale because they have
  legal-specific meaning that doesn't translate)
- Translation-review process (native-speaker review per Decision 18
  consent-first authorship; credit in `AUTHORS.md`)

The CI parity test (`tests/test_phase0_i18n_parity.py`) gates
locale-bundle PRs.

## Pull Request Process

1. Fork the repository and create a feature branch from `main`.
   Name pattern: `<type>/<short-kebab-case-description>`, e.g.
   `feat/esco-skill-lookup` or `docs/contributing-clarification`.
2. Make your changes. Keep the PR focused — one logical change per PR.
3. Add or update tests where behavior changes. New AI-prompt or
   AI-routing code needs at least one test that pins the prompt or the
   routing decision.
4. Update relevant documentation (README, ARCHITECTURE.md, MCP catalogue,
   CHANGELOG.md once that exists in Week 3).
5. Ensure `python3 -m unittest discover -s tests` (the bare
   `discover` from repo root collects zero tests because the project's
   tests live under `tests/`) and, if you ran them, the Playwright
   suite pass. CI runs the same on push.
6. Open a pull request using the
   [pull-request template](.github/PULL_REQUEST_TEMPLATE.md). Fill every
   section.
7. In your first non-trivial PR, add the CLA assent line (see below).
8. A maintainer reviews. We aim to respond within 7 days; in practice
   during the grant sprint (May–August 2026) response times may be
   longer. Please be patient.

## Contributor License Agreement

Helpmefindthejob uses an Apache-style Individual Contributor License
Agreement. The full text is in [`cla.md`](cla.md); it has not been
amended with any novel terms beyond the Apache ICLA template.

**For every non-trivial pull request, please add this comment exactly:**

> I have read and agree to the Helpmefindthejob Individual Contributor
> License Agreement, version 1.0, dated 2026-05-17.

State your full legal name and the email address you commit from. A
maintainer records the assent in [`AUTHORS.md`](AUTHORS.md) (or, for
contributors who prefer not to appear publicly, in an internal register)
before merging.

Trivial contributions — typo fixes, documentation clarifications,
single-line bug fixes — may be merged without prior CLA assent at
maintainer discretion. Anything beyond trivial needs assent on file.

Operational note: a self-service CLA-signing tool (CLA Assistant or
equivalent) will be wired up in Week 3 of the grant sprint or shortly
after. Until then the PR-comment mechanism above is the canonical assent
process.

## Reporting Bugs and Requesting Features

Use the [issue templates](.github/ISSUE_TEMPLATE/) — bug, feature, or
security. Security issues should follow the private process documented
in [`SECURITY.md`](SECURITY.md), not the public issue tracker.

## Code of Conduct

By participating in this project, you agree to abide by the
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). The Code of Conduct is the
Contributor Covenant 2.1.

## Recognition

Contributors are credited in [`AUTHORS.md`](AUTHORS.md). Significant
contributors of code, translation, design, or institutional support are
acknowledged in [`ACKNOWLEDGMENTS.md`](ACKNOWLEDGMENTS.md). We do not
distinguish between "core" and "external" contributors in attribution —
credit is granted by the contribution.
