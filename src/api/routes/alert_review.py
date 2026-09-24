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
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel, Field

from src.api.auth import approval_key_header, enforce_approval_key, verify_api_key
from src.alerts.engine import AlertEngine
from src.alerts.formatter import calculate_score, get_risk_tier
from src.exposure.community_names import get_affected_communities
from src.exposure.impact_estimator import impact_estimator
from src.hydrology.sentinel_processor import sentinel_processor
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

# Common Alerting Protocol (OASIS CAP standard - the international
# backbone behind FEMA IPAWS, the EU, Japan, Canada's NAAD) classifies
# every alert along three INDEPENDENT axes instead of one collapsed
# score. A reviewer seeing "Severe / Immediate / Observed" has genuinely
# richer decision context than just "78%".
_SEVERITY_BY_TIER = {
    "EXTREME": "Extreme",
    "CRITICAL": "Severe",
    "HIGH": "Moderate",
    "MODERATE": "Minor",
}

# JMA-style tiered response guidance (Japan Meteorological Agency's 5-level
# warning system ties each level to WHICH population segment must act, not
# just a severity label - Level 3 = vulnerable groups start evacuating,
# Level 4 = everyone evacuates, Level 5 = emergency/already occurring).
# Applied here to our existing 4 review-worthy tiers so a reviewer sees
# exactly who needs to move, not just how bad the score is.
_RESPONSE_GUIDANCE_BY_TIER = {
    "EXTREME": (
        "EVACUATE NOW - all residents in the affected communities, "
        "no exceptions. Conditions are life-threatening."
    ),
    "CRITICAL": (
        "EVACUATE NOW - elderly, children, disabled, and pregnant residents "
        "first; all other residents evacuate within hours."
    ),
    "HIGH": (
        "Vulnerable residents (elderly, disabled, young children) should "
        "relocate to higher ground or a shelter now. Other residents "
        "prepare to evacuate and avoid the affected areas."
    ),
    "MODERATE": (
        "Vulnerable residents should monitor conditions closely and "
        "prepare an emergency kit. Evacuation is not yet needed."
    ),
}

# CAP status values this app actually uses (OASIS CAP also defines System/
# Draft, not needed here). 'Exercise' rows practice the full review
# workflow (assess -> queue -> approve -> retract) with AlertEngine.process()
# never once invoked - see approve_pending_alert/cancel_pending_alert.
_CAP_STATUS_ACTUAL = "Actual"
_CAP_STATUS_EXERCISE = "Exercise"


def _urgency_from_lead_time(lead_time_hours: int) -> str:
    """CAP urgency = time available to prepare, not a fixed lookup - real
    lead_time_hours already comes from src/exposure/impact_estimator.py,
    keyed off the same risk tier used everywhere else."""
    if lead_time_hours <= 2:
        return "Immediate"
    if lead_time_hours <= 6:
        return "Expected"
    return "Future"


def _certainty_from_satellite(satellite: dict) -> str:
    """CAP certainty = confidence in the observation/prediction. Real
    Sentinel-1 SAR water detection (src/hydrology/sentinel_processor.py)
    is actual physical evidence, not a forecast - "Observed" per CAP's
    own definition ("determined to have occurred or to be ongoing").
    Falls back to "Likely" (rainfall-forecast-based, not yet confirmed by
    satellite) when Earth Engine isn't reachable or no water is detected
    yet, rather than overclaiming certainty the system doesn't have."""
    if satellite.get("source") == "Sentinel-1 SAR" and satellite.get("water_detected"):
        return "Observed"
    return "Likely"


class AssessRequest(BaseModel):
    location: str = Field(..., description="District location")
    precipitation: float = Field(default=0.0, description="Precipitation in mm", ge=0)
    score_override: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description=(
            "A pre-computed 0-100 risk score, bypassing "
            "calculate_score(precipitation) entirely - for signals that "
            "are already a risk score, not a rainfall depth (e.g. the "
            "fluvial/dam-river pathway, src/hydrology/fluvial_pathway.py: "
            "feeding a dam's WARNING/DANGER/FLOOD-derived risk number "
            "through the rainfall-mm curve would silently distort it, "
            "since that curve was fit to precipitation depths, not risk "
            "points). When set, `precipitation` is not used for scoring "
            "and is stored as-is only for display."
        ),
    )
    exercise: bool = Field(
        default=False,
        description=(
            "CAP status=Exercise - queue this as a drill. Approving an "
            "exercise alert never calls AlertEngine.process(), so no real "
            "message can go out no matter what a reviewer clicks."
        ),
    )
    basis: str = Field(
        default="forecast_next_24h",
        description=(
            "Which real signal this assessment used - 'forecast_next_24h' "
            "(anticipatory rainfall, Open-Meteo), 'antecedent_3d_accumulation' "
            "/'antecedent_3d_observed_fallback' (real rainfall already "
            "fallen, CHIRPS/Open-Meteo), or 'dam_river_pathway' (real "
            "river/dam levels via score_override, independent of local "
            "rainfall - see src/hydrology/fluvial_pathway.py's module "
            "docstring for why dam-driven flooding needs its own signal "
            "rather than only ever being visible through a rainfall "
            "number). Real backtesting "
            "(src/models/rare_event_verification.py) found rainfall "
            "accumulation has meaningfully better rare-event skill (SEDI) "
            "than same-day/forecast-only scoring, so the automated "
            "pipeline assesses every independent signal separately per "
            "district."
        ),
    )


class ReviewDecision(BaseModel):
    reviewed_by: str = Field(default="dashboard", description="Who made this decision")


@router.post("/assess", dependencies=[Depends(verify_api_key)])
async def assess_district(request: AssessRequest):
    """Run a real risk assessment and, if it's at least MODERATE, queue it
    for human review - never sends anything itself."""
    score = (
        request.score_override
        if request.score_override is not None
        else calculate_score(request.precipitation)
    )
    risk_tier = get_risk_tier(score)

    if score < _REVIEW_THRESHOLD:
        return {
            "queued": False,
            "location": request.location,
            "score": score,
            "risk_tier": risk_tier,
            "basis": request.basis,
            "reason": f"Score {score} below review threshold ({_REVIEW_THRESHOLD})",
        }

    message = _DEFAULT_MESSAGES.get(risk_tier, "Flood alert issued.")
    cap_status = _CAP_STATUS_EXERCISE if request.exercise else _CAP_STATUS_ACTUAL
    if request.exercise:
        # CAP's own guidance (used by FEMA IPAWS/EU/Japan) is that an
        # Exercise message must be unambiguously labeled wherever it's
        # displayed, even though this app never lets one reach
        # AlertEngine.process() at all (see approve_pending_alert).
        message = f"EXERCISE - THIS IS A DRILL. {message}"

    # Real severity/urgency/certainty - not fabricated to look
    # standards-compliant. Each falls back honestly if its real source is
    # unavailable rather than raising and losing the assessment entirely.
    severity = _SEVERITY_BY_TIER.get(risk_tier, "Unknown")

    try:
        impact = impact_estimator.estimate_impact(request.location, score, risk_tier)
        urgency = _urgency_from_lead_time(impact.get("lead_time_hours", 24))
    except Exception as e:
        logger.warning(f"Impact estimate failed for urgency calc: {e}")
        urgency = "Future"

    try:
        satellite = sentinel_processor.detect_flood(request.location)
        certainty = _certainty_from_satellite(satellite)
    except Exception as e:
        logger.warning(f"Satellite check failed for certainty calc: {e}")
        certainty = "Likely"

    # Geotargeting: real named communities within the district (not just
    # the district name) and JMA-style guidance on who specifically should
    # act at this tier.
    affected_communities = get_affected_communities(request.location)
    response_guidance = _RESPONSE_GUIDANCE_BY_TIER.get(risk_tier)

    alert_id = save_pending_alert(
        location=request.location,
        score=score,
        risk_tier=risk_tier,
        precipitation=request.precipitation,
        message=message,
        severity=severity,
        urgency=urgency,
        certainty=certainty,
        cap_status=cap_status,
        affected_communities=affected_communities,
        response_guidance=response_guidance,
        basis=request.basis,
    )
    logger.info(
        f"Queued pending alert #{alert_id} for {request.location} "
        f"(score={score}, tier={risk_tier}, basis={request.basis}, "
        f"CAP: {severity}/{urgency}/{certainty}, status={cap_status})"
    )
    return {
        "queued": True,
        "id": alert_id,
        "location": request.location,
        "score": score,
        "risk_tier": risk_tier,
        "message": message,
        "severity": severity,
        "urgency": urgency,
        "certainty": certainty,
        "cap_status": cap_status,
        "affected_communities": affected_communities,
        "response_guidance": response_guidance,
        "basis": request.basis,
    }


class ExerciseRequest(BaseModel):
    location: str = Field(..., description="District location")
    risk_tier: str = Field(
        default="HIGH",
        description="Tier to drill against: MODERATE, HIGH, CRITICAL, or EXTREME",
    )
    message: Optional[str] = Field(
        default=None,
        description="Custom drill scenario text; a default is used if omitted",
    )


@router.post("/exercise", dependencies=[Depends(verify_api_key)])
async def create_exercise_alert(request: ExerciseRequest):
    """Manually queue a training drill for any district/tier on demand -
    unlike /assess, this doesn't wait for real rainfall to cross the
    review threshold, so the team can practice the review workflow
    (assess -> queue -> approve -> retract) at any time. Always
    cap_status='Exercise': approving or cancelling this alert never calls
    AlertEngine.process() (see approve_pending_alert/cancel_pending_alert),
    so no real message can reach anyone no matter what a reviewer clicks."""
    risk_tier = request.risk_tier.upper()
    if risk_tier not in _SEVERITY_BY_TIER:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown risk_tier '{request.risk_tier}' - must be one of "
                f"{list(_SEVERITY_BY_TIER)}"
            ),
        )

    base_message = request.message or _DEFAULT_MESSAGES.get(
        risk_tier, "Flood alert issued."
    )
    message = f"EXERCISE - THIS IS A DRILL. {base_message}"

    # A drill scenario has no real precipitation/impact/satellite reading
    # behind it, so its score is synthetic (midpoint of the tier's band)
    # and certainty is honestly "Likely", never "Observed" - nothing was
    # actually observed, this is a practice run.
    _TIER_MIDPOINT_SCORE = {
        "MODERATE": 40.0,
        "HIGH": 60.0,
        "CRITICAL": 77.0,
        "EXTREME": 92.0,
    }
    score = _TIER_MIDPOINT_SCORE[risk_tier]

    alert_id = save_pending_alert(
        location=request.location,
        score=score,
        risk_tier=risk_tier,
        precipitation=0.0,
        message=message,
        severity=_SEVERITY_BY_TIER[risk_tier],
        urgency="Immediate",
        certainty="Likely",
        cap_status=_CAP_STATUS_EXERCISE,
        affected_communities=get_affected_communities(request.location),
        response_guidance=_RESPONSE_GUIDANCE_BY_TIER.get(risk_tier),
    )
    logger.info(
        f"Queued EXERCISE alert #{alert_id} for {request.location} "
        f"(tier={risk_tier}) - training drill, no real data behind it"
    )
    return {
        "queued": True,
        "id": alert_id,
        "location": request.location,
        "risk_tier": risk_tier,
        "message": message,
        "cap_status": _CAP_STATUS_EXERCISE,
    }


@router.get("/pending")
async def list_pending_alerts(status: str = "pending"):
    """List review-queue alerts. status='all' returns every status."""
    alerts = get_pending_alerts(status=None if status == "all" else status)
    return {"count": len(alerts), "alerts": alerts}


@router.post("/pending/{alert_id}/approve", dependencies=[Depends(verify_api_key)])
async def approve_pending_alert(
    alert_id: int,
    decision: ReviewDecision,
    approval_key: str = Security(approval_key_header),
):
    """Human approves a queued assessment - this is the one place a real
    alert actually gets sent as a result of automated assessment.

    approval_key is checked (via enforce_approval_key, only when
    settings.ALERT_APPROVAL_KEY is configured) below, after fetching
    `pending` - never for an exercise alert, which this function's own
    later branch already guarantees can't send a real message by any
    other path, so requiring a second secret to approve a drill would add
    friction with no matching real-world safety benefit."""
    pending = get_pending_alert(alert_id)
    if pending is None:
        raise HTTPException(status_code=404, detail=f"No pending alert #{alert_id}")
    if pending["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Alert #{alert_id} already {pending['status']}",
        )

    if pending.get("cap_status") == _CAP_STATUS_EXERCISE:
        # Exercise alerts NEVER reach AlertEngine.process() - not even a
        # code path that happens to skip the real provider, an entirely
        # separate branch that never imports or touches the engine. This
        # is the actual safety guarantee: a reviewer clicking Approve on a
        # drill cannot, by any bug elsewhere in AlertEngine, cause a real
        # message to go out.
        result = {
            "alert_sent": False,
            "simulated": True,
            "note": (
                "EXERCISE - no real message was sent. This was a training "
                "drill of the review workflow only."
            ),
        }
        update_pending_alert_status(alert_id, "approved", decision.reviewed_by)
        logger.info(
            f"EXERCISE alert #{alert_id} approved by {decision.reviewed_by} "
            "- simulated, nothing sent"
        )
        return {"id": alert_id, "status": "approved", "send_result": result}

    enforce_approval_key(approval_key)

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


class CancelDecision(BaseModel):
    reviewed_by: str = Field(default="dashboard")
    reason: str = Field(..., description="Why this alert is being retracted/corrected")


@router.post("/pending/{alert_id}/cancel", dependencies=[Depends(verify_api_key)])
async def cancel_pending_alert(
    alert_id: int,
    decision: CancelDecision,
    approval_key: str = Security(approval_key_header),
):
    """Retract an already-sent alert (CAP msgType=Cancel - the OASIS
    Common Alerting Protocol standard behind FEMA IPAWS/EU/Japan/Canada
    treats retraction as a first-class alert type, not an afterthought).

    Directly motivated by South Korea's May 2023 false missile alert: the
    public endured ~20 minutes of confusion partly because there was no
    fast, clear correction message - only silence followed by an
    after-the-fact clarification. This sends a real, immediate correction
    through the same channels/recipients as the original alert, rather
    than just quietly flipping a status flag nobody but this dashboard
    ever sees."""
    pending = get_pending_alert(alert_id)
    if pending is None:
        raise HTTPException(status_code=404, detail=f"No pending alert #{alert_id}")
    if pending["status"] != "approved":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Alert #{alert_id} is {pending['status']}, not approved - "
                "only a sent alert can be retracted"
            ),
        )

    cancel_message = (
        f"CORRECTION - Previous flood alert for {pending['location']} "
        f"has been RETRACTED: {decision.reason}"
    )

    if pending.get("cap_status") == _CAP_STATUS_EXERCISE:
        # Same guarantee as approve_pending_alert - an exercise retraction
        # never touches AlertEngine either.
        result = {
            "alert_sent": False,
            "simulated": True,
            "note": "EXERCISE - no real retraction was sent.",
        }
        update_pending_alert_status(alert_id, "cancelled", decision.reviewed_by)
        logger.info(
            f"EXERCISE alert #{alert_id} cancelled by {decision.reviewed_by} "
            f"(reason: {decision.reason}) - simulated, nothing sent"
        )
        return {
            "id": alert_id,
            "status": "cancelled",
            "reason": decision.reason,
            "retraction_send_result": result,
        }

    enforce_approval_key(approval_key)

    from src.api.main import alert_engine as global_alert_engine

    engine = global_alert_engine or AlertEngine()
    result = engine.process(
        location=pending["location"],
        score=pending["score"],
        force=True,
        precipitation=pending["precipitation"],
        message=cancel_message,
    )

    update_pending_alert_status(alert_id, "cancelled", decision.reviewed_by)
    logger.warning(
        f"Pending alert #{alert_id} CANCELLED by {decision.reviewed_by} "
        f"(reason: {decision.reason}) - retraction send result: "
        f"{result.get('alert_sent')}"
    )
    return {
        "id": alert_id,
        "status": "cancelled",
        "reason": decision.reason,
        "retraction_send_result": result,
    }


@router.post("/pending/{alert_id}/dismiss", dependencies=[Depends(verify_api_key)])
async def dismiss_pending_alert(
    alert_id: int,
    decision: ReviewDecision,
    approval_key: str = Security(approval_key_header),
):
    """Human dismisses a queued assessment - nothing gets sent, but for a
    REAL (non-exercise) pending alert this is still a safety-relevant
    decision, just one of omission rather than commission: someone
    holding only the regular API key could otherwise silently suppress a
    legitimate flood warning before any other human reviewer ever saw it
    queued. Requires the same stronger approval_key as approve/cancel
    when one is configured - except for an exercise alert (the
    stakeholder demo's own Dismiss button uses this same endpoint and
    must keep working without provisioning that second secret)."""
    pending = get_pending_alert(alert_id)
    if pending is None:
        raise HTTPException(status_code=404, detail=f"No pending alert #{alert_id}")
    if pending["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Alert #{alert_id} already {pending['status']}",
        )

    if pending.get("cap_status") != _CAP_STATUS_EXERCISE:
        enforce_approval_key(approval_key)

    update_pending_alert_status(alert_id, "dismissed", decision.reviewed_by)
    logger.info(f"Pending alert #{alert_id} dismissed by {decision.reviewed_by}")
    return {"id": alert_id, "status": "dismissed"}
