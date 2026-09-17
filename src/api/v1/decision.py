"""GET /v1/districts/{district}/decision - the AI Decision Engine's
structured DecisionCard output, on the same resource-oriented path
pattern as risk/forecast/evidence/resources (district in the path,
precipitation_mm as a query parameter) rather than POST /decision/card's
{location, precipitation} request body.

Thin wrapper: calls the exact same get_decision_card()
(src/api/routes/decision_card.py) - one DecisionCard implementation, not
two. GET rather than POST because decision_card.py's own docstring is
explicit that this "has no side effects and never calls AlertEngine" -
it's a pure computed read, so GET is the correct verb here even though
the original endpoint (kept as POST, unchanged, for backward
compatibility) predates this /v1 pattern.
"""

from fastapi import APIRouter, HTTPException, Query

from src.api.routes.decision_card import DecisionCard, DecisionCardRequest, get_decision_card
from src.exposure.districts import get_district

router = APIRouter(prefix="/districts", tags=["v1"])


@router.get("/{district}/decision", response_model=DecisionCard)
async def get_district_decision(
    district: str,
    precipitation_mm: float = Query(..., ge=0, description="Precipitation in mm"),
) -> DecisionCard:
    if get_district(district) is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"'{district}' is not a tracked district. "
                "See GET /v1/districts for the full list."
            ),
        )
    return await get_decision_card(
        DecisionCardRequest(location=district, precipitation=precipitation_mm)
    )
