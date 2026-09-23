"""GET /v1/districts/{district}/forecast - real forecast data plus the
derived risk projection, on its own contract instead of buried inside
POST /situation's response.

Two genuinely different things live here, both real:
- Rainfall forecast (src/hydrology/weather_forecast.py) - real Open-Meteo
  data when reachable, an honestly-labeled ("fallback") seasonal estimate
  otherwise. Not new logic; this endpoint just gives it its own contract.
- risk_timeline - a forward projection of calculate_score() at +6h/+12h/
  +18h/+24h, layering the real forecast's cumulative rainfall on top of
  the caller-supplied current precipitation. This is the same computation
  POST /situation already builds inline; it needs current_precipitation_mm
  as an input because "what will the score be" depends on where it's
  starting from "now", which isn't a property of the district alone.
"""

from typing import Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.alerts.formatter import calculate_score, get_risk_tier
from src.exposure.districts import get_district
from src.hydrology.weather_forecast import weather_forecast

router = APIRouter(prefix="/districts", tags=["v1"])


class DailyForecast(BaseModel):
    day: int
    rainfall_mm: float


class RiskTimelinePoint(BaseModel):
    hour: str
    score: float
    risk_tier: str


class ForecastResponse(BaseModel):
    district: str
    forecast_24h_mm: float
    forecast_48h_mm: float
    forecast_72h_mm: float
    cumulative_6h_mm: Dict[str, float]
    daily: List[DailyForecast]
    risk_timeline: List[RiskTimelinePoint]
    source: str
    generated_at: str


@router.get("/{district}/forecast", response_model=ForecastResponse)
async def get_district_forecast(
    district: str,
    current_precipitation_mm: float = Query(
        ...,
        ge=0,
        description="Current precipitation in mm, used to anchor the risk_timeline",
    ),
) -> ForecastResponse:
    if get_district(district) is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"'{district}' is not a tracked district. "
                "See GET /v1/districts for the full list."
            ),
        )

    forecast = weather_forecast.get_forecast_for_district(district)
    cumulative = forecast.get("cumulative_6h", {})

    # Same construction as src/api/routes/situation.py's risk_timeline -
    # "Now" always matches a direct calculate_score(current_precipitation_mm)
    # call, and each future point layers the real forecast's cumulative
    # rainfall on top of it, rather than a fixed synthetic offset.
    score_now = calculate_score(current_precipitation_mm)
    timeline = [
        RiskTimelinePoint(
            hour="Now", score=score_now, risk_tier=get_risk_tier(score_now)
        )
    ]
    for h in (6, 12, 18, 24):
        future_precip = current_precipitation_mm + cumulative.get(str(h), 0.0)
        future_score = calculate_score(future_precip)
        timeline.append(
            RiskTimelinePoint(
                hour=f"{h}h", score=future_score, risk_tier=get_risk_tier(future_score)
            )
        )

    return ForecastResponse(
        district=district,
        forecast_24h_mm=forecast.get("24h", 0.0),
        forecast_48h_mm=forecast.get("48h", 0.0),
        forecast_72h_mm=forecast.get("72h", 0.0),
        cumulative_6h_mm=cumulative,
        daily=[DailyForecast(**d) for d in forecast.get("daily", [])],
        risk_timeline=timeline,
        source=forecast.get("source", "unknown"),
        generated_at=forecast.get("timestamp", ""),
    )
