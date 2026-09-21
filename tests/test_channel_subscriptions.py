"""Regression tests for src/database/channel_subscriptions_db.py and
src/community/alert_subscription_commands.py - the outbound half of
citizen reporting: a citizen opts into flood alerts through the same
WhatsApp/Telegram chat they already report floods from, and
src/alerts/providers/whatsapp_provider.py + telegram_provider.py
genuinely query these subscribers on every real alert send (unlike the
pre-existing email `subscriptions` table, found to have zero real
consumers anywhere in the send path).

Every test here uses its own unique fake identifier
("test-chan-sub-<n>") and cleans up via unsubscribe() in a fixture,
since this module - unlike community_memory.py's isolated per-test DB -
shares data/alerts.db with every other alert_db table already relying on
that file persisting across the whole pytest session.
"""

import pytest

from src.community.alert_subscription_commands import (
    handle_subscription_command,
    parse_subscription_command,
)
from src.database import channel_subscriptions_db


@pytest.fixture(autouse=True, scope="module")
def _ensure_table_exists():
    """Self-contained rather than relying on src.api.main's module-level
    init call having already run in this pytest session by the time
    this file is collected."""
    channel_subscriptions_db.init_channel_subscriptions_table()


@pytest.fixture
def cleanup_subscription():
    """Unsubscribes a list of (channel, identifier) pairs after the test,
    regardless of what the test itself did - keeps this file from
    leaking rows into other tests sharing data/alerts.db."""
    created = []

    def _track(channel, identifier):
        created.append((channel, identifier))
        return identifier

    yield _track

    for channel, identifier in created:
        channel_subscriptions_db.unsubscribe(channel, identifier)


def test_subscribe_and_fetch_for_matching_district(cleanup_subscription):
    identifier = cleanup_subscription("whatsapp", "test-chan-sub-1")
    channel_subscriptions_db.subscribe("whatsapp", identifier, district="Accra Central")

    matches = channel_subscriptions_db.get_subscribers_for_alert("whatsapp", "Accra Central", "HIGH")
    assert any(m["identifier"] == identifier for m in matches)


def test_subscriber_not_returned_for_different_district(cleanup_subscription):
    identifier = cleanup_subscription("whatsapp", "test-chan-sub-2")
    channel_subscriptions_db.subscribe("whatsapp", identifier, district="Tamale")

    matches = channel_subscriptions_db.get_subscribers_for_alert("whatsapp", "Accra Central", "HIGH")
    assert not any(m["identifier"] == identifier for m in matches)


def test_all_districts_subscriber_matches_any_district(cleanup_subscription):
    identifier = cleanup_subscription("telegram", "test-chan-sub-3")
    channel_subscriptions_db.subscribe("telegram", identifier, district=None)

    for district in ("Accra Central", "Tamale", "Kumasi"):
        matches = channel_subscriptions_db.get_subscribers_for_alert("telegram", district, "HIGH")
        assert any(m["identifier"] == identifier for m in matches)


def test_min_risk_tier_filters_out_lower_severity_alerts(cleanup_subscription):
    identifier = cleanup_subscription("whatsapp", "test-chan-sub-4")
    channel_subscriptions_db.subscribe("whatsapp", identifier, district="Accra Central", min_risk_tier="CRITICAL")

    moderate_matches = channel_subscriptions_db.get_subscribers_for_alert("whatsapp", "Accra Central", "MODERATE")
    assert not any(m["identifier"] == identifier for m in moderate_matches)

    critical_matches = channel_subscriptions_db.get_subscribers_for_alert("whatsapp", "Accra Central", "CRITICAL")
    assert any(m["identifier"] == identifier for m in critical_matches)


def test_unsubscribe_removes_from_matches(cleanup_subscription):
    identifier = cleanup_subscription("whatsapp", "test-chan-sub-5")
    channel_subscriptions_db.subscribe("whatsapp", identifier, district="Accra Central")
    assert channel_subscriptions_db.unsubscribe("whatsapp", identifier) is True

    matches = channel_subscriptions_db.get_subscribers_for_alert("whatsapp", "Accra Central", "HIGH")
    assert not any(m["identifier"] == identifier for m in matches)


def test_resubscribe_reactivates_and_updates_district(cleanup_subscription):
    identifier = cleanup_subscription("whatsapp", "test-chan-sub-6")
    channel_subscriptions_db.subscribe("whatsapp", identifier, district="Tamale")
    channel_subscriptions_db.unsubscribe("whatsapp", identifier)
    channel_subscriptions_db.subscribe("whatsapp", identifier, district="Accra Central")

    matches = channel_subscriptions_db.get_subscribers_for_alert("whatsapp", "Accra Central", "HIGH")
    assert any(m["identifier"] == identifier for m in matches)
    old_district_matches = channel_subscriptions_db.get_subscribers_for_alert("whatsapp", "Tamale", "HIGH")
    assert not any(m["identifier"] == identifier for m in old_district_matches)


class TestParseSubscriptionCommand:
    def test_not_a_command_returns_none(self):
        assert parse_subscription_command("Kaneshie flooding, cars can't pass") is None

    def test_bare_alerts_on_subscribes_all_districts(self):
        cmd = parse_subscription_command("ALERTS ON")
        assert cmd.action == "subscribe"
        assert cmd.district is None
        assert cmd.recognized is True

    def test_alerts_on_all_keyword(self):
        cmd = parse_subscription_command("alerts on all")
        assert cmd.district is None
        assert cmd.recognized is True

    def test_alerts_on_recognized_district(self):
        cmd = parse_subscription_command("ALERTS ON Kaneshie")
        assert cmd.action == "subscribe"
        assert cmd.district == "Accra Central"
        assert cmd.recognized is True

    def test_alerts_on_unrecognized_place(self):
        cmd = parse_subscription_command("ALERTS ON Narnia")
        assert cmd.action == "subscribe"
        assert cmd.recognized is False

    def test_alerts_off(self):
        cmd = parse_subscription_command("ALERTS OFF")
        assert cmd.action == "unsubscribe"

    def test_stop_is_treated_as_unsubscribe(self):
        cmd = parse_subscription_command("stop")
        assert cmd.action == "unsubscribe"


class TestHandleSubscriptionCommand:
    def test_returns_none_for_non_command_text(self):
        assert handle_subscription_command("whatsapp", "irrelevant", "Kaneshie flooding") is None

    def test_subscribe_creates_real_row(self, cleanup_subscription):
        identifier = cleanup_subscription("whatsapp", "test-chan-sub-7")
        reply = handle_subscription_command("whatsapp", identifier, "ALERTS ON Kaneshie")
        assert "Accra Central" in reply

        matches = channel_subscriptions_db.get_subscribers_for_alert("whatsapp", "Accra Central", "HIGH")
        assert any(m["identifier"] == identifier for m in matches)

    def test_unrecognized_district_does_not_subscribe(self, cleanup_subscription):
        identifier = cleanup_subscription("whatsapp", "test-chan-sub-8")
        reply = handle_subscription_command("whatsapp", identifier, "ALERTS ON Narnia")
        assert "didn't recognize" in reply

        all_subs = channel_subscriptions_db.get_all_channel_subscriptions(active_only=True)
        assert not any(s["identifier"] == identifier for s in all_subs)
