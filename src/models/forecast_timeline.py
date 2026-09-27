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


def build_risk_timeline(
    current_precipitation_mm: float, forecast: Dict
) -> List[Dict]:
    """'Now' (scored directly from current_precipitation_mm) plus
    +6h/+12h/+18h/+24h projections, each layering the real forecast's
    cumulative rainfall on top of current_precipitation_mm and scoring
    through calculate_score()/get_risk_tier() - the same functions every
    other real risk figure in this platform uses, never a separate curve."""
    cumulative = forecast.get("cumulative_6h", {})
    score_now = calculate_score(current_precipitation_mm)
    timeline = [
        {"hour": "Now", "score": score_now, "risk_tier": get_risk_tier(score_now)}
    ]
    for h in (6, 12, 18, 24):
        future_precip = current_precipitation_mm + cumulative.get(str(h), 0.0)
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
    """Real rainfall forecast (24h/48h/72h/daily, Open-Meteo-backed, an
    honestly-labeled "fallback" seasonal estimate when unreachable - see
    weather_forecast.py) plus its derived risk_timeline, for one district -
    the single computation POST /situation, GET /v1/districts/{d}/forecast,
    and the AI Copilot's get_district_forecast tool all now share."""
    forecast = weather_forecast.get_forecast_for_district(district)
    return {
        "forecast_24h_mm": forecast.get("24h", 0.0),
        "forecast_48h_mm": forecast.get("48h", 0.0),
        "forecast_72h_mm": forecast.get("72h", 0.0),
        "cumulative_6h_mm": forecast.get("cumulative_6h", {}),
        "daily": forecast.get("daily", []),
        "risk_timeline": build_risk_timeline(current_precipitation_mm, forecast),
        "source": forecast.get("source", "unknown"),
        "generated_at": forecast.get("timestamp", ""),
    }
