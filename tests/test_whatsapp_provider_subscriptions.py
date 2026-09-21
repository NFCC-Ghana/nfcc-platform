"""Regression tests for WhatsAppAlertProvider's dynamic-recipient merge
(src/alerts/providers/whatsapp_provider.py's _get_recipients) - real,
per-district channel subscribers (src/database/channel_subscriptions_db.py)
UNIONED with the static settings.WHATSAPP_RECIPIENTS list, not either/or.

Kept in its own file (not tests/unit/test_providers_complete.py or
test_providers_mock.py) since it needs the real channel_subscriptions
table initialized and cleaned-up subscription rows, unlike those files'
pure-mock static-list tests.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.alerts.models import AlertPayload
from src.alerts.providers.whatsapp_provider import WhatsAppAlertProvider
from src.database import channel_subscriptions_db

_FAKE_TWILIO_SID = "AC" + "0" * 32


@pytest.fixture(autouse=True, scope="module")
def _ensure_table_exists():
    channel_subscriptions_db.init_channel_subscriptions_table()


@pytest.fixture
def cleanup_subscription():
    created = []

    def _track(identifier):
        created.append(identifier)
        return identifier

    yield _track

    for identifier in created:
        channel_subscriptions_db.unsubscribe("whatsapp", identifier)


def _alert(location="Accra Central", risk_tier="HIGH"):
    return AlertPayload(location=location, score=60.0, risk_tier=risk_tier, message="Test", precipitation=45.0)


def test_static_recipients_still_receive_alerts_with_zero_subscribers():
    """Backward compatibility: a provider configured only with the old
    static settings.WHATSAPP_RECIPIENTS-style list, with no dynamic
    subscribers at all, must behave exactly as before."""
    with patch("twilio.rest.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(sid="SM123")

        provider = WhatsAppAlertProvider(
            account_sid=_FAKE_TWILIO_SID,
            auth_token="test_token",
            from_number="+1234567890",
            to_numbers=["+1234567890"],
        )
        result = provider.send(_alert(location="Sunyani"))  # no test subscribers ever target Sunyani

    assert result["success"] is True
    assert result["recipient_count"] == 1


def test_dynamic_subscriber_added_alongside_static_list(cleanup_subscription):
    identifier = cleanup_subscription("test-whatsapp-provider-1")
    channel_subscriptions_db.subscribe("whatsapp", identifier, district="Accra Central")

    with patch("twilio.rest.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(sid="SM123")

        provider = WhatsAppAlertProvider(
            account_sid=_FAKE_TWILIO_SID,
            auth_token="test_token",
            from_number="+1234567890",
            to_numbers=["+1234567890"],  # the static "always notify" number
        )
        result = provider.send(_alert(location="Accra Central"))

    # static number + the one real dynamic subscriber = 2 recipients
    assert result["recipient_count"] == 2
    sent_to = {call.kwargs["to"] for call in mock_client.messages.create.call_args_list}
    assert "whatsapp:+1234567890" in sent_to
    assert f"whatsapp:{identifier}" in sent_to


def test_dynamic_subscriber_of_different_district_not_included(cleanup_subscription):
    identifier = cleanup_subscription("test-whatsapp-provider-2")
    channel_subscriptions_db.subscribe("whatsapp", identifier, district="Tamale")

    with patch("twilio.rest.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(sid="SM123")

        provider = WhatsAppAlertProvider(
            account_sid=_FAKE_TWILIO_SID,
            auth_token="test_token",
            from_number="+1234567890",
            to_numbers=[],  # no static recipients at all
        )
        result = provider.send(_alert(location="Accra Central"))

    assert result["recipient_count"] == 0


def test_no_static_recipients_pure_dynamic_send(cleanup_subscription):
    """The whole point of this feature: a provider with NO static
    recipients configured at all still delivers, purely from real
    subscribers - this is what get_provider_status() now assumes is
    possible (src/config/settings.py no longer requires
    WHATSAPP_RECIPIENTS for the provider to be considered usable)."""
    identifier = cleanup_subscription("test-whatsapp-provider-3")
    channel_subscriptions_db.subscribe("whatsapp", identifier, district="Kumasi")

    with patch("twilio.rest.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(sid="SM123")

        provider = WhatsAppAlertProvider(
            account_sid=_FAKE_TWILIO_SID,
            auth_token="test_token",
            from_number="+1234567890",
            to_numbers=[],
        )
        result = provider.send(_alert(location="Kumasi"))

    assert result["success"] is True
    assert result["recipient_count"] == 1
