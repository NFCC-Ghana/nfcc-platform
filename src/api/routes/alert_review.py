"""Human-in-the-loop alert review queue.

Before this existed, AlertEngine.process() sent real alerts the instant a
score crossed threshold, with no human step anywhere in the code - the
opposite of the intended NFCC workflow: automated data gathering -> risk
assessment displayed for a human to review -> human explicitly triggers
dissemination.

POST /alerts/assess is the automated side (called on a schedule by
scripts/automated_risk_assessment.py via
.github/workflows/automated_risk_assessment.yml, using real current
rainfall from Open-Meteo per src/hydrology/weather_forecast.py) - it
computes a real score/tier and queues a pending_alerts row instead of
sending anything. GET /alerts/pending, POST .../approve, and POST
.../dismiss are the human review side, meant to back a dashboard screen
(hackathon/app/pages/dashboard.py's Alert Review Queue).

Storage note: pending_alerts lives in the same SQLite file as the rest of
this app's alert history (src/database/alert_db.py), which sits on Cloud
Run's ephemeral filesystem - a pending item can be lost if the container
instance scales to zero before a human reviews it. Fine for now (matches
how every other table in this app already persists), but worth knowing if
this queue needs to be reliably durable: either keep at least one Cloud
Run instance always running (--min-instances=1) or move this table to a
persistent store (Firestore/Cloud SQL) later.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.alerts.engine import AlertEngine
from src.alerts.formatter import calculate_score, get_risk_tier
from src.database.alert_db import (
    get_pending_alert,
    get_pending_alerts,
    save_pending_alert,
    update_pending_alert_status,
)

logger = logging.getLogger("nfcc-api.alert-review")

router = APIRouter(prefix="/alerts", tags=["alert-review"])

# Matches AlertEngine.THRESHOLDS["MODERATE"][0] and
# src/alerts/formatter.py:get_risk_tier's own LOW/MODERATE boundary - an
# assessment below this doesn't warrant a human's attention at all.
_REVIEW_THRESHOLD = 30

_DEFAULT_MESSAGES = {
    "MODERATE": "Moderate flood risk. Monitor conditions.",
    "HIGH": "High flood risk. Take precautions.",
    "CRITICAL": "CRITICAL flood risk. Immediate action required.",
    "EXTREME": "EXTREME flood risk. Emergency response needed.",
}


class AssessRequest(BaseModel):
    location: str = Field(..., description="District location")
    precipitation: float = Field(..., description="Precipitation in mm", ge=0)


class ReviewDecision(BaseModel):
    reviewed_by: str = Field(
        default="dashboard", description="Who made this decision"
    )


@router.post("/assess")
async def assess_district(request: AssessRequest):
    """Run a real risk assessment and, if it's at least MODERATE, queue it
    for human review - never sends anything itself."""
    score = calculate_score(request.precipitation)
    risk_tier = get_risk_tier(score)

    if score < _REVIEW_THRESHOLD:
        return {
            "queued": False,
            "location": request.location,
            "score": score,
            "risk_tier": risk_tier,
            "reason": f"Score {score} below review threshold ({_REVIEW_THRESHOLD})",
        }

    message = _DEFAULT_MESSAGES.get(risk_tier, "Flood alert issued.")
    alert_id = save_pending_alert(
        location=request.location,
        score=score,
        risk_tier=risk_tier,
        precipitation=request.precipitation,
        message=message,
    )
    logger.info(
        f"Queued pending alert #{alert_id} for {request.location} "
        f"(score={score}, tier={risk_tier})"
    )
    return {
        "queued": True,
        "id": alert_id,
        "location": request.location,
        "score": score,
        "risk_tier": risk_tier,
        "message": message,
    }


@router.get("/pending")
async def list_pending_alerts(status: str = "pending"):
    """List review-queue alerts. status='all' returns every status."""
    alerts = get_pending_alerts(status=None if status == "all" else status)
    return {"count": len(alerts), "alerts": alerts}


@router.post("/pending/{alert_id}/approve")
async def approve_pending_alert(alert_id: int, decision: ReviewDecision):
    """Human approves a queued assessment - this is the one place a real
    alert actually gets sent as a result of automated assessment."""
    pending = get_pending_alert(alert_id)
    if pending is None:
        raise HTTPException(status_code=404, detail=f"No pending alert #{alert_id}")
    if pending["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Alert #{alert_id} already {pending['status']}",
        )

    from src.api.main import alert_engine as global_alert_engine

    engine = global_alert_engine or AlertEngine()
    result = engine.process(
        location=pending["location"],
        score=pending["score"],
        force=True,
        precipitation=pending["precipitation"],
        message=pending["message"],
    )

    update_pending_alert_status(alert_id, "approved", decision.reviewed_by)
    logger.warning(
        f"Pending alert #{alert_id} APPROVED by {decision.reviewed_by} - "
        f"send result: {result.get('alert_sent')}"
    )
    return {"id": alert_id, "status": "approved", "send_result": result}


@router.post("/pending/{alert_id}/dismiss")
async def dismiss_pending_alert(alert_id: int, decision: ReviewDecision):
    """Human dismisses a queued assessment - nothing gets sent."""
    pending = get_pending_alert(alert_id)
    if pending is None:
        raise HTTPException(status_code=404, detail=f"No pending alert #{alert_id}")
    if pending["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Alert #{alert_id} already {pending['status']}",
        )

    update_pending_alert_status(alert_id, "dismissed", decision.reviewed_by)
    logger.info(f"Pending alert #{alert_id} dismissed by {decision.reviewed_by}")
    return {"id": alert_id, "status": "dismissed"}
