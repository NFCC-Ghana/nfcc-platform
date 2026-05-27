"""Factory for creating mock providers with patched clients."""

from unittest.mock import patch, MagicMock
from src.alerts.providers.sms_provider import SMSProvider
from src.alerts.providers.whatsapp_provider import WhatsAppProvider
from src.alerts.providers.email_provider import EmailProvider


class MockProviderFactory:
    """Factory for creating provider instances with mocked external clients."""

    @staticmethod
    def create_sms_provider(config=None):
        """Create SMS provider with mocked Twilio client."""
        if config is None:
            config = {
                "account_sid": "test_sid",
                "auth_token": "test_token",
                "from_number": "+1234567890",
                "recipients": ["+1234567890"],
                "retry_attempts": 3,
                "retry_delay": 1,
            }

        # Patch the Twilio Client at the correct import location
        patcher = patch("twilio.rest.Client")
        mock_client_class = patcher.start()
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock the messages.create method
        mock_message = MagicMock()
        mock_message.sid = "SM_test123"
        mock_client.messages.create.return_value = mock_message

        provider = SMSProvider(config)
        return mock_client, patcher, provider

    @staticmethod
    def create_whatsapp_provider(config=None):
        """Create WhatsApp provider with mocked Twilio client."""
        if config is None:
            config = {
                "account_sid": "test_sid",
                "auth_token": "test_token",
                "from_number": "whatsapp:+14155238886",
                "recipients": ["whatsapp:+1234567890"],
                "retry_attempts": 3,
                "retry_delay": 1,
            }

        # Patch the Twilio Client at the correct import location
        patcher = patch("twilio.rest.Client")
        mock_client_class = patcher.start()
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock the messages.create method
        mock_message = MagicMock()
        mock_message.sid = "SM_test123"
        mock_client.messages.create.return_value = mock_message

        provider = WhatsAppProvider(config)
        return mock_client, patcher, provider

    @staticmethod
    def create_email_provider(config=None):
        """Create email provider with mocked SMTP."""
        if config is None:
            config = {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "test@gmail.com",
                "password": "test_password",
                "from_email": "test@gmail.com",
                "recipients": ["test@example.com"],
                "retry_attempts": 3,
                "retry_delay": 1,
            }

        # Patch SMTP
        patcher = patch("smtplib.SMTP")
        mock_smtp_class = patcher.start()
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        provider = EmailProvider(config)
        return mock_smtp, patcher, provider
