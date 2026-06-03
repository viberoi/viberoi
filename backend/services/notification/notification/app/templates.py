"""Notification template registry.

A template is a function: `payload: dict -> ChannelPayload`. Lookup
by name happens in the consumer; unknown templates ack-and-log
(unrecoverable — there's no point retrying a typo).

Adding a template:
  1. Add a function below that builds a `SlackPayload` (or
     `EmailPayload` once V2 lands).
  2. Register it in `TEMPLATES`.
  3. Add a test in `tests/test_templates.py`.

Templates NEVER fetch user content, decode PII, or look anything up.
The caller of `enqueue` puts everything the template needs into
`payload`. This keeps templates safe to render in a Lambda-style
context.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

# Slack mrkdwn control characters. A payload value embedded into mrkdwn
# can otherwise spoof links (`<url|label>`), inject `@channel` mentions,
# or close/reopen formatting. We strip these from every free-text
# payload value before interpolation.
_SLACK_MRKDWN_CONTROL_CHARS = "<>|&@#!"

# Hosts a `reconnect_url` (or any other template-supplied URL) is allowed
# to point at. Anything else falls back to the home page link; the
# template never embeds a caller-controlled hostname into a Slack link.
_ALLOWED_LINK_HOSTS = frozenset(
    {"app.viberoi.io", "staging.viberoi.io", "localhost"}
)
_DEFAULT_RECONNECT_URL = "https://app.viberoi.io/settings/integrations"


def _safe_text(value: Any, *, fallback: str = "?") -> str:
    """Strip Slack mrkdwn control chars from a payload value."""
    if value is None:
        return fallback
    s = str(value)
    return "".join(c for c in s if c not in _SLACK_MRKDWN_CONTROL_CHARS)


def _safe_link_url(value: Any, *, fallback: str = _DEFAULT_RECONNECT_URL) -> str:
    """Return `value` if it's an https URL pointing at an allowed host,
    otherwise fall back. Prevents the template from rendering a Slack
    link to an attacker-controlled host."""
    if not value:
        return fallback
    parsed = urlparse(str(value))
    if parsed.scheme != "https":
        return fallback
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_LINK_HOSTS:
        return fallback
    return parsed.geturl()


@dataclass(frozen=True)
class SlackPayload:
    """What we POST to a Slack incoming webhook.

    `text` is the plaintext fallback (shown in notification preview
    and in clients that can't render blocks).
    """

    text: str
    blocks: list[dict[str, Any]]


def _slack_section(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


# ── Template renderers ────────────────────────────────────────────────────


def _integration_revoked(payload: dict[str, Any]) -> SlackPayload:
    provider = _safe_text(payload.get("provider"))
    reason = _safe_text(payload.get("reason"), fallback="token_refresh_failed")
    reconnect_url = _safe_link_url(payload.get("reconnect_url"))
    text = (
        f"VibeROI: your *{provider}* integration was revoked "
        f"({reason}). Re-connect to resume tracking."
    )
    blocks = [
        _slack_section(text),
        _slack_section(f"<{reconnect_url}|Open VibeROI settings>"),
    ]
    return SlackPayload(text=text, blocks=blocks)


def _hallucination_loop_detected(payload: dict[str, Any]) -> SlackPayload:
    cost = _safe_text(payload.get("session_cost_usd"))
    developer = _safe_text(payload.get("developer_name"), fallback="a teammate")
    ticket = _safe_text(payload.get("ticket_external_id"), fallback="")
    ticket_str = f" on *{ticket}*" if ticket else ""
    text = (
        f"VibeROI: hallucination-loop signal triggered for {developer}"
        f"{ticket_str}. Session cost: ${cost}."
    )
    return SlackPayload(text=text, blocks=[_slack_section(text)])


# ── Registry ──────────────────────────────────────────────────────────────


TEMPLATES: dict[str, Callable[[dict[str, Any]], SlackPayload]] = {
    "integration_revoked": _integration_revoked,
    "hallucination_loop_detected": _hallucination_loop_detected,
}


class UnknownTemplateError(Exception):
    """Raised when `enqueue` ships a template name the consumer doesn't know.

    The consumer acks + logs — no retry will fix a typo. Distinct
    exception type so the consumer can distinguish "unknown" (ack)
    from "delivery failed" (don't ack).
    """


def render(template: str, payload: dict[str, Any]) -> SlackPayload:
    fn = TEMPLATES.get(template)
    if fn is None:
        raise UnknownTemplateError(template)
    return fn(payload)
