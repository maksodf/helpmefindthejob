# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Environment-variable compatibility shim.

Helpmefindthejob inherits two generations of env-var naming:

* ``COMPANY_DISCOVERY_*`` — the pre-rename project's prefix.
* ``DIRECTJOB_*`` — the post-Week-1 / pre-Decision-22 prefix.

Forward-going, the project's canonical prefix is ``HELPMEFINDTHEJOB_*``
(Decision 22, 2026-05-19). The migration is deliberately staged so that
existing institutional deployments do not break on a single push: every
read site uses :func:`get_env` (or its `_int`/`_bool` variants) which
tries the new prefix first, then the legacy name(s), emitting a
``DeprecationWarning`` whenever a legacy variable is consumed.

The legacy prefixes are removed in Phase 3; see the migration path in
``docs/deployment-recipe.md``. Until then this shim is the single
choke point through which every environment read flows.

Doctrine:

* Always pass the **new** ``HELPMEFINDTHEJOB_*`` name as the first
  argument so the call site documents the going-forward identity.
* Pass the legacy ``DIRECTJOB_*`` name as the second argument so the
  shim can fall back without the call site needing to know which
  generation the deployer set.
* For the four ``COMPANY_DISCOVERY_*`` variables that survived two
  rename cycles, pass both legacy names — the shim accepts a list.
* Tests that exercise behavior under specific env values should clear
  both old and new names in ``setUp`` (see
  ``tests/test_env_compat.py``).

This module has zero non-stdlib dependencies and is safe to import
from any other module.
"""

from __future__ import annotations

import os
import warnings
from typing import Iterable, Optional, Union, overload


def _normalize_legacy_arg(
    legacy_name: str | Iterable[str] | None,
) -> tuple[str, ...]:
    """Coerce the ``legacy_name`` arg to a tuple of names.

    Accepts ``None`` (no legacy fallback), a single string, or an
    iterable of strings (for variables that have lived under more
    than one legacy prefix).
    """
    if legacy_name is None:
        return ()
    if isinstance(legacy_name, str):
        return (legacy_name,)
    return tuple(legacy_name)


@overload
def get_env(
    new_name: str,
    legacy_name: Union[str, Iterable[str], None] = ...,
    default: None = ...,
) -> Optional[str]: ...


@overload
def get_env(
    new_name: str,
    legacy_name: Union[str, Iterable[str], None],
    default: str,
) -> str: ...


def get_env(
    new_name: str,
    legacy_name: Union[str, Iterable[str], None] = None,
    default: Optional[str] = None,
) -> Optional[str]:
    """Read an environment variable with legacy-prefix fallback.

    The lookup order is:

    1. The ``HELPMEFINDTHEJOB_*`` name (``new_name``). If set to any
       value (including an empty string), it is returned verbatim and
       the legacy names are not consulted.
    2. Each legacy name in order. The first one set returns its value
       and emits a ``DeprecationWarning`` so deployers see the rename
       reminder in their logs / CI.
    3. The ``default`` (which itself defaults to ``None``).

    The function does **not** strip or casefold. Callers that need
    those transformations should apply them on the returned value;
    keeping this helper transparent makes the shim trivially testable
    and avoids subtle differences from prior ``os.environ.get`` reads
    that the call sites already perform inline.
    """
    value = os.environ.get(new_name)
    if value is not None:
        return value
    for legacy in _normalize_legacy_arg(legacy_name):
        legacy_value = os.environ.get(legacy)
        if legacy_value is None:
            continue
        warnings.warn(
            f"Env var {legacy!r} is deprecated; rename to {new_name!r}. "
            "The legacy prefix is accepted with this DeprecationWarning "
            "through Phase 2; it is removed in Phase 3 — see "
            "docs/deployment-recipe.md migration path.",
            DeprecationWarning,
            stacklevel=2,
        )
        return legacy_value
    return default


def get_env_int(
    new_name: str,
    legacy_name: str | Iterable[str] | None = None,
    default: int = 0,
) -> int:
    """Convenience wrapper that parses the result of :func:`get_env`
    as ``int``. Returns ``default`` on parse failure or missing value.
    """
    raw = get_env(new_name, legacy_name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return default


_TRUE_TOKENS = frozenset({"true", "1", "yes", "on"})


def get_env_bool(
    new_name: str,
    legacy_name: str | Iterable[str] | None = None,
    default: bool = False,
) -> bool:
    """Convenience wrapper that parses the result of :func:`get_env`
    as a permissive boolean. Returns ``default`` when neither name is
    set; otherwise returns ``True`` iff the value (casefolded,
    stripped) is in ``{"true", "1", "yes", "on"}``.
    """
    raw = get_env(new_name, legacy_name)
    if raw is None:
        return default
    return raw.strip().casefold() in _TRUE_TOKENS
