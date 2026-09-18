"""Regression tests for GET /v1/data-quality (src/api/v1/data_quality.py)
- real per-source QARTOD-based quality reports."""

from unittest.mock import patch


def test_schema_and_never_crashes(api_client):
    resp = api_client.get("/v1/data-quality")
    assert resp.status_code == 200
    data = resp.json()
    assert "system_status" in data
    assert data["system_status"] in ("healthy", "partial", "degraded")
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) >= 4
    for source in data["sources"]:
        assert "source" in source
        assert "overall" in source


def test_river_gauge_stale_reading_flagged_fail(api_client):
    with patch(
        "src.api.v1.data_quality.get_river_level_for_district",
        return_value={
            "available": True,
            "water_surface_elevation_m": 80.0,
            "observation_date": "2020-01-01T00:00:00",
        },
    ):
        resp = api_client.get("/v1/data-quality")
    river = next(s for s in resp.json()["sources"] if s["source"] == "river_gauge_tamale")
    assert river["overall"] == "fail"


def test_river_gauge_implausible_value_flagged_fail(api_client):
    with patch(
        "src.api.v1.data_quality.get_river_level_for_district",
        return_value={
            "available": True,
            "water_surface_elevation_m": 99999.0,
            "observation_date": "2026-01-01T00:00:00",
        },
    ):
        resp = api_client.get("/v1/data-quality")
    river = next(s for s in resp.json()["sources"] if s["source"] == "river_gauge_tamale")
    assert river["overall"] == "fail"


def test_river_gauge_unavailable_reported_as_missing(api_client):
    with patch(
        "src.api.v1.data_quality.get_river_level_for_district",
        return_value={"available": False, "reason": "no coverage"},
    ):
        resp = api_client.get("/v1/data-quality")
    river = next(s for s in resp.json()["sources"] if s["source"] == "river_gauge_tamale")
    assert river["overall"] == "missing"
    assert river["reason"] == "no coverage"


def test_system_status_degraded_when_any_source_fails(api_client):
    with patch(
        "src.api.v1.data_quality.get_river_level_for_district",
        return_value={
            "available": True,
            "water_surface_elevation_m": 99999.0,
            "observation_date": "2026-01-01T00:00:00",
        },
    ):
        resp = api_client.get("/v1/data-quality")
    assert resp.json()["system_status"] == "degraded"
