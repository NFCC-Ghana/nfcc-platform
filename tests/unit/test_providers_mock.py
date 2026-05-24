"""Mock provider tests - no real credentials needed."""

import pytest
from unittest.mock import MagicMock, patch
from src.alerts.providers.email_provider import EmailAlertProvider
from src.alerts.providers.sms_provider import SMSAlertProvider
from src.alerts.providers.whatsapp_provider import WhatsAppAlertProvider
from src.alerts.models import AlertPayload


@pytest.fixture
def alert_payload():
    return AlertPayload(
        location="Accra",
        score=85.0,
        risk_tier="CRITICAL",
        message="Test flood alert",
        precipitation=10.0,
        roll_3d=25.0,
        z_score=1.5
    )


@pytest.fixture
def mock_email_config(monkeypatch):
    monkeypatch.setenv("ALERT_EMAIL_RECIPIENTS", "test@example.com")
    monkeypatch.setenv("SMTP_HOST", "localhost")
    monkeypatch.setenv("SMTP_PORT", "1025")
    monkeypatch.setenv("SMTP_USER", "test")
    monkeypatch.setenv("SMTP_PASSWORD", "test")
    monkeypatch.setenv("TEST_MODE", "true")


@pytest.fixture
def mock_sms_config(monkeypatch):
    monkeypatch.setenv("ALERT_SMS_RECIPIENTS", "+1234567890")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "test_sid")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test_token")
    monkeypatch.setenv("TWILIO_SMS_FROM", "+1234567890")
    monkeypatch.setenv("TEST_MODE", "true")


@pytest.fixture
def mock_whatsapp_config(monkeypatch):
    monkeypatch.setenv("ALERT_WHATSAPP_RECIPIENTS", "+1234567890")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "test_sid")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test_token")
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "whatsapp:+1234567890")
    monkeypatch.setenv("TEST_MODE", "true")


class TestEmailProvider:
    def test_send_success(self, mock_email_config, alert_payload):
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            provider = EmailAlertProvider()
            result = provider.send(alert_payload)

            assert result["success"] is True
            assert provider.name == "email"

    def test_missing_recipients(self, monkeypatch, alert_payload):
        monkeypatch.delenv("ALERT_EMAIL_RECIPIENTS", raising=False)
        monkeypatch.setenv("TEST_MODE", "false")

        with pytest.raises(ValueError, match="Email recipients"):
            EmailAlertProvider()


class TestSMSProvider:
    def test_send_success(self, mock_sms_config, alert_payload):
        provider = SMSAlertProvider()
        result = provider.send(alert_payload)

        assert result["success"] is True
        assert provider.name == "sms"

    def test_missing_recipients(self, monkeypatch, alert_payload):
        monkeypatch.delenv("ALERT_SMS_RECIPIENTS", raising=False)
        monkeypatch.setenv("TEST_MODE", "false")

        with pytest.raises(EnvironmentError, match="SMS provider requires"):
            SMSAlertProvider()


class TestWhatsAppProvider:
    def test_send_success(self, mock_whatsapp_config, alert_payload):
        provider = WhatsAppAlertProvider()
        result = provider.send(alert_payload)

        assert result["success"] is True
        assert provider.name == "whatsapp"

    def test_missing_recipients(self, monkeypatch, alert_payload):
        monkeypatch.delenv("ALERT_WHATSAPP_RECIPIENTS", raising=False)
        monkeypatch.setenv("TEST_MODE", "false")

        with pytest.raises(EnvironmentError, match="WhatsApp provider requires"):
            WhatsAppAlertProvider()
