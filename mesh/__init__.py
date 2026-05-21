# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Reference implementation of the helpmefindthejob civic-services mesh.

This package ships simulator stubs for three cooperating civic
agents — housing, Anerkennung, social-services — so the
employment-agent's outbound MCP tools (``propose_referral``,
``get_user_profile_for_consent``, ``query_esco_skill``) have
concrete receivers we can demonstrate against.

Why we ship simulators with the project:

1. **Protocol reality, not protocol promise.** Without working
   receivers, the federated-mesh story is theoretical. With
   them, the architecture is testable + demonstrable end-to-
   end via a single ``docker compose up``.

2. **Reference implementations for partner integrators.** When
   a real Berlin Wohnungsamt wants to integrate with the
   employment-agent, they can read ``mesh/housing_agent.py``
   as a worked example of the protocol — not a 30-page spec
   document.

3. **Test fixtures.** Each simulator carries 2–3 realistic
   scenarios per cohort (Aïcha §16d / Yusuf Blue Card / Olga
   §24 etc.) so the end-to-end demo isn't a single happy path.

4. **Dependency minimalism.** Each simulator runs on Python
   stdlib only — same dep policy as the main app. The whole
   mesh runs from one docker-compose with no FastAPI, no
   Flask, no Django, no Node.js. That itself is part of the
   civic-sovereignty story: a Beratungsstelle running on a
   modest server doesn't pay an operational tax for the mesh.

Layout::

    mesh/
        __init__.py                      — this file
        common.py                        — shared utilities
        housing_agent.py                 — port 8101
        anerkennung_agent.py             — port 8102
        social_services_agent.py         — port 8103
        demo_aicha_walk.py               — end-to-end script
        mesh-docker-compose.yml          — orchestration
        README.md                        — protocol + diagram

The main employment-agent at ``app.py`` listens on its own port
(default 8765) and is the ORIGIN of every mesh interaction in the
demo — the simulators are passive receivers that respond to its
referrals.
"""

from __future__ import annotations
