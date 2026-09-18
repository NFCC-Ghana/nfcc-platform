"""Regression tests for GET /v1/districts/{district}/fluvial-risk
(src/api/v1/fluvial_risk.py) - the standalone, rainfall-independent
dam/river risk check scripts/automated_risk_assessment.py depends on
so a pure dam-release flood isn't invisible to the automated pipeline."""

from unittest.mock import patch


def test_unknown_district_404(api_client):
    resp = api_client.get("/v1/districts/Atlantis/fluvial-risk")
    assert resp.status_code == 404


def test_dam_overflow_shows_high_risk_with_no_rainfall_input(api_client):
    """The whole point of this endpoint: it takes NO precipitation
    input at all, yet must still report high risk when a real dam is
    at flood status."""
    with patch(
        "src.api.v1.fluvial_risk.get_dam_intelligence_for_district",
        return_value=[{"dam": "Akosombo", "available": True, "status": "FLOOD"}],
    ), patch(
        "src.api.v1.fluvial_risk.get_river_level_for_district",
        return_value={"available": False, "reason": "no coverage"},
    ):
        resp = api_client.get("/v1/districts/Tema/fluvial-risk")
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_0_100"] == 95.0


def test_no_dam_no_river_district_honestly_reports_no_pathway(api_client):
    with patch(
        "src.api.v1.fluvial_risk.get_dam_intelligence_for_district", return_value=[]
    ), patch(
        "src.api.v1.fluvial_risk.get_river_level_for_district",
        return_value={"available": False, "reason": "no coverage"},
    ):
        resp = api_client.get("/v1/districts/Kumasi/fluvial-risk")
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_0_100"] is None
