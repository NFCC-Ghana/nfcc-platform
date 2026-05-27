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
        response = api_client.post("/score", json={
            "location": "Accra Central",
            "precipitation": 45.5
        })
        assert response.status_code == 200
        data = response.json()
        assert "score" in data or "risk_score" in data
        assert "location" in data
    
    def test_score_endpoint_negative_rainfall(self, api_client: TestClient):
        """Test negative rainfall (should be 422)."""
        response = api_client.post("/score", json={
            "location": "Accra Central",
            "precipitation": -10
        })
        assert response.status_code == 422
    
    def test_districts_endpoint(self, api_client: TestClient):
        """Test districts endpoint."""
        response = api_client.get("/districts")
        assert response.status_code == 200
        data = response.json()
        assert "districts" in data
    
    def test_alerts_endpoint(self, api_client: TestClient):
        """Test alerts endpoint."""
        response = api_client.get("/alerts")
        assert response.status_code == 200
        assert response.json() is not None
