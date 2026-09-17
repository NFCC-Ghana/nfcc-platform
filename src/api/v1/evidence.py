"""GET /v1/districts/{district}/evidence - the evidence array on its own
contract, independently fetchable instead of only reachable embedded
inside POST /decision/card's larger response.

Calls the exact same build_evidence() (src/api/routes/decision_card.py)
that POST /decision/card uses - one evidence-gathering implementation,
not two that could drift the way this platform's district lists and
lead-time tables already have before being consolidated.
"""

from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.api.routes.decision_card import EvidenceItem, build_evidence
from src.api.routes.situation import SituationRequest, get_situation
from src.exposure.districts import get_district

router = APIRouter(prefix="/districts", tags=["v1"])


class EvidenceResponse(BaseModel):
    district: str
    risk_tier: str
    evidence: List[EvidenceItem]
    reason: str
    data_gaps: List[str]


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

    situation = await get_situation(
        SituationRequest(location=district, precipitation=precipitation_mm)
    )
    tier = situation.get("risk_tier", "LOW")
    evidence, reason, data_gaps, _sat_confirmed, _verified = build_evidence(tier, situation)

    return EvidenceResponse(
        district=district,
        risk_tier=tier,
        evidence=evidence,
        reason=reason,
        data_gaps=data_gaps,
    )
