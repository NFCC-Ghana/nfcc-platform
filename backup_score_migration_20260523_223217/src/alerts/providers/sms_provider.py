"""SMS alert provider using Twilio."""

import logging
import os
from typing import Dict, Any, List

from src.alerts.providers.base import BaseAlertProvider
from src.alerts.models import AlertPayload

logger = logging.getLogger("nfcc.alert.sms")

# Try to import Twilio, but don't fail if not installed
try:
    from twilio.rest import Client

    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio not installed. SMS provider will be limited to mock mode.")


class SMSAlertProvider(BaseAlertProvider):
    """SMS provider that sends alerts via Twilio."""

    name = "sms"

    def __init__(self, recipients: List[str] = None, **kwargs):
        """
        Initialize SMS provider.

        Args:
            recipients: List of phone numbers
            account_sid: Twilio account SID (default from env)
            auth_token: Twilio auth token (default from env)
            from_number: Twilio from number (default from env)
        """
        self.recipients = recipients or os.getenv("ALERT_SMS_RECIPIENTS", "").split(",")
        self.account_sid = kwargs.get("account_sid", os.getenv("TWILIO_ACCOUNT_SID"))
        self.auth_token = kwargs.get("auth_token", os.getenv("TWILIO_AUTH_TOKEN"))
        self.from_number = kwargs.get("from_number", os.getenv("TWILIO_FROM_NUMBER"))

        if not self.recipients or not self.recipients[0]:
            raise ValueError("SMS recipients must be configured")

    def send(self, payload: AlertPayload) -> Dict[str, Any]:
        """
        Send SMS alert.

        Args:
            payload: AlertPayload object

        Returns:
            Success response or error
        """
        self.validate_payload(payload)

        message_text = self._format_message(payload)
        results = []

        for recipient in self.recipients:
            for attempt in range(3):
                try:
                    if TWILIO_AVAILABLE and self.account_sid:
                        client = Client(self.account_sid, self.auth_token)
                        message = client.messages.create(
                            body=message_text,
                            from_=self.from_number,
                            to=recipient.strip(),
                        )
                        results.append({"recipient": recipient, "sid": message.sid})
                        logger.info("SMS sent to %s | SID: %s", recipient, message.sid)
                        break
                    else:
                        # Mock mode for testing
                        logger.info(
                            "SMS sent to %s | SID: MOCK_%s",
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
                        logger.error("SMS failed after 3 attempts for %s", recipient)
                        results.append({"recipient": recipient, "error": str(e)})

        success = any("sid" in r for r in results)

        return {
            "success": success,
            "provider": self.name,
            "results": results,
        }

    def _format_message(self, payload: AlertPayload) -> str:
        """Format SMS message (160 char limit)."""
        emoji_map = {
            "EXTREME": "🔴🚨",
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MODERATE": "🟡",
            "LOW": "🟢",
        }
        emoji = emoji_map.get(payload.risk_tier, "⚠️")

        return (
            f"{emoji} NFCC FLOOD ALERT\n"
            f"Location: {payload.location}\n"
            f"Risk: {payload.risk_tier} ({payload.score:.0f}/100)\n"
            f"Rain: {payload.precipitation:.1f}mm\n"
            f"{payload.message[:50]}..."
        )
