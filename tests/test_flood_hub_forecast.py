"""Tests for src/hydrology/flood_hub_forecast.py - the real Google Flood
Hub client added 2026-09-27. No real FLOOD_HUB_API_KEY exists (pilot API
access not yet granted - see that module's docstring), so every test
here either checks the honest "not configured" path or mocks the HTTP
layer against the schema documented at developers.google.com/
flood-forecasting/rest/v1."""

from unittest.mock import MagicMock, patch

import pytest

from src.hydrology import flood_hub_forecast as fh


@pytest.fixture(autouse=True)
def _clear_cache_and_key(monkeypatch):
    """Isolate each test from both the in-process gauge cache and
    whatever FLOOD_HUB_API_KEY happens to be set in the real environment
    this test runs in."""
    fh._gauge_cache = {}
    fh._gauge_cache_at = None
    monkeypatch.delenv("FLOOD_HUB_API_KEY", raising=False)
    yield
    fh._gauge_cache = {}
    fh._gauge_cache_at = None


def test_unconfigured_honestly_reported():
    """The real state of production today: no pilot API key exists."""
    result = fh.get_flood_hub_forecast_for_district(5.560, -0.210)
    assert result["available"] is False
    assert "FLOOD_HUB_API_KEY not configured" in result["reason"]


def test_no_gauge_in_range(monkeypatch):
    monkeypatch.setenv("FLOOD_HUB_API_KEY", "test-key")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "gauges": [
            {
                "gaugeId": "far-away",
                "location": {"latitude": 40.0, "longitude": -74.0},
                "siteName": "Not Ghana",
                "river": "Hudson",
                "countryCode": "US",
                "qualityVerified": True,
                "hasModel": True,
            }
        ]
    }
    mock_resp.raise_for_status = MagicMock()
    with patch("src.hydrology.flood_hub_forecast.requests.post", return_value=mock_resp):
        result = fh.get_flood_hub_forecast_for_district(5.560, -0.210)
    assert result["available"] is False
    assert "within" in result["reason"]


def test_search_request_failure_is_honest(monkeypatch):
    monkeypatch.setenv("FLOOD_HUB_API_KEY", "test-key")
    with patch(
        "src.hydrology.flood_hub_forecast.requests.post",
        side_effect=fh.requests.exceptions.ConnectionError("no route"),
    ):
        result = fh.get_flood_hub_forecast_for_district(5.560, -0.210)
    assert result["available"] is False
    assert "reason" in result


def _mock_search_response(gauge_id="volta-1", lat=5.60, lon=-0.20):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "gauges": [
            {
                "gaugeId": gauge_id,
                "location": {"latitude": lat, "longitude": lon},
                "siteName": "Volta at Akosombo",
                "river": "Volta",
                "countryCode": "GH",
                "qualityVerified": True,
                "hasModel": True,
            }
        ]
    }
    return resp


def _mock_thresholds_response(warning=10.0, danger=20.0, extreme=30.0):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "thresholds": {
            "warningLevel": warning,
            "dangerLevel": danger,
            "extremeDangerLevel": extreme,
        }
    }
    return resp


def _mock_forecast_response(gauge_id="volta-1", value=15.0):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "forecasts": {
            gauge_id: {
                "forecasts": [
                    {
                        "gaugeId": gauge_id,
                        "issuedTime": "2026-09-27T00:00:00Z",
                        "forecastRanges": [
                            {
                                "value": value,
                                "forecastStartTime": "2026-09-27T00:00:00Z",
                                "forecastEndTime": "2026-09-27T06:00:00Z",
                            }
                        ],
                    }
                ]
            }
        }
    }
    return resp


def test_full_real_path_normalizes_against_real_thresholds(monkeypatch):
    """End-to-end with a mocked but schema-accurate API: a gauge within
    range, real thresholds, a forecast value between warning and danger
    -> a risk score in the 40-75 band, not a guessed number."""
    monkeypatch.setenv("FLOOD_HUB_API_KEY", "test-key")
    search_resp = _mock_search_response()
    thresholds_resp = _mock_thresholds_response(warning=10.0, danger=20.0, extreme=30.0)
    forecast_resp = _mock_forecast_response(value=15.0)

    with patch("src.hydrology.flood_hub_forecast.requests.post", return_value=search_resp), \
         patch(
             "src.hydrology.flood_hub_forecast.requests.get",
             side_effect=[thresholds_resp, forecast_resp],
         ):
        result = fh.get_flood_hub_forecast_for_district(5.560, -0.210)

    assert result["available"] is True
    assert result["source"] == "Google Flood Hub"
    assert result["gauge_id"] == "volta-1"
    # value=15 is exactly halfway between warning=10 and danger=20 ->
    # 40 + 35*0.5 = 57.5
    assert result["flood_hub_risk"] == pytest.approx(57.5)


def test_missing_thresholds_is_honest_not_guessed(monkeypatch):
    monkeypatch.setenv("FLOOD_HUB_API_KEY", "test-key")
    search_resp = _mock_search_response()
    no_thresholds_resp = MagicMock()
    no_thresholds_resp.raise_for_status = MagicMock()
    no_thresholds_resp.json.return_value = {}
    forecast_resp = _mock_forecast_response(value=15.0)

    with patch("src.hydrology.flood_hub_forecast.requests.post", return_value=search_resp), \
         patch(
             "src.hydrology.flood_hub_forecast.requests.get",
             side_effect=[no_thresholds_resp, forecast_resp],
         ):
        result = fh.get_flood_hub_forecast_for_district(5.560, -0.210)

    assert result["available"] is False
    assert "unavailable" in result["reason"]


def test_normalize_risk_boundaries():
    thresholds = {"warningLevel": 10.0, "dangerLevel": 20.0, "extremeDangerLevel": 30.0}
    assert fh._normalize_risk(0.0, thresholds) == 0.0
    assert fh._normalize_risk(10.0, thresholds) == pytest.approx(40.0)
    assert fh._normalize_risk(20.0, thresholds) == pytest.approx(75.0)
    assert fh._normalize_risk(30.0, thresholds) == 100.0
    assert fh._normalize_risk(50.0, thresholds) == 100.0


def test_normalize_risk_missing_thresholds_returns_none():
    assert fh._normalize_risk(15.0, {}) is None
    assert fh._normalize_risk(15.0, {"warningLevel": 10.0}) is None


def test_haversine_zero_distance():
    assert fh._haversine_km(5.56, -0.21, 5.56, -0.21) == pytest.approx(0.0)


def test_situation_includes_flood_hub_field(api_client, monkeypatch):
    """End-to-end check that src/api/routes/situation.py actually wires
    this module into the real /situation response - a unit test of
    flood_hub_forecast.py in isolation (the tests above) doesn't confirm
    the wiring itself works, only that the module's own logic is correct
    in isolation."""
    monkeypatch.delenv("FLOOD_HUB_API_KEY", raising=False)
    resp = api_client.post("/situation", json={"location": "Tamale", "precipitation": 60})
    assert resp.status_code == 200
    data = resp.json()
    assert "flood_hub" in data
    # Honest state of production today: no pilot API key exists yet.
    assert data["flood_hub"]["available"] is False
    assert "FLOOD_HUB_API_KEY not configured" in data["flood_hub"]["reason"]


def test_situation_flood_hub_field_for_untracked_district(api_client, monkeypatch):
    monkeypatch.delenv("FLOOD_HUB_API_KEY", raising=False)
    resp = api_client.post(
        "/situation", json={"location": "Not A Real District", "precipitation": 10}
    )
    assert resp.status_code == 200
    assert resp.json()["flood_hub"]["available"] is False
