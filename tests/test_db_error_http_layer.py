# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
"""Phase 2 #78 Layer 2 — HTTP-handler integration contract.

Tests the Handler._handle_db_error + _request_locale helpers
that route sqlite-Error exceptions through the policy classifier
in db_errors before responding to the user.
"""

from __future__ import annotations

import sqlite3
import unittest
from unittest.mock import MagicMock, patch

from app import Handler
from company_discovery.db_errors import (
    ERR_DISK_FULL,
    ERR_LOCK_BUSY,
    ERR_REFERENTIAL_MISSING,
    ERR_SCHEMA_DRIFT,
)


def _make_handler_stub() -> Handler:
    """Build a stub Handler that has just enough surface for the
    `_handle_db_error` + `_request_locale` methods to run. Real
    BaseHTTPRequestHandler initialisation would need a socket; we
    bypass it by allocating the object via __new__ + wiring the
    minimum attributes the methods touch."""

    handler = Handler.__new__(Handler)
    # send_json / send_error_json want self.wfile / self.headers.
    handler.headers = {}  # Accept-Language defaults to empty
    handler.send_error_json = MagicMock()  # type: ignore[method-assign]
    return handler


class RequestLocaleTests(unittest.TestCase):
    def test_empty_header_defaults_to_en(self):
        h = _make_handler_stub()
        self.assertEqual(h._request_locale(), "en")  # noqa: SLF001

    def test_de_primary_language_resolves(self):
        h = _make_handler_stub()
        h.headers = {"Accept-Language": "de"}
        self.assertEqual(h._request_locale(), "de")  # noqa: SLF001

    def test_de_DE_resolves(self):
        h = _make_handler_stub()
        h.headers = {"Accept-Language": "de-DE"}
        self.assertEqual(h._request_locale(), "de")  # noqa: SLF001

    def test_de_with_q_factors_resolves(self):
        h = _make_handler_stub()
        h.headers = {"Accept-Language": "de;q=0.9, en;q=0.5"}
        self.assertEqual(h._request_locale(), "de")  # noqa: SLF001

    def test_en_resolves(self):
        h = _make_handler_stub()
        h.headers = {"Accept-Language": "en"}
        self.assertEqual(h._request_locale(), "en")  # noqa: SLF001

    def test_fr_falls_back_to_en(self):
        h = _make_handler_stub()
        h.headers = {"Accept-Language": "fr-FR"}
        self.assertEqual(h._request_locale(), "en")  # noqa: SLF001


class HandleDbErrorTests(unittest.TestCase):
    def test_lock_busy_routes_503_with_friendly_message(self):
        h = _make_handler_stub()
        with patch("company_discovery.db_errors.emit_admin_alert") as alert_mock:
            h._handle_db_error(sqlite3.OperationalError("database is locked"))  # noqa: SLF001
        h.send_error_json.assert_called_once()
        (status, code, message), kwargs = h.send_error_json.call_args
        self.assertEqual(int(status), 503)
        self.assertEqual(code, ERR_LOCK_BUSY)
        self.assertIn("try again", message.lower())
        # No admin alert for Case A (lock-busy is a transient retry condition)
        alert_mock.assert_called_once()  # called but with ERR_LOCK_BUSY which is a no-op inside
        # Verify the alert was for ERR_LOCK_BUSY (the function itself decides whether to actually emit)
        self.assertEqual(alert_mock.call_args.args[0], ERR_LOCK_BUSY)

    def test_disk_full_routes_507_with_admin_alert(self):
        h = _make_handler_stub()
        with patch("company_discovery.audit_log.emit_system_event") as audit_mock:
            h._handle_db_error(  # noqa: SLF001
                sqlite3.OperationalError("database or disk is full")
            )
        (status, code, _message), _ = h.send_error_json.call_args
        self.assertEqual(int(status), 507)
        self.assertEqual(code, ERR_DISK_FULL)
        # Admin alert fires for Case B
        audit_mock.assert_called_once()
        self.assertEqual(
            audit_mock.call_args.kwargs.get("system_event_kind"),
            "db_disk_full",
        )

    def test_integrity_error_routes_409(self):
        h = _make_handler_stub()
        h._handle_db_error(  # noqa: SLF001
            sqlite3.IntegrityError("FOREIGN KEY constraint failed")
        )
        (status, code, message), _ = h.send_error_json.call_args
        self.assertEqual(int(status), 409)
        self.assertEqual(code, ERR_REFERENTIAL_MISSING)
        self.assertIn("no longer exists", message.lower())

    def test_schema_drift_routes_500_with_generic_message(self):
        h = _make_handler_stub()
        with patch("company_discovery.audit_log.emit_system_event") as audit_mock:
            h._handle_db_error(  # noqa: SLF001
                sqlite3.OperationalError("no such column: foo")
            )
        (status, code, message), _ = h.send_error_json.call_args
        self.assertEqual(int(status), 500)
        self.assertEqual(code, ERR_SCHEMA_DRIFT)
        # User-facing message is generic — does NOT leak the column name
        self.assertNotIn("foo", message.lower())
        self.assertNotIn("no such column", message.lower())
        # Admin alert fires for Case D
        audit_mock.assert_called_once()

    def test_de_locale_returns_german_message(self):
        h = _make_handler_stub()
        h.headers = {"Accept-Language": "de"}
        h._handle_db_error(sqlite3.OperationalError("database is locked"))  # noqa: SLF001
        (_status, _code, message), _ = h.send_error_json.call_args
        self.assertIn("speichern läuft", message.lower())

    def test_include_body_false_propagates(self):
        h = _make_handler_stub()
        h._handle_db_error(  # noqa: SLF001
            sqlite3.OperationalError("database is locked"),
            include_body=False,
        )
        # Verify include_body=False was passed to send_error_json
        kwargs = h.send_error_json.call_args.kwargs
        self.assertFalse(kwargs.get("include_body"))

    def test_policy_classifier_failure_falls_back_to_generic_500(self):
        """If the policy-handling code itself raises, the helper must
        still send a 500 — never let the top-level catch crash."""
        h = _make_handler_stub()
        with patch(
            "company_discovery.db_errors.classify_db_error",
            side_effect=RuntimeError("policy broken"),
        ):
            h._handle_db_error(  # noqa: SLF001
                sqlite3.OperationalError("database is locked")
            )
        # Still wrote a response
        h.send_error_json.assert_called_once()
        (status, code, _message), _ = h.send_error_json.call_args
        self.assertEqual(int(status), 500)
        self.assertEqual(code, "internal_error")


if __name__ == "__main__":
    unittest.main()
