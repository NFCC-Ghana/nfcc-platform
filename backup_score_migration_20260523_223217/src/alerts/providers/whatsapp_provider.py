"""WhatsApp alert provider using Twilio WhatsApp API."""

import logging
import os
from typing import Dict, Any, List

from src.alerts.providers.base import BaseAlertProvider
from src.alerts.models import AlertPayload

logger = logging.getLogger("nfcc.alert.whatsapp")

try:
    from twilio.rest import Client

    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning(
        "Twilio not installed. WhatsApp provider will be limited to mock mode."
    )


class WhatsAppAlertProvider(BaseAlertProvider):
    """WhatsApp provider that sends alerts via Twilio WhatsApp API."""

    name = "whatsapp"

    def __init__(self, recipients: List[str] = None, **kwargs):
        """
        Initialize WhatsApp provider.

        Args:
            recipients: List of phone numbers with country code
            account_sid: Twilio account SID (default from env)
            auth_token: Twilio auth token (default from env)
            from_number: Twilio WhatsApp number (default from env)
        """
        self.recipients = recipients or os.getenv(
            "ALERT_WHATSAPP_RECIPIENTS", ""
        ).split(",")
        self.account_sid = kwargs.get("account_sid", os.getenv("TWILIO_ACCOUNT_SID"))
        self.auth_token = kwargs.get("auth_token", os.getenv("TWILIO_AUTH_TOKEN"))
        self.from_number = kwargs.get(
            "from_number", os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
        )

        # Ensure from_number has whatsapp: prefix
        if not self.from_number.startswith("whatsapp:"):
            self.from_number = f"whatsapp:{self.from_number}"

        if not self.recipients or not self.recipients[0]:
            raise ValueError("WhatsApp recipients must be configured")

    def send(self, payload: AlertPayload) -> Dict[str, Any]:
        """
        Send WhatsApp alert.

        Args:
            payload: AlertPayload object

        Returns:
            Success response or error
        """
        self.validate_payload(payload)

        message_text = self._format_message(payload)
        results = []

        for recipient in self.recipients:
            # Ensure recipient has whatsapp: prefix
            if not recipient.startswith("whatsapp:"):
                recipient = f"whatsapp:{recipient}"

            for attempt in range(3):
                try:
                    if TWILIO_AVAILABLE and self.account_sid:
                        client = Client(self.account_sid, self.auth_token)
                        message = client.messages.create(
                            body=message_text, from_=self.from_number, to=recipient
                        )
                        results.append({"recipient": recipient, "sid": message.sid})
                        logger.info(
                            "WhatsApp sent to %s | SID: %s", recipient, message.sid
                        )
                        break
                    else:
                        # Mock mode for testing
                        logger.info(
                            "WhatsApp sent to %s | SID: MOCK_%s",
                            recipient,
                            payload.timestamp,
                        )
                        results.append(
                            {"recipient": recipient, "sid": f"MOCK_{payload.timestamp}"}
                        )
                        break

                except Exception as e:
                    logger.warning(
                        "Attempt %d failed for %s: %s", attempt + 1, recipient, str(e)
                    )
                    if attempt == 2:
                        logger.error(
                            "WhatsApp failed after 3 attempts for %s", recipient
                        )
                        results.append({"recipient": recipient, "error": str(e)})

        success = any("sid" in r for r in results)

        return {
            "success": success,
            "provider": self.name,
            "results": results,
        }

    def _format_message(self, payload: AlertPayload) -> str:
        """Format WhatsApp message."""
        emoji_map = {
            "EXTREME": "🔴🚨🔥",
            "CRITICAL": "🔴🚨",
            "HIGH": "🟠⚠️",
            "MODERATE": "🟡📢",
            "LOW": "🟢ℹ️",
        }
        emoji = emoji_map.get(payload.risk_tier, "⚠️")

        return (
            f"{emoji} *NFCC FLOOD ALERT* {emoji}\n\n"
            f"📍 *Location:* {payload.location}\n"
            f"📊 *Risk:* {payload.risk_tier} ({payload.score:.0f}/100)\n"
            f"🌧️ *Rainfall:* {payload.precipitation:.1f} mm\n"
            f"📈 *3-Day Total:* {payload.roll_3d:.1f} mm\n\n"
            f"📝 *Message:* {payload.message}\n\n"
            f"🕐 *Time:* {payload.timestamp}\n\n"
            f"_National Flood Control Centre, Ghana_"
        )
