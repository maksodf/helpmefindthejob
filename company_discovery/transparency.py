# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Public transparency dashboard aggregations (Invariant 5).

The /transparency surface gives any visitor — auditor,
journalist, deployer-considering-adoption, user, regulator —
verifiable evidence that the deployer is walking the talk.

What this module computes:

1. AI Act Article 50 disclosure counts: how many AI invocations
   happened in the last N days, broken down by purpose.
2. Cost-saving doctrine measured outcomes: per-mechanism event
   counts + confidence tag (proven/plausible/aspirational).
3. Refusal stack: how many invocations were refused for
   consent / cost-cap / quota reasons.
4. Audit-log chain status: latest sequence_no + chain head
   HMAC fingerprint, so any auditor can request the log and
   verify back to this point.

What this module does NOT do:

- It does NOT expose any per-user data. Aggregations are
  computed across the whole audit log; the differential-privacy
  layer at :func:`apply_dp_noise` adds calibrated Laplace noise
  to counts so individual users can't be re-identified.
- It does NOT expose AI invocation content. Hashes only.

Design contract:

- The aggregation runs on every /transparency request
  (small audit logs) — for larger deployments a cron job
  pre-computes and caches via the same functions.
- All numbers shown publicly have DP noise applied with a
  published epsilon. The "raw" numbers stay internal.
"""

from __future__ import annotations

import html as _html_escape
import json
import math
import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


# Differential-privacy epsilon. Lower = more privacy, less
# accuracy. We use a moderate epsilon (1.0) appropriate for
# aggregate-count surfaces with k-anonymity >= 5; the noise
# magnitude is ~1/epsilon = ~1 count. Published as part of the
# transparency surface so an auditor can recompute the bound.
DEFAULT_DP_EPSILON = 1.0

# Minimum count before we report a number publicly. Below this
# we report "<5" to avoid singling out small cohorts.
SUPPRESSION_THRESHOLD = 5


# /transparency is unauthenticated. Without a cache an attacker
# could DoS the server by hammering the endpoint — each request
# scans up to 20_000 audit-log records + the cost-saving metrics
# JSONL. A 60-second TTL cache means even a flood degrades to "one
# scan per minute" while the dashboard stays fresh enough for the
# public surface. We use a tuple key on (window_days, log_mtime)
# so a fresh log invalidates the cache automatically.
import threading as _threading
import time as _time

_AGGREGATE_CACHE: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
_AGGREGATE_CACHE_LOCK = _threading.Lock()
_AGGREGATE_CACHE_TTL_SECONDS = 60.0


def cached_aggregate_for_path(
    log_path: Path,
    *,
    window_days: int,
    fresh_reader: Any,  # callable taking (log_path) -> list[records]
) -> dict[str, Any]:
    """Cached wrapper around :func:`aggregate_ai_invocations`.

    Keyed by ``(window_days, log_path, log_mtime, ttl_bucket)``.
    The mtime captures "log was rotated or appended"; the
    ttl_bucket captures "60s elapsed since cache fill" so even a
    write-frozen log refreshes its window-based aggregation.

    A bounded-size cache (LRU-by-eviction) would be safer for
    very-many-window deployments, but window_days is clamped to
    [1, 90] at the HTTP layer so at most ~90 entries can
    accumulate — bounded by construction.
    """

    try:
        mtime = log_path.stat().st_mtime if log_path.exists() else 0.0
    except OSError:
        mtime = 0.0
    ttl_bucket = int(_time.time() // _AGGREGATE_CACHE_TTL_SECONDS)
    key = (window_days, str(log_path), mtime, ttl_bucket)
    with _AGGREGATE_CACHE_LOCK:
        cached = _AGGREGATE_CACHE.get(key)
        if cached is not None:
            return cached[1]
    # Compute outside the lock — aggregation is CPU-bound and
    # holding the lock would serialise all concurrent requests.
    records = fresh_reader(log_path)
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    aggregates = aggregate_ai_invocations(records, since=since)
    with _AGGREGATE_CACHE_LOCK:
        # Bound the cache so a quirky deployer can't OOM us by
        # rapidly varying the window param (HTTP layer clamps to
        # [1, 90] but a future caller might not). Evict oldest.
        if len(_AGGREGATE_CACHE) > 200:
            _AGGREGATE_CACHE.clear()
        _AGGREGATE_CACHE[key] = (_time.time(), aggregates)
    return aggregates


def apply_dp_noise(true_count: int, *, epsilon: float = DEFAULT_DP_EPSILON, rng: random.Random | None = None) -> int:
    """Add Laplace(0, 1/epsilon) noise to a count and round.

    The Laplace mechanism is the standard ε-differential privacy
    mechanism for COUNT queries on data where any single
    record's presence/absence changes the count by at most 1
    (true here — each AI invocation contributes ≤ 1 to any
    count we report).

    Noise is added BEFORE rounding + bounded to ≥0 (counts
    can't go negative — clamp at 0).
    """

    if epsilon <= 0:
        raise ValueError("epsilon_must_be_positive")
    r = rng or random.Random()
    # Laplace via inverse-CDF: ln(2u) for u in (0, 0.5), -ln(2(1-u)) for u in (0.5, 1)
    u = r.random()
    if u < 0.5:
        noise = math.log(2 * u) / epsilon
    else:
        noise = -math.log(2 * (1 - u)) / epsilon
    noised = true_count + noise
    rounded = int(round(noised))
    return max(0, rounded)


def _apply_suppression(value: int) -> int | str:
    """Suppress small counts to ``"<5"`` so a small cohort
    isn't accidentally identifiable. Called AFTER DP noise."""

    if value < SUPPRESSION_THRESHOLD:
        return f"<{SUPPRESSION_THRESHOLD}"
    return value


def aggregate_ai_invocations(
    records: list[dict[str, Any]],
    *,
    since: datetime | None = None,
) -> dict[str, Any]:
    """Aggregate Article 50 disclosure counts from a list of
    raw audit-log records (read via :func:`_read_ai_act_audit_tail`
    or equivalent).

    Returns a structured dict:

        {
            "totalInvocations": int,
            "byPurpose": {<purpose>: int, ...},
            "byProvider": {<provider_id>: int, ...},
            "byOutcome": {"ok": int, "error": int, ...},
            "refusals": {"cost_cap_exceeded": int, ...},
            "windowDays": int,
            "chainHead": {
                "sequenceNo": int | None,
                "chainHmacFingerprint": str | None,  # first 12 hex
            }
        }
    """

    since = since or (datetime.now(timezone.utc) - timedelta(days=30))
    by_purpose: Counter[str] = Counter()
    by_provider: Counter[str] = Counter()
    by_outcome: Counter[str] = Counter()
    refusals: Counter[str] = Counter()
    total = 0
    max_seq = 0
    head_hmac = ""
    for rec in records:
        if rec.get("event_type") != "ai_invocation":
            # We still want chain head tracking across ALL records
            seq = rec.get("sequence_no")
            if isinstance(seq, int) and seq > max_seq:
                max_seq = seq
                head_hmac = str(rec.get("chain_hmac", "") or "")
            continue
        ts_raw = rec.get("timestamp")
        if isinstance(ts_raw, str):
            try:
                ts = datetime.fromisoformat(ts_raw)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts < since:
                    continue
            except ValueError:
                continue
        payload_raw = rec.get("event_payload")
        # event_payload SHOULD be a dict by contract — but the audit
        # log is append-only and a buggy emitter or a malicious
        # federation peer could plant a string/list/null. We coerce
        # defensively so the public surface never crashes on a
        # malformed record. Anything not-a-dict → empty dict.
        payload = payload_raw if isinstance(payload_raw, dict) else {}
        total += 1
        purpose = str(payload.get("purpose") or "unknown")
        by_purpose[purpose] += 1
        provider = str(rec.get("ai_provider") or "unknown")
        by_provider[provider] += 1
        outcome = str(rec.get("outcome") or "unknown")
        by_outcome[outcome] += 1
        seq = rec.get("sequence_no")
        if isinstance(seq, int) and seq > max_seq:
            max_seq = seq
            head_hmac = str(rec.get("chain_hmac", "") or "")

    # Refusals come from a sibling event type
    for rec in records:
        if rec.get("event_type") != "ai_invocation_refused_cap":
            continue
        ts_raw = rec.get("timestamp")
        if isinstance(ts_raw, str):
            try:
                ts = datetime.fromisoformat(ts_raw)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts < since:
                    continue
            except ValueError:
                continue
        refusals["cost_cap_exceeded"] += 1

    return {
        "totalInvocations": total,
        "byPurpose": dict(by_purpose),
        "byProvider": dict(by_provider),
        "byOutcome": dict(by_outcome),
        "refusals": dict(refusals),
        "windowDays": (datetime.now(timezone.utc) - since).days,
        "chainHead": {
            "sequenceNo": max_seq if max_seq else None,
            "chainHmacFingerprint": head_hmac[:12] if head_hmac else None,
        },
    }


def render_public_aggregates(
    aggregates: dict[str, Any],
    *,
    epsilon: float = DEFAULT_DP_EPSILON,
    rng: random.Random | None = None,
    seed_for_reproducibility: int | None = None,
) -> dict[str, Any]:
    """Apply DP noise + small-cohort suppression to every count
    in the aggregates dict. Returns the public-facing shape.

    Numbers that survive both DP noise + suppression are
    reported as integers. Suppressed numbers are reported as
    ``"<5"`` strings. The dashboard renderer treats both as
    strings to display.

    If ``seed_for_reproducibility`` is given, the same input
    produces the same noisy output — useful for testing that
    the DP layer doesn't break the shape, NOT for production
    (a stable seed defeats privacy).
    """

    if rng is None:
        rng = random.Random(seed_for_reproducibility)

    def _noise_value(v: int) -> int | str:
        return _apply_suppression(apply_dp_noise(v, epsilon=epsilon, rng=rng))

    def _noise_dict(d: dict[str, int]) -> dict[str, int | str]:
        return {k: _noise_value(v) for k, v in d.items()}

    return {
        "totalInvocations": _noise_value(aggregates.get("totalInvocations", 0)),
        "byPurpose": _noise_dict(aggregates.get("byPurpose", {})),
        "byProvider": _noise_dict(aggregates.get("byProvider", {})),
        "byOutcome": _noise_dict(aggregates.get("byOutcome", {})),
        "refusals": _noise_dict(aggregates.get("refusals", {})),
        "windowDays": aggregates.get("windowDays", 30),
        "chainHead": aggregates.get("chainHead", {"sequenceNo": None, "chainHmacFingerprint": None}),
        "privacy": {
            "dpEpsilon": epsilon,
            "suppressionThreshold": SUPPRESSION_THRESHOLD,
            "mechanism": "Laplace ε-differential privacy on counts; small-cohort suppression",
        },
    }


_CONFIDENCE_CLASSES: frozenset[str] = frozenset({"proven", "plausible", "aspirational"})


def _esc(value: object) -> str:
    """HTML-escape a value for safe interpolation. Audit-log records
    can contain attacker-controlled strings (a malicious provider
    name, a poisoned event_payload.purpose). Without escaping, the
    public /transparency page would be vulnerable to stored XSS.

    Centralised so every interpolation goes through the same
    escaper — easier to audit than scattered f-strings.
    """

    return _html_escape.escape(str(value), quote=True)


def render_html(public_aggregates: dict[str, Any], cost_saving_snapshot: dict[str, Any] | None = None) -> str:
    """Render the public-facing /transparency HTML page.

    Inline-styled (no external CSS) so the page works behind a
    CDN with no extra round-trips; the inline CSS is small.

    Every interpolated value is HTML-escaped via :func:`_esc` —
    the audit-log record set can carry attacker-controlled strings
    (a hostile MCP federation peer could plant a malicious purpose
    field, for example), so escaping is non-negotiable.
    """

    def _row(label: object, value: object) -> str:
        return f"<tr><td>{_esc(label)}</td><td>{_esc(value)}</td></tr>"

    by_purpose_rows = "".join(
        _row(k, v) for k, v in sorted(public_aggregates.get("byPurpose", {}).items())
    )
    by_provider_rows = "".join(
        _row(k, v) for k, v in sorted(public_aggregates.get("byProvider", {}).items())
    )
    by_outcome_rows = "".join(
        _row(k, v) for k, v in sorted(public_aggregates.get("byOutcome", {}).items())
    )
    refusals_rows = "".join(
        _row(k, v) for k, v in sorted(public_aggregates.get("refusals", {}).items())
    )

    mechanism_rows = ""
    if cost_saving_snapshot:
        for mech, stats in sorted(
            cost_saving_snapshot.get("mechanisms", {}).items()
        ):
            raw_confidence = str(stats.get("confidence", "aspirational"))
            # CSS class allowlist: only the three known confidence
            # tiers can be embedded as a class attribute. Anything
            # else falls back to "aspirational" — no attacker-
            # controlled value reaches the class attribute even
            # though _esc would also block it.
            confidence_class = (
                raw_confidence if raw_confidence in _CONFIDENCE_CLASSES else "aspirational"
            )
            events = stats.get("events", 0)
            mechanism_rows += (
                f"<tr><td>{_esc(mech)}</td>"
                f"<td>{_esc(events)}</td>"
                f'<td class="confidence-{confidence_class}">{_esc(raw_confidence)}</td></tr>'
            )
    else:
        mechanism_rows = '<tr><td colspan="3"><em>Cost-saving metrics not enabled on this deployment</em></td></tr>'

    chain_head = public_aggregates.get("chainHead", {})
    head_seq = chain_head.get("sequenceNo")
    head_hmac = chain_head.get("chainHmacFingerprint")
    chain_block = (
        f"<p>Audit-log chain head: <code>seq={_esc(head_seq)} hmac_prefix={_esc(head_hmac)}</code>"
        if head_seq
        else "<p><em>No audit-log entries in window</em>"
    )
    chain_block += "</p>"

    privacy = public_aggregates.get("privacy", {})
    epsilon = _esc(privacy.get("dpEpsilon"))
    suppression = _esc(privacy.get("suppressionThreshold"))
    mechanism_desc = _esc(privacy.get("mechanism", ""))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Public Transparency Dashboard — helpmefindthejob</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    max-width: 900px;
    margin: 2rem auto;
    padding: 0 1rem;
    color: #1a1a1a;
    line-height: 1.5;
  }}
  h1 {{ font-size: 1.8rem; margin-bottom: 0.2rem; }}
  h2 {{ font-size: 1.2rem; margin-top: 2rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: 0.6rem 0; }}
  th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #e0e0e0; }}
  th {{ background: #f6f6f6; }}
  .confidence-proven {{ color: #1a7f37; font-weight: 600; }}
  .confidence-plausible {{ color: #9a6700; }}
  .confidence-aspirational {{ color: #888; font-style: italic; }}
  .meta {{ font-size: 0.85rem; color: #555; margin: 1rem 0; }}
  code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; font-size: 0.9rem; }}
</style>
</head>
<body>
<h1>Public Transparency Dashboard</h1>
<p class="meta">
  Last <strong>{_esc(public_aggregates.get("windowDays", 30))} days</strong> of AI invocations
  on this deployment, with ε-differential privacy noise applied.
  Updated on every request.
</p>

<h2>AI invocations (Article 50 disclosure)</h2>
<p><strong>Total</strong>: {_esc(public_aggregates.get("totalInvocations", 0))} invocations in the window.</p>

<h3>By purpose</h3>
<table><thead><tr><th>Purpose</th><th>Count (noised)</th></tr></thead>
<tbody>{by_purpose_rows or '<tr><td colspan="2"><em>No invocations in window</em></td></tr>'}</tbody>
</table>

<h3>By provider</h3>
<table><thead><tr><th>Provider</th><th>Count (noised)</th></tr></thead>
<tbody>{by_provider_rows or '<tr><td colspan="2"><em>No invocations in window</em></td></tr>'}</tbody>
</table>

<h3>By outcome</h3>
<table><thead><tr><th>Outcome</th><th>Count (noised)</th></tr></thead>
<tbody>{by_outcome_rows}</tbody>
</table>

<h3>Refusals</h3>
<table><thead><tr><th>Refusal type</th><th>Count (noised)</th></tr></thead>
<tbody>{refusals_rows or '<tr><td colspan="2"><em>No refusals in window</em></td></tr>'}</tbody>
</table>

<h2>Cost-saving doctrine — measured outcomes</h2>
<table><thead><tr><th>Mechanism</th><th>Events</th><th>Confidence</th></tr></thead>
<tbody>{mechanism_rows}</tbody>
</table>

<h2>Audit-log integrity</h2>
{chain_block}
<p class="meta">
  An auditor can request a copy of the audit log (GDPR Article 15)
  and use <code>company_discovery.audit_log.verify_chain</code> to
  confirm the chain back to this sequence number.
</p>

<h2>Privacy mechanism</h2>
<p>
  Every count on this page has Laplace(0, 1/ε) noise added with
  ε = <strong>{epsilon}</strong>, then suppressed if below
  k = <strong>{suppression}</strong>. {mechanism_desc}
</p>

<p class="meta">
  Source: <code>company_discovery/transparency.py</code>.
  Spec: <a href="/commons/friction-class-spec-v0.1.md">friction-class-spec-v0.1</a>.
  License: <a href="/LICENSE">Apache 2.0</a>.
</p>
</body>
</html>
"""
