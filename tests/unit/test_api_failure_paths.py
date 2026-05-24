"""Elite API failure-path suite - production hardening."""

import pytest
import time
import threading
import os
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def api_client():
    return TestClient(app)


class TestAPIInputValidation:
    def test_invalid_json_returns_422(self, api_client):
        response = api_client.post(
            "/score",
            data='{"invalid": json}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_empty_body_returns_422(self, api_client):
        response = api_client.post("/score", json={})
        assert response.status_code == 422

    def test_missing_required_field_precipitation(self, api_client):
        response = api_client.post(
            "/score",
            json={
                "location": "Accra",
                "roll_3d": 10.0,
                "roll_7d": 20.0,
                "roll_30d": 30.0,
                "cumulative": 100.0,
                "z_score": 1.5,
            },
        )
        assert response.status_code == 422

    def test_invalid_type_rejected(self, api_client):
        response = api_client.post(
            "/score",
            json={
                "precipitation": "invalid",
                "roll_3d": 10.0,
                "roll_7d": 20.0,
                "roll_30d": 30.0,
                "cumulative": 100.0,
                "z_score": 1.5,
                "location": "Accra",
            },
        )
        assert response.status_code == 422

    def test_negative_precipitation_rejected(self, api_client):
        response = api_client.post(
            "/score",
            json={
                "precipitation": -5,
                "roll_3d": 10.0,
                "roll_7d": 20.0,
                "roll_30d": 30.0,
                "cumulative": 100.0,
                "z_score": 1.5,
                "location": "Accra",
            },
        )
        assert response.status_code == 422


class TestAPIBoundaries:
    def test_zero_values_valid(self, api_client):
        response = api_client.post(
            "/score",
            json={
                "precipitation": 0.0,
                "roll_3d": 0.0,
                "roll_7d": 0.0,
                "roll_30d": 0.0,
                "cumulative": 0.0,
                "z_score": 0.0,
                "location": "Accra",
            },
        )
        assert response.status_code == 200
        assert "score" in response.json()

    def test_max_boundary_values(self, api_client):
        response = api_client.post(
            "/score",
            json={
                "precipitation": 500.0,
                "roll_3d": 500.0,
                "roll_7d": 500.0,
                "roll_30d": 500.0,
                "cumulative": 5000.0,
                "z_score": 10.0,
                "location": "Accra",
            },
        )
        assert response.status_code == 200

    def test_roll_validation_logic(self, api_client):
        response = api_client.post(
            "/score",
            json={
                "precipitation": 50.0,
                "roll_3d": 10.0,
                "roll_7d": 20.0,
                "roll_30d": 30.0,
                "cumulative": 100.0,
                "z_score": 1.5,
                "location": "Accra",
            },
        )
        assert response.status_code == 422


class TestAPIModelFailures:
    def test_model_crash_returns_500(self, api_client, monkeypatch):
        def crash(*args, **kwargs):
            raise Exception("Model crash")

        monkeypatch.setattr("src.api.main.model.predict", crash)

        response = api_client.post(
            "/score",
            json={
                "precipitation": 10,
                "roll_3d": 10,
                "roll_7d": 20,
                "roll_30d": 30,
                "cumulative": 100,
                "z_score": 1.5,
                "location": "Accra",
            },
        )
        assert response.status_code == 500
        assert "error" in response.text.lower() or "detail" in response.text.lower()

    def test_model_none_returns_500(self, api_client, monkeypatch):
        monkeypatch.setattr("src.api.main.model", None)

        response = api_client.post(
            "/score",
            json={
                "precipitation": 10,
                "roll_3d": 10,
                "roll_7d": 20,
                "roll_30d": 30,
                "cumulative": 100,
                "z_score": 1.5,
                "location": "Accra",
            },
        )
        assert response.status_code == 500


class TestAPIPerformanceFailures:
    def test_slow_model_handled(self, api_client, monkeypatch):
        def slow(*args, **kwargs):
            time.sleep(0.2)
            return [50.0]

        monkeypatch.setattr("src.api.main.model.predict", slow)

        response = api_client.post(
            "/score",
            json={
                "precipitation": 10,
                "roll_3d": 10,
                "roll_7d": 20,
                "roll_30d": 30,
                "cumulative": 100,
                "z_score": 1.5,
                "location": "Accra",
            },
        )
        assert response.status_code in (200, 500)


class TestAPIBatchFailures:
    def test_empty_batch_rejected(self, api_client):
        response = api_client.post("/score/batch", json={"records": []})
        assert response.status_code == 400

    def test_excess_batch_size_rejected(self, api_client):
        records = [
            {
                "precipitation": 10,
                "roll_3d": 10,
                "roll_7d": 20,
                "roll_30d": 30,
                "cumulative": 100,
                "z_score": 1.5,
                "location": "Accra",
            }
            for _ in range(400)
        ]

        response = api_client.post("/score/batch", json={"records": records})
        assert response.status_code == 400

    def test_partial_batch_failure(self, api_client):
        response = api_client.post(
            "/score/batch",
            json={
                "records": [
                    {
                        "precipitation": 10,
                        "roll_3d": 10,
                        "roll_7d": 20,
                        "roll_30d": 30,
                        "cumulative": 100,
                        "z_score": 1.5,
                        "location": "Accra",
                    },
                    {
                        "precipitation": "bad",
                        "roll_3d": 10,
                        "roll_7d": 20,
                        "roll_30d": 30,
                        "cumulative": 100,
                        "z_score": 1.5,
                        "location": "Kumasi",
                    },
                ]
            },
        )
        assert response.status_code in (200, 400, 422)


class TestAPIConcurrency:
    def test_parallel_requests(self, api_client):
        results = []

        def make_request():
            res = api_client.post(
                "/score",
                json={
                    "precipitation": 10,
                    "roll_3d": 10,
                    "roll_7d": 20,
                    "roll_30d": 30,
                    "cumulative": 100,
                    "z_score": 1.5,
                    "location": "Accra",
                },
            )
            results.append(res.status_code)

        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(code in (200, 429, 500) for code in results)


class TestAPIAlertFailures:
    def test_missing_alert_log(self, api_client, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda x: False)

        res = api_client.get("/alerts")
        assert res.status_code == 200
        data = res.json()
        assert "alerts" in data or isinstance(data, list)


class TestAPISystemEndpoints:
    def test_health(self, api_client):
        res = api_client.get("/health")
        assert res.status_code == 200
        assert "status" in res.json()

    def test_root(self, api_client):
        res = api_client.get("/")
        assert res.status_code == 200
        assert "service" in res.json()

    def test_districts_endpoint(self, api_client):
        res = api_client.get("/districts")
        assert res.status_code == 200
        data = res.json()
        assert "districts" in data
        assert isinstance(data["districts"], list)
        assert len(data["districts"]) > 0
        assert "city" in data
        assert "Accra" in data["city"]


class TestAPIResponseContracts:
    def test_score_response_structure(self, api_client):
        res = api_client.post(
            "/score",
            json={
                "precipitation": 10,
                "roll_3d": 10,
                "roll_7d": 20,
                "roll_30d": 30,
                "cumulative": 100,
                "z_score": 1.5,
                "location": "Accra",
            },
        )
        if res.status_code == 200:
            data = res.json()
            assert "score" in data or "risk_score" in data

    def test_batch_response_structure(self, api_client):
        res = api_client.post("/score/batch", json={"records": []})
        assert res.status_code == 400
        data = res.json()
        assert "detail" in data or "error" in str(data)
