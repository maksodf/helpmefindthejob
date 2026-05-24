# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Environment-variable helpers.

Thin wrappers over :mod:`os.environ` with ``int`` + ``bool`` coercion.

After Phase 3 (Decision 22 closeout 2026-05-22), the legacy
``COMPANY_DISCOVERY_*`` and ``DIRECTJOB_*`` prefixes are no longer
accepted. The module name ``env_compat`` is retained for import
stability; the compat shim itself is gone. Every env-var read in
the codebase routes through here so coercion stays uniform.

The module name is kept (instead of e.g. ``env_helpers``) so callers
do not need a sweeping import rewrite. The migration guidance for
operators with a pre-Decision-22 ``.env`` is in
``docs/deployment-recipe.md`` under "Migrating an existing
deployment".
"""

from __future__ import annotations

import os
from typing import Optional, overload

_TRUE_TOKENS = frozenset({"true", "1", "yes", "on"})


@overload
def get_env(name: str, default: str) -> str: ...
@overload
def get_env(name: str, default: None = ...) -> Optional[str]: ...
@overload
def get_env(name: str) -> Optional[str]: ...
def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Return the env var ``name`` or ``default`` if unset.

    Empty string counts as set (returned as-is). This mirrors
    :func:`os.environ.get` and is intentional — some env vars
    (e.g. proxy URLs) accept an empty string as "explicitly off".

    Overloads narrow the return type when a ``str`` default is
    supplied (return is ``str``) vs. when no default is supplied
    (return is ``Optional[str]``). This lets strict-checked callers
    avoid ``cast`` / ``assert`` boilerplate at common sites.
    """
    return os.environ.get(name, default)


def get_env_int(name: str, default: int = 0) -> int:
    """Return the env var ``name`` parsed as ``int``.

    Returns ``default`` if the var is unset, empty, or fails to
    parse. The fall-through-to-default behaviour matches the
    pre-Phase-3 shim so call sites do not need to add try/except.
    """
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return default


def get_env_bool(name: str, default: bool = False) -> bool:
    """Return the env var ``name`` parsed as a permissive bool.

    Returns ``default`` when the var is unset. When set, returns
    ``True`` iff the value (casefolded, stripped) is in
    ``{"true", "1", "yes", "on"}``; otherwise ``False``.

    This permissive set was the fix for the PART 6 bug where an
    operator setting ``HELPMEFINDTHEJOB_ALLOW_REGISTRATION=1``
    silently fell through the strict ``== "true"`` check.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().casefold() in _TRUE_TOKENS
