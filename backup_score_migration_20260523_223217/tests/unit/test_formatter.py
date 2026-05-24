from datetime import datetime
from src.alerts.formatter import format_alert, get_risk_tier, get_instruction


class TestGetRiskTier:
    def test_basic(self):
        assert get_risk_tier(80) == "EXTREME"


class TestGetInstruction:
    def test_basic(self):
        assert "EVACUATION" in get_instruction("EXTREME").upper()


class TestFormatAlert:
    def test_basic(self):
        ts = datetime(2026, 1, 1, 10, 0)

        result = format_alert(
            location="Accra",
            score=85,
            risk_tier="EXTREME",
            timestamp=ts,
        )

        assert "Accra" in result
        assert "85" in result
