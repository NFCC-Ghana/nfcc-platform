"""Provider test fixtures with proper mocking."""

import pytest
from src.alerts.models import AlertPayload


@pytest.fixture
def mock_email_config(monkeypatch):
    """Mock email configuration."""
    monkeypatch.setenv("ALERT_EMAIL_RECIPIENTS", "test@example.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "test@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "test_password")


@pytest.fixture
def mock_sms_config(monkeypatch):
    """Mock SMS configuration."""
    monkeypatch.setenv("ALERT_SMS_RECIPIENTS", "+1234567890")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "test_sid")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test_token")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+1234567890")


@pytest.fixture
def mock_whatsapp_config(monkeypatch):
    """Mock WhatsApp configuration."""
    monkeypatch.setenv("ALERT_WHATSAPP_RECIPIENTS", "+1234567890")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "test_sid")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test_token")
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "whatsapp:+1234567890")


@pytest.fixture
def sample_alert_payload():
    """Create sample AlertPayload for testing."""
    return AlertPayload(
        location="Accra",
        score=85.0,
        risk_tier="CRITICAL",
        message="Test alert message",
        precipitation=10.0,
        roll_3d=25.0,
        z_score=1.5
    )
