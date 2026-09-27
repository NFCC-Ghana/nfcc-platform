"""GET /v1/districts/{district}/forecast - real forecast data plus the
derived risk projection, on its own contract instead of buried inside
POST /situation's response.

Two genuinely different things live here, both real:
- Rainfall forecast (src/hydrology/weather_forecast.py) - real Open-Meteo
  data when reachable, an honestly-labeled ("fallback") seasonal estimate
  otherwise. Not new logic; this endpoint just gives it its own contract.
- risk_timeline - a forward projection of calculate_score() at +6h/+12h/
  +18h/+24h, layering the real forecast's cumulative rainfall on top of
  the caller-supplied current precipitation.

Both come from src/models/forecast_timeline.py's get_forecast_and_timeline()
- the single shared implementation POST /situation and the AI Copilot's
get_district_forecast tool also call, after an audit found this exact
computation independently reimplemented three times (see that module's
docstring). This route just adapts the shared dict into its own
versioned Pydantic contract.
"""

from typing import Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.exposure.districts import get_district
from src.models.forecast_timeline import get_forecast_and_timeline

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

    data = get_forecast_and_timeline(district, current_precipitation_mm)

    return ForecastResponse(
        district=district,
        forecast_24h_mm=data["forecast_24h_mm"],
        forecast_48h_mm=data["forecast_48h_mm"],
        forecast_72h_mm=data["forecast_72h_mm"],
        cumulative_6h_mm=data["cumulative_6h_mm"],
        daily=[DailyForecast(**d) for d in data["daily"]],
        risk_timeline=[RiskTimelinePoint(**p) for p in data["risk_timeline"]],
        source=data["source"],
        generated_at=data["generated_at"],
    )
