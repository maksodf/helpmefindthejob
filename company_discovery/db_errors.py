# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 #78 — database-error classification + retry helper.

Implements Layer 1 of the database-error surfacing policy at
``docs/grant/17-database-error-policy.md``. The 5 cases (A-E) +
friendly messages are sourced from the policy; this module is the
shared shoulder of helpers the HTTP layer + repository layer call.
"""

from __future__ import annotations

import functools
import sqlite3
import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")


# ─── Case classification ─────────────────────────────────────────


# Per the policy doc, classify_db_error returns one of these stable
# string codes. Callers map to HTTP status + friendly message via
# the helpers below; tests can pin the exact code so future
# sqlite-version-string churn doesn't break the contract.
ERR_LOCK_BUSY = "db_lock_busy"
ERR_DISK_FULL = "db_disk_full"
ERR_REFERENTIAL_MISSING = "db_referential_missing"
ERR_SCHEMA_DRIFT = "db_schema_drift"
ERR_INTERNAL = "db_internal_error"


def classify_db_error(exc: BaseException) -> str:
    """Map a sqlite exception to one of the five policy codes.

    Returns ``ERR_INTERNAL`` for any exception that isn't a
    recognised sqlite failure (catch-all so the handler always has
    a code to dispatch on).
    """

    if isinstance(exc, sqlite3.IntegrityError):
        return ERR_REFERENTIAL_MISSING
    if isinstance(exc, sqlite3.OperationalError):
        message = str(exc).lower()
        if "database is locked" in message or "database table is locked" in message:
            return ERR_LOCK_BUSY
        if (
            "disk i/o error" in message
            or "disk is full" in message
            or "database or disk is full" in message
            or "no space left on device" in message
        ):
            return ERR_DISK_FULL
        if (
            "no such column" in message
            or "no such table" in message
            or "type mismatch" in message
            or "duplicate column name" in message
        ):
            return ERR_SCHEMA_DRIFT
        # Other OperationalErrors (e.g. corruption, encoding) — treat
        # as internal so the user gets a generic message + the
        # operator gets an alert.
        return ERR_INTERNAL
    if isinstance(exc, sqlite3.Error):
        return ERR_INTERNAL
    return ERR_INTERNAL


# ─── User-facing friendly messages (EN + DE) ─────────────────────


_FRIENDLY_MESSAGES: dict[str, dict[str, str]] = {
    ERR_LOCK_BUSY: {
        "en": "Saving in progress — give us a couple of seconds and try again.",
        "de": "Speichern läuft — bitte einen Moment warten und nochmal versuchen.",
    },
    ERR_DISK_FULL: {
        "en": (
            "Saving is temporarily unavailable on this deployment. "
            "The operator has been alerted. Your work is preserved "
            "in this session — try again in a few minutes, or contact "
            "your deployment admin."
        ),
        "de": (
            "Speichern ist auf dieser Instanz vorübergehend nicht "
            "verfügbar. Der Betreiber wurde benachrichtigt. Deine "
            "Arbeit ist in dieser Sitzung erhalten — versuche es "
            "in ein paar Minuten erneut oder wende dich an den "
            "Administrator."
        ),
    },
    ERR_REFERENTIAL_MISSING: {
        "en": "That record no longer exists. Refresh the page and try again.",
        "de": "Dieser Eintrag existiert nicht mehr. Bitte Seite neu laden und erneut versuchen.",
    },
    ERR_SCHEMA_DRIFT: {
        "en": "Something went wrong on the server. The operator has been alerted.",
        "de": "Ein Serverfehler ist aufgetreten. Der Betreiber wurde benachrichtigt.",
    },
    ERR_INTERNAL: {
        "en": "Something went wrong on the server. The operator has been alerted.",
        "de": "Ein Serverfehler ist aufgetreten. Der Betreiber wurde benachrichtigt.",
    },
}


def format_user_message(error_code: str, locale: str = "en") -> str:
    """Return the friendly user-facing message for an error code in
    the given locale. Falls back to ``en`` for unknown locales and
    to a generic message for unknown codes."""

    bundle = _FRIENDLY_MESSAGES.get(error_code, _FRIENDLY_MESSAGES[ERR_INTERNAL])
    return bundle.get(locale, bundle.get("en", ""))


# ─── HTTP status mapping ─────────────────────────────────────────


_HTTP_STATUS: dict[str, int] = {
    ERR_LOCK_BUSY: 503,
    ERR_DISK_FULL: 507,
    ERR_REFERENTIAL_MISSING: 409,
    ERR_SCHEMA_DRIFT: 500,
    ERR_INTERNAL: 500,
}


def http_status_for(error_code: str) -> int:
    """Return the HTTP status code for a policy error code. Defaults
    to 500 for unknown codes."""

    return _HTTP_STATUS.get(error_code, 500)


# ─── Case A retry helper ─────────────────────────────────────────


def retry_on_lock(
    attempts: int = 3,
    backoff_ms: tuple[int, ...] = (50, 200, 500),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator: retry the wrapped function on
    ``sqlite3.OperationalError: database is locked`` up to
    ``attempts`` times with the given backoff sequence (milliseconds).

    Non-lock OperationalErrors raise immediately (Case B / D / E
    handling lives at the HTTP layer). Backoff is naive sleep —
    the project is sync (BaseHTTPRequestHandler + ThreadingHTTPServer)
    so blocking is fine.

    Usage::

        @retry_on_lock()
        def write_user_profile(...):
            ...

        @retry_on_lock(attempts=5, backoff_ms=(10, 50, 200, 500, 1000))
        def critical_write(...):
            ...
    """

    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: BaseException | None = None
            for attempt_idx in range(attempts):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as exc:
                    if classify_db_error(exc) != ERR_LOCK_BUSY:
                        # Not a lock — re-raise immediately
                        raise
                    last_exc = exc
                    if attempt_idx + 1 < attempts:
                        idx = min(attempt_idx, len(backoff_ms) - 1)
                        delay = backoff_ms[idx] / 1000.0
                        time.sleep(delay)
            # Exhausted attempts — re-raise the last lock exception
            assert last_exc is not None  # noqa: S101 - invariant; the loop only sets last_exc on OperationalError
            raise last_exc

        return wrapper

    return decorator


# ─── Admin alert emission ────────────────────────────────────────


def emit_admin_alert(error_code: str, detail: str) -> None:
    """Emit a system_event admin alert for Case B / D failures.
    Best-effort — failures here never break the calling write site."""

    try:
        from company_discovery import audit_log

        # Map policy codes to audit-log system_event_kind. Codes are
        # operator-facing; the underlying detail is what an admin needs
        # to actually fix the deployment.
        kind_map = {
            ERR_DISK_FULL: "db_disk_full",
            ERR_SCHEMA_DRIFT: "db_schema_drift",
        }
        kind = kind_map.get(error_code)
        if not kind:
            return  # Other cases don't admin-alert
        audit_log.emit_system_event(
            system_event_kind=kind,
        )
    except Exception:  # noqa: BLE001 - admin-alert is best-effort; failure must not break the caller
        # Logged via the emitter's own stderr fallback channel;
        # never reraise.
        return
