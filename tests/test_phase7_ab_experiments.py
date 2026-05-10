"""A/B experiment framework (Phase 7 tracker item #61).

``AppState.assign_variant`` is a pure function: hash
``(experiment_id | identity)`` → modulo number of variants → return
the slug. Two correctness properties:

1. **Deterministic**: same identity → same variant for the lifetime
   of the experiment. The hash domain-separator (``experiment_id``)
   means the same visitor gets independent assignments across
   different experiments rather than always landing in "the lucky
   bucket".
2. **Roughly even split**: at scale, the variants are sampled
   uniformly. We test this with 10 000 synthetic identities and
   assert each bucket lands within 5% of the mean.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class _StatelessApp:
    """We don't need the full AppState here; the helper is pure. But
    importing it via the test runner exercises the same code path."""

    def __init__(self) -> None:
        from app import AppState
        self._state_class = AppState


def _state():
    """Build a real AppState (cheaper than mocking) for tests that
    actually need the helper bound to an instance."""

    from app import AppState
    tmp = TemporaryDirectory()
    state = AppState(
        Path(tmp.name) / "company.sqlite3",
        Path(tmp.name) / "auth.sqlite3",
        Path(tmp.name) / "ai.json",
        Path(tmp.name) / "schedule.json",
        start_scheduler=False,
    )
    return state, tmp


class AssignVariantTests(unittest.TestCase):
    def test_same_identity_same_variant(self) -> None:
        state, tmp = _state()
        try:
            v1 = state.assign_variant(
                experiment_id="hero_cta", identity="anon-uuid-1234",
                variants=("control", "treatment"),
            )
            v2 = state.assign_variant(
                experiment_id="hero_cta", identity="anon-uuid-1234",
                variants=("control", "treatment"),
            )
            self.assertEqual(v1, v2)
        finally:
            state.auth_store.close()
            state.repository.close()
            tmp.cleanup()

    def test_different_experiments_can_yield_different_variants(self) -> None:
        # Domain separation: a visitor who lands in the "control"
        # bucket on experiment A is independently bucketed on B.
        state, tmp = _state()
        try:
            seen_a: set[str] = set()
            seen_b: set[str] = set()
            for i in range(200):
                identity = f"u{i}"
                seen_a.add(state.assign_variant(
                    experiment_id="exp_a", identity=identity,
                    variants=("control", "treatment"),
                ))
                seen_b.add(state.assign_variant(
                    experiment_id="exp_b", identity=identity,
                    variants=("control", "treatment"),
                ))
            self.assertEqual(seen_a, {"control", "treatment"})
            self.assertEqual(seen_b, {"control", "treatment"})
        finally:
            state.auth_store.close()
            state.repository.close()
            tmp.cleanup()

    def test_two_way_split_is_roughly_even(self) -> None:
        state, tmp = _state()
        try:
            from collections import Counter

            counts: Counter[str] = Counter()
            n = 10_000
            for i in range(n):
                v = state.assign_variant(
                    experiment_id="big_exp", identity=f"id-{i}",
                    variants=("control", "treatment"),
                )
                counts[v] += 1
            mean = n / 2
            tolerance = n * 0.05  # 5%
            for variant, count in counts.items():
                self.assertLess(
                    abs(count - mean), tolerance,
                    f"variant {variant} got {count}, expected within ±{tolerance:g} of {mean}",
                )
        finally:
            state.auth_store.close()
            state.repository.close()
            tmp.cleanup()

    def test_three_way_split_is_roughly_even(self) -> None:
        state, tmp = _state()
        try:
            from collections import Counter

            counts: Counter[str] = Counter()
            n = 9_000
            variants = ("control", "treatment_a", "treatment_b")
            for i in range(n):
                v = state.assign_variant(
                    experiment_id="three_way", identity=f"id-{i}",
                    variants=variants,
                )
                counts[v] += 1
            mean = n / 3
            tolerance = n * 0.05
            for variant in variants:
                self.assertLess(
                    abs(counts[variant] - mean), tolerance,
                    f"variant {variant} got {counts[variant]}, expected within ±{tolerance:g} of {mean}",
                )
        finally:
            state.auth_store.close()
            state.repository.close()
            tmp.cleanup()

    def test_validation_errors(self) -> None:
        state, tmp = _state()
        try:
            with self.assertRaises(ValueError):
                state.assign_variant(experiment_id="", identity="u", variants=("a",))
            with self.assertRaises(ValueError):
                state.assign_variant(experiment_id="x", identity="", variants=("a",))
            with self.assertRaises(ValueError):
                state.assign_variant(experiment_id="x", identity="u", variants=())
        finally:
            state.auth_store.close()
            state.repository.close()
            tmp.cleanup()


class ExperimentConfigTests(unittest.TestCase):
    def _state_with_config(self, payload: dict):
        from app import AppState
        tmp = TemporaryDirectory()
        root = Path(tmp.name)
        (root / "experiments.json").write_text(json.dumps(payload), encoding="utf-8")
        state = AppState(
            root / "company.sqlite3",
            root / "auth.sqlite3",
            root / "ai.json",
            root / "schedule.json",
            start_scheduler=False,
        )
        return state, tmp

    def test_missing_file_returns_empty(self) -> None:
        from app import AppState
        tmp = TemporaryDirectory()
        try:
            state = AppState(
                Path(tmp.name) / "company.sqlite3",
                Path(tmp.name) / "auth.sqlite3",
                Path(tmp.name) / "ai.json",
                Path(tmp.name) / "schedule.json",
                start_scheduler=False,
            )
            try:
                self.assertEqual(state.experiment_config(), [])
            finally:
                state.auth_store.close()
                state.repository.close()
        finally:
            tmp.cleanup()

    def test_filters_invalid_entries(self) -> None:
        state, tmp = self._state_with_config({
            "experiments": [
                {"id": "valid_exp", "variants": ["a", "b"]},
                {"id": "no variants", "variants": []},  # filtered (no variants)
                {"id": "bad chars!", "variants": ["a"]},  # filtered (bad id)
                {"variants": ["a"]},  # filtered (no id)
            ],
        })
        try:
            ids = [e["id"] for e in state.experiment_config()]
            self.assertEqual(ids, ["valid_exp"])
        finally:
            state.auth_store.close()
            state.repository.close()
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
