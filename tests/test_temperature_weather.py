"""Regression tests for real temperature/weather-condition/rain-
probability data (src/hydrology/weather_forecast.py, wired into GET/POST
/situation) - the system stays useful outside rainy season, when score/
risk_tier sit near zero for every district, by still showing what it's
actually like outside right now.
"""

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


def test_fallback_forecast_includes_honest_temperature_and_rain_probability():
    """Regression test for the real bug class this session has focused
    on: a fallback value must be usable but never mistaken for a real
    reading - always check forecast_source first."""
    result = weather_forecast._generate_fallback_forecast(lat=9.4, lon=-0.84, hours=72)
    assert result["source"] == "fallback"
    assert result["temperature_c"] is not None
    assert 15 <= result["temperature_c"] <= 45  # sane Ghana range, not an arbitrary number
    assert result["temperature_f"] == celsius_to_fahrenheit(result["temperature_c"])
    assert result["rain_probability_now_percent"] is not None
    assert result["rain_probability_today_percent"] is not None
    assert isinstance(result["is_raining_now"], bool)


def test_real_forecast_for_district_includes_temperature_fields():
    """Live call against the real Open-Meteo API - skipped gracefully
    (falls back) if the network is unavailable, matching every other
    real-API test in this suite."""
    result = weather_forecast.get_forecast_for_district("Accra Central")
    assert "temperature_c" in result
    assert "weather_description" in result
    assert "weather_icon" in result
    assert "rain_probability_today_percent" in result
    assert result["source"] in ("open-meteo", "fallback")


def test_situation_endpoint_exposes_temperature_and_rain_probability(api_client):
    resp = api_client.post("/situation", json={"location": "Sunyani", "precipitation": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert "temperature_c" in data
    assert "temperature_f" in data
    assert "weather_icon" in data
    assert "rain_probability_today_percent" in data
    assert "forecast_source" in data


def test_situation_still_useful_with_zero_rainfall(api_client):
    """The exact scenario motivating this feature: dry season, zero
    precipitation input, flood risk at its floor - the system must
    still surface real temperature/weather data rather than going
    blank just because there's no flood risk to report."""
    resp = api_client.post("/situation", json={"location": "Accra Central", "precipitation": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 0.0
    assert data["temperature_c"] is not None
    assert data["weather_icon"] is not None
