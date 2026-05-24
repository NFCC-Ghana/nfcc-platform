"""
API failure-path and validation tests.
"""

from unittest.mock import patch


class TestPredictionValidation:
    """Validation and malformed request tests."""

    def test_missing_required_fields(self, api_client):
        """Request missing required fields should fail."""
        payload = {
            "precipitation": 10.0,
            # missing remaining fields
        }

        response = api_client.post("/score", json=payload)

        assert response.status_code == 422

    def test_empty_payload(self, api_client):
        """Empty payload should fail validation."""
        response = api_client.post("/score", json={})

        assert response.status_code == 422

    def test_invalid_data_types(self, api_client):
        """String values instead of floats should fail."""
        payload = {
            "precipitation": "invalid",
            "roll_3d": "bad",
            "roll_7d": "bad",
            "roll_30d": "bad",
            "cumulative": "bad",
            "z_score": "bad",
        }

        response = api_client.post("/score", json=payload)

        assert response.status_code == 422

    def test_null_values(self, api_client):
        """Null values should fail validation."""
        payload = {
            "precipitation": None,
            "roll_3d": None,
            "roll_7d": None,
            "roll_30d": None,
            "cumulative": None,
            "z_score": None,
        }

        response = api_client.post("/score", json=payload)

        assert response.status_code == 422

    def test_extra_unexpected_fields(self, api_client):
        """Unexpected fields should not break API."""
        payload = {
            "precipitation": 10.0,
            "roll_3d": 20.0,
            "roll_7d": 15.0,
            "roll_30d": 5.0,
            "cumulative": 200.0,
            "z_score": 1.2,
            "unexpected_field": "ignored",
        }

        response = api_client.post("/score", json=payload)

        # Usually FastAPI ignores extra fields unless forbidden
        assert response.status_code in [200, 422]


class TestPredictionRuntimeFailures:
    """Internal runtime failure tests."""

    def test_model_prediction_exception(self, api_client):
        """Model prediction crash should return 500."""

        payload = {
            "precipitation": 10.0,
            "roll_3d": 20.0,
            "roll_7d": 15.0,
            "roll_30d": 5.0,
            "cumulative": 200.0,
            "z_score": 1.2,
        }

        with patch(
            "src.api.main.model.predict",
            side_effect=Exception("Model crashed"),
        ):
            response = api_client.post("/score", json=payload)

        assert response.status_code in [500, 503]

    def test_model_returns_invalid_shape(self, api_client):
        """Invalid prediction output should fail safely."""

        payload = {
            "precipitation": 10.0,
            "roll_3d": 20.0,
            "roll_7d": 15.0,
            "roll_30d": 5.0,
            "cumulative": 200.0,
            "z_score": 1.2,
        }

        with patch(
            "src.api.main.model.predict",
            return_value=[],
        ):
            response = api_client.post("/score", json=payload)

        assert response.status_code >= 400

    def test_model_returns_non_numeric_prediction(self, api_client):
        """Non-numeric prediction should fail safely."""

        payload = {
            "precipitation": 10.0,
            "roll_3d": 20.0,
            "roll_7d": 15.0,
            "roll_30d": 5.0,
            "cumulative": 200.0,
            "z_score": 1.2,
        }

        with patch(
            "src.api.main.model.predict",
            return_value=["invalid"],
        ):
            response = api_client.post("/score", json=payload)

        assert response.status_code >= 400


class TestBoundaryValues:
    """Boundary and extreme input tests."""

    def test_zero_values(self, api_client):
        """Zero values should still work."""

        payload = {
            "precipitation": 0.0,
            "roll_3d": 0.0,
            "roll_7d": 0.0,
            "roll_30d": 0.0,
            "cumulative": 0.0,
            "z_score": 0.0,
        }

        response = api_client.post("/score", json=payload)

        assert response.status_code == 200

    def test_extremely_large_values(self, api_client):
        """Very large values should not crash API."""

        payload = {
            "precipitation": 999999.0,
            "roll_3d": 999999.0,
            "roll_7d": 999999.0,
            "roll_30d": 999999.0,
            "cumulative": 999999.0,
            "z_score": 999999.0,
        }

        response = api_client.post("/score", json=payload)

        assert response.status_code in [200, 400, 422]

    def test_negative_values(self, api_client):
        """Negative values should be handled safely."""

        payload = {
            "precipitation": -10.0,
            "roll_3d": -20.0,
            "roll_7d": -15.0,
            "roll_30d": -5.0,
            "cumulative": -200.0,
            "z_score": -1.2,
        }

        response = api_client.post("/score", json=payload)

        assert response.status_code in [200, 400, 422]


class TestHealthEndpoints:
    """Health and metadata endpoints."""

    def test_health_endpoint(self, api_client):
        """Health endpoint should respond."""
        response = api_client.get("/health")

        assert response.status_code == 200

    def test_root_endpoint(self, api_client):
        """Root endpoint should respond."""
        response = api_client.get("/")

        assert response.status_code == 200
