"""Round-6 tests: B6 server-side push wiring."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from company_discovery.models import PushSubscription
from company_discovery.push_transport import (
    PushPayload,
    PushUnavailableError,
    is_push_configured,
    send_push,
    vapid_public_key,
)
from company_discovery.repository import InMemoryCompanyDiscoveryRepository


class PushPayloadTests(unittest.TestCase):
    def test_to_json_strips_none_fields(self) -> None:
        payload = PushPayload(title="Hi", body="hello", url=None, icon=None)
        out = payload.to_json()
        self.assertIn('"title": "Hi"', out)
        self.assertNotIn("url", out)
        self.assertNotIn("icon", out)


class PushTransportEnvTests(unittest.TestCase):
    def setUp(self) -> None:
        for key in ("DIRECTJOB_VAPID_PUBLIC_KEY", "DIRECTJOB_VAPID_PRIVATE_KEY"):
            os.environ.pop(key, None)

    def test_disabled_when_env_vars_missing(self) -> None:
        self.assertFalse(is_push_configured())
        self.assertIsNone(vapid_public_key())

    def test_send_push_raises_when_disabled(self) -> None:
        sub = PushSubscription(
            user_id="u1",
            endpoint="https://push.example.com/ep/123",
            p256dh="aaa",
            auth="bbb",
        )
        with self.assertRaises(PushUnavailableError):
            send_push(sub, PushPayload(title="t", body="b"))

    def test_enabled_when_env_vars_set(self) -> None:
        os.environ["DIRECTJOB_VAPID_PUBLIC_KEY"] = "synthetic-public-key"
        os.environ["DIRECTJOB_VAPID_PRIVATE_KEY"] = "synthetic-private-key"
        try:
            self.assertTrue(is_push_configured())
            self.assertEqual(vapid_public_key(), "synthetic-public-key")
        finally:
            for key in ("DIRECTJOB_VAPID_PUBLIC_KEY", "DIRECTJOB_VAPID_PRIVATE_KEY"):
                os.environ.pop(key, None)


class PushSubscriptionRepoTests(unittest.TestCase):
    def test_save_find_delete(self) -> None:
        repo = InMemoryCompanyDiscoveryRepository()
        sub = PushSubscription(
            user_id="u1",
            endpoint="https://push.example/ep1",
            p256dh="x", auth="y",
        )
        repo.save_push_subscription(sub)
        self.assertEqual(len(repo.list_push_subscriptions("u1")), 1)
        found = repo.find_push_subscription("https://push.example/ep1")
        assert found is not None
        self.assertEqual(found.id, sub.id)
        repo.delete_push_subscription(sub.id)
        self.assertEqual(repo.list_push_subscriptions("u1"), [])


class PushHttpEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="round6-push-"))
        os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(cls.tmpdir)
        for name in list(sys.modules):
            if name == "app":
                del sys.modules[name]
        import app  # noqa: E402

        cls.state = app.STATE

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_subscription_roundtrip_through_repo(self) -> None:
        sub = PushSubscription(
            user_id="user_push_test",
            endpoint="https://push.example/ep-final",
            p256dh="p1",
            auth="a1",
        )
        self.state.repository.save_push_subscription(sub)
        listed = self.state.repository.list_push_subscriptions("user_push_test")
        self.assertEqual(len(listed), 1)


if __name__ == "__main__":
    unittest.main()
