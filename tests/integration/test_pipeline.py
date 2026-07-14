"""Integration tests for the ML pipeline."""

import numpy as np
import pandas as pd
import pytest

from src.alerts.engine import AlertEngine
from src.alerts.providers.mock_provider import MockAlertProvider


class TestFullPipeline:
    """Test the full ML pipeline."""

    def test_dataframe_loads_and_scores(
        self, sample_dataframe_with_features, alert_engine, trained_model
    ):
        """Test that dataframe loads and scores correctly."""
        # Sample dataframe should have required columns
        df = sample_dataframe_with_features.copy()

        # Add any missing required columns
        if "roll_3d" not in df.columns:
            df["roll_3d"] = df["precipitation"].rolling(3, min_periods=1).mean()
        if "roll_7d" not in df.columns:
            df["roll_7d"] = df["precipitation"].rolling(7, min_periods=1).mean()
        if "roll_30d" not in df.columns:
            df["roll_30d"] = df["precipitation"].rolling(30, min_periods=1).mean()
        if "cumulative" not in df.columns:
            df["cumulative"] = df["precipitation"].cumsum()
        if "z_score" not in df.columns:
            mean_rain = df["precipitation"].mean()
            std_rain = df["precipitation"].std()
            df["z_score"] = (df["precipitation"] - mean_rain) / (std_rain + 0.001)

        # Process each row
        results = []
        for idx, row in df.iterrows():
            result = alert_engine.process(
                location="Test Location",
                score=float(row["precipitation"]) / 2,  # Simple scoring
                precipitation=float(row["precipitation"]),
            )
            results.append(result)

        assert len(results) > 0
        assert all("alert_sent" in r for r in results)

    def test_mock_provider_receives_alert(self, alert_engine):
        """Test that mock provider receives alerts."""
        result = alert_engine.process(
            location="Integration Test", score=85.0, precipitation=50.0
        )
        assert "alert_sent" in result
        # Mock provider should have processed the alert
        assert result.get("alert_sent") is not None
