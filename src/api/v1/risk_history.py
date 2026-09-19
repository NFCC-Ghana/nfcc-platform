"""GET/POST /v1/districts/{district}/risk/history - priority deliverable
#9, the one genuinely new capability among the 10: nothing before this
persisted a continuous, timestamped record of computed risk over time.
alert_db.py's `alerts` table only records a row when a real alert was
actually SENT, and pending_alerts only exists while an assessment awaits
human review.

POST records one real snapshot (score computed server-side via the same
calculate_score() everything else uses, from a caller-supplied
precipitation value) - this exists specifically for
scripts/automated_risk_assessment.py (run every 3 hours by
.github/workflows/automated_risk_assessment.yml) to call for every
tracked district on each scheduled run, since that script runs outside
this container and has no direct database access, the same reason
POST /alerts/assess exists as an API rather than a direct DB write.

GET returns what's been recorded - empty until the scheduled job has run
at least once after this endpoint was deployed.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.auth import verify_api_key
from src.alerts.formatter import calculate_score, get_risk_tier
from src.database.risk_history_db import get_risk_history, save_risk_snapshot
from src.exposure.districts import get_district

router = APIRouter(prefix="/districts", tags=["v1"])


class RiskHistoryPoint(BaseModel):
    id: int
    district: str
    score: float
    risk_tier: str
    precipitation: float
    source: str
    recorded_at: str


class RiskHistoryResponse(BaseModel):
    district: str
    count: int
    history: List[RiskHistoryPoint]


class RecordRiskSnapshotRequest(BaseModel):
    precipitation_mm: float = Field(..., ge=0)
    source: str = Field(
        default="manual",
        description="What triggered this snapshot, e.g. 'scheduled' for the automated cron job",
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


@router.get("/{district}/risk/history", response_model=RiskHistoryResponse)
async def get_district_risk_history(
    district: str, limit: int = Query(100, ge=1, le=1000)
) -> RiskHistoryResponse:
    _require_tracked_district(district)
    history = get_risk_history(district, limit=limit)
    return RiskHistoryResponse(district=district, count=len(history), history=history)


@router.post(
    "/{district}/risk/history",
    response_model=RiskHistoryPoint,
    dependencies=[Depends(verify_api_key)],
)
async def record_district_risk_snapshot(
    district: str, request: RecordRiskSnapshotRequest
) -> RiskHistoryPoint:
    _require_tracked_district(district)
    score = calculate_score(request.precipitation_mm)
    risk_tier = get_risk_tier(score)
    saved = save_risk_snapshot(
        district=district,
        score=score,
        risk_tier=risk_tier,
        precipitation=request.precipitation_mm,
        source=request.source,
    )
    return RiskHistoryPoint(
        id=saved["id"],
        district=district,
        score=score,
        risk_tier=risk_tier,
        precipitation=request.precipitation_mm,
        source=request.source,
        recorded_at=saved["recorded_at"],
    )
