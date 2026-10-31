"""When Open-Meteo is unreachable the platform must report the forecast
as unavailable - never invent rainfall.

src/hydrology/weather_forecast.py used to return made-up rainfall in an
outage (15 mm plus a random draw in rainy months), labelled "fallback".
Those numbers reached users and were scored through calculate_score()
by the forecast risk timeline and the AI Copilot's risk tools, so an
outage could raise a district's risk on no evidence. These tests pin
the replacement behaviour end to end.
"""

import asyncio
from unittest.mock import patch

import requests

from src.alerts.formatter import calculate_score
from src.hydrology.weather_forecast import WeatherForecastEngine, weather_forecast
from src.models.forecast_timeline import build_risk_timeline, get_forecast_and_timeline


def _down(*args, **kwargs):
    raise requests.ConnectionError("Open-Meteo unreachable")


def test_unavailable_forecast_has_no_invented_values():
    result = WeatherForecastEngine()._unavailable_forecast(lat=6.6, lon=0.47, hours=72)
    assert result["source"] == "unavailable"
    for key in (
        "24h",
        "48h",
        "72h",
        "temperature_c",
        "is_raining_now",
        "rain_probability_now_percent",
        "rain_probability_today_percent",
    ):
        assert result[key] is None, key
    assert result["daily"] == [] and result["cumulative_6h"] == {}


def test_outage_returns_unavailable_and_is_not_cached():
    engine = WeatherForecastEngine()
    with patch("src.hydrology.weather_forecast.requests.get", side_effect=_down):
        result = engine.get_forecast(lat=5.6, lon=-0.2, hours=72)
    assert result["source"] == "unavailable"
    assert result["24h"] is None
    # recovery must be picked up on the next call, not served for an hour
    assert engine.forecast_cache == {}


def test_risk_timeline_has_no_projection_without_a_forecast():
    forecast = WeatherForecastEngine()._unavailable_forecast(5.6, -0.2, 72)
    timeline = build_risk_timeline(12.0, forecast)
    assert [p["hour"] for p in timeline] == ["Now"]


def test_forecast_and_timeline_passes_nulls_through():
    with patch("src.hydrology.weather_forecast.requests.get", side_effect=_down):
        weather_forecast.forecast_cache.clear()
        data = get_forecast_and_timeline("Accra Central", 0.0)
    assert data["source"] == "unavailable"
    assert data["forecast_24h_mm"] is None
    assert len(data["risk_timeline"]) == 1


def test_copilot_refuses_to_score_without_a_forecast():
    from src.copilot import tools

    with patch("src.hydrology.weather_forecast.requests.get", side_effect=_down):
        weather_forecast.forecast_cache.clear()
        for fn in (tools.get_district_decision, tools.get_district_evidence):
            out = asyncio.run(fn("Accra Central"))
            assert out["error"] == "forecast_unavailable"
            assert "risk_tier" not in out
        out = asyncio.run(tools.get_district_forecast("Accra Central"))
        assert out["error"] == "forecast_unavailable"


def test_timeline_does_not_add_the_forecast_to_itself():
    """Callers pass the 24 h forecast as the current rainfall; the +24h
    point must score that forecast once, not twice."""
    forecast = {
        "source": "open-meteo",
        "cumulative_6h": {"6": 2.0, "12": 4.0, "18": 6.0, "24": 8.0},
    }
    timeline = build_risk_timeline(8.0, forecast)
    assert timeline[0]["score"] == timeline[-1]["score"] == calculate_score(8.0)
