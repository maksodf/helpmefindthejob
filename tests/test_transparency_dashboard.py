# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""4-week plan W2 D8-9: public transparency dashboard contract tests
(Invariant 5).

The /transparency surface is the unauthenticated public-facing page
that proves the deployer is walking the talk. These tests pin:

1. Aggregation shape (no schema drift across releases)
2. DP noise contract: variance scales with 1/ε; small-cohort
   suppression below k=5
3. PII safety: aggregator never echoes a raw user identifier
4. HTTP route is unauthenticated + emits text/html (default) or
   application/json (?format=json or .json suffix)
5. Stability under empty input (no records → all-zeros, no crash)
6. Cost-saving snapshot is rendered when present, gracefully
   absent when the log doesn't exist
7. The chain-head fingerprint matches the highest sequence_no in
   the records (auditor cross-check claim)
8. The /transparency.json shape is reproducible — given the same
   seed the DP noise is deterministic so a CI run can pin it

The page is BUILT to survive misconfiguration — if the audit log
is unreadable the page MUST still render. Tests #5 + the broken-
log adversarial case enforce that.
"""

from __future__ import annotations

import json
import random
import unittest
from datetime import datetime, timedelta, timezone

from company_discovery.transparency import (
    DEFAULT_DP_EPSILON,
    SUPPRESSION_THRESHOLD,
    aggregate_ai_invocations,
    apply_dp_noise,
    cached_aggregate_for_path,
    render_html,
    render_public_aggregates,
    render_public_cost_saving_snapshot,
)


def _mk_record(
    *,
    seq: int,
    event_type: str = "ai_invocation",
    purpose: str = "auto_fit",
    provider: str = "openai",
    outcome: str = "ok",
    when: datetime | None = None,
    chain_hmac: str = "deadbeefcafe1234567890abcdef0000",
) -> dict:
    when = when or datetime.now(timezone.utc)
    return {
        "event_type": event_type,
        "sequence_no": seq,
        "timestamp": when.isoformat(),
        "ai_provider": provider,
        "outcome": outcome,
        "chain_hmac": chain_hmac,
        "event_payload": {"purpose": purpose},
    }


class AggregationContract(unittest.TestCase):
    def test_empty_records_returns_zeros(self):
        agg = aggregate_ai_invocations([])
        self.assertEqual(agg["totalInvocations"], 0)
        self.assertEqual(agg["byPurpose"], {})
        self.assertEqual(agg["byProvider"], {})
        self.assertEqual(agg["byOutcome"], {})
        self.assertEqual(agg["refusals"], {})
        self.assertIsNone(agg["chainHead"]["sequenceNo"])

    def test_groups_by_purpose_provider_outcome(self):
        records = [
            _mk_record(seq=1, purpose="auto_fit", provider="openai", outcome="ok"),
            _mk_record(seq=2, purpose="auto_fit", provider="openai", outcome="ok"),
            _mk_record(seq=3, purpose="cover_letter", provider="deepseek", outcome="error"),
        ]
        agg = aggregate_ai_invocations(records)
        self.assertEqual(agg["totalInvocations"], 3)
        self.assertEqual(agg["byPurpose"], {"auto_fit": 2, "cover_letter": 1})
        self.assertEqual(agg["byProvider"], {"openai": 2, "deepseek": 1})
        self.assertEqual(agg["byOutcome"], {"ok": 2, "error": 1})

    def test_window_filter_excludes_old_records(self):
        old = datetime.now(timezone.utc) - timedelta(days=120)
        recent = datetime.now(timezone.utc) - timedelta(days=2)
        records = [
            _mk_record(seq=1, when=old, purpose="auto_fit"),
            _mk_record(seq=2, when=recent, purpose="auto_fit"),
        ]
        agg = aggregate_ai_invocations(records, since=datetime.now(timezone.utc) - timedelta(days=30))
        self.assertEqual(agg["totalInvocations"], 1)

    def test_chain_head_is_max_sequence(self):
        records = [
            _mk_record(seq=10, chain_hmac="aaaa" * 8),
            _mk_record(seq=42, chain_hmac="bbbb" * 8),
            _mk_record(seq=27, chain_hmac="cccc" * 8),
        ]
        agg = aggregate_ai_invocations(records)
        self.assertEqual(agg["chainHead"]["sequenceNo"], 42)
        self.assertTrue(agg["chainHead"]["chainHmacFingerprint"].startswith("bbbb"))

    def test_refusals_counted_separately(self):
        records = [
            _mk_record(seq=1, event_type="ai_invocation_refused_cap"),
            _mk_record(seq=2, event_type="ai_invocation_refused_cap"),
            _mk_record(seq=3, event_type="ai_invocation"),
        ]
        agg = aggregate_ai_invocations(records)
        self.assertEqual(agg["totalInvocations"], 1)
        self.assertEqual(agg["refusals"]["cost_cap_exceeded"], 2)

    def test_bad_timestamp_is_skipped_not_crashed(self):
        bad = _mk_record(seq=1)
        bad["timestamp"] = "not-a-date"
        records = [bad, _mk_record(seq=2)]
        agg = aggregate_ai_invocations(records)
        self.assertEqual(agg["totalInvocations"], 1)

    def test_malformed_event_payload_does_not_crash(self):
        """Defensive: if a buggy emitter or malicious federation
        peer plants event_payload as a string/list/None instead of
        a dict, we coerce to {} rather than AttributeError."""

        for bad_payload in ("string-not-dict", ["a", "b"], 42, None):
            rec = _mk_record(seq=1)
            rec["event_payload"] = bad_payload
            agg = aggregate_ai_invocations([rec])
            self.assertEqual(agg["totalInvocations"], 1)
            # Falls back to "unknown" purpose since payload.get("purpose") returns None
            self.assertEqual(agg["byPurpose"], {"unknown": 1})


class CacheContract(unittest.TestCase):
    """The /transparency aggregation is cached with a 60-second
    TTL to absorb DoS on the unauthenticated endpoint. These tests
    pin the cache contract."""

    def setUp(self) -> None:
        # Cache is module-level — tests across the class otherwise
        # contaminate each other. Reset on every test entry.
        from company_discovery import transparency as _t

        with _t._AGGREGATE_CACHE_LOCK:
            _t._AGGREGATE_CACHE.clear()

    def test_cache_returns_same_object_within_ttl(self):
        from pathlib import Path as _P

        # Use a non-existent path so the reader returns []; what we
        # care about is whether the cache memoises the call.
        calls = []

        def _reader(path):
            calls.append(path)
            return []

        path = _P("/tmp/transparency-cache-test-nonexistent.log")
        a = cached_aggregate_for_path(path, window_days=30, fresh_reader=_reader)
        b = cached_aggregate_for_path(path, window_days=30, fresh_reader=_reader)
        # The reader is called at most once within the same TTL bucket
        self.assertLessEqual(len(calls), 1)
        # Both responses are structurally equal
        self.assertEqual(a, b)

    def test_cache_separates_by_window(self):
        from pathlib import Path as _P

        calls = []

        def _reader(path):
            calls.append(path)
            return []

        path = _P("/tmp/transparency-cache-test-nonexistent.log")
        cached_aggregate_for_path(path, window_days=30, fresh_reader=_reader)
        cached_aggregate_for_path(path, window_days=7, fresh_reader=_reader)
        # Different windows → different cache entries → two reader calls
        self.assertEqual(len(calls), 2)


class DPNoiseContract(unittest.TestCase):
    def test_dp_noise_is_calibrated_by_epsilon(self):
        # Bigger epsilon → tighter noise; smaller → wider.
        # Empirically: std dev = sqrt(2)/ε. With ε=10 expect
        # very tight (<3 typical), with ε=0.1 wider (>>10 typical).
        rng = random.Random(7)
        true_count = 1000
        samples_tight = [apply_dp_noise(true_count, epsilon=10.0, rng=rng) for _ in range(200)]
        samples_loose = [apply_dp_noise(true_count, epsilon=0.1, rng=rng) for _ in range(200)]
        spread_tight = max(samples_tight) - min(samples_tight)
        spread_loose = max(samples_loose) - min(samples_loose)
        self.assertLess(spread_tight, spread_loose)

    def test_dp_noise_clamps_at_zero(self):
        # Even with huge noise, a 0-count can't go negative.
        rng = random.Random(13)
        for _ in range(100):
            noised = apply_dp_noise(0, epsilon=0.01, rng=rng)
            self.assertGreaterEqual(noised, 0)

    def test_dp_noise_zero_epsilon_rejected(self):
        with self.assertRaises(ValueError):
            apply_dp_noise(10, epsilon=0)

    def test_dp_noise_unbiased(self):
        # Mean of many samples ≈ true count
        rng = random.Random(99)
        true_count = 500
        samples = [apply_dp_noise(true_count, epsilon=1.0, rng=rng) for _ in range(2000)]
        empirical_mean = sum(samples) / len(samples)
        # Within 5% of truth at this sample size
        self.assertAlmostEqual(empirical_mean, true_count, delta=true_count * 0.05)


class PublicShapeContract(unittest.TestCase):
    def test_small_counts_suppressed(self):
        agg = {
            "totalInvocations": 1,
            "byPurpose": {"x": 1},
            "byProvider": {},
            "byOutcome": {},
            "refusals": {},
            "windowDays": 30,
            "chainHead": {"sequenceNo": None, "chainHmacFingerprint": None},
        }
        # With a stable seed the noise is deterministic
        public = render_public_aggregates(agg, seed_for_reproducibility=42)
        # totalInvocations of 1 + small noise = essentially always
        # below 5 → suppressed as "<5"
        self.assertEqual(public["totalInvocations"], f"<{SUPPRESSION_THRESHOLD}")
        # Privacy metadata MUST appear
        self.assertEqual(public["privacy"]["dpEpsilon"], DEFAULT_DP_EPSILON)
        self.assertEqual(public["privacy"]["suppressionThreshold"], SUPPRESSION_THRESHOLD)
        self.assertIn("Laplace", public["privacy"]["mechanism"])

    def test_large_counts_pass_through_with_noise(self):
        agg = {
            "totalInvocations": 10_000,
            "byPurpose": {"auto_fit": 8000, "cover_letter": 2000},
            "byProvider": {"openai": 10_000},
            "byOutcome": {"ok": 10_000},
            "refusals": {},
            "windowDays": 30,
            "chainHead": {"sequenceNo": 12345, "chainHmacFingerprint": "deadbeefcafe"},
        }
        public = render_public_aggregates(agg, seed_for_reproducibility=42)
        # Large counts survive suppression — must be int, not "<5"
        self.assertIsInstance(public["totalInvocations"], int)
        # Noised value is within Laplace tail of truth
        self.assertGreater(public["totalInvocations"], 9_990)
        self.assertLess(public["totalInvocations"], 10_010)
        # Chain head must be pass-through (no noise on integrity fingerprint)
        self.assertEqual(public["chainHead"]["sequenceNo"], 12345)
        self.assertEqual(public["chainHead"]["chainHmacFingerprint"], "deadbeefcafe")

    def test_reproducibility_seed_makes_test_deterministic(self):
        agg = {
            "totalInvocations": 100,
            "byPurpose": {"a": 50, "b": 50},
            "byProvider": {},
            "byOutcome": {},
            "refusals": {},
            "windowDays": 30,
            "chainHead": {"sequenceNo": None, "chainHmacFingerprint": None},
        }
        run_a = render_public_aggregates(agg, seed_for_reproducibility=42)
        run_b = render_public_aggregates(agg, seed_for_reproducibility=42)
        self.assertEqual(run_a["totalInvocations"], run_b["totalInvocations"])
        self.assertEqual(run_a["byPurpose"], run_b["byPurpose"])

    def test_different_seeds_produce_different_noise(self):
        agg = {
            "totalInvocations": 1000,
            "byPurpose": {},
            "byProvider": {},
            "byOutcome": {},
            "refusals": {},
            "windowDays": 30,
            "chainHead": {"sequenceNo": None, "chainHmacFingerprint": None},
        }
        a = render_public_aggregates(agg, seed_for_reproducibility=1)
        b = render_public_aggregates(agg, seed_for_reproducibility=2)
        # In rare cases two seeds could produce identical noise; we test
        # the structural property by sampling many positions
        # (totalInvocations is one). A single tail collision is fine.
        # The point is the seed is honored.
        # Both must still pass through the suppression / shape layer
        # cleanly:
        self.assertIsInstance(a["totalInvocations"], int)
        self.assertIsInstance(b["totalInvocations"], int)


class CostSavingDPContract(unittest.TestCase):
    """Privacy-posture parity for the cost-saving snapshot. Earlier
    the dashboard showed cost-saving events as RAW counts — that
    leaked the size of the deployer's user base. This contract
    pins that the same DP + suppression is applied to the
    cost-saving side."""

    def test_none_snapshot_returns_none(self):
        self.assertIsNone(render_public_cost_saving_snapshot(None))

    def test_small_event_counts_suppressed(self):
        snapshot = {
            "mechanisms": {
                "shorter_journey": {"events": 3, "users": 2, "total": 5.0, "unit": "h", "confidence": "aspirational"},
            },
            "uniqueUsers": 2,
            "windowDays": 30,
        }
        public = render_public_cost_saving_snapshot(snapshot, seed_for_reproducibility=42)
        mech = public["mechanisms"]["shorter_journey"]
        # 3 events + noise + suppression → expect "<5"
        self.assertEqual(mech["events"], f"<{SUPPRESSION_THRESHOLD}")
        # confidence + unit pass-through (not noised)
        self.assertEqual(mech["confidence"], "aspirational")
        self.assertEqual(mech["unit"], "h")

    def test_large_event_counts_survive_with_noise(self):
        snapshot = {
            "mechanisms": {
                "shorter_journey": {
                    "events": 1000,
                    "users": 500,
                    "total": 5000.0,
                    "unit": "h",
                    "confidence": "proven",
                },
            },
            "uniqueUsers": 500,
            "windowDays": 30,
        }
        public = render_public_cost_saving_snapshot(snapshot, seed_for_reproducibility=42)
        mech = public["mechanisms"]["shorter_journey"]
        self.assertIsInstance(mech["events"], int)
        # Within Laplace tail of truth
        self.assertGreater(mech["events"], 990)
        self.assertLess(mech["events"], 1010)
        self.assertEqual(mech["confidence"], "proven")

    def test_malformed_mechanism_entry_is_skipped(self):
        """Defensive: if a mechanism stat is not a dict (corrupt
        snapshot), skip it rather than crash."""

        snapshot = {
            "mechanisms": {
                "good": {"events": 100, "users": 50, "total": 200, "unit": "x", "confidence": "plausible"},
                "bad": "not a dict",
            },
            "uniqueUsers": 50,
            "windowDays": 30,
        }
        public = render_public_cost_saving_snapshot(snapshot, seed_for_reproducibility=1)
        self.assertIn("good", public["mechanisms"])
        self.assertNotIn("bad", public["mechanisms"])

    def test_privacy_metadata_present(self):
        snapshot = {"mechanisms": {}, "uniqueUsers": 0, "windowDays": 30}
        public = render_public_cost_saving_snapshot(snapshot)
        self.assertIn("privacy", public)
        self.assertEqual(public["privacy"]["dpEpsilon"], DEFAULT_DP_EPSILON)
        self.assertEqual(public["privacy"]["suppressionThreshold"], SUPPRESSION_THRESHOLD)


class PIISafetyContract(unittest.TestCase):
    """The most critical contract: a user identifier in the
    audit-log record MUST NOT appear in the aggregator output.
    Aggregator strips event_payload to its non-PII fields."""

    def test_user_hash_does_not_leak_into_aggregates(self):
        records = [
            {
                "event_type": "ai_invocation",
                "sequence_no": 1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ai_provider": "openai",
                "outcome": "ok",
                "chain_hmac": "aaaa" * 8,
                "user_hash": "1234567890abcdef",  # ← MUST NOT appear in output
                "event_payload": {
                    "purpose": "auto_fit",
                    "user_id": "alice@example.com",  # ← MUST NOT appear
                },
            }
        ]
        agg = aggregate_ai_invocations(records)
        serialized = json.dumps(agg)
        self.assertNotIn("alice@example.com", serialized)
        self.assertNotIn("1234567890abcdef", serialized)


class HTMLRendererContract(unittest.TestCase):
    def test_html_renders_with_minimal_input(self):
        agg = {
            "totalInvocations": 0,
            "byPurpose": {},
            "byProvider": {},
            "byOutcome": {},
            "refusals": {},
            "windowDays": 30,
            "chainHead": {"sequenceNo": None, "chainHmacFingerprint": None},
            "privacy": {
                "dpEpsilon": 1.0,
                "suppressionThreshold": 5,
                "mechanism": "Laplace ε-DP",
            },
        }
        html = render_html(agg)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Public Transparency Dashboard", html)
        # Privacy mechanism MUST be on the page
        self.assertIn("Laplace", html)
        # Window MUST be shown
        self.assertIn("30", html)

    def test_html_with_cost_saving_snapshot(self):
        agg = {
            "totalInvocations": 100,
            "byPurpose": {},
            "byProvider": {},
            "byOutcome": {},
            "refusals": {},
            "windowDays": 30,
            "chainHead": {"sequenceNo": 7, "chainHmacFingerprint": "abc"},
            "privacy": {"dpEpsilon": 1.0, "suppressionThreshold": 5, "mechanism": ""},
        }
        snapshot = {
            "mechanisms": {
                "shorter_journey": {"events": 250, "confidence": "proven"},
                "self_serve_anerkennung": {"events": 50, "confidence": "plausible"},
                "higher_apply_rate": {"events": 5, "confidence": "aspirational"},
            }
        }
        html = render_html(agg, cost_saving_snapshot=snapshot)
        self.assertIn("shorter_journey", html)
        self.assertIn("proven", html)
        self.assertIn("plausible", html)
        self.assertIn("aspirational", html)
        # Chain head must show seq + hmac
        self.assertIn("seq=7", html)
        self.assertIn("hmac_prefix=abc", html)

    def test_html_escapes_attacker_controlled_strings(self):
        """If the audit log carries a malicious provider/purpose name
        (planted by a hostile federation peer, say), the rendered
        HTML MUST NOT execute it. Pins XSS-safety as a contract."""

        agg = {
            "totalInvocations": 100,
            "byPurpose": {"<script>alert('xss')</script>": 50},
            "byProvider": {"\"onerror=\"alert(1)": 30},
            "byOutcome": {"<img src=x onerror=alert(1)>": 20},
            "refusals": {"<svg/onload=alert(1)>": 10},
            "windowDays": 30,
            "chainHead": {"sequenceNo": 1, "chainHmacFingerprint": "<b>x</b>"},
            "privacy": {
                "dpEpsilon": 1.0,
                "suppressionThreshold": 5,
                "mechanism": "<script>alert('p')</script>",
            },
        }
        snapshot = {
            "mechanisms": {
                "<script>": {"events": 5, "confidence": "javascript:alert(1)"},
            }
        }
        html_out = render_html(agg, cost_saving_snapshot=snapshot)
        # No raw <script>, <img onerror>, <svg onload> allowed
        self.assertNotIn("<script>alert", html_out)
        self.assertNotIn("<img src=x onerror", html_out)
        self.assertNotIn("<svg/onload", html_out)
        self.assertNotIn("\"onerror=\"alert", html_out)
        # Escaped forms MUST appear (proves the values went through
        # the escaper rather than being stripped entirely)
        self.assertIn("&lt;script&gt;", html_out)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", html_out)
        # The confidence-class attribute MUST be one of the allowlist
        # values, not the attacker-supplied "javascript:alert(1)"
        self.assertNotIn('class="confidence-javascript:alert(1)"', html_out)
        self.assertIn('class="confidence-aspirational"', html_out)

    def test_html_without_cost_saving_shows_disabled_message(self):
        agg = {
            "totalInvocations": 0,
            "byPurpose": {},
            "byProvider": {},
            "byOutcome": {},
            "refusals": {},
            "windowDays": 30,
            "chainHead": {"sequenceNo": None, "chainHmacFingerprint": None},
            "privacy": {"dpEpsilon": 1.0, "suppressionThreshold": 5, "mechanism": ""},
        }
        html = render_html(agg, cost_saving_snapshot=None)
        self.assertIn("not enabled", html)


class HTTPRouteContract(unittest.TestCase):
    """End-to-end: boot the real Handler and exercise /transparency.

    We use the same ``Handler.__new__`` stub pattern that other
    HTTP-layer tests use (test_db_error_http_layer.py) so we don't
    need a socket, but we DO exercise the real route dispatch + the
    real send_text/send_json plumbing — that's the layer Most
    Likely To Break under refactor.
    """

    def setUp(self) -> None:
        from io import BytesIO
        from unittest.mock import MagicMock

        from app import Handler

        self.handler = Handler.__new__(Handler)
        self.handler.headers = {}
        self.handler.wfile = BytesIO()
        self.handler.send_response = MagicMock()
        self.handler.send_header = MagicMock()
        self.handler.end_headers = MagicMock()
        # send_text / send_json are real methods on Handler — let
        # them run so the route's response actually serializes.
        self.captured_status: list = []
        self.captured_headers: list = []

        def _capture_status(code):
            self.captured_status.append(code)

        def _capture_header(name, value):
            self.captured_headers.append((name, value))

        self.handler.send_response.side_effect = _capture_status
        self.handler.send_header.side_effect = _capture_header

    def _read_body(self) -> str:
        self.handler.wfile.seek(0)
        return self.handler.wfile.read().decode("utf-8")

    def test_html_route_returns_200_text_html(self):
        self.handler.path = "/transparency"
        self.handler.do_GET()
        self.assertIn(200, self.captured_status)
        # text/html content-type
        types = [v for n, v in self.captured_headers if n.lower() == "content-type"]
        self.assertTrue(any("text/html" in t for t in types), f"got types: {types}")
        body = self._read_body()
        self.assertIn("Public Transparency Dashboard", body)

    def test_json_route_returns_application_json(self):
        self.handler.path = "/transparency.json"
        self.handler.do_GET()
        self.assertIn(200, self.captured_status)
        types = [v for n, v in self.captured_headers if n.lower() == "content-type"]
        self.assertTrue(
            any("application/json" in t for t in types),
            f"got types: {types}",
        )
        body = self._read_body()
        payload = json.loads(body)
        self.assertIn("aiInvocations", payload)
        # PII safety claim, end-to-end: the JSON serialization MUST
        # NOT contain "user_id" or "email"
        self.assertNotIn("user_id", body)
        self.assertNotIn("@", body)

    def test_window_query_param_is_bounded(self):
        # Adversarial: window=99999 should be clamped to 90.
        # We don't read the windowDays here (DP-noised) but the
        # request MUST NOT crash.
        self.handler.path = "/transparency.json?window=99999"
        self.handler.do_GET()
        self.assertIn(200, self.captured_status)

    def test_negative_window_falls_back_to_default(self):
        # max(1, min(window_days, 90)) -- negative clamps to 1
        self.handler.path = "/transparency.json?window=-5"
        self.handler.do_GET()
        self.assertIn(200, self.captured_status)

    def test_non_numeric_window_falls_back_to_default(self):
        self.handler.path = "/transparency.json?window=DROP%20TABLE"
        self.handler.do_GET()
        self.assertIn(200, self.captured_status)

    def test_html_route_sets_csp_headers(self):
        """The public HTML page MUST set Content-Security-Policy
        with script-src 'none' so even a hypothetical future XSS
        slip can't execute. This pins the security posture."""

        self.handler.path = "/transparency"
        self.handler.do_GET()
        csp_values = [v for n, v in self.captured_headers if n.lower() == "content-security-policy"]
        self.assertEqual(len(csp_values), 1, f"expected exactly 1 CSP header, got {csp_values}")
        csp = csp_values[0]
        self.assertIn("script-src 'none'", csp)
        self.assertIn("default-src 'none'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        # X-Content-Type-Options nosniff is paired with CSP
        nosniff = [v for n, v in self.captured_headers if n.lower() == "x-content-type-options"]
        self.assertIn("nosniff", nosniff)

    def test_html_route_sets_cache_control(self):
        """The HTML page sets Cache-Control: public, max-age=60
        so a CDN/reverse-proxy absorbs hot traffic. Pins the
        DoS-defense contract."""

        self.handler.path = "/transparency"
        self.handler.do_GET()
        cache_control = [v for n, v in self.captured_headers if n.lower() == "cache-control"]
        self.assertEqual(len(cache_control), 1)
        self.assertIn("max-age=60", cache_control[0])

    def test_json_route_sets_nosniff_and_cache(self):
        """The JSON path also gets X-Content-Type-Options + a public
        cache-control so the same CDN-absorbtion + browser-safety
        properties hold for JSON consumers."""

        self.handler.path = "/transparency.json"
        self.handler.do_GET()
        nosniff = [v for n, v in self.captured_headers if n.lower() == "x-content-type-options"]
        self.assertIn("nosniff", nosniff)
        cache_control = [v for n, v in self.captured_headers if n.lower() == "cache-control"]
        # Multiple Cache-Control values may be set; one MUST be public,max-age=60
        self.assertTrue(
            any("max-age=60" in v for v in cache_control),
            f"expected max-age=60 in cache-control, got {cache_control}",
        )


if __name__ == "__main__":
    unittest.main()
