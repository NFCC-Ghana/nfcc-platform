"""Real per-district rainfall forecast + derived risk-projection timeline
- the single canonical computation, added 2026-09-27 after an audit found
it independently reimplemented in three separate places: src/api/routes/
situation.py (POST /situation), src/api/v1/forecast.py
(GET /v1/districts/{district}/forecast), and src/copilot/tools.py
(get_district_forecast). All three called the exact same real sources
(src/hydrology/weather_forecast.py's Open-Meteo-backed forecast,
src/alerts/formatter.py's calculate_score/get_risk_tier) with the exact
same +6h/+12h/+18h/+24h layering logic, by hand, three times - meaning
any future change (different hour steps, a different layering rule) had
to be made in three files with nothing enforcing agreement between them.

Each of the three call sites now calls get_forecast_and_timeline() and
adapts the plain dict it returns into its own response shape (a Pydantic
model for the versioned route, a merged field set for /situation's larger
response, a passthrough dict for the Copilot tool) - the computation
itself lives in exactly one place.
"""

from typing import Dict, List

from src.alerts.formatter import calculate_score, get_risk_tier
from src.hydrology.weather_forecast import weather_forecast


def build_risk_timeline(current_precipitation_mm: float, forecast: Dict) -> List[Dict]:
    """'Now' (scored from current_precipitation_mm, the rainfall the caller
    is assessing) plus +6h/+12h/+18h/+24h points scored from the forecast's
    cumulative rainfall up to each hour, through calculate_score()/
    get_risk_tier() like every other risk figure.

    The projection used to ADD the forecast to current_precipitation_mm.
    Most callers (dashboard, kiosk, copilot) pass the 24 h forecast itself
    as current_precipitation_mm, so the +24h point scored twice the
    forecast. Each projected point is now the forecast's own accumulation,
    so with the forecast as input the +24h point equals 'Now'."""
    cumulative = forecast.get("cumulative_6h", {})
    score_now = calculate_score(current_precipitation_mm)
    timeline = [
        {"hour": "Now", "score": score_now, "risk_tier": get_risk_tier(score_now)}
    ]
    if forecast.get("source") == "unavailable" or not cumulative:
        # No forecast: no projection. A flat line built from missing
        # values would look like a real "no change" forecast.
        return timeline
    for h in (6, 12, 18, 24):
        future_precip = cumulative.get(str(h), 0.0)
        future_score = calculate_score(future_precip)
        timeline.append(
            {
                "hour": f"{h}h",
                "score": future_score,
                "risk_tier": get_risk_tier(future_score),
            }
        )
    return timeline


def get_forecast_and_timeline(district: str, current_precipitation_mm: float) -> Dict:
    """Real rainfall forecast (24h/48h/72h/daily, Open-Meteo-backed;
    None values with source "unavailable" when unreachable - see
    weather_forecast.py) plus its derived risk_timeline, for one district -
    the single computation POST /situation, GET /v1/districts/{d}/forecast,
    and the AI Copilot's get_district_forecast tool all now share."""
    forecast = weather_forecast.get_forecast_for_district(district)
    return {
        "forecast_24h_mm": forecast.get("24h"),
        "forecast_48h_mm": forecast.get("48h"),
        "forecast_72h_mm": forecast.get("72h"),
        "cumulative_6h_mm": forecast.get("cumulative_6h", {}),
        "daily": forecast.get("daily", []),
        "risk_timeline": build_risk_timeline(current_precipitation_mm, forecast),
        "source": forecast.get("source", "unknown"),
        "generated_at": forecast.get("timestamp", ""),
    }
