"""Regression tests for src/alerts/providers/telegram_provider.py - the
outbound half of the Telegram citizen-reporting channel. Recipients
come entirely from real subscriptions (src/database/
channel_subscriptions_db.py); unlike WhatsAppAlertProvider there was
never a static-recipient env var to fall back to, so "no subscribers"
is a real, expected empty-send outcome, not a misconfiguration.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.alerts.models import AlertPayload
from src.alerts.providers.telegram_provider import TelegramAlertProvider, send_telegram_message
from src.config.settings import settings
from src.database import channel_subscriptions_db


@pytest.fixture(autouse=True, scope="module")
def _ensure_table_exists():
    channel_subscriptions_db.init_channel_subscriptions_table()


@pytest.fixture(autouse=True)
def _telegram_configured(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "fake-token-for-test")
    monkeypatch.setattr(settings, "ALERT_DRY_RUN", False)


@pytest.fixture
def cleanup_subscription():
    created = []

    def _track(identifier):
        created.append(identifier)
        return identifier

    yield _track

    for identifier in created:
        channel_subscriptions_db.unsubscribe("telegram", identifier)


def _alert(location="Accra Central", risk_tier="HIGH", score=60.0):
    return AlertPayload(location=location, score=score, risk_tier=risk_tier, message="Test warning", precipitation=45.0)


def test_no_subscribers_reports_failure_not_crash():
    provider = TelegramAlertProvider()
    result = provider.send(_alert(location="Sunyani"))  # no test subscribers ever target Sunyani
    assert result["success"] is False
    assert result["recipient_count"] == 0


def test_sends_to_real_matching_subscriber(cleanup_subscription):
    identifier = cleanup_subscription("test-telegram-provider-1")
    channel_subscriptions_db.subscribe("telegram", identifier, district="Accra Central")

    with patch("src.alerts.providers.telegram_provider.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"ok": True})
        result = TelegramAlertProvider().send(_alert(location="Accra Central"))

    assert result["success"] is True
    assert result["recipient_count"] == 1
    sent_json = mock_post.call_args.kwargs["json"]
    assert sent_json["chat_id"] == identifier
    assert "Accra Central" in sent_json["text"]
    assert "HIGH" in sent_json["text"]


def test_does_not_send_to_subscriber_of_different_district(cleanup_subscription):
    identifier = cleanup_subscription("test-telegram-provider-2")
    channel_subscriptions_db.subscribe("telegram", identifier, district="Tamale")

    with patch("src.alerts.providers.telegram_provider.requests.post") as mock_post:
        result = TelegramAlertProvider().send(_alert(location="Accra Central"))

    assert result["recipient_count"] == 0
    mock_post.assert_not_called()


def test_dry_run_does_not_call_telegram_api(cleanup_subscription, monkeypatch):
    identifier = cleanup_subscription("test-telegram-provider-3")
    channel_subscriptions_db.subscribe("telegram", identifier, district="Accra Central")
    monkeypatch.setattr(settings, "ALERT_DRY_RUN", True)

    with patch("src.alerts.providers.telegram_provider.requests.post") as mock_post:
        result = TelegramAlertProvider().send(_alert(location="Accra Central"))

    assert result["dry_run"] is True
    assert result["recipient_count"] == 1
    mock_post.assert_not_called()


def test_missing_bot_token_fails_cleanly(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", None)
    result = TelegramAlertProvider().send(_alert())
    assert result["success"] is False
    assert "TELEGRAM_BOT_TOKEN" in result["message"]


def test_send_telegram_message_reports_failure_on_bad_response():
    with patch("src.alerts.providers.telegram_provider.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=400, json=lambda: {"ok": False})
        result = send_telegram_message(123, "hello")
    assert result["success"] is False


def test_send_telegram_message_without_token_configured(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", None)
    result = send_telegram_message(123, "hello")
    assert result["success"] is False
    assert "TELEGRAM_BOT_TOKEN" in result["error"]
