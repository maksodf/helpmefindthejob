# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Feature-flag runtime substrate (13-plan item 5/13; gap #18).

Goal: enable safe rollout of new features without requiring a
re-deploy per toggle. Three layers of decision (highest priority
first):

1. **Operator env-var override** —
   ``HELPMEFINDTHEJOB_FLAG_<FLAG_NAME>=true|false``. When set,
   wins over everything else. Use for kill-switches + emergency
   disables.
2. **Per-user deterministic percentage rollout** — a flag with
   ``rollout_percent=25`` is enabled for the same ~25% of users
   on every call, derived from a stable HMAC over (flag_name,
   user_id). Same user always gets the same answer; cohort
   membership is stable across process restarts.
3. **Code-default** — when no operator override exists and no
   user_id is provided (system call), return the flag's
   declared default.

Design rules:

- **Enumerated flags only**: every flag MUST be registered in
  :data:`FLAGS` with a name, default, description, and rollout
  percent. A typo at the call site (``flags.is_enabled("typo")``)
  raises ``KeyError`` rather than silently returning False —
  catches drift between caller + flag registry.
- **Stdlib only**: stays consistent with the anti-framework
  doctrine the rest of the project follows.
- **Deterministic** within a process: same (flag_name, user_id)
  always returns the same answer. No random sampling per call.
- **No DB writes**: this module is pure read-side. The
  per-user-override-database escape hatch is intentionally NOT
  built — the env-var override + percentage rollout cover 95%
  of needs; specific-user overrides are a Phase 2 item if any
  flag truly needs them.

A/B testing (13-plan item 6/13) builds on top of this:
``assign_variant("experiment_name", user_id, variants=["A","B"])``
uses the same stable-hash mechanism to put users in cohorts.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Flag:
    """One feature flag.

    - ``name`` is the canonical key callers use.
    - ``default`` is returned when no override + no user_id +
      rollout_percent is 0.
    - ``description`` is operator-facing; surfaced in admin
      diagnostics so the operator knows what each flag does.
    - ``rollout_percent`` is 0–100 (clamped). 0 means "code-
      default only, never rolled out by hash"; 100 means
      "enabled for all users when no override says otherwise".
    """

    name: str
    default: bool
    description: str
    rollout_percent: int = 0


# The canonical registry. Every flag MUST be listed here.
# Adding a new flag = add an entry below; remove a deprecated
# one = remove the entry + delete every is_enabled call site.
#
# When you ship a new flag:
#   1. Add it here with `default=False, rollout_percent=0`
#      (cold start — nothing changes for anyone).
#   2. Land the code that calls `is_enabled(name, user_id=…)`.
#   3. Bump `rollout_percent` to 10, then 50, then 100 over
#      successive deploys.
#   4. Once at 100 for a release cycle without incident,
#      remove the call sites + the flag entry (no permanent
#      "if flag_x" branches in the codebase).
#
# Names: lowercase + underscore. Group by domain prefix.
FLAGS: dict[str, Flag] = {
    "ui.new_funnel_card": Flag(
        name="ui.new_funnel_card",
        default=True,
        description="Show the apply→reply→interview funnel card on the dashboard (13-plan item 3/13).",
        rollout_percent=100,
    ),
    "ui.workspace_member_admin": Flag(
        name="ui.workspace_member_admin",
        default=True,
        description="Show the workspace members admin UI in Settings (13-plan item 4/13).",
        rollout_percent=100,
    ),
    "ai.streaming_dispatch": Flag(
        name="ai.streaming_dispatch",
        default=True,
        description="Use the SSE token-streaming dispatch for AI calls (Phase 2 #77).",
        rollout_percent=100,
    ),
    "experiment.example_ab": Flag(
        name="experiment.example_ab",
        default=False,
        description="Example experiment flag — used by the A/B testing E2E tests. Safe to leave at 0%.",
        rollout_percent=0,
    ),
}


# Env-var prefix for operator overrides. To override `ui.new_funnel_card`,
# the operator sets `HELPMEFINDTHEJOB_FLAG_UI_NEW_FUNNEL_CARD=false`.
_ENV_PREFIX = "HELPMEFINDTHEJOB_FLAG_"
# Salt for the per-user stable hash. Different from the audit-log
# salt so a flag's cohort assignment is not derivable from the
# audit chain (and vice-versa).
_ROLLOUT_HMAC_SALT = b"helpmefindthejob:feature-flag:v1"


def _env_var_name(flag_name: str) -> str:
    """Map flag name to env var name: `ui.new_funnel_card` →
    `HELPMEFINDTHEJOB_FLAG_UI_NEW_FUNNEL_CARD`."""

    sanitized = flag_name.upper().replace(".", "_").replace("-", "_")
    return _ENV_PREFIX + sanitized


def _read_env_override(flag_name: str) -> bool | None:
    """Read the operator env-var override for a flag. Returns
    None if unset; True / False if set. Accepts a generous set of
    truthy / falsy spellings so the operator doesn't get tripped
    up by case."""

    raw = os.environ.get(_env_var_name(flag_name), "").strip().lower()
    if raw in {"true", "1", "yes", "on", "enable", "enabled"}:
        return True
    if raw in {"false", "0", "no", "off", "disable", "disabled"}:
        return False
    return None


def _percentage_bucket(flag_name: str, user_id: str) -> int:
    """Stable 0–99 bucket for a (flag_name, user_id) pair.

    HMAC-SHA256 so the bucket is not predictable from the
    flag_name alone — an attacker can't easily craft a user_id
    that lands in any specific bucket (defends against
    cohort-targeting attacks if a flag controls a security-
    sensitive surface).

    Same input → same bucket forever (no randomness, no time
    component). This is the foundation for stable A/B
    assignments.
    """

    digest = hmac.new(
        _ROLLOUT_HMAC_SALT,
        f"{flag_name}|{user_id}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    # Take the first 4 bytes as a big-endian uint32, mod 100
    bucket = int.from_bytes(digest[:4], "big") % 100
    return bucket


def is_enabled(
    flag_name: str,
    *,
    user_id: str | None = None,
) -> bool:
    """Return whether ``flag_name`` is enabled.

    Decision order (highest precedence first):
    1. Env-var override — wins over everything.
    2. If ``user_id`` is provided AND the flag has
       ``rollout_percent > 0``: deterministic percentage
       bucket — same user always gets the same answer.
    3. Otherwise the flag's ``default``.

    Raises ``KeyError`` if ``flag_name`` is not registered in
    :data:`FLAGS` — typos at call sites would otherwise silently
    return False forever.
    """

    if flag_name not in FLAGS:
        raise KeyError(f"unregistered_flag:{flag_name!r}")
    override = _read_env_override(flag_name)
    if override is not None:
        return override
    flag = FLAGS[flag_name]
    if user_id and flag.rollout_percent > 0:
        # Clamp to [0, 100] so a misconfigured registry entry
        # can't break the math
        pct = max(0, min(100, flag.rollout_percent))
        bucket = _percentage_bucket(flag_name, user_id)
        return bucket < pct
    return flag.default


def all_flags() -> list[dict[str, object]]:
    """Return every registered flag's metadata as a list of
    dicts. Used by the admin diagnostic endpoint so operators
    can audit which flags are present + their defaults."""

    return [
        {
            "name": flag.name,
            "default": flag.default,
            "description": flag.description,
            "rolloutPercent": flag.rollout_percent,
            "envVar": _env_var_name(flag.name),
        }
        for flag in sorted(FLAGS.values(), key=lambda f: f.name)
    ]


def assign_variant(
    experiment_name: str,
    user_id: str,
    variants: list[str],
) -> str:
    """Deterministically assign a user to one of ``variants``
    for an A/B (or A/B/C/…) experiment.

    Uses the same HMAC bucket mechanism as percentage rollout
    so the assignment is stable across process restarts.

    This is the foundation for 13-plan item 6/13 (A/B testing
    framework). The experiment name doubles as a flag-style
    key so the same operator overrides (kill switch) work.

    Returns the chosen variant. Raises ``ValueError`` for
    empty variants list.
    """

    if not variants:
        raise ValueError("variants_must_not_be_empty")
    # Same hash mechanism as percentage rollout so cohort
    # membership stays stable. Modulo by the variant count.
    digest = hmac.new(
        _ROLLOUT_HMAC_SALT,
        f"experiment:{experiment_name}|{user_id}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    bucket = int.from_bytes(digest[:4], "big") % len(variants)
    return variants[bucket]
