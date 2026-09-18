"""GET /v1/districts/{district}/antecedent-rainfall - real 3-day
rolling sum of observed CHIRPS rainfall for a district
(src/hydrology/antecedent_rainfall.py).

Exists so scripts/automated_risk_assessment.py (runs in GitHub Actions,
no Earth Engine credentials) can fetch this real, validated signal over
plain HTTP instead of needing its own EE auth - every real Earth Engine
call in this platform happens server-side, inside this Cloud Run
service, where auth already works via ADC.
"""

from fastapi import APIRouter, HTTPException

from src.hydrology.antecedent_rainfall import get_antecedent_rainfall

router = APIRouter(prefix="/districts", tags=["v1"])


@router.get("/{district}/antecedent-rainfall")
async def get_district_antecedent_rainfall(district: str) -> dict:
    result = get_antecedent_rainfall(district)
    if not result["available"] and "not one of the 9 districts" in result.get("reason", ""):
        raise HTTPException(status_code=404, detail=result["reason"])
    return result
