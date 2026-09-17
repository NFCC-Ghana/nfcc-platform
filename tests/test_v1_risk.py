"""Regression tests for GET /v1/districts/{district}/risk
(src/api/v1/risk.py)."""

from src.alerts.formatter import calculate_score, get_risk_tier


def test_risk_matches_calculate_score(api_client):
    """The endpoint must return exactly what calculate_score()/
    get_risk_tier() compute - it's a contract around that function, not
    a separate reimplementation that could drift from it."""
    resp = api_client.get(
        "/v1/districts/Tamale/risk", params={"precipitation_mm": 90}
    )
    assert resp.status_code == 200
    data = resp.json()
    expected_score = calculate_score(90)
    assert data["score"] == expected_score
    assert data["risk_tier"] == get_risk_tier(expected_score)
    assert data["district"] == "Tamale"
    assert data["precipitation_mm"] == 90


def test_risk_unknown_district_404(api_client):
    resp = api_client.get(
        "/v1/districts/Atlantis/risk", params={"precipitation_mm": 50}
    )
    assert resp.status_code == 404


def test_risk_missing_precipitation_422(api_client):
    resp = api_client.get("/v1/districts/Tamale/risk")
    assert resp.status_code == 422


def test_risk_negative_precipitation_422(api_client):
    resp = api_client.get(
        "/v1/districts/Tamale/risk", params={"precipitation_mm": -5}
    )
    assert resp.status_code == 422


def test_risk_is_district_agnostic_by_design(api_client):
    """Scoring is currently a pure function of precipitation only (see
    risk.py's module docstring on why district-adjusted scoring isn't
    wired in) - two different tracked districts with the same
    precipitation must get the same score, confirming this endpoint
    didn't silently introduce per-district adjustment."""
    r1 = api_client.get(
        "/v1/districts/Tamale/risk", params={"precipitation_mm": 40}
    )
    r2 = api_client.get(
        "/v1/districts/Kumasi/risk", params={"precipitation_mm": 40}
    )
    assert r1.json()["score"] == r2.json()["score"]
    assert r1.json()["risk_tier"] == r2.json()["risk_tier"]
