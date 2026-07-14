"""Email alert provider using SMTP."""

import logging
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from src.alerts.models import AlertPayload
from src.alerts.providers.base import BaseAlertProvider

logger = logging.getLogger("nfcc.alert.email")


class EmailAlertProvider(BaseAlertProvider):
    """Email provider that sends alerts via SMTP."""

    name = "email"

    def __init__(
        self,
        recipients: List[str] = None,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_password: str = None,
        from_email: str = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        # CRITICAL: Only use environment if recipients is None (not empty list)
        if recipients is None:
            env_recipients = os.getenv("ALERT_EMAIL_RECIPIENTS", "")
            self.recipients = [
                r.strip() for r in env_recipients.split(",") if r.strip()
            ]
        else:
            self.recipients = recipients

        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_email = from_email or os.getenv("SMTP_USER", "alerts@nfcc.com")
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self._mock_mode = not (
            self.smtp_user and self.smtp_password and self.smtp_user != "test@gmail.com"
        )

        if self._mock_mode:
            logger.warning("Email provider: MOCK MODE (no valid credentials)")
        elif self.recipients:
            logger.info(
                f"Email provider initialized for {len(self.recipients)} recipients"
            )

    def _format_html_message(self, alert: AlertPayload) -> str:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .alert {{ padding: 20px; border-radius: 5px; }}
                .extreme {{ background-color: #ff4444; color: white; }}
            </style>
        </head>
        <body>
            <div class="alert {alert.risk_tier.lower()}">
                <h1>🚨 FLOOD ALERT: {alert.location}</h1>
                <h2>Risk: {alert.risk_tier} ({alert.score:.1f}/100)</h2>
            </div>
            <p><strong>Rainfall:</strong> {alert.precipitation:.1f} mm</p>
            <p><strong>Message:</strong> {alert.message}</p>
            <p><strong>Time:</strong> {alert.timestamp}</p>
            <hr>
            <small>NFCC Flood Alert System</small>
        </body>
        </html>
        """

    def _format_text_message(self, alert: AlertPayload) -> str:
        return f"""
🚨 FLOOD ALERT: {alert.location}
Risk: {alert.risk_tier} ({alert.score:.1f}/100)

Rainfall: {alert.precipitation:.1f} mm
Message: {alert.message}
Time: {alert.timestamp}

NFCC Flood Alert System
"""

    def _format_message(self, alert: AlertPayload) -> str:
        return self._format_text_message(alert)

    def send(self, alert: AlertPayload) -> Dict[str, Any]:
        """Send email alert with retry logic."""
        # Check empty recipients FIRST
        if not self.recipients:
            return {
                "success": False,
                "message": "No email recipients configured",
                "provider": self.name,
                "recipient_count": 0,
            }

        if self._mock_mode:
            logger.info(f"[MOCK Email] Would send to {self.recipients}")
            return {
                "success": True,
                "message": f"MOCK: Email sent to {len(self.recipients)} recipient(s)",
                "provider": self.name,
                "recipient_count": len(self.recipients),
                "mock": True,
            }

        # Real email sending
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚨 FLOOD ALERT: {alert.location} - {alert.risk_tier} Risk"
        msg["From"] = self.from_email
        msg["To"] = ", ".join(self.recipients)

        text_part = MIMEText(self._format_text_message(alert), "plain")
        html_part = MIMEText(self._format_html_message(alert), "html")
        msg.attach(text_part)
        msg.attach(html_part)

        for attempt in range(1, self.max_retries + 1):
            try:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)

                logger.info(f"Email sent to {self.recipients}")
                return {
                    "success": True,
                    "message": f"Email sent to {len(self.recipients)} recipient(s)",
                    "provider": self.name,
                    "recipient_count": len(self.recipients),
                }

            except Exception as e:
                logger.warning(f"Attempt {attempt} failed: {e}")
                if attempt == self.max_retries:
                    return {
                        "success": False,
                        "message": f"Email failed: {str(e)}",
                        "provider": self.name,
                        "recipient_count": 0,
                    }
                time.sleep(self.retry_delay * attempt)

        return {
            "success": False,
            "message": "Email sending failed",
            "provider": self.name,
            "recipient_count": 0,
        }
