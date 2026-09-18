"""Regression tests for src/models/rare_event_verification.py's pure
logic (contingency tables, SEDI/EDI, episode counting, percentile
thresholds, bootstrap CI) using synthetic data - Earth Engine isn't
available in this test environment, so the real full-record fetch
itself is exercised only for graceful degradation."""

from datetime import date
from unittest.mock import patch

from src.models.rare_event_verification import (
    _bootstrap_sedi_ci,
    _flag_days_raw_mm,
    _label_flood_days,
    compute_edi,
    compute_sedi,
    contingency_table,
    count_warning_episodes,
    percentile_threshold_mm,
    run_district_verification,
    run_full_verification,
)


def test_contingency_table_counts_all_four_categories():
    flags = [True, True, False, False]
    labels = [True, False, True, False]
    table = contingency_table(flags, labels)
    assert table == {
        "hits": 1,
        "false_alarms": 1,
        "misses": 1,
        "correct_negatives": 1,
    }


def test_sedi_is_high_for_a_near_perfect_discriminator():
    # 95 hits out of 100 positives, only 2 false alarms out of 900 negatives
    sedi = compute_sedi(hits=95, misses=5, false_alarms=2, correct_negatives=898)
    assert sedi is not None
    assert sedi > 0.8


def test_sedi_is_near_zero_for_a_threshold_crossed_regardless_of_outcome():
    """The exact failure mode this module exists to catch: a threshold
    that fires on almost every positive AND almost every negative day
    has no real discriminative skill, even though POD alone would read
    as near-perfect."""
    hits, misses = 99, 1  # naive POD = 0.99, looks like a great result
    false_alarms, correct_negatives = 880, 20  # but fires on ~98% of negative days too
    sedi = compute_sedi(hits, misses, false_alarms, correct_negatives)
    naive_pod = hits / (hits + misses)
    assert naive_pod == 0.99
    assert sedi is not None
    assert sedi < 0.3  # SEDI correctly reports this as low real skill


def test_sedi_handles_zero_false_alarms_without_crashing():
    sedi = compute_sedi(hits=5, misses=0, false_alarms=0, correct_negatives=100)
    assert sedi is not None
    assert -1.0 <= sedi <= 1.0


def test_sedi_none_when_no_positives_or_no_negatives():
    assert compute_sedi(hits=0, misses=0, false_alarms=5, correct_negatives=10) is None
    assert compute_sedi(hits=5, misses=2, false_alarms=0, correct_negatives=0) is None


def test_edi_and_sedi_agree_on_direction():
    good_edi = compute_edi(hits=95, misses=5, false_alarms=2, correct_negatives=898)
    bad_edi = compute_edi(hits=99, misses=1, false_alarms=880, correct_negatives=20)
    assert good_edi is not None and bad_edi is not None
    assert good_edi > bad_edi


def test_count_warning_episodes_collapses_consecutive_runs():
    # 5-day rain spell should be one episode, not five
    dates = [f"2020-01-{d:02d}" for d in range(1, 11)]
    flags = [False, True, True, True, True, True, False, False, True, False]
    assert count_warning_episodes(dates, flags) == 2


def test_count_warning_episodes_zero_when_never_flagged():
    dates = [f"2020-01-{d:02d}" for d in range(1, 4)]
    assert count_warning_episodes(dates, [False, False, False]) == 0


def test_percentile_threshold_mm_matches_manual_sort():
    values = [0.0, 1.0, 2.0, 10.0, 50.0]
    # 80th percentile of 5 sorted values -> index round(0.8*4)=3 -> 10.0
    assert percentile_threshold_mm(values, 80) == 10.0


def test_percentile_threshold_mm_empty_series():
    assert percentile_threshold_mm([], 95) == 0.0


def test_flag_days_raw_mm_uses_raw_value_not_calculate_score():
    values = [5.0, 9.9, 10.0, 25.0]
    flags = _flag_days_raw_mm(values, 10.0)
    assert flags == [False, False, True, True]


def test_label_flood_days_marks_window_before_event_only():
    dates = [f"2020-01-{d:02d}" for d in range(1, 15)]
    event_dates = [date(2020, 1, 10)]
    labels = _label_flood_days(dates, event_dates)
    # 7-day window before and including Jan 10 -> Jan 3 through Jan 10
    labeled_days = [d for d, l in zip(dates, labels) if l]
    assert labeled_days == [f"2020-01-{d:02d}" for d in range(3, 11)]


def test_bootstrap_ci_returns_none_for_too_short_series():
    assert _bootstrap_sedi_ci([True] * 10, [True] * 10) is None


def test_bootstrap_ci_returns_ordered_bounds_for_long_series():
    import random

    rng = random.Random(1)
    n = 400
    labels = [rng.random() < 0.05 for _ in range(n)]
    flags = [label if rng.random() < 0.8 else rng.random() < 0.1 for label in labels]
    ci = _bootstrap_sedi_ci(flags, labels)
    assert ci is not None
    lo, hi = ci
    assert lo <= hi
    assert -1.0 <= lo <= 1.0
    assert -1.0 <= hi <= 1.0


def test_run_district_verification_unknown_district_honestly_reported():
    result = run_district_verification("North Tongu")
    assert result["available"] is False
    assert "not one of the 9 districts" in result["reason"]


def test_run_district_verification_no_events_honestly_reported():
    result = run_district_verification("Kumasi")
    assert result["available"] is False
    assert "No documented" in result["reason"]


def test_run_district_verification_graceful_when_ee_unavailable():
    with patch(
        "src.models.rare_event_verification.fetch_historical_chirps_series",
        return_value=[],
    ):
        result = run_district_verification("Tamale")
    assert result["available"] is False
    assert "Earth Engine unavailable" in result["reason"]


def test_run_full_verification_never_crashes_with_no_real_data(monkeypatch):
    monkeypatch.setattr(
        "src.models.rare_event_verification.fetch_historical_chirps_series",
        lambda *a, **k: [],
    )
    report = run_full_verification()
    assert "districts" in report
    assert "methodology" in report
    assert all(not d["available"] for d in report["districts"].values())
