"""Integration tests — Full data pipeline from raw rainfall to alert dispatch."""

import numpy as np
import pandas as pd


class TestFullPipeline:
    def test_dataframe_loads_and_scores(
        self, sample_dataframe, alert_engine, trained_model
    ):
        """Full pipeline: dataframe row → engine → score."""
        row = sample_dataframe.iloc[-1]
        obs = {
            "precipitation": float(row["precipitation"]),
            "roll_3d": float(row["roll_3d"]),
            "roll_7d": float(row["roll_7d"]),
            "roll_30d": float(row["roll_30d"]),
            "cumulative": float(row["cumulative"]),
            "z_score": float(row["z_score"]),
        }

        # Get prediction from model
        features = pd.DataFrame([obs])
        score = float(trained_model.predict(features)[0])

        # Use new engine API with explicit parameters
        result = alert_engine.process(
            location="Pipeline Test",
            score=score,
            precipitation=obs["precipitation"],
            roll_3d=obs["roll_3d"],
            z_score=obs["z_score"],
        )

        assert "dispatched" in result

    def test_mock_provider_receives_alert(
        self, alert_engine, critical_risk_observation, trained_model
    ):
        """Verify mock provider receives and processes alert."""
        # Use new engine API with explicit parameters
        result = alert_engine.process(
            location="Integration Test", score=85.0, force=True
        )

        assert result.get("dispatched", False) is True
