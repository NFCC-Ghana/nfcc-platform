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

    def test_label_argument_selects_the_flood_record(self):
        panel = _panel([0] * 10).assign(flood_news=[0] * 6 + [1] + [0] * 3)
        assert build_features(panel, "news")["onset"].sum() == 1
        assert build_features(panel.drop(columns="flood_news"))["onset"].sum() == 0

    def test_forecast_inputs_are_lagged(self):
        panel = _panel([0] * 10).assign(q_week_max=np.arange(10, dtype=float))
        df = build_features(panel)
        assert (df["q_week_max_log_lag1"] == np.log1p(df["q_week_max"] - 1)).all()


class TestTolerantScores:
    def test_one_week_early_alert_is_a_hit_not_a_false_alarm(self):
        weeks = pd.date_range("2020-01-06", periods=6, freq="7D")
        y = [0, 0, 0, 1, 0, 0]
        alert = [0, 0, 1, 0, 0, 0]
        out = M.tolerant([1] * 6, weeks, y, alert)
        assert out == {"tol_pod": 1.0, "tol_far": 0.0}
        strict = M.categorical(y, alert)
        assert strict["recall_pod"] == 0.0 and strict["false_alarm_ratio"] == 1.0

    def test_alert_in_another_district_does_not_count(self):
        weeks = pd.date_range("2020-01-06", periods=2, freq="7D")
        out = M.tolerant([1, 2], weeks, [1, 0], [0, 1])
        assert out == {"tol_pod": 0.0, "tol_far": 1.0}


class TestModels:
    def test_river_percentile_ranks_within_each_district(self):
        from research.flood_experiments.models import RiverPercentile

        train = pd.DataFrame(
            {
                "district_code": [1] * 4 + [2] * 4,
                "q_week_max": [1, 2, 3, 4, 10, 20, 30, 40],
            }
        )
        test = pd.DataFrame({"district_code": [1, 2, 3], "q_week_max": [4, 15, 5]})
        p = RiverPercentile().fit(train).predict(test)
        assert p.tolist() == [1.0, 0.25, 0.0]

    def test_xgb_is_monotone_in_rainfall(self):
        from research.flood_experiments.models import XGB

        rng = np.random.default_rng(0)
        n = 3000
        df = pd.DataFrame(
            {"rain_week_sum": rng.gamma(2, 20, n), "elev_mean": rng.normal(100, 30, n)}
        )
        df["onset"] = (rng.random(n) < 0.02 + 0.002 * df["rain_week_sum"]).astype(int)
        m = XGB(["rain_week_sum", "elev_mean"]).fit(df, df)
        grid = pd.DataFrame(
            {"rain_week_sum": np.linspace(0, 200, 50), "elev_mean": 100.0}
        )
        assert np.all(np.diff(m.predict(grid)) >= -1e-9)


class TestSarAudit:
    def test_controls_are_matched_and_never_flooded(self):
        from research.flood_experiments.sar_labels import audit_sample

        weeks = pd.date_range("2016-01-04", periods=160, freq="7D")
        rows = []
        for code in (1, 2, 3):
            for k, w in enumerate(weeks):
                rows.append((code, w.strftime("%Y-%m-%d"), int(code == 1 and k == 80)))
        panel = pd.DataFrame(rows, columns=["district_code", "week", "flood_news"])
        panel = panel.assign(
            region="R",
            rain_week_sum=1.0,
            rain_week_max=1.0,
            sm_week_mean=0.3,
            runoff_week_sum=0.1,
            q_week_max=10.0,
            population=1e3,
            area_km2=10.0,
        )
        s = audit_sample(panel)
        onset = s[s.kind == "onset"].iloc[0]
        same_week = s[s.kind == "control_same_week"].iloc[0]
        same_place = s[s.kind == "control_same_place"].iloc[0]
        assert (onset.district_code, onset.week) == (1, weeks[80].strftime("%Y-%m-%d"))
        assert same_week.week == onset.week and same_week.district_code != 1
        assert same_place.district_code == 1 and same_place.week != onset.week
        assert pd.Timestamp(same_place.week).weekday() == 0


class TestNadmoMatching:
    def test_matches_exact_suffix_stripped_and_reports_unmatched(
        self, tmp_path, monkeypatch
    ):
        from research.flood_experiments import config as C
        from research.flood_experiments import nadmo

        monkeypatch.setattr(C, "DATA_DIR", tmp_path)
        (tmp_path / "raw").mkdir()
        pd.DataFrame(
            {
                "date": ["2022-06-01"] * 3,
                "district": ["Keta Municipal", "Keta", "Nowhere"],
                "region": ["Volta"] * 3,
                "deaths": [0, 1, 0],
                "affected": [100, 50, 10],
                "houses_damaged": [5, 2, 0],
            }
        ).to_csv(tmp_path / "raw" / "nadmo_incidents.csv", index=False)
        static = pd.DataFrame(
            {"district": ["Keta Municipal"], "region": ["Volta"], "district_code": [7]}
        )
        out = nadmo.load_incidents(static)
        assert out["district_code"].tolist() == [7, 7]
        assert (tmp_path / "raw" / "nadmo_unmatched.csv").exists()


class TestWhenNotWhere:
    def test_within_district_auc_ignores_which_district_floods_more(self):
        # district 1 floods often and always scores high; within each
        # district the scores are random, so timing skill is 0.5
        rng = np.random.default_rng(0)
        d = np.repeat([1, 2], 500)
        y = np.concatenate([rng.random(500) < 0.2, rng.random(500) < 0.02]).astype(int)
        p = np.where(d == 1, 0.9, 0.1) + rng.normal(0, 0.01, 1000)
        assert M.probabilistic(y, p)["roc_auc"] > 0.7  # pooled: rewards "where"
        assert M.within_district_auc(d, y, p) == pytest.approx(0.5, abs=0.1)

    def test_relative_value_is_one_for_perfect_and_zero_for_useless(self):
        y = np.array([0] * 90 + [1] * 10)
        perfect = M.relative_value(y, y.astype(float), alphas=np.array([0.05, 0.3]))
        assert perfect["value"] == pytest.approx([1.0, 1.0])
        noise = M.relative_value(y, np.full(100, 0.5), alphas=np.array([0.05, 0.3]))
        assert max(noise["value"]) <= 1e-9


class TestForecastArchive:
    def test_day_k_of_the_week_uses_the_forecast_issued_k_plus_1_days_earlier(self):
        from research.flood_experiments.forecast_archive import weekly_forecast

        t = pd.date_range("2024-01-01", periods=7 * 24, freq="h")  # Mon-Sun
        hourly = {"time": t.strftime("%Y-%m-%dT%H:%M").tolist()}
        for n in range(1, 8):
            # lead n forecasts 1 mm/h on day n-1 only, 0 elsewhere
            hourly[f"precipitation_previous_day{n}"] = [
                1.0 if ts.dayofweek == n - 1 else 0.0 for ts in t
            ]
        w = weekly_forecast(hourly)
        assert w["fc_rain_week_sum"].tolist() == [7 * 24.0]
        assert w["fc_rain_week_max"].tolist() == [24.0]

    def test_with_sparse_leads_each_day_uses_the_shortest_lead_issued_before_the_week(
        self,
    ):
        from research.flood_experiments.forecast_archive import weekly_forecast

        t = pd.date_range("2024-01-01", periods=7 * 24, freq="h")
        hourly = {"time": t.strftime("%Y-%m-%dT%H:%M").tolist()}
        for n in (2, 4, 6, 7):  # each lead forecasts n mm/h everywhere
            hourly[f"precipitation_previous_day{n}"] = [float(n)] * len(t)
        w = weekly_forecast(hourly)
        # days 0-1 lead 2, days 2-3 lead 4, days 4-5 lead 6, day 6 lead 7
        assert w["fc_rain_week_sum"].iloc[0] == 24 * (2 + 2 + 4 + 4 + 6 + 6 + 7)


class TestLocalClimate:
    def test_percentile_is_relative_to_each_districts_own_record(self):
        from research.flood_experiments.features import local_percentile

        clim = {"rain_week_sum": {1: np.arange(0, 100.0), 2: np.arange(0, 10.0)}}
        df = pd.DataFrame({"district_code": [1, 2], "rain_week_sum": [40.0, 40.0]})
        pct = local_percentile(df, "rain_week_sum", clim)
        assert pct[0] == pytest.approx(0.41)  # ordinary for district 1
        assert pct[1] == 1.0  # beyond anything district 2 has seen

    def test_operational_inputs_are_all_known_when_the_week_starts(self):
        from research.flood_experiments.models import OPERATIONAL

        same_week_observed = {
            "sm_week_mean",
            "runoff_week_sum",
            "q_week_max_log",
            "q_ratio",
        }
        assert not same_week_observed & set(OPERATIONAL)


class TestShadowRunResilience:
    """The first scheduled shadow run crashed on one GloFAS timeout."""

    def test_discharge_timeout_becomes_missing_not_a_crash(self, monkeypatch):
        import requests

        from research.flood_experiments import operational as ops

        monkeypatch.setattr(ops.time, "sleep", lambda s: None)
        monkeypatch.setattr(
            ops.requests,
            "get",
            lambda *a, **k: (_ for _ in ()).throw(requests.ReadTimeout()),
        )
        from datetime import date

        assert math.isnan(ops._discharge_lag1(6.0, 0.6, date(2026, 11, 2)))

    def test_retries_recover_from_a_temporary_failure(self, monkeypatch):
        import requests

        from research.flood_experiments import operational as ops

        monkeypatch.setattr(ops.time, "sleep", lambda s: None)
        calls = []

        class _Ok:
            status_code = 200

            def json(self):
                return {"daily": {"river_discharge": [1.0, 5.0, None]}}

        def flaky(*a, **k):
            calls.append(1)
            if len(calls) < 3:
                raise requests.ConnectionError()
            return _Ok()

        monkeypatch.setattr(ops.requests, "get", flaky)
        from datetime import date

        assert ops._discharge_lag1(6.0, 0.6, date(2026, 11, 2)) == 5.0
        assert len(calls) == 3
