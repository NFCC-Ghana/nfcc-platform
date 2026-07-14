"""Mock SMTP client for email testing."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SMTPErrorType(Enum):
    """SMTP error types for simulation."""

    NONE = "none"
    CONNECTION_REFUSED = "connection_refused"
    AUTH_FAILED = "auth_failed"
    TIMEOUT = "timeout"
    SEND_FAILED = "send_failed"
    RATE_LIMIT = "rate_limit"


@dataclass
class EmailRecord:
    """Record of sent email."""

    from_addr: str
    to_addrs: List[str]
    subject: str
    body: str
    timestamp: float = field(default_factory=time.time)
    success: bool = True
    error: Optional[str] = None


class MockSMTPClient:
    """Mock SMTP client for testing email providers."""

    def __init__(self, host: str = "localhost", port: int = 25):
        self.host = host
        self.port = port
        self.connected = False
        self.logged_in = False
        self.sent_emails: List[EmailRecord] = []
        self.error_type = SMTPErrorType.NONE
        self.fail_count = 0
        self.max_failures = 0
        self.delay_ms = 0

    def set_error_mode(
        self, error_type: SMTPErrorType, fail_count: int = 1, delay_ms: int = 0
    ):
        """Configure error simulation."""
        self.error_type = error_type
        self.max_failures = fail_count
        self.fail_count = 0
        self.delay_ms = delay_ms

    def connect(self, host: str, port: int):
        """Simulate connection."""
        if self.error_type == SMTPErrorType.CONNECTION_REFUSED:
            raise Exception(f"Connection refused to {host}:{port}")

        if self.delay_ms > 0:
            time.sleep(self.delay_ms / 1000)

        self.connected = True
        return self

    def starttls(self):
        """Simulate TLS upgrade."""
        if self.error_type == SMTPErrorType.TIMEOUT:
            time.sleep(5)
            raise Exception("Connection timeout")
        return self

    def login(self, user: str, password: str):
        """Simulate login."""
        if self.error_type == SMTPErrorType.AUTH_FAILED:
            self.fail_count += 1
            if self.fail_count <= self.max_failures:
                raise Exception("Authentication failed")

        self.logged_in = True
        return self

    def send_message(self, msg):
        """Simulate sending email."""
        if self.error_type == SMTPErrorType.SEND_FAILED:
            self.fail_count += 1
            if self.fail_count <= self.max_failures:
                raise Exception("Failed to send email")

        if self.error_type == SMTPErrorType.RATE_LIMIT:
            raise Exception("Rate limit exceeded")

        # Extract email details
        subject = msg.get("Subject", "No Subject")
        from_addr = msg.get("From", "test@example.com")
        to_addrs = msg.get("To", "").split(", ")

        record = EmailRecord(
            from_addr=from_addr, to_addrs=to_addrs, subject=subject, body=str(msg)
        )
        self.sent_emails.append(record)
        return {"message_id": f"mock-{len(self.sent_emails)}"}

    def quit(self):
        """Simulate quit."""
        self.connected = False
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()

    def get_sent_emails(self) -> List[EmailRecord]:
        """Get all sent emails."""
        return self.sent_emails

    def get_last_email(self) -> Optional[EmailRecord]:
        """Get the last sent email."""
        return self.sent_emails[-1] if self.sent_emails else None

    def clear(self):
        """Clear all sent emails."""
        self.sent_emails.clear()
        self.fail_count = 0
