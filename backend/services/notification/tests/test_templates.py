"""Template-registry tests."""

from __future__ import annotations

import pytest

from notification.app.templates import (
    SlackPayload,
    UnknownTemplateError,
    render,
)


def test_integration_revoked_includes_provider() -> None:
    out = render(
        "integration_revoked",
        {
            "provider": "github",
            "reconnect_url": "https://app.viberoi.io/settings/integrations",
        },
    )
    assert isinstance(out, SlackPayload)
    assert "github" in out.text
    assert any("github" in block.get("text", {}).get("text", "") for block in out.blocks)


def test_hallucination_loop_uses_developer_and_cost() -> None:
    out = render(
        "hallucination_loop_detected",
        {"developer_name": "Alice", "session_cost_usd": "4.20"},
    )
    assert "Alice" in out.text
    assert "4.20" in out.text


def test_unknown_template_raises() -> None:
    with pytest.raises(UnknownTemplateError):
        render("does_not_exist", {})


# ── Security: mrkdwn injection guard ────────────────────────────────────────


def test_provider_strips_mrkdwn_controls() -> None:
    """A provider value containing `<` / `>` / `|` must not survive into
    the rendered text — those are the Slack mrkdwn link-smuggle chars
    (`<url|label>` would render `label` and hide `url`). The bare hostname
    will still appear as plain text and may auto-linkify, but that's a
    visible URL rather than a smuggled one."""
    out = render(
        "integration_revoked",
        {"provider": "<https://evil.com|click>"},
    )
    assert "<" not in out.text
    assert ">" not in out.text
    assert "|" not in out.text


def test_reconnect_url_attacker_host_falls_back_to_default() -> None:
    """A reconnect_url pointing outside the allowlist must NOT be rendered
    into the Slack link — it falls back to the home page."""
    out = render(
        "integration_revoked",
        {"provider": "github", "reconnect_url": "https://evil.com/phish"},
    )
    block_texts = " ".join(b.get("text", {}).get("text", "") for b in out.blocks)
    assert "evil.com" not in block_texts
    assert "app.viberoi.io" in block_texts


def test_reconnect_url_http_scheme_falls_back() -> None:
    out = render(
        "integration_revoked",
        {"provider": "github", "reconnect_url": "http://app.viberoi.io/x"},
    )
    block_texts = " ".join(b.get("text", {}).get("text", "") for b in out.blocks)
    assert "http://app.viberoi.io" not in block_texts
    assert "https://app.viberoi.io" in block_texts


def test_developer_name_strips_mrkdwn_controls() -> None:
    out = render(
        "hallucination_loop_detected",
        {
            "developer_name": "Alice <!channel> <https://evil.com|click>",
            "session_cost_usd": "1",
        },
    )
    assert "<" not in out.text
    assert "|" not in out.text
    assert "Alice" in out.text


def test_ticket_id_strips_mrkdwn_controls() -> None:
    out = render(
        "hallucination_loop_detected",
        {
            "developer_name": "Alice",
            "session_cost_usd": "1",
            "ticket_external_id": "ABC-1 <@U123>",
        },
    )
    assert "<@U123>" not in out.text
    assert "ABC-1" in out.text
