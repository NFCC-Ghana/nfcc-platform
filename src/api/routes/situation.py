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

import requests
from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.alerts.formatter import calculate_score, get_risk_tier
from src.community.community_memory import community_memory
from src.exposure.impact_estimator import impact_estimator
from src.exposure.shelter_candidates import get_shelter_names
from src.hydrology.dam_intelligence import get_dam_intelligence_for_district
from src.hydrology.unified_intelligence import unified_intelligence
from src.hydrology.weather_forecast import weather_forecast

logger = logging.getLogger("nfcc-api.situation")

router = APIRouter(tags=["situation"])

_FLOOD_API_URL = "https://flood-api.open-meteo.com/v1/flood"
# A district counts as an "active flood zone" when today's simulated river
# discharge (Open-Meteo's GloFAS-based Flood API - real river gauge data
# doesn't exist anywhere in the codebase; src/hydrology/river_gauge_api.py's
# configured endpoint, hydrology.gov.gh, doesn't resolve) is running well
# above its long-term seasonal mean for that day. 1.5x is an illustrative
# threshold, not a calibrated hydrological one - no flood-stage threshold
# per Ghana river exists publicly.
_ELEVATED_DISCHARGE_RATIO = 1.5


def _is_district_flood_zone_active(lat: float, lon: float) -> Optional[bool]:
    """True if a district's real-time river discharge is elevated relative
    to its seasonal mean; None if the Flood API call failed."""
    try:
        resp = requests.get(
            _FLOOD_API_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "river_discharge,river_discharge_mean",
                "forecast_days": 1,
            },
            timeout=8,
        )
        resp.raise_for_status()
        daily = resp.json().get("daily", {})
        discharge = daily.get("river_discharge", [])
        mean = daily.get("river_discharge_mean", [])
        # Open-Meteo returns null for either value at some coastal points
        # where no river is resolved within their 5km grid (documented
        # limitation, not an error) - Cape Coast hits this in practice.
        if not discharge or not mean:
            return None
        latest_discharge, latest_mean = discharge[-1], mean[-1]
        if latest_discharge is None or not latest_mean:
            return None
        return latest_discharge > _ELEVATED_DISCHARGE_RATIO * latest_mean
    except Exception as e:
        logger.warning(f"Flood API call failed for ({lat},{lon}): {e}")
        return None


@router.get("/national/summary")
async def get_national_summary():
    """District count and a real, computed "active flood zones" count
    (river discharge vs. seasonal mean, via Open-Meteo's Flood API) across
    every district this app tracks - was previously a hardcoded "10
    districts / 3 zones" with no data behind either number. Independent of
    which single district is selected in the dashboard, so this is its own
    endpoint rather than folded into /situation."""

    results = {}
    for district, coords in weather_forecast.district_coords.items():
        results[district] = _is_district_flood_zone_active(
            coords["lat"], coords["lon"]
        )

    active = [d for d, is_active in results.items() if is_active]
    checked = [d for d, is_active in results.items() if is_active is not None]

    return {
        "district_count": len(weather_forecast.district_coords),
        "active_flood_zones": len(active),
        "active_flood_zone_districts": active,
        "districts_checked": len(checked),
        "source": "open-meteo-flood-api",
    }


class SituationRequest(BaseModel):
    location: str = Field(..., description="District location")
    precipitation: float = Field(..., description="Precipitation in mm", ge=0)


# Economic impact has no calibrated model behind it anywhere in the
# codebase - impact_estimator only estimates *exposure counts*
# (households/schools/hospitals/markets), not GHS losses. This is a simple,
# transparent, asset-based estimate (illustrative per-unit costs x real
# exposed counts), not a real economic model - it replaced an earlier,
# cruder version that just split one population-derived total three ways
# by fixed ratios, which meant residential/infrastructure/agricultural loss
# always moved in lockstep and never actually reflected how many schools,
# hospitals, or markets were really exposed in a given district.
_GHS_PER_HOUSEHOLD = 8_000  # flood repair/replacement: structure + contents
_GHS_PER_SCHOOL = 400_000  # building + equipment
_GHS_PER_HOSPITAL = 1_500_000  # building + critical medical equipment
_GHS_PER_MARKET = 250_000  # stalls + goods
_GHS_PER_SUBSTATION = 800_000  # electrical infrastructure
_GHS_PER_KM2_AGRICULTURE = 300_000  # at full rainfall intensity


def _estimate_economic_loss(
    households_affected: int,
    schools_exposed: int,
    hospitals_exposed: int,
    markets_exposed: int,
    power_substations_affected: int,
    area_km2: float,
    rainfall_mm: float,
) -> dict:
    rainfall_factor = min(1.0, rainfall_mm / 100)

    residential = households_affected * _GHS_PER_HOUSEHOLD
    infrastructure = (
        schools_exposed * _GHS_PER_SCHOOL
        + hospitals_exposed * _GHS_PER_HOSPITAL
        + markets_exposed * _GHS_PER_MARKET
        + power_substations_affected * _GHS_PER_SUBSTATION
    )
    agricultural = area_km2 * _GHS_PER_KM2_AGRICULTURE * rainfall_factor

    return {
        "residential_loss_ghs": round(residential, 2),
        "infrastructure_loss_ghs": round(infrastructure, 2),
        "agricultural_loss_ghs": round(agricultural, 2),
        "total_loss_ghs": round(residential + infrastructure + agricultural, 2),
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
        # Real, named public buildings per district (see
        # src/exposure/shelter_candidates.py) - not an officially
        # designated shelter registry (none exists publicly for Ghana),
        # but genuine places, not generic "{district} Senior High School"
        # placeholder text repeated for every district.
        "shelter_names": get_shelter_names(request.location),
        # Honest dam/reservoir disclosure (src/hydrology/dam_intelligence.py)
        # for the 3 tracked districts genuinely downstream of a dam this
        # platform knows about - [] for the other 6. Each entry is either
        # real data (Akosombo, if DAHITI_API_KEY is configured) or an
        # explicit available=False with the real reason no live feed
        # exists, never a fabricated reservoir level.
        "dam_intelligence": get_dam_intelligence_for_district(request.location),
    }

    if impact:
        population_exposed = impact["population_exposed"]
        households_affected = int(population_exposed / 4)
        # impact_estimator doesn't model power infrastructure at all - same
        # rough population-based heuristic the dashboard's old fallback
        # used, not real substation data.
        power_substations_affected = max(1, int(impact["population_total"] / 75000))

        response.update(
            {
                "population_total": impact["population_total"],
                "population_exposed": population_exposed,
                "exposure_percentage": impact["exposure_percentage"],
                "children_exposed": impact["children_exposed"],
                "elderly_exposed": impact["elderly_exposed"],
                "households_affected": households_affected,
                "schools_exposed": impact["schools_exposed"],
                "hospitals_exposed": impact["hospitals_exposed"],
                "markets_exposed": impact["markets_exposed"],
                "power_substations_affected": power_substations_affected,
                "lead_time_hours": impact["lead_time_hours"],
                "lead_time_action": impact["lead_time_action"],
                "area_km2": impact["area_km2"],
            }
        )
        response.update(
            _estimate_economic_loss(
                households_affected=households_affected,
                schools_exposed=impact["schools_exposed"],
                hospitals_exposed=impact["hospitals_exposed"],
                markets_exposed=impact["markets_exposed"],
                power_substations_affected=power_substations_affected,
                area_km2=impact["area_km2"],
                rainfall_mm=request.precipitation,
            )
        )

    if hydrology:
        response["rainfall_mm"] = request.precipitation
        response["river_level_m"] = hydrology["river"].get("current_level_m", 0)
        response["soil_saturation_percent"] = hydrology["soil"].get(
            "saturation_percent", 0
        )
        response["recommendations"] = hydrology.get("recommendations", [])
        # Real Sentinel-1 SAR satellite flood detection (Google Earth
        # Engine, via src/hydrology/sentinel_processor.py) when reachable;
        # satellite["source"] says "Sentinel-1 SAR" for a real detection
        # or "Sentinel-1 (simulated)"/"(unavailable)" otherwise - always
        # check this field before treating the numbers as real.
        response["satellite"] = hydrology.get("satellite", {})

    # Risk timeline: real Open-Meteo forecast rainfall (see
    # src/hydrology/weather_forecast.py), layered on top of the current
    # precipitation input and scored through the same calculate_score()
    # used everywhere else - "now" always matches the score above exactly;
    # future points show what the real forecast implies is coming, instead
    # of a fixed +15/+10/+5 synthetic offset with no forecast behind it at
    # all (the dashboard's old behavior).
    try:
        forecast = weather_forecast.get_forecast_for_district(request.location)
        cumulative = forecast.get("cumulative_6h", {})
        timeline = [{"hour": "Now", "score": score, "risk_tier": risk_tier}]
        for h in [6, 12, 18, 24]:
            future_precip = request.precipitation + cumulative.get(str(h), 0.0)
            future_score = calculate_score(future_precip)
            timeline.append(
                {
                    "hour": f"{h}h",
                    "score": future_score,
                    "risk_tier": get_risk_tier(future_score),
                }
            )
        response["risk_timeline"] = timeline
        response["forecast_24h_mm"] = forecast.get("24h", 0.0)
        response["forecast_48h_mm"] = forecast.get("48h", 0.0)
        response["forecast_72h_mm"] = forecast.get("72h", 0.0)
        response["forecast_source"] = forecast.get("source", "unknown")
    except Exception as e:
        logger.error(f"Weather forecast failed for {request.location}: {e}")

    return response
