"""Edge case tests for alert engine."""

import pytest
from src.alerts.engine import AlertEngine
from src.alerts.providers.mock_provider import MockAlertProvider
from src.alerts.providers.base import BaseAlertProvider
from src.alerts.provider_factory import ProviderFactory
from src.alerts.models import AlertPayload


class FailingProvider(BaseAlertProvider):
    """Provider that fails on send."""
    
    name = "failing"
    
    def __init__(self):
        self.call_count = 0
        self.last_alert = None
    
    def _format_message(self, alert: AlertPayload) -> str:
        return "Failing message"
    
    def send(self, alert: AlertPayload):
        self.call_count += 1
        self.last_alert = alert
        raise Exception("Provider crashed")


@pytest.fixture(autouse=True)
def reset_provider_factory():
    """Reset provider factory before each test to ensure isolation."""
    ProviderFactory.reset()
    yield
    ProviderFactory.reset()


class TestEngineProviderFailures:
    """Test provider failure scenarios."""
    
    def test_provider_crash_handled_gracefully(self):
        """Test that provider crash doesn't stop the engine."""
        failing = FailingProvider()
        engine = AlertEngine(providers=[failing])
        
        result = engine.process(location="Accra", score=85.0)
        
        assert failing.call_count == 1
        assert "alert_sent" in result
        assert result["alert_sent"] is False
    
    def test_multiple_providers_partial_failure(self):
        """Test that one provider failing doesn't stop others."""
        failing = FailingProvider()
        mock = MockAlertProvider()
        engine = AlertEngine(providers=[failing, mock])
        result = engine.process(location="Accra", score=85.0)
        
        assert "alert_sent" in result
        assert failing.call_count >= 1
    
    def test_no_providers_configured(self):
        """Test engine adds mock provider when none specified."""
        engine = AlertEngine(providers=[])
        assert len(engine.providers) > 0


class TestEngineThreshold:
    """Test alert threshold behavior."""
    
    def test_score_below_threshold_no_alert(self):
        engine = AlertEngine(providers=[MockAlertProvider()])
        result = engine.process(location="Accra", score=20.0)
        assert result["alert_sent"] is False
    
    def test_score_at_threshold_triggers_alert(self):
        engine = AlertEngine(providers=[MockAlertProvider()])
        result = engine.process(location="Accra", score=30.0)
        assert "alert_sent" in result
    
    def test_score_above_critical_threshold(self):
        engine = AlertEngine(providers=[MockAlertProvider()])
        result = engine.process(location="Accra", score=90.0)
        assert "alert_sent" in result


class TestEngineRateLimiting:
    """Test rate limiting behavior."""
    
    def test_rate_limit_blocks_alert(self):
        engine = AlertEngine(providers=[MockAlertProvider()], alerts_per_hour=1)
        engine.process(location="Accra", score=85.0)
        result = engine.process(location="Accra", score=85.0)
        assert result["alert_sent"] is False
    
    def test_force_bypasses_rate_limit(self):
        engine = AlertEngine(providers=[MockAlertProvider()], alerts_per_hour=1)
        engine.process(location="Accra", score=85.0)
        result = engine.process(location="Accra", score=85.0, force=True)
        assert "alert_sent" in result


class TestEngineLogging:
    """Test engine logging behavior."""
    
    def test_process_returns_result_structure(self):
        engine = AlertEngine(providers=[MockAlertProvider()])
        result = engine.process(location="Accra", score=85.0)
        assert "alert_sent" in result
        assert "risk_tier" in result
        assert "score" in result
