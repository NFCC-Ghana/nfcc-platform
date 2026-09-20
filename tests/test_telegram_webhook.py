"""Regression tests for POST /webhooks/telegram
(src/api/routes/telegram_webhook.py) - the second citizen-reporting
intake channel, added because Telegram's Bot API has no billing/trial
restriction anywhere (unlike Twilio - see test_whatsapp_webhook.py and
whatsapp_webhook.py's module docstring for that history).

Shares its parsing (src/community/report_parsing.py) with the WhatsApp
webhook, so most classification edge cases are already covered there;
these tests focus on what's specific to Telegram's own message shape:
JSON updates (not Twilio's form-encoded payload), location-only
messages with no text, /start, and the X-Telegram-Bot-Api-Secret-Token
auth scheme.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.community.community_memory import community_memory
from src.config.settings import settings


@pytest.fixture(autouse=True)
def _isolated_reports_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_community_reports.db"
    monkeypatch.setattr(community_memory, "db_path", db_path)
    community_memory._init_db()
    yield


@pytest.fixture(autouse=True)
def _telegram_settings(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "fake-token-for-test")
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", None)


@pytest.fixture
def mock_send():
    with patch("src.api.routes.telegram_webhook.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        yield mock_post


def _update(chat_id=1, user_id=1, text=None, location=None, first_name="Test"):
    message = {"from": {"id": user_id, "first_name": first_name}, "chat": {"id": chat_id}}
    if text is not None:
        message["text"] = text
    if location is not None:
        message["location"] = location
    return {"update_id": 1, "message": message}


def test_recognized_community_maps_and_replies(api_client, mock_send):
    resp = api_client.post(
        "/webhooks/telegram", json=_update(text="Kaneshie flooding, cars can't pass, about 40cm")
    )
    assert resp.status_code == 200
    reply_text = mock_send.call_args.kwargs["json"]["text"]
    assert "Kaneshie" in reply_text
    assert "Accra Central" in reply_text

    reports = api_client.get("/v1/community-reports?limit=1").json()["reports"]
    assert reports[0]["district"] == "Accra Central"
    assert reports[0]["reporter_phone"] == "telegram:1"
    assert reports[0]["flood_depth_m"] == pytest.approx(0.40)


def test_location_only_message_is_saved(api_client, mock_send):
    resp = api_client.post(
        "/webhooks/telegram",
        json=_update(chat_id=2, user_id=2, location={"latitude": 5.55, "longitude": -0.2}),
    )
    assert resp.status_code == 200
    reports = api_client.get("/v1/community-reports?limit=1").json()["reports"]
    assert reports[0]["latitude"] == pytest.approx(5.55)
    assert reports[0]["longitude"] == pytest.approx(-0.2)


def test_no_text_no_location_prompts_for_content(api_client, mock_send):
    resp = api_client.post("/webhooks/telegram", json=_update(chat_id=3, user_id=3))
    assert resp.status_code == 200
    reply_text = mock_send.call_args.kwargs["json"]["text"]
    assert "didn't receive any text or location" in reply_text


def test_start_command_returns_help(api_client, mock_send):
    resp = api_client.post("/webhooks/telegram", json=_update(chat_id=4, user_id=4, text="/start"))
    assert resp.status_code == 200
    reply_text = mock_send.call_args.kwargs["json"]["text"]
    assert "NFCC Flood Reporting" in reply_text


def test_non_message_update_is_acknowledged_and_ignored(api_client, mock_send):
    resp = api_client.post("/webhooks/telegram", json={"update_id": 1, "channel_post": {}})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    mock_send.assert_not_called()


def test_missing_secret_token_rejected(api_client, monkeypatch, mock_send):
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "super-secret-123")
    resp = api_client.post("/webhooks/telegram", json=_update(text="test"))
    assert resp.status_code == 403


def test_correct_secret_token_accepted(api_client, monkeypatch, mock_send):
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "super-secret-123")
    resp = api_client.post(
        "/webhooks/telegram",
        json=_update(text="Osu flooding"),
        headers={"X-Telegram-Bot-Api-Secret-Token": "super-secret-123"},
    )
    assert resp.status_code == 200


def test_critical_urgency_escalates_reply(api_client, mock_send):
    resp = api_client.post(
        "/webhooks/telegram",
        json=_update(chat_id=5, user_id=5, text="Help, we are trapped, water still rising in Circle"),
    )
    assert resp.status_code == 200
    reply_text = mock_send.call_args.kwargs["json"]["text"]
    assert "immediate danger" in reply_text
