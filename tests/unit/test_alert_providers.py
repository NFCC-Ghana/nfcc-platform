# flake8: noqa: E402

"""Comprehensive unit tests for alert providers (email, SMS, WhatsApp)."""

# ==========================================================
# STANDARD LIB IMPORTS (must be first)
# ==========================================================
import sys
from unittest.mock import MagicMock, patch

# ===================================================================
# MOCK TWILIO AT MODULE LEVEL (avoids import errors)
# ===================================================================
mock_twilio = MagicMock()
mock_twilio.rest = MagicMock()
mock_twilio.rest.Client = MagicMock()
mock_twilio.base = MagicMock()
mock_twilio.base.exceptions = MagicMock()


class MockTwilioRestException(Exception):
    def __init__(self, *args, **kwargs):
        msg = kwargs.get("msg", "Twilio error")
        super().__init__(msg)


mock_twilio.base.exceptions.TwilioRestException = MockTwilioRestException
sys.modules["twilio"] = mock_twilio
sys.modules["twilio.rest"] = mock_twilio.rest
sys.modules["twilio.base"] = mock_twilio.base
sys.modules["twilio.base.exceptions"] = mock_twilio.base.exceptions

# Now import pytest and providers
import pytest
from src.alerts.providers.base import AlertPayload
from src.alerts.providers.email_provider import EmailAlertProvider
from src.alerts.providers.sms_provider import SMSAlertProvider
from src.alerts.providers.whatsapp_provider import WhatsAppAlertProvider

# ===================================================================
# TEST DATA FIXTURES
# ===================================================================


@pytest.fixture
def sample_payload():
    return AlertPayload(
        location="Accra Central",
        risk_score=85.5,
        risk_tier="HIGH",
        precipitation=25.3,
        roll_3d=65.2,
        z_score=2.5,
    )


@pytest.fixture
def critical_payload():
    return AlertPayload(
        location="Tema Beach",
        risk_score=95.0,
        risk_tier="CRITICAL",
        precipitation=65.8,
        roll_3d=145.0,
        z_score=4.2,
    )


@pytest.fixture
def moderate_payload():
    return AlertPayload(
        location="Madina",
        risk_score=55.0,
        risk_tier="MODERATE",
        precipitation=12.5,
        roll_3d=28.0,
        z_score=1.2,
    )


@pytest.fixture
def low_payload():
    return AlertPayload(
        location="East Legon",
        risk_score=25.0,
        risk_tier="LOW",
        precipitation=3.2,
        roll_3d=8.5,
        z_score=0.3,
    )


# ===================================================================
# EMAIL PROVIDER TESTS
# ===================================================================


class TestEmailAlertProvider:
    """Comprehensive tests for EmailAlertProvider."""

    def test_init_with_env_vars(self, monkeypatch):
        monkeypatch.setenv("SMTP_HOST", "smtp.sendgrid.net")
        monkeypatch.setenv("SMTP_PORT", "587")
        monkeypatch.setenv("SMTP_USER", "test@example.com")
        monkeypatch.setenv("SMTP_PASS", "secret")
        monkeypatch.setenv("ALERT_EMAIL_FROM", "alerts@nfcc.gov.gh")
        monkeypatch.setenv(
            "ALERT_EMAIL_RECIPIENTS", "admin@example.com,ops@example.com"
        )

        provider = EmailAlertProvider()
        assert provider.smtp_host == "smtp.sendgrid.net"
        assert provider.smtp_port == 587
        assert provider.max_retries == 3

    def test_init_with_params(self):
        provider = EmailAlertProvider(
            smtp_host="smtp.mailgun.org",
            smtp_port=465,
            smtp_user="user@mailgun.com",
            smtp_pass="password123",
            from_email="noreply@nfcc.gh",
            to_emails=["test1@example.com", "test2@example.com"],
            max_retries=5,
            retry_delay=1.5,
        )
        assert provider.smtp_host == "smtp.mailgun.org"
        assert provider.max_retries == 5

    def test_init_missing_required_env_vars(self, monkeypatch):
        monkeypatch.delenv("SMTP_USER", raising=False)
        monkeypatch.delenv("SMTP_PASS", raising=False)
        monkeypatch.delenv("ALERT_EMAIL_FROM", raising=False)
        monkeypatch.delenv("ALERT_EMAIL_RECIPIENTS", raising=False)

        with pytest.raises(EnvironmentError, match="requires SMTP_USER, SMTP_PASS"):
            EmailAlertProvider()

    def test_build_html_high_risk(self, sample_payload):
        provider = EmailAlertProvider(
            smtp_user="test",
            smtp_pass="test",
            from_email="test@example.com",
            to_emails=["test@example.com"],
        )
        html = provider._build_html(sample_payload)
        assert "NFCC FLOOD ALERT" in html
        assert "HIGH" in html

    def test_build_html_critical_risk(self, critical_payload):
        provider = EmailAlertProvider(
            smtp_user="test",
            smtp_pass="test",
            from_email="test@example.com",
            to_emails=["test@example.com"],
        )
        html = provider._build_html(critical_payload)
        assert "CRITICAL" in html

    def test_build_html_moderate_risk(self, moderate_payload):
        provider = EmailAlertProvider(
            smtp_user="test",
            smtp_pass="test",
            from_email="test@example.com",
            to_emails=["test@example.com"],
        )
        html = provider._build_html(moderate_payload)
        assert "MODERATE" in html

    def test_build_html_low_risk(self, low_payload):
        provider = EmailAlertProvider(
            smtp_user="test",
            smtp_pass="test",
            from_email="test@example.com",
            to_emails=["test@example.com"],
        )
        html = provider._build_html(low_payload)
        assert "LOW" in html

    @patch("smtplib.SMTP")
    def test_send_success_first_attempt(self, mock_smtp_class, sample_payload):
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        provider = EmailAlertProvider(
            smtp_user="test@gmail.com",
            smtp_pass="password",
            from_email="alerts@nfcc.gh",
            to_emails=["admin@example.com"],
        )
        result = provider.send(sample_payload)

        assert result["success"] is True
        assert result["provider"] == "email"
        mock_server.sendmail.assert_called_once()

    @patch("smtplib.SMTP")
    def test_send_success_multiple_recipients(self, mock_smtp_class, sample_payload):
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        provider = EmailAlertProvider(
            smtp_user="test@gmail.com",
            smtp_pass="password",
            from_email="alerts@nfcc.gh",
            to_emails=[
                "admin1@example.com",
                "admin2@example.com",
                "admin3@example.com",
            ],
        )
        result = provider.send(sample_payload)

        assert result["success"] is True
        assert len(mock_server.sendmail.call_args[0][1]) == 3

    @patch("smtplib.SMTP")
    @patch("time.sleep")
    def test_send_retry_on_sendmail_failure(
        self, mock_sleep, mock_smtp_class, sample_payload
    ):
        mock_server = MagicMock()
        mock_server.sendmail.side_effect = [Exception("Connection lost"), None]
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        provider = EmailAlertProvider(
            smtp_user="test@gmail.com",
            smtp_pass="password",
            from_email="alerts@nfcc.gh",
            to_emails=["admin@example.com"],
            max_retries=3,
            retry_delay=0.1,
        )

        result = provider.send(sample_payload)

        assert result["success"] is True
        assert mock_server.sendmail.call_count == 2
        mock_sleep.assert_called_once_with(0.1)

    @patch("smtplib.SMTP")
    @patch("time.sleep")
    def test_send_retry_on_login_failure(
        self, mock_sleep, mock_smtp_class, sample_payload
    ):
        mock_server = MagicMock()
        mock_server.login.side_effect = [Exception("Authentication timeout"), None]
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        provider = EmailAlertProvider(
            smtp_user="test@gmail.com",
            smtp_pass="password",
            from_email="alerts@nfcc.gh",
            to_emails=["admin@example.com"],
            max_retries=3,
            retry_delay=0.1,
        )

        result = provider.send(sample_payload)

        assert result["success"] is True
        assert mock_server.login.call_count == 2
        mock_sleep.assert_called_once_with(0.1)

    @patch("smtplib.SMTP")
    @patch("time.sleep")
    def test_send_failure_after_all_retries(
        self, mock_sleep, mock_smtp_class, sample_payload
    ):
        mock_server = MagicMock()
        mock_server.sendmail.side_effect = Exception("Authentication failed")
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        provider = EmailAlertProvider(
            smtp_user="test@gmail.com",
            smtp_pass="wrong_password",
            from_email="alerts@nfcc.gh",
            to_emails=["admin@example.com"],
            max_retries=3,
            retry_delay=0.1,
        )

        result = provider.send(sample_payload)

        assert result["success"] is False
        assert "Authentication failed" in result["error"]
        assert mock_server.sendmail.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("smtplib.SMTP")
    @patch("time.sleep")
    def test_send_smtp_connection_failure(
        self, mock_sleep, mock_smtp_class, sample_payload
    ):
        mock_smtp_class.side_effect = Exception("Connection refused")

        provider = EmailAlertProvider(
            smtp_host="invalid.smtp.com",
            smtp_port=587,
            smtp_user="test@gmail.com",
            smtp_pass="password",
            from_email="alerts@nfcc.gh",
            to_emails=["admin@example.com"],
            max_retries=3,
            retry_delay=0.1,
        )

        result = provider.send(sample_payload)

        assert result["success"] is False
        assert "Connection refused" in result["error"]
        assert mock_smtp_class.call_count == 3
        assert mock_sleep.call_count == 2


# ===================================================================
# SMS PROVIDER TESTS
# ===================================================================


class TestSMSAlertProvider:
    """Comprehensive tests for SMSAlertProvider."""

    def test_init_with_env_vars(self, monkeypatch):
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123456789")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token123")
        monkeypatch.setenv("TWILIO_SMS_FROM", "+1234567890")
        monkeypatch.setenv("ALERT_SMS_RECIPIENTS", "+233501234567,+233502345678")

        provider = SMSAlertProvider()
        assert provider.account_sid == "AC123456789"
        assert provider.to_numbers == ["+233501234567", "+233502345678"]

    def test_init_with_params(self):
        provider = SMSAlertProvider(
            account_sid="AC_CUSTOM",
            auth_token="custom_token",
            from_number="+1987654321",
            to_numbers=["+233555555555"],
            max_retries=5,
            retry_delay=1.0,
        )
        assert provider.account_sid == "AC_CUSTOM"
        assert provider.max_retries == 5

    def test_init_missing_required_config(self, monkeypatch):
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_SMS_FROM", raising=False)
        monkeypatch.delenv("ALERT_SMS_RECIPIENTS", raising=False)

        with pytest.raises(EnvironmentError, match="requires TWILIO_ACCOUNT_SID"):
            SMSAlertProvider()

    def test_send_success_single_recipient(self, sample_payload):
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = "SM123456789"
        mock_client.messages.create.return_value = mock_message

        with patch("twilio.rest.Client", return_value=mock_client):
            provider = SMSAlertProvider(
                account_sid="AC_test",
                auth_token="token",
                from_number="+1234567890",
                to_numbers=["+233501234567"],
            )
            result = provider.send(sample_payload)

        assert result["success"] is True
        assert result["message_id"] == "SM123456789"

    def test_send_success_multiple_recipients(self, sample_payload):
        mock_client = MagicMock()
        mock_message1 = MagicMock()
        mock_message1.sid = "SM111"
        mock_message2 = MagicMock()
        mock_message2.sid = "SM222"
        mock_client.messages.create.side_effect = [mock_message1, mock_message2]

        with patch("twilio.rest.Client", return_value=mock_client):
            provider = SMSAlertProvider(
                account_sid="AC_test",
                auth_token="token",
                from_number="+1234567890",
                to_numbers=["+233501234567", "+233502345678"],
            )
            result = provider.send(sample_payload)

        assert result["success"] is True
        assert result["message_id"] == "SM111, SM222"

    @patch("time.sleep")
    def test_send_retry_on_failure_then_success(self, mock_sleep, sample_payload):
        from twilio.base.exceptions import TwilioRestException

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            TwilioRestException(
                status=500, uri="/", method="POST", msg="Service unavailable"
            ),
            MagicMock(sid="SM_SUCCESS"),
        ]

        with patch("twilio.rest.Client", return_value=mock_client):
            provider = SMSAlertProvider(
                account_sid="AC_test",
                auth_token="token",
                from_number="+1234567890",
                to_numbers=["+233501234567"],
                max_retries=3,
                retry_delay=0.1,
            )
            result = provider.send(sample_payload)

        assert result["success"] is True
        assert result["message_id"] == "SM_SUCCESS"
        mock_sleep.assert_called_once_with(0.1)

    @patch("time.sleep")
    def test_send_failure_after_all_retries(self, mock_sleep, sample_payload):
        from twilio.base.exceptions import TwilioRestException

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = TwilioRestException(
            status=401, uri="/", method="POST", msg="Authentication failed"
        )

        with patch("twilio.rest.Client", return_value=mock_client):
            provider = SMSAlertProvider(
                account_sid="AC_test",
                auth_token="wrong_token",
                from_number="+1234567890",
                to_numbers=["+233501234567"],
                max_retries=3,
                retry_delay=0.1,
            )
            result = provider.send(sample_payload)

        assert result["success"] is False
        assert "Authentication failed" in result["error"]

    @patch("time.sleep")
    def test_send_first_recipient_fails_returns_error(self, mock_sleep):
        from twilio.base.exceptions import TwilioRestException

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = TwilioRestException(
            status=500, uri="/", method="POST", msg="Failed"
        )

        payload = AlertPayload(
            location="Test",
            risk_score=90.0,
            risk_tier="HIGH",
            precipitation=30.0,
            roll_3d=70.0,
            z_score=3.0,
        )

        with patch("twilio.rest.Client", return_value=mock_client):
            provider = SMSAlertProvider(
                account_sid="AC_test",
                auth_token="token",
                from_number="+1234567890",
                to_numbers=["+233111111111", "+233222222222"],
                max_retries=2,
                retry_delay=0.1,
            )
            result = provider.send(payload)

        assert result["success"] is False
        assert "Failed" in result["error"]


# ===================================================================
# WHATSAPP PROVIDER TESTS
# ===================================================================


class TestWhatsAppAlertProvider:
    """Comprehensive tests for WhatsAppAlertProvider."""

    def test_init_with_env_vars(self, monkeypatch):
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123456789")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token123")
        monkeypatch.setenv("ALERT_WHATSAPP_RECIPIENTS", "+233501234567")

        provider = WhatsAppAlertProvider()
        assert provider.account_sid == "AC123456789"
        assert provider.from_number == "whatsapp:+14155238886"

    def test_init_default_whatsapp_from_number(self, monkeypatch):
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
        monkeypatch.setenv("ALERT_WHATSAPP_RECIPIENTS", "+233501234567")

        provider = WhatsAppAlertProvider()
        assert provider.from_number == "whatsapp:+14155238886"

    def test_init_with_params(self):
        provider = WhatsAppAlertProvider(
            account_sid="AC_CUSTOM",
            auth_token="custom_token",
            from_number="whatsapp:+1987654321",
            to_numbers=["+233555555555"],
            max_retries=5,
        )
        assert provider.account_sid == "AC_CUSTOM"
        assert provider.max_retries == 5

    def test_init_missing_recipients(self, monkeypatch):
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
        monkeypatch.delenv("ALERT_WHATSAPP_RECIPIENTS", raising=False)

        with pytest.raises(EnvironmentError, match="requires TWILIO_ACCOUNT_SID"):
            WhatsAppAlertProvider()

    def test_send_success_single_recipient(self, sample_payload):
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = "WH123456789"
        mock_client.messages.create.return_value = mock_message

        with patch("twilio.rest.Client", return_value=mock_client):
            provider = WhatsAppAlertProvider(
                account_sid="AC_test", auth_token="token", to_numbers=["+233501234567"]
            )
            result = provider.send(sample_payload)

        assert result["success"] is True
        assert result["message_id"] == "WH123456789"

    def test_send_handles_whatsapp_prefix_correctly(self, sample_payload):
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = "WH123"
        mock_client.messages.create.return_value = mock_message

        with patch("twilio.rest.Client", return_value=mock_client):
            provider = WhatsAppAlertProvider(
                account_sid="AC_test",
                auth_token="token",
                to_numbers=["whatsapp:+233501234567"],
            )
            result = provider.send(sample_payload)

        assert result["success"] is True

    def test_send_success_multiple_recipients(self, sample_payload):
        mock_client = MagicMock()
        mock_message1 = MagicMock()
        mock_message1.sid = "WH111"
        mock_message2 = MagicMock()
        mock_message2.sid = "WH222"
        mock_client.messages.create.side_effect = [mock_message1, mock_message2]

        with patch("twilio.rest.Client", return_value=mock_client):
            provider = WhatsAppAlertProvider(
                account_sid="AC_test",
                auth_token="token",
                to_numbers=["+233501234567", "+233502345678"],
            )
            result = provider.send(sample_payload)

        assert result["success"] is True
        assert result["message_id"] == "WH111, WH222"

    @patch("time.sleep")
    def test_send_retry_on_failure_then_success(self, mock_sleep, critical_payload):
        from twilio.base.exceptions import TwilioRestException

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            TwilioRestException(
                status=503, uri="/", method="POST", msg="Service unavailable"
            ),
            MagicMock(sid="WH_SUCCESS"),
        ]

        with patch("twilio.rest.Client", return_value=mock_client):
            provider = WhatsAppAlertProvider(
                account_sid="AC_test",
                auth_token="token",
                to_numbers=["+233501234567"],
                max_retries=3,
                retry_delay=0.1,
            )
            result = provider.send(critical_payload)

        assert result["success"] is True
        assert result["message_id"] == "WH_SUCCESS"
        mock_sleep.assert_called_once_with(0.1)

    @patch("time.sleep")
    def test_send_failure_after_all_retries(self, mock_sleep, sample_payload):
        from twilio.base.exceptions import TwilioRestException

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = TwilioRestException(
            status=403, uri="/", method="POST", msg="Forbidden"
        )

        with patch("twilio.rest.Client", return_value=mock_client):
            provider = WhatsAppAlertProvider(
                account_sid="AC_test",
                auth_token="wrong_token",
                to_numbers=["+233501234567"],
                max_retries=3,
                retry_delay=0.1,
            )
            result = provider.send(sample_payload)

        assert result["success"] is False
        assert "Forbidden" in result["error"]


# ===================================================================
# INTEGRATION TESTS
# ===================================================================


class TestAllProvidersIntegration:
    def test_all_providers_have_correct_names(self):
        email_provider = EmailAlertProvider(
            smtp_user="test",
            smtp_pass="test",
            from_email="test@example.com",
            to_emails=["test@example.com"],
        )
        sms_provider = SMSAlertProvider(
            account_sid="test",
            auth_token="test",
            from_number="+123",
            to_numbers=["+123"],
        )
        whatsapp_provider = WhatsAppAlertProvider(
            account_sid="test", auth_token="test", to_numbers=["+123"]
        )

        assert email_provider.name == "email"
        assert sms_provider.name == "sms"
        assert whatsapp_provider.name == "whatsapp"

    def test_all_providers_return_consistent_response_format(self, sample_payload):
        email_provider = EmailAlertProvider(
            smtp_user="test",
            smtp_pass="test",
            from_email="test@example.com",
            to_emails=["test@example.com"],
        )
        sms_provider = SMSAlertProvider(
            account_sid="test",
            auth_token="test",
            from_number="+123",
            to_numbers=["+123"],
        )
        whatsapp_provider = WhatsAppAlertProvider(
            account_sid="test", auth_token="test", to_numbers=["+123"]
        )

        mock_twilio_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = "TEST_SID"
        mock_twilio_client.messages.create.return_value = mock_message

        with (
            patch("smtplib.SMTP"),
            patch("twilio.rest.Client", return_value=mock_twilio_client),
        ):
            for provider in [email_provider, sms_provider, whatsapp_provider]:
                result = provider.send(sample_payload)
                assert "success" in result
                assert "provider" in result
                assert provider.name == result["provider"]
