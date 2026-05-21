"""Email alert provider via SMTP."""

import logging
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.alerts.providers.base import BaseAlertProvider, AlertPayload

logger = logging.getLogger("nfcc.alert.email")


class EmailAlertProvider(BaseAlertProvider):
    """Send email alerts via SMTP with retry logic."""

    name = "email"

    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_pass: str = None,
        from_email: str = None,
        to_emails: list[str] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_pass = smtp_pass or os.getenv("SMTP_PASS")
        self.from_email = from_email or os.getenv("ALERT_EMAIL_FROM")
        self.to_emails = to_emails or [
            e.strip()
            for e in os.getenv("ALERT_EMAIL_RECIPIENTS", "").split(",")
            if e.strip()
        ]
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        if not all([self.smtp_user, self.smtp_pass, self.from_email, self.to_emails]):
            raise EnvironmentError(
                "Email provider requires SMTP_USER, SMTP_PASS, "
                "ALERT_EMAIL_FROM, and ALERT_EMAIL_RECIPIENTS."
            )

    def _build_html(self, payload: AlertPayload) -> str:
        tier_color = {
            "CRITICAL": "#c0392b",
            "HIGH": "#e67e22",
            "MODERATE": "#f1c40f",
            "LOW": "#27ae60",
        }.get(payload.risk_tier, "#2980b9")

        return f"""
        <html><body style="font-family:Arial,sans-serif;
                           background:#f4f4f4; padding:20px;">
          <div style="max-width:600px; margin:auto;
                      background:white; border-radius:10px;
                      overflow:hidden; box-shadow:0 2px 8px #ccc;">
            <div style="background:{tier_color};
                        padding:20px; text-align:center;">
              <h1 style="color:white; margin:0;">
                🌧️ NFCC FLOOD ALERT
              </h1>
              <h2 style="color:white; margin:5px 0;">
                {payload.risk_tier}
              </h2>
            </div>
            <div style="padding:24px;">
              <table width="100%" cellpadding="8"
                     style="border-collapse:collapse;">
                <tr style="background:#f9f9f9;">
                  <td><b>Location</b></td>
                  <td>{payload.location}</td>
                </table>
                <tr>
                  <td><b>Risk Score</b></td>
                  <td style="color:{tier_color};font-weight:bold;">
                    {payload.risk_score:.1f} / 100
                  </td>
                </tr>
                <tr style="background:#f9f9f9;">
                  <td><b>Today's Rainfall</b></td>
                  <td>{payload.precipitation:.1f} mm</td>
                </tr>
                <tr>
                  <td><b>3-Day Total</b></td>
                  <td>{payload.roll_3d:.1f} mm</td>
                </tr>
                <tr style="background:#f9f9f9;">
                  <td><b>Z-Score</b></td>
                  <td>{payload.z_score:.2f}</td>
                </tr>
                <tr>
                  <td><b>Timestamp</b></td>
                  <td>{payload.timestamp[:19].replace('T', ' ')} UTC</td>
                </tr>
              </table>
            </div>
            <div style="background:#0f1923; padding:14px;
                        text-align:center; color:#aaa; font-size:12px;">
              National Flood Control Centre · Accra, Ghana ·
              NFCC Intelligence Platform
            </div>
          </div>
        </body></html>
        """

    def send(self, payload: AlertPayload) -> dict:
        subject = (
            f"[NFCC] {payload.risk_tier} Flood Alert — "
            f"{payload.location} — Score: {payload.risk_score:.0f}/100"
        )

        for attempt in range(self.max_retries):
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = self.from_email
                msg["To"] = ", ".join(self.to_emails)
                msg.attach(MIMEText(payload.message, "plain"))
                msg.attach(MIMEText(self._build_html(payload), "html"))

                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.from_email, self.to_emails, msg.as_string())

                logger.info(f"Email sent to {self.to_emails} | {subject}")
                return {
                    "success": True,
                    "provider": self.name,
                    "message_id": subject,
                    "error": None,
                }

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Email failed after {self.max_retries} attempts")
                    return {
                        "success": False,
                        "provider": self.name,
                        "message_id": None,
                        "error": str(e),
                    }
