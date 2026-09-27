"""Tests for src/models/real_forecast_fusion.py - the real, per-district
activation of src/models/forecast_fusion.py's previously-disconnected
CHIRPS/GloFAS/Flood Hub fusion math (2026-09-27)."""

from unittest.mock import patch

import pytest

from src.models.real_forecast_fusion import (
    _normalize_glofas_ratio,
    get_chirps_risk,
    get_glofas_risk,
    get_real_forecast_fusion,
)


def test_unknown_district_honestly_reported():
    result = get_real_forecast_fusion("Not A Real District")
    assert result["available"] is False


# --- chirps_risk ---------------------------------------------------


def test_chirps_risk_unavailable_when_antecedent_unavailable():
    with patch(
        "src.models.real_forecast_fusion.get_antecedent_rainfall",
        return_value={"available": False, "reason": "Earth Engine unavailable"},
    ):
        result = get_chirps_risk("Tamale")
    assert result["available"] is False
    assert result["reason"] == "Earth Engine unavailable"


def test_chirps_risk_unavailable_when_stale():
    """A stale antecedent reading must not be fed into the fusion as if
    current - get_antecedent_rainfall's own "stale" flag (beyond
    _STALE_AFTER_DAYS) explicitly means it no longer represents current
    ground conditions."""
    with patch(
        "src.models.real_forecast_fusion.get_antecedent_rainfall",
        return_value={
            "available": True,
            "rolling_3d_mm": 40.0,
            "data_age_days": 27,
            "stale": True,
        },
    ):
        result = get_chirps_risk("Tamale")
    assert result["available"] is False
    assert "27 days old" in result["reason"]


def test_chirps_risk_real_score_when_fresh():
    with patch(
        "src.models.real_forecast_fusion.get_antecedent_rainfall",
        return_value={
            "available": True,
            "rolling_3d_mm": 60.0,
            "data_age_days": 2,
            "stale": False,
        },
    ):
        result = get_chirps_risk("Tamale")
    assert result["available"] is True
    # calculate_score(60.0) via the real curve, not asserted to an exact
    # value here (that's calculate_score's own test's job) - just that a
    # real score was computed, not skipped.
    assert result["risk"] > 0
    assert result["rolling_3d_mm"] == 60.0


# --- glofas_risk -----------------------------------------------------


def test_glofas_risk_unavailable_when_no_river_resolved():
    with patch(
        "src.models.real_forecast_fusion.fetch_glofas_discharge_ratio",
        return_value=None,
    ):
        result = get_glofas_risk(5.10, -1.25)
    assert result["available"] is False


def test_normalize_glofas_ratio_at_or_below_seasonal_mean_is_zero():
    assert _normalize_glofas_ratio(1.0) == 0.0
    assert _normalize_glofas_ratio(0.5) == 0.0


def test_normalize_glofas_ratio_at_elevated_threshold():
    from src.hydrology.glofas_discharge import ELEVATED_DISCHARGE_RATIO

    assert _normalize_glofas_ratio(ELEVATED_DISCHARGE_RATIO) == pytest.approx(60.0)


def test_normalize_glofas_ratio_at_and_beyond_max_is_capped():
    assert _normalize_glofas_ratio(2.5) == 100.0
    assert _normalize_glofas_ratio(10.0) == 100.0


# --- full fusion -------------------------------------------------------


def test_fusion_uses_only_available_sources():
    """With chirps stale and flood_hub unconfigured (the real state of
    production today - no pilot API key exists), only glofas should
    contribute, and both others must be listed as genuinely missing, not
    silently defaulted to some value."""
    with patch(
        "src.models.real_forecast_fusion.get_antecedent_rainfall",
        return_value={"available": False, "reason": "unavailable"},
    ), patch(
        "src.models.real_forecast_fusion.fetch_glofas_discharge_ratio",
        return_value=2.0,
    ):
        result = get_real_forecast_fusion("Tamale")

    assert result["available"] is True
    assert result["present_sources"] == ["glofas"]
    assert set(result["missing_sources"]) == {"chirps", "flood_hub"}
    assert result["sources"]["flood_hub"]["available"] is False
    assert "FLOOD_HUB_API_KEY" in result["sources"]["flood_hub"]["reason"]


def test_fusion_combines_chirps_and_glofas_when_both_available():
    with patch(
        "src.models.real_forecast_fusion.get_antecedent_rainfall",
        return_value={
            "available": True,
            "rolling_3d_mm": 60.0,
            "data_age_days": 1,
            "stale": False,
        },
    ), patch(
        "src.models.real_forecast_fusion.fetch_glofas_discharge_ratio",
        return_value=2.0,
    ):
        result = get_real_forecast_fusion("Tamale")

    assert result["available"] is True
    assert set(result["present_sources"]) == {"chirps", "glofas"}
    assert result["missing_sources"] == ["flood_hub"]
    assert 0.0 <= result["unified_risk"] <= 100.0
    assert 0.0 <= result["confidence"] <= 100.0


# --- end-to-end wiring (the actual routes, not the module in isolation) -


def test_v1_forecast_fusion_route(api_client):
    resp = api_client.get("/v1/districts/Tamale/forecast-fusion")
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is True
    assert "unified_risk" in data
    assert "sources" in data


def test_v1_forecast_fusion_route_unknown_district_404(api_client):
    resp = api_client.get("/v1/districts/Not-A-Real-Place/forecast-fusion")
    assert resp.status_code == 404


def test_situation_includes_forecast_fusion_field(api_client):
    """Confirms the wiring itself, not just the module in isolation - a
    unit test of real_forecast_fusion.py alone wouldn't catch a mistake
    in how situation.py calls it."""
    resp = api_client.post("/situation", json={"location": "Tamale", "precipitation": 60})
    assert resp.status_code == 200
    data = resp.json()
    assert "forecast_fusion" in data
    assert data["forecast_fusion"]["available"] is True
