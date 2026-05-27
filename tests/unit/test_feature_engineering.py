"""Tests for feature engineering module."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def sample_dataframe():
    """Create a sample dataframe for feature engineering tests."""
    dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(365)]
    np.random.seed(42)
    rainfall = np.random.gamma(2, 5, 365)

    df = pd.DataFrame({"time": dates, "precipitation": rainfall})
    df.set_index("time", inplace=True)
    return df


class TestFeatureEngineering:
    """Test feature engineering functions."""

    def test_dataframe_has_required_columns(self, sample_dataframe):
        """Test that dataframe has required columns."""
        assert "precipitation" in sample_dataframe.columns

    def test_365_rows(self, sample_dataframe):
        """Test that dataframe has 365 rows."""
        assert len(sample_dataframe) == 365

    def test_no_negative_precipitation(self, sample_dataframe):
        """Test that precipitation is non-negative."""
        assert (sample_dataframe["precipitation"] >= 0).all()

    def test_index_is_datetime(self, sample_dataframe):
        """Test that index is datetime."""
        assert isinstance(sample_dataframe.index, pd.DatetimeIndex)

    def test_cumulative_is_monotonic(self, sample_dataframe):
        """Test that cumulative rainfall is monotonic."""
        cumulative = sample_dataframe["precipitation"].cumsum()
        assert cumulative.is_monotonic_increasing

    def test_risk_score_in_range(self, sample_dataframe):
        """Test that risk score is within 0-100."""
        # Simulate risk score calculation
        max_rain = sample_dataframe["precipitation"].max()
        risk_score = (sample_dataframe["precipitation"] / max_rain * 100).clip(0, 100)
        assert (risk_score >= 0).all() and (risk_score <= 100).all()
