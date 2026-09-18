"""GET /v1/districts/{district}/fluvial-risk - real river/dam-driven
flood risk for a district, entirely independent of rainfall
(src/hydrology/fluvial_pathway.py).

Exists so scripts/automated_risk_assessment.py (the actual scheduled
production alerting pipeline) can assess dam/river-driven flood risk
on its own, not only ever through a rainfall number. Real flood
science and real dam-release warning practice both treat rainfall-
driven (pluvial) and dam/river-driven (fluvial) flooding as
independent causal pathways (src/models/multi_source_confidence.py's
module docstring has the citations) - before this endpoint existed, a
pure dam-release flood with zero local rainfall, like Ghana's own real
2023 Akosombo spillage or 2021/2010 Bagre-driven Tamale floods, could
never have crossed this platform's review threshold at all.
"""

from fastapi import APIRouter, HTTPException

from src.exposure.districts import get_district
from src.hydrology.dam_intelligence import get_dam_intelligence_for_district
from src.hydrology.fluvial_pathway import build_fluvial_sources
from src.hydrology.river_level_intelligence import (
    get_river_level_for_district,
    has_river_coverage,
)
from src.models.multi_source_confidence import fuse_sources

router = APIRouter(prefix="/districts", tags=["v1"])


@router.get("/{district}/fluvial-risk")
async def get_fluvial_risk(district: str) -> dict:
    if get_district(district) is None:
        raise HTTPException(
            status_code=404,
            detail=f"'{district}' is not a tracked district. See GET /v1/districts.",
        )

    river_gauge = get_river_level_for_district(district)
    dam_intelligence = get_dam_intelligence_for_district(district)
    sources = build_fluvial_sources(
        river_gauge=river_gauge,
        dam_intelligence=dam_intelligence,
        river_applicable=has_river_coverage(district),
    )
    result = fuse_sources(sources)

    return {
        "district": district,
        "risk_0_100": result.unified_risk,
        "confidence": result.confidence,
        "coverage": result.coverage_factor,
        "agreement": result.agreement_factor,
        "degraded": result.degraded,
        "explanation": result.explanation,
        "present_sources": [r.display_name for r in result.present],
        "missing_sources": [r.display_name for r in result.missing],
    }
