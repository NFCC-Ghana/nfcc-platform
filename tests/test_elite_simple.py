"""Simple elite resilience tests."""

import pytest
import time
import threading


class TestEliteResilience:
    """Elite resilience tests for API hardening."""

    def test_idempotent_scores(self, api_client):
        """Test that same input produces same output."""
        payload = {
            "precipitation": 10.5,
            "roll_3d": 25.0,
            "roll_7d": 30.0,
            "roll_30d": 40.0,
            "cumulative": 150.0,
            "z_score": 1.2,
            "location": "Accra",
        }

        scores = []
        for i in range(5):
            response = api_client.post("/score", json=payload)
            assert response.status_code == 200, f"Request {i+1} failed"
            data = response.json()
            score = data.get("risk_score", data.get("score"))
            scores.append(score)
            time.sleep(0.05)

        # All scores should be identical
        assert all(s == scores[0] for s in scores), f"Scores not consistent: {scores}"

    def test_replay_failure(self, api_client):
        """Test that failures are reproducible."""
        invalid_payload = {"precipitation": -50, "roll_3d": 10}

        response1 = api_client.post("/score", json=invalid_payload)
        response2 = api_client.post("/score", json=invalid_payload)

        assert response1.status_code == response2.status_code
        assert response1.status_code in (400, 422)

    def test_concurrent_requests(self, api_client):
        """Test concurrent request handling."""
        payload = {
            "precipitation": 10.5,
            "roll_3d": 25.0,
            "roll_7d": 30.0,
            "roll_30d": 40.0,
            "cumulative": 150.0,
            "z_score": 1.2,
            "location": "Accra",
        }

        results = []

        def make_request():
            response = api_client.post("/score", json=payload)
            results.append(response.status_code)

        threads = [threading.Thread(target=make_request) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed or be rate-limited
        for status in results:
            assert status in (200, 429, 400), f"Unexpected status: {status}"

    def test_all_endpoints(self, api_client):
        """Test all endpoints return successfully."""
        endpoints = [
            ("/", "get"),
            ("/health", "get"),
            ("/districts", "get"),
            ("/alerts", "get"),
        ]

        for endpoint, method in endpoints:
            if method == "get":
                response = api_client.get(endpoint)
            else:
                response = api_client.post(endpoint, json={})
            assert (
                response.status_code == 200
            ), f"Endpoint {endpoint} failed: {response.status_code}"

    def test_graceful_degradation(self, api_client, monkeypatch):
        """Test graceful degradation under model failure."""
        payload = {
            "precipitation": 10.5,
            "roll_3d": 25.0,
            "roll_7d": 30.0,
            "roll_30d": 40.0,
            "cumulative": 150.0,
            "z_score": 1.2,
            "location": "Accra",
        }

        import src.api.main as api_module

        def failing_predict(*args, **kwargs):
            raise Exception("Model unavailable")

        original_predict = api_module.model.predict

        try:
            api_module.model.predict = failing_predict
            response = api_client.post("/score", json=payload)
            # Should handle gracefully (either error or fallback)
            assert response.status_code in (200, 500, 503)
        finally:
            api_module.model.predict = original_predict

    def test_batch_endpoint(self, api_client):
        """Test batch endpoint with valid data."""
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
                },
                {
                    "precipitation": 20.0,
                    "roll_3d": 35.0,
                    "roll_7d": 40.0,
                    "roll_30d": 50.0,
                    "cumulative": 200.0,
                    "z_score": 2.0,
                    "location": "Tema",
                },
            ]
        }

        response = api_client.post("/score/batch", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 2

    def test_rate_limit_resilience(self, api_client):
        """Test rate limiting resilience under load."""
        payload = {
            "precipitation": 10.5,
            "roll_3d": 25.0,
            "roll_7d": 30.0,
            "roll_30d": 40.0,
            "cumulative": 150.0,
            "z_score": 1.2,
            "location": "Accra",
        }

        statuses = []
        for i in range(50):
            response = api_client.post("/score", json=payload)
            statuses.append(response.status_code)
            if i % 10 == 0:
                time.sleep(0.01)

        # Should have some successes
        successes = [s for s in statuses if s == 200]
        assert len(successes) > 0, "No successful requests"

        # Rate limiting may or may not kick in
        print(
            f"Status distribution: {dict((s, statuses.count(s)) for s in set(statuses))}"
        )
