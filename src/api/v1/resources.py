"""GET /v1/districts/{district}/resources - operational resources: real
named shelter candidates, real dam disclosure, and real infrastructure
exposure counts, on their own contract instead of scattered across
/situation's larger response.

Deliberately excludes rescue_boats/ambulances/pumps/rescue_teams -
hackathon/app/pages/dashboard.py's DashboardState carries those as fixed
illustrative defaults (rescue_boats=3, ambulances=5, ...) with no real
inventory/dispatch system behind them anywhere in this codebase. Listing
them here as if they were a real "operational resources" contract would
be exactly the fabrication this platform's guardrails work has been
built to eliminate - no emergency-resource inventory system exists yet,
so this endpoint doesn't invent one.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.api.routes.situation import SituationRequest, get_situation
from src.exposure.districts import get_district
from src.exposure.shelter_candidates import get_shelter_names

router = APIRouter(prefix="/districts", tags=["v1"])


class DamStatus(BaseModel):
    dam: str
    available: bool
    reason: Optional[str] = None
    water_surface_elevation_m: Optional[float] = None
    uncertainty_m: Optional[float] = None
    observation_date: Optional[str] = None
    age_days: Optional[int] = None
    stale: Optional[bool] = None
    source: Optional[str] = None
    downstream_communities: List[str] = []
    note: Optional[str] = None


class OperationalResourcesResponse(BaseModel):
    district: str
    # Real, named public buildings that could serve as shelters
    # (src/exposure/shelter_candidates.py) - not an officially designated
    # shelter registry (none exists publicly for Ghana).
    shelters: List[str]
    # Real dam disclosure (src/hydrology/dam_intelligence.py) - [] for
    # districts with no known dam exposure.
    dams: List[DamStatus]
    # Real infrastructure exposure counts at the given precipitation
    # level (src/exposure/impact_estimator.py via /situation) - None if
    # the estimate couldn't be computed.
    schools_exposed: Optional[int] = None
    hospitals_exposed: Optional[int] = None
    markets_exposed: Optional[int] = None
    power_substations_affected: Optional[int] = None


@router.get("/{district}/resources", response_model=OperationalResourcesResponse)
async def get_district_resources(
    district: str,
    precipitation_mm: float = Query(
        ..., ge=0, description="Precipitation in mm, used to compute infrastructure exposure"
    ),
) -> OperationalResourcesResponse:
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

    return OperationalResourcesResponse(
        district=district,
        shelters=get_shelter_names(district),
        dams=[DamStatus(**d) for d in situation.get("dam_intelligence", [])],
        schools_exposed=situation.get("schools_exposed"),
        hospitals_exposed=situation.get("hospitals_exposed"),
        markets_exposed=situation.get("markets_exposed"),
        power_substations_affected=situation.get("power_substations_affected"),
    )
