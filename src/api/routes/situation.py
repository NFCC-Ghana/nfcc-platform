"""Situation endpoint - a single consolidated response combining the flood
risk score with hydrology evidence, impact estimates, and community report
stats. Built to feed hackathon/app/pages/dashboard.py's Impact Assessment,
Evidence & Confidence, and Operations panels, which previously always fell
back to static demo numbers because /score never returned any of this.

The risk score/tier here is computed with the exact same
calculate_score()/get_risk_tier() used by /score - this is the one place
those numbers are computed, so every consumer stays consistent. Hydrology,
impact, and community data are all derived FROM that score/tier rather than
letting the underlying modules compute their own independent risk numbers,
to avoid reintroducing the kind of drift just fixed across the dashboard.
"""

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.alerts.formatter import calculate_score, get_risk_tier
from src.community.community_memory import community_memory
from src.exposure.impact_estimator import impact_estimator
from src.hydrology.unified_intelligence import unified_intelligence

logger = logging.getLogger("nfcc-api.situation")

router = APIRouter(tags=["situation"])


class SituationRequest(BaseModel):
    location: str = Field(..., description="District location")
    precipitation: float = Field(..., description="Precipitation in mm", ge=0)


# Economic impact has no calibrated model behind it (impact_estimator only
# estimates population/infrastructure exposure, not GHS losses) - this is a
# simple, transparent per-person estimate, not a real economic model. Kept
# in the same order of magnitude as the dashboard's previous fallback
# formula (hackathon/app/modules/v4/state_fallback.py) for continuity, but
# now driven by the real population_exposed figure instead of a separately
# re-derived one.
_GHS_LOSS_PER_PERSON = 2500
_RESIDENTIAL_SHARE = 0.55
_INFRASTRUCTURE_SHARE = 0.30
_AGRICULTURE_SHARE = 0.15


def _estimate_economic_loss(population_exposed: int, rainfall_mm: float) -> dict:
    rainfall_factor = min(1.0, rainfall_mm / 100)
    total = population_exposed * _GHS_LOSS_PER_PERSON * rainfall_factor
    return {
        "residential_loss_ghs": round(total * _RESIDENTIAL_SHARE, 2),
        "infrastructure_loss_ghs": round(total * _INFRASTRUCTURE_SHARE, 2),
        "agricultural_loss_ghs": round(total * _AGRICULTURE_SHARE, 2),
        "total_loss_ghs": round(total, 2),
    }


@router.post("/situation")
async def get_situation(request: SituationRequest):
    """Full situation assessment for a district: risk score, hydrology
    evidence (rainfall/river/soil/dam), population and infrastructure
    impact estimates, a simple economic loss estimate, and community
    report stats - everything the dashboard's non-header panels need,
    computed from real district data instead of static placeholders."""

    score = calculate_score(request.precipitation)
    risk_tier = get_risk_tier(score)

    try:
        hydrology = unified_intelligence.get_complete_risk_assessment(
            request.location, request.precipitation
        )
    except Exception as e:
        logger.error(f"Hydrology assessment failed for {request.location}: {e}")
        hydrology = None

    try:
        impact = impact_estimator.estimate_impact(request.location, score, risk_tier)
        if "error" in impact:
            logger.warning(f"Impact estimate error: {impact['error']}")
            impact = None
    except Exception as e:
        logger.error(f"Impact estimate failed for {request.location}: {e}")
        impact = None

    try:
        report_stats = community_memory.get_report_stats(request.location)
    except Exception as e:
        logger.error(f"Report stats failed for {request.location}: {e}")
        report_stats = {"total_reports": 0, "validated_reports": 0}

    response = {
        "location": request.location,
        "score": score,
        "risk_tier": risk_tier,
        "total_reports": report_stats.get("total_reports", 0),
        "verified_reports": report_stats.get("validated_reports", 0),
    }

    if impact:
        population_exposed = impact["population_exposed"]
        response.update(
            {
                "population_total": impact["population_total"],
                "population_exposed": population_exposed,
                "exposure_percentage": impact["exposure_percentage"],
                "children_exposed": impact["children_exposed"],
                "elderly_exposed": impact["elderly_exposed"],
                "households_affected": int(population_exposed / 4),
                "schools_exposed": impact["schools_exposed"],
                "hospitals_exposed": impact["hospitals_exposed"],
                "markets_exposed": impact["markets_exposed"],
                # impact_estimator doesn't model power infrastructure at
                # all - same rough population-based heuristic the
                # dashboard's old fallback used, not real substation data.
                "power_substations_affected": max(
                    1, int(impact["population_total"] / 75000)
                ),
                "lead_time_hours": impact["lead_time_hours"],
                "lead_time_action": impact["lead_time_action"],
                "area_km2": impact["area_km2"],
            }
        )
        response.update(
            _estimate_economic_loss(population_exposed, request.precipitation)
        )

    if hydrology:
        response["rainfall_mm"] = request.precipitation
        response["river_level_m"] = hydrology["river"].get("current_level_m", 0)
        response["soil_saturation_percent"] = hydrology["soil"].get(
            "saturation_percent", 0
        )
        response["recommendations"] = hydrology.get("recommendations", [])

    return response
