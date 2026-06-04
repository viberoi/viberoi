"""Pricing module: per-model rate math + fallback behavior."""

import pytest

from viberoi_shared.pricing import compute_cost


def test_claude_opus_input_only() -> None:
    cost, est = compute_cost(
        model="claude-opus-4-7",
        input_tokens=1_000_000,
        output_tokens=0,
    )
    assert cost == pytest.approx(15.0)
    assert est is False


def test_claude_opus_mixed_tokens() -> None:
    # 100k input + 50k output @ Opus rates
    cost, _ = compute_cost(
        model="claude-opus-4-7",
        input_tokens=100_000,
        output_tokens=50_000,
        cache_read_tokens=200_000,
        cache_write_tokens=10_000,
    )
    expected = (100_000 * 15 + 50_000 * 75 + 200_000 * 1.5 + 10_000 * 18.75) / 1_000_000
    assert cost == pytest.approx(expected)


def test_sonnet_cheaper_than_opus() -> None:
    a, _ = compute_cost(model="claude-sonnet-4-6", input_tokens=1_000_000, output_tokens=0)
    b, _ = compute_cost(model="claude-opus-4-7", input_tokens=1_000_000, output_tokens=0)
    assert a < b


def test_unknown_model_uses_fallback_and_flags_estimated() -> None:
    cost, est = compute_cost(model="unknown-llm-2099", input_tokens=1_000_000, output_tokens=0)
    assert cost == pytest.approx(5.0)
    assert est is True


def test_subscription_flagged_estimated_even_for_known_model() -> None:
    _, est = compute_cost(
        model="claude-opus-4-7",
        input_tokens=1000,
        output_tokens=0,
        pricing_type="subscription",
    )
    assert est is True


def test_case_insensitive_and_whitespace_tolerant() -> None:
    a, _ = compute_cost(model="Claude-Opus-4-7", input_tokens=1000, output_tokens=0)
    b, _ = compute_cost(model="  claude-opus-4-7  ", input_tokens=1000, output_tokens=0)
    c, _ = compute_cost(model="claude-opus-4-7", input_tokens=1000, output_tokens=0)
    assert a == b == c


def test_zero_tokens_zero_cost() -> None:
    cost, _ = compute_cost(model="claude-opus-4-7", input_tokens=0, output_tokens=0)
    assert cost == 0.0
