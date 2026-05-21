# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Feature-flag runtime contract tests (13-plan item 5/13; gap #18).

Pins the decision order, determinism, distribution properties,
and the safety guardrails (typo → KeyError, not silent False).
"""

from __future__ import annotations

import os
import unittest
from collections import Counter
from unittest.mock import patch

from company_discovery.feature_flags import (
    FLAGS,
    Flag,
    _env_var_name,
    _percentage_bucket,
    _read_env_override,
    all_flags,
    assign_variant,
    is_enabled,
)


class FlagRegistry(unittest.TestCase):
    def test_registry_not_empty(self):
        # Sanity: at least the example experiment flag ships
        # so the A/B test (item 6) has a fixture to use.
        self.assertGreater(len(FLAGS), 0)

    def test_every_registered_flag_has_required_fields(self):
        for flag in FLAGS.values():
            self.assertIsInstance(flag, Flag)
            self.assertTrue(flag.name)
            self.assertIsInstance(flag.default, bool)
            self.assertTrue(flag.description)
            self.assertGreaterEqual(flag.rollout_percent, 0)
            self.assertLessEqual(flag.rollout_percent, 100)

    def test_flag_names_are_canonical(self):
        # Lowercase + dot or underscore separators, no spaces /
        # uppercase / weird chars
        import re

        pattern = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
        for name in FLAGS:
            self.assertRegex(name, pattern, f"non-canonical flag name: {name!r}")


class EnvVarOverride(unittest.TestCase):
    def setUp(self) -> None:
        self._original_env = dict(os.environ)

    def tearDown(self) -> None:
        # Clean any flag env vars I set
        for key in list(os.environ):
            if key.startswith("HELPMEFINDTHEJOB_FLAG_"):
                if key not in self._original_env:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = self._original_env[key]

    def test_env_var_name_translation(self):
        self.assertEqual(
            _env_var_name("ui.new_funnel_card"),
            "HELPMEFINDTHEJOB_FLAG_UI_NEW_FUNNEL_CARD",
        )

    def test_truthy_overrides_recognised(self):
        for value in ("true", "True", "1", "yes", "on", "ENABLED", "enable"):
            os.environ["HELPMEFINDTHEJOB_FLAG_EXPERIMENT_EXAMPLE_AB"] = value
            self.assertTrue(is_enabled("experiment.example_ab"))

    def test_falsy_overrides_recognised(self):
        for value in ("false", "False", "0", "no", "off", "DISABLED"):
            os.environ["HELPMEFINDTHEJOB_FLAG_UI_NEW_FUNNEL_CARD"] = value
            self.assertFalse(is_enabled("ui.new_funnel_card"))

    def test_empty_or_garbage_env_treated_as_unset(self):
        os.environ["HELPMEFINDTHEJOB_FLAG_UI_NEW_FUNNEL_CARD"] = "maybe"
        # Falls through to default (which is True for this flag)
        self.assertTrue(is_enabled("ui.new_funnel_card"))

    def test_env_override_wins_over_default(self):
        # ui.new_funnel_card defaults to True. Env override flips it.
        os.environ["HELPMEFINDTHEJOB_FLAG_UI_NEW_FUNNEL_CARD"] = "false"
        self.assertFalse(is_enabled("ui.new_funnel_card"))


class CodeDefault(unittest.TestCase):
    def test_no_override_no_user_returns_default(self):
        # ui.new_funnel_card defaults to True
        self.assertTrue(is_enabled("ui.new_funnel_card"))
        # experiment.example_ab defaults to False
        self.assertFalse(is_enabled("experiment.example_ab"))


class UnregisteredFlagRaises(unittest.TestCase):
    def test_unregistered_flag_raises_keyerror(self):
        with self.assertRaises(KeyError):
            is_enabled("totally_made_up_flag")

    def test_typo_at_call_site_caught(self):
        # ui.new_funnel_card exists; ui.new_funnle_card (typo) does not
        with self.assertRaises(KeyError):
            is_enabled("ui.new_funnle_card")


class PercentageRollout(unittest.TestCase):
    """The user-deterministic rollout is the foundation A/B
    builds on. These tests pin both determinism + distribution."""

    def test_same_user_always_gets_same_bucket(self):
        # Same call 100 times → same bucket every time
        buckets = {_percentage_bucket("ui.test_flag", "user-stable") for _ in range(100)}
        self.assertEqual(len(buckets), 1)

    def test_different_users_get_different_buckets(self):
        # 100 distinct user_ids → much more than 1 distinct bucket
        # (with HMAC distribution we expect close to 100 different
        # buckets, but the conservative pin is >= 30)
        buckets = {_percentage_bucket("ui.test_flag", f"user-{i}") for i in range(100)}
        self.assertGreater(len(buckets), 30)

    def test_bucket_in_valid_range(self):
        for i in range(50):
            bucket = _percentage_bucket("ui.test_flag", f"user-{i}")
            self.assertGreaterEqual(bucket, 0)
            self.assertLess(bucket, 100)

    def test_different_flags_distribute_user_differently(self):
        # The HMAC includes the flag name, so the same user_id
        # lands in different cohorts for different flags.
        # Otherwise every flag with rollout=50% would catch the
        # same users.
        b1 = _percentage_bucket("flag_one", "shared-user")
        b2 = _percentage_bucket("flag_two", "shared-user")
        # In rare cases they'd collide; the property is "not
        # systematically identical for ALL inputs."
        collisions = sum(
            1
            for i in range(100)
            if _percentage_bucket("flag_one", f"u-{i}")
            == _percentage_bucket("flag_two", f"u-{i}")
        )
        # Expect ~1% collisions for two independent uint8-bucket hashes
        self.assertLess(collisions, 10)

    def test_rollout_50_pct_hits_close_to_half(self):
        # A flag at 50% should be enabled for ~50% of a large
        # sample of users. We test the property loosely (±10%)
        # so we don't fail on harmless distribution variance.
        # Use a temporary flag for this test.
        original = FLAGS.get("ui.test_dist")
        FLAGS["ui.test_dist"] = Flag(
            name="ui.test_dist",
            default=False,
            description="dist test",
            rollout_percent=50,
        )
        try:
            count_enabled = sum(
                1
                for i in range(1000)
                if is_enabled("ui.test_dist", user_id=f"user-{i}")
            )
            # Empirical 1000-trial: expect ~500 ± ~30 (3σ ≈ 30 for binomial)
            self.assertGreater(count_enabled, 400)
            self.assertLess(count_enabled, 600)
        finally:
            if original is None:
                FLAGS.pop("ui.test_dist", None)
            else:
                FLAGS["ui.test_dist"] = original

    def test_rollout_zero_pct_disabled_for_everyone(self):
        # experiment.example_ab has rollout_percent=0
        for i in range(50):
            self.assertFalse(
                is_enabled("experiment.example_ab", user_id=f"user-{i}")
            )

    def test_rollout_100_pct_enabled_for_everyone(self):
        # ui.new_funnel_card has rollout_percent=100 + default=True;
        # either way every user gets True
        for i in range(50):
            self.assertTrue(
                is_enabled("ui.new_funnel_card", user_id=f"user-{i}")
            )


class DecisionPrecedence(unittest.TestCase):
    """The precedence order is critical. Env > percentage > default."""

    def setUp(self) -> None:
        self._original_env = dict(os.environ)
        # Use a fresh test flag at 50% rollout
        FLAGS["ui.precedence_test"] = Flag(
            name="ui.precedence_test",
            default=False,
            description="precedence test",
            rollout_percent=50,
        )

    def tearDown(self) -> None:
        FLAGS.pop("ui.precedence_test", None)
        for key in list(os.environ):
            if key.startswith("HELPMEFINDTHEJOB_FLAG_"):
                if key not in self._original_env:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = self._original_env[key]

    def test_env_override_wins_over_percentage(self):
        # User who'd be enabled by 50% rollout → forced off by env
        # Find a user_id that the percentage bucket would enable
        target_user = next(
            f"user-{i}"
            for i in range(100)
            if _percentage_bucket("ui.precedence_test", f"user-{i}") < 50
        )
        # Without override: enabled
        self.assertTrue(is_enabled("ui.precedence_test", user_id=target_user))
        # With env=false: disabled
        os.environ["HELPMEFINDTHEJOB_FLAG_UI_PRECEDENCE_TEST"] = "false"
        self.assertFalse(is_enabled("ui.precedence_test", user_id=target_user))


class AssignVariant(unittest.TestCase):
    """A/B (or A/B/C/…) variant assignment using the same stable
    hash mechanism. Foundation for 13-plan item 6/13."""

    def test_same_user_same_variant(self):
        variants = ["A", "B"]
        first = assign_variant("exp1", "user-x", variants)
        for _ in range(100):
            self.assertEqual(first, assign_variant("exp1", "user-x", variants))

    def test_distributes_across_two_variants(self):
        variants = ["A", "B"]
        counts = Counter(
            assign_variant("exp1", f"user-{i}", variants) for i in range(1000)
        )
        # Both arms should land within ±10% of 50:50
        self.assertGreater(counts["A"], 400)
        self.assertGreater(counts["B"], 400)

    def test_distributes_across_three_variants(self):
        variants = ["A", "B", "C"]
        counts = Counter(
            assign_variant("exp_three", f"user-{i}", variants) for i in range(900)
        )
        for v in variants:
            self.assertGreater(counts[v], 200)  # ~33% with margin
            self.assertLess(counts[v], 400)

    def test_different_experiments_assign_independently(self):
        # The same user_id can land in different arms for
        # different experiments — so we can run multiple
        # experiments concurrently without coupling.
        variants = ["A", "B"]
        a_exp1 = sum(
            1
            for i in range(100)
            if assign_variant("exp_a", f"user-{i}", variants) == "A"
        )
        a_exp2 = sum(
            1
            for i in range(100)
            if assign_variant("exp_b", f"user-{i}", variants) == "A"
        )
        # The same arm count would suggest coupling
        self.assertNotEqual(a_exp1, a_exp2)

    def test_empty_variants_raises(self):
        with self.assertRaises(ValueError):
            assign_variant("exp", "user", [])


class AllFlagsIntrospection(unittest.TestCase):
    def test_all_flags_returns_metadata_for_each(self):
        result = all_flags()
        self.assertEqual(len(result), len(FLAGS))
        # Sorted by name
        names = [f["name"] for f in result]
        self.assertEqual(names, sorted(names))
        # Each entry carries the expected shape
        for entry in result:
            self.assertIn("name", entry)
            self.assertIn("default", entry)
            self.assertIn("description", entry)
            self.assertIn("rolloutPercent", entry)
            self.assertIn("envVar", entry)
            self.assertTrue(entry["envVar"].startswith("HELPMEFINDTHEJOB_FLAG_"))


if __name__ == "__main__":
    unittest.main()
