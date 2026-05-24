"""Factory for creating mock providers with configurable behavior."""

from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock
from tests.mocks.smtp_mock import MockSMTPClient, SMTPErrorType
from tests.mocks.twilio_mock import MockTwilioClient, TwilioErrorType


class MockProviderFactory:
    """Factory for creating configured mock providers."""
    
    @staticmethod
    def create_email_provider(config: Optional[Dict[str, Any]] = None):
        """Create email provider with mock SMTP."""
        config = config or {}
        
        mock_smtp = MockSMTPClient()
        
        # Configure error simulation
        error_type = config.get("error_type", SMTPErrorType.NONE)
        fail_count = config.get("fail_count", 1)
        delay_ms = config.get("delay_ms", 0)
        
        if error_type != SMTPErrorType.NONE:
            mock_smtp.set_error_mode(error_type, fail_count, delay_ms)
        
        # Patch smtplib.SMTP
        patcher = patch("smtplib.SMTP", return_value=mock_smtp)
        patcher.start()
        
        return mock_smtp, patcher
    
    @staticmethod
    def create_sms_provider(config: Optional[Dict[str, Any]] = None):
        """Create SMS provider with mock Twilio."""
        config = config or {}
        
        mock_client = MockTwilioClient()
        
        # Configure error simulation
        error_type = config.get("error_type", TwilioErrorType.NONE)
        fail_count = config.get("fail_count", 1)
        delay_ms = config.get("delay_ms", 0)
        
        if error_type != TwilioErrorType.NONE:
            mock_client.set_error_mode(error_type, fail_count, delay_ms)
        
        # Patch twilio.rest.Client
        patcher = patch("src.alerts.providers.sms_provider.Client", return_value=mock_client)
        patcher.start()
        
        return mock_client, patcher
    
    @staticmethod
    def create_whatsapp_provider(config: Optional[Dict[str, Any]] = None):
        """Create WhatsApp provider with mock Twilio."""
        config = config or {}
        
        mock_client = MockTwilioClient()
        
        # Configure error simulation
        error_type = config.get("error_type", TwilioErrorType.NONE)
        fail_count = config.get("fail_count", 1)
        delay_ms = config.get("delay_ms", 0)
        
        if error_type != TwilioErrorType.NONE:
            mock_client.set_error_mode(error_type, fail_count, delay_ms)
        
        # Patch twilio.rest.Client
        patcher = patch("src.alerts.providers.whatsapp_provider.Client", return_value=mock_client)
        patcher.start()
        
        return mock_client, patcher
    
    @staticmethod
    def cleanup(patchers: list):
        """Clean up all patchers."""
        for patcher in patchers:
            patcher.stop()
