# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Round-7 tests: items 13–17 closeout."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

class AutoPushHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="round7-push-"))
        os.environ["HELPMEFINDTHEJOB_DATA_DIR"] = str(cls.tmpdir)
        os.environ["HELPMEFINDTHEJOB_VAPID_PUBLIC_KEY"] = "synthetic"
        os.environ["HELPMEFINDTHEJOB_VAPID_PRIVATE_KEY"] = "synthetic"
        for name in list(sys.modules):
            if name == "app" or name.startswith("company_discovery.push_transport"):
                del sys.modules[name]
        import app
        from company_discovery import push_transport

        cls.app = app
        cls.state = app.STATE
        cls.push_transport = push_transport
        cls.original_send = push_transport.send_push

    @classmethod
    def tearDownClass(cls) -> None:
        cls.push_transport.send_push = cls.original_send
        for key in ("HELPMEFINDTHEJOB_VAPID_PUBLIC_KEY", "HELPMEFINDTHEJOB_VAPID_PRIVATE_KEY"):
            os.environ.pop(key, None)
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_no_subscription_returns_no_subscriptions(self) -> None:
        out = self.state.notify_new_matches("user_no_subs")
        self.assertEqual(out["status"], "no_subscriptions")
        self.assertEqual(out["sent"], 0)


if __name__ == "__main__":
    unittest.main()
