"""Basic mock tests for providers."""

from unittest.mock import MagicMock, patch

import pytest

from src.alerts.models import AlertPayload
from src.alerts.providers.email_provider import EmailAlertProvider
from src.alerts.providers.sms_provider import SMSAlertProvider
from src.alerts.providers.whatsapp_provider import WhatsAppAlertProvider


class TestSMSProvider:
    """Basic SMS provider tests."""

    def test_send_success(self):
        """Test successful SMS sending with mock."""
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
                timestamp="2024-01-01T00:00:00Z",
            )

            result = provider.send(alert)

            assert result["success"] is True
            mock_client.messages.create.assert_called_once()

    def test_missing_recipients(self):
        """Test SMS provider with missing recipients."""
        provider = SMSAlertProvider(
            account_sid="test_sid",
            auth_token="test_token",
            from_number="+1234567890",
            to_numbers=[],  # Empty
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
        # Should handle gracefully without raising exception
        assert isinstance(result, dict)
        assert "success" in result


class TestWhatsAppProvider:
    """Basic WhatsApp provider tests."""

    def test_send_success(self):
        """Test successful WhatsApp sending with mock."""
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
            mock_client.messages.create.assert_called_once()

    def test_missing_recipients(self):
        """Test WhatsApp provider with missing recipients."""
        provider = WhatsAppAlertProvider(
            account_sid="test_sid",
            auth_token="test_token",
            from_number="whatsapp:+14155238886",
            to_numbers=[],  # Empty
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
        assert isinstance(result, dict)
        assert "success" in result


class TestEmailProvider:
    """Basic email provider tests."""

    def test_send_success(self):
        """Test successful email sending with mock."""
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
        assert isinstance(result, dict)
        assert "success" in result
