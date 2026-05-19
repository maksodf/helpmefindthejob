#!/usr/bin/env python3
# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Seed the seven-persona panel into a Helpmefindthejob instance.

This script is part of the §3.4 parallel-public-instance recipe. It
creates seven demo accounts (Aïcha, Yusuf, Olga, Mahmoud, Maria,
Käthe, Tobias) with the maintainer-supplied demo password, each
pre-populated with a CV summary, target roles, residency context,
and 1-2 saved searches matching the persona's job-target situation.

The persona records are sourced from
``company_discovery/persona_fixtures.py`` — the same module
``tests/test_bias_methodology.py`` consumes, so there is exactly one
canonical persona definition in the codebase.

Idempotency
-----------
Re-running the script is a no-op when all seven personas already
exist with their profiles and saved searches. Partial-state recovery:
if seeding crashed after 3 of 7 personas, the next invocation picks
up at #4. Existing user accounts with the same email are detected
via ``AuthStore.list_users()`` and their passwords are NOT overwritten
unless ``--force-password-reset`` is passed.

Operation modes
---------------
The script writes directly to the local SQLite database via
``app.build_state()`` — no HTTP, no auth dance, runs offline. The
``--base-url`` flag is accepted for forward compatibility with a
future HTTP-API mode but is not currently consumed; surface a
warning if a non-default value is supplied. The recipe at
``docs/deployment-recipe.md`` documents how to invoke the script
inside the running container via ``docker compose exec``.

Usage
-----
::

    python3 scripts/seed-personas.py --password '<demo-password>'

Other flags::

    --data-dir PATH         Override COMPANY_DISCOVERY_DATA_DIR for one run.
    --email-domain DOMAIN   Override the default demo.helpmefindthejob.com.
    --base-url URL          Reserved for future HTTP-API mode; not used.
    --force-password-reset  Overwrite existing personas' passwords too.
    --dry-run               Print what would be created; don't write anything.

The maintainer never hardcodes the demo password — it is always
passed at run time and never written to disk.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import sys
from pathlib import Path
from typing import Any

# Make the repo root importable when the script is run from anywhere
# (including ``docker compose exec`` which sets CWD to /app, and
# bare ``python3 scripts/seed-personas.py`` which sets CWD to the
# script's directory). Adding the parent of ``scripts/`` to sys.path
# is the canonical pattern used by the rest of the project's scripts.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


from company_discovery.models import SavedSearch, UserProfile  # noqa: E402
from company_discovery.persona_fixtures import (  # noqa: E402
    PERSONAS,
    PersonaFixture,
    demo_email,
)

# ---------------------------------------------------------------------------
# Idempotent persona-record materialisation.
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class SeedSummary:
    """What happened during a single seed-personas invocation."""

    created: list[str] = dataclasses.field(default_factory=list)
    already_present: list[str] = dataclasses.field(default_factory=list)
    profile_updated: list[str] = dataclasses.field(default_factory=list)
    saved_searches_created: int = 0
    password_reset: list[str] = dataclasses.field(default_factory=list)
    dry_run: bool = False

    def render(self) -> str:
        lines = []
        if self.dry_run:
            lines.append("DRY-RUN (no writes performed)")
        if self.created:
            lines.append(f"created accounts: {sorted(self.created)}")
        if self.already_present:
            lines.append(f"already-present accounts: {sorted(self.already_present)}")
        if self.profile_updated:
            lines.append(f"profile updated: {sorted(self.profile_updated)}")
        if self.password_reset:
            lines.append(f"password reset: {sorted(self.password_reset)}")
        lines.append(f"saved searches created (this run): {self.saved_searches_created}")
        return "\n".join(lines)


def _persona_to_user_profile(persona: PersonaFixture, user_id: str) -> UserProfile:
    """Build a ``UserProfile`` from a ``PersonaFixture``."""
    return UserProfile(
        user_id=user_id,
        persona_id=persona.slug,
        target_roles=list(persona.target_roles),
        industry=persona.industry,
        location=persona.location,
        seniority=persona.seniority,
        years_experience=persona.years_experience,
        languages=list(persona.languages),
        cv_text=persona.cv_summary,
        locale=persona.locale,
        notes=persona.friction_notes,
    )


def _persona_to_saved_searches(persona: PersonaFixture, user_id: str) -> list[SavedSearch]:
    """Build the persona's saved searches as ``SavedSearch`` records."""
    records: list[SavedSearch] = []
    for entry in persona.saved_searches:
        records.append(
            SavedSearch(
                user_id=user_id,
                name=entry["name"],
                target_roles=list(entry.get("target_roles", [])),
                industry=entry.get("industry", persona.industry),
                location=entry.get("location"),
                notes=entry.get("notes"),
            )
        )
    return records


def _existing_user_id(state: Any, email: str) -> str | None:
    """Look up an existing user's ID by email, returning ``None`` if missing."""
    for user in state.auth_store.list_users():
        if getattr(user, "email", "").lower() == email.lower():
            return user.id
    return None


def _existing_saved_search_names(state: Any, user_id: str) -> set[str]:
    """Names of saved searches already attached to the user."""
    try:
        return {s.name for s in state.repository.list_saved_searches(user_id)}
    except Exception:  # noqa: BLE001 - repository surface differs across backends
        return set()


def seed(
    state: Any,
    password: str,
    email_domain: str,
    *,
    force_password_reset: bool = False,
    dry_run: bool = False,
) -> SeedSummary:
    """Run the seed against the supplied ``state`` (an ``AppState``).

    Idempotent: existing personas are detected by email and skipped
    unless ``force_password_reset`` is set. Saved searches are detected
    by ``(user_id, name)`` and never duplicated.
    """
    summary = SeedSummary(dry_run=dry_run)
    for persona in PERSONAS:
        email = demo_email(persona.slug, email_domain)
        existing_id = _existing_user_id(state, email)
        if existing_id is None:
            if dry_run:
                summary.created.append(persona.slug)
                continue
            user = state.auth_store.create_user(email=email, password=password, role="member")
            user_id = user.id
            summary.created.append(persona.slug)
        else:
            user_id = existing_id
            summary.already_present.append(persona.slug)
            if force_password_reset and not dry_run:
                # AuthStore exposes set_password; if not available,
                # fall through silently rather than block the seed.
                set_password = getattr(state.auth_store, "set_password", None)
                if callable(set_password):
                    set_password(user_id, password)
                    summary.password_reset.append(persona.slug)

        # Always upsert the profile and saved searches — the profile content
        # may have evolved between runs as persona_fixtures.py is updated.
        profile = _persona_to_user_profile(persona, user_id)
        if not dry_run:
            state.repository.save_user_profile(profile)
        summary.profile_updated.append(persona.slug)

        existing_search_names = _existing_saved_search_names(state, user_id)
        for search in _persona_to_saved_searches(persona, user_id):
            if search.name in existing_search_names:
                continue
            if not dry_run:
                state.repository.save_saved_search(search)
            summary.saved_searches_created += 1

    return summary


# ---------------------------------------------------------------------------
# CLI entry point.
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the seven-persona panel into a Helpmefindthejob instance."
    )
    parser.add_argument(
        "--password",
        required=True,
        help=(
            "Demo password applied to every persona account. Never "
            "hardcoded; the maintainer supplies it at run time and the "
            "value is never written to disk."
        ),
    )
    parser.add_argument(
        "--email-domain",
        default="demo.helpmefindthejob.com",
        help=(
            "Email domain for the seven persona accounts. Default is "
            "the public-tree placeholder convention (Decision 12); "
            "deployers override with their real demo subdomain "
            "(the override stays in the deployer's private .env)."
        ),
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help=(
            "Override COMPANY_DISCOVERY_DATA_DIR for this run. "
            "Useful for tests or for running the seed against a "
            "non-default data location."
        ),
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8765",
        help=(
            "Reserved for future HTTP-API mode; not currently consumed. "
            "The script writes directly to the local SQLite database "
            "via app.build_state(). The flag is accepted for forward "
            "compatibility."
        ),
    )
    parser.add_argument(
        "--force-password-reset",
        action="store_true",
        help=(
            "Overwrite existing persona accounts' passwords too. "
            "Default: existing accounts' passwords are NOT touched."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without writing anything.",
    )
    return parser.parse_args(argv)


def _build_state(data_dir: str | None) -> Any:
    """Construct an ``AppState`` against the configured data dir.

    The script does not spin up the HTTP server. For tests that need
    a fresh state instance against a tmp directory, call
    ``seed(state, ...)`` directly with a state built by the test.
    """
    if data_dir is not None:
        os.environ["COMPANY_DISCOVERY_DATA_DIR"] = data_dir
    # Import here so the env-var override takes effect before app.py's
    # module-level configuration loading.
    from app import AppState

    return AppState(start_scheduler=False)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.base_url and args.base_url != "http://localhost:8765":
        print(
            f"[seed-personas] note: --base-url={args.base_url!r} is reserved for a "
            f"future HTTP-API mode and is not consumed in this version. The script "
            f"writes directly to the local SQLite DB via app.build_state(). See the "
            f"script docstring for the operational story.",
            file=sys.stderr,
        )

    state = _build_state(args.data_dir)
    summary = seed(
        state,
        password=args.password,
        email_domain=args.email_domain,
        force_password_reset=args.force_password_reset,
        dry_run=args.dry_run,
    )
    print(summary.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
