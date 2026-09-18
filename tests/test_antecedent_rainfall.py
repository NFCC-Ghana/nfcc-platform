"""Regression tests for src/hydrology/antecedent_rainfall.py - the live
production wiring of the real 3-day rolling accumulation signal that
src/models/rare_event_verification.py validated against 36.7 years of
real CHIRPS data. Earth Engine isn't available in this test
environment, so the real fetch itself is exercised only for graceful
degradation; the "most recent 3 real days" selection logic is tested
with a synthetic series."""

from unittest.mock import patch

from src.hydrology.antecedent_rainfall import get_antecedent_rainfall


def test_unknown_district_honestly_reported():
    result = get_antecedent_rainfall("Not A Real District")
    assert result["available"] is False
    assert "not one of the 9 districts" in result["reason"]


def test_graceful_when_ee_unavailable():
    with patch(
        "src.hydrology.antecedent_rainfall.fetch_historical_chirps_series",
        return_value=[],
    ):
        result = get_antecedent_rainfall("Tamale")
    assert result["available"] is False
    assert "Earth Engine unavailable" in result["reason"]


def test_uses_near_real_time_collection_not_the_delayed_final_product():
    """Real production bug this guards against: UCSB-CHG/CHIRPS/DAILY
    (the gauge-corrected 'Final' product used for backtesting) has real
    publication latency of weeks to months and returned zero images
    ('No bands in collection') when queried for the last 14 days in
    production. This live signal must use the near-real-time collection
    instead, or it can never return a value at all."""
    with patch(
        "src.hydrology.antecedent_rainfall.fetch_historical_chirps_series",
        return_value=[],
    ) as mock_fetch:
        get_antecedent_rainfall("Tamale")
    _, kwargs = mock_fetch.call_args
    assert kwargs["collection_id"] == "UCSB-CHC/CHIRPS/V3/DAILY_SAT"


def test_uses_most_recent_three_real_days_even_with_a_data_gap():
    """CHIRPS publication latency means the freshest 1-3 calendar days
    might not exist yet - this must use whichever 3 real days it
    actually got (the tail of the series), not assume today/yesterday
    are present."""
    series = [
        {"date": "2026-09-01", "precipitation_mm": 100.0},  # should be ignored
        {"date": "2026-09-10", "precipitation_mm": 5.0},
        {"date": "2026-09-11", "precipitation_mm": 10.0},
        {"date": "2026-09-12", "precipitation_mm": 15.0},
    ]
    with patch(
        "src.hydrology.antecedent_rainfall.fetch_historical_chirps_series",
        return_value=series,
    ):
        result = get_antecedent_rainfall("Tamale")
    assert result["available"] is True
    assert result["rolling_3d_mm"] == 30.0  # 5 + 10 + 15, NOT including the 100.0
    assert result["days_used"] == ["2026-09-10", "2026-09-11", "2026-09-12"]
    assert result["freshest_date"] == "2026-09-12"
    assert isinstance(result["data_age_days"], int)
