"""Tests for the research experiment framework (metrics, onset target).

Skipped when the research extras (requirements-research.txt) aren't
installed - the main CI installs only the API's dependencies.
"""

import math

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")

from research.flood_experiments import metrics as M  # noqa: E402
from research.flood_experiments.features import build_features  # noqa: E402


class TestCategorical:
    def test_contingency_counts(self):
        y = [1, 1, 0, 0, 0]
        yhat = [1, 0, 1, 0, 0]
        assert M.contingency(y, yhat) == {
            "hits": 1,
            "misses": 1,
            "false_alarms": 1,
            "correct_negatives": 2,
        }

    def test_scores_from_known_table(self):
        out = M.categorical([1, 1, 0, 0, 0], [1, 0, 1, 0, 0])
        assert out["precision"] == 0.5
        assert out["recall_pod"] == 0.5
        assert out["f1"] == 0.5
        assert out["false_alarm_ratio"] == 0.5
        assert out["missed_event_rate"] == 0.5

    def test_sedi_matches_ferro_stephenson_formula(self):
        h, f = 0.6, 0.1
        expected = (math.log(f) - math.log(h) - math.log(1 - f) + math.log(1 - h)) / (
            math.log(f) + math.log(h) + math.log(1 - f) + math.log(1 - h)
        )
        assert M.sedi(60, 40, 10, 90) == pytest.approx(expected)

    def test_sedi_is_zero_for_random_forecast(self):
        # hit rate == false-alarm rate is no skill
        assert M.sedi(10, 90, 10, 90) == pytest.approx(0.0, abs=1e-9)

    def test_sedi_undefined_without_events(self):
        assert math.isnan(M.sedi(0, 0, 3, 10))


class TestProbabilistic:
    def test_perfect_ranking(self):
        out = M.probabilistic([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])
        assert out["roc_auc"] == 1.0
        assert out["pr_auc"] == 1.0

    def test_calibrated_constant_has_zero_ece(self):
        y = np.tile([1] + [0] * 9, 10)
        assert M.reliability(y, np.full(100, 0.1))["ece"] == pytest.approx(0.0)

    def test_threshold_chosen_on_validation_separates_classes(self):
        y = np.array([0] * 95 + [1] * 5)
        p = np.concatenate([np.linspace(0, 0.3, 95), np.linspace(0.7, 0.9, 5)])
        t = M.best_f1_threshold(y, p)
        assert M.categorical(y, p >= t)["f1"] == 1.0

    def test_block_bootstrap_interval_brackets_point_estimate(self):
        rng = np.random.default_rng(0)
        y = rng.random(2000) < 0.05
        p = np.where(y, 0.6, 0.2) + rng.normal(0, 0.15, 2000)
        years = np.repeat(np.arange(2000, 2020), 100)
        point = M.probabilistic(y, p)["roc_auc"]
        lo, hi = M.block_bootstrap_ci(
            y, p, years, lambda a, b: M.probabilistic(a, b)["roc_auc"], n_boot=100
        )
        assert lo <= point <= hi


def _panel(flood):
    n = len(flood)
    return pd.DataFrame(
        {
            "district_code": 1,
            "region": "R",
            "week": pd.date_range("2005-01-03", periods=n, freq="7D").astype(str),
            "rain_week_sum": np.arange(n, dtype=float),
            "rain_week_max": 1.0,
            "sm_week_mean": 0.3,
            "runoff_week_sum": 0.1,
            "q_week_max": 10.0,
            "population": 1000.0,
            "area_km2": 10.0,
            "flood": flood,
        }
    )


class TestOnsetTarget:
    def test_onset_marks_first_flooded_week_and_drops_weeks_after_a_flood(self):
        flood = [0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0]
        df = build_features(_panel(flood))
        # weeks 0-3 lack lags; weeks 6, 7, 8 and 11 follow a flooded week,
        # so they can't be onsets and are not scored
        assert df["week"].dt.strftime("%m-%d").tolist() == [
            "01-31",
            "02-07",
            "03-07",
            "03-14",
        ]
        assert df["onset"].tolist() == [0, 1, 0, 1]

    def test_lags_come_from_earlier_weeks_only(self):
        df = build_features(_panel([0] * 10))
        first = df.iloc[0]
        assert first["rain_week_sum"] == 4.0
        assert first["rain_lag1"] == 3.0
        assert first["rain_prev4w_sum"] == 3.0 + 2.0 + 1.0 + 0.0
