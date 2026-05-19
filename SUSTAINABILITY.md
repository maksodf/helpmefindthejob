<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Sustainability

## Stated commitment

Helpmefindthejob is sustainable because it is **open-source under
Apache 2.0**, **hosted by The Commons Conservancy** (admission
pending), and **self-hostable by anyone on commodity hardware**.
Sustainability of this project does **not** depend on a single
funder, a single contributor, a single hosting choice, or a
commercial-revenue stream. It depends on the durability of the
three structures listed above and on the public benefit the
commons delivers to institutions and individuals navigating the
European labour market.

This document is the project's honest record of how that
sustainability is structured today and how it grows from here.

---

## Post-grant operational model

| Pillar | How Helpmefindthejob is set up |
|---|---|
| **Open-source core** | Apache 2.0 + Contributor License Agreement ([Decision 1](docs/grant/04-research-and-decisions.md#decision-1-license--apache-20--contributor-license-agreement)). No closed components. Every line of code that ships to a user is in the public repository. |
| **Institutional wrapper** | Programme of [The Commons Conservancy](https://commonsconservancy.org/), a Dutch stichting co-founded by NLnet. Admission application targeted for Week 2 of the grant sprint ([Decision 2](docs/grant/04-research-and-decisions.md)). The Conservancy provides governance continuity, legal personality, and a fiscal channel for grants + donations independent of any single human maintainer. |
| **Self-hostable** | The full application — chat router, MCP server, AI provider abstraction, encrypted-at-rest persistence — runs on commodity hardware (a 2 GiB-RAM VM, a Raspberry Pi, a Docker host). Deployment recipe at [`docs/deployment-recipe.md`](docs/deployment-recipe.md). Reproducible build via Nix flake at [`flake.nix`](flake.nix). |
| **No commercial gate** | Zero per-seat licensing fees ([cost-saving doctrine §3](docs/grant/08-cost-saving-doctrine.md)). No paid-tier feature gating. No "open-core" double-licensing. |
| **No vendor lock-in** | BYO-AI architecture: every provider call routes through a small abstraction in `company_discovery/ai_providers.py` (OpenAI / Gemini / DeepSeek / OpenRouter / Ollama / manual / Claude Code). Switching providers is one config change, not a re-engineering effort. |
| **Privacy-preserving by design** | CV text + TOTP secrets encrypted at rest (ChaCha20-Poly1305 AEAD with per-user AAD; see [`company_discovery/crypto_kit.py`](company_discovery/crypto_kit.py)). No data egress beyond user-consented AI provider calls. Audit log per EU AI Act Article 12. |
| **Cost-saving doctrine** | Every feature decision is evaluated against "does it reduce institutional cost while improving outcomes?" Full evaluation rubric at [`docs/grant/08-cost-saving-doctrine.md`](docs/grant/08-cost-saving-doctrine.md). |

The combination — open-source license, Conservancy wrapper,
self-hostability, no commercial gate, no vendor lock-in,
privacy-preserving design, cost-saving doctrine — makes the
project's existence resilient to changes in any single funder's
priorities, any single contributor's availability, or any single
hosting provider's terms.

---

## Grant arc plan

Helpmefindthejob's funding model is a **multi-grant arc** —
following the documented Redwax pattern within the NLnet
ecosystem. The arc has four phases:

### Phase 1 — current submission

**Target**: [NLnet NGI Zero Commons Fund](https://nlnet.nl/commonsfund/).
**Ask**: ~€37,000 across 6 milestones (frugal-by-default budget;
full breakdown in
[`docs/grant/12-application-package.md`](docs/grant/12-application-package.md)).
**Phase 1 deliverables shipped or anchored before submission**:

- Legal hardening: Apache 2.0 + CLA + Code of Conduct + governance
  pack
- Repository hygiene: SPDX headers, signed releases (cosign), SBOM
  (CycloneDX), reproducible build (Nix flake)
- MCP composition proof: 13-tool catalogue (v0.2.0) with stdio
  JSON-RPC + schema-validated input
- EU AI Act compliance pack: transparency notice, risk-management
  plan, FRIA template, technical documentation, accuracy + bias
  testing methodology, audit-log schema, data governance,
  human-oversight guide, deployer operating manual
- Public demo (parallel-public-instance deployment recipe)
- Accessibility: WCAG 2.2 AA first pass + auth-surface audit +
  light-mode + compliance markdown + dynamic-state coverage
- Documentation site at maksodf.github.io/helpmefindthejob/
- RFC 9116 `/.well-known/security.txt`
- Translator-contributor pathway
- OpenSSF Scorecard workflow + SHA-pinned actions

### Phase 2 — NLnet follow-on (multi-grant pattern)

**Target**: a second NLnet round (Commons Fund / NGI Search /
NGI Trustchain depending on framing fit). **Multi-grant arcs
inside the NLnet ecosystem are common** — the Redwax project
ran four consecutive NLnet rounds and the trajectory is
documented in NLnet's own programme history.

**Phase 2 scope** (under planning, not committed):

- **Framework extraction** — convert Helpmefindthejob's
  modular core into a reusable template for other civic
  agents (housing, healthcare, residency, education).
  Composable via the existing MCP catalogue.
- **Second institutional pilot** — partner with an
  Optionskommune, an IQ-Netzwerk regional anchor, or an MBE
  network for a real-deployment evidence run. Outcome
  artefact: a published case study of caseload-reduction +
  time-to-employment effects.
- **WIP module reintegration** — Decision 16 parked several
  in-progress modules during Phase 1 to keep the sprint
  focused; the
  [`docs/grant/03-post-grant.md`](docs/grant/03-post-grant.md)
  triage gate evaluates each module on its merits before
  reintegrating.
- **Localisation** — Arabic + Ukrainian + Turkish + Romanian
  locale bundles, anchored to the persona panel per Decision
  21. Translator pathway already documented at
  [`docs/translating.md`](docs/translating.md).
- **Accessibility deepening** — keyboard + screen-reader
  review (HAN University audit pathway is NLnet's standard
  partner once Conservancy admission lands).

### Phase 3 — diversification

**Targets** under consideration (each independent of the
others):

- [Sovereign Tech Fund](https://www.sovereigntechfund.de/) —
  Germany-side complement to the NLnet arc; explicit mandate
  for digital-commons infrastructure that the public sector
  depends on
- [NGI Search](https://www.ngi.eu/ngi-projects/ngi-search/) —
  if Helpmefindthejob's discovery-and-aggregation layer
  matures to a stand-alone proposition
- [NGI Trustchain](https://trustchain.ngi.eu/) — relevant
  for the EU AI Act compliance + auditability stack as a
  reusable artefact
- EU Digital Europe Programme calls aligned with civic-tech
  infrastructure

### Long-term — anchor + diversify

Long-term, Helpmefindthejob remains anchored as **a Programme
of The Commons Conservancy** with **diversified funding**:
multiple short-to-medium grants (not a single perpetual
grant), optional institutional support contracts (see
below), and community donations. No single funding stream
exceeds ~50% of the project's resource needs in any year —
this is the same diversification posture the Conservancy
encourages for all of its Programmes.

---

## Optional support contracts (carefully framed)

Helpmefindthejob's **default operational model is self-host +
community support**. This will remain the default.

Institutional deployers (a Beratungsstelle, an
Optionskommune, an MBE network, a Migrationsberatungsstelle,
a university career service, a foundation-funded social
service) **may** optionally engage paid support via:

1. **Hosted-instance contracts** — the Conservancy or a
   maintainer-appointed entity hosts an instance for the
   institution at-cost-plus-margin. Hardware + bandwidth + AI
   provider passthrough + a small operations fee.
2. **Custom-integration consulting** — wiring DirectJob
   Scout into the institution's existing case-management
   stack (SAP HR, Jobs2Web, internal databases). Engagement-
   scoped, not per-seat.
3. **Training + onboarding for advisors** — a half-day to
   full-day onboarding for advisor staff at an institution
   that deploys the tool.

**Pricing is per-engagement, not per-seat.** This preserves
the [no-per-seat-pricing commitment](docs/grant/08-cost-saving-doctrine.md)
that underwrites the cost-saving doctrine.

**The Commons Conservancy receives these contracts on the
project's behalf** (post-admission). Revenue flows to the
Conservancy, not to any individual maintainer; the
Conservancy then funds maintainer time + infrastructure
based on the project's needs.

**Honest framing**: as of 2026-05-19, **zero contracts of
any kind exist**. There is no current revenue. The above
describes the structure that's available to use, not a
current offering.

---

## Community + contribution channels

| Channel | Purpose | Reference |
|---|---|---|
| **GitHub Discussions** | Questions, design discussions, support requests | [`SUPPORT.md`](SUPPORT.md) |
| **GitHub Issues** | Bug reports, feature requests | [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/) |
| **Pull requests (CLA-gated)** | Code, documentation, translations | [`CONTRIBUTING.md`](CONTRIBUTING.md) + [`cla.md`](cla.md) |
| **Translation contributions** | New locale bundles (Arabic / Ukrainian / Turkish / Romanian roadmap per Decision 6 + Decision 21) | [`docs/translating.md`](docs/translating.md) |
| **Security disclosure** | Private vulnerability reports | [`SECURITY.md`](SECURITY.md) + RFC 9116 [`security.txt`](https://maksodf.github.io/helpmefindthejob/.well-known/security.txt) |
| **Code of Conduct** | Contributor Covenant 2.1 | [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) |

Contributors are credited in [`AUTHORS.md`](AUTHORS.md) and
[`ACKNOWLEDGMENTS.md`](ACKNOWLEDGMENTS.md). Both follow the
**consent-first authorship policy** ([Decision 18](docs/grant/04-research-and-decisions.md)):
a contributor's name appears in those files only after explicit
consent, captured in a separate dated commit.

---

## Donation channels (placeholder framing)

The project's preferred sustainability channel is the
**multi-grant arc + the Commons Conservancy wrapper**.
Donations are welcome but secondary.

| Channel | Status | Notes |
|---|---|---|
| **GitHub Sponsors** | Placeholder in [`.github/FUNDING.yml`](.github/FUNDING.yml) | The maintainer activates the actual Sponsors profile when ready, per [Decision 18](docs/grant/04-research-and-decisions.md) consent-first authorship — pre-launch (Decision 17) the project deliberately does not invite donations |
| **Open Collective** | Placeholder | Post-Conservancy-admission, the Conservancy entity may set up an Open Collective channel that flows to it |
| **The Commons Conservancy direct donation** | Available post-admission | The Conservancy publishes a stichting bank account; donations earmarked for Helpmefindthejob are routed to the project's Conservancy account |

Contributors and donors are credited (with their consent) in
[`ACKNOWLEDGMENTS.md`](ACKNOWLEDGMENTS.md). Crediting policy
preserves Decision 18 consent-first authorship: no name appears
without an explicit, dated consent commit.

---

## Honest state of the project (2026-05-19)

- **Never publicly launched.** Per [Decision 17](docs/grant/04-research-and-decisions.md),
  the project is pre-launch. There is no public demo URL today; the
  parallel-public-instance deployment recipe describes how a
  deployer would bring one up post-grant.
- **One private tester** (the maintainer's partner / co-maintainer
  per Decision 17). The partner is the project's domain expert,
  bureaucratic-coordination lead, and sole user-facing tester.
- **Zero paying users today.** Zero hosted-instance contracts.
  Zero training-onboarding engagements. Zero
  custom-integration consulting bookings.
- **Zero outside contributors today** (single-maintainer +
  one co-maintainer per Decision 17). The project is open to
  contributors; none have arrived yet.
- **Zero donations received today.** GitHub Sponsors not yet
  activated; Open Collective not yet set up.

**The project is sustainable on these terms.** The
sustainability commitment is structural, not revenue-driven:
- the Apache 2.0 + CLA license makes the code permanently
  forkable
- the Commons Conservancy wrapper (pending) makes the
  governance + fiscal channel durable beyond any individual
  contributor
- the multi-grant arc provides funded development windows
- the self-hostable architecture means institutional
  deployers can run Helpmefindthejob indefinitely on their
  own infrastructure without depending on the maintainer

**No growth-metric promises.** This document does not commit
to a target user count, deployment count, contributor count,
or revenue figure. The commitment is to keep existing as a
useful commons — code reachable from the public repository,
governance reachable from the Conservancy wrapper, and
operating documentation reachable from this and adjacent
files.

---

## Sustainability red flags (what would change this story)

The project would have to reassess its sustainability posture
if any of the following happens. None has happened today; the
list is the honest pre-mortem:

1. **NLnet rejection without alternative grant within 6
   months.** Mitigation: the Conservancy wrapper + multi-grant
   arc has at least 3 viable Phase 2 paths (NLnet follow-on /
   STF / NGI Search) — single-grant failure isn't existential
   if the Conservancy admission lands.
2. **Conservancy admission rejected.** Mitigation: alternative
   institutional wrappers exist (Software Freedom Conservancy,
   Code for Germany e.V., Prototype Fund's portfolio
   relationship). The
   [`docs/grant/03-post-grant.md`](docs/grant/03-post-grant.md)
   "If we don't win the grant" section sketches this fallback.
3. **The maintainer + co-maintainer both withdraw.** The
   Conservancy wrapper preserves the code + the governance
   structure independent of any human; another maintainer
   can take stewardship via the Conservancy's
   Programme-handover process.
4. **An institutional pilot proves the cost-saving doctrine
   wrong.** This would surface as a real-world signal that
   the project's cost-savings claims don't generalise. The
   doctrine ([`docs/grant/08-cost-saving-doctrine.md`](docs/grant/08-cost-saving-doctrine.md))
   is structured as testable hypotheses, not as marketing
   copy. A failed pilot triggers re-evaluation, not a defensive
   patch.

---

## Cross-links

| Surface | Reference |
|---|---|
| Project brief — mission, positioning, strategy | [`docs/grant/01-project-brief.md`](docs/grant/01-project-brief.md) |
| Post-grant detailed roadmap | [`docs/grant/03-post-grant.md`](docs/grant/03-post-grant.md) |
| Cost-saving doctrine — institutional value evaluation | [`docs/grant/08-cost-saving-doctrine.md`](docs/grant/08-cost-saving-doctrine.md) |
| Decisions log | [`docs/grant/04-research-and-decisions.md`](docs/grant/04-research-and-decisions.md) |
| Quarterly public roadmap | [`ROADMAP.md`](ROADMAP.md) |
| Crediting policy + consent-first authorship | [`AUTHORS.md`](AUTHORS.md) + [Decision 18](docs/grant/04-research-and-decisions.md) |
| The Commons Conservancy | <https://commonsconservancy.org/> |
| NLnet NGI Zero Commons Fund | <https://nlnet.nl/commonsfund/> |
| Sovereign Tech Fund | <https://www.sovereigntechfund.de/> |
| Standards we implement | [`STANDARDS.md`](STANDARDS.md) |
| Reproducible build (Nix flake) | [`flake.nix`](flake.nix) + [`docs/deployment-recipe.md`](docs/deployment-recipe.md) §12 |
| Signed releases + SBOM | [`docs/releases/v0.1.0-signing.md`](docs/releases/v0.1.0-signing.md) |
| RFC 9116 security.txt | <https://maksodf.github.io/helpmefindthejob/.well-known/security.txt> |
