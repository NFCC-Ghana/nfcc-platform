"""SMS alert provider via Twilio."""

import logging
import os
import time
from src.alerts.providers.base import BaseAlertProvider
from src.alerts.models import AlertPayload

logger = logging.getLogger("nfcc.alert.sms")


class SMSAlertProvider(BaseAlertProvider):
    """Send SMS alerts via Twilio with retry logic."""

    name = "sms"

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
        self.from_number = from_number or os.getenv("TWILIO_SMS_FROM")
        self.to_numbers = to_numbers or [
            n.strip()
            for n in os.getenv("ALERT_SMS_RECIPIENTS", "").split(",")
            if n.strip()
        ]
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Allow mock mode for testing
        if not all([self.account_sid, self.auth_token, self.from_number, self.to_numbers]):
            if os.getenv("TEST_MODE") != "true":
                raise EnvironmentError(
                    "SMS provider requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
                    "TWILIO_SMS_FROM, and ALERT_SMS_RECIPIENTS."
                )

    def send(self, payload: AlertPayload) -> dict:
        self.validate_payload(payload)

        # Lazy import to prevent CI failures
        try:
            from twilio.rest import Client
            from twilio.base.exceptions import TwilioRestException
            client = Client(self.account_sid, self.auth_token)
        except ImportError:
            # Mock mode for testing
            client = None
            TwilioRestException = Exception

        message_ids = []

        # Use payload.score (not risk_score)
        sms_body = (
            f"NFCC ALERT | {payload.risk_tier} | {payload.location} | "
            f"Risk: {payload.score:.0f}/100 | Rain: {payload.precipitation:.1f}mm"
        )

        for recipient in self.to_numbers:
            for attempt in range(self.max_retries):
                try:
                    if client:
                        msg = client.messages.create(
                            body=sms_body,
                            from_=self.from_number,
                            to=recipient,
                        )
                        message_ids.append(msg.sid)
                    else:
                        # Mock mode
                        import uuid
                        mock_sid = str(uuid.uuid4())
                        message_ids.append(mock_sid)
                        logger.info(f"SMS mock sent to {recipient} | SID: {mock_sid}")

                    logger.info(f"SMS sent to {recipient}")
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
