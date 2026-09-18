"""Regression tests for src/hydrology/altimetry_thresholds.py - shared
real percentile-threshold logic used by both river gauges and (newly)
dam/upstream-proxy water levels."""

from src.hydrology.altimetry_thresholds import (
    classify_level,
    compute_relative_thresholds,
)


def _readings(elevations):
    return [{"wse": e} for e in elevations]


def test_returns_none_with_too_few_readings():
    assert compute_relative_thresholds(_readings([1.0] * 19)) is None


def test_computes_real_percentile_thresholds():
    elevations = list(range(100))  # 0..99, simple, verifiable percentiles
    thresholds = compute_relative_thresholds(_readings(elevations))
    assert thresholds is not None
    assert thresholds["baseline_m"] == 5.0  # 5th percentile of 0..99
    assert thresholds["warning_level_m"] == 70.0  # 75th percentile (75) - baseline (5)
    assert thresholds["danger_level_m"] == 85.0  # 90th percentile (90) - baseline (5)
    assert thresholds["flood_stage_m"] == 90.0  # 95th percentile (95) - baseline (5)


def test_ignores_readings_with_no_wse():
    elevations = list(range(100))
    readings = _readings(elevations) + [{"wse": None}, {}]
    assert compute_relative_thresholds(readings) == compute_relative_thresholds(
        _readings(elevations)
    )


def test_classify_level_bands():
    thresholds = {
        "baseline_m": 100.0,
        "warning_level_m": 5.0,
        "danger_level_m": 10.0,
        "flood_stage_m": 15.0,
    }
    assert classify_level(102.0, thresholds)["status"] == "NORMAL"
    assert classify_level(106.0, thresholds)["status"] == "WARNING"
    assert classify_level(111.0, thresholds)["status"] == "DANGER"
    assert classify_level(120.0, thresholds)["status"] == "FLOOD"


def test_classify_level_computes_real_level_above_baseline():
    thresholds = {
        "baseline_m": 50.0,
        "warning_level_m": 5.0,
        "danger_level_m": 10.0,
        "flood_stage_m": 15.0,
    }
    result = classify_level(53.5, thresholds)
    assert result["level_above_baseline_m"] == 3.5
