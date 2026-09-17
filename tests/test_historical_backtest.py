"""Regression tests for src/models/historical_backtest.py's pure logic
(rolling sums, threshold-crossing detection, aggregation) using
synthetic rainfall series - Earth Engine isn't available in this test
environment (no local GEE credentials, confirmed earlier this session),
so the real-data fetch itself (fetch_historical_chirps_series) is tested
separately for graceful degradation only, not for real results."""

from datetime import date
from unittest.mock import patch

from src.alerts.formatter import calculate_score
from src.models.historical_backtest import (
    _ALERT_THRESHOLD,
    _first_threshold_crossing,
    _rolling_3d_sums,
    backtest_event,
    fetch_historical_chirps_series,
    run_full_backtest,
)


def test_rolling_3d_sums_matches_manual_calculation():
    series = [
        {"date": "2020-01-01", "precipitation_mm": 10.0},
        {"date": "2020-01-02", "precipitation_mm": 5.0},
        {"date": "2020-01-03", "precipitation_mm": 20.0},
        {"date": "2020-01-04", "precipitation_mm": 0.0},
    ]
    sums = _rolling_3d_sums(series)
    assert sums[0] == 10.0  # only 1 day available
    assert sums[1] == 15.0  # 10 + 5
    assert sums[2] == 35.0  # 10 + 5 + 20
    assert sums[3] == 25.0  # 5 + 20 + 0


def test_first_threshold_crossing_finds_correct_day():
    dates = ["2020-01-01", "2020-01-02", "2020-01-03"]
    values = [1.0, 2.0, 90.0]  # only day 3 crosses the real alert threshold
    result = _first_threshold_crossing(values, dates, date(2020, 1, 5))
    assert result is not None
    assert result["date"] == "2020-01-03"
    assert result["score"] == calculate_score(90.0)
    assert result["score"] >= _ALERT_THRESHOLD
    assert result["lead_time_days"] == 2  # Jan 5 - Jan 3


def test_first_threshold_crossing_none_when_never_crossed():
    dates = ["2020-01-01", "2020-01-02"]
    values = [0.0, 1.0]
    result = _first_threshold_crossing(values, dates, date(2020, 1, 5))
    assert result is None


def test_rolling_3d_detects_earlier_than_same_day():
    """The whole point of testing a temporal feature: real accumulating
    rainfall, each single day below calculate_score()'s own threshold
    (any single day >=10mm alone already scores >=30 - confirmed by
    calculate_score(10) == 30 - so daily values must all stay under
    10mm for this to test anything real), should let rolling_3d detect
    a crossing that same-day scoring misses entirely."""
    dates = [f"2020-01-{d:02d}" for d in range(1, 6)]
    daily = [4.0, 4.0, 4.0, 0.0, 0.0]  # each day alone: calculate_score(4) == 12
    same_day = _first_threshold_crossing(daily, dates, date(2020, 1, 10))
    rolling = _first_threshold_crossing(_rolling_3d_sums(
        [{"date": d, "precipitation_mm": v} for d, v in zip(dates, daily)]
    ), dates, date(2020, 1, 10))
    assert same_day is None
    assert rolling is not None
    assert rolling["date"] == "2020-01-03"  # 4+4+4=12mm rolling sum, score 34


def test_fetch_historical_chirps_returns_empty_list_when_ee_unavailable():
    """Graceful degradation, not a crash, when Earth Engine isn't
    reachable - matches every other real data source in this codebase."""
    with patch(
        "src.models.historical_backtest.initialize_earth_engine",
        return_value=False,
    ):
        result = fetch_historical_chirps_series(9.4, -0.84, "2015-05-01", "2015-06-05")
    assert result == []


def test_backtest_event_reports_unavailable_when_no_real_data():
    with patch(
        "src.models.historical_backtest.fetch_historical_chirps_series",
        return_value=[],
    ):
        result = backtest_event(
            {
                "event_id": "test_event",
                "date": "2015-06-03",
                "districts": ["Accra Central"],
            }
        )
    assert result["available"] is False
    assert "reason" in result


def test_backtest_event_unknown_district_honestly_reported():
    result = backtest_event(
        {"event_id": "x", "date": "2007-09-01", "districts": ["North Tongu"]}
    )
    assert result["available"] is False


def test_run_full_backtest_never_crashes_with_no_real_data(monkeypatch):
    """With Earth Engine unavailable (this test environment), every
    event should honestly report unavailable rather than the whole
    backtest crashing."""
    monkeypatch.setattr(
        "src.models.historical_backtest.initialize_earth_engine", lambda: False
    )
    report = run_full_backtest()
    assert "events" in report
    assert "aggregate" in report
    assert "limitations" in report
    assert all(not e["available"] for e in report["events"])
    assert report["aggregate"]["same_day"]["events_evaluated"] == 0


def test_backtest_never_reports_far_or_csi():
    """The module docstring is explicit that FAR/CSI cannot be honestly
    computed from this incomplete historical record - this must never
    silently appear in the report."""
    report = run_full_backtest()
    assert "false_alarm_ratio" not in report["aggregate"]["same_day"]
    assert "csi" not in report["aggregate"]["same_day"]
