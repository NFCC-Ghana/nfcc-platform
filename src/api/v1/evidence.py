"""GET /v1/districts/{district}/evidence - the evidence array on its own
contract, independently fetchable instead of only reachable embedded
inside POST /decision/card's larger response.

Calls the exact same build_evidence() (src/api/routes/decision_card.py)
that POST /decision/card uses - one evidence-gathering implementation,
not two that could drift the way this platform's district lists and
lead-time tables already have before being consolidated. Now also
includes the same real multi-source confidence fusion
(src/models/multi_source_confidence.py) that /decision/card returns -
previously this endpoint had no confidence field at all, forcing a
caller who only wanted evidence to also call /decision/card just to
learn how much to trust it.
"""

from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.api.routes.decision_card import (
    ConfidenceBlock,
    EvidenceItem,
    basis_from_fusion,
    build_confidence,
    build_evidence,
)
from src.api.routes.situation import SituationRequest, _build_situation_response
from src.exposure.districts import get_district

router = APIRouter(prefix="/districts", tags=["v1"])


class EvidenceResponse(BaseModel):
    district: str
    risk_tier: str
    evidence: List[EvidenceItem]
    reason: str
    data_gaps: List[str]
    confidence: ConfidenceBlock


@router.get("/{district}/evidence", response_model=EvidenceResponse)
async def get_district_evidence(
    district: str,
    precipitation_mm: float = Query(..., ge=0, description="Precipitation in mm"),
) -> EvidenceResponse:
    if get_district(district) is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"'{district}' is not a tracked district. "
                "See GET /v1/districts for the full list."
            ),
        )

    situation = await _build_situation_response(
        SituationRequest(location=district, precipitation=precipitation_mm)
    )
    tier = situation.get("risk_tier", "LOW")
    evidence, reason, data_gaps, sat_confirmed, verified = build_evidence(tier, situation)
    fusion = build_confidence(district, situation, sat_confirmed, verified)

    return EvidenceResponse(
        district=district,
        risk_tier=tier,
        evidence=evidence,
        reason=reason,
        data_gaps=data_gaps,
        confidence=ConfidenceBlock(
            value=round(fusion.confidence),
            basis=basis_from_fusion(fusion),
            coverage=fusion.coverage_factor,
            agreement=fusion.agreement_factor,
            degraded=fusion.degraded,
            explanation=fusion.explanation,
        ),
    )
