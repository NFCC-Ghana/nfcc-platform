"""GET /v1/districts and GET /v1/districts/{district} - the stable,
versioned district-level data contract (see src/exposure/districts.py
for the canonical registry this reads from).

This is the FIRST /v1 contract, establishing the pattern the other
requested contracts (risk/forecast/alerts/evidence/resources/decision/
history/health) will follow: a Pydantic response_model (so the OpenAPI
schema is a real, checked contract, not just "whatever the code happens
to return"), and no dependency on which adapter (real vs. simulated)
supplied the underlying data - that choice happens below this layer, so
production data can replace simulated data without this contract, or
anything consuming it, changing shape.

Deliberately additive: GET /districts (src/api/main.py, keyed off the
separate and inconsistent DISTRICT_PROFILES list, which has since
diverged - see src/exposure/districts.py's docstring for specifics) and
GET /national/summary (src/api/routes/situation.py) are UNCHANGED by
this. Nothing that already depends on their exact shape breaks. This is
the corrected contract new consumers should use going forward.
"""

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.exposure.districts import get_district, list_districts

router = APIRouter(prefix="/districts", tags=["v1"])


class DistrictResponse(BaseModel):
    name: str
    region: str
    lat: float
    lon: float
    elevation_m: float
    population: int
    area_km2: float
    communities: List[str]


@router.get("", response_model=List[DistrictResponse])
async def get_districts() -> List[DistrictResponse]:
    """Every district this platform tracks - the real 9 (Accra Central/
    West/East, Tema, Kumasi, Tamale, Cape Coast, Ho, Sunyani), not the
    stale 10-district list (with a since-diverged "Sekondi-Takoradi"
    entry and no relation to any of the other tracked-district data)
    still served by the legacy GET /districts."""
    return [DistrictResponse(**d.__dict__) for d in list_districts()]


@router.get("/{district}", response_model=DistrictResponse)
async def get_district_by_name(district: str) -> DistrictResponse:
    d = get_district(district)
    if d is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"'{district}' is not a tracked district. "
                "See GET /v1/districts for the full list."
            ),
        )
    return DistrictResponse(**d.__dict__)
