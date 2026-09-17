"""Complete unit tests for all providers with proper mocking."""

import pytest
from unittest.mock import patch, MagicMock
from src.alerts.models import AlertPayload
from src.alerts.providers.sms_provider import SMSAlertProvider
from src.alerts.providers.whatsapp_provider import WhatsAppAlertProvider
from src.alerts.providers.email_provider import EmailAlertProvider

# See tests/unit/test_providers_mock.py's comment on this same constant -
# SMSAlertProvider/WhatsAppAlertProvider only ever touch the (here, patched)
# twilio.rest.Client if account_sid looks like a real Twilio SID
# ("AC" + >20 chars); "test_sid" fails that check and silently falls back to
# the provider's own MOCK MODE branch instead, which is why patching
# twilio.rest.Client had no effect on these tests.
_FAKE_TWILIO_SID = "AC" + "0" * 32

# ============================================================
# SMS Provider Tests
# ============================================================


class TestSMSProviderComplete:
    """Complete SMS provider tests."""

    def test_send_success(self):
        """Test successful SMS sending."""
        with patch("twilio.rest.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            mock_message = MagicMock()
            mock_message.sid = "SM_test123"
            mock_client.messages.create.return_value = mock_message

            provider = SMSAlertProvider(
                account_sid=_FAKE_TWILIO_SID,
                auth_token="test_token",
                from_number="+1234567890",
                to_numbers=["+1234567890"],
                max_retries=3,
                retry_delay=1,
            )

            alert = AlertPayload(
                location="Accra",
                score=85.0,
                risk_tier="EXTREME",
                message="Test alert",
                precipitation=25.5,
                roll_3d=50.0,
                z_score=1.5,
                timestamp="2024-01-01T00:00:00Z",
            )

            result = provider.send(alert)

            assert result["success"] is True
            mock_client.messages.create.assert_called_once()

    def test_send_multiple_recipients(self):
        """Test sending SMS to multiple recipients."""
        with patch("twilio.rest.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            mock_message = MagicMock()
            mock_message.sid = "SM_test123"
            mock_client.messages.create.return_value = mock_message

            provider = SMSAlertProvider(
                account_sid=_FAKE_TWILIO_SID,
                auth_token="test_token",
                from_number="+1234567890",
                to_numbers=["+1234567890", "+1987654321"],
                max_retries=3,
                retry_delay=1,
            )

            alert = AlertPayload(
                location="Accra",
                score=85.0,
                risk_tier="EXTREME",
                message="Test alert",
                timestamp="2024-01-01T00:00:00Z",
            )

            result = provider.send(alert)

            assert result["success"] is True
            # Should send to both recipients (2 calls)
            assert mock_client.messages.create.call_count == 2

    def test_send_retry_on_failure(self):
        """Test retry logic on failure."""
        with patch("twilio.rest.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            # Make first attempt fail, second succeed
            mock_client.messages.create.side_effect = [
                Exception("Network error"),
                MagicMock(sid="SM_success"),
            ]

            provider = SMSAlertProvider(
                account_sid=_FAKE_TWILIO_SID,
                auth_token="test_token",
                from_number="+1234567890",
                to_numbers=["+1234567890"],
                max_retries=3,
                retry_delay=1,
            )

            alert = AlertPayload(
                location="Accra",
                score=85.0,
                risk_tier="EXTREME",
                message="Test alert",
                timestamp="2024-01-01T00:00:00Z",
            )

            result = provider.send(alert)

            assert result["success"] is True
            assert mock_client.messages.create.call_count == 2

    def test_send_all_retries_fail(self):
        """Test when all retries fail."""
        with patch("twilio.rest.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            # Make all attempts fail
            mock_client.messages.create.side_effect = Exception("Network error")

            provider = SMSAlertProvider(
                account_sid=_FAKE_TWILIO_SID,
                auth_token="test_token",
                from_number="+1234567890",
                to_numbers=["+1234567890"],
                max_retries=2,
                retry_delay=1,
            )

            alert = AlertPayload(
                location="Accra",
                score=85.0,
                risk_tier="EXTREME",
                message="Test alert",
                timestamp="2024-01-01T00:00:00Z",
            )

            result = provider.send(alert)

            assert result["success"] is False
            # SMSAlertProvider._send_to_number treats max_retries as the
            # TOTAL attempt count (range(1, max_retries + 1), and its own
            # log message says "after {max_retries} attempts") - not
            # "retries after the first" - so max_retries=2 means 2 calls,
            # not 3.
            assert mock_client.messages.create.call_count == 2


# ============================================================
# WhatsApp Provider Tests
# ============================================================


class TestWhatsAppProviderComplete:
    """Complete WhatsApp provider tests."""

    def test_send_success(self):
        """Test successful WhatsApp sending."""
        with patch("twilio.rest.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            mock_message = MagicMock()
            mock_message.sid = "SM_test123"
            mock_client.messages.create.return_value = mock_message

            provider = WhatsAppAlertProvider(
                account_sid=_FAKE_TWILIO_SID,
                auth_token="test_token",
                from_number="whatsapp:+14155238886",
                to_numbers=["whatsapp:+1234567890"],
                max_retries=3,
                retry_delay=1,
            )

            alert = AlertPayload(
                location="Accra",
                score=85.0,
                risk_tier="EXTREME",
                message="Test alert",
                timestamp="2024-01-01T00:00:00Z",
            )

            result = provider.send(alert)

            assert result["success"] is True

    def test_send_multiple_recipients(self):
        """Test sending WhatsApp to multiple recipients."""
        with patch("twilio.rest.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            mock_message = MagicMock()
            mock_message.sid = "SM_test123"
            mock_client.messages.create.return_value = mock_message

            provider = WhatsAppAlertProvider(
                account_sid=_FAKE_TWILIO_SID,
                auth_token="test_token",
                from_number="whatsapp:+14155238886",
                to_numbers=["whatsapp:+1234567890", "whatsapp:+1987654321"],
                max_retries=3,
                retry_delay=1,
            )

            alert = AlertPayload(
                location="Accra",
                score=85.0,
                risk_tier="EXTREME",
                message="Test alert",
                timestamp="2024-01-01T00:00:00Z",
            )

            result = provider.send(alert)

            assert result["success"] is True
            assert mock_client.messages.create.call_count == 2

    def test_send_retry_on_failure(self):
        """Test retry logic on WhatsApp failure."""
        with patch("twilio.rest.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            # Make first attempt fail, second succeed
            mock_client.messages.create.side_effect = [
                Exception("Network error"),
                MagicMock(sid="SM_success"),
            ]

            provider = WhatsAppAlertProvider(
                account_sid=_FAKE_TWILIO_SID,
                auth_token="test_token",
                from_number="whatsapp:+14155238886",
                to_numbers=["whatsapp:+1234567890"],
                max_retries=3,
                retry_delay=1,
            )

            alert = AlertPayload(
                location="Accra",
                score=85.0,
                risk_tier="EXTREME",
                message="Test alert",
                timestamp="2024-01-01T00:00:00Z",
            )

            result = provider.send(alert)

            assert result["success"] is True
            assert mock_client.messages.create.call_count == 2


# ============================================================
# Email Provider Tests
# ============================================================


class TestEmailProviderComplete:
    """Complete email provider tests."""

    def test_send_success(self):
        """Test successful email sending."""
        with patch("smtplib.SMTP") as MockSMTP:
            mock_smtp = MagicMock()
            MockSMTP.return_value = mock_smtp

            provider = EmailAlertProvider(
                recipients=["test@example.com"],
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_user="test@gmail.com",
                smtp_password="test_password",
            )

            alert = AlertPayload(
                location="Accra",
                score=85.0,
                risk_tier="EXTREME",
                message="Test alert",
                timestamp="2024-01-01T00:00:00Z",
            )

            result = provider.send(alert)

            assert result["success"] is True

    def test_send_retry_on_failure(self):
        """Test email retry on failure."""
        with patch("smtplib.SMTP") as MockSMTP:
            mock_smtp = MagicMock()
            MockSMTP.return_value = mock_smtp
            # EmailAlertProvider.send() does `with smtplib.SMTP(...) as
            # server:` - a MagicMock's __enter__() returns a *different*
            # auto-generated MagicMock by default, not mock_smtp itself, so
            # without this line `server` inside send() is never the object
            # this test configures below, and mock_smtp.send_message is
            # never actually called no matter what the code does.
            mock_smtp.__enter__.return_value = mock_smtp

            # Mock the send_message to fail first, then succeed
            mock_smtp.send_message.side_effect = [Exception("Connection error"), None]

            provider = EmailAlertProvider(
                recipients=["test@example.com"],
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                # "test@gmail.com" is EmailAlertProvider's own explicit
                # placeholder-detection value (see _mock_mode in
                # email_provider.py) - using it here forces MOCK MODE,
                # which returns success without ever calling smtplib.SMTP
                # at all. Any other value takes the real (here, patched)
                # SMTP path this test actually means to exercise.
                smtp_user="ci-test-sender@example.com",
                smtp_password="test_password",
                retry_delay=0.05,
            )

            alert = AlertPayload(
                location="Accra",
                score=85.0,
                risk_tier="EXTREME",
                message="Test alert",
                timestamp="2024-01-01T00:00:00Z",
            )

            result = provider.send(alert)

            assert result["success"] is True
            assert mock_smtp.send_message.call_count >= 1  # Might retry internally

    def test_missing_recipients(self):
        """Test email provider with missing recipients."""
        provider = EmailAlertProvider(
            recipients=[],  # Empty
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="test@gmail.com",
            smtp_password="test_password",
        )

        alert = AlertPayload(
            location="Accra",
            score=85.0,
            risk_tier="EXTREME",
            message="Test alert",
            timestamp="2024-01-01T00:00:00Z",
        )

        result = provider.send(alert)
        assert (
            result["success"] is False or "no recipients" in result["message"].lower()
        )
