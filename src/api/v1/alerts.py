"""GET/POST /v1/alerts/... - the versioned alert contract, consolidating
what was previously split across three separately-prefixed router files
all claiming /alerts with no path collisions today only by luck of
non-overlapping sub-paths: src/api/routes/alerts.py (history/stats),
alert_review.py (assess/exercise/pending/approve/cancel/dismiss), and
cap_export.py (CAP XML export).

This is a thin contract layer, not a reimplementation: every handler
here calls the exact same underlying route functions the original
/alerts routes call, so there is exactly one place the actual alert-
review/CAP-export/history logic lives (the DB access, AlertEngine calls,
CAP XML serialization) - matching the same single-source-of-truth
discipline behind the dashboard's earlier migration to POST
/decision/card. The only new thing here is the stable path and, for the
pending-alert endpoints, a formal Pydantic response contract matching
the real pending_alerts schema (src/database/alert_db.py) instead of an
unvalidated dict.

Additive: GET/POST /alerts/... (the original three files) are completely
unchanged and keep working exactly as before.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.auth import verify_api_key
from src.api.routes.alert_review import (
    AssessRequest,
    CancelDecision,
    ExerciseRequest,
    ReviewDecision,
    approve_pending_alert,
    assess_district,
    cancel_pending_alert,
    create_exercise_alert,
    dismiss_pending_alert,
    list_pending_alerts,
)
from src.api.routes.alerts import AlertHistoryResponse, AlertStatsResponse, get_history, get_stats
from src.api.routes.cap_export import export_cap_xml

router = APIRouter(prefix="/alerts", tags=["v1"])


class PendingAlertResponse(BaseModel):
    id: int
    location: str
    score: float
    risk_tier: str
    precipitation: float
    message: str
    status: str
    created_at: str
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    severity: Optional[str] = None
    urgency: Optional[str] = None
    certainty: Optional[str] = None
    cap_status: Optional[str] = None
    affected_communities: List[str] = []
    response_guidance: Optional[str] = None
    basis: Optional[str] = None


class PendingAlertListResponse(BaseModel):
    count: int
    alerts: List[PendingAlertResponse]


@router.post("/assess", dependencies=[Depends(verify_api_key)])
async def v1_assess(request: AssessRequest):
    return await assess_district(request)


@router.post("/exercise", dependencies=[Depends(verify_api_key)])
async def v1_exercise(request: ExerciseRequest):
    return await create_exercise_alert(request)


@router.get("/pending", response_model=PendingAlertListResponse)
async def v1_list_pending(status: str = "pending"):
    return await list_pending_alerts(status=status)


@router.post("/pending/{alert_id}/approve", dependencies=[Depends(verify_api_key)])
async def v1_approve(alert_id: int, decision: ReviewDecision):
    return await approve_pending_alert(alert_id, decision)


@router.post("/pending/{alert_id}/cancel", dependencies=[Depends(verify_api_key)])
async def v1_cancel(alert_id: int, decision: CancelDecision):
    return await cancel_pending_alert(alert_id, decision)


@router.post("/pending/{alert_id}/dismiss", dependencies=[Depends(verify_api_key)])
async def v1_dismiss(alert_id: int, decision: ReviewDecision):
    return await dismiss_pending_alert(alert_id, decision)


@router.get("/pending/{alert_id}/cap.xml")
async def v1_cap_xml(alert_id: int):
    return await export_cap_xml(alert_id)


@router.get("/history", response_model=AlertHistoryResponse)
async def v1_history(
    limit: int = 50, offset: int = 0, location_filter: Optional[str] = None
):
    return await get_history(limit=limit, offset=offset, location_filter=location_filter)


@router.get("/stats", response_model=AlertStatsResponse)
async def v1_stats(location: Optional[str] = None):
    return await get_stats(location=location)
