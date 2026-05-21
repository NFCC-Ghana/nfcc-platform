"""SMS alert provider via Twilio."""

import logging
import os
import time
from src.alerts.providers.base import BaseAlertProvider, AlertPayload

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

        if not all(
            [self.account_sid, self.auth_token, self.from_number, self.to_numbers]
        ):
            raise EnvironmentError(
                "SMS provider requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
                "TWILIO_SMS_FROM, and ALERT_SMS_RECIPIENTS."
            )

    def send(self, payload: AlertPayload) -> dict:
        from twilio.rest import Client
        from twilio.base.exceptions import TwilioRestException

        client = Client(self.account_sid, self.auth_token)
        message_ids = []

        # SMS has 160-char limit — use shortened message
        sms_body = (
            f"NFCC ALERT | {payload.risk_tier} | {payload.location} | "
            f"Risk: {payload.risk_score:.0f}/100 | Rain: {payload.precipitation:.1f}mm"
        )

        for recipient in self.to_numbers:
            for attempt in range(self.max_retries):
                try:
                    msg = client.messages.create(
                        body=sms_body,
                        from_=self.from_number,
                        to=recipient,
                    )
                    message_ids.append(msg.sid)
                    logger.info(f"SMS sent to {recipient} | SID: {msg.sid}")
                    break
                except TwilioRestException as e:
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
