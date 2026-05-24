"""Unit tests — Feature engineering pipeline using sample_dataframe fixture."""

import pandas as pd


class TestFeatureEngineering:
    def test_dataframe_has_required_columns(self, sample_dataframe):
        required = [
            "precipitation",
            "roll_3d",
            "roll_7d",
            "roll_30d",
            "cumulative",
            "z_score",
            "score",
            "rainfall_class",
        ]
        for col in required:
            assert col in sample_dataframe.columns

    def test_index_is_datetime(self, sample_dataframe):
        assert pd.api.types.is_datetime64_any_dtype(sample_dataframe.index)

    def test_no_negative_precipitation(self, sample_dataframe):
        assert (sample_dataframe["precipitation"] >= 0).all()

    def test_cumulative_is_monotonic(self, sample_dataframe):
        assert sample_dataframe["cumulative"].is_monotonic_increasing

    def test_score_in_range(self, sample_dataframe):
        scores = sample_dataframe["score"]
        assert (scores >= 0).all()
        assert (scores <= 100).all()

    def test_365_rows(self, sample_dataframe):
        assert len(sample_dataframe) == 365
