"""Integration tests — Full data pipeline from raw rainfall to alert dispatch."""


class TestFullPipeline:
    def test_dataframe_loads_and_scores(self, sample_dataframe, alert_engine):
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
        result = alert_engine.process(obs, location="Pipeline Test")
        assert "risk_score" in result
        assert 0.0 <= result["risk_score"] <= 100.0

    def test_mock_provider_receives_alert(
        self, alert_engine, critical_risk_observation
    ):
        """Verify mock provider receives and processes alert."""

        result = alert_engine.process(
            risk_score=85.0,
            location="Integration Test",
            observation=critical_risk_observation,
            force=True,
        )

        assert result["dispatched"] is True
        assert any(r["success"] for r in result["results"])
