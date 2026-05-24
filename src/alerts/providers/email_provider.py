"""Email alert provider using SMTP."""

import logging
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List

from src.alerts.providers.base import BaseAlertProvider
from src.alerts.models import AlertPayload

logger = logging.getLogger("nfcc.alert.email")


class EmailAlertProvider(BaseAlertProvider):
    """Email provider that sends alerts via SMTP."""

    name = "email"

    def __init__(
        self,
        smtp_host=None,
        smtp_port=587,
        username=None,
        password=None,
        to_emails=None,
        max_retries=3,
        **kwargs,
    ):
        """
        Initialize email provider.

        Args:
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            to_emails: List OR comma-separated email recipients
            max_retries: Retry attempts
        """

        # SMTP configuration
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")

        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))

        self.username = username or os.getenv("SMTP_USERNAME")

        self.password = password or os.getenv("SMTP_PASSWORD")

        # Normalize recipients
        emails = to_emails or os.getenv("ALERT_EMAILS", "")

        # Support both list and comma-separated string
        if isinstance(emails, list):
            self.to_emails = [e.strip() for e in emails if e.strip()]
        else:
            self.to_emails = [e.strip() for e in emails.split(",") if e.strip()]

        self.max_retries = max_retries

        # Backward compatibility
        self.recipients = self.to_emails
        self.smtp_user = self.username
        self.smtp_password = self.password

        if not self.to_emails:
            raise ValueError("Email recipients must be configured")

    def send(self, payload: AlertPayload) -> Dict[str, Any]:
        """
        Send email alert.

        Args:
            payload: AlertPayload object

        Returns:
            Success response or error
        """
        self.validate_payload(payload)

        html_body = self._build_html_email(payload)

        for attempt in range(self.max_retries):  # Retry up to 3 times
            try:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    if self.smtp_user and self.smtp_password:
                        server.login(self.smtp_user, self.smtp_password)

                    msg = MIMEMultipart()
                    msg["From"] = self.smtp_user
                    msg["To"] = ", ".join(self.to_emails)
                    msg["Subject"] = (
                        f"[NFCC] {payload.risk_tier} Flood Alert — {payload.location}"
                    )

                    msg.attach(MIMEText(html_body, "html"))

                    server.send_message(msg)

                    logger.info(
                        "Email sent to %s | [NFCC] %s Flood Alert — %s — Score: %.1f/100
                        self.to_emails,
                        payload.risk_tier,
                        payload.location,
                        payload.score,
                    )

                    return {
                        "success": True,
                        "provider": self.name,
                        "recipients": self.to_emails,
                        "sent": len(self.to_emails),
                    }

            except Exception as e:
                logger.warning("Attempt %d failed: %s", attempt + 1, str(e))
                if attempt == 2:
                    logger.error("Email failed after 3 attempts")

                    return {
                        "success": False,
                        "provider": self.name,
                        "error": str(e),
                        "sent": 0,
                    }

        return {
            "success": False,
            "provider": self.name,
            "error": "Max retries exceeded",
            "sent": 0,
        }

    def _build_html_email(self, payload: AlertPayload) -> str:
        """Build HTML email body."""
        color_map = {
            "EXTREME": "#dc3545",
            "CRITICAL": "#dc3545",
            "HIGH": "#fd7e14",
            "MODERATE": "#ffc107",
            "LOW": "#28a745",
        }
        color = color_map.get(payload.risk_tier, "#6c757d")

        return f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: {color}; color: white; padding: 10px; }}
                .content {{ padding: 20px; }}
                .score {{ font-size: 24px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>NFCC Flood Alert - {payload.risk_tier}</h2>
            </div>
            <div class="content">
                <p><strong>Location:</strong> {payload.location}</p>
                <p><strong>Risk Score:</strong> <span class="score">{payload.score:.1f}/
                <p><strong>Current Rainfall:</strong> {payload.precipitation:.1f} mm</p>
                <p><strong>3-Day Total:</strong> {payload.roll_3d:.1f} mm</p>
                <p><strong>Message:</strong> {payload.message}</p>
                <p><strong>Time:</strong> {payload.timestamp}</p>
                <hr>
                <p><em>National Flood Control Centre, Accra, Ghana</em></p>
            </div>
        </body>
        </html>
        """
