# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Production readiness summary.

Exposes a pure function and an HTTP-layer payload builder that grade
*configuration* — never secrets — across the dimensions the operator
cares about for a sellable launch.

Each signal returns a status of:

- ``ok`` — configured and active
- ``partial`` — usable but not production-grade (e.g. console email, manual billing)
- ``missing`` — unconfigured or external blocker
- ``unknown`` — unable to determine without running side effects

The builder is read-only and safe to expose to admins.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from company_discovery.env_compat import get_env

READINESS_LEVELS = ("ok", "partial", "missing", "unknown")
TRUE_VALUES = {"yes", "true", "1"}


@dataclass
class ReadinessSignal:
    id: str
    label: str
    status: str
    summary: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReadinessReport:
    generated_at: str
    environment: str
    app_version: str
    overall_status: str
    blockers: list[str]
    signals: list[ReadinessSignal]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generatedAt": self.generated_at,
            "environment": self.environment,
            "appVersion": self.app_version,
            "overallStatus": self.overall_status,
            "blockers": list(self.blockers),
            "signals": [asdict(signal) for signal in self.signals],
        }


def _redact_email_backend() -> ReadinessSignal:
    backend = (
        (get_env("HELPMEFINDTHEJOB_EMAIL_BACKEND") or "console")
        .strip()
        .casefold()
    )
    public_url = (get_env("HELPMEFINDTHEJOB_PUBLIC_URL") or "").strip()
    if backend == "smtp":
        host = get_env("HELPMEFINDTHEJOB_SMTP_HOST", "")
        port = get_env("HELPMEFINDTHEJOB_SMTP_PORT", "")
        username = bool(get_env("HELPMEFINDTHEJOB_SMTP_USERNAME"))
        password_present = bool(
            get_env("HELPMEFINDTHEJOB_SMTP_PASSWORD")
        )
        from_address_present = bool(get_env("HELPMEFINDTHEJOB_EMAIL_FROM"))
        missing: list[str] = []
        if not host:
            missing.append("HELPMEFINDTHEJOB_SMTP_HOST")
        if not port:
            missing.append("HELPMEFINDTHEJOB_SMTP_PORT")
        if not password_present:
            missing.append("HELPMEFINDTHEJOB_SMTP_PASSWORD")
        if missing:
            return ReadinessSignal(
                id="email",
                label="Email (SMTP, incomplete)",
                status="partial",
                summary=("SMTP backend selected but missing: " + ", ".join(missing) + "."),
                detail={
                    "backend": "smtp",
                    "host": host or None,
                    "port": port or None,
                    "hasUsername": username,
                    "hasPassword": password_present,
                    "hasFromAddress": from_address_present,
                    "publicUrl": public_url or None,
                    "missingFields": missing,
                },
            )
        return ReadinessSignal(
            id="email",
            label="Email (SMTP configured)",
            status="ok",
            summary=f"SMTP via {host}:{port}. Real invitations and reset emails are delivered.",
            detail={
                "backend": "smtp",
                "host": host,
                "port": port,
                "hasUsername": username,
                "hasFromAddress": from_address_present,
                "publicUrl": public_url or None,
            },
        )
    return ReadinessSignal(
        id="email",
        label="Email (console only)",
        status="partial",
        summary="ConsoleTransport active. Invites and reset links are written to data/email_outbox.log; no real email is sent.",
        detail={"backend": "console", "publicUrl": public_url or None},
    )


def _public_url_signal() -> ReadinessSignal:
    public_url = (get_env("HELPMEFINDTHEJOB_PUBLIC_URL") or "").strip()
    if not public_url:
        return ReadinessSignal(
            id="public_url",
            label="Public URL",
            status="missing",
            summary="HELPMEFINDTHEJOB_PUBLIC_URL is not set; invitation and reset links use relative paths.",
        )
    if not (public_url.startswith("http://") or public_url.startswith("https://")):
        return ReadinessSignal(
            id="public_url",
            label="Public URL",
            status="partial",
            summary="HELPMEFINDTHEJOB_PUBLIC_URL is set but does not start with http/https.",
            detail={"value": public_url},
        )
    if public_url.startswith("http://"):
        return ReadinessSignal(
            id="public_url",
            label="Public URL",
            status="partial",
            summary="HELPMEFINDTHEJOB_PUBLIC_URL uses http; production should use https.",
            detail={"value": public_url},
        )
    return ReadinessSignal(
        id="public_url",
        label="Public URL",
        status="ok",
        summary="HTTPS public URL configured.",
        detail={"value": public_url},
    )


def _backup_signal(*, data_dir: Path) -> ReadinessSignal:
    backend = (
        (get_env("HELPMEFINDTHEJOB_BACKUP_BACKEND") or "local")
        .strip()
        .casefold()
    )
    backup_dir = (os.environ.get("BACKUP_DIR") or "./backups").strip()
    retention = (os.environ.get("BACKUP_RETENTION_DAYS") or "30").strip()
    detail = {"backend": backend, "directory": backup_dir, "retentionDays": retention}
    if backend in {"rclone", "s3", "aws"}:
        target = get_env("HELPMEFINDTHEJOB_BACKUP_REMOTE", "")
        detail["remote"] = target or None
        if not target:
            return ReadinessSignal(
                id="backups",
                label="Backups",
                status="partial",
                summary=f"Off-host backend selected ({backend}) but HELPMEFINDTHEJOB_BACKUP_REMOTE is empty.",
                detail=detail,
            )
        return ReadinessSignal(
            id="backups",
            label="Backups",
            status="ok",
            summary=f"Off-host backups via {backend} → {target}.",
            detail=detail,
        )
    backups_path = Path(backup_dir).resolve()
    detail["resolvedDirectory"] = str(backups_path)
    return ReadinessSignal(
        id="backups",
        label="Backups (local only)",
        status="partial",
        summary="Local backups only. Configure off-host upload before the first production rollout.",
        detail=detail,
    )


def _monitoring_signal() -> ReadinessSignal:
    domain = (get_env("HELPMEFINDTHEJOB_DOMAIN") or "").strip()
    monitor_url = (
        get_env("HELPMEFINDTHEJOB_MONITORING_URL") or ""
    ).strip()
    log_target = (get_env("HELPMEFINDTHEJOB_LOG_TARGET") or "").strip()
    detail = {
        "monitoringUrl": monitor_url or None,
        "logTarget": log_target or None,
        "domain": domain or None,
    }
    if monitor_url and log_target:
        return ReadinessSignal(
            id="monitoring",
            label="Monitoring + log shipping",
            status="ok",
            summary="Uptime + log targets configured.",
            detail=detail,
        )
    if monitor_url or log_target:
        return ReadinessSignal(
            id="monitoring",
            label="Monitoring",
            status="partial",
            summary="Either uptime or log shipping is configured but not both.",
            detail=detail,
        )
    return ReadinessSignal(
        id="monitoring",
        label="Monitoring",
        status="missing",
        summary="No monitoring vendor URL or log target documented in env.",
        detail=detail,
    )


def _billing_signal() -> ReadinessSignal:
    backend = (
        (get_env("HELPMEFINDTHEJOB_BILLING_BACKEND") or "manual")
        .strip()
        .casefold()
    )
    if backend == "stripe":
        api_key = bool(get_env("HELPMEFINDTHEJOB_STRIPE_API_KEY"))
        price_team = bool(
            get_env("HELPMEFINDTHEJOB_STRIPE_PRICE_TEAM")
        )
        price_org = bool(get_env("HELPMEFINDTHEJOB_STRIPE_PRICE_ORG"))
        if api_key and (price_team or price_org):
            return ReadinessSignal(
                id="billing",
                label="Billing (Stripe)",
                status="ok",
                summary="Stripe credentials configured.",
                detail={"hasApiKey": True, "hasPriceTeam": price_team, "hasPriceOrg": price_org},
            )
        return ReadinessSignal(
            id="billing",
            label="Billing (Stripe)",
            status="partial",
            summary="Stripe backend selected; some env vars missing.",
            detail={"hasApiKey": api_key, "hasPriceTeam": price_team, "hasPriceOrg": price_org},
        )
    return ReadinessSignal(
        id="billing",
        label="Billing (Manual)",
        status="partial",
        summary="Manual billing is fine for a pilot. Switch to Stripe before charging customers.",
        detail={"backend": "manual"},
    )


def _legal_signal() -> ReadinessSignal:
    reviewed = (
        (get_env("HELPMEFINDTHEJOB_LEGAL_REVIEWED") or "")
        .strip()
        .casefold()
    )
    if reviewed in TRUE_VALUES:
        return ReadinessSignal(
            id="legal",
            label="Legal review",
            status="ok",
            summary="Legal pages marked as counsel-reviewed (HELPMEFINDTHEJOB_LEGAL_REVIEWED=true).",
        )
    return ReadinessSignal(
        id="legal",
        label="Legal review",
        status="partial",
        summary="Legal pages exist but counsel review is not confirmed via HELPMEFINDTHEJOB_LEGAL_REVIEWED.",
    )


def _allow_uninitialized_runtime() -> bool:
    return (
        get_env(
            "HELPMEFINDTHEJOB_READINESS_ALLOW_UNINITIALIZED_RUNTIME",
        )
        or ""
    ).strip().casefold() in TRUE_VALUES


def _scheduler_signal(*, scheduler_path: Path | None, active_jobs: int | None) -> ReadinessSignal:
    if scheduler_path is None or not scheduler_path.exists():
        if _allow_uninitialized_runtime():
            return ReadinessSignal(
                id="scheduler",
                label="Durable scheduler",
                status="ok",
                summary="Scheduler database is not initialized yet; allowed for preflight-only readiness.",
                detail={"runtimeInitialized": False},
            )
        return ReadinessSignal(
            id="scheduler",
            label="Durable scheduler",
            status="partial",
            summary="Scheduler database not yet initialised. It will be created on first start.",
        )
    return ReadinessSignal(
        id="scheduler",
        label="Durable scheduler",
        status="ok",
        summary=f"Scheduler database active. {active_jobs or 0} enabled job(s).",
        detail={"activeJobs": int(active_jobs or 0)},
    )


def _quota_signal() -> ReadinessSignal:
    keys = (
        "HELPMEFINDTHEJOB_QUOTA_SCANS_PER_DAY",
        "HELPMEFINDTHEJOB_QUOTA_AI_PER_DAY",
        "HELPMEFINDTHEJOB_QUOTA_DOMAIN_PER_HOUR",
        "HELPMEFINDTHEJOB_QUOTA_ACTIVE_SCANS",
    )
    detail = {key: os.environ.get(key) or "default" for key in keys}
    return ReadinessSignal(
        id="quotas",
        label="Quotas + concurrency",
        status="ok",
        summary="Quotas active.",
        detail=detail,
    )


def _admin_audit_signal(*, audit_path: Path | None) -> ReadinessSignal:
    if audit_path is None:
        return ReadinessSignal(
            id="admin_audit",
            label="Admin audit log",
            status="unknown",
            summary="Audit log path not provided to readiness builder.",
        )
    if audit_path.exists():
        size = audit_path.stat().st_size
        return ReadinessSignal(
            id="admin_audit",
            label="Admin audit log",
            status="ok",
            summary=f"Audit log file present ({size} bytes).",
        )
    if _allow_uninitialized_runtime():
        return ReadinessSignal(
            id="admin_audit",
            label="Admin audit log",
            status="ok",
            summary="Audit log is not initialized yet; allowed for preflight-only readiness.",
            detail={"runtimeInitialized": False},
        )
    return ReadinessSignal(
        id="admin_audit",
        label="Admin audit log",
        status="partial",
        summary="Audit log file does not exist yet — it is created on first admin action.",
    )


def _deployment_status_signal(*, environment: str) -> ReadinessSignal:
    if environment == "production":
        return ReadinessSignal(
            id="deployment",
            label="Deployment env",
            status="ok",
            summary="HELPMEFINDTHEJOB_ENV=production.",
        )
    return ReadinessSignal(
        id="deployment",
        label="Deployment env",
        status="partial",
        summary=f"HELPMEFINDTHEJOB_ENV={environment}. Production deployments must set this to 'production'.",
    )


def build_report(
    *,
    app_version: str,
    environment: str,
    data_dir: Path,
    audit_path: Path | None = None,
    scheduler_path: Path | None = None,
    active_scheduler_jobs: int | None = None,
) -> ReadinessReport:
    signals: list[ReadinessSignal] = [
        _deployment_status_signal(environment=environment),
        _public_url_signal(),
        _redact_email_backend(),
        _backup_signal(data_dir=data_dir),
        _monitoring_signal(),
        _billing_signal(),
        _legal_signal(),
        _scheduler_signal(scheduler_path=scheduler_path, active_jobs=active_scheduler_jobs),
        _quota_signal(),
        _admin_audit_signal(audit_path=audit_path),
    ]
    blockers = [signal.id for signal in signals if signal.status in {"missing", "partial"}]
    if any(signal.status == "missing" for signal in signals):
        overall = "missing"
    elif blockers:
        overall = "partial"
    else:
        overall = "ok"
    return ReadinessReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        environment=environment,
        app_version=app_version,
        overall_status=overall,
        blockers=blockers,
        signals=signals,
    )
