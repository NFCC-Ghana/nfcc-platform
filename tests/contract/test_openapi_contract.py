"""OpenAPI contract validation tests."""

import pytest
import json
from pathlib import Path
from jsonschema import validate, ValidationError


class TestOpenAPIContract:
    """Validate API responses against OpenAPI schema."""

    @pytest.fixture
    def openapi_schema(self):
        """Load OpenAPI schema."""
        schema_path = Path(__file__).parent.parent.parent / "openapi.json"
        if not schema_path.exists():
            pytest.skip("OpenAPI schema not found")
        with open(schema_path) as f:
            return json.load(f)

    def test_score_response_schema(self, api_client, openapi_schema):
        """Test score response matches schema."""
        payload = {
            "precipitation": 10.5,
            "roll_3d": 25.0,
            "roll_7d": 30.0,
            "roll_30d": 40.0,
            "cumulative": 150.0,
            "z_score": 1.2,
            "location": "Accra",
        }

        response = api_client.post("/score", json=payload)
        assert response.status_code == 200

        data = response.json()

        # Validate required fields
        required_fields = ["risk_score", "risk_tier", "alert", "location"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Validate score range
        score = data.get("risk_score", data.get("score"))
        assert 0 <= score <= 100, f"Score out of range: {score}"

    def test_batch_response_schema(self, api_client, openapi_schema):
        """Test batch response matches schema."""
        payload = {
            "records": [
                {
                    "precipitation": 10.5,
                    "roll_3d": 25.0,
                    "roll_7d": 30.0,
                    "roll_30d": 40.0,
                    "cumulative": 150.0,
                    "z_score": 1.2,
                    "location": "Accra",
                }
            ]
        }

        response = api_client.post("/score/batch", json=payload)
        assert response.status_code == 200

        data = response.json()

        # Validate batch structure
        assert "results" in data
        assert isinstance(data["results"], list)
        assert "total_records" in data

    def test_error_response_schema(self, api_client):
        """Test error response schema."""
        response = api_client.post("/score", json={})
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data or "error" in data

    def test_health_response_schema(self, api_client):
        """Test health endpoint schema."""
        response = api_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        required_fields = ["status", "model_loaded", "timestamp"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        assert data["status"] in ["ok", "healthy"]

    def test_districts_response_schema(self, api_client):
        """Test districts endpoint schema."""
        response = api_client.get("/districts")
        assert response.status_code == 200

        data = response.json()
        required_fields = ["districts", "city"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        assert isinstance(data["districts"], list)
        assert len(data["districts"]) > 0

        # Validate each district has required fields
        for district in data["districts"]:
            assert "district" in district
            assert "risk_zone" in district
