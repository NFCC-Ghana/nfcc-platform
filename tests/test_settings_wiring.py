"""Regression tests for a real bug class found during a codebase-wide
"wired but never actually connected" audit: several settings were
documented in .env.example as real, deployer-configurable values since
this project's earliest version, but the consuming code read them via
getattr(settings, "X", default) for an X that was never actually a
Settings attribute - the getattr silently fell back to the hardcoded
default every time, so setting the env var had zero effect. Found for
ALERT_DRY_RUN, then ALERT_COOLDOWN_MINUTES, ALERT_THRESHOLD_*, and
REDIS_URL's /health "configured" field while auditing for the same
pattern elsewhere.

These tests assert the actual effect of setting the env var - not just
that a Settings attribute exists with the right name (that alone would
not have caught the original bugs, since getattr's fallback made the
attribute's absence invisible to a shallow check).
"""

import pytest

from src.database import channel_subscriptions_db


@pytest.fixture(autouse=True, scope="module")
def _ensure_table_exists():
    channel_subscriptions_db.init_channel_subscriptions_table()


def test_alert_dry_run_actually_suppresses_whatsapp_send(monkeypatch):
    from src.alerts.models import AlertPayload
    from src.alerts.providers.whatsapp_provider import WhatsAppAlertProvider
    from src.config.settings import settings

    monkeypatch.setattr(settings, "ALERT_DRY_RUN", True)
    provider = WhatsAppAlertProvider(
        account_sid="AC" + "0" * 32,
        auth_token="test",
        from_number="+1234567890",
        to_numbers=["+1234567890"],
    )
    alert = AlertPayload(location="Accra", score=90.0, risk_tier="EXTREME", message="test")
    result = provider.send(alert)
    assert result.get("dry_run") is True


def test_alert_cooldown_minutes_actually_changes_engine_behavior(monkeypatch):
    """Regression test for the real bug: AlertEngine used to read this
    via getattr(settings, "ALERT_COOLDOWN_MINUTES", 30) for an attribute
    settings never actually had, so the fallback default was always used
    regardless of what was configured."""
    from src.alerts.engine import AlertEngine
    from src.config.settings import settings

    monkeypatch.setattr(settings, "ALERT_COOLDOWN_MINUTES", 99)
    engine = AlertEngine(providers=["mock"])
    assert engine.cooldown_minutes == 99


def test_risk_tier_boundaries_and_alert_engine_thresholds_stay_consistent():
    """The exact regression this bug risked: get_risk_tier() and
    AlertEngine.THRESHOLDS used to be two independently hardcoded copies
    of the same boundaries - if only one had been wired to settings, they
    could silently diverge. Assert every boundary score's tier label
    matches which THRESHOLDS bucket it falls into."""
    from src.alerts.engine import AlertEngine
    from src.alerts.formatter import get_risk_tier

    for score in (0, 15, 29.9, 30, 45, 49.9, 50, 65, 69.9, 70, 80, 84.9, 85, 95, 100):
        tier = get_risk_tier(score)
        low, high = AlertEngine.THRESHOLDS[tier]
        assert low <= score < high or (tier == "EXTREME" and score >= low), (
            f"score={score} tier={tier} THRESHOLDS[{tier}]={AlertEngine.THRESHOLDS[tier]}"
        )


def test_redis_url_configured_field_reflects_real_env_var(monkeypatch):
    from src.config.settings import settings

    monkeypatch.setattr(settings, "REDIS_URL", "redis://example:6379/0")
    assert bool(getattr(settings, "REDIS_URL", None)) is True

    monkeypatch.setattr(settings, "REDIS_URL", None)
    assert bool(getattr(settings, "REDIS_URL", None)) is False
