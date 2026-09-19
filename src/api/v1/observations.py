"""POST/GET /v1/districts/{district}/observations - the real, durable
historical archive of every raw source reading (src/database/
observation_history_db.py), the "Historical data" foundation for
training/backtesting/evaluation/model comparison/event replay.

POST records one real observation - exists specifically for
scripts/automated_risk_assessment.py (run every 3 hours) to call for
every real source it fetches on each scheduled run, since that script
runs outside this container and has no direct database access, the
same reason POST /alerts/assess and POST .../risk/history exist as
APIs rather than direct DB writes.

GET returns what's accumulated so far - empty until the scheduled job
has run at least once after this endpoint was deployed, growing with
every real run after that.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.auth import verify_api_key
from src.database.observation_history_db import get_observations, save_observation
from src.exposure.districts import get_district

router = APIRouter(prefix="/districts", tags=["v1"])


class ObservationPoint(BaseModel):
    id: int
    district: str
    source: str
    value: Optional[float]
    unit: Optional[str]
    quality_flag: str
    observation_date: Optional[str]
    recorded_at: str


class ObservationListResponse(BaseModel):
    district: str
    count: int
    observations: List[ObservationPoint]


class RecordObservationRequest(BaseModel):
    source: str = Field(..., description="e.g. 'rainfall_forecast', 'river_gauge', 'dam_akosombo', 'smap_soil_moisture'")
    value: Optional[float] = Field(default=None, description="None is a real, honest 'missing' reading, not skipped")
    unit: str = Field(..., description="e.g. 'mm', 'm', 'risk_0_100', 'm3m3'")
    quality_flag: str = Field(
        default="not_evaluated",
        description="QARTOD flag (src/data_quality/quality_checks.py): pass/suspect/fail/missing/not_evaluated",
    )
    observation_date: Optional[str] = Field(
        default=None, description="Real timestamp of the underlying reading, if known"
    )


def _require_tracked_district(district: str) -> None:
    if get_district(district) is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"'{district}' is not a tracked district. "
                "See GET /v1/districts for the full list."
            ),
        )


@router.get("/{district}/observations", response_model=ObservationListResponse)
async def get_district_observations(
    district: str,
    source: Optional[str] = Query(default=None),
    limit: int = Query(500, ge=1, le=5000),
) -> ObservationListResponse:
    _require_tracked_district(district)
    rows = get_observations(district=district, source=source, limit=limit)
    return ObservationListResponse(district=district, count=len(rows), observations=rows)


@router.post(
    "/{district}/observations",
    response_model=ObservationPoint,
    dependencies=[Depends(verify_api_key)],
)
async def record_district_observation(
    district: str, request: RecordObservationRequest
) -> ObservationPoint:
    _require_tracked_district(district)
    saved = save_observation(
        district=district,
        source=request.source,
        value=request.value,
        unit=request.unit,
        quality_flag=request.quality_flag,
        observation_date=request.observation_date,
    )
    return ObservationPoint(
        id=saved["id"],
        district=district,
        source=request.source,
        value=request.value,
        unit=request.unit,
        quality_flag=request.quality_flag,
        observation_date=request.observation_date,
        recorded_at=saved["recorded_at"],
    )
