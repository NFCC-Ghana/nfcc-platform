"""GET /v1/districts/{district}/forecast-fusion - the real, per-district
activation of src/models/forecast_fusion.py's CHIRPS/GloFAS/Flood Hub
fusion math, on its own contract instead of buried inside /situation's
larger response (which also carries it, additively, as
response["forecast_fusion"]).

See src/models/real_forecast_fusion.py's module docstring for the full
picture: this used to be a "disconnected chirps/glofas/flood_hub demo"
(multi_source_confidence.py's own words) that only GET /forecast/
confidence exercised, and only with caller-supplied numbers - nothing in
this codebase computed real ones. This module is that missing real
computation, and this route is its stable versioned contract.
"""

from fastapi import APIRouter, HTTPException

from src.exposure.districts import get_district
from src.models.real_forecast_fusion import get_real_forecast_fusion

router = APIRouter(prefix="/districts", tags=["v1"])


@router.get("/{district}/forecast-fusion")
async def get_district_forecast_fusion(district: str) -> dict:
    if get_district(district) is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"'{district}' is not a tracked district. "
                "See GET /v1/districts for the full list."
            ),
        )
    return get_real_forecast_fusion(district)
