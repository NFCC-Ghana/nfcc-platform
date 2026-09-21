"""Regression tests for GET /v1/alert-subscriptions
(src/api/v1/alert_subscriptions.py) - operator visibility into real
WhatsApp/Telegram alert opt-ins, mirroring
src/api/v1/community_reports.py's role for inbound reports."""

import pytest

from src.database import channel_subscriptions_db


@pytest.fixture(autouse=True, scope="module")
def _ensure_table_exists():
    channel_subscriptions_db.init_channel_subscriptions_table()


@pytest.fixture
def cleanup_subscription():
    created = []

    def _track(channel, identifier):
        created.append((channel, identifier))
        return identifier

    yield _track

    for channel, identifier in created:
        channel_subscriptions_db.unsubscribe(channel, identifier)


def test_requires_api_key(api_client):
    resp = api_client.get("/v1/alert-subscriptions", headers={"X-API-Key": ""})
    assert resp.status_code in (401, 403)


def test_lists_real_subscriber(api_client, cleanup_subscription):
    identifier = cleanup_subscription("whatsapp", "test-v1-alert-sub-1")
    channel_subscriptions_db.subscribe("whatsapp", identifier, district="Accra Central")

    resp = api_client.get("/v1/alert-subscriptions")
    assert resp.status_code == 200
    data = resp.json()
    assert any(s["identifier"] == identifier and s["district"] == "Accra Central" for s in data["subscriptions"])


def test_inactive_excluded_by_default(api_client, cleanup_subscription):
    identifier = cleanup_subscription("whatsapp", "test-v1-alert-sub-2")
    channel_subscriptions_db.subscribe("whatsapp", identifier, district="Tamale")
    channel_subscriptions_db.unsubscribe("whatsapp", identifier)

    resp = api_client.get("/v1/alert-subscriptions")
    assert not any(s["identifier"] == identifier for s in resp.json()["subscriptions"])

    resp_all = api_client.get("/v1/alert-subscriptions?active_only=false")
    assert any(s["identifier"] == identifier for s in resp_all.json()["subscriptions"])
