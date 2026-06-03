"""Destination guards for outbound notification webhooks.

The Notification service POSTs to URLs that come out of the
`notification_channels` table. The encryption-at-rest decision protects
the URL on disk / in logs, but does nothing to constrain *where* the
consumer connects when the URL is decrypted.

These guards are the single anti-SSRF control. They run at write time
(repository.upsert_channel) AND at consume time (Notification service)
so the live URL is checked at both sides — defense in depth.

V1 scope: only Slack. Teams / generic webhooks add their own guard
when those channels land.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# The single allowed Slack incoming-webhook host. Slack publishes this as
# stable in their docs; if/when Slack moves the URL we ship a new release.
_SLACK_WEBHOOK_HOST = "hooks.slack.com"


def assert_safe_slack_webhook_url(url: str) -> None:
    """Raise `ValueError` unless `url` is a real-Slack-host HTTPS webhook.

    Checks (in order — fail fast):
      1. Scheme must be `https`.
      2. Hostname must be exactly `hooks.slack.com` (case-insensitive).
      3. Resolved IP address(es) must all be public — no RFC1918, no
         loopback, no link-local, no multicast, no reserved. This is a
         belt-and-braces check against DNS rebinding; (2) alone should
         be sufficient since Slack controls the DNS.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Webhook URL must use https.")
    host = (parsed.hostname or "").lower()
    if host != _SLACK_WEBHOOK_HOST:
        raise ValueError("Webhook host is not a Slack incoming-webhook host.")
    # Belt-and-braces: resolve and reject any private IP.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise ValueError("Webhook host did not resolve.") from e
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            # Unparseable address — treat as unsafe.
            raise ValueError("Webhook host resolved to unparseable address.") from None
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise ValueError(
                "Webhook host resolved to a non-public IP address."
            )
