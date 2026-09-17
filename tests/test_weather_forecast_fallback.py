"""Regression test for src/hydrology/weather_forecast.py's
_generate_fallback_forecast() - had zero test coverage before, and used
random.exponential() (a numpy.random method, not part of Python's
stdlib `random` module the file actually imports), which crashed with
AttributeError every single time this fallback path was actually
exercised. Only surfaced when tests/test_v1_forecast.py's real-API-call
test hit Open-Meteo being unreachable in CI and fell through to this
branch - this test exercises the fallback directly so it can never
silently regress again."""

from src.hydrology.weather_forecast import WeatherForecastEngine


def test_fallback_forecast_does_not_crash():
    engine = WeatherForecastEngine()
    result = engine._generate_fallback_forecast(lat=6.601, lon=0.471, hours=72)
    assert result["source"] == "fallback"
    for key in ("24h", "48h", "72h"):
        assert isinstance(result[key], float)
        assert result[key] >= 0
    assert len(result["daily"]) == 3
    assert set(result["cumulative_6h"].keys()) == {"6", "12", "18", "24"}


def test_fallback_forecast_is_deterministic_per_location():
    """Seeded on hash(lat_lon) - same location must give the same
    result, not fresh randomness each call."""
    engine = WeatherForecastEngine()
    first = engine._generate_fallback_forecast(lat=9.4, lon=-0.84, hours=72)
    second = engine._generate_fallback_forecast(lat=9.4, lon=-0.84, hours=72)
    assert first["24h"] == second["24h"]
