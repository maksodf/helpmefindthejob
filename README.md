# DirectJob Scout

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![tests](https://github.com/maksodf/directjob-scout/actions/workflows/test.yml/badge.svg?branch=claude/project-analysis-bpHCo)](https://github.com/maksodf/directjob-scout/actions/workflows/test.yml)
[![quality](https://github.com/maksodf/directjob-scout/actions/workflows/quality.yml/badge.svg?branch=claude/project-analysis-bpHCo)](https://github.com/maksodf/directjob-scout/actions/workflows/quality.yml)
[![MCP integration](https://github.com/maksodf/directjob-scout/actions/workflows/mcp-integration.yml/badge.svg?branch=claude/project-analysis-bpHCo)](https://github.com/maksodf/directjob-scout/actions/workflows/mcp-integration.yml)
[![Fresh-clone install](https://github.com/maksodf/directjob-scout/actions/workflows/fresh-clone-install.yml/badge.svg?branch=claude/project-analysis-bpHCo)](https://github.com/maksodf/directjob-scout/actions/workflows/fresh-clone-install.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/maksodf/directjob-scout/badge)](https://securityscorecards.dev/viewer/?uri=github.com/maksodf/directjob-scout)
[![codecov](https://codecov.io/gh/maksodf/directjob-scout/branch/claude%2Fproject-analysis-bpHCo/graph/badge.svg)](https://codecov.io/gh/maksodf/directjob-scout)
[![Release](https://img.shields.io/badge/release-pre--v0.1.0-lightgrey.svg)](#)
[![Languages](https://img.shields.io/badge/languages-EN%20%2B%20DE-informational.svg)](static/i18n/)
[![MCP](https://img.shields.io/badge/MCP-2024--11--05-blueviolet.svg)](https://modelcontextprotocol.io)
[![Docs](https://github.com/maksodf/directjob-scout/actions/workflows/docs-publish.yml/badge.svg?branch=claude/project-analysis-bpHCo)](https://maksodf.github.io/directjob-scout/)

> Aïcha is a Tunisian-trained registered nurse working through §16d
> Anerkennung in Berlin — clinically capable, German at B1 climbing
> toward B2, CV shaped for a Tunisian recruiter. Käthe is a German
> nurse returning to clinical work after twelve years out for childcare
> — legally certified, German-native, but everything about practising
> nursing in Germany has changed since 2013 and her old CV reads wrong
> for 2026 conventions. The same Berlin clinic is hiring the role both
> of them are qualified for. The bureaucratic stack between either of
> them and that role is not something Google or LinkedIn can navigate
> for them. **DirectJob Scout is the open civic-employment commons
> built so Aïcha and Käthe — and the millions of others facing the same
> structural friction across the European labor market — can navigate
> that stack themselves.**

DirectJob Scout is an **open-source EU-wide civic-employment commons** —
an MCP-composable copilot that captures specialist HR and
bureaucratic-navigation knowledge into modular, standards-anchored tools
and puts it directly into the hands of anyone facing structural friction
between their actual capability and the European labor market's ability
to recognise and connect them to work. Migrants and EU-mobile workers
are the most acute use case (and primary narrative anchor in our
demos); the same architecture serves career changers, workers returning
after extended absence, the long-term unemployed, and others. Germany
is the first reference deployment because that is where the maintainer
is; the architecture is country-neutral.

The project is being prepared as a Programme of **The Commons
Conservancy** (the NLnet-co-founded Dutch stichting whose Programmes
include Redwax, FileSender, eduVPN, and others). License is **Apache 2.0
with a Contributor License Agreement** so that public-sector and
non-profit institutions across the EU can adopt, fork, and self-host
without licence friction. See [`docs/grant/`](docs/grant/) for the full
strategic context.

**Status**: pre-v0.1.0 alpha. Working hosted reference implementation in
private testing; public demo deploys in Week 3 of the grant sprint
(see [Roadmap](#roadmap)). The main branch is intended to stay buildable
but may contain unfinished work. Honest about instability — see
[`CONTRIBUTORS-NOTE.md`](CONTRIBUTORS-NOTE.md) for the project's history
including the deprecated commercial phase.

## What it does

DirectJob Scout combines three discovery rails behind a single chat
interface:

- **Career-page monitoring** of companies the user adds to a watchlist
  (robots.txt-aware, page-bounded, redirect-safe).
- **Live job-aggregator fan-out** across configurable providers
  (Adzuna, Indeed, LinkedIn public listings, federated country-specific
  career pages), with deduplication and source attribution.
- **Bookmarklet captures** for roles seen on third-party sites that the
  scanners do not reach.

Discovered jobs flow into a structured 12-phase journey state machine
(see [`company_discovery/journey.py`](company_discovery/journey.py)) that
gates every AI invocation to a phase and asks for user confirmation
before any write. From there the user can score role-fit, generate a
tailored CV per opening, draft a motivation letter grounded in their CV
facts, and track which CV variant gets replies. Anerkennung,
Beratungsstelle, and Jobcenter context is built into the prompts so the
guidance is actually useful to someone navigating §16d, Blue Card, §24,
subsidiary protection, or Romanian / EU-citizen tracks rather than a
generic English-speaking job market.

## Quickstart

A clean clone should land you at a working local instance in five
minutes.

```bash
git clone https://github.com/maksodf/directjob-scout.git
cd directjob-scout

# Option 1: Python directly. Requires Python 3.11+.
pip install -r requirements.txt
python3 app.py
# Open http://127.0.0.1:8765

# Option 2: Docker.
docker compose up --build
# Open http://127.0.0.1:8765
```

Run the test suite directly on a fresh clone:

```bash
python3 -m unittest discover -s tests
```

The 994-test suite passes natively on Python 3.11 and 3.12 across
macOS, Linux, and the `python:3.11-slim` / `python:3.12-slim` Docker
containers — verified on every push by the `fresh-clone-install`
workflow at `.github/workflows/fresh-clone-install.yml`. Docker is
supported as a deployment target but is no longer required for
testing.

Configuration is environment-variable driven; see
[`.env.example`](.env.example) for the full list. The
[Deployment](#self-hosting) section covers production with Caddy HTTPS.

## The personas

DirectJob Scout's design is anchored by a **panel of seven personas**
split into two groups: five **most-acute-use-case** personas (migrants
and EU-mobile workers facing the densest concentration of friction —
the strongest specific narrative evidence in proposals and demos) and
two **wider-friction-class** personas (non-migrant users facing
structurally similar friction in different forms — their presence
demonstrates the friction-class architectural claim per Decision 21).
The system serves a category of human situations, not a single
demographic. The panel doubles as a forcing function for accessibility,
RTL-language readiness, regulated-profession recognition flows, and EU
vs non-EU work-rights nuances. Real consenting anonymised stories
replace fictional ones over time. See
[`docs/grant/07-personas.md`](docs/grant/07-personas.md) for the full
profiles.

**The five most-acute-use-case personas** (migrants and EU-mobile workers):

| Persona | Origin | Profession | Status | Solves |
|---|---|---|---|---|
| Aïcha | Tunisia | Registered nurse | §16d Anerkennung | Recognition-friendly employer matching + clinical-German CV |
| Yusuf | Turkey | Mechanical engineer | EU Blue Card pending | Post-arrival timeline + cross-city role comparison |
| Olga | Ukraine | Senior frontend dev | §24 protection | English-team / remote tech matching + residence-status explainer |
| Mahmoud | Syria | Trade apprentice | Subsidiärer Schutz | Ausbildung aggregation + Handwerk-format CV |
| Maria | Romania | Care worker | EU citizen | Language-barrier-friendly Pflegedienst matching |

**The two wider-friction-class personas** (non-migrant users with structurally similar friction):

| Persona | Origin | Profession | Status | Solves |
|---|---|---|---|---|
| Käthe | Germany | Registered nurse returning after 12 years out for childcare | German citizen | Wiedereinstieg-programme matching + 2026-format CV for re-entrants |
| Tobias | Germany | Backend developer pivoting commercial → civic-tech | German citizen | Public-sector / TVöD-aware CV reframe + civic-employer landscape |

## Standards we implement

The project is standards-anchored on purpose. Adopters inherit
interoperability and the ability to switch out individual layers
without forking.

- **Apache License 2.0** ([LICENSE](LICENSE)) — broad permissive
  software licence with a Contributor License Agreement
  ([cla.md](cla.md)) modelled on the Apache Individual CLA.
- **Model Context Protocol (MCP)** — composition surface, version
  `2024-11-05`. JSON-RPC over stdio. Public tool catalogue with JSON
  Schemas (full catalogue documentation lands in Week 2). See
  [modelcontextprotocol.io](https://modelcontextprotocol.io).
- **schema.org JobPosting** — canonical structure for job records.
- **ESCO** (European Skills, Competences, Qualifications and
  Occupations) — taxonomy for cross-EU occupation mapping; integrated
  in Week 2.
- **EURES schema** — interoperability with the European Employment
  Services portal; export endpoint in Week 2.
- **WCAG 2.2 AA** — accessibility target. Honest audit and remediation
  plan in [`ACCESSIBILITY.md`](ACCESSIBILITY.md) (lands Week 3).
- **RFC 9116** — `/.well-known/security.txt` for vulnerability
  disclosure (lands with the public demo in Week 3).
- **GDPR alignment** — encrypted profile-at-rest with
  ChaCha20-Poly1305, user-sovereign AI provider choice (BYO-AI
  including Ollama for fully-offline mode), explicit-consent data
  egress, user-export and user-deletion paths.
- **EU AI Act compliance** — designed for high-risk AI under Annex III
  §4. Full compliance pack shipped at
  [`compliance/`](compliance/): risk-management plan, data-governance
  documentation, Annex IV technical documentation, Article 12 audit
  logging (`company_discovery/audit_log.py` emitter integrated into
  MCP and analysis paths), user-facing transparency notice,
  deployer-facing operating manual, human-oversight guide with
  `/api/admin/oversight/queue` admin endpoint (Article 14),
  accuracy-and-bias testing methodology anchored to the seven-persona
  panel (Article 15), pre-fillable templates for EU AI database
  registration (Article 49) and the Fundamental Rights Impact
  Assessment (Article 27). Aligned with the 2 August 2026 enforcement
  date.

## MCP composition

The MCP server in [`mcp_server.py`](mcp_server.py) exposes the project
as composable civic infrastructure. Other open civic agents — housing,
healthcare, residency, education — compose with DirectJob Scout
without forking either project. See
[`docs/grant/09-mcp-composition.md`](docs/grant/09-mcp-composition.md)
for the composition patterns (sequential handoff, profile-shared,
orchestrated) and
[`docs/grant/01-project-brief.md`](docs/grant/01-project-brief.md) §8
for the architectural reasoning.

A reference integration with an open housing agent — proving the
composition claim end-to-end — ships in Week 2 of the grant sprint
under [`examples/`](examples/) (TBD).

## Self-hosting

DirectJob Scout is designed to be deployed by a single NGO, a
Beratungsstelle, a Jobcenter, a university career service, or an
individual at home, on commodity hardware. There is no per-seat licence
fee and no managed cloud lock-in. The reference deployment uses Docker
Compose with Caddy HTTPS:

```bash
cp .env.example .env
# Edit .env: domain, admin email/password, DIRECTJOB_SECRET_KEY,
# DIRECTJOB_PUBLIC_URL, SMTP credentials, AI provider config.
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

Backup, restore, restore-drill, smoke checks, uptime checks, and
TLS-expiry monitoring scripts live in [`scripts/`](scripts/). A `Nix`
flake for reproducible builds lands in Week 3.

For sensitive deployments, the BYO-AI abstraction
([`company_discovery/ai_providers.py`](company_discovery/ai_providers.py))
supports fully-offline operation via Ollama; the chat router falls back
to deterministic templated responses when no provider is configured,
so the user-facing flow still works.

## Hosted by

**Hosted by The Commons Conservancy** *(application pending — Week 2 of
the grant sprint).* Once admission lands, this section is updated with
the Programme page link and any required acknowledgment language.

## Roadmap

A quarterly roadmap with milestones for **2026 Q3 → 2028 Q2** lives at
[`ROADMAP.md`](ROADMAP.md). At a glance:

- **2026 Q3** — grant-sprint completion + first stable release
  (v0.1.0 shipped 2026-05-18). Commons Conservancy application
  submitted; NLnet NGI Zero Commons Fund application submitted by
  end of Week 4.
- **2026 Q4** — Arabic as the third UI language; first NGO pilot
  deployment; WIP reintegration begins (per Decision 16).
- **2027 Q1** — Phase 2 NLnet application; framework extraction
  begins.
- **2027 Q2** — housing-agent integration hardened; healthcare-agent
  scoping starts.
- **2027 Q3** — multi-agent orchestrator scoping.
- **2027 Q4** — multi-agent civic platform first integration.
- **2028 Q1 / Q2** — multi-country localisation (Austria, then
  France + Netherlands).

The full version-by-version history of what shipped is at
[`CHANGELOG.md`](CHANGELOG.md). Long-horizon context (Phases 2–4,
sustainability model) at [`docs/grant/03-post-grant.md`](docs/grant/03-post-grant.md).

## Documentation

- [`ROADMAP.md`](ROADMAP.md) — quarterly milestones 2026 Q3 → 2028 Q2.
- [`SUSTAINABILITY.md`](SUSTAINABILITY.md) — post-grant operational
  model, multi-grant arc, optional support contracts (carefully
  framed), community + donation channels, honest pre-launch state.
- [`CHANGELOG.md`](CHANGELOG.md) — what shipped in each release.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — system diagram and component
  map.
- [`STANDARDS.md`](STANDARDS.md) — every standard the project
  implements.
- [`ACCESSIBILITY.md`](ACCESSIBILITY.md) — WCAG 2.2 Level AA target;
  axe-core CLI 4.11 audit findings + fixes shipped + known gaps with
  remediation plan; reproduction commands.
- [`compliance/`](compliance/) — EU AI Act compliance pack (Articles
  9–15, 27, 49).
- [`docs/grant/`](docs/grant/) — strategic source of truth: project
  brief, execution plan, decisions log, research notes, personas,
  cost-saving doctrine, MCP composition spec, AI Act compliance plan.
- [`docs/mcp-server.md`](docs/mcp-server.md) — public MCP server
  documentation, 13-tool catalogue (v0.2.0).
- [`docs/esco-integration.md`](docs/esco-integration.md) — ESCO + EURES
  integration reference.
- [`docs/releases/`](docs/releases/) — version-controlled release
  notes (`docs/releases/v0.1.0.md` for the current release).
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to contribute.
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) — Contributor Covenant 2.1.
- [`SECURITY.md`](SECURITY.md) — private vulnerability disclosure.
- [`SUPPORT.md`](SUPPORT.md) — where to ask questions.
- [`AUTHORS.md`](AUTHORS.md), [`ACKNOWLEDGMENTS.md`](ACKNOWLEDGMENTS.md) — who built this.
- [`TRADEMARK.md`](TRADEMARK.md) — name and mark usage.
- [`CONTRIBUTORS-NOTE.md`](CONTRIBUTORS-NOTE.md) — honest project history.
- **Documentation site**: lands in Week 3 at `docs.<public-domain>`.
- **Public demo**: lands in Week 3 at `demo.<public-domain>` with the
  seven-persona panel pre-seeded.

## Why this exists

The honest version: every advisor at a Migrationsberatungsstelle, every
caseworker at an Optionskommune, every nurse-recognition coordinator,
every Anerkennung specialist already holds in their head most of what
DirectJob Scout will eventually codify. Their time is rationed. Their
caseload is structurally larger than their capacity. Their advice is
rarely written down in a form a foreign-credentialed worker can act on
alone at 11 p.m. between two shifts. The opportunity is to put that
specialist knowledge into modular, MCP-composable tools — under an
open licence, AI Act compliant by design, hosted by a Dutch stichting
that outlasts any one maintainer — and to evaluate every feature by
whether it reduces institutional cost while improving end-user
outcomes. See
[`docs/grant/08-cost-saving-doctrine.md`](docs/grant/08-cost-saving-doctrine.md)
for the full doctrine.

## Licence

Apache License 2.0 — see [`LICENSE`](LICENSE), [`NOTICE`](NOTICE),
[`TRADEMARK.md`](TRADEMARK.md), and [`cla.md`](cla.md).

Copyright (c) 2026 DirectJob Scout contributors.
