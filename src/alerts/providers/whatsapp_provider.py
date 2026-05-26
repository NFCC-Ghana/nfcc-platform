"""Production WhatsApp alert provider with lazy initialization."""

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from src.alerts.providers.base import BaseAlertProvider
from src.alerts.models import AlertPayload
from src.config.settings import settings

logger = logging.getLogger("nfcc.alert.whatsapp")

# Non-retryable Twilio error codes
NON_RETRYABLE_ERROR_CODES = {
    "63038",
    "20003",
    "21211",
    "21408",
    "21610",
    "21612",
    "21614",
}


@dataclass
class WhatsAppDeliveryResult:
    to: str
    success: bool
    sid: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    attempt_count: int = 0
    is_retryable: bool = True


class WhatsAppAlertProvider(BaseAlertProvider):
    """Production WhatsApp provider with lazy initialization."""

    name = "whatsapp"

    def __init__(
        self,
        account_sid: str = None,
        auth_token: str = None,
        from_number: str = None,
        to_numbers: List[str] = None,
        max_retries: int = None,
        retry_delay: float = None,
    ):
        self.account_sid = account_sid or settings.TWILIO_ACCOUNT_SID
        self.auth_token = auth_token or settings.TWILIO_AUTH_TOKEN
        self.from_number = from_number or settings.TWILIO_WHATSAPP_FROM
        self.to_numbers = to_numbers or settings.WHATSAPP_RECIPIENTS
        self.max_retries = max_retries or getattr(settings, "WHATSAPP_MAX_RETRIES", 3)
        self.retry_delay = retry_delay or getattr(settings, "WHATSAPP_RETRY_DELAY", 2.0)

        if self.from_number and not self.from_number.startswith("whatsapp:"):
            self.from_number = f"whatsapp:{self.from_number}"

        self.to_numbers = [
            n if n.startswith("whatsapp:") else f"whatsapp:{n}" for n in self.to_numbers
        ]

        # Lazy initialization - no network calls at startup
        self._client = None
        self._initialized = False
        self._mock_mode = not self._has_valid_credentials()

        if self._mock_mode:
            logger.warning("WhatsApp provider: MOCK MODE (no valid credentials)")
        else:
            logger.info(
                f"WhatsApp provider configured for {len(self.to_numbers)} recipients (lazy init)"
            )

    def _has_valid_credentials(self) -> bool:
        if not self.account_sid or not self.auth_token:
            return False
        if self.account_sid == "mock_sid":
            return False
        return self.account_sid.startswith("AC") and len(self.account_sid) > 20

    def _ensure_client(self):
        """Lazy initialize Twilio client - only on first send."""
        if self._client is not None or self._mock_mode:
            return

        try:
            from twilio.rest import Client

            self._client = Client(self.account_sid, self.auth_token)
            self._initialized = True
            logger.info("✅ Twilio WhatsApp client initialized (lazy)")
        except ImportError:
            logger.error("twilio package not installed")
            self._mock_mode = True
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            self._mock_mode = True

    def _is_dry_run(self) -> bool:
        """Check if dry run mode is enabled."""
        return getattr(settings, "ALERT_DRY_RUN", False)

    def _extract_error_code(self, error: Exception) -> Optional[str]:
        """Extract Twilio error code from exception."""
        try:
            if hasattr(error, "code"):
                return str(error.code)
            error_str = str(error)
            if "Error " in error_str:
                import re

                match = re.search(r"Error (\d+)", error_str)
                if match:
                    return match.group(1)
        except:
            pass
        return None

    def _format_message(self, alert: AlertPayload) -> str:
        risk_emoji = {
            "LOW": "🟢",
            "MODERATE": "🟡",
            "HIGH": "🟠",
            "CRITICAL": "🔴",
            "EXTREME": "💀",
        }.get(alert.risk_tier, "⚠️")

        return (
            f"{risk_emoji} *FLOOD ALERT: {alert.location}*\n\n"
            f"*Risk:* {alert.risk_tier} ({alert.score:.0f}/100)\n"
            f"*Rainfall:* {alert.precipitation:.1f}mm\n"
            f"*Message:* {alert.message}\n\n"
            f"🕐 {alert.timestamp[:19]}"
        )

    def send(self, alert: AlertPayload) -> Dict[str, Any]:
        """Send WhatsApp alert with lazy initialization and dry run support."""
        # Dry run mode - no actual sending
        if self._is_dry_run():
            logger.info(f"🔵 DRY RUN: Would send WhatsApp to {self.to_numbers}")
            return {
                "success": True,
                "message": f"DRY RUN: Would send to {len(self.to_numbers)} recipient(s)",
                "provider": self.name,
                "recipient_count": len(self.to_numbers),
                "dry_run": True,
            }

        if not self.to_numbers:
            return {
                "success": False,
                "message": "No WhatsApp recipients",
                "provider": self.name,
                "recipient_count": 0,
            }

        # Lazy initialization - only now do we create the client
        self._ensure_client()

        results = []
        for to_number in self.to_numbers:
            for attempt in range(1, self.max_retries + 1):
                try:
                    if self._mock_mode:
                        logger.info(f"[MOCK WhatsApp] Would send to {to_number}")
                        results.append({"to": to_number, "success": True, "mock": True})
                        break

                    message = self._client.messages.create(
                        body=self._format_message(alert),
                        from_=self.from_number,
                        to=to_number,
                    )

                    logger.info(f"✅ WhatsApp sent to {to_number} | SID: {message.sid}")
                    results.append(
                        {"to": to_number, "success": True, "sid": message.sid}
                    )
                    break

                except Exception as e:
                    error_code = self._extract_error_code(e)
                    is_retryable = (
                        error_code not in NON_RETRYABLE_ERROR_CODES
                        if error_code
                        else True
                    )

                    logger.warning(f"⚠️ Attempt {attempt} failed for {to_number}: {e}")
                    if error_code:
                        logger.warning(
                            f"   Error code: {error_code}, Retryable: {is_retryable}"
                        )

                    if not is_retryable:
                        logger.error(
                            f"❌ Non-retryable error, stopping for {to_number}"
                        )
                        results.append(
                            {
                                "to": to_number,
                                "success": False,
                                "error": str(e),
                                "error_code": error_code,
                            }
                        )
                        break

                    if attempt == self.max_retries:
                        logger.error(
                            f"❌ WhatsApp failed for {to_number} after {self.max_retries} attempts"
                        )
                        results.append(
                            {"to": to_number, "success": False, "error": str(e)}
                        )
                    else:
                        time.sleep(self.retry_delay * attempt)

        success_count = sum(1 for r in results if r.get("success"))

        return {
            "success": success_count > 0,
            "message": f"WhatsApp: {success_count}/{len(results)} delivered",
            "provider": self.name,
            "recipient_count": len(results),
            "delivery": {
                "total": len(results),
                "successful": success_count,
                "failed": len(results) - success_count,
                "details": results,
            },
        }
