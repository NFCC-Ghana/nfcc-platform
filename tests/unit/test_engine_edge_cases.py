"""Edge case tests for AlertEngine."""

import pytest
from unittest.mock import MagicMock
from src.alerts.engine import AlertEngine
from src.alerts.providers.mock_provider import MockAlertProvider


class TestEngineEdgeCases:
    """Test edge cases for AlertEngine."""

    def test_provider_failure_does_not_crash_engine(self, trained_model):
        """Test that provider failure doesn't crash the engine."""

        class FailingProvider(MockAlertProvider):
            def send(self, payload):
                raise Exception("Provider down")

        engine = AlertEngine(
            providers=[FailingProvider()], alert_threshold=0.0, model=trained_model
        )

        result = engine.process(location="Accra", score=85, force=True)
        assert result["dispatched"] is False
        assert result["failed"] == 1

    def test_rate_limit_blocks_sending(self, trained_model):
        """Test that rate limiting blocks excessive alerts."""
        from src.alerts.rate_limit import RateLimiter

        rate_limiter = RateLimiter(max_alerts_per_hour=1, window_seconds=3600)
        engine = AlertEngine(
            providers=[MockAlertProvider()],
            rate_limiter=rate_limiter,
            alert_threshold=0.0,
            model=trained_model,
        )

        # First alert should go through
        result1 = engine.process(location="Tema", score=85, force=False)
        assert result1["dispatched"] is True

        # Second alert should be rate limited
        result2 = engine.process(location="Tema", score=85, force=False)
        assert result2["blocked"] is True
        assert result2["dispatched"] is False

    def test_partial_provider_failure(self, trained_model):
        """Test partial failure when one provider succeeds, another fails."""

        class FailingProvider(MockAlertProvider):
            def send(self, payload):
                raise Exception("SMS failed")

        engine = AlertEngine(
            providers=[MockAlertProvider(), FailingProvider()],
            alert_threshold=0.0,
            model=trained_model,
        )

        result = engine.process(location="Accra", score=85, force=True)
        assert result["sent"] == 1
        assert result["failed"] == 1
        assert result["dispatched"] is True

    def test_force_override_bypasses_rate_limit(self, trained_model):
        """Test that force=True bypasses rate limiting."""
        from src.alerts.rate_limit import RateLimiter

        rate_limiter = RateLimiter(max_alerts_per_hour=1, window_seconds=3600)
        engine = AlertEngine(
            providers=[MockAlertProvider()],
            rate_limiter=rate_limiter,
            alert_threshold=0.0,
            model=trained_model,
        )

        # First alert
        engine.process(location="Accra", score=85, force=False)

        # Second alert with force=True should go through despite rate limit
        result = engine.process(location="Accra", score=85, force=True)
        assert result["dispatched"] is True

    def test_empty_provider_list(self, trained_model):
        """Test engine with no providers."""
        engine = AlertEngine(providers=[], alert_threshold=0.0, model=trained_model)

        result = engine.process(location="Accra", score=85, force=True)
        assert result["dispatched"] is False
        assert result["sent"] == 0

    def test_formatter_is_called(self, trained_model):
        """Test that formatter is called when provided."""
        formatter_mock = MagicMock()
        formatter_mock.format_alert.return_value = "Formatted message"

        engine = AlertEngine(
            providers=[MockAlertProvider()],
            formatter=formatter_mock,
            alert_threshold=0.0,
            model=trained_model,
        )

        engine.process(location="Accra", score=88, force=True)

        # Verify formatter was called
        formatter_mock.format_alert.assert_called()

    def test_provider_receives_formatted_message(self, trained_model):
        """Test that provider receives properly formatted message."""
        mock_provider = MagicMock(spec=MockAlertProvider)
        mock_provider.name = "mock"
        mock_provider.send.return_value = {"success": True}

        engine = AlertEngine(
            providers=[mock_provider], alert_threshold=0.0, model=trained_model
        )

        engine.process(location="Accra", score=88, force=True)

        # Verify provider.send was called with AlertPayload
        mock_provider.send.assert_called_once()
        args, _ = mock_provider.send.call_args
        assert hasattr(args[0], "message")
        assert "flood" in args[0].message.lower()
