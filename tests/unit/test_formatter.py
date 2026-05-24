"""Tests for alert formatter module."""

from datetime import datetime


from src.alerts.formatter import (
    format_alert,
    get_instruction,
    get_risk_tier,
)

# =========================================================
# RISK TIER TESTS
# =========================================================


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


# =========================================================
# INSTRUCTION TESTS
# =========================================================


class TestGetInstruction:
    def test_extreme_instruction(self):
        result = get_instruction("EXTREME")
        assert "IMMEDIATE EVACUATION" in result

    def test_high_instruction(self):
        result = get_instruction("HIGH")
        assert "Prepare for flooding" in result

    def test_moderate_instruction(self):
        result = get_instruction("MODERATE")
        assert "Stay alert" in result

    def test_low_instruction(self):
        result = get_instruction("LOW")
        assert "No immediate action needed" in result

    def test_unknown_tier(self):
        result = get_instruction("UNKNOWN")
        assert result == "Monitor local conditions for updates."

    def test_empty_tier(self):
        result = get_instruction("")
        assert result == "Monitor local conditions for updates."

    def test_none_tier(self):
        result = get_instruction(None)
        assert result == "Monitor local conditions for updates."


# =========================================================
# FORMAT ALERT TESTS
# =========================================================


class TestFormatAlert:
    def test_basic_alert_format(self):
        timestamp = datetime(2025, 1, 1, 12, 30)

        result = format_alert(
            location="Accra",
            score=85.5,
            timestamp=timestamp,
        )

        assert "NFCC FLOOD ALERT" in result
        assert "Accra" in result
        assert "85.5 / 100" in result
        assert "EXTREME" in result

    def test_auto_generates_risk_tier(self):
        result = format_alert(
            location="Kumasi",
            score=65,
        )

        assert "HIGH" in result

    def test_custom_risk_tier(self):
        result = format_alert(
            location="Tamale",
            score=10,
            risk_tier="EXTREME",
        )

        assert "EXTREME" in result

    def test_excludes_instruction_when_disabled(self):
        result = format_alert(
            location="Cape Coast",
            score=90,
            include_instruction=False,
        )

        assert "INSTRUCTION" not in result

    def test_includes_instruction_by_default(self):
        result = format_alert(
            location="Ho",
            score=90,
        )

        assert "INSTRUCTION" in result

    def test_timestamp_formatting(self):
        timestamp = datetime(2024, 6, 15, 8, 45)

        result = format_alert(
            location="Bolgatanga",
            score=50,
            timestamp=timestamp,
        )

        assert "2024-06-15 08:45" in result

    def test_none_timestamp_uses_current_time(self):
        result = format_alert(
            location="Accra",
            score=50,
            timestamp=None,
        )

        assert "Time" in result
        assert "Accra" in result
        assert "/ 100" in result

    def test_low_risk_emoji(self):
        result = format_alert(
            location="Sunyani",
            score=10,
        )

        assert "🟢" in result

    def test_moderate_risk_emoji(self):
        result = format_alert(
            location="Takoradi",
            score=45,
        )

        assert "🟡" in result

    def test_high_risk_emoji(self):
        result = format_alert(
            location="Wa",
            score=70,
        )

        assert "🟠" in result

    def test_extreme_risk_emoji(self):
        result = format_alert(
            location="Tema",
            score=95,
        )

        assert "🔴🔥" in result

    def test_unknown_tier_emoji_fallback(self):
        result = format_alert(
            location="Unknown",
            score=50,
            risk_tier="CUSTOM",
        )

        assert "⚠️" in result

    def test_empty_location(self):
        result = format_alert(
            location="",
            score=50,
        )

        assert "Location    :" in result

    def test_zero_score(self):
        result = format_alert(
            location="Accra",
            score=0,
        )

        assert "0.0 / 100" in result

    def test_decimal_score_rounding(self):
        result = format_alert(
            location="Accra",
            score=77.777,
        )

        assert "77.8 / 100" in result


# =========================================================
# EDGE CASES
# =========================================================


class TestFormatterEdgeCases:
    def test_very_large_score(self):
        result = format_alert(
            location="Accra",
            score=999,
        )

        assert "999.0 / 100" in result

    def test_unicode_location(self):
        result = format_alert(
            location="São Paulo",
            score=70,
        )

        assert "São Paulo" in result

    def test_multiline_output(self):
        result = format_alert(
            location="Accra",
            score=80,
        )

        assert "\n" in result
        assert result.count("\n") >= 5

    def test_returns_string(self):
        result = format_alert(
            location="Accra",
            score=50,
        )

        assert isinstance(result, str)
