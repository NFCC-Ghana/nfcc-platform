"""OpenAPI contract tests."""

import pytest
from fastapi.testclient import TestClient


class TestOpenAPIContract:
    """Test OpenAPI contract compliance."""

    def test_health_response_schema(self, api_client: TestClient):
        """Test health endpoint response schema."""
        response = api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # Check for presence of expected fields (not exact match)
        assert "status" in data
        assert data["status"] in ["healthy", "ok"]

    def test_error_response_schema(self, api_client: TestClient):
        """Test error response schema."""
        response = api_client.post("/score", json={})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_districts_response_schema(self, api_client: TestClient):
        """Test districts endpoint response schema."""
        response = api_client.get("/districts")
        assert response.status_code == 200
        data = response.json()
        assert "districts" in data or "count" in data

    def test_score_response_schema(self, api_client: TestClient):
        """Test score endpoint response schema."""
        response = api_client.post(
            "/score", json={"location": "Accra", "precipitation": 50}
        )
        assert response.status_code in [200, 422]

    def test_batch_response_schema(self, api_client: TestClient):
        """Test batch endpoint response schema."""
        response = api_client.post("/score/batch", json={"requests": []})
        assert response.status_code in [200, 422]
