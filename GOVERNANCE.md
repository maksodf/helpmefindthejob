<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Governance

This document describes **how Helpmefindthejob is governed** — who decides
what, how someone earns a say, and how the project is meant to outlive any
single contributor. It is deliberately short and honest about the project's
current stage; it will grow as the contributor base does.

For the *mechanics* of contributing (CLA, dev setup, commit conventions, the
review bar), see [`CONTRIBUTING.md`](CONTRIBUTING.md). For expected behaviour,
see [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). The strategic rationale behind
the project lives in [`docs/grant/`](docs/grant/).

## Current state (be honest about the stage)

Helpmefindthejob is, today, an **early-stage project with a single active
maintainer** (see [`AUTHORS.md`](AUTHORS.md)) and no outside contributors yet.
The [claims ledger](docs/claims-ledger.md) records this plainly: a
contributor community is a *human-track* goal, not something the code can
manufacture. We would rather state that openly than imply a board that does not
exist. This governance model is sized for that reality and is explicitly
designed to decentralise as people arrive.

## Decision-making

- The **maintainer is the final decision-maker** on technical and product
  direction, consistent with the *“How decisions are made”* section of
  [`CONTRIBUTING.md`](CONTRIBUTING.md).
- Decisions are made **in the open** wherever practical: substantive changes go
  through pull requests and issues so the reasoning is on the record.
- **Strategic decisions are logged.** Binding choices (licence, institutional
  wrapper, persona doctrine, AI-Act posture, etc.) are recorded in
  [`docs/grant/04-research-and-decisions.md`](docs/grant/04-research-and-decisions.md)
  with their rationale, so future contributors can see *why*, not just *what*.
- **Disagreement** is resolved by discussion on the relevant issue/PR; if no
  consensus emerges, the maintainer decides and records the reasoning. As the
  maintainer group grows (below), contentious calls move to maintainer
  consensus, then to a documented lazy-consensus vote.

## Becoming a maintainer

Maintainership is **earned through sustained, high-quality contribution**, not
appointed. The path and expectations are described under *“Recognition and
maintainership”* in [`CONTRIBUTING.md`](CONTRIBUTING.md). In short: contribute
real work, review others' work well, show good judgement on scope and user
impact, and a maintainer will propose adding you. New maintainers are added by
agreement of the existing maintainer(s) and listed in
[`AUTHORS.md`](AUTHORS.md).

## Licensing and contributions

- The project is licensed under **Apache 2.0** (see [`LICENSE`](LICENSE) and
  [`NOTICE`](NOTICE)).
- All contributions are accepted under a **Contributor License Agreement**
  (see [`cla.md`](cla.md)), which keeps the project re-licensable by a future
  steward (e.g. The Commons Conservancy) without having to chase every past
  contributor — a deliberate sustainability choice for a civic commons.
- New source files carry an `SPDX-License-Identifier: Apache-2.0` header.

## Institutional stewardship and succession

A civic-employment commons should not depend on one person's continued
availability. Two mechanisms address that:

1. **Commons Conservancy track.** The project is applying to become a
   **Programme of [The Commons Conservancy](https://commonsconservancy.org)**
   (a Dutch *stichting* co-founded by NLnet). *Admission is pending* — the
   public surfaces say so, and this is not yet a completed fact. Once admitted,
   the Conservancy provides a neutral, non-profit institutional home and an
   asset-lock that survives any individual maintainer. Until then, the
   Apache-2.0 + CLA combination already lets any capable steward fork and carry
   the project forward.
2. **Bus-factor mitigation.** Everything required to run, deploy, and reason
   about the project is in the repository and reproducible: the deployment
   recipe, the AI-Act compliance pack, the reproducible build, and the decision
   log. There are no private dependencies that would strand a successor. If the
   maintainer becomes unavailable, a contributor can self-host, fork, and
   continue under the same licence with no permission required.

## Code of Conduct

Participation is governed by [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
(Contributor Covenant). Conduct concerns can be raised via the maintainer
contact in [`AUTHORS.md`](AUTHORS.md); a dedicated `conduct@helpmefindthejob.org`
address is added once the project's mail domain is wired (tracked alongside the
`security@` mailbox in [`SECURITY.md`](SECURITY.md)).

## How this document evolves

This is a living document. As the project gains co-maintainers and (post-grant)
an institutional home, the decision model formalises — from “maintainer
decides, in the open” toward documented maintainer consensus and, where the
Conservancy requires it, programme-level governance. Changes to governance go
through the same open pull-request process as any other change.
