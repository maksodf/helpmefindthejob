"""Model pricing table — $/1M tokens.

Operator-facing only; never exposed to users. Updated when providers
change prices. Returns (input_$/1M_tokens, output_$/1M_tokens). Unknown
models return (0, 0) so an unrecognised model never crashes accounting
— operator just sees $0 for it until they update the table.

Prices reflect public list pricing as of Q2 2026. If your operator
contract has discounts, override via ``DIRECTJOB_PRICE_<MODEL>_IN_USD_M``
and ``..._OUT_USD_M`` env vars (e.g.
``DIRECTJOB_PRICE_CLAUDE_HAIKU_4_5_IN_USD_M=0.50``).
"""

from __future__ import annotations

import os
import re

# Map of normalised model name → (input $/1M, output $/1M)
DEFAULT_PRICES: dict[str, tuple[float, float]] = {
    # ── Anthropic ──────────────────────────────────────────────
    "claude-haiku-4-5":      (0.80, 4.00),
    "claude-sonnet-4-6":     (3.00, 15.00),
    "claude-opus-4-7":       (15.00, 75.00),
    "claude-3-5-haiku":      (0.80, 4.00),
    "claude-3-5-sonnet":     (3.00, 15.00),
    "claude-3-opus":         (15.00, 75.00),
    # ── OpenAI ─────────────────────────────────────────────────
    "gpt-4o":                (2.50, 10.00),
    "gpt-4o-mini":           (0.15, 0.60),
    "gpt-4-turbo":           (10.00, 30.00),
    "gpt-3.5-turbo":         (0.50, 1.50),
    # ── DeepSeek ───────────────────────────────────────────────
    "deepseek-chat":         (0.14, 0.28),
    "deepseek-reasoner":     (0.55, 2.19),
    # ── Google ─────────────────────────────────────────────────
    "gemini-1.5-flash":      (0.075, 0.30),
    "gemini-1.5-pro":        (1.25, 5.00),
    "gemini-2.0-flash":      (0.075, 0.30),
}


def _normalise(name: str) -> str:
    """Lower-cased, provider prefixes stripped, version suffixes
    stripped down to the base name. Handles all the date suffix
    shapes the major providers use today:

      claude-haiku-4-5-20251001  (Anthropic — 8-digit YYYYMMDD)
      gpt-4o-2024-08-06          (OpenAI — dashed YYYY-MM-DD)
      anthropic/claude-haiku-4-5 (OpenRouter — provider prefix)

    Without this, a real production model name lands as (0,0) in
    the pricing table and the cost dashboard understates spend on
    a paid model — silent revenue burn.
    """
    if not name:
        return ""
    n = name.strip().lower()
    if "/" in n:
        n = n.split("/", 1)[1]
    # Strip a trailing dashed YYYY-MM-DD first (longer form).
    n = re.sub(r"-\d{4}-\d{2}-\d{2}$", "", n)
    # Strip a trailing YYYYMMDD (8 consecutive digits) — Anthropic style.
    n = re.sub(r"-?\d{8}$", "", n)
    return n


def _env_override(model: str) -> tuple[float, float] | None:
    safe = re.sub(r"[^a-z0-9]", "_", model).upper()
    inp = os.environ.get(f"DIRECTJOB_PRICE_{safe}_IN_USD_M")
    out = os.environ.get(f"DIRECTJOB_PRICE_{safe}_OUT_USD_M")
    if inp is None or out is None:
        return None
    try:
        return float(inp), float(out)
    except ValueError:
        return None


def lookup_pricing(model: str) -> tuple[float, float]:
    """Return (input $/1M, output $/1M) for the given model. Unknown
    models return (0, 0)."""
    if not model:
        return (0.0, 0.0)
    normalised = _normalise(model)
    override = _env_override(normalised)
    if override is not None:
        return override
    return DEFAULT_PRICES.get(normalised, (0.0, 0.0))


def estimate_cost_usd(model: str, input_tokens: int,
                       output_tokens: int) -> float:
    """USD cost of one LLM call. Returns 0.0 for unknown models or
    bad inputs so accounting never crashes the chat. Defensive
    because the LLM provider sometimes returns no ``usage`` block
    on an error response — tokens land as None."""
    if not model:
        return 0.0
    try:
        it = int(input_tokens or 0)
        ot = int(output_tokens or 0)
    except (TypeError, ValueError):
        return 0.0
    if it < 0 or ot < 0:
        return 0.0
    in_price, out_price = lookup_pricing(model)
    return (it * in_price + ot * out_price) / 1_000_000.0
