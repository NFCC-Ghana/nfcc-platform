"""Regression tests for real temperature/weather-condition/rain-
probability data (src/hydrology/weather_forecast.py, wired into GET/POST
/situation) - the system stays useful outside rainy season, when score/
risk_tier sit near zero for every district, by still showing what it's
actually like outside right now.
"""

from unittest.mock import patch

import pytest

from src.hydrology.weather_forecast import (
    WMO_WEATHER_CODES,
    celsius_to_fahrenheit,
    describe_weather_code,
    weather_forecast,
)


def test_celsius_to_fahrenheit_known_points():
    assert celsius_to_fahrenheit(0) == 32.0
    assert celsius_to_fahrenheit(100) == 212.0
    assert celsius_to_fahrenheit(28) == pytest.approx(82.4)


def test_describe_weather_code_known_codes():
    clear = describe_weather_code(0, is_day=True)
    assert clear["description"] == "Clear sky"
    assert clear["icon"] == "☀️"
    assert clear["is_precipitating"] is False

    rain = describe_weather_code(63, is_day=True)
    assert rain["is_precipitating"] is True

    thunder = describe_weather_code(95, is_day=True)
    assert thunder["is_precipitating"] is True


def test_describe_weather_code_night_swaps_icon():
    day = describe_weather_code(0, is_day=True)
    night = describe_weather_code(0, is_day=False)
    assert day["icon"] != night["icon"]
    assert night["icon"] == "🌙"


def test_describe_weather_code_unknown_code_does_not_crash():
    result = describe_weather_code(9999, is_day=True)
    assert result["description"] == "Unknown"


def test_every_wmo_code_has_required_fields():
    for code, info in WMO_WEATHER_CODES.items():
        assert "description" in info
        assert "icon" in info
        assert "is_precipitating" in info


def test_unavailable_forecast_never_guesses_temperature_or_rain():
    """An outage must not produce a plausible-looking reading: the old
    fallback invented a temperature and a 70-85% rain chance."""
    result = weather_forecast._unavailable_forecast(lat=9.4, lon=-0.84, hours=72)
    assert result["source"] == "unavailable"
    assert result["temperature_c"] is None
    assert result["rain_probability_now_percent"] is None
    assert result["rain_probability_today_percent"] is None
    assert result["is_raining_now"] is None


def test_real_forecast_for_district_includes_temperature_fields():
    """Live call against the real Open-Meteo API - skipped gracefully
    (falls back) if the network is unavailable, matching every other
    real-API test in this suite."""
    result = weather_forecast.get_forecast_for_district("Accra Central")
    assert "temperature_c" in result
    assert "weather_description" in result
    assert "weather_icon" in result
    assert "rain_probability_today_percent" in result
    assert result["source"] in ("open-meteo", "unavailable")


def test_situation_endpoint_exposes_temperature_and_rain_probability(api_client):
    resp = api_client.post(
        "/situation", json={"location": "Sunyani", "precipitation": 0}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "temperature_c" in data
    assert "temperature_f" in data
    assert "weather_icon" in data
    assert "rain_probability_today_percent" in data
    assert "forecast_source" in data


_REAL_SHAPED_FORECAST = {
    "24h": 0.0,
    "48h": 0.0,
    "72h": 0.0,
    "daily": [],
    "cumulative_6h": {"6": 0.0, "12": 0.0, "18": 0.0, "24": 0.0},
    "temperature_c": 31.2,
    "temperature_f": celsius_to_fahrenheit(31.2),
    "weather_code": 1,
    "weather_description": "Mainly clear",
    "weather_icon": "🌤️",
    "is_day": True,
    "is_raining_now": False,
    "rain_probability_now_percent": 5,
    "rain_probability_today_percent": 10,
    "source": "open-meteo",
    "timestamp": "2026-10-30T12:00:00",
}


def test_situation_still_useful_with_zero_rainfall(api_client):
    """The exact scenario motivating this feature: dry season, zero
    precipitation input, flood risk at its floor - the system must
    still surface real temperature/weather data rather than going
    blank just because there's no flood risk to report. Uses a fixed
    real-shaped Open-Meteo reading so a CI timeout can't fail it."""
    with patch.object(
        weather_forecast,
        "get_forecast_for_district",
        return_value=_REAL_SHAPED_FORECAST,
    ):
        resp = api_client.post(
            "/situation", json={"location": "Accra Central", "precipitation": 0}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 0.0
    assert data["temperature_c"] is not None
    assert data["weather_icon"] is not None


def test_situation_never_guesses_weather_when_forecast_unreachable(
    api_client, offline_http
):
    """Outage: the reading is reported as unavailable, never guessed."""
    weather_forecast.forecast_cache.clear()
    resp = api_client.post(
        "/situation", json={"location": "Accra Central", "precipitation": 0}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["forecast_source"] == "unavailable"
    assert data["temperature_c"] is None
    assert data["forecast_24h_mm"] is None
