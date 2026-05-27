"""Tests for alert formatter module."""

import pytest
from src.alerts.formatter import get_risk_tier, get_instruction, format_alert


class TestGetRiskTier:
    """Test risk tier classification."""
    
    def test_extreme_threshold(self):
        assert get_risk_tier(85) == "EXTREME"
        assert get_risk_tier(100) == "EXTREME"
    
    def test_extreme_above_threshold(self):
        assert get_risk_tier(95) == "EXTREME"
    
    def test_high_upper_boundary(self):
        assert get_risk_tier(69.9) == "HIGH"
    
    def test_high_threshold(self):
        assert get_risk_tier(50) == "HIGH"
        assert get_risk_tier(69.9) == "HIGH"
    
    def test_moderate_upper_boundary(self):
        assert get_risk_tier(49.9) == "MODERATE"
    
    def test_moderate_threshold(self):
        assert get_risk_tier(30) == "MODERATE"
        assert get_risk_tier(49.9) == "MODERATE"
    
    def test_low_boundary(self):
        assert get_risk_tier(29.9) == "LOW"
    
    def test_zero_score(self):
        assert get_risk_tier(0) == "LOW"
    
    def test_negative_score(self):
        assert get_risk_tier(-10) == "LOW"


class TestGetInstruction:
    """Test instruction generation."""
    
    def test_extreme_instruction(self):
        result = get_instruction("EXTREME")
        assert "seek higher ground" in result.lower()
    
    def test_critical_instruction(self):
        result = get_instruction("CRITICAL")
        assert "prepare" in result.lower()
    
    def test_high_instruction(self):
        result = get_instruction("HIGH")
        assert "precautions" in result.lower()
    
    def test_moderate_instruction(self):
        result = get_instruction("MODERATE")
        assert "monitor" in result.lower()
    
    def test_low_instruction(self):
        result = get_instruction("LOW")
        assert "no immediate action" in result.lower()
    
    def test_empty_tier(self):
        result = get_instruction("")
        assert "alert" in result.lower()
    
    def test_unknown_tier(self):
        result = get_instruction("UNKNOWN")
        assert "alert" in result.lower()
    
    def test_none_tier(self):
        result = get_instruction(None)
        assert "alert" in result.lower()


class TestFormatAlert:
    """Test alert formatting."""
    
    def test_basic_alert_format(self):
        result = format_alert(location="Accra", score=45.5)
        assert result["location"] == "Accra"
        assert result["score"] == 45.5
        assert "instruction" in result
    
    def test_auto_generates_risk_tier(self):
        result = format_alert(location="Kumasi", score=65)
        assert result["risk_tier"] == "HIGH"
    
    def test_custom_risk_tier(self):
        result = format_alert(location="Tamale", score=10, risk_tier="EXTREME")
        assert result["risk_tier"] == "EXTREME"
