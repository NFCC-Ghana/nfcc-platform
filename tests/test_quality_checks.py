"""Regression tests for src/data_quality/quality_checks.py - the real
QARTOD (IOOS/NOAA real-time data quality standard) test implementations
used to grade every real source this platform ingests."""

from datetime import datetime, timedelta

from src.data_quality.quality_checks import (
    QCFlag,
    aggregate_quality,
    completeness_percent,
    flat_line_test,
    freshness_test,
    gross_range_test,
    rate_of_change_test,
    spike_test,
)


def test_gross_range_pass_and_fail():
    assert gross_range_test(50.0, 0, 100).flag == QCFlag.PASS
    assert gross_range_test(150.0, 0, 100).flag == QCFlag.FAIL
    assert gross_range_test(None, 0, 100).flag == QCFlag.MISSING


def test_spike_test_detects_real_spike():
    # 10, 90, 12 - a real spike in the middle
    result = spike_test(value=90.0, previous=10.0, following=12.0, threshold=20.0)
    assert result.flag == QCFlag.SUSPECT


def test_spike_test_passes_smooth_transition():
    result = spike_test(value=15.0, previous=10.0, following=20.0, threshold=20.0)
    assert result.flag == QCFlag.PASS


def test_spike_test_not_evaluated_without_neighbors():
    assert spike_test(10.0, None, 12.0, 20.0).flag == QCFlag.NOT_EVALUATED


def test_rate_of_change_flags_implausible_jump():
    # 100mm change in 1 hour - implausible for most sources
    result = rate_of_change_test(150.0, 50.0, hours_elapsed=1.0, max_rate_per_hour=10.0)
    assert result.flag == QCFlag.SUSPECT


def test_rate_of_change_passes_plausible_change():
    result = rate_of_change_test(55.0, 50.0, hours_elapsed=1.0, max_rate_per_hour=10.0)
    assert result.flag == QCFlag.PASS


def test_flat_line_detects_stuck_sensor():
    values = [10.0, 10.001, 10.0005, 9.999, 10.0002]
    result = flat_line_test(values, tolerance=0.01, min_repeats=5)
    assert result.flag == QCFlag.SUSPECT


def test_flat_line_passes_real_variation():
    values = [10.0, 15.0, 8.0, 20.0, 5.0]
    result = flat_line_test(values, tolerance=0.01, min_repeats=5)
    assert result.flag == QCFlag.PASS


def test_flat_line_not_evaluated_with_too_little_history():
    assert flat_line_test([10.0, 10.0], tolerance=0.01, min_repeats=5).flag == QCFlag.NOT_EVALUATED


def test_freshness_pass_and_fail():
    now = datetime(2026, 1, 10, 12, 0, 0)
    fresh = now - timedelta(hours=2)
    stale = now - timedelta(hours=100)
    assert freshness_test(fresh, now, max_age_hours=24).flag == QCFlag.PASS
    assert freshness_test(stale, now, max_age_hours=24).flag == QCFlag.FAIL
    assert freshness_test(None, now, max_age_hours=24).flag == QCFlag.MISSING


def test_freshness_flags_future_timestamp_as_suspect():
    now = datetime(2026, 1, 10, 12, 0, 0)
    future = now + timedelta(hours=5)
    assert freshness_test(future, now, max_age_hours=24).flag == QCFlag.SUSPECT


def test_completeness_percent():
    assert completeness_percent(3, 3) == 100.0
    assert completeness_percent(3, 1) == 33.3
    assert completeness_percent(3, 0) == 0.0
    assert completeness_percent(0, 5) == 100.0  # nothing expected -> trivially complete


def test_aggregate_worst_flag_wins_not_diluted_by_passes():
    """The core QARTOD aggregation principle: one real FAIL must not be
    averaged away by several PASS results."""
    tests = [
        gross_range_test(50.0, 0, 100),  # PASS
        freshness_test(None, datetime.utcnow(), 24),  # MISSING
        rate_of_change_test(999.0, 1.0, 1.0, 10.0),  # SUSPECT
    ]
    report = aggregate_quality("test_source", tests)
    assert report.overall == QCFlag.SUSPECT  # SUSPECT outranks MISSING/PASS present


def test_aggregate_fail_always_wins():
    tests = [
        gross_range_test(50.0, 0, 100),  # PASS
        gross_range_test(500.0, 0, 100),  # FAIL
        rate_of_change_test(5.0, 4.0, 1.0, 10.0),  # PASS
    ]
    report = aggregate_quality("test_source", tests)
    assert report.overall == QCFlag.FAIL


def test_aggregate_empty_tests_not_evaluated():
    report = aggregate_quality("test_source", [])
    assert report.overall == QCFlag.NOT_EVALUATED


def test_qartod_numeric_codes_match_standard():
    """QARTOD's own numeric flag convention: 1=pass, 2=not_evaluated,
    3=suspect, 4=fail, 9=missing - kept so this can round-trip with the
    real standard, not an incompatible ad hoc scheme."""
    assert gross_range_test(50.0, 0, 100).qartod_code == 1
    assert gross_range_test(500.0, 0, 100).qartod_code == 4
    assert gross_range_test(None, 0, 100).qartod_code == 9
