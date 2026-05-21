# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 #78 — db_errors helper contract tests.

Covers the 5-case classification + friendly-message lookup + HTTP
status mapping + retry-on-lock decorator. The policy contract lives
at docs/grant/17-database-error-policy.md; this file is the
executable enforcement.
"""

from __future__ import annotations

import sqlite3
import time
import unittest
from unittest.mock import patch

from company_discovery.db_errors import (
    ERR_DISK_FULL,
    ERR_INTERNAL,
    ERR_LOCK_BUSY,
    ERR_REFERENTIAL_MISSING,
    ERR_SCHEMA_DRIFT,
    classify_db_error,
    emit_admin_alert,
    format_user_message,
    http_status_for,
    retry_on_lock,
)


class ClassifyDbErrorTests(unittest.TestCase):
    def test_classifies_lock_busy(self):
        exc = sqlite3.OperationalError("database is locked")
        self.assertEqual(classify_db_error(exc), ERR_LOCK_BUSY)

    def test_classifies_table_lock(self):
        exc = sqlite3.OperationalError("database table is locked")
        self.assertEqual(classify_db_error(exc), ERR_LOCK_BUSY)

    def test_classifies_disk_full(self):
        for msg in (
            "disk I/O error",
            "database or disk is full",
            "no space left on device",
        ):
            self.assertEqual(
                classify_db_error(sqlite3.OperationalError(msg)),
                ERR_DISK_FULL,
                msg=msg,
            )

    def test_classifies_referential_missing(self):
        exc = sqlite3.IntegrityError("FOREIGN KEY constraint failed")
        self.assertEqual(classify_db_error(exc), ERR_REFERENTIAL_MISSING)

    def test_classifies_schema_drift(self):
        for msg in (
            "no such column: foo",
            "no such table: bar",
            "type mismatch",
            "duplicate column name: x",
        ):
            self.assertEqual(
                classify_db_error(sqlite3.OperationalError(msg)),
                ERR_SCHEMA_DRIFT,
                msg=msg,
            )

    def test_unknown_operational_error_falls_back_to_internal(self):
        exc = sqlite3.OperationalError("something weird happened")
        self.assertEqual(classify_db_error(exc), ERR_INTERNAL)

    def test_non_sqlite_exception_falls_back_to_internal(self):
        exc = ValueError("not a db error")
        self.assertEqual(classify_db_error(exc), ERR_INTERNAL)

    def test_case_insensitive_message_matching(self):
        exc = sqlite3.OperationalError("DATABASE IS LOCKED")
        self.assertEqual(classify_db_error(exc), ERR_LOCK_BUSY)


class FormatUserMessageTests(unittest.TestCase):
    def test_lock_busy_message_en(self):
        msg = format_user_message(ERR_LOCK_BUSY, locale="en")
        self.assertIn("try again", msg.lower())

    def test_lock_busy_message_de(self):
        msg = format_user_message(ERR_LOCK_BUSY, locale="de")
        self.assertIn("speichern läuft", msg.lower())

    def test_disk_full_message_de(self):
        msg = format_user_message(ERR_DISK_FULL, locale="de")
        self.assertIn("administrator", msg.lower())

    def test_referential_missing_message_en(self):
        msg = format_user_message(ERR_REFERENTIAL_MISSING, locale="en")
        self.assertIn("no longer exists", msg.lower())

    def test_unknown_code_returns_generic_message(self):
        msg = format_user_message("totally-bogus-code", locale="en")
        self.assertIn("something went wrong", msg.lower())

    def test_unknown_locale_falls_back_to_english(self):
        msg = format_user_message(ERR_LOCK_BUSY, locale="fr")
        # English message has "try again" substring
        self.assertIn("try again", msg.lower())


class HttpStatusTests(unittest.TestCase):
    def test_lock_busy_returns_503(self):
        self.assertEqual(http_status_for(ERR_LOCK_BUSY), 503)

    def test_disk_full_returns_507(self):
        self.assertEqual(http_status_for(ERR_DISK_FULL), 507)

    def test_referential_missing_returns_409(self):
        self.assertEqual(http_status_for(ERR_REFERENTIAL_MISSING), 409)

    def test_schema_drift_returns_500(self):
        self.assertEqual(http_status_for(ERR_SCHEMA_DRIFT), 500)

    def test_internal_returns_500(self):
        self.assertEqual(http_status_for(ERR_INTERNAL), 500)

    def test_unknown_code_defaults_to_500(self):
        self.assertEqual(http_status_for("totally-bogus"), 500)


class RetryOnLockTests(unittest.TestCase):
    def test_succeeds_first_attempt_when_no_lock(self):
        calls = []

        @retry_on_lock(attempts=3, backoff_ms=(1, 1, 1))
        def write():
            calls.append("call")
            return "ok"

        self.assertEqual(write(), "ok")
        self.assertEqual(len(calls), 1)

    def test_retries_on_lock_then_succeeds(self):
        calls = []

        @retry_on_lock(attempts=3, backoff_ms=(1, 1, 1))
        def flaky_write():
            calls.append("call")
            if len(calls) < 3:
                raise sqlite3.OperationalError("database is locked")
            return "ok"

        result = flaky_write()
        self.assertEqual(result, "ok")
        self.assertEqual(len(calls), 3)

    def test_exhausts_attempts_then_re_raises(self):
        calls = []

        @retry_on_lock(attempts=2, backoff_ms=(1, 1))
        def perpetually_locked():
            calls.append("call")
            raise sqlite3.OperationalError("database is locked")

        with self.assertRaises(sqlite3.OperationalError):
            perpetually_locked()
        self.assertEqual(len(calls), 2)

    def test_non_lock_error_does_not_retry(self):
        calls = []

        @retry_on_lock(attempts=3, backoff_ms=(1, 1, 1))
        def schema_drift():
            calls.append("call")
            raise sqlite3.OperationalError("no such table: foo")

        with self.assertRaises(sqlite3.OperationalError):
            schema_drift()
        # Only one call — non-lock errors don't retry
        self.assertEqual(len(calls), 1)

    def test_integrity_error_does_not_retry(self):
        calls = []

        @retry_on_lock(attempts=3, backoff_ms=(1, 1, 1))
        def fk_violation():
            calls.append("call")
            raise sqlite3.IntegrityError("FOREIGN KEY constraint failed")

        with self.assertRaises(sqlite3.IntegrityError):
            fk_violation()
        self.assertEqual(len(calls), 1)

    def test_attempts_less_than_one_raises(self):
        with self.assertRaises(ValueError):
            retry_on_lock(attempts=0)

    def test_backoff_is_actually_observed(self):
        calls: list[float] = []

        @retry_on_lock(attempts=2, backoff_ms=(20,))
        def flaky():
            calls.append(time.monotonic())
            if len(calls) < 2:
                raise sqlite3.OperationalError("database is locked")
            return "ok"

        flaky()
        self.assertEqual(len(calls), 2)
        # The retry waited at least 20ms (0.02s); allow margin
        # for system scheduling jitter.
        elapsed = calls[1] - calls[0]
        self.assertGreaterEqual(elapsed, 0.015)


class AdminAlertEmissionTests(unittest.TestCase):
    def test_disk_full_emits_admin_alert(self):
        with patch(
            "company_discovery.audit_log.emit_system_event"
        ) as mock_emit:
            emit_admin_alert(ERR_DISK_FULL, "detail string")
        mock_emit.assert_called_once()
        kwargs = mock_emit.call_args.kwargs
        self.assertEqual(kwargs.get("system_event_kind"), "db_disk_full")

    def test_schema_drift_emits_admin_alert(self):
        with patch(
            "company_discovery.audit_log.emit_system_event"
        ) as mock_emit:
            emit_admin_alert(ERR_SCHEMA_DRIFT, "detail string")
        mock_emit.assert_called_once()
        kwargs = mock_emit.call_args.kwargs
        self.assertEqual(kwargs.get("system_event_kind"), "db_schema_drift")

    def test_lock_busy_does_not_emit_admin_alert(self):
        with patch(
            "company_discovery.audit_log.emit_system_event"
        ) as mock_emit:
            emit_admin_alert(ERR_LOCK_BUSY, "detail")
        mock_emit.assert_not_called()

    def test_audit_log_failure_does_not_propagate(self):
        with patch(
            "company_discovery.audit_log.emit_system_event",
            side_effect=Exception("audit broken"),
        ):
            # Must not raise
            emit_admin_alert(ERR_DISK_FULL, "detail")


if __name__ == "__main__":
    unittest.main()
