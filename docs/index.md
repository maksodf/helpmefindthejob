<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 DirectJob Scout contributors -->

# DirectJob Scout

**Open-source EU-wide civic employment commons.** An MCP-composable
copilot for users facing structural labor-market friction in Europe.

---

## Who we build for

> **Aïcha** is a Tunisian-trained registered nurse working through
> §16d Anerkennung in Berlin — clinically capable, German at B1
> climbing toward B2, CV shaped for a Tunisian recruiter. The hospital
> ward she would slot into is short-staffed; the friction is
> bureaucratic, linguistic, and CV-formatting — not capability.

> **Käthe** is a German nurse returning to clinical work after twelve
> years out for childcare — legally certified, German-native, but
> everything about practising nursing in Germany has changed since
> 2013 and her old CV reads wrong for 2026 conventions. The same
> Berlin clinic is hiring the role both Aïcha and Käthe could fill.

The project's architecture is **friction-driven, not demographic-
driven**. Migrants and EU-mobile workers are the most acute use case
and the primary narrative anchor; the same friction shapes affect
career changers, returning workers, the long-term unemployed, and
returning expats. DirectJob Scout captures specialist HR and
bureaucratic-navigation knowledge into modular, standards-anchored
MCP tools and puts that knowledge directly into the hands of anyone
navigating the European labour market.

See the [seven-persona panel](https://github.com/maksodf/directjob-scout/blob/main/docs/grant/07-personas.md)
for the full friction-class breakdown (five most-acute migrant +
two wider-friction-class).

---

## What's here

- **[Quickstart](https://github.com/maksodf/directjob-scout#quickstart)** —
  install, run, and try the journey state machine locally.
- **[MCP API](mcp-server.md)** — the five composition-oriented tools
  the MCP server exposes today (catalogue v0.2.0).
- **[Deployment recipe](deployment-recipe.md)** + **[production
  deployment](production-deployment.md)** — the generic parallel-public-
  instance recipe + the maintainer's private deployment baseline.
- **[ESCO + EURES integration](esco-integration.md)** — the curated
  skills reference dataset and EURES projection contract.
- **[Architecture](https://github.com/maksodf/directjob-scout/blob/main/ARCHITECTURE.md)** —
  Mermaid system diagram + component map (read first if you're going to
  contribute code).
- **[Standards](https://github.com/maksodf/directjob-scout/blob/main/STANDARDS.md)** —
  the standards we hold ourselves to (Apache 2.0, ESCO, MCP, WCAG 2.2,
  EU AI Act).
- **[Compliance pack](https://github.com/maksodf/directjob-scout/tree/main/compliance)** —
  EU AI Act artefacts (transparency notice, risk management plan, FRIA
  template, technical documentation, accuracy + bias testing
  methodology, audit-log schema, data governance, human-oversight
  guide, deployer operating manual, EU database registration template).
- **[Roadmap](https://github.com/maksodf/directjob-scout/blob/main/ROADMAP.md)**
  and **[Changelog](https://github.com/maksodf/directjob-scout/blob/main/CHANGELOG.md)** —
  what's shipped, what's next.

---

## License + governance

Apache 2.0 with a Contributor License Agreement. Programme of
**The Commons Conservancy** (Dutch stichting co-founded by NLnet).
Read **[CONTRIBUTING.md](https://github.com/maksodf/directjob-scout/blob/main/CONTRIBUTING.md)**
before opening a pull request.

---

## Stability + honesty

This is **alpha software**. We hold ourselves to the project's
"demand runtime proof on every closeout" standard — every feature
gets a live runtime probe before it's declared done. We are honest
about what's executed (the bias-testing surface, the deployment
recipe, the persona seed script) and what's deferred (the four
remaining methodology scenario classes, the §3.6 accessibility audit,
the translator contributor pathway). See the
[grant workspace](https://github.com/maksodf/directjob-scout/tree/main/docs/grant)
for the maintained planning record.

---

## Contact

- Issues + discussion: [GitHub](https://github.com/maksodf/directjob-scout/issues)
- Security: [SECURITY.md](https://github.com/maksodf/directjob-scout/blob/main/SECURITY.md)
- Code of conduct: [CODE_OF_CONDUCT.md](https://github.com/maksodf/directjob-scout/blob/main/CODE_OF_CONDUCT.md)
