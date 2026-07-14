"""Edge case tests for AlertEngine - provider failures, rate limiting, force bypass."""

from unittest.mock import MagicMock

import pytest

from src.alerts.engine import AlertEngine
from src.alerts.providers.mock_provider import MockAlertProvider


class TestEngineThreshold:
    """Test threshold-based alert suppression."""

    def test_no_alert_below_threshold(self, alert_engine_no_cooldown):
        """Score below 30 should NOT trigger alert."""
        result = alert_engine_no_cooldown.process(
            location="Accra",
            score=10.0,
            precipitation=0,
            force=True,
        )
        assert result["alert_sent"] is False
        assert "below moderate threshold" in result.get("reason", "")

    def test_alert_at_threshold(self, alert_engine_no_cooldown):
        """Score at 30 should trigger alert."""
        result = alert_engine_no_cooldown.process(
            location="Accra",
            score=30.0,
            precipitation=30,
            force=True,
        )
        assert result["alert_sent"] is True

    def test_alert_above_critical(self, alert_engine_no_cooldown):
        """Score above 85 should trigger alert."""
        result = alert_engine_no_cooldown.process(
            location="Accra",
            score=90.0,
            precipitation=100,
            force=True,
        )
        assert result["alert_sent"] is True


class TestEngineRateLimiting:
    """Test rate limiting behavior."""

    def test_rate_limit_blocks_alert(self):
        """After rate limit exhausted, alerts should be blocked."""
        # Create engine with EXPLICIT limit of 3 (not relying on env config)
        engine = AlertEngine(
            providers=[MockAlertProvider()],
            alerts_per_hour=3,
        )
        engine.cooldown_minutes = 0

        location = "Accra"

        # First 3 alerts should be allowed
        for i in range(3):
            result = engine.process(
                location=location,
                score=90.0,
                precipitation=50,
                force=False,
            )
            assert result["alert_sent"] is True, f"Alert {i+1} should be allowed"

        # 4th alert should be blocked
        result = engine.process(
            location=location,
            score=90.0,
            precipitation=50,
            force=False,
        )

        assert result["alert_sent"] is False
        assert "rate limited" in result.get("reason", "").lower()

    def test_force_bypasses_rate_limit(self):
        """Force flag should bypass rate limit."""
        # Create engine with EXPLICIT limit
        engine = AlertEngine(
            providers=[MockAlertProvider()],
            alerts_per_hour=3,
        )
        engine.cooldown_minutes = 0

        location = "Accra"

        # Manually record 5 sends (exceeding limit)
        for i in range(5):
            engine.rate_limiter.record_send(location)

        # Force should bypass rate limit
        result = engine.process(
            location=location,
            score=90.0,
            precipitation=50,
            force=True,
        )

        assert result["alert_sent"] is True


class TestEngineProviderFailures:
    """Test provider failure handling with duck-typed mocks."""

    def test_provider_crash_handled_gracefully(self):
        """A crashing provider should not stop other providers."""
        # Create mock providers with duck-typed 'send' method
        failing_provider = MagicMock()
        failing_provider.send.side_effect = Exception("Provider crashed")
        failing_provider.name = "failing"

        working_provider = MagicMock()
        working_provider.send.return_value = {
            "success": True,
            "message": "Sent",
            "provider": "working",
        }
        working_provider.name = "working"

        engine = AlertEngine(providers=[failing_provider, working_provider])

        result = engine.process(
            location="Accra",
            score=90.0,
            precipitation=50,
            force=True,
        )

        assert len(result["providers"]) == 2
        assert result["providers"][0]["success"] is False
        assert result["providers"][1]["success"] is True
        assert result["alert_sent"] is True

        # Verify both providers were called
        failing_provider.send.assert_called_once()
        working_provider.send.assert_called_once()

    def test_multiple_providers_partial_failure(self):
        """Partial failure should not stop successful providers."""
        failing_provider = MagicMock()
        failing_provider.send.side_effect = Exception("Send failed")
        failing_provider.name = "failing"

        working_provider = MagicMock()
        working_provider.send.return_value = {
            "success": True,
            "message": "Sent",
            "provider": "working",
        }
        working_provider.name = "working"

        engine = AlertEngine(providers=[failing_provider, working_provider])

        result = engine.process(
            location="Accra",
            score=90.0,
            precipitation=50,
            force=True,
        )

        assert len(result["providers"]) == 2
        assert result["providers"][0]["success"] is False
        assert result["providers"][1]["success"] is True
        assert result["alert_sent"] is True

    def test_no_providers_uses_mock(self):
        """With no providers, engine should use mock provider."""
        engine = AlertEngine(providers=[])

        result = engine.process(
            location="Accra",
            score=90.0,
            precipitation=50,
            force=True,
        )

        assert result["alert_sent"] is True
        assert len(result["providers"]) == 1
        assert result["providers"][0]["provider"] == "mock"

    def test_string_provider_names_work(self):
        """String provider names should be resolved via factory."""
        engine = AlertEngine(providers=["mock"])

        result = engine.process(
            location="Accra",
            score=90.0,
            precipitation=50,
            force=True,
        )

        assert result["alert_sent"] is True
        assert len(result["providers"]) == 1


class TestEngineLogging:
    """Test logging and result structure."""

    def test_process_returns_result_structure(self, alert_engine):
        """Result should contain expected fields."""
        alert_engine.cooldown_minutes = 0
        result = alert_engine.process(
            location="Accra",
            score=30.0,
            precipitation=30,
            force=True,
        )

        assert "alert_sent" in result
        assert "risk_tier" in result
        assert "score" in result
        assert isinstance(result["score"], float)
