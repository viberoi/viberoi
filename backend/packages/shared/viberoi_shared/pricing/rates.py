"""Model rate table + cost computation.

Rates are $/million tokens for each token kind (input / output /
cache_read / cache_write). Sourced from Anthropic + OpenAI public
pricing as of 2026-06.

When a model is unknown (new release, third-party model), we fall back
to a blended `$5/Mtok` to avoid showing $0 — clearly wrong but at least
visible in the dashboard. The session is marked `is_estimated=True`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rate:
    """Per-Mtok rates for a single model."""

    input: float
    output: float
    cache_read: float = 0.0
    cache_write: float = 0.0


# Per-Mtok rates (USD). Keys are the lower-cased model strings the
# agent reports. Add aliases as new release names emerge.
RATE_TABLE: dict[str, Rate] = {
    # Claude 4.x family (Anthropic public API pricing, June 2026)
    "claude-opus-4-7":    Rate(input=15.00, output=75.00, cache_read=1.50,  cache_write=18.75),
    "claude-opus-4-8":    Rate(input=15.00, output=75.00, cache_read=1.50,  cache_write=18.75),
    "claude-opus-4-6":    Rate(input=15.00, output=75.00, cache_read=1.50,  cache_write=18.75),
    "claude-sonnet-4-6":  Rate(input=3.00,  output=15.00, cache_read=0.30,  cache_write=3.75),
    "claude-sonnet-4-7":  Rate(input=3.00,  output=15.00, cache_read=0.30,  cache_write=3.75),
    "claude-haiku-4-5":   Rate(input=0.80,  output=4.00,  cache_read=0.08,  cache_write=1.00),
    # Claude 3.x family (still in use by some clients)
    "claude-3-5-sonnet":  Rate(input=3.00,  output=15.00, cache_read=0.30,  cache_write=3.75),
    "claude-3-5-haiku":   Rate(input=0.80,  output=4.00,  cache_read=0.08,  cache_write=1.00),
    "claude-3-opus":      Rate(input=15.00, output=75.00),
    # GitHub Copilot (subscription — $19/user/mo enterprise; rates here
    # are a blended approximation so subscription users get a dollar
    # value comparable to API users on the dashboard)
    "copilot":            Rate(input=2.00,  output=8.00),
    "gpt-4o":             Rate(input=2.50,  output=10.00),
    "gpt-4o-mini":        Rate(input=0.15,  output=0.60),
    # Cursor blended (uses multiple backend models; rough average)
    "cursor-default":     Rate(input=3.00,  output=15.00),
}

# Fallback used when the model name doesn't match anything above —
# blended $5/Mtok so the cost is non-zero but clearly approximate.
_UNKNOWN_RATE = Rate(input=5.00, output=5.00, cache_read=0.5, cache_write=0.5)


def compute_cost(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    pricing_type: str = "api_key",
) -> tuple[float, bool]:
    """Return `(cost_usd, is_estimated)`.

    `is_estimated=True` when (a) we used the fallback rate (unknown
    model) or (b) the tool is subscription-priced — the as-if-API
    figure is a comparison aid, not a real bill.
    """
    key = (model or "").strip().lower()
    rate = RATE_TABLE.get(key)
    fallback = rate is None
    if rate is None:
        rate = _UNKNOWN_RATE

    cost = (
        input_tokens * rate.input
        + output_tokens * rate.output
        + cache_read_tokens * rate.cache_read
        + cache_write_tokens * rate.cache_write
    ) / 1_000_000.0

    is_estimated = fallback or pricing_type != "api_key"
    return round(cost, 6), is_estimated
