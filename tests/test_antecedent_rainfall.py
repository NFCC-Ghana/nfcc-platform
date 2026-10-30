"""Regression tests for src/hydrology/antecedent_rainfall.py - the live
production wiring of the real 3-day rolling accumulation signal that
src/models/rare_event_verification.py validated against 36.7 years of
real CHIRPS data. Earth Engine isn't available in this test
environment, so the real fetch itself is exercised only for graceful
degradation; the "most recent 3 real days" selection logic is tested
with a synthetic series."""

from unittest.mock import patch

import pytest

from src.hydrology.antecedent_rainfall import get_antecedent_rainfall
from src.hydrology.antecedent_rainfall import fetch_imerg_daily_series as _real_imerg


@pytest.fixture(autouse=True)
def _no_imerg():
    """IMERG is the primary source; these tests exercise the CHIRPS v3
    fallback, so IMERG returns nothing (and never reaches Earth Engine)."""
    with patch(
        "src.hydrology.antecedent_rainfall.fetch_imerg_daily_series",
        return_value=([], 1.0),
    ):
        yield


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
    assert isinstance(result["stale"], bool)


def test_marks_result_stale_when_freshest_data_is_old():
    from datetime import date, timedelta

    old_date = (date.today() - timedelta(days=25)).isoformat()
    series = [{"date": old_date, "precipitation_mm": 5.0}]
    with patch(
        "src.hydrology.antecedent_rainfall.fetch_historical_chirps_series",
        return_value=series,
    ):
        result = get_antecedent_rainfall("Tamale")
    assert result["available"] is True
    assert result["stale"] is True


def test_not_stale_when_freshest_data_is_recent():
    from datetime import date, timedelta

    recent_date = (date.today() - timedelta(days=2)).isoformat()
    series = [{"date": recent_date, "precipitation_mm": 5.0}]
    with patch(
        "src.hydrology.antecedent_rainfall.fetch_historical_chirps_series",
        return_value=series,
    ):
        result = get_antecedent_rainfall("Tamale")
    assert result["available"] is True
    assert result["stale"] is False


def test_imerg_is_primary_and_reported_as_the_source():
    """CHIRPS in Earth Engine ran a month behind (ended 2026-09-30 when
    checked on 2026-10-30); IMERG is about 2 days behind."""
    from datetime import date, timedelta

    recent = [
        {"date": (date.today() - timedelta(days=k)).isoformat(), "precipitation_mm": mm}
        for k, mm in ((4, 1.0), (3, 2.0), (2, 4.0))
    ]
    with (
        patch(
            "src.hydrology.antecedent_rainfall.fetch_imerg_daily_series",
            return_value=(recent, 1.2),
        ),
        patch(
            "src.hydrology.antecedent_rainfall.fetch_historical_chirps_series"
        ) as chirps,
    ):
        result = get_antecedent_rainfall("Tamale")
    chirps.assert_not_called()
    assert result["source"] == "imerg_v07_scaled_to_chirps"
    assert result["rolling_3d_mm"] == 7.0
    assert result["imerg_to_chirps_scale"] == 1.2
    assert result["stale"] is False


def test_falls_back_to_chirps_when_imerg_is_unavailable():
    series = [{"date": "2026-09-12", "precipitation_mm": 5.0}]
    with patch(
        "src.hydrology.antecedent_rainfall.fetch_historical_chirps_series",
        return_value=series,
    ):
        result = get_antecedent_rainfall("Tamale")
    assert result["source"] == "chirps_v3_daily_sat"
    assert result["imerg_to_chirps_scale"] == 1.0


def test_imerg_series_keeps_only_complete_days_and_applies_the_scale():
    """A day still being processed (fewer than 48 half-hourly images)
    must not read as a dry day."""
    from src.hydrology import antecedent_rainfall as ar

    payload = {
        "days": [
            {"date": "2026-10-26", "n": 48, "mm": 10.0},
            {"date": "2026-10-27", "n": 48, "mm": 0.0},
            {"date": "2026-10-28", "n": 20, "mm": 1.0},  # incomplete
            {"date": "2026-10-29", "n": 0, "mm": None},  # not published yet
        ],
    }

    class _Dict:
        def __init__(self, *a, **k):
            pass

        def getInfo(self):
            return payload

    with (
        patch.object(ar, "initialize_earth_engine", return_value=True),
        patch.object(ar, "_imerg_to_chirps_scale", return_value=1.2),
        patch("ee.Dictionary", _Dict),
        patch("ee.Geometry.Point"),
        patch("ee.ImageCollection"),
        patch("ee.List"),
    ):
        series, scale = _real_imerg(9.4, -0.84)  # the autouse fixture stubs ar's copy
    assert scale == 1.2
    assert series == [
        {"date": "2026-10-26", "precipitation_mm": 12.0},
        {"date": "2026-10-27", "precipitation_mm": 0.0},
    ]
