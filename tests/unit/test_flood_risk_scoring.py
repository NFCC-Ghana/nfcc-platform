"""Unit tests — Flood risk score computation and risk tiers."""

import numpy as np


def flood_risk_score(precipitation, roll_3d, z_score):
    score = min(precipitation / 30 * 40, 40)
    score += min(roll_3d / 60 * 35, 35)
    score += min(max(z_score, 0) / 3 * 25, 25)
    return round(np.clip(score, 0, 100), 2)


def risk_tier(score):
    if score >= 75:
        return "CRITICAL"
    elif score >= 50:
        return "HIGH"
    elif score >= 25:
        return "MODERATE"
    return "LOW"


class TestFloodRiskScore:
    def test_dry_day_scores_zero(self):
        assert flood_risk_score(0.0, 0.0, 0.0) == 0.0

    def test_score_non_negative(self):
        assert flood_risk_score(0.0, 0.0, -5.0) >= 0.0

    def test_score_capped_at_100(self):
        assert flood_risk_score(500.0, 1000.0, 10.0) <= 100.0

    def test_heavy_rain_high_score(self):
        score = flood_risk_score(45.0, 95.0, 3.8)
        assert score >= 75.0

    def test_score_increases_with_rain(self):
        low = flood_risk_score(5.0, 10.0, 0.5)
        high = flood_risk_score(30.0, 70.0, 2.5)
        assert high > low


class TestRiskTier:
    def test_low_tier(self):
        assert risk_tier(10.0) == "LOW"

    def test_moderate_tier(self):
        assert risk_tier(25.0) == "MODERATE"

    def test_high_tier(self):
        assert risk_tier(50.0) == "HIGH"

    def test_critical_tier(self):
        assert risk_tier(75.0) == "CRITICAL"
