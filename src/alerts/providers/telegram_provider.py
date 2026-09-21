"""Production Telegram alert provider - the outbound half of the channel
whose inbound side is src/api/routes/telegram_webhook.py.

Real per-district recipients come from
src/database/channel_subscriptions_db.py's get_subscribers_for_alert() -
a citizen opts in with "ALERTS ON <district>" in the exact same chat
they already use to report floods
(src/community/alert_subscription_commands.py), not a separate signup
flow. No billing tier or trial restriction of any kind here, unlike
Twilio/WhatsApp (see whatsapp_provider.py's module for that history) -
Telegram's Bot API is free for every message, always.
"""

import logging
from typing import Any, Dict

import requests

from src.alerts.models import AlertPayload
from src.alerts.providers.base import BaseAlertProvider
from src.config.settings import settings
from src.database.channel_subscriptions_db import get_subscribers_for_alert

logger = logging.getLogger("nfcc.alert.telegram")

TELEGRAM_API_BASE = "https://api.telegram.org"


def send_telegram_message(chat_id, text: str) -> Dict[str, Any]:
    """Shared by this provider (outbound alerts) and
    src/api/routes/telegram_webhook.py (inbound reply confirmations) -
    one place that knows how to actually call Telegram's sendMessage."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return {"success": False, "error": "TELEGRAM_BOT_TOKEN not configured"}
    try:
        resp = requests.post(
            f"{TELEGRAM_API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        ok = resp.status_code == 200 and bool(resp.json().get("ok"))
        return {"success": ok, "status_code": resp.status_code}
    except Exception as e:
        logger.warning("Telegram send failed for chat_id=%s: %s", chat_id, e)
        return {"success": False, "error": str(e)}


class TelegramAlertProvider(BaseAlertProvider):
    """Real Telegram provider - recipients are entirely dynamic
    (channel_subscriptions), unlike WhatsAppAlertProvider's static
    settings.WHATSAPP_RECIPIENTS fallback, since Telegram never had an
    existing static-recipient mechanism to stay backward compatible
    with."""

    name = "telegram"

    def _is_dry_run(self) -> bool:
        return getattr(settings, "ALERT_DRY_RUN", False)

    def _format_message(self, alert: AlertPayload) -> str:
        risk_emoji = {
            "LOW": "\U0001f7e2",
            "MODERATE": "\U0001f7e1",
            "HIGH": "\U0001f7e0",
            "CRITICAL": "\U0001f534",
            "EXTREME": "\U0001f480",
        }.get(alert.risk_tier, "⚠️")

        return (
            f"{risk_emoji} FLOOD ALERT: {alert.location}\n\n"
            f"Risk: {alert.risk_tier} ({alert.score:.0f}/100)\n"
            f"Rainfall: {alert.precipitation:.1f}mm\n"
            f"{alert.message}\n\n"
            f"Reply 'ALERTS OFF' to stop these messages."
        )

    def send(self, alert: AlertPayload) -> Dict[str, Any]:
        if not settings.TELEGRAM_BOT_TOKEN:
            return {
                "success": False,
                "message": "TELEGRAM_BOT_TOKEN not configured",
                "provider": self.name,
                "recipient_count": 0,
            }

        subscribers = get_subscribers_for_alert("telegram", alert.location, alert.risk_tier)

        if self._is_dry_run():
            logger.info("DRY RUN: Would send Telegram alert to %d subscriber(s)", len(subscribers))
            return {
                "success": True,
                "message": f"DRY RUN: Would send to {len(subscribers)} subscriber(s)",
                "provider": self.name,
                "recipient_count": len(subscribers),
                "dry_run": True,
            }

        if not subscribers:
            return {
                "success": False,
                "message": f"No Telegram subscribers for {alert.location} at {alert.risk_tier}",
                "provider": self.name,
                "recipient_count": 0,
            }

        message_text = self._format_message(alert)
        results = []
        for sub in subscribers:
            result = send_telegram_message(sub["identifier"], message_text)
            results.append({"to": sub["identifier"], **result})

        success_count = sum(1 for r in results if r.get("success"))

        return {
            "success": success_count > 0,
            "message": f"Telegram: {success_count}/{len(results)} delivered",
            "provider": self.name,
            "recipient_count": len(results),
            "delivery": {
                "total": len(results),
                "successful": success_count,
                "failed": len(results) - success_count,
                "details": results,
            },
        }
