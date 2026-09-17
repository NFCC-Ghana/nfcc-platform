"""Regression tests for GET /v1/districts/{district}/forecast
(src/api/v1/forecast.py)."""

from src.alerts.formatter import calculate_score, get_risk_tier


def test_forecast_schema(api_client):
    resp = api_client.get(
        "/v1/districts/Tamale/forecast", params={"current_precipitation_mm": 40}
    )
    assert resp.status_code == 200
    data = resp.json()
    for key in (
        "district",
        "forecast_24h_mm",
        "forecast_48h_mm",
        "forecast_72h_mm",
        "cumulative_6h_mm",
        "daily",
        "risk_timeline",
        "source",
        "generated_at",
    ):
        assert key in data
    assert data["district"] == "Tamale"


def test_forecast_risk_timeline_now_matches_calculate_score(api_client):
    """The timeline's first point ("Now") must exactly equal
    calculate_score(current_precipitation_mm) - it's not a separate
    estimate, it's the same deterministic function everything else uses."""
    resp = api_client.get(
        "/v1/districts/Kumasi/forecast", params={"current_precipitation_mm": 60}
    )
    assert resp.status_code == 200
    data = resp.json()
    now_point = data["risk_timeline"][0]
    assert now_point["hour"] == "Now"
    expected_score = calculate_score(60)
    assert now_point["score"] == expected_score
    assert now_point["risk_tier"] == get_risk_tier(expected_score)


def test_forecast_risk_timeline_has_five_points(api_client):
    """Now, 6h, 12h, 18h, 24h - matching /situation's existing timeline
    shape, since this endpoint is meant to be a drop-in replacement for
    that part of it."""
    resp = api_client.get(
        "/v1/districts/Ho/forecast", params={"current_precipitation_mm": 20}
    )
    data = resp.json()
    hours = [p["hour"] for p in data["risk_timeline"]]
    assert hours == ["Now", "6h", "12h", "18h", "24h"]


def test_forecast_unknown_district_404(api_client):
    resp = api_client.get(
        "/v1/districts/Atlantis/forecast", params={"current_precipitation_mm": 10}
    )
    assert resp.status_code == 404


def test_forecast_missing_precipitation_422(api_client):
    resp = api_client.get("/v1/districts/Tamale/forecast")
    assert resp.status_code == 422
