"""Production email alert provider using SMTP."""

import logging
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from src.alerts.providers.base import BaseAlertProvider
from src.alerts.models import AlertPayload
from src.config.settings import settings

logger = logging.getLogger("nfcc.alert.email")


@dataclass
class EmailDeliveryResult:
    """Email delivery result."""

    to: str
    success: bool
    error: Optional[str] = None
    attempt_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EmailAlertProvider(BaseAlertProvider):
    """Production email provider with HTML formatting and retries."""

    name = "email"

    def __init__(
        self,
        recipients: List[str] = None,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_password: str = None,
        from_email: str = None,
        max_retries: int = None,
        retry_delay: float = None,
    ):
        self.recipients = recipients or settings.EMAIL_RECIPIENTS
        self.smtp_host = smtp_host or settings.SMTP_HOST
        self.smtp_port = smtp_port or settings.SMTP_PORT
        self.smtp_user = smtp_user or settings.SMTP_USER
        self.smtp_password = smtp_password or settings.SMTP_PASSWORD
        self.from_email = from_email or settings.SMTP_FROM or settings.SMTP_USER
        self.max_retries = max_retries or settings.EMAIL_MAX_RETRIES
        self.retry_delay = retry_delay or settings.EMAIL_RETRY_DELAY
        self.use_tls = settings.SMTP_USE_TLS

        # Check if we have real credentials
        self._mock_mode = not (
            self.smtp_user and self.smtp_password and self.smtp_user != "test@gmail.com"
        )

        if self._mock_mode:
            logger.warning("Email provider: MOCK MODE (no valid credentials)")
        else:
            logger.info(
                f"Email provider initialized for {len(self.recipients)} recipients"
            )

    def _format_html_message(self, alert: AlertPayload) -> str:
        """Format HTML email with professional styling."""
        risk_colors = {
            "LOW": "#4CAF50",
            "MODERATE": "#FFC107",
            "HIGH": "#FF9800",
            "CRITICAL": "#FF5722",
            "EXTREME": "#F44336",
        }
        color = risk_colors.get(alert.risk_tier, "#9E9E9E")

        return f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
        .header {{ background-color: {color}; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .metric {{ background-color: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .critical {{ border-left: 4px solid #F44336; }}
        .footer {{ font-size: 12px; color: #666; text-align: center; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚨 FLOOD ALERT</h1>
        <h2>{alert.location}</h2>
        <h3>{alert.risk_tier} Risk ({alert.score:.0f}/100)</h3>
    </div>

    <div class="content">
        <div class="metric">
            <h3>📊 Alert Details</h3>
            <p><strong>Message:</strong> {alert.message}</p>
            <p><strong>Time:</strong> {alert.timestamp}</p>
        </div>

        <div class="metric">
            <h3>🌧️ Rainfall Data</h3>
            <p><strong>Current:</strong> {alert.precipitation:.1f} mm</p>
            <p><strong>3-Day Rolling:</strong> {alert.roll_3d:.1f} mm</p>
            <p><strong>Z-Score:</strong> {alert.z_score:.2f}</p>
        </div>

        <div class="metric critical">
            <h3>⚠️ Recommended Actions</h3>
            <p>• Monitor local water levels</p>
            <p>• Avoid low-lying areas</p>
            <p>• Keep emergency contacts ready</p>
        </div>
    </div>

    <div class="footer">
        <p>NFCC Flood Alert System | Automated alert - do not reply</p>
        <p>For emergencies, contact local authorities immediately</p>
    </div>
</body>
</html>"""

    def _format_text_message(self, alert: AlertPayload) -> str:
        """Format plain text email."""
        return f"""
🚨 FLOOD ALERT: {alert.location}
Risk Level: {alert.risk_tier} ({alert.score:.0f}/100)

Message: {alert.message}
Time: {alert.timestamp}

Rainfall Data:
- Current: {alert.precipitation:.1f} mm
- 3-Day Rolling: {alert.roll_3d:.1f} mm
- Z-Score: {alert.z_score:.2f}

Recommended Actions:
- Monitor local water levels
- Avoid low-lying areas
- Keep emergency contacts ready

NFCC Flood Alert System
"""

    def _format_message(self, alert: AlertPayload) -> str:
        """Base format method - returns text version."""
        return self._format_text_message(alert)

    def _send_to_recipient(
        self, recipient: str, alert: AlertPayload
    ) -> EmailDeliveryResult:
        """Send email to a single recipient with retries."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚨 FLOOD ALERT: {alert.location} - {alert.risk_tier} Risk"
        msg["From"] = self.from_email
        msg["To"] = recipient

        text_part = MIMEText(self._format_text_message(alert), "plain")
        html_part = MIMEText(self._format_html_message(alert), "html")
        msg.attach(text_part)
        msg.attach(html_part)

        for attempt in range(1, self.max_retries + 1):
            try:
                if self._mock_mode:
                    logger.info(f"[MOCK Email] Would send to {recipient}")
                    return EmailDeliveryResult(
                        to=recipient, success=True, attempt_count=attempt
                    )

                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)

                logger.info(f"✅ Email sent to {recipient}")
                return EmailDeliveryResult(
                    to=recipient, success=True, attempt_count=attempt
                )

            except Exception as e:
                logger.warning(
                    f"⚠️ Email attempt {attempt} failed for {recipient}: {e}"
                )
                if attempt == self.max_retries:
                    logger.error(
                        f"❌ Email failed for {recipient} after {self.max_retries} attempts"
                    )
                    return EmailDeliveryResult(
                        to=recipient, success=False, error=str(e), attempt_count=attempt
                    )
                time.sleep(self.retry_delay * attempt)

        return EmailDeliveryResult(
            to=recipient, success=False, error="Max retries exceeded"
        )

    def send(self, alert: AlertPayload) -> Dict[str, Any]:
        """Send email alerts to all configured recipients."""
        if not self.recipients:
            return {
                "success": False,
                "message": "No email recipients configured",
                "provider": self.name,
                "recipient_count": 0,
            }

        results = [self._send_to_recipient(r, alert) for r in self.recipients]

        success_count = sum(1 for r in results if r.success)

        return {
            "success": success_count > 0,
            "message": f"Email: {success_count}/{len(results)} delivered",
            "provider": self.name,
            "recipient_count": len(results),
            "delivery": {
                "total": len(results),
                "successful": success_count,
                "failed": len(results) - success_count,
                "details": [r.to_dict() for r in results],
            },
        }
