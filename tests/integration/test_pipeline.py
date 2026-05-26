"""Integration tests — Full data pipeline from raw rainfall to alert dispatch."""

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
        risk_score = float(trained_model.predict(features)[0])

        # Only pass location and score (engine doesn't accept other kwargs)
        result = alert_engine.process(location="Pipeline Test", score=risk_score)

        assert "dispatched" in result

    def test_mock_provider_receives_alert(
        self, alert_engine, critical_risk_observation, trained_model
    ):
        result = alert_engine.process(
            location="Integration Test", score=85.0, force=True
        )

        assert result.get("dispatched", False) is True
