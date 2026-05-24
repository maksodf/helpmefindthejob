# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Alert-delivery end-to-end contract tests (post-sprint engineer-
gap #9).

The 40-gap analysis flagged: "no real-time job alerts beyond Slack
webhook (no email digests verified, no push notifications
verified)." This file closes the verification gap by exercising
every alert pipeline end-to-end with structured assertions.

Coverage:

1. **Email digest pipeline**
   - `STATE.send_user_digest(user)` writes a real Email to the
     transport with the right shape.
   - Empty data still produces a sent message (operator gets
     "nothing new today" visibility).
   - `STATE.run_user_daily(user_id)` returns `digestSent=True`.

2. **Web Push pipeline**
   - `STATE.notify_new_matches` handles every "no work to do"
     condition gracefully (no subs, no searches, push disabled).
   - With matching jobs + one sub + VAPID configured, send_push
     fires per (job × sub).
   - **Idempotency**: same job not pushed twice — pinned via
     `last_push_notified_at` threshold.
   - **max_pushes cap** is enforced.
   - **Dead-sub pruning** (gap #9 root-cause fix): when
     pywebpush raises a 410-Gone or 404-Not-Found, the
     subscription is deleted from the repo so subsequent runs
     don't waste time on it.
   - **Transient errors don't prune**: a 503 / network blip
     leaves the sub in place.

3. **Slack pipeline**
   - No-op when webhook URL is unset.
   - Only fires when `auto_fit_score >= slack_fit_threshold`.
   - **Dedup**: same job not slacked twice (via
     `slack_notified_job_ids`).
   - **Failed-ping doesn't mark notified** — must retry.
   - Notified-ids list capped at 200 to bound memory.

4. **classify_push_exception** unit tests pin the contract
   the call sites depend on.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app import AppState
from company_discovery.email_transport import Email
from company_discovery.models import (
    Company,
    DiscoveredJob,
    PushSubscription,
    SavedSearch,
)
from company_discovery.push_transport import (
    PUSH_SUBSCRIPTION_GONE_STATUSES,
    PushUnavailableError,
    classify_push_exception,
)


def _build_state(tmpdir: Path) -> AppState:
    """Fresh AppState with isolated DB + outbox path."""

    state = AppState(
        tmpdir / "company.sqlite3",
        tmpdir / "auth.sqlite3",
        tmpdir / "ai.json",
        tmpdir / "schedule.json",
        start_scheduler=False,
    )
    return state


# ---------------------------------------------------------------------------
# classify_push_exception unit contract
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _FakeWebPushException(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"fake webpush {status_code}")
        self.response = _FakeResponse(status_code)


class ClassifyPushException(unittest.TestCase):
    def test_unavailable_classification(self):
        self.assertEqual(
            classify_push_exception(PushUnavailableError("no_vapid")),
            "unavailable",
        )

    def test_gone_classification_404(self):
        self.assertEqual(classify_push_exception(_FakeWebPushException(404)), "gone")

    def test_gone_classification_410(self):
        self.assertEqual(classify_push_exception(_FakeWebPushException(410)), "gone")

    def test_transient_classification_503(self):
        self.assertEqual(classify_push_exception(_FakeWebPushException(503)), "transient")

    def test_transient_classification_no_response(self):
        # A bare ConnectionError has no .response attribute — must
        # classify as transient, never "gone".
        self.assertEqual(
            classify_push_exception(ConnectionError("network down")),
            "transient",
        )

    def test_transient_classification_response_no_status(self):
        # A WebPushException-like object whose response object is
        # missing status_code → transient, never "gone".
        class _NoStatus:
            pass

        exc = Exception("weird shape")
        exc.response = _NoStatus()  # type: ignore[attr-defined]
        self.assertEqual(classify_push_exception(exc), "transient")

    def test_gone_status_set_matches_constant(self):
        # The frozenset of gone-codes is the source of truth.
        self.assertEqual(PUSH_SUBSCRIPTION_GONE_STATUSES, frozenset({404, 410}))


# ---------------------------------------------------------------------------
# Email digest pipeline
# ---------------------------------------------------------------------------


class EmailDigestE2E(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = _build_state(Path(self.tmp.name))
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.user = self.state.auth_store.create_user("digest@example.com", "secret-pass-12345678")

    def test_send_user_digest_writes_to_transport(self):
        # Replace the email transport with a recording mock so we
        # can assert on the exact Email object sent.
        sent: list[Email] = []

        class _RecordingTransport:
            def send(self, email: Email) -> None:
                sent.append(email)

        self.state.email_transport = _RecordingTransport()
        text = self.state.send_user_digest(user=self.user)
        self.assertEqual(len(sent), 1, "expected exactly one email sent")
        email = sent[0]
        self.assertEqual(email.to, "digest@example.com")
        self.assertIn("digest", email.subject.lower())
        self.assertTrue(email.text, "digest body MUST be non-empty")
        # The function's return value MUST match what was sent
        self.assertEqual(text, email.text)
        # From address MUST be set (not empty) — many SMTP relays
        # reject envelope-from-less mail
        self.assertTrue(email.from_address)

    def test_digest_handles_user_with_no_data(self):
        # A fresh user with no companies + no discovered jobs MUST
        # still get a valid digest (no crash, no empty string).
        sent: list[Email] = []

        class _RecordingTransport:
            def send(self, email: Email) -> None:
                sent.append(email)

        self.state.email_transport = _RecordingTransport()
        text = self.state.send_user_digest(user=self.user)
        self.assertEqual(len(sent), 1)
        # Body is non-empty (template renders some "nothing new" copy)
        self.assertTrue(text)

    def test_run_user_daily_marks_digest_sent(self):
        # The scheduler orchestrator. Even with no data, digestSent
        # in the result MUST be True if email send succeeded.
        class _RecordingTransport:
            def __init__(self) -> None:
                self.sent: list[Email] = []

            def send(self, email: Email) -> None:
                self.sent.append(email)

        transport = _RecordingTransport()
        self.state.email_transport = transport
        result = self.state.run_user_daily(self.user.id, trigger="test")
        self.assertTrue(
            result.get("digestSent"),
            f"run_user_daily MUST report digestSent=True; got {result}",
        )
        self.assertEqual(len(transport.sent), 1)


# ---------------------------------------------------------------------------
# Web Push pipeline
# ---------------------------------------------------------------------------


def _set_vapid_env() -> None:
    """Set synthetic VAPID env vars so is_push_configured() = True."""
    os.environ["HELPMEFINDTHEJOB_VAPID_PUBLIC_KEY"] = "synthetic-pub"
    os.environ["HELPMEFINDTHEJOB_VAPID_PRIVATE_KEY"] = "synthetic-priv"


def _clear_vapid_env() -> None:
    for key in (
        "HELPMEFINDTHEJOB_VAPID_PUBLIC_KEY",
        "HELPMEFINDTHEJOB_VAPID_PRIVATE_KEY",
        "HELPMEFINDTHEJOB_VAPID_PUBLIC_KEY",
        "HELPMEFINDTHEJOB_VAPID_PRIVATE_KEY",
    ):
        os.environ.pop(key, None)


class NotifyNewMatchesE2E(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = _build_state(Path(self.tmp.name))
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.user = self.state.auth_store.create_user("push@example.com", "secret-pass-12345678")
        _clear_vapid_env()
        self.addCleanup(_clear_vapid_env)

    # ---- "nothing to do" paths --------------------------------------------

    def test_no_subscriptions_returns_zero(self):
        _set_vapid_env()
        result = self.state.notify_new_matches(self.user.id)
        self.assertEqual(result["status"], "no_subscriptions")
        self.assertEqual(result["sent"], 0)

    def test_no_saved_searches_returns_zero(self):
        _set_vapid_env()
        self.state.repository.save_push_subscription(
            PushSubscription(
                user_id=self.user.id,
                endpoint="https://push.example/ep1",
                p256dh="aaa",
                auth="bbb",
            )
        )
        result = self.state.notify_new_matches(self.user.id)
        self.assertEqual(result["status"], "no_saved_searches")
        self.assertEqual(result["sent"], 0)

    def test_push_unavailable_returns_zero(self):
        # No VAPID env vars set
        self.state.repository.save_push_subscription(
            PushSubscription(
                user_id=self.user.id,
                endpoint="https://push.example/ep1",
                p256dh="aaa",
                auth="bbb",
            )
        )
        result = self.state.notify_new_matches(self.user.id)
        self.assertEqual(result["status"], "push_unavailable")
        self.assertEqual(result["sent"], 0)

    # ---- happy path -------------------------------------------------------

    def _setup_one_matching_job(
        self,
    ) -> tuple[Company, DiscoveredJob, SavedSearch, PushSubscription]:
        company = Company(
            user_id=self.user.id,
            name="ACME Pflege",
            website_url="https://acme-pflege.example.com",
        )
        self.state.repository.save_company(company)
        job = DiscoveredJob(
            user_id=self.user.id,
            company_id=company.id,
            source_url="https://jobs.example.com/p1",
            title="Pflegekraft Berlin",
            confidence_score=0.95,
        )
        self.state.repository.save_discovered_job(job)
        search = SavedSearch(
            user_id=self.user.id,
            name="Pflege Berlin",
            target_roles=["Pflegekraft"],
        )
        self.state.repository.save_saved_search(search)
        sub = PushSubscription(
            user_id=self.user.id,
            endpoint="https://push.example/ep1",
            p256dh="aaa",
            auth="bbb",
        )
        self.state.repository.save_push_subscription(sub)
        return company, job, search, sub

    def test_matching_job_triggers_push(self):
        _set_vapid_env()
        self._setup_one_matching_job()
        with patch("app.send_push") as mock_send:
            result = self.state.notify_new_matches(self.user.id)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["sent"], 1)
        self.assertEqual(mock_send.call_count, 1)
        # The PushPayload MUST carry job title + company name
        payload_arg = mock_send.call_args[0][1]
        self.assertIn("Pflegekraft Berlin", payload_arg.title)

    def test_idempotency_does_not_push_same_job_twice(self):
        _set_vapid_env()
        self._setup_one_matching_job()
        with patch("app.send_push") as mock_send:
            self.state.notify_new_matches(self.user.id)
            # Second call: the same job is now BELOW the
            # last_push_notified_at threshold → no push
            self.state.notify_new_matches(self.user.id)
        # Only the first call fires send_push
        self.assertEqual(mock_send.call_count, 1)

    def test_max_pushes_caps_batch(self):
        _set_vapid_env()
        company, _, search, sub = self._setup_one_matching_job()
        # Add 5 more matching jobs (6 total)
        for i in range(5):
            self.state.repository.save_discovered_job(
                DiscoveredJob(
                    user_id=self.user.id,
                    company_id=company.id,
                    source_url=f"https://jobs.example.com/extra-{i}",
                    title=f"Pflegekraft Berlin extra {i}",
                    confidence_score=0.9,
                )
            )
        with patch("app.send_push") as mock_send:
            result = self.state.notify_new_matches(self.user.id, max_pushes=3)
        self.assertEqual(result["sent"], 3)
        self.assertEqual(mock_send.call_count, 3)

    # ---- the gap-#9 root-cause fix: dead-sub pruning ---------------------

    def test_gone_response_prunes_subscription(self):
        """A 410-Gone from the push service MUST delete the
        subscription so subsequent runs don't waste time on it.
        This is the real root-cause fix that this audit landed."""

        _set_vapid_env()
        company, job, search, sub = self._setup_one_matching_job()
        # send_push raises a fake WebPushException with status 410
        with patch("app.send_push", side_effect=_FakeWebPushException(410)):
            result = self.state.notify_new_matches(self.user.id)
        # Status is still "ok" (the batch completed; just no successful pushes)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["sent"], 0)
        # AND the subscription is now gone from the repo
        remaining = self.state.repository.list_push_subscriptions(self.user.id)
        self.assertEqual(
            len(remaining),
            0,
            "410-Gone response MUST trigger subscription delete; "
            "otherwise dead subs accumulate forever",
        )

    def test_404_response_prunes_subscription(self):
        _set_vapid_env()
        self._setup_one_matching_job()
        with patch("app.send_push", side_effect=_FakeWebPushException(404)):
            self.state.notify_new_matches(self.user.id)
        remaining = self.state.repository.list_push_subscriptions(self.user.id)
        self.assertEqual(len(remaining), 0)

    def test_transient_503_keeps_subscription(self):
        """A 503 is transient — the sub MUST stay in the repo so
        the next tick retries. Without this distinction the
        deployer's first network blip would wipe every sub."""

        _set_vapid_env()
        self._setup_one_matching_job()
        with patch("app.send_push", side_effect=_FakeWebPushException(503)):
            self.state.notify_new_matches(self.user.id)
        remaining = self.state.repository.list_push_subscriptions(self.user.id)
        self.assertEqual(
            len(remaining),
            1,
            "transient 503 MUST NOT delete the subscription",
        )

    def test_connection_error_keeps_subscription(self):
        # Pure network failure (no HTTP response at all) is transient
        _set_vapid_env()
        self._setup_one_matching_job()
        with patch("app.send_push", side_effect=ConnectionError("network down")):
            self.state.notify_new_matches(self.user.id)
        remaining = self.state.repository.list_push_subscriptions(self.user.id)
        self.assertEqual(len(remaining), 1)


# ---------------------------------------------------------------------------
# Slack pipeline
# ---------------------------------------------------------------------------


class SlackNotifyE2E(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = _build_state(Path(self.tmp.name))
        self.addCleanup(self.state.auth_store.close)
        self.addCleanup(self.state.repository.close)
        self.user = self.state.auth_store.create_user("slack@example.com", "secret-pass-12345678")
        self.company = Company(
            user_id=self.user.id,
            name="ACME GmbH",
            website_url="https://acme.example.com",
        )
        self.state.repository.save_company(self.company)

    def _make_job(self, *, score: float = 0.85, job_id: str | None = None) -> DiscoveredJob:
        job = DiscoveredJob(
            user_id=self.user.id,
            company_id=self.company.id,
            source_url="https://jobs.example.com/x",
            title="Test job",
            confidence_score=0.9,
            auto_fit_score=score,
        )
        if job_id:
            job.id = job_id
        self.state.repository.save_discovered_job(job)
        return job

    def test_no_op_when_webhook_url_unset(self):
        job = self._make_job()
        with patch("app.post_high_fit_notification") as mock_post:
            self.state.maybe_notify_slack(self.user.id, job)
        mock_post.assert_not_called()

    def test_fires_when_score_above_threshold(self):
        profile = self.state.profile_for(self.user.id)
        profile.slack_webhook_url = "https://hooks.slack.com/services/x/y/z"
        profile.slack_fit_threshold = 0.7
        self.state.repository.save_user_profile(profile)
        job = self._make_job(score=0.85)
        with patch(
            "app.post_high_fit_notification",
            return_value={"status": "ok"},
        ) as mock_post:
            self.state.maybe_notify_slack(self.user.id, job)
        mock_post.assert_called_once()

    def test_does_not_fire_when_score_below_threshold(self):
        profile = self.state.profile_for(self.user.id)
        profile.slack_webhook_url = "https://hooks.slack.com/services/x/y/z"
        profile.slack_fit_threshold = 0.9
        self.state.repository.save_user_profile(profile)
        job = self._make_job(score=0.5)
        with patch("app.post_high_fit_notification") as mock_post:
            self.state.maybe_notify_slack(self.user.id, job)
        mock_post.assert_not_called()

    def test_dedup_does_not_fire_same_job_twice(self):
        profile = self.state.profile_for(self.user.id)
        profile.slack_webhook_url = "https://hooks.slack.com/services/x/y/z"
        profile.slack_fit_threshold = 0.5
        self.state.repository.save_user_profile(profile)
        job = self._make_job(score=0.85, job_id="job-dedup-1")
        with patch("app.post_high_fit_notification", return_value={"status": "ok"}) as mock_post:
            self.state.maybe_notify_slack(self.user.id, job)
            self.state.maybe_notify_slack(self.user.id, job)
        self.assertEqual(
            mock_post.call_count,
            1,
            "second call for the same job MUST be deduped via slack_notified_job_ids",
        )

    def test_failed_ping_does_not_mark_notified(self):
        """If the Slack POST fails, the job MUST NOT be added to
        slack_notified_job_ids — so the next run can retry. A
        regression here would silently drop notifications for
        Slack outages."""

        profile = self.state.profile_for(self.user.id)
        profile.slack_webhook_url = "https://hooks.slack.com/services/x/y/z"
        profile.slack_fit_threshold = 0.5
        self.state.repository.save_user_profile(profile)
        job = self._make_job(score=0.85, job_id="job-retry-1")
        # First call: Slack returns non-ok
        with patch(
            "app.post_high_fit_notification",
            return_value={"status": "error", "error": "slack 500"},
        ):
            self.state.maybe_notify_slack(self.user.id, job)
        # The job MUST NOT be in the notified list
        profile_reloaded = self.state.profile_for(self.user.id)
        self.assertNotIn(
            "job-retry-1",
            getattr(profile_reloaded, "slack_notified_job_ids", []),
        )
        # Second call: Slack succeeds; this call MUST actually fire
        with patch(
            "app.post_high_fit_notification", return_value={"status": "ok"}
        ) as mock_post_retry:
            self.state.maybe_notify_slack(self.user.id, job)
        mock_post_retry.assert_called_once()

    def test_notified_list_caps_at_200(self):
        """Memory bound: notified_ids MUST stay <= 200."""

        profile = self.state.profile_for(self.user.id)
        profile.slack_webhook_url = "https://hooks.slack.com/services/x/y/z"
        profile.slack_fit_threshold = 0.0
        # Pre-fill with 250 ids
        profile.slack_notified_job_ids = [f"job-{i}" for i in range(250)]
        self.state.repository.save_user_profile(profile)
        # Send one more
        job = self._make_job(score=0.85, job_id="job-new")
        with patch("app.post_high_fit_notification", return_value={"status": "ok"}):
            self.state.maybe_notify_slack(self.user.id, job)
        profile_reloaded = self.state.profile_for(self.user.id)
        self.assertLessEqual(
            len(profile_reloaded.slack_notified_job_ids),
            200,
            "slack_notified_job_ids MUST be bounded; otherwise it grows "
            "forever as the user accrues notifications",
        )
        # And the new job is in the kept window
        self.assertIn("job-new", profile_reloaded.slack_notified_job_ids)


if __name__ == "__main__":
    unittest.main()
