# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""4-week-plan Invariant 2: Trust Receipt contract tests.

Pins the build / verify / tampering / CLI behaviour of the
signed-decision-receipt surface.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.trust_receipt import (
    DECISION_FIT_SCORE,
    DECISION_TAILOR_CV,
    KNOWN_DECISIONS,
    RECEIPT_SCHEMA_VERSION,
    TrustReceipt,
    build_trust_receipt,
    looks_like_receipt_id,
    render_receipt_markdown,
    verify_trust_receipt,
)


_TEST_SALT = b"test-salt-for-trust-receipts-suite-padding-padding"


class BuildTrustReceipt(unittest.TestCase):
    def test_returns_TrustReceipt_dataclass(self):
        receipt = build_trust_receipt(
            decision_type=DECISION_FIT_SCORE,
            user_id="alice@example.com",
            ai_provider="ollama",
            prompt_template_id="fit_score_v3",
            prompt_text="prompt body",
            response_text="response body",
            salt=_TEST_SALT,
        )
        self.assertIsInstance(receipt, TrustReceipt)
        self.assertEqual(receipt.schema_version, RECEIPT_SCHEMA_VERSION)
        self.assertEqual(receipt.decision_type, DECISION_FIT_SCORE)
        self.assertEqual(receipt.ai_provider, "ollama")
        self.assertEqual(receipt.prompt_template_id, "fit_score_v3")
        # Signature is 64 hex chars (SHA-256)
        self.assertEqual(len(receipt.signature), 64)
        # Hashes are 16 hex chars (short SHA-256)
        self.assertEqual(len(receipt.prompt_hash), 16)
        self.assertEqual(len(receipt.response_hash), 16)
        # Opaque user id is 16 hex chars
        self.assertEqual(len(receipt.user_id_opaque), 16)

    def test_unknown_decision_type_rejected(self):
        with self.assertRaises(ValueError) as cm:
            build_trust_receipt(
                decision_type="invented",
                user_id="u",
                ai_provider="x",
                prompt_template_id="y",
                prompt_text="p",
                response_text="r",
                salt=_TEST_SALT,
            )
        self.assertIn("unknown_decision_type", str(cm.exception))

    def test_salt_too_short_rejected(self):
        with self.assertRaises(ValueError) as cm:
            build_trust_receipt(
                decision_type=DECISION_FIT_SCORE,
                user_id="u",
                ai_provider="x",
                prompt_template_id="y",
                prompt_text="p",
                response_text="r",
                salt=b"short",
            )
        self.assertIn("salt", str(cm.exception))

    def test_no_plaintext_pii_in_receipt(self):
        """The PII surface — user id, prompt body, response body —
        must never appear as plaintext in the signed receipt."""
        plaintext_user = "alice-secret-email@example.com"
        plaintext_prompt = "VERY-PRIVATE-PROMPT-BODY-AICHA-TUNISIA"
        plaintext_response = "VERY-PRIVATE-RESPONSE-CHOOSE-Berlin"
        receipt = build_trust_receipt(
            decision_type=DECISION_FIT_SCORE,
            user_id=plaintext_user,
            ai_provider="ollama",
            prompt_template_id="fit_v3",
            prompt_text=plaintext_prompt,
            response_text=plaintext_response,
            salt=_TEST_SALT,
        )
        flat = json.dumps(receipt.to_dict())
        self.assertNotIn(plaintext_user, flat)
        self.assertNotIn(plaintext_prompt, flat)
        self.assertNotIn(plaintext_response, flat)

    def test_audit_log_linkage_fields_carried(self):
        receipt = build_trust_receipt(
            decision_type=DECISION_TAILOR_CV,
            user_id="u",
            ai_provider="openai",
            prompt_template_id="tailor_v2",
            prompt_text="p",
            response_text="r",
            salt=_TEST_SALT,
            audit_log_sequence_no=42,
            audit_log_chain_hmac="abc123" + "00" * 29,
        )
        self.assertEqual(receipt.audit_log_sequence_no, 42)
        self.assertEqual(receipt.audit_log_chain_hmac, "abc123" + "00" * 29)


class VerifyTrustReceipt(unittest.TestCase):
    def test_signature_validates_with_correct_salt(self):
        receipt = build_trust_receipt(
            decision_type=DECISION_FIT_SCORE,
            user_id="u",
            ai_provider="ollama",
            prompt_template_id="v3",
            prompt_text="p",
            response_text="r",
            salt=_TEST_SALT,
        )
        result = verify_trust_receipt(receipt.to_dict(), _TEST_SALT)
        self.assertTrue(result.ok)
        self.assertIsNone(result.reason)

    def test_wrong_salt_fails(self):
        receipt = build_trust_receipt(
            decision_type=DECISION_FIT_SCORE,
            user_id="u",
            ai_provider="ollama",
            prompt_template_id="v3",
            prompt_text="p",
            response_text="r",
            salt=_TEST_SALT,
        )
        result = verify_trust_receipt(
            receipt.to_dict(), b"wrong-salt-aaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "signature_mismatch")

    def test_tampered_field_fails(self):
        receipt_dict = build_trust_receipt(
            decision_type=DECISION_FIT_SCORE,
            user_id="u",
            ai_provider="ollama",
            prompt_template_id="v3",
            prompt_text="p",
            response_text="r",
            salt=_TEST_SALT,
        ).to_dict()
        # Tamper: change provider
        receipt_dict["aiProvider"] = "openai"
        result = verify_trust_receipt(receipt_dict, _TEST_SALT)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "signature_mismatch")

    def test_missing_signature_fails(self):
        receipt_dict = build_trust_receipt(
            decision_type=DECISION_FIT_SCORE,
            user_id="u",
            ai_provider="ollama",
            prompt_template_id="v3",
            prompt_text="p",
            response_text="r",
            salt=_TEST_SALT,
        ).to_dict()
        del receipt_dict["signature"]
        result = verify_trust_receipt(receipt_dict, _TEST_SALT)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "missing_signature")

    def test_invalid_shape_fails(self):
        result = verify_trust_receipt("not-a-dict", _TEST_SALT)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "invalid_shape")

    def test_unknown_schema_version_fails(self):
        receipt_dict = build_trust_receipt(
            decision_type=DECISION_FIT_SCORE,
            user_id="u",
            ai_provider="ollama",
            prompt_template_id="v3",
            prompt_text="p",
            response_text="r",
            salt=_TEST_SALT,
        ).to_dict()
        receipt_dict["schemaVersion"] = "v999"
        result = verify_trust_receipt(receipt_dict, _TEST_SALT)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "schema_version_unknown")


class ReceiptIdentifierAndKnownDecisions(unittest.TestCase):
    def test_known_decisions_count(self):
        # 9 decision types as of v1 — every user-visible AI output
        # type is covered. Chat-router intent classification is NOT
        # in this list by design: it runs many times per
        # conversation and produces no user-visible artifact, so
        # emitting receipts for it would flood the user's log.
        self.assertEqual(len(KNOWN_DECISIONS), 9)

    def test_looks_like_receipt_id_accepts_real(self):
        self.assertTrue(looks_like_receipt_id("rcpt-0123456789ab"))

    def test_looks_like_receipt_id_rejects_garbage(self):
        for bad in (
            "",
            "rcpt-tooshort",
            "rcpt-ABCDEF012345",  # uppercase
            "../etc/passwd",
            "rcpt-0123456789ab/../",
            "RCPT-0123456789ab",
            "receipt-0123456789ab",
        ):
            self.assertFalse(looks_like_receipt_id(bad), f"should reject {bad!r}")


class MarkdownRendering(unittest.TestCase):
    def test_renders_all_fields(self):
        receipt = build_trust_receipt(
            decision_type=DECISION_FIT_SCORE,
            user_id="u",
            ai_provider="ollama",
            prompt_template_id="v3",
            prompt_text="p",
            response_text="r",
            salt=_TEST_SALT,
        )
        md = render_receipt_markdown(receipt)
        # Header
        self.assertIn("# Trust Receipt", md)
        # Every receipt field appears
        for fragment in (
            receipt.receipt_id,
            receipt.signature,
            receipt.ai_provider,
            receipt.prompt_template_id,
            receipt.prompt_hash,
            receipt.response_hash,
        ):
            self.assertIn(fragment, md)
        # Verify section is present
        self.assertIn("How to verify this receipt", md)

    def test_renders_null_audit_fields_gracefully(self):
        receipt = build_trust_receipt(
            decision_type=DECISION_FIT_SCORE,
            user_id="u",
            ai_provider="ollama",
            prompt_template_id="v3",
            prompt_text="p",
            response_text="r",
            salt=_TEST_SALT,
        )
        # Audit fields are None by default
        md = render_receipt_markdown(receipt)
        self.assertIn("`null`", md)


class CLIVerifier(unittest.TestCase):
    """Offline verifier — must work as a standalone command-line
    tool with just Python + this file + the salt."""

    @classmethod
    def setUpClass(cls):
        cls.python = sys.executable
        cls.repo_root = Path(__file__).resolve().parent.parent

    def _run_cli(
        self, receipt_file: Path, salt_b64: str, expect_exit: int
    ) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [
                self.python,
                "-m",
                "company_discovery.verify_receipt_cli",
                str(receipt_file),
                "--salt-b64",
                salt_b64,
            ],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(
            result.returncode,
            expect_exit,
            f"unexpected exit code; stdout={result.stdout!r} stderr={result.stderr!r}",
        )
        return result

    def test_cli_verifies_valid_receipt(self):
        receipt = build_trust_receipt(
            decision_type=DECISION_FIT_SCORE,
            user_id="u",
            ai_provider="ollama",
            prompt_template_id="v3",
            prompt_text="p",
            response_text="r",
            salt=_TEST_SALT,
        )
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            path.write_text(json.dumps(receipt.to_dict()))
            salt_b64 = base64.b64encode(_TEST_SALT).decode("ascii")
            res = self._run_cli(path, salt_b64, expect_exit=0)
            self.assertIn("signature OK", res.stdout)

    def test_cli_rejects_tampered_receipt(self):
        receipt = build_trust_receipt(
            decision_type=DECISION_TAILOR_CV,
            user_id="u",
            ai_provider="openai",
            prompt_template_id="v2",
            prompt_text="p",
            response_text="r",
            salt=_TEST_SALT,
        ).to_dict()
        receipt["aiProvider"] = "tampered"
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            path.write_text(json.dumps(receipt))
            salt_b64 = base64.b64encode(_TEST_SALT).decode("ascii")
            res = self._run_cli(path, salt_b64, expect_exit=1)
            self.assertIn("signature_mismatch", res.stderr)

    def test_cli_rejects_wrong_salt(self):
        receipt = build_trust_receipt(
            decision_type=DECISION_FIT_SCORE,
            user_id="u",
            ai_provider="ollama",
            prompt_template_id="v3",
            prompt_text="p",
            response_text="r",
            salt=_TEST_SALT,
        )
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            path.write_text(json.dumps(receipt.to_dict()))
            wrong_b64 = base64.b64encode(b"wrong-salt" + b"0" * 32).decode("ascii")
            res = self._run_cli(path, wrong_b64, expect_exit=1)
            self.assertIn("signature_mismatch", res.stderr)


if __name__ == "__main__":
    unittest.main()
