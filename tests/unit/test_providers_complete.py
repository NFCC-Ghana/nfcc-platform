"""Complete provider tests using mock layer."""

import pytest
from src.alerts.providers.email_provider import EmailAlertProvider
from src.alerts.providers.sms_provider import SMSAlertProvider
from src.alerts.providers.whatsapp_provider import WhatsAppAlertProvider
from src.alerts.models import AlertPayload
from tests.mocks.smtp_mock import SMTPErrorType
from tests.mocks.twilio_mock import TwilioErrorType
from tests.mocks.provider_factory import MockProviderFactory


@pytest.fixture
def alert_payload():
    """Create test alert payload."""
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
def email_config(monkeypatch):
    """Mock email configuration."""
    monkeypatch.setenv("ALERT_EMAIL_RECIPIENTS", "test@example.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "test@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "test_password")


@pytest.fixture
def sms_config(monkeypatch):
    """Mock SMS configuration."""
    monkeypatch.setenv("ALERT_SMS_RECIPIENTS", "+1234567890")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACmock")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "mock_token")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+1234567890")


@pytest.fixture
def whatsapp_config(monkeypatch):
    """Mock WhatsApp configuration."""
    monkeypatch.setenv("ALERT_WHATSAPP_RECIPIENTS", "+1234567890")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACmock")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "mock_token")
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "whatsapp:+1234567890")


# ============================================================
# EMAIL PROVIDER TESTS
# ============================================================

class TestEmailProviderComplete:
    """Complete email provider test suite."""
    
    def test_send_success(self, email_config, alert_payload):
        """Test successful email send."""
        mock_smtp, patcher = MockProviderFactory.create_email_provider()
        
        try:
            provider = EmailAlertProvider()
            result = provider.send(alert_payload)
            
            assert result["success"] is True
            assert result["provider"] == "email"
            assert len(mock_smtp.get_sent_emails()) == 1
            
            email = mock_smtp.get_last_email()
            assert "Accra" in email.body
            assert "CRITICAL" in email.body
        finally:
            patcher.stop()
    
    def test_send_with_retry_on_failure(self, email_config, alert_payload):
        """Test retry logic on failure."""
        config = {
            "error_type": SMTPErrorType.SEND_FAILED,
            "fail_count": 1,  # Fail once, succeed on retry
        }
        mock_smtp, patcher = MockProviderFactory.create_email_provider(config)
        
        try:
            provider = EmailAlertProvider()
            result = provider.send(alert_payload)
            
            # Should succeed after retry
            assert result["success"] is True
            assert len(mock_smtp.get_sent_emails()) == 1
        finally:
            patcher.stop()
    
    def test_send_auth_failure_retry(self, email_config, alert_payload):
        """Test auth failure with retry."""
        config = {
            "error_type": SMTPErrorType.AUTH_FAILED,
            "fail_count": 1,
        }
        mock_smtp, patcher = MockProviderFactory.create_email_provider(config)
        
        try:
            provider = EmailAlertProvider()
            result = provider.send(alert_payload)
            
            # Should succeed after retry
            assert result["success"] is True
        finally:
            patcher.stop()
    
    def test_send_all_retries_fail(self, email_config, alert_payload):
        """Test failure after all retries exhausted."""
        config = {
            "error_type": SMTPErrorType.SEND_FAILED,
            "fail_count": 3,  # Fail all 3 attempts
        }
        mock_smtp, patcher = MockProviderFactory.create_email_provider(config)
        
        try:
            provider = EmailAlertProvider()
            result = provider.send(alert_payload)
            
            assert result["success"] is False
            assert "error" in result
        finally:
            patcher.stop()
    
    def test_send_connection_timeout(self, email_config, alert_payload):
        """Test connection timeout handling."""
        config = {
            "error_type": SMTPErrorType.TIMEOUT,
            "fail_count": 1,
            "delay_ms": 100,
        }
        mock_smtp, patcher = MockProviderFactory.create_email_provider(config)
        
        try:
            provider = EmailAlertProvider()
            result = provider.send(alert_payload)
            
            assert result["success"] is True  # Should retry and succeed
        finally:
            patcher.stop()
    
    def test_send_rate_limit(self, email_config, alert_payload):
        """Test rate limit handling."""
        config = {
            "error_type": SMTPErrorType.RATE_LIMIT,
        }
        mock_smtp, patcher = MockProviderFactory.create_email_provider(config)
        
        try:
            provider = EmailAlertProvider()
            result = provider.send(alert_payload)
            
            assert result["success"] is False
        finally:
            patcher.stop()


# ============================================================
# SMS PROVIDER TESTS
# ============================================================

class TestSMSProviderComplete:
    """Complete SMS provider test suite."""
    
    def test_send_success(self, sms_config, alert_payload):
        """Test successful SMS send."""
        mock_client, patcher = MockProviderFactory.create_sms_provider()
        
        try:
            provider = SMSAlertProvider()
            result = provider.send(alert_payload)
            
            assert result["success"] is True
            assert len(mock_client.messages.get_sent_messages()) == 1
        finally:
            patcher.stop()
    
    def test_send_multiple_recipients(self, monkeypatch, alert_payload):
        """Test sending to multiple recipients."""
        monkeypatch.setenv("ALERT_SMS_RECIPIENTS", "+1234567890,+0987654321")
        
        mock_client, patcher = MockProviderFactory.create_sms_provider()
        
        try:
            provider = SMSAlertProvider()
            result = provider.send(alert_payload)
            
            assert result["success"] is True
            assert len(mock_client.messages.get_sent_messages()) == 2
        finally:
            patcher.stop()
    
    def test_send_retry_on_failure(self, sms_config, alert_payload):
        """Test retry on failure."""
        config = {
            "error_type": TwilioErrorType.SERVICE_UNAVAILABLE,
            "fail_count": 1,
        }
        mock_client, patcher = MockProviderFactory.create_sms_provider(config)
        
        try:
            provider = SMSAlertProvider()
            result = provider.send(alert_payload)
            
            assert result["success"] is True
        finally:
            patcher.stop()
    
    def test_send_auth_failure(self, sms_config, alert_payload):
        """Test authentication failure."""
        config = {
            "error_type": TwilioErrorType.AUTH_FAILED,
        }
        mock_client, patcher = MockProviderFactory.create_sms_provider(config)
        
        try:
            provider = SMSAlertProvider()
            result = provider.send(alert_payload)
            
            assert result["success"] is False
        finally:
            patcher.stop()
    
    def test_send_invalid_number(self, sms_config, alert_payload):
        """Test invalid phone number."""
        config = {
            "error_type": TwilioErrorType.INVALID_NUMBER,
        }
        mock_client, patcher = MockProviderFactory.create_sms_provider(config)
        
        try:
            provider = SMSAlertProvider()
            result = provider.send(alert_payload)
            
            assert result["success"] is False
        finally:
            patcher.stop()
    
    def test_send_rate_limit(self, sms_config, alert_payload):
        """Test rate limiting."""
        config = {
            "error_type": TwilioErrorType.RATE_LIMIT,
        }
        mock_client, patcher = MockProviderFactory.create_sms_provider(config)
        
        try:
            provider = SMSAlertProvider()
            result = provider.send(alert_payload)
            
            assert result["success"] is False
        finally:
            patcher.stop()


# ============================================================
# WHATSAPP PROVIDER TESTS
# ============================================================

class TestWhatsAppProviderComplete:
    """Complete WhatsApp provider test suite."""
    
    def test_send_success(self, whatsapp_config, alert_payload):
        """Test successful WhatsApp send."""
        mock_client, patcher = MockProviderFactory.create_whatsapp_provider()
        
        try:
            provider = WhatsAppAlertProvider()
            result = provider.send(alert_payload)
            
            assert result["success"] is True
            assert len(mock_client.messages.get_sent_messages()) == 1
        finally:
            patcher.stop()
    
    def test_send_multiple_recipients(self, monkeypatch, alert_payload):
        """Test sending to multiple recipients."""
        monkeypatch.setenv("ALERT_WHATSAPP_RECIPIENTS", "+1234567890,+0987654321")
        
        mock_client, patcher = MockProviderFactory.create_whatsapp_provider()
        
        try:
            provider = WhatsAppAlertProvider()
            result = provider.send(alert_payload)
            
            assert result["success"] is True
            assert len(mock_client.messages.get_sent_messages()) == 2
        finally:
            patcher.stop()
    
    def test_whatsapp_prefix_auto_added(self, monkeypatch, alert_payload):
        """Test WhatsApp prefix is automatically added."""
        monkeypatch.setenv("ALERT_WHATSAPP_RECIPIENTS", "+1234567890")
        monkeypatch.delenv("TWILIO_WHATSAPP_FROM", raising=False)
        
        mock_client, patcher = MockProviderFactory.create_whatsapp_provider()
        
        try:
            provider = WhatsAppAlertProvider()
            # Should use default WhatsApp number with prefix
            assert provider.from_number.startswith("whatsapp:")
        finally:
            patcher.stop()
    
    def test_send_retry_on_failure(self, whatsapp_config, alert_payload):
        """Test retry on failure."""
        config = {
            "error_type": TwilioErrorType.SERVICE_UNAVAILABLE,
            "fail_count": 1,
        }
        mock_client, patcher = MockProviderFactory.create_whatsapp_provider(config)
        
        try:
            provider = WhatsAppAlertProvider()
            result = provider.send(alert_payload)
            
            assert result["success"] is True
        finally:
            patcher.stop()
    
    def test_send_all_retries_fail(self, whatsapp_config, alert_payload):
        """Test failure after all retries."""
        config = {
            "error_type": TwilioErrorType.SERVICE_UNAVAILABLE,
            "fail_count": 3,
        }
        mock_client, patcher = MockProviderFactory.create_whatsapp_provider(config)
        
        try:
            provider = WhatsAppAlertProvider()
            result = provider.send(alert_payload)
            
            assert result["success"] is False
        finally:
            patcher.stop()


# ============================================================
# EDGE CASE TESTS
# ============================================================

class TestProviderEdgeCases:
    """Edge case tests for all providers."""
    
    def test_email_missing_recipients(self, monkeypatch, alert_payload):
        """Test email with no recipients configured."""
        monkeypatch.delenv("ALERT_EMAIL_RECIPIENTS", raising=False)
        
        with pytest.raises(ValueError, match="Email recipients"):
            EmailAlertProvider()
    
    def test_sms_missing_recipients(self, monkeypatch, alert_payload):
        """Test SMS with no recipients configured."""
        monkeypatch.delenv("ALERT_SMS_RECIPIENTS", raising=False)
        
        with pytest.raises(ValueError, match="SMS recipients"):
            SMSAlertProvider()
    
    def test_whatsapp_missing_recipients(self, monkeypatch, alert_payload):
        """Test WhatsApp with no recipients configured."""
        monkeypatch.delenv("ALERT_WHATSAPP_RECIPIENTS", raising=False)
        
        with pytest.raises(ValueError, match="WhatsApp recipients"):
            WhatsAppAlertProvider()
    
    def test_email_message_formatting(self, email_config, alert_payload):
        """Test email message formatting."""
        mock_smtp, patcher = MockProviderFactory.create_email_provider()
        
        try:
            provider = EmailAlertProvider()
            provider.send(alert_payload)
            
            email = mock_smtp.get_last_email()
            assert email.subject == "[NFCC] CRITICAL Flood Alert — Accra"
            assert "85.0" in email.body
        finally:
            patcher.stop()
    
    def test_sms_message_formatting(self, sms_config, alert_payload):
        """Test SMS message formatting."""
        mock_client, patcher = MockProviderFactory.create_sms_provider()
        
        try:
            provider = SMSAlertProvider()
            provider.send(alert_payload)
            
            message = mock_client.messages.get_last_message()
            assert "CRITICAL" in message.body
            assert "85" in message.body
            assert len(message.body) <= 160  # SMS character limit
        finally:
            patcher.stop()
