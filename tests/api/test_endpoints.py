"""API endpoint tests."""

import pytest
from fastapi.testclient import TestClient


class TestAPIEndpoints:
    """Test API endpoints."""

    def test_health_endpoint(self, api_client: TestClient):
        """Test health endpoint."""
        response = api_client.get("/health")
        assert response.status_code == 200
        assert "status" in response.json()

    def test_root_endpoint(self, api_client: TestClient):
        """Test root endpoint."""
        response = api_client.get("/")
        assert response.status_code == 200
        assert "name" in response.json() or "service" in response.json()

    def test_score_endpoint_valid(self, api_client: TestClient):
        """Test valid score request."""
        response = api_client.post(
            "/score", json={"location": "Accra Central", "precipitation": 45.5}
        )
        assert response.status_code == 200
        data = response.json()
        assert "score" in data or "risk_score" in data
        assert "location" in data

    def test_score_endpoint_negative_rainfall(self, api_client: TestClient):
        """Test negative rainfall (should be 422)."""
        response = api_client.post(
            "/score", json={"location": "Accra Central", "precipitation": -10}
        )
        assert response.status_code == 422

    def test_districts_endpoint(self, api_client: TestClient):
        """The real, canonical districts endpoint - the old unversioned
        /districts (a second, uncited, since-diverged 7-district list) was
        removed 2026-09-27; this is the one thing that was ever meant."""
        response = api_client.get("/v1/districts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) and len(data) == 9

    def test_alerts_endpoint(self, api_client: TestClient):
        """The bare GET /alerts alias (and the rest of the unversioned
        /alerts/* surface) was removed 2026-09-27 - GET /v1/alerts/history
        is the real, current equivalent."""
        response = api_client.get("/v1/alerts/history")
        assert response.status_code == 200
        assert response.json() is not None
