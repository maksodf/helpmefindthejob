"""Onboarding email drip (Phase 3 tracker item #37).

After the day-0 welcome email (#32), the operator wants two more
nudges: day-3 ("install the bookmarklet") and day-7 ("any luck?").
Both fire from the hourly retention-purge thread via
``run_onboarding_drip``. Per-user columns make the sweep idempotent —
once a user has the column populated, the next sweep skips them.

Eligibility windows:
- day-3 fires when ``created_at`` is between 3 and 14 days old
- day-7 fires when ``created_at`` is between 7 and 30 days old

Bound the upper edges so the cron doesn't email a long-dormant
account that signed up six months ago.
"""

from __future__ import annotations

import unittest
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from company_discovery.auth import AuthStore, now_utc


class DripEligibilityTests(unittest.TestCase):
    def _store(self) -> AuthStore:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = AuthStore(Path(tmp.name) / "auth.sqlite3", secret_key="x" * 64)
        self.addCleanup(store.close)
        return store

    def _set_created_at(self, store: AuthStore, user_id: str, days_ago: int) -> None:
        when = (now_utc() - timedelta(days=days_ago)).isoformat()
        store.connection.execute(
            "UPDATE users SET created_at = ? WHERE id = ?", (when, user_id),
        )
        store.connection.commit()

    def test_day3_eligibility_window(self) -> None:
        store = self._store()
        too_new = store.create_user("a@example.com", "very-secret-pass-1234")
        in_window_low = store.create_user("b@example.com", "very-secret-pass-1234")
        in_window_high = store.create_user("c@example.com", "very-secret-pass-1234")
        too_old = store.create_user("d@example.com", "very-secret-pass-1234")

        self._set_created_at(store, too_new.id, 1)
        self._set_created_at(store, in_window_low.id, 3)
        self._set_created_at(store, in_window_high.id, 13)
        self._set_created_at(store, too_old.id, 30)

        due = {u.id for u in store.users_due_for_drip(
            column="drip_day3_sent_at", min_age_days=3, max_age_days=14,
        )}
        self.assertNotIn(too_new.id, due)
        self.assertIn(in_window_low.id, due)
        self.assertIn(in_window_high.id, due)
        self.assertNotIn(too_old.id, due)

    def test_mark_sent_excludes_from_next_sweep(self) -> None:
        store = self._store()
        user = store.create_user("alice@example.com", "very-secret-pass-1234")
        self._set_created_at(store, user.id, 5)

        self.assertEqual(
            [u.id for u in store.users_due_for_drip(column="drip_day3_sent_at", min_age_days=3, max_age_days=14)],
            [user.id],
        )
        store.mark_drip_sent(user.id, "drip_day3_sent_at")
        self.assertEqual(
            list(store.users_due_for_drip(column="drip_day3_sent_at", min_age_days=3, max_age_days=14)),
            [],
        )
        # day-7 column is independent — same user still surfaces on
        # that sweep when their age crosses 7d.
        self._set_created_at(store, user.id, 8)
        self.assertEqual(
            [u.id for u in store.users_due_for_drip(column="drip_day7_sent_at", min_age_days=7, max_age_days=30)],
            [user.id],
        )

    def test_invalid_column_rejected(self) -> None:
        store = self._store()
        with self.assertRaises(ValueError):
            store.users_due_for_drip(column="dropping_table_users", min_age_days=3)
        with self.assertRaises(ValueError):
            store.mark_drip_sent("u1", column="dropping_table_users")

    def test_inactive_users_skipped(self) -> None:
        store = self._store()
        active = store.create_user("a@example.com", "very-secret-pass-1234")
        inactive = store.create_user("b@example.com", "very-secret-pass-1234")
        self._set_created_at(store, active.id, 5)
        self._set_created_at(store, inactive.id, 5)
        store.connection.execute(
            "UPDATE users SET active = 0 WHERE id = ?", (inactive.id,),
        )
        store.connection.commit()
        due = {u.id for u in store.users_due_for_drip(column="drip_day3_sent_at", min_age_days=3, max_age_days=14)}
        self.assertIn(active.id, due)
        self.assertNotIn(inactive.id, due)


class RunOnboardingDripIntegrationTests(unittest.TestCase):
    """End-to-end pass through ``AppState.run_onboarding_drip``: stage
    a user with the right ``created_at``, run the sweep, assert the
    email transport was hit and the column flipped."""

    def _state(self) -> tuple["AppState", str]:
        from app import AppState
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        state = AppState(
            root / "company.sqlite3",
            root / "auth.sqlite3",
            root / "ai.json",
            root / "schedule.json",
            start_scheduler=False,
        )
        self.addCleanup(state.auth_store.close)
        self.addCleanup(state.repository.close)
        return state, str(root)

    def _set_created_at(self, state, user_id, days_ago: int) -> None:
        when = (now_utc() - timedelta(days=days_ago)).isoformat()
        state.auth_store.connection.execute(
            "UPDATE users SET created_at = ? WHERE id = ?", (when, user_id),
        )
        state.auth_store.connection.commit()

    def test_run_drip_sends_and_marks(self) -> None:
        state, _ = self._state()
        user = state.auth_store.create_user("alice@example.com", "very-secret-pass-1234")
        self._set_created_at(state, user.id, 5)

        result = state.run_onboarding_drip()
        self.assertEqual(result["day3"], 1)
        self.assertEqual(result["day7"], 0)
        # Re-running is a no-op (column flipped, account excluded).
        again = state.run_onboarding_drip()
        self.assertEqual(again["day3"], 0)

        # Push the user into the day-7 window; only day-7 fires.
        self._set_created_at(state, user.id, 9)
        third = state.run_onboarding_drip()
        self.assertEqual(third["day7"], 1)
        # day-3 column was already set so it does not re-fire.
        self.assertEqual(third["day3"], 0)


if __name__ == "__main__":
    unittest.main()
