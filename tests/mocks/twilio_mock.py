"""Mock Twilio client for SMS/WhatsApp testing."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import time


class TwilioErrorType(Enum):
    """Twilio error types for simulation."""

    NONE = "none"
    AUTH_FAILED = "auth_failed"
    INVALID_NUMBER = "invalid_number"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    SERVICE_UNAVAILABLE = "service_unavailable"
    MESSAGE_TOO_LONG = "message_too_long"


@dataclass
class MessageRecord:
    """Record of sent message."""

    to: str
    from_: str
    body: str
    timestamp: float = field(default_factory=time.time)
    sid: str = ""
    status: str = "sent"
    error: Optional[str] = None


class MockMessage:
    """Mock Twilio message."""

    def __init__(self, sid: str, status: str = "sent"):
        self.sid = sid
        self.status = status


class MockTwilioClient:
    """Mock Twilio client for testing SMS/WhatsApp providers."""

    def __init__(self, account_sid: str = "ACmock", auth_token: str = "token"):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.messages = MockMessages(self)
        self.sent_messages: List[MessageRecord] = []
        self.error_type = TwilioErrorType.NONE
        self.fail_count = 0
        self.max_failures = 0
        self.delay_ms = 0

    def set_error_mode(
        self, error_type: TwilioErrorType, fail_count: int = 1, delay_ms: int = 0
    ):
        """Configure error simulation."""
        self.error_type = error_type
        self.max_failures = fail_count
        self.fail_count = 0
        self.delay_ms = delay_ms
        self.messages.error_type = error_type
        self.messages.max_failures = fail_count
        self.messages.fail_count = 0

    def clear(self):
        """Clear all sent messages."""
        self.sent_messages.clear()
        self.messages.sent_messages.clear()
        self.fail_count = 0


class MockMessages:
    """Mock Twilio messages resource."""

    def __init__(self, client: MockTwilioClient):
        self.client = client
        self.sent_messages: List[MessageRecord] = []
        self.error_type = TwilioErrorType.NONE
        self.fail_count = 0
        self.max_failures = 0

    def create(self, to: str, from_: str, body: str) -> MockMessage:
        """Create a mock message."""
        if self.delay_ms > 0:
            time.sleep(self.delay_ms / 1000)

        # Simulate errors
        if self.error_type != TwilioErrorType.NONE:
            self.fail_count += 1
            if self.fail_count <= self.max_failures:
                errors = {
                    TwilioErrorType.AUTH_FAILED: Exception("Authentication failed"),
                    TwilioErrorType.INVALID_NUMBER: Exception("Invalid phone number"),
                    TwilioErrorType.RATE_LIMIT: Exception("Rate limit exceeded"),
                    TwilioErrorType.TIMEOUT: Exception("Request timeout"),
                    TwilioErrorType.SERVICE_UNAVAILABLE: Exception(
                        "Service unavailable"
                    ),
                    TwilioErrorType.MESSAGE_TOO_LONG: Exception(
                        "Message exceeds 1600 characters"
                    ),
                }
                raise errors.get(self.error_type, Exception("Twilio error"))

        # Record the message
        sid = f"SM{len(self.sent_messages) + 1:06d}"
        record = MessageRecord(to=to, from_=from_, body=body, sid=sid)
        self.sent_messages.append(record)
        self.client.sent_messages.append(record)

        return MockMessage(sid)

    def set_error_mode(
        self, error_type: TwilioErrorType, fail_count: int = 1, delay_ms: int = 0
    ):
        """Configure error simulation."""
        self.error_type = error_type
        self.max_failures = fail_count
        self.fail_count = 0
        self.delay_ms = delay_ms

    def get_sent_messages(self) -> List[MessageRecord]:
        """Get all sent messages."""
        return self.sent_messages

    def get_last_message(self) -> Optional[MessageRecord]:
        """Get the last sent message."""
        return self.sent_messages[-1] if self.sent_messages else None

    def clear(self):
        """Clear all sent messages."""
        self.sent_messages.clear()
        self.fail_count = 0
