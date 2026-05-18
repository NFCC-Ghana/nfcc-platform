"""API endpoint tests using api_client fixture."""


class TestAPIEndpoints:
    def test_health_endpoint(self, api_client):
        response = api_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_root_endpoint(self, api_client):
        response = api_client.get("/")
        assert response.status_code == 200
        assert "NFCC" in response.json()["service"]

    def test_score_endpoint_valid(self, api_client):
        payload = {
            "precipitation": 28.5,
            "roll_3d": 55.2,
            "roll_7d": 18.3,
            "roll_30d": 9.1,
            "cumulative": 620.0,
            "z_score": 2.8,
            "location": "Accra Central",
        }
        response = api_client.post("/score", json=payload)
        assert response.status_code == 200
        assert "risk_score" in response.json()

    def test_score_endpoint_negative_rainfall(self, api_client):
        payload = {
            "precipitation": -10,
            "roll_3d": 55.2,
            "roll_7d": 18.3,
            "roll_30d": 9.1,
            "cumulative": 620.0,
            "z_score": 2.8,
            "location": "Accra Central",
        }
        response = api_client.post("/score", json=payload)
        assert response.status_code == 422

    def test_alerts_endpoint(self, api_client):
        response = api_client.get("/alerts")
        assert response.status_code == 200

    def test_districts_endpoint(self, api_client):
        response = api_client.get("/districts")
        assert response.status_code == 200
