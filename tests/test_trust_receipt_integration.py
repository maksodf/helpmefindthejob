# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""4-week-plan W1 D4: Trust Receipt end-to-end integration.

Pins the full pipeline:

1. The dispatch chokepoint accepts a ``receipt_emitter`` kwarg
   and invokes it post-call when set.
2. AppState ships a working ``receipt_emitter_for(user_id)``
   that constructs + signs + persists a receipt.
3. The persisted receipt verifies with the AppState's salt.
4. Cross-tenant isolation: user A cannot see user B's receipts.
5. The receipt links to the most-recent audit-log sequence_no
   so a reviewer can correlate decisions across the two stores.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app import AppState
from company_discovery.analysis import AnalysisExecutionResult, _dispatch_provider
from company_discovery.ai_providers import AIProviderConfig
from company_discovery.trust_receipt import (
    DECISION_TAILOR_CV,
    verify_trust_receipt,
)


def _make_state() -> tuple[AppState, str]:
    tmp = TemporaryDirectory()
    root = Path(tmp.name)
    state = AppState(
        root / "company.sqlite3",
        root / "auth.sqlite3",
        root / "ai.json",
        root / "schedule.json",
        start_scheduler=False,
    )
    state._test_tmp = tmp  # noqa: SLF001
    user = state.auth_store.create_user("rcpt@example.com", "secret-pass-12345678")
    return state, user.id


class ReceiptEmitterChokepoint(unittest.TestCase):
    def setUp(self) -> None:
        self.state, self.user_id = _make_state()
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.addCleanup(lambda: self.state._test_tmp.cleanup())  # noqa: SLF001

    def test_receipt_minted_after_successful_dispatch(self) -> None:
        """A successful AI call through _dispatch_provider with a
        receipt_emitter set produces exactly one receipt on disk."""
        provider = AIProviderConfig(
            provider_id="manual", invocation_mode="manual"
        )

        fake_result = AnalysisExecutionResult(
            status="completed",
            provider_id="manual",
            invocation_mode="manual",
            output="fake AI output",
            prompt="fake prompt",
        )

        with patch(
            "company_discovery.analysis._dispatch_provider_impl",
            return_value=fake_result,
        ):
            _dispatch_provider(
                "fake prompt",
                provider,
                "",
                purpose=DECISION_TAILOR_CV,
                receipt_emitter=self.state.receipt_emitter_for(self.user_id),
            )

        receipts = self.state.trust_receipt_store.list_for_user(self.user_id)
        self.assertEqual(len(receipts), 1)
        r = receipts[0]
        self.assertEqual(r["decisionType"], DECISION_TAILOR_CV)
        self.assertEqual(r["aiProvider"], "manual")

    def test_no_receipt_on_failed_dispatch(self) -> None:
        """If the AI dispatch raises, NO receipt is emitted —
        there's nothing to attest to on a failed call."""
        provider = AIProviderConfig(
            provider_id="manual", invocation_mode="manual"
        )

        with patch(
            "company_discovery.analysis._dispatch_provider_impl",
            side_effect=RuntimeError("simulated provider failure"),
        ):
            with self.assertRaises(RuntimeError):
                _dispatch_provider(
                    "fake prompt",
                    provider,
                    "",
                    purpose=DECISION_TAILOR_CV,
                    receipt_emitter=self.state.receipt_emitter_for(self.user_id),
                )

        receipts = self.state.trust_receipt_store.list_for_user(self.user_id)
        self.assertEqual(len(receipts), 0)

    def test_no_receipt_on_empty_output(self) -> None:
        """Provider returned successfully but with empty output —
        no decision to attest to, so no receipt."""
        provider = AIProviderConfig(
            provider_id="manual", invocation_mode="manual"
        )
        fake = AnalysisExecutionResult(
            status="completed",
            provider_id="manual",
            invocation_mode="manual",
            output="",
            prompt="p",
        )
        with patch(
            "company_discovery.analysis._dispatch_provider_impl",
            return_value=fake,
        ):
            _dispatch_provider(
                "p",
                provider,
                "",
                purpose=DECISION_TAILOR_CV,
                receipt_emitter=self.state.receipt_emitter_for(self.user_id),
            )
        self.assertEqual(
            len(self.state.trust_receipt_store.list_for_user(self.user_id)), 0
        )

    def test_persisted_receipt_verifies_with_store_salt(self) -> None:
        provider = AIProviderConfig(
            provider_id="manual", invocation_mode="manual"
        )
        fake = AnalysisExecutionResult(
            status="completed",
            provider_id="manual",
            invocation_mode="manual",
            output="real output content",
            prompt="prompt body",
        )
        with patch(
            "company_discovery.analysis._dispatch_provider_impl",
            return_value=fake,
        ):
            _dispatch_provider(
                "prompt body",
                provider,
                "",
                purpose=DECISION_TAILOR_CV,
                receipt_emitter=self.state.receipt_emitter_for(self.user_id),
            )
        receipts = self.state.trust_receipt_store.list_for_user(self.user_id)
        self.assertEqual(len(receipts), 1)
        salt = self.state.trust_receipt_store.salt
        self.assertTrue(verify_trust_receipt(receipts[0], salt).ok)

    def test_cross_tenant_isolation(self) -> None:
        """User A's receipts must not be visible to user B."""
        other_user = self.state.auth_store.create_user(
            "rcpt-other@example.com", "secret-pass-12345678"
        )
        provider = AIProviderConfig(
            provider_id="manual", invocation_mode="manual"
        )
        fake = AnalysisExecutionResult(
            status="completed",
            provider_id="manual",
            invocation_mode="manual",
            output="user-A-private-output",
            prompt="user-A-private-prompt",
        )
        with patch(
            "company_discovery.analysis._dispatch_provider_impl",
            return_value=fake,
        ):
            _dispatch_provider(
                "user-A-private-prompt",
                provider,
                "",
                purpose=DECISION_TAILOR_CV,
                receipt_emitter=self.state.receipt_emitter_for(self.user_id),
            )
        # User A has 1 receipt
        self.assertEqual(
            len(self.state.trust_receipt_store.list_for_user(self.user_id)), 1
        )
        # User B has 0 receipts
        self.assertEqual(
            len(self.state.trust_receipt_store.list_for_user(other_user.id)), 0
        )

    def test_receipt_carries_audit_log_linkage(self) -> None:
        """The minted receipt should carry the most-recent audit
        log sequence_no so a reviewer can correlate stores."""
        provider = AIProviderConfig(
            provider_id="manual", invocation_mode="manual"
        )
        fake = AnalysisExecutionResult(
            status="completed",
            provider_id="manual",
            invocation_mode="manual",
            output="output",
            prompt="p",
        )
        with patch(
            "company_discovery.analysis._dispatch_provider_impl",
            return_value=fake,
        ):
            _dispatch_provider(
                "p",
                provider,
                "",
                purpose=DECISION_TAILOR_CV,
                receipt_emitter=self.state.receipt_emitter_for(self.user_id),
            )
        receipts = self.state.trust_receipt_store.list_for_user(self.user_id)
        self.assertEqual(len(receipts), 1)
        receipt = receipts[0]
        # auditLogSequenceNo should be a positive int (or None if
        # the audit-log emitter never wrote — but it just did, via
        # _emit_dispatch_audit, so we expect a real seq_no).
        seq = receipt.get("auditLogSequenceNo")
        self.assertIsNotNone(seq)
        self.assertIsInstance(seq, int)
        self.assertGreater(seq, 0)
        # chain_hmac should be a 64-char hex string
        chain = receipt.get("auditLogChainHmac")
        self.assertIsNotNone(chain)
        self.assertEqual(len(chain), 64)


class SaltRotationContract(unittest.TestCase):
    """Quality-audit (2026-05-21): salt rotation MUST NOT silently
    orphan a user's receipt files. The signatures become stale
    (intended — that's what rotation means), but the files
    themselves remain reachable so the user can still download
    their historical decisions."""

    def test_receipts_remain_reachable_after_salt_rotation(self) -> None:
        from company_discovery.trust_receipt import build_trust_receipt
        from company_discovery.trust_receipt_store import TrustReceiptStore

        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            salt_v1 = b"salt-version-1-padding-padding-pad"
            salt_v2 = b"salt-version-2-padding-padding-pad"
            user_id = "user_aabbccddeeff00112233445566778899"

            # Issue receipt with salt v1
            store_v1 = TrustReceiptStore(base, salt=salt_v1)
            r = build_trust_receipt(
                decision_type="fit_score",
                user_id=user_id,
                ai_provider="ollama",
                prompt_template_id="fit_v3",
                prompt_text="p",
                response_text="r",
                salt=salt_v1,
            )
            store_v1.save(user_id, r)
            self.assertEqual(len(store_v1.list_for_user(user_id)), 1)

            # Rotate salt — files MUST still be reachable
            store_v2 = TrustReceiptStore(base, salt=salt_v2)
            listed = store_v2.list_for_user(user_id)
            self.assertEqual(
                len(listed),
                1,
                "Salt rotation must not orphan receipt files — "
                "user must still be able to download historical receipts",
            )
            # But the signature is now stale (intended behaviour)
            self.assertFalse(store_v2.verify(listed[0]))


class ReceiptEmitterFailureIsolation(unittest.TestCase):
    """The receipt-emit hook is Case-E best-effort: failure must
    NOT propagate to the AI call. Pin that contract."""

    def setUp(self) -> None:
        self.state, self.user_id = _make_state()
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.addCleanup(lambda: self.state._test_tmp.cleanup())  # noqa: SLF001

    def test_emitter_exception_does_not_break_dispatch(self) -> None:
        provider = AIProviderConfig(
            provider_id="manual", invocation_mode="manual"
        )
        fake = AnalysisExecutionResult(
            status="completed",
            provider_id="manual",
            invocation_mode="manual",
            output="ok",
            prompt="p",
        )

        def _broken_emitter(**_kwargs):
            raise RuntimeError("simulated emitter crash")

        with patch(
            "company_discovery.analysis._dispatch_provider_impl",
            return_value=fake,
        ):
            # Should NOT raise — the dispatch must survive a broken
            # receipt emitter.
            result = _dispatch_provider(
                "p",
                provider,
                "",
                purpose=DECISION_TAILOR_CV,
                receipt_emitter=_broken_emitter,
            )
        self.assertEqual(result.status, "completed")


if __name__ == "__main__":
    unittest.main()
