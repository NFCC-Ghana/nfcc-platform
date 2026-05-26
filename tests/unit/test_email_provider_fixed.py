"""Fixed email provider tests."""

import pytest
from unittest.mock import MagicMock, patch
from src.alerts.providers.email_provider import EmailAlertProvider
from src.alerts.models import AlertPayload


@pytest.fixture
def alert_payload():
    return AlertPayload(
        location="Accra",
        score=85.0,
        risk_tier="CRITICAL",
        message="Test alert",
        precipitation=10.0,
        roll_3d=25.0,
        z_score=1.5,
    )


@pytest.fixture
def mock_config(monkeypatch):
    monkeypatch.setenv("ALERT_EMAIL_RECIPIENTS", "test@example.com")
    monkeypatch.setenv("SMTP_HOST", "localhost")
    monkeypatch.setenv("SMTP_PORT", "1025")
    monkeypatch.setenv("SMTP_USER", "test")
    monkeypatch.setenv("SMTP_PASSWORD", "test")
    monkeypatch.setenv("TEST_MODE", "true")


class TestEmailProviderFixed:
    def test_send_success(self, mock_config, alert_payload):
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            provider = EmailAlertProvider()
            result = provider.send(alert_payload)

            assert result["success"] is True

    def test_send_retry_on_failure(self, mock_config, alert_payload):
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_server.send_message.side_effect = [Exception("Failed"), None]
            mock_smtp.return_value.__enter__.return_value = mock_server

            provider = EmailAlertProvider()
            result = provider.send(alert_payload)

            assert result["success"] is True

    def test_send_all_retries_fail(self, mock_config, alert_payload):
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_server.send_message.side_effect = Exception("Always fails")
            mock_smtp.return_value.__enter__.return_value = mock_server

            provider = EmailAlertProvider()
            result = provider.send(alert_payload)

            assert result["success"] is False

    def test_missing_recipients(self, monkeypatch, alert_payload):
        monkeypatch.delenv("ALERT_EMAIL_RECIPIENTS", raising=False)
        monkeypatch.setenv("TEST_MODE", "false")

        with pytest.raises(ValueError, match="Email recipients"):
            EmailAlertProvider()
