"""Shared "ALERTS ON/OFF" command parsing for the WhatsApp and Telegram
citizen-reporting webhooks - lets a citizen opt into outbound flood
alerts through the exact same chat they already use to report floods
(src/api/routes/whatsapp_webhook.py, telegram_webhook.py), rather than
a separate signup flow. Real recipients are read from
src/database/channel_subscriptions_db.py by
src/alerts/providers/whatsapp_provider.py and telegram_provider.py on
every real alert send.

Reuses report_parsing.py's own district/community matching (word-
boundary, exact-match-only - no fuzzy guessing) so "ALERTS ON Kaneshie"
resolves to "Accra Central" the same way free-text report parsing does,
and an unrecognized place name is reported back rather than silently
subscribing to the wrong thing or to everything.
"""

import re
from typing import NamedTuple, Optional

from src.community.report_parsing import extract_location
from src.database import channel_subscriptions_db


class SubscriptionCommand(NamedTuple):
    action: str  # "subscribe" | "unsubscribe"
    district: Optional[str]  # None means "all districts"
    recognized: bool  # False if a district name was given but not matched


_ON_RE = re.compile(r"^\s*alerts?\s+on\b(.*)$", re.IGNORECASE | re.DOTALL)
_OFF_RE = re.compile(r"^\s*(alerts?\s+off|stop|unsubscribe)\s*$", re.IGNORECASE)
_ALL_KEYWORDS = {"all", "everywhere", "everything", "any", "anywhere"}


def parse_subscription_command(text: str) -> Optional[SubscriptionCommand]:
    """Returns None if `text` isn't a subscription command at all - the
    caller should fall through to normal report parsing in that case."""
    stripped = text.strip()

    if _OFF_RE.match(stripped):
        return SubscriptionCommand(action="unsubscribe", district=None, recognized=True)

    on_match = _ON_RE.match(stripped)
    if not on_match:
        return None

    remainder = on_match.group(1).strip()
    if not remainder or remainder.lower() in _ALL_KEYWORDS:
        return SubscriptionCommand(action="subscribe", district=None, recognized=True)

    district, _community = extract_location(remainder)
    if district:
        return SubscriptionCommand(
            action="subscribe", district=district, recognized=True
        )
    return SubscriptionCommand(action="subscribe", district=None, recognized=False)


def handle_subscription_command(
    channel: str, identifier: str, text: str
) -> Optional[str]:
    """If `text` is an ALERTS ON/OFF command, applies it (real DB write)
    and returns the reply text. Returns None if it wasn't a subscription
    command at all, so the caller falls through to normal report
    handling - this function has no side effect in that case."""
    command = parse_subscription_command(text)
    if command is None:
        return None

    if command.action == "unsubscribe":
        channel_subscriptions_db.unsubscribe(channel, identifier)
        return "You've been unsubscribed from flood alerts. Reply 'ALERTS ON' any time to resubscribe."

    if not command.recognized:
        return (
            "We didn't recognize that district. Reply 'ALERTS ON' for all "
            "districts, or 'ALERTS ON <district or community name>' for a "
            "specific one, e.g. 'ALERTS ON Kaneshie'."
        )

    channel_subscriptions_db.subscribe(channel, identifier, district=command.district)
    where = command.district or "all tracked districts"
    return (
        f"You're now subscribed to flood alerts for {where}. "
        "Reply 'ALERTS OFF' any time to stop."
    )
