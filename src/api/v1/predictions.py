"""POST/GET /v1/predictions - the prediction ledger (src/database/
prediction_ledger_db.py): what happened, where, when, what the system
predicted, why, and - once known - what eventually happened. The
"Database design" foundation this platform previously had no answer
for at all.

POST /v1/predictions/record exists for scripts/automated_risk_
assessment.py to call once per district per scheduled run, logging a
full real snapshot (the district's /decision/card response at that
moment) - the same reason every other write-path in this database is
an API endpoint, not a direct DB write: that script runs outside this
container.

POST /v1/predictions/{id}/outcome fills in the "what eventually
happened" half, later, once real - a human curator confirming a real
flood (or its absence) from news reports, satellite confirmation, or
verified citizen reports crossing a real threshold. Never guessed or
auto-filled; a NULL outcome (the default) is an honest "not yet known".
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.auth import verify_api_key
from src.database.prediction_ledger_db import (
    get_prediction,
    get_predictions,
    record_outcome,
    save_prediction,
)
from src.exposure.districts import get_district
from src.verification.outcome_verifier import verify_outcome

router = APIRouter(prefix="/predictions", tags=["v1"])


class PredictionRecord(BaseModel):
    id: int
    district: str
    predicted_at: str
    evidence_snapshot: Dict[str, Any]
    risk_score: Optional[float] = None
    risk_tier: Optional[str] = None
    fused_risk_score: Optional[float] = None
    fused_risk_tier: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    risk_attribution: Optional[str] = None
    outcome: Optional[str] = None
    outcome_source: Optional[str] = None
    outcome_recorded_at: Optional[str] = None


class RecordPredictionRequest(BaseModel):
    district: str
    evidence_snapshot: Dict[str, Any] = Field(
        ..., description="Real evidence at prediction time - a /decision/card response is the intended shape"
    )
    risk_score: Optional[float] = None
    risk_tier: Optional[str] = None
    fused_risk_score: Optional[float] = None
    fused_risk_tier: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    risk_attribution: Optional[str] = None


class RecordOutcomeRequest(BaseModel):
    outcome: str = Field(
        ..., description="e.g. 'flood_confirmed', 'no_flood_confirmed' - a real, known outcome, never guessed"
    )
    outcome_source: str = Field(
        ..., description="e.g. 'news_report', 'verified_citizen_reports', 'documented_event', 'manual_review'"
    )


class PredictionListResponse(BaseModel):
    count: int
    predictions: List[PredictionRecord]


@router.post("/record", response_model=PredictionRecord, dependencies=[Depends(verify_api_key)])
async def record_prediction(request: RecordPredictionRequest) -> PredictionRecord:
    if get_district(request.district) is None:
        raise HTTPException(
            status_code=404,
            detail=f"'{request.district}' is not a tracked district. See GET /v1/districts.",
        )
    saved = save_prediction(
        district=request.district,
        evidence_snapshot=request.evidence_snapshot,
        risk_score=request.risk_score,
        risk_tier=request.risk_tier,
        fused_risk_score=request.fused_risk_score,
        fused_risk_tier=request.fused_risk_tier,
        confidence=request.confidence,
        reason=request.reason,
        risk_attribution=request.risk_attribution,
    )
    return PredictionRecord(
        id=saved["id"],
        district=request.district,
        predicted_at=saved["predicted_at"],
        evidence_snapshot=request.evidence_snapshot,
        risk_score=request.risk_score,
        risk_tier=request.risk_tier,
        fused_risk_score=request.fused_risk_score,
        fused_risk_tier=request.fused_risk_tier,
        confidence=request.confidence,
        reason=request.reason,
        risk_attribution=request.risk_attribution,
    )


@router.get("", response_model=PredictionListResponse)
async def list_predictions(
    district: Optional[str] = None, outcome: Optional[str] = None, limit: int = 100
) -> PredictionListResponse:
    rows = get_predictions(district=district, outcome=outcome, limit=limit)
    return PredictionListResponse(count=len(rows), predictions=rows)


@router.get("/{prediction_id}", response_model=PredictionRecord)
async def get_one_prediction(prediction_id: int) -> PredictionRecord:
    row = get_prediction(prediction_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No prediction #{prediction_id}")
    return row


@router.post("/{prediction_id}/outcome", response_model=PredictionRecord, dependencies=[Depends(verify_api_key)])
async def record_prediction_outcome(
    prediction_id: int, request: RecordOutcomeRequest
) -> PredictionRecord:
    success = record_outcome(prediction_id, request.outcome, request.outcome_source)
    if not success:
        raise HTTPException(status_code=404, detail=f"No prediction #{prediction_id}")
    return get_prediction(prediction_id)


@router.post("/{prediction_id}/auto-verify", dependencies=[Depends(verify_api_key)])
async def auto_verify_prediction(prediction_id: int) -> dict:
    """Runs the real automated outcome check (src/verification/
    outcome_verifier.py - ReliefWeb, GDELT, verified citizen reports,
    Sentinel-1 SAR) for this prediction and records the result -
    replacing what was previously a fully manual curation step.

    Must run server-side, not from scripts/verify_predictions.py
    directly: the verifier calls real Earth Engine (Sentinel-1) and
    this platform's own SQLite database (verified citizen reports),
    both of which only work inside this Cloud Run service's own
    identity/filesystem, the same reason every other Earth-Engine- or
    DB-touching operation in this platform is server-side with the
    scheduled scripts calling it over HTTP."""
    prediction = get_prediction(prediction_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail=f"No prediction #{prediction_id}")

    result = verify_outcome(prediction["district"], prediction["predicted_at"])
    record_outcome(prediction_id, result["outcome"], result["outcome_source"])

    return {
        "prediction_id": prediction_id,
        "verification": result,
        "prediction": get_prediction(prediction_id),
    }
