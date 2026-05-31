"""Tests for the explainability API endpoint."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


class TestExplainEndpoint:
    """Test the /explain endpoint."""

    def test_explain_returns_200_and_has_required_fields(self):
        """POST /explain returns 200 and contains expected fields."""
        response = client.post(
            "/explain/", json={"location": "Accra Central", "precipitation": 50.0}
        )
        assert response.status_code == 200
        data = response.json()

        # Check for expected fields in the actual API response
        assert "location" in data
        assert "precipitation" in data
        assert "risk_score" in data
        assert "risk_tier" in data
        assert "explanation" in data
        assert "factors" in data
        assert "precipitation_contribution" in data["factors"]

    def test_explain_includes_risk_score_and_metadata(self):
        """Response should include risk score and metadata."""
        response = client.post(
            "/explain/", json={"location": "Accra Central", "precipitation": 75.0}
        )
        assert response.status_code == 200
        data = response.json()

        # Check for risk score and metadata
        assert "risk_score" in data
        assert isinstance(data["risk_score"], (int, float))
        assert data["risk_score"] > 0
        assert "risk_tier" in data
        assert data["risk_tier"] in ["LOW", "MODERATE", "HIGH", "CRITICAL", "EXTREME"]

    def test_explain_calculates_correct_risk_for_rainfall(self):
        """Test risk score calculation for different rainfall amounts."""
        # Light rain
        response = client.post(
            "/explain/", json={"location": "Accra Central", "precipitation": 5.0}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["risk_score"] == 15.0
        assert data["risk_tier"] == "LOW"

        # Moderate rain
        response = client.post(
            "/explain/", json={"location": "Accra Central", "precipitation": 25.0}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["risk_score"] == 52.5
        assert data["risk_tier"] == "HIGH"

        # Heavy rain
        response = client.post(
            "/explain/", json={"location": "Accra Central", "precipitation": 95.5}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["risk_score"] == 98.3
        assert data["risk_tier"] == "EXTREME"

    def test_explain_handles_zero_precipitation(self):
        """Zero precipitation should return minimal risk."""
        response = client.post(
            "/explain/", json={"location": "Accra Central", "precipitation": 0.0}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["risk_score"] == 0.0
        assert data["risk_tier"] == "LOW"

    def test_explain_handles_negative_precipitation(self):
        """Negative precipitation should be treated as 0."""
        response = client.post(
            "/explain/", json={"location": "Accra Central", "precipitation": -10.0}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["risk_score"] == 0.0
        assert data["risk_tier"] == "LOW"

    def test_explain_accepts_different_locations(self):
        """Different locations should work."""
        locations = ["Accra Central", "Tema", "Kumasi", "Takoradi", "Tamale"]
        for location in locations:
            response = client.post(
                "/explain/", json={"location": location, "precipitation": 50.0}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["location"] == location
