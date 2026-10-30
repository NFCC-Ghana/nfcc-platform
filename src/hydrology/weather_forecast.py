"""Weather forecast engine with Open-Meteo integration."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests

from src.exposure.districts import list_districts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WMO weather interpretation codes (the standard Open-Meteo, and most
# other real weather APIs, use) - https://open-meteo.com/en/docs lists
# the full table. Kept as the complete WMO set rather than trimmed to
# "codes Ghana actually sees" so a genuinely unusual real reading (fog
# during harmattan, an unseasonal code) still gets a real description
# instead of falling through to "Unknown".
WMO_WEATHER_CODES: Dict[int, Dict] = {
    0: {"description": "Clear sky", "icon": "☀️", "is_precipitating": False},
    1: {"description": "Mainly clear", "icon": "🌤️", "is_precipitating": False},
    2: {"description": "Partly cloudy", "icon": "⛅", "is_precipitating": False},
    3: {"description": "Overcast", "icon": "☁️", "is_precipitating": False},
    45: {"description": "Fog", "icon": "🌫️", "is_precipitating": False},
    48: {"description": "Depositing rime fog", "icon": "🌫️", "is_precipitating": False},
    51: {"description": "Light drizzle", "icon": "🌦️", "is_precipitating": True},
    53: {"description": "Moderate drizzle", "icon": "🌦️", "is_precipitating": True},
    55: {"description": "Dense drizzle", "icon": "🌧️", "is_precipitating": True},
    56: {
        "description": "Light freezing drizzle",
        "icon": "🌦️",
        "is_precipitating": True,
    },
    57: {
        "description": "Dense freezing drizzle",
        "icon": "🌧️",
        "is_precipitating": True,
    },
    61: {"description": "Slight rain", "icon": "🌦️", "is_precipitating": True},
    63: {"description": "Moderate rain", "icon": "🌧️", "is_precipitating": True},
    65: {"description": "Heavy rain", "icon": "🌧️", "is_precipitating": True},
    66: {"description": "Light freezing rain", "icon": "🌧️", "is_precipitating": True},
    67: {"description": "Heavy freezing rain", "icon": "🌧️", "is_precipitating": True},
    71: {"description": "Slight snow fall", "icon": "🌨️", "is_precipitating": True},
    73: {"description": "Moderate snow fall", "icon": "🌨️", "is_precipitating": True},
    75: {"description": "Heavy snow fall", "icon": "🌨️", "is_precipitating": True},
    77: {"description": "Snow grains", "icon": "🌨️", "is_precipitating": True},
    80: {"description": "Slight rain showers", "icon": "🌦️", "is_precipitating": True},
    81: {
        "description": "Moderate rain showers",
        "icon": "🌧️",
        "is_precipitating": True,
    },
    82: {"description": "Violent rain showers", "icon": "⛈️", "is_precipitating": True},
    85: {"description": "Slight snow showers", "icon": "🌨️", "is_precipitating": True},
    86: {"description": "Heavy snow showers", "icon": "🌨️", "is_precipitating": True},
    95: {"description": "Thunderstorm", "icon": "⛈️", "is_precipitating": True},
    96: {
        "description": "Thunderstorm with slight hail",
        "icon": "⛈️",
        "is_precipitating": True,
    },
    99: {
        "description": "Thunderstorm with heavy hail",
        "icon": "⛈️",
        "is_precipitating": True,
    },
}

_UNKNOWN_WEATHER = {"description": "Unknown", "icon": "❓", "is_precipitating": False}


def describe_weather_code(code: Optional[int], is_day: bool = True) -> Dict:
    """Real WMO code -> {description, icon, is_precipitating}. Clear/
    mainly-clear swap to a moon icon at night (is_day=False) - the same
    distinction Open-Meteo's own is_day field exists to make, since
    "sunny" is a meaningless/misleading claim after dark."""
    info = dict(WMO_WEATHER_CODES.get(code, _UNKNOWN_WEATHER))
    if not is_day:
        if code == 0:
            info["icon"] = "🌙"
            info["description"] = "Clear night sky"
        elif code == 1:
            info["icon"] = "🌤️"
            info["description"] = "Mainly clear night"
    return info


def celsius_to_fahrenheit(celsius: float) -> float:
    return round(celsius * 9 / 5 + 32, 1)


class WeatherForecastEngine:
    """
    Weather forecast engine for flood prediction.
    Integrates the Open-Meteo API; reports "unavailable" when it is down.
    """

    def __init__(self):
        self.cache_path = Path("data/forecast_cache.json")
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.forecast_cache = {}
        self.open_meteo_url = "https://api.open-meteo.com/v1/forecast"

        # Real district coordinates from src/exposure/districts.py, the
        # canonical registry - this used to be its own independent copy
        # (one of 5+ scattered district datasets found in a 2026-09-27
        # audit), matched by hand against dashboard.py's and
        # sentinel_processor.py's own copies rather than sharing one real
        # source. district_coords kept as an attribute (not just a module-
        # level import used inline) since get_forecast_for_district/
        # get_all_district_forecasts below already read it as
        # self.district_coords.
        self.district_coords = {
            district.name: {"lat": district.lat, "lon": district.lon}
            for district in list_districts()
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
            # Fetch from Open-Meteo - "current" gives the real
            # right-now reading (temperature/weather/precipitation),
            # independent of the "hourly" array used for the rainfall
            # forecast timeline. Both come back in one request.
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "rain,precipitation_probability",
                "current": "temperature_2m,weather_code,precipitation,is_day",
                "forecast_days": 3,
                "timezone": "GMT",
            }

            response = requests.get(self.open_meteo_url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                forecast = self._parse_open_meteo(data, hours, lat, lon)
            else:
                logger.warning(f"Open-Meteo API returned status {response.status_code}")
                forecast = self._unavailable_forecast(lat, lon, hours)

        except Exception as e:
            logger.warning(f"Open-Meteo API error: {e}")
            forecast = self._unavailable_forecast(lat, lon, hours)

        # Cache real forecasts only, so recovery is picked up on the next
        # call instead of an outage being served for an hour.
        if forecast["source"] == "open-meteo":
            self.forecast_cache[cache_key] = {
                "data": forecast,
                "timestamp": datetime.now(),
            }

        return forecast

    def _parse_open_meteo(self, data: Dict, hours: int, lat: float, lon: float) -> Dict:
        """Parse Open-Meteo API response."""
        hourly = data.get("hourly", {})
        rain = hourly.get("rain", [])
        precip_probability = hourly.get("precipitation_probability", [])

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

        # Real current conditions - the district is still worth showing
        # something useful for outside rainy season, when every other
        # field on this platform is near-zero (see this module's own
        # docstring history and situation.py's temperature fields).
        current = data.get("current") or {}
        temp_c = current.get("temperature_2m")
        is_day = bool(current.get("is_day", 1))
        weather_code = current.get("weather_code")
        weather_info = describe_weather_code(weather_code, is_day=is_day)

        forecast["temperature_c"] = round(temp_c, 1) if temp_c is not None else None
        forecast["temperature_f"] = (
            celsius_to_fahrenheit(temp_c) if temp_c is not None else None
        )
        forecast["weather_code"] = weather_code
        forecast["weather_description"] = weather_info["description"]
        forecast["weather_icon"] = weather_info["icon"]

        # Real "chance of rain" - a genuinely different, complementary
        # signal from this platform's own flood-risk score/tier: this is
        # the probability rain falls at all (Open-Meteo's own forecast
        # model output), not a downstream consequence of a rainfall
        # amount already assumed. Today's max (next 24h) is the single
        # most useful number for "should I expect rain today".
        if precip_probability:
            forecast["rain_probability_now_percent"] = precip_probability[0]
            forecast["rain_probability_today_percent"] = max(precip_probability[:24])
        else:
            forecast["rain_probability_now_percent"] = None
            forecast["rain_probability_today_percent"] = None
        forecast["is_day"] = is_day
        forecast["is_raining_now"] = bool(
            weather_info["is_precipitating"] or (current.get("precipitation") or 0) > 0
        )

        forecast["source"] = "open-meteo"
        forecast["timestamp"] = datetime.now().isoformat()

        return forecast

    def _unavailable_forecast(self, lat: float, lon: float, hours: int) -> Dict:
        """What callers get when Open-Meteo is unreachable: no numbers.

        This used to return invented rainfall (15 mm plus a random draw
        in rainy months) and a guessed temperature, labelled "fallback".
        Those numbers reached users (/situation forecast_*_mm), the
        forecast risk timeline and the AI Copilot's risk tools, which
        scored them through calculate_score() like real rain - so an
        outage could raise a district's risk. A warning system must say
        "unavailable", never guess: every value here is None and callers
        handle the gap explicitly.
        """
        return {
            "24h": None,
            "48h": None,
            "72h": None,
            "daily": [],
            "cumulative_6h": {},
            "temperature_c": None,
            "temperature_f": None,
            "weather_code": None,
            "weather_description": "Forecast unavailable (Open-Meteo unreachable)",
            "weather_icon": None,
            "is_day": None,
            "is_raining_now": None,
            "rain_probability_now_percent": None,
            "rain_probability_today_percent": None,
            "source": "unavailable",
            "timestamp": datetime.now().isoformat(),
        }

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
