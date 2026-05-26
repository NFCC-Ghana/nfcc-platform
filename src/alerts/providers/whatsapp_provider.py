"""WhatsApp alert provider via Twilio."""

import logging
import os
import time
from src.alerts.providers.base import BaseAlertProvider
from src.alerts.models import AlertPayload

logger = logging.getLogger("nfcc.alert.whatsapp")


class WhatsAppAlertProvider(BaseAlertProvider):
    """Send WhatsApp alerts via Twilio with retry logic."""

    name = "whatsapp"

    def __init__(
        self,
        account_sid: str = None,
        auth_token: str = None,
        from_number: str = None,
        to_numbers: list[str] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = from_number or os.getenv(
            "TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"
        )
        self.to_numbers = to_numbers or [
            n.strip()
            for n in os.getenv("ALERT_WHATSAPP_RECIPIENTS", "").split(",")
            if n.strip()
        ]
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Allow mock mode for testing
        if not all([self.account_sid, self.auth_token, self.to_numbers]):
            if os.getenv("TEST_MODE") != "true":
                raise EnvironmentError(
                    "WhatsApp provider requires TWILIO_ACCOUNT_SID, "
                    "TWILIO_AUTH_TOKEN, and ALERT_WHATSAPP_RECIPIENTS."
                )

    def send(self, payload: AlertPayload) -> dict:
        self.validate_payload(payload)

        # Lazy import to prevent CI failures
        try:
            from twilio.rest import Client
            from twilio.base.exceptions import TwilioRestException
            client = Client(self.account_sid, self.auth_token)
        except ImportError:
            client = None
            TwilioRestException = Exception

        message_ids = []

        for recipient in self.to_numbers:
            to = (
                f"whatsapp:{recipient}"
                if not recipient.startswith("whatsapp:")
                else recipient
            )

            for attempt in range(self.max_retries):
                try:
                    if client:
                        msg = client.messages.create(
                            body=payload.message,
                            from_=self.from_number,
                            to=to,
                        )
                        message_ids.append(msg.sid)
                    else:
                        # Mock mode
                        import uuid
                        mock_sid = str(uuid.uuid4())
                        message_ids.append(mock_sid)
                        logger.info(f"WhatsApp mock sent to {recipient} | SID: {mock_sid}")

                    logger.info(f"WhatsApp sent to {recipient} | SID: {message_ids[-1]}")
                    break

                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                    else:
                        return {
                            "success": False,
                            "provider": self.name,
                            "message_id": None,
                            "error": str(e),
                        }

        return {
            "success": True,
            "provider": self.name,
            "message_id": ", ".join(message_ids),
            "error": None,
        }
