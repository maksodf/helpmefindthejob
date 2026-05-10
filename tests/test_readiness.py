"""Unit tests for the production-readiness builder.

The builder is a pure function over environment variables + a few file
paths. Tests poke env vars, build a report, and assert the right
status / detail per signal.
"""

from __future__ import annotations

import os
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.readiness import build_report


_VARS = (
    "DIRECTJOB_EMAIL_BACKEND",
    "DIRECTJOB_PUBLIC_URL",
    "DIRECTJOB_SMTP_HOST",
    "DIRECTJOB_SMTP_PORT",
    "DIRECTJOB_SMTP_USERNAME",
    "DIRECTJOB_SMTP_PASSWORD",
    "DIRECTJOB_EMAIL_FROM",
    "DIRECTJOB_BACKUP_BACKEND",
    "DIRECTJOB_BACKUP_REMOTE",
    "DIRECTJOB_MONITORING_URL",
    "DIRECTJOB_LOG_TARGET",
    "DIRECTJOB_LEGAL_REVIEWED",
    "DIRECTJOB_READINESS_ALLOW_UNINITIALIZED_RUNTIME",
    "DIRECTJOB_BILLING_BACKEND",
    "DIRECTJOB_STRIPE_API_KEY",
    "DIRECTJOB_STRIPE_PRICE_TEAM",
    "DIRECTJOB_STRIPE_PRICE_ORG",
)


@contextmanager
def env(**overrides):
    """Temporarily replace the readiness env vars; restore on exit."""
    saved = {key: os.environ.get(key) for key in _VARS}
    try:
        for key in _VARS:
            os.environ.pop(key, None)
        for key, value in overrides.items():
            if value is not None:
                os.environ[key] = value
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _signal(report, signal_id):
    for signal in report.signals:
        if signal.id == signal_id:
            return signal
    raise AssertionError(f"no such signal: {signal_id}")


class ReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data_dir = Path(self.tmp.name)

    def _build(self):
        return build_report(
            app_version="0.4.0",
            environment="production",
            data_dir=self.data_dir,
            audit_path=self.data_dir / "admin_audit.log",
            scheduler_path=self.data_dir / "scheduler.sqlite3",
            active_scheduler_jobs=0,
        )

    def test_console_email_is_partial(self) -> None:
        with env(DIRECTJOB_EMAIL_BACKEND="console", DIRECTJOB_PUBLIC_URL="https://example.org"):
            report = self._build()
        signal = _signal(report, "email")
        self.assertEqual(signal.status, "partial")
        self.assertEqual(signal.detail["backend"], "console")

    def test_smtp_partial_lists_missing_fields(self) -> None:
        with env(
            DIRECTJOB_EMAIL_BACKEND="smtp",
            DIRECTJOB_SMTP_HOST="smtp.example.org",
            DIRECTJOB_SMTP_PORT="587",
            DIRECTJOB_SMTP_USERNAME="user",
            DIRECTJOB_PUBLIC_URL="https://example.org",
        ):
            report = self._build()
        signal = _signal(report, "email")
        self.assertEqual(signal.status, "partial")
        self.assertIn("DIRECTJOB_SMTP_PASSWORD", signal.detail["missingFields"])

    def test_smtp_complete_is_ok(self) -> None:
        with env(
            DIRECTJOB_EMAIL_BACKEND="smtp",
            DIRECTJOB_SMTP_HOST="smtp.example.org",
            DIRECTJOB_SMTP_PORT="587",
            DIRECTJOB_SMTP_USERNAME="user",
            DIRECTJOB_SMTP_PASSWORD="pw",
            DIRECTJOB_EMAIL_FROM="bot@example.org",
            DIRECTJOB_PUBLIC_URL="https://example.org",
        ):
            report = self._build()
        signal = _signal(report, "email")
        self.assertEqual(signal.status, "ok")
        self.assertNotIn("password", str(signal.detail).lower())

    def test_backup_local_is_partial(self) -> None:
        with env(DIRECTJOB_BACKUP_BACKEND="local"):
            report = self._build()
        self.assertEqual(_signal(report, "backups").status, "partial")

    def test_backup_offhost_without_remote_is_partial(self) -> None:
        with env(DIRECTJOB_BACKUP_BACKEND="rclone"):
            report = self._build()
        self.assertEqual(_signal(report, "backups").status, "partial")

    def test_backup_offhost_with_remote_is_ok(self) -> None:
        with env(DIRECTJOB_BACKUP_BACKEND="rclone", DIRECTJOB_BACKUP_REMOTE="remote:bucket/dj"):
            report = self._build()
        self.assertEqual(_signal(report, "backups").status, "ok")

    def test_monitoring_signal(self) -> None:
        with env():
            self.assertEqual(_signal(self._build(), "monitoring").status, "missing")
        with env(DIRECTJOB_MONITORING_URL="https://uptime.example"):
            self.assertEqual(_signal(self._build(), "monitoring").status, "partial")
        with env(DIRECTJOB_MONITORING_URL="https://uptime.example", DIRECTJOB_LOG_TARGET="loki"):
            self.assertEqual(_signal(self._build(), "monitoring").status, "ok")

    def test_legal_signal_uses_env_flag(self) -> None:
        with env():
            self.assertEqual(_signal(self._build(), "legal").status, "partial")
        with env(DIRECTJOB_LEGAL_REVIEWED="true"):
            self.assertEqual(_signal(self._build(), "legal").status, "ok")

    def test_billing_manual_is_partial_stripe_complete_is_ok(self) -> None:
        with env(DIRECTJOB_BILLING_BACKEND="manual"):
            self.assertEqual(_signal(self._build(), "billing").status, "partial")
        with env(
            DIRECTJOB_BILLING_BACKEND="stripe",
            DIRECTJOB_STRIPE_API_KEY="sk_test",
            DIRECTJOB_STRIPE_PRICE_TEAM="price_team",
        ):
            self.assertEqual(_signal(self._build(), "billing").status, "ok")

    def test_overall_status_aggregation(self) -> None:
        with env(DIRECTJOB_PUBLIC_URL="https://example.org"):
            report = self._build()
        self.assertEqual(report.overall_status, "missing")  # monitoring missing
        with env(
            DIRECTJOB_PUBLIC_URL="https://example.org",
            DIRECTJOB_EMAIL_BACKEND="smtp",
            DIRECTJOB_SMTP_HOST="smtp.example.org",
            DIRECTJOB_SMTP_PORT="587",
            DIRECTJOB_SMTP_USERNAME="user",
            DIRECTJOB_SMTP_PASSWORD="pw",
            DIRECTJOB_EMAIL_FROM="bot@example.org",
            DIRECTJOB_BACKUP_BACKEND="rclone",
            DIRECTJOB_BACKUP_REMOTE="remote:bucket",
            DIRECTJOB_MONITORING_URL="https://uptime.example",
            DIRECTJOB_LOG_TARGET="loki",
            DIRECTJOB_LEGAL_REVIEWED="true",
            DIRECTJOB_BILLING_BACKEND="stripe",
            DIRECTJOB_STRIPE_API_KEY="sk_test",
            DIRECTJOB_STRIPE_PRICE_TEAM="price_team",
        ):
            report = self._build()
        # admin_audit is partial until the file exists; create it then re-check
        (self.data_dir / "admin_audit.log").write_text("{}\n")
        (self.data_dir / "scheduler.sqlite3").write_text("")
        with env(
            DIRECTJOB_PUBLIC_URL="https://example.org",
            DIRECTJOB_EMAIL_BACKEND="smtp",
            DIRECTJOB_SMTP_HOST="smtp.example.org",
            DIRECTJOB_SMTP_PORT="587",
            DIRECTJOB_SMTP_USERNAME="user",
            DIRECTJOB_SMTP_PASSWORD="pw",
            DIRECTJOB_EMAIL_FROM="bot@example.org",
            DIRECTJOB_BACKUP_BACKEND="rclone",
            DIRECTJOB_BACKUP_REMOTE="remote:bucket",
            DIRECTJOB_MONITORING_URL="https://uptime.example",
            DIRECTJOB_LOG_TARGET="loki",
            DIRECTJOB_LEGAL_REVIEWED="true",
            DIRECTJOB_BILLING_BACKEND="stripe",
            DIRECTJOB_STRIPE_API_KEY="sk_test",
            DIRECTJOB_STRIPE_PRICE_TEAM="price_team",
        ):
            report = self._build()
        self.assertEqual(report.overall_status, "ok")

    def test_uninitialized_runtime_can_be_allowed_for_preflight(self) -> None:
        with env(DIRECTJOB_READINESS_ALLOW_UNINITIALIZED_RUNTIME="true"):
            report = self._build()
        self.assertEqual(_signal(report, "scheduler").status, "ok")
        self.assertEqual(_signal(report, "admin_audit").status, "ok")


if __name__ == "__main__":
    unittest.main()
