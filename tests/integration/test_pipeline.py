"""Integration tests — Full data pipeline from raw rainfall to alert dispatch."""

# import numpy as np  # Remove or comment out - not used
import pandas as pd  # Add this import


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
        # Create features dataframe and get prediction
        features = pd.DataFrame([obs])
        risk_score = float(trained_model.predict(features)[0])
        result = alert_engine.process(
            risk_score, location="Pipeline Test", observation=obs
        )
        assert "risk_score" in result
        assert 0.0 <= result["risk_score"] <= 100.0

    def test_mock_provider_receives_alert(
        self, alert_engine, critical_risk_observation, trained_model
    ):
        """Verify mock provider receives and processes alert."""
        # Use a high risk score to trigger alert
        risk_score = 85.0
        result = alert_engine.process(
            risk_score,
            location="Integration Test",
            observation=critical_risk_observation,
            force=True,
        )
        assert result["dispatched"] is True
        assert any(r["success"] for r in result["results"])
