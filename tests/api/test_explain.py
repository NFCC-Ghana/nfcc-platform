"""Tests for POST /explain (SHAP feature importance)."""

import pytest

from src.models.train_model import FEATURE_COLS


def _valid_explain_payload():
    return {
        "precipitation": 28.5,
        "roll_3d": 55.2,
        "roll_7d": 18.3,
        "roll_30d": 9.1,
        "cumulative": 620.0,
        "z_score": 2.8,
        "location": "Accra Central",
        "timestamp": "2024-06-01T12:00:00",
    }


class TestExplainEndpoint:
    def test_explain_returns_200_and_six_features(self, api_client):
        response = api_client.post("/explain", json=_valid_explain_payload())
        assert response.status_code == 200
        data = response.json()
        assert "features" in data
        assert len(data["features"]) == 6
        names = [f["feature"] for f in data["features"]]
        assert names == FEATURE_COLS

    def test_explain_importance_scores_sum_to_one(self, api_client):
        response = api_client.post("/explain", json=_valid_explain_payload())
        assert response.status_code == 200
        total = sum(f["importance"] for f in response.json()["features"])
        assert total == pytest.approx(1.0, abs=1e-5)

    def test_explain_includes_risk_score_and_metadata(self, api_client):
        response = api_client.post("/explain", json=_valid_explain_payload())
        assert response.status_code == 200
        body = response.json()
        assert "risk_score" in body
        assert "base_value" in body
        assert "method" in body
        assert body["location"] == "Accra Central"
        assert body["timestamp"] == "2024-06-01T12:00:00"
        for item in body["features"]:
            assert "shap_value" in item
            assert item["importance"] >= 0.0

    def test_explain_rejects_negative_precipitation(self, api_client):
        bad = _valid_explain_payload()
        bad["precipitation"] = -1.0
        response = api_client.post("/explain", json=bad)
        assert response.status_code == 422
