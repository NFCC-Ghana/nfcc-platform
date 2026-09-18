"""Regression tests for GET /v1/districts/{district}/antecedent-rainfall
(src/api/v1/antecedent_rainfall.py) - the HTTP-reachable wrapper around
src/hydrology/antecedent_rainfall.py that
scripts/automated_risk_assessment.py depends on, since that script has
no Earth Engine credentials of its own."""

from unittest.mock import patch


def test_unknown_district_404(api_client):
    resp = api_client.get("/v1/districts/Not A Real District/antecedent-rainfall")
    assert resp.status_code == 404


def test_known_district_ee_unavailable_returns_200_with_honest_unavailable(api_client):
    """Earth Engine being unreachable is an operational fact, not a
    client error - the automated pipeline calling this must be able to
    tell the difference between 'bad district name' (404) and 'real
    district, data temporarily unavailable' (200, available=False)."""
    with patch(
        "src.hydrology.antecedent_rainfall.fetch_historical_chirps_series",
        return_value=[],
    ):
        resp = api_client.get("/v1/districts/Tamale/antecedent-rainfall")
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is False


def test_known_district_returns_real_shape_when_data_available(api_client):
    series = [
        {"date": "2026-09-10", "precipitation_mm": 5.0},
        {"date": "2026-09-11", "precipitation_mm": 10.0},
        {"date": "2026-09-12", "precipitation_mm": 15.0},
    ]
    with patch(
        "src.hydrology.antecedent_rainfall.fetch_historical_chirps_series",
        return_value=series,
    ):
        resp = api_client.get("/v1/districts/Tamale/antecedent-rainfall")
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is True
    assert data["rolling_3d_mm"] == 30.0
