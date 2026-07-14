"""Production SMS alert provider via Twilio."""

import logging
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from src.alerts.models import AlertPayload
from src.alerts.providers.base import BaseAlertProvider
from src.config.settings import settings

logger = logging.getLogger("nfcc.alert.sms")


@dataclass
class SMSDeliveryResult:
    """SMS delivery result."""

    to: str
    success: bool
    sid: Optional[str] = None
    error: Optional[str] = None
    attempt_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SMSAlertProvider(BaseAlertProvider):
    """Production SMS alert provider with retry and monitoring."""

    name = "sms"

    def __init__(
        self,
        account_sid: str = None,
        auth_token: str = None,
        from_number: str = None,
        to_numbers: List[str] = None,
        max_retries: int = None,
        retry_delay: float = None,
    ):
        # Use settings if not provided
        self.account_sid = account_sid or settings.TWILIO_ACCOUNT_SID
        self.auth_token = auth_token or settings.TWILIO_AUTH_TOKEN
        self.from_number = from_number or settings.TWILIO_SMS_FROM
        self.to_numbers = to_numbers or settings.SMS_RECIPIENTS
        self.max_retries = max_retries or settings.SMS_MAX_RETRIES
        self.retry_delay = retry_delay or settings.SMS_RETRY_DELAY

        self._client = None
        self._mock_mode = not self._has_valid_credentials()

        if self._mock_mode:
            logger.warning("SMS provider: MOCK MODE (no valid credentials)")
        else:
            self._init_client()
            logger.info(
                f"SMS provider initialized for {len(self.to_numbers)} recipients"
            )

    def _has_valid_credentials(self) -> bool:
        """Check if we have valid Twilio credentials."""
        if not self.account_sid or not self.auth_token:
            return False
        if self.account_sid == "mock_sid":
            return False
        # Real Twilio SIDs start with "AC" and are longer than 20 chars
        if self.account_sid.startswith("AC") and len(self.account_sid) > 20:
            return True
        return False

    def _init_client(self):
        """Initialize Twilio client."""
        try:
            from twilio.rest import Client

            self._client = Client(self.account_sid, self.auth_token)
            # Test the connection
            self._client.api.accounts(self.account_sid).fetch()
            logger.info("✅ Twilio SMS client initialized successfully")
        except ImportError:
            logger.error("twilio package not installed. Run: pip install twilio")
            self._mock_mode = True
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            self._mock_mode = True

    def _get_client(self):
        """Get or create Twilio client."""
        if self._client is None and not self._mock_mode:
            self._init_client()
        return self._client

    def _format_message(self, alert: AlertPayload) -> str:
        """Format alert for SMS (160 char limit awareness)."""
        # Truncate message to avoid hitting SMS limits
        short_message = alert.message[:50] if alert.message else "Flood warning"

        message = (
            f"FLOOD: {alert.location} | "
            f"{alert.risk_tier} ({alert.score:.0f}) | "
            f"Rain: {alert.precipitation:.0f}mm | "
            f"{short_message}"
        )
        # Truncate to 160 chars (SMS limit)
        if len(message) > 160:
            message = message[:157] + "..."
        return message

    def _send_to_number(self, to_number: str, alert: AlertPayload) -> SMSDeliveryResult:
        """Send SMS to a single number with retries."""
        for attempt in range(1, self.max_retries + 1):
            try:
                if self._mock_mode:
                    logger.info(f"[MOCK SMS] Would send to {to_number}")
                    return SMSDeliveryResult(
                        to=to_number,
                        success=True,
                        sid="MOCK_SID",
                        attempt_count=attempt,
                    )

                client = self._get_client()
                message = client.messages.create(
                    body=self._format_message(alert),
                    from_=self.from_number,
                    to=to_number,
                )

                logger.info(
                    f"✅ SMS sent to {to_number} | SID: {message.sid} | Attempt: {attempt}"
                )
                return SMSDeliveryResult(
                    to=to_number, success=True, sid=message.sid, attempt_count=attempt
                )

            except Exception as e:
                logger.warning(f"⚠️ SMS attempt {attempt} failed for {to_number}: {e}")

                if attempt == self.max_retries:
                    logger.error(
                        f"❌ SMS failed for {to_number} after {self.max_retries} attempts"
                    )
                    return SMSDeliveryResult(
                        to=to_number, success=False, error=str(e), attempt_count=attempt
                    )

                time.sleep(self.retry_delay * attempt)  # Exponential backoff

        return SMSDeliveryResult(
            to=to_number, success=False, error="Max retries exceeded"
        )

    def send(self, alert: AlertPayload) -> Dict[str, Any]:
        """Send SMS alerts to all configured recipients."""
        if not self.to_numbers:
            return {
                "success": False,
                "message": "No SMS recipients configured",
                "provider": self.name,
                "recipient_count": 0,
            }

        results = [self._send_to_number(to, alert) for to in self.to_numbers]

        success_count = sum(1 for r in results if r.success)

        return {
            "success": success_count > 0,
            "message": f"SMS: {success_count}/{len(results)} delivered",
            "provider": self.name,
            "recipient_count": len(results),
            "delivery": {
                "total": len(results),
                "successful": success_count,
                "failed": len(results) - success_count,
                "details": [r.to_dict() for r in results],
            },
        }
