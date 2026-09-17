"""Regression tests for GET /v1/health/data-sources
(src/api/v1/health.py) - priority deliverable #10's missing half (the
existing GET /health never reported on data sources)."""

from unittest.mock import MagicMock, patch


def test_data_source_health_schema(api_client):
    resp = api_client.get("/v1/health/data-sources")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_status" in data
    assert "sources" in data
    assert "checked_at" in data
    names = {s["name"] for s in data["sources"]}
    assert any("Earth Engine" in n for n in names)
    assert any("DAHITI" in n for n in names)
    assert any("Open-Meteo" in n for n in names)
    assert any("River Gauges" in n for n in names)
    assert any("Community reports" in n for n in names)


def test_river_gauges_reported_as_not_configured():
    """No credential mechanism exists for this integration at all - it
    must never be reported as 'connected'."""
    from src.api.v1.health import _check_river_gauges

    result = _check_river_gauges()
    assert result.status == "not_configured"


def test_dahiti_not_configured_is_not_degraded(monkeypatch):
    """DAHITI being unconfigured is a real, expected, functioning-without-
    it state (the platform works fine, just with less Akosombo evidence)
    - it must never be reported as 'unavailable' (which would mark the
    whole platform degraded) the way a genuine outage would. Unit-tested
    directly against _check_dahiti rather than through the live endpoint,
    to avoid a broad os.getenv patch affecting anything else the request
    cycle reads from the environment."""
    from src.api.v1.health import _check_dahiti

    monkeypatch.delenv("DAHITI_API_KEY", raising=False)
    result = _check_dahiti()
    assert result.status == "not_configured"


def test_open_meteo_unreachable_marks_degraded(api_client):
    with patch("requests.get", side_effect=Exception("connection refused")):
        resp = api_client.get("/v1/health/data-sources")
    data = resp.json()
    open_meteo = next(s for s in data["sources"] if "Open-Meteo" in s["name"])
    assert open_meteo["status"] == "unavailable"
    assert data["overall_status"] == "degraded"


def test_open_meteo_reachable_reports_connected(api_client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("requests.get", return_value=mock_resp):
        resp = api_client.get("/v1/health/data-sources")
    data = resp.json()
    open_meteo = next(s for s in data["sources"] if "Open-Meteo" in s["name"])
    assert open_meteo["status"] == "connected"
