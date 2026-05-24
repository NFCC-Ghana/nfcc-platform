"""Tests for alert formatter module."""

from datetime import datetime

from src.alerts.formatter import (
    format_alert,
    get_instruction,
    get_risk_tier,
)


class TestGetRiskTier:
    def test_extreme_threshold(self):
        assert get_risk_tier(80) == "EXTREME"

    def test_extreme_above_threshold(self):
        assert get_risk_tier(95.5) == "EXTREME"

    def test_high_threshold(self):
        assert get_risk_tier(60) == "HIGH"

    def test_high_upper_boundary(self):
        assert get_risk_tier(79.9) == "HIGH"

    def test_moderate_threshold(self):
        assert get_risk_tier(40) == "MODERATE"

    def test_moderate_upper_boundary(self):
        assert get_risk_tier(59.9) == "MODERATE"

    def test_low_boundary(self):
        assert get_risk_tier(39.9) == "LOW"

    def test_zero_score(self):
        assert get_risk_tier(0) == "LOW"

    def test_negative_score(self):
        assert get_risk_tier(-10) == "LOW"


class TestGetInstruction:
    def test_extreme_instruction(self):
        result = get_instruction("EXTREME")
        assert "evacuation" in result.lower()

    def test_high_instruction(self):
        result = get_instruction("HIGH")
        assert "prepare" in result.lower()

    def test_moderate_instruction(self):
        result = get_instruction("MODERATE")
        assert "alert" in result.lower()

    def test_low_instruction(self):
        result = get_instruction("LOW")
        # Match actual output: "No immediate action needed. Continue normal monitoring."
        assert "no action needed" in result.lower()

    def test_unknown_tier(self):
        result = get_instruction("UNKNOWN")
        # Actual output: "Monitor local conditions for updates."
        assert "monitor local conditions" in result.lower()

    def test_empty_tier(self):
        result = get_instruction("")
        assert "monitor local conditions" in result.lower()

    def test_none_tier(self):
        result = get_instruction(None)
        assert "monitor local conditions" in result.lower()


class TestFormatAlert:
    def test_basic_alert_format(self):
        timestamp = datetime(2025, 1, 1, 12, 30)
        result = format_alert(
            location="Accra",
            risk_score=85.5,
            timestamp=timestamp,
        )
        assert "NFCC FLOOD ALERT" in result
        assert "Accra" in result
        assert "85.5" in result

    def test_auto_generates_risk_tier(self):
        result = format_alert(location="Kumasi", risk_score=65)
        assert "HIGH" in result

    def test_custom_risk_tier(self):
        result = format_alert(location="Tamale", risk_score=10, risk_tier="EXTREME")
        assert "EXTREME" in result
