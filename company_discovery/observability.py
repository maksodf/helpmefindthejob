# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Observability substrate (phase2-backlog #17).

Three opt-in surfaces, all gated by env vars so the project ships
zero third-party dependencies in the default build:

1. **Error reporter** — ``report_error(exc, context)`` dispatches
   to a configured backend (Sentry / log-only / no-op).
   Activated by ``HELPMEFINDTHEJOB_SENTRY_DSN``.

2. **Product event emitter** — ``emit_event(name, properties)``
   for funnel + UX analytics. PostHog-compatible payload shape.
   Activated by ``HELPMEFINDTHEJOB_POSTHOG_KEY``. Properties go
   through a PII sanitiser before dispatch.

3. **Prometheus-style metrics** — ``inc(name, labels)``,
   ``observe(name, value, labels)``, ``set_gauge(name, value,
   labels)``. The /api/metrics endpoint renders these in
   Prometheus exposition format for Grafana / Prometheus scraping.
   Always active (in-memory; zero overhead when not scraped).

Doctrinal constraints honoured:

- **No new runtime dependencies**: substrate is pure stdlib.
  Sentry / PostHog HTTP backends are activated only when the
  operator has explicitly installed those clients AND set the
  env vars.
- **No PII leakage**: events + error contexts pass through
  ``_sanitise_for_telemetry`` which drops common PII keys
  (email / cv_text / password / token / authorization).
- **Honest fallback**: when a backend isn't configured the
  function is a no-op + returns False (never raises).
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Env-var gates
# ---------------------------------------------------------------------------


def _env(key_new: str, key_legacy: str = "") -> str:
    """Look up env var with the canonical new name first, then the
    legacy DirectJob prefix as a fallback."""

    value = os.environ.get(key_new, "").strip()
    if value:
        return value
    if key_legacy:
        return os.environ.get(key_legacy, "").strip()
    return ""


def sentry_dsn() -> str:
    return _env("HELPMEFINDTHEJOB_SENTRY_DSN", "DIRECTJOB_SENTRY_DSN")


def posthog_key() -> str:
    return _env("HELPMEFINDTHEJOB_POSTHOG_KEY", "DIRECTJOB_POSTHOG_KEY")


def posthog_host() -> str:
    return _env(
        "HELPMEFINDTHEJOB_POSTHOG_HOST", "DIRECTJOB_POSTHOG_HOST"
    ) or "https://eu.posthog.com"


# ---------------------------------------------------------------------------
# PII sanitiser
# ---------------------------------------------------------------------------


# Property keys that frequently carry PII. Values are dropped /
# replaced with ``"<redacted>"`` before dispatch to any external
# backend. Conservative list — extend when new sensitive fields
# appear in event payloads.
_PII_KEYS: frozenset[str] = frozenset({
    "email", "email_address", "cv_text", "cv", "cvText",
    "password", "password_hash", "token", "authorization",
    "auth", "session_token", "api_key", "apikey",
    "phone", "phone_number", "address", "name", "full_name",
    "first_name", "last_name", "given_name", "surname",
    "ssn", "passport", "national_id",
})


def _sanitise_for_telemetry(value: Any) -> Any:
    """Recursively walk a dict / list and replace PII values with
    ``"<redacted>"``. Non-dict / non-list values pass through. Keys
    matched case-insensitively against ``_PII_KEYS``.

    Strings longer than 1000 chars are truncated to the first 1000
    + "<...truncated>" suffix — telemetry should never carry
    full CV text or chat transcripts.
    """

    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if str(k).lower() in _PII_KEYS:
                out[k] = "<redacted>"
            else:
                out[k] = _sanitise_for_telemetry(v)
        return out
    if isinstance(value, (list, tuple)):
        return [_sanitise_for_telemetry(v) for v in value]
    if isinstance(value, str) and len(value) > 1000:
        return value[:1000] + "<...truncated>"
    return value


# ---------------------------------------------------------------------------
# Error reporter
# ---------------------------------------------------------------------------


def report_error(
    exc: BaseException,
    *,
    context: dict[str, Any] | None = None,
    severity: str = "error",
) -> bool:
    """Dispatch an exception to the configured error backend.

    Returns True if the report was attempted, False if no backend
    was configured. Never raises — error reporting must not
    introduce errors.

    Backend resolution:
    - If ``HELPMEFINDTHEJOB_SENTRY_DSN`` is set AND the
      ``sentry-sdk`` library is importable, dispatches via Sentry.
    - Otherwise: no-op + returns False.

    The Sentry path is wrapped in a broad try/except so a
    misconfigured DSN or network failure doesn't break the calling
    request.
    """

    dsn = sentry_dsn()
    if not dsn:
        return False
    try:
        import sentry_sdk  # type: ignore[import-not-found]
    except ImportError:
        return False
    try:
        # Lazy init — only run once per process
        if not getattr(sentry_sdk, "_helpme_initialized", False):
            sentry_sdk.init(dsn=dsn, traces_sample_rate=0.0)
            setattr(sentry_sdk, "_helpme_initialized", True)
        if context:
            with sentry_sdk.push_scope() as scope:
                for k, v in _sanitise_for_telemetry(context).items():
                    scope.set_tag(str(k)[:32], str(v)[:200])
                scope.set_level(severity)
                sentry_sdk.capture_exception(exc)
        else:
            sentry_sdk.capture_exception(exc)
        return True
    except Exception:  # noqa: BLE001 - error reporting must never re-raise
        return False


# ---------------------------------------------------------------------------
# Product event emitter
# ---------------------------------------------------------------------------


def emit_event(
    name: str,
    *,
    properties: dict[str, Any] | None = None,
    distinct_id: str = "anonymous",
) -> bool:
    """Dispatch a product event to the configured analytics backend.

    Returns True if dispatched, False if no backend configured.
    Never raises. PII is stripped from ``properties`` before
    sending.

    Backend resolution:
    - If ``HELPMEFINDTHEJOB_POSTHOG_KEY`` is set, dispatches via
      PostHog's capture endpoint over plain HTTPS (no SDK
      dependency).
    - Otherwise: no-op + returns False.

    ``distinct_id`` should already be the HMAC-hashed form of the
    user_id (see ``audit_log._hash_user_id``); raw user IDs MUST
    NOT be passed here.
    """

    key = posthog_key()
    if not key:
        return False
    sanitised_props = _sanitise_for_telemetry(properties or {})
    payload = {
        "api_key": key,
        "event": name,
        "properties": {
            **sanitised_props,
            "$lib": "helpmefindthejob/observability",
            "$lib_version": "0.1.0",
        },
        "distinct_id": distinct_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        host = posthog_host().rstrip("/")
        url = f"{host}/capture/"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # 1s timeout — analytics must not slow the request path
        urllib.request.urlopen(req, timeout=1.0).close()
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Prometheus-style metrics — in-memory, scraped via /api/metrics
# ---------------------------------------------------------------------------


@dataclass
class _Metric:
    name: str
    kind: str  # "counter" / "gauge" / "histogram"
    help_text: str = ""
    # For counter / gauge: labels -> float value
    # For histogram: labels -> (sum, count, bucket_counts dict)
    values: dict[tuple[tuple[str, str], ...], Any] = field(default_factory=dict)


# Default histogram buckets (seconds). Standard Prometheus bucket
# layout; covers low-ms responses through long-running AI calls.
_DEFAULT_HISTOGRAM_BUCKETS: tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0,
)


class _MetricsRegistry:
    """Process-local metrics registry. Thread-safe."""

    def __init__(self) -> None:
        self._metrics: dict[str, _Metric] = {}
        self._lock = threading.Lock()

    def _ensure(self, name: str, kind: str, help_text: str = "") -> _Metric:
        with self._lock:
            existing = self._metrics.get(name)
            if existing is None:
                m = _Metric(name=name, kind=kind, help_text=help_text)
                self._metrics[name] = m
                return m
            if existing.kind != kind:
                raise ValueError(
                    f"metric {name!r} already registered as "
                    f"{existing.kind!r}, cannot re-register as {kind!r}"
                )
            return existing

    def inc(
        self,
        name: str,
        *,
        labels: dict[str, str] | None = None,
        value: float = 1.0,
        help_text: str = "",
    ) -> None:
        m = self._ensure(name, "counter", help_text=help_text)
        key = tuple(sorted((labels or {}).items()))
        with self._lock:
            m.values[key] = m.values.get(key, 0.0) + float(value)

    def set_gauge(
        self,
        name: str,
        value: float,
        *,
        labels: dict[str, str] | None = None,
        help_text: str = "",
    ) -> None:
        m = self._ensure(name, "gauge", help_text=help_text)
        key = tuple(sorted((labels or {}).items()))
        with self._lock:
            m.values[key] = float(value)

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: dict[str, str] | None = None,
        help_text: str = "",
        buckets: tuple[float, ...] = _DEFAULT_HISTOGRAM_BUCKETS,
    ) -> None:
        m = self._ensure(name, "histogram", help_text=help_text)
        key = tuple(sorted((labels or {}).items()))
        with self._lock:
            stats = m.values.get(key)
            if stats is None:
                stats = {"sum": 0.0, "count": 0, "buckets": {b: 0 for b in buckets}}
                m.values[key] = stats
            stats["sum"] += float(value)
            stats["count"] += 1
            for b in buckets:
                if value <= b:
                    stats["buckets"][b] += 1

    def prometheus_text(self) -> str:
        """Render the registry in Prometheus exposition format
        (`text/plain; version=0.0.4`)."""

        lines: list[str] = []
        with self._lock:
            for name, metric in sorted(self._metrics.items()):
                if metric.help_text:
                    lines.append(f"# HELP {name} {metric.help_text}")
                lines.append(f"# TYPE {name} {metric.kind}")
                if metric.kind in ("counter", "gauge"):
                    for label_key, value in sorted(metric.values.items()):
                        label_str = _labels_to_prom(label_key)
                        lines.append(f"{name}{label_str} {value}")
                elif metric.kind == "histogram":
                    for label_key, stats in sorted(metric.values.items()):
                        label_str_base = list(label_key)
                        for bucket, count in sorted(stats["buckets"].items()):
                            bucket_labels = label_str_base + [("le", str(bucket))]
                            lines.append(
                                f"{name}_bucket{_labels_to_prom(tuple(bucket_labels))} {count}"
                            )
                        # +Inf bucket = count of all
                        plus_inf_labels = label_str_base + [("le", "+Inf")]
                        lines.append(
                            f"{name}_bucket{_labels_to_prom(tuple(plus_inf_labels))} {stats['count']}"
                        )
                        lines.append(
                            f"{name}_sum{_labels_to_prom(tuple(label_str_base))} {stats['sum']}"
                        )
                        lines.append(
                            f"{name}_count{_labels_to_prom(tuple(label_str_base))} {stats['count']}"
                        )
        return "\n".join(lines) + "\n"

    def reset_for_test(self) -> None:
        with self._lock:
            self._metrics.clear()


def _labels_to_prom(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    parts = [f'{k}="{_escape_label(v)}"' for k, v in labels]
    return "{" + ",".join(parts) + "}"


def _escape_label(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


# Module-level singleton — process-local
_REGISTRY = _MetricsRegistry()


def inc(name: str, *, labels: dict[str, str] | None = None, value: float = 1.0, help_text: str = "") -> None:
    """Increment a counter metric. Creates the counter if it doesn't
    exist yet."""

    _REGISTRY.inc(name, labels=labels, value=value, help_text=help_text)


def set_gauge(name: str, value: float, *, labels: dict[str, str] | None = None, help_text: str = "") -> None:
    """Set a gauge metric to a specific value."""

    _REGISTRY.set_gauge(name, value, labels=labels, help_text=help_text)


def observe(name: str, value: float, *, labels: dict[str, str] | None = None, help_text: str = "") -> None:
    """Record an observation against a histogram metric."""

    _REGISTRY.observe(name, value, labels=labels, help_text=help_text)


def prometheus_text() -> str:
    """Return the metrics registry in Prometheus exposition
    format for the /api/metrics scrape endpoint."""

    return _REGISTRY.prometheus_text()


def _reset_registry_for_test() -> None:
    """Test-only: clear the metrics registry. Never call from
    production code."""

    _REGISTRY.reset_for_test()
