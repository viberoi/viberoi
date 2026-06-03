"""Tests for the Slack webhook URL SSRF guard."""

from __future__ import annotations

import pytest

from viberoi_shared.notifications import assert_safe_slack_webhook_url


def test_accepts_real_slack_https_url() -> None:
    # hooks.slack.com resolves to public IPs only — fine.
    assert_safe_slack_webhook_url(
        "https://hooks.slack.com/services/T01/B01/abc"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://hooks.slack.com/services/T/B/X",  # not https
        "https://evil.com/services/T/B/X",  # wrong host
        "https://hooks.slack.com.evil.com/services",  # suffix spoof
        "https://localhost/services/T/B/X",  # localhost
        "https://127.0.0.1/services/T/B/X",  # loopback IP literal
        "https://169.254.169.254/latest/meta-data/",  # IMDS
        "https://10.0.0.1/services/T/B/X",  # RFC1918
        "https://192.168.1.1/services/T/B/X",  # RFC1918
        "https://[::1]/services/T/B/X",  # IPv6 loopback
        "ftp://hooks.slack.com/services/T/B/X",  # wrong scheme
    ],
)
def test_rejects_unsafe_url(url: str) -> None:
    with pytest.raises(ValueError):
        assert_safe_slack_webhook_url(url)


def test_rejects_unresolvable_host() -> None:
    with pytest.raises(ValueError):
        assert_safe_slack_webhook_url(
            "https://hooks.slack.com.does-not-resolve-anywhere-vibreoi-test"
        )
