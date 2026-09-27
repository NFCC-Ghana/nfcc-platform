"""GET /v1/districts/{district}/risk - the FLOOD RISK ENGINE contract,
on its own instead of buried inside /situation's larger blob.

Wraps the exact same calculate_score()/get_risk_tier()
(src/alerts/formatter.py) every other consumer already uses (POST
/situation, POST /decision/card, POST /alerts/assess) - this endpoint
adds no new scoring behavior, it gives the existing one a clean,
independently-fetchable, versioned contract.

Scoring is currently district-agnostic (a pure function of
precipitation): src/alerts/district_risk.py used to have a real
calculate_adjusted_score()/should_alert_for_district() pair that DID
adjust per district, but it was never called anywhere in the live
pipeline and carried its own uncited, since-diverged 7-district list;
deleted 2026-09-27 along with the equally-dead GET /districts route that
was its only other reference. District-adjusted thresholds remain a
separate, real feature to build properly (against the canonical 9-
district registry, src/exposure/districts.py) if wanted later, not
something worth resurrecting the old module for.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.alerts.formatter import calculate_score, get_risk_tier
from src.exposure.districts import get_district

router = APIRouter(prefix="/districts", tags=["v1"])


class RiskResponse(BaseModel):
    district: str
    precipitation_mm: float
    score: float
    risk_tier: str
    computed_at: str
    method: str = (
        "src/alerts/formatter.py:calculate_score - deterministic threshold model"
    )


@router.get("/{district}/risk", response_model=RiskResponse)
async def get_district_risk(
    district: str,
    precipitation_mm: float = Query(..., ge=0, description="Precipitation in mm"),
) -> RiskResponse:
    if get_district(district) is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"'{district}' is not a tracked district. "
                "See GET /v1/districts for the full list."
            ),
        )

    score = calculate_score(precipitation_mm)
    risk_tier = get_risk_tier(score)

    return RiskResponse(
        district=district,
        precipitation_mm=precipitation_mm,
        score=score,
        risk_tier=risk_tier,
        computed_at=datetime.now(timezone.utc).isoformat(),
    )
