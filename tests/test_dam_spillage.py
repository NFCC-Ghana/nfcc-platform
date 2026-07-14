"""
Unit tests for dam spillage prediction model.
"""

import pytest

from src.models.dam_spillage import (
    compute_spillage_probability,
    get_spillage_forecast,
    validate_historical_events,
)


def test_probability_range():
    """Test that probability is always between 0 and 100."""
    result = compute_spillage_probability(100, 80, 200)
    assert 0 <= result <= 100

    result = compute_spillage_probability(0, 0, 0)
    assert result == 0

    result = compute_spillage_probability(500, 500, 500)
    assert result <= 100


def test_high_risk_akosombo():
    """Test high risk conditions (based on 2023 Akosombo event)."""
    result = compute_spillage_probability(180, 95, 450)
    assert result > 70
    assert result >= 85


def test_high_risk_bagre():
    """Test high risk conditions for Bagre dam."""
    result = compute_spillage_probability(160, 92, 380)
    assert result > 70


def test_medium_risk():
    """Test medium risk conditions."""
    result = compute_spillage_probability(80, 60, 250)
    assert 40 <= result <= 70


def test_low_risk():
    """Test low risk conditions."""
    result = compute_spillage_probability(20, 30, 100)
    assert result < 40


def test_extreme_conditions():
    """Test extreme conditions (should be >70)."""
    result = compute_spillage_probability(500, 95, 1000)
    assert result > 70


def test_zero_conditions():
    """Test zero conditions (should be 0)."""
    result = compute_spillage_probability(0, 0, 0)
    assert result == 0


def test_get_spillage_forecast_returns_all_fields():
    """Test that forecast returns all required fields."""
    forecast = get_spillage_forecast("akosombo", 180, 95, 450)
    assert "dam" in forecast
    assert "spillage_probability" in forecast
    assert "risk_level" in forecast
    assert "status" in forecast
    assert "inputs" in forecast


def test_historical_validation():
    """Test historical validation against 2023 Akosombo and Bagre events."""
    validation = validate_historical_events()
    assert "events_validated" in validation
    assert "accuracy_percent" in validation
    assert validation["events_validated"] >= 3
    assert validation["accuracy_percent"] > 80
