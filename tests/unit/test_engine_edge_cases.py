"""Edge case tests for AlertEngine - matching actual API return structure."""

import pytest
from src.alerts.engine import AlertEngine
from src.alerts.providers.mock_provider import MockAlertProvider


class TestEngineProviderFailures:
    """Test provider failure handling."""

    def test_provider_crash_handled_gracefully(self):
        """Test that provider crash doesn't crash the engine."""

        class FailingProvider(MockAlertProvider):
            def send(self, payload):
                raise Exception("Provider crashed")

        engine = AlertEngine(providers=[FailingProvider()], alert_threshold=0.0)

        result = engine.process(location="Accra", score=85, force=True)

        assert result["dispatched"] is True
        assert len(result["results"]) == 1
        assert result["results"][0]["success"] is False
        assert "crashed" in result["results"][0]["error"]

    def test_multiple_providers_partial_failure(self):
        """Test partial failure with multiple providers."""

        class FailingProvider(MockAlertProvider):
            def send(self, payload):
                raise Exception("SMS failed")

        engine = AlertEngine(
            providers=[MockAlertProvider(), FailingProvider()], alert_threshold=0.0
        )

        result = engine.process(location="Accra", score=85, force=True)

        assert result["dispatched"] is True
        assert len(result["results"]) == 2
        assert result["results"][0]["success"] is True
        assert result["results"][1]["success"] is False

    def test_no_providers_configured(self):
        """Test engine with no providers — engine adds default MockProvider."""
        engine = AlertEngine(providers=[], alert_threshold=0.0)

        result = engine.process(location="Accra", score=85)

        # Engine adds a default MockProvider when none are given
        assert len(result["results"]) == 1
        assert result["results"][0]["provider"] == "mock"
        assert result["results"][0]["success"] is True


class TestEngineThreshold:
    """Test threshold behavior."""

    def test_score_below_threshold_no_alert(self):
        engine = AlertEngine(providers=[MockAlertProvider()], alert_threshold=50.0)

        result = engine.process(location="Accra", score=30.0)

        assert result["dispatched"] is False
        assert result["results"] == []

    def test_score_at_alert_threshold_triggers_alert(self):
        engine = AlertEngine(providers=[MockAlertProvider()], alert_threshold=50.0)

        result = engine.process(location="Accra", score=50.0)

        assert result["dispatched"] is True
        assert len(result["results"]) == 1

    def test_score_above_critical_threshold(self):
        engine = AlertEngine(
            providers=[MockAlertProvider()],
            alert_threshold=50.0,
            critical_threshold=80.0,
        )

        result = engine.process(location="Accra", score=85.0)

        assert result["dispatched"] is True
        assert len(result["results"]) == 1


class TestEngineRateLimiting:
    """Test rate limiting edge cases."""

    def test_rate_limit_blocks_alert(self):
        engine = AlertEngine(
            providers=[MockAlertProvider()], alert_threshold=0.0, rate_limit_minutes=1
        )

        results = []
        for i in range(5):
            result = engine.process(location="Accra", score=85)
            results.append(result)

        for result in results:
            assert "dispatched" in result

    def test_force_bypasses_rate_limit(self):
        engine = AlertEngine(
            providers=[MockAlertProvider()], alert_threshold=0.0, rate_limit_minutes=1
        )

        result = engine.process(location="Accra", score=85, force=True)
        assert result["dispatched"] is True


class TestEngineLogging:
    """Test logging behavior."""

    def test_process_returns_result_structure(self):
        engine = AlertEngine(providers=[MockAlertProvider()], alert_threshold=0.0)

        result = engine.process(location="Accra", score=85, force=True)

        assert isinstance(result, dict)
        assert "dispatched" in result
        assert "results" in result
        assert isinstance(result["results"], list)
