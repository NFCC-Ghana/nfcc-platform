"""Weather forecast engine with Open-Meteo integration."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeatherForecastEngine:
    """
    Weather forecast engine for flood prediction.
    Integrates Open-Meteo API with fallback generation.
    """

    def __init__(self):
        self.cache_path = Path("data/forecast_cache.json")
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.forecast_cache = {}
        self.open_meteo_url = "https://api.open-meteo.com/v1/forecast"

        # Ghana district coordinates (verified) - matches
        # hackathon/app/pages/dashboard.py's get_district_data, the only
        # other place these are listed.
        self.district_coords = {
            "Accra Central": {"lat": 5.560, "lon": -0.210},
            "Accra West": {"lat": 5.550, "lon": -0.230},
            "Accra East": {"lat": 5.565, "lon": -0.190},
            "Tema": {"lat": 5.650, "lon": -0.020},
            "Kumasi": {"lat": 6.670, "lon": -1.620},
            "Tamale": {"lat": 9.400, "lon": -0.840},
            "Cape Coast": {"lat": 5.100, "lon": -1.250},
            "Ho": {"lat": 6.601, "lon": 0.471},
            "Sunyani": {"lat": 7.333, "lon": -2.333},
        }

        logger.info("Weather Forecast Engine initialized")

    def get_forecast(self, lat: float, lon: float, hours: int = 72) -> Dict:
        """Get weather forecast for a location."""
        cache_key = f"{lat}_{lon}_{hours}"

        # Check cache
        if cache_key in self.forecast_cache:
            cached = self.forecast_cache[cache_key]
            if (datetime.now() - cached["timestamp"]).seconds < 3600:
                return cached["data"]

        try:
            # Fetch from Open-Meteo
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "rain",
                "forecast_days": 3,
                "timezone": "GMT",
            }

            response = requests.get(self.open_meteo_url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                forecast = self._parse_open_meteo(data, hours)
            else:
                logger.warning(f"Open-Meteo API returned status {response.status_code}")
                forecast = self._generate_fallback_forecast(lat, lon, hours)

        except Exception as e:
            logger.warning(f"Open-Meteo API error: {e}")
            forecast = self._generate_fallback_forecast(lat, lon, hours)

        # Cache
        self.forecast_cache[cache_key] = {"data": forecast, "timestamp": datetime.now()}

        return forecast

    def _parse_open_meteo(self, data: Dict, hours: int) -> Dict:
        """Parse Open-Meteo API response."""
        hourly = data.get("hourly", {})
        rain = hourly.get("rain", [])

        forecast = {}

        # Sum rainfall for 24h, 48h, 72h
        for h in [24, 48, 72]:
            if h <= hours and len(rain) > h:
                total_rain = sum(rain[:h])
                forecast[f"{h}h"] = round(total_rain, 1)
            else:
                forecast[f"{h}h"] = 0.0

        # Cumulative rainfall at each 6-hour mark within the next 24h - used
        # to build a real forecast-driven risk timeline (src/api/routes/
        # situation.py), rather than a fixed +15/+10/+5 synthetic offset
        # from the current score with no actual forecast behind it.
        forecast["cumulative_6h"] = {}
        for h in [6, 12, 18, 24]:
            forecast["cumulative_6h"][str(h)] = (
                round(sum(rain[:h]), 1) if len(rain) >= h else 0.0
            )

        # Daily breakdown
        forecast["daily"] = []
        for day in range(3):
            if len(rain) > (day + 1) * 24:
                daily_rain = sum(rain[day * 24 : (day + 1) * 24])
                forecast["daily"].append(
                    {"day": day + 1, "rainfall_mm": round(daily_rain, 1)}
                )
            else:
                forecast["daily"].append({"day": day + 1, "rainfall_mm": 0.0})

        forecast["source"] = "open-meteo"
        forecast["timestamp"] = datetime.now().isoformat()

        return forecast

    def _generate_fallback_forecast(self, lat: float, lon: float, hours: int) -> Dict:
        """Generate fallback forecast."""
        import random

        random.seed(hash(f"{lat}_{lon}") % 2**32)

        month = datetime.now().month
        is_rainy = month in [5, 6, 7, 9, 10]

        forecast = {}

        for h in [24, 48, 72]:
            if h <= hours:
                # random.exponential() doesn't exist on Python's stdlib
                # `random` module (that's a numpy.random method) - this
                # silently crashed with AttributeError any time this
                # fallback path was actually exercised (real Open-Meteo
                # call failing), never caught before because nothing had
                # forced the fallback branch in a test until now.
                # random.expovariate(lambd) is the stdlib equivalent. with
                # lambd = 1/mean, matching numpy's exponential(scale=mean).
                if is_rainy:
                    base = 15 + random.expovariate(1 / 10)
                else:
                    base = 3 + random.expovariate(1 / 5)
                forecast[f"{h}h"] = round(max(0, base), 1)
            else:
                forecast[f"{h}h"] = 0.0

        forecast["daily"] = []
        for day in range(3):
            forecast["daily"].append(
                {
                    "day": day + 1,
                    "rainfall_mm": forecast.get(
                        "24h" if day == 0 else "48h" if day == 1 else "72h", 0
                    )
                    / 3,
                }
            )

        # Same shape as _parse_open_meteo's real cumulative_6h, linearly
        # interpolated from the 24h total so callers don't need to handle
        # two different response shapes depending on whether the real API
        # call succeeded.
        rain_24h = forecast.get("24h", 0.0)
        forecast["cumulative_6h"] = {
            str(h): round(rain_24h * h / 24, 1) for h in [6, 12, 18, 24]
        }

        forecast["source"] = "fallback"
        forecast["timestamp"] = datetime.now().isoformat()

        return forecast

    def get_forecast_for_district(self, district: str, hours: int = 72) -> Dict:
        """Get forecast for a specific district."""
        coords = self.district_coords.get(district)
        if not coords:
            return {
                "error": f"District {district} not found",
                "24h": 0,
                "48h": 0,
                "72h": 0,
                "daily": [],
            }

        forecast = self.get_forecast(coords["lat"], coords["lon"], hours)
        forecast["district"] = district
        forecast["coordinates"] = coords

        return forecast

    def get_all_forecasts(self, hours: int = 72) -> Dict:
        """Get forecasts for all districts."""
        forecasts = {}
        for district in self.district_coords.keys():
            forecasts[district] = self.get_forecast_for_district(district, hours)
        return forecasts


# Singleton instance
weather_forecast = WeatherForecastEngine()
