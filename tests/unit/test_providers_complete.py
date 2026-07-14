"""Complete unit tests for all providers with proper mocking."""

from unittest.mock import MagicMock, patch

import pytest

from src.alerts.models import AlertPayload
from src.alerts.providers.email_provider import EmailAlertProvider
from src.alerts.providers.sms_provider import SMSAlertProvider
from src.alerts.providers.whatsapp_provider import WhatsAppAlertProvider

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
                account_sid="test_sid",
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
                account_sid="test_sid",
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
                account_sid="test_sid",
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
                account_sid="test_sid",
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
            assert mock_client.messages.create.call_count == 3  # Initial + 2 retries


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
                account_sid="test_sid",
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
                account_sid="test_sid",
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
                account_sid="test_sid",
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

            # Mock the send_message to fail first, then succeed
            mock_smtp.send_message.side_effect = [Exception("Connection error"), None]

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
