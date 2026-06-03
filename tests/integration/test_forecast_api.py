"""Integration tests for forecast fusion API routes."""


def test_forecast_confidence_endpoint(api_client):
    r = api_client.post(
        "/forecast/confidence",
        json={
            "location": "Accra Central",
            "chirps_risk": 40.0,
            "glofas_risk": 60.0,
            "flood_hub_risk": 50.0,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["unified_risk"] == 50.0
    assert "confidence" in data
    assert 0.0 <= data["confidence"] <= 100.0


def test_explain_forecast_endpoint(api_client):
    r = api_client.post(
        "/explain/forecast",
        json={
            "location": "Tema",
            "chirps_risk": 30.0,
            "glofas_risk": 70.0,
            "flood_hub_risk": None,
            "nsamples": 32,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "shap_values" in data
    assert "glofas" in data["shap_values"]


def test_forecast_confidence_validation(api_client):
    r = api_client.post(
        "/forecast/confidence",
        json={"location": "X", "chirps_risk": 101.0},
    )
    assert r.status_code == 422
