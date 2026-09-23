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
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from src.api.auth import limiter, verify_api_key
from src.alerts.formatter import calculate_score, get_risk_tier
from src.community.community_memory import community_memory
from src.exposure.impact_estimator import impact_estimator
from src.exposure.shelter_candidates import get_shelter_names
from src.hydrology.dam_intelligence import get_dam_intelligence_for_district
from src.hydrology.river_level_intelligence import get_river_level_for_district
from src.hydrology.sentinel_processor import sentinel_processor
from src.hydrology.smap_soil_moisture import get_soil_moisture_for_district
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
        results[district] = _is_district_flood_zone_active(coords["lat"], coords["lon"])

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


async def _build_situation_response(body: SituationRequest) -> dict:
    """Full situation assessment for a district: risk score, hydrology
    evidence (rainfall/river/soil/dam), population and infrastructure
    impact estimates, a simple economic loss estimate, and community
    report stats - everything the dashboard's non-header panels need,
    computed from real district data instead of static placeholders.

    score includes a real urban-drainage adjustment
    (src/hydrology/urban_drainage.py via calculate_score's district
    param) - a neutral 1.0x for the districts this module has no real
    data on, currently a real >1.0x for Accra Central/West/East's known
    poor/blocked drainage. Deliberately NOT yet applied to
    src/api/routes/alert_review.py's /alerts/assess (the real automated
    alert-triggering path) - that's a separate, more consequential
    decision (it changes when a real evacuation alert fires) left for
    an explicit choice rather than silently folded in here.

    The real business logic, deliberately separate from the /situation
    HTTP route below it - src/api/routes/decision_card.py's
    get_decision_card() reuses this directly as a plain function call
    (no real HTTP request involved), which broke when a rate-limit
    decorator requiring a genuine starlette.Request first appeared on
    the route version of this function. Routes call this; nothing else
    should call the route function directly."""

    score = calculate_score(body.precipitation, district=body.location)
    risk_tier = get_risk_tier(score)

    try:
        # Direct call, not through unified_intelligence.get_complete_risk_
        # assessment() - that function's only genuinely live-used output
        # was this same satellite dict (see response["satellite"] below);
        # everything else it computed (rainfall_history, river_intelligence,
        # reservoir_intelligence, soil_moisture - all four fabricate via
        # random.seed(hash(...)), undisclosed, since none of their output
        # ever reached a response) plus a whole second, independent
        # composite_risk score/tier were being computed from scratch on
        # every single /situation call and immediately discarded. Found
        # during a codebase-wide audit for exactly the pattern this file's
        # own module docstring warns against: "avoid reintroducing the
        # kind of drift just fixed" by letting a module compute its own
        # independent risk number nothing uses.
        satellite = sentinel_processor.detect_flood(body.location)
    except Exception as e:
        logger.error(f"Satellite detection failed for {body.location}: {e}")
        satellite = None

    try:
        impact = impact_estimator.estimate_impact(body.location, score, risk_tier)
        if "error" in impact:
            logger.warning(f"Impact estimate error: {impact['error']}")
            impact = None
    except Exception as e:
        logger.error(f"Impact estimate failed for {body.location}: {e}")
        impact = None

    try:
        report_stats = community_memory.get_report_stats(body.location)
    except Exception as e:
        logger.error(f"Report stats failed for {body.location}: {e}")
        report_stats = {"total_reports": 0, "validated_reports": 0}

    response = {
        "location": body.location,
        "score": score,
        "risk_tier": risk_tier,
        "total_reports": report_stats.get("total_reports", 0),
        "verified_reports": report_stats.get("validated_reports", 0),
        # Real, named public buildings per district (see
        # src/exposure/shelter_candidates.py) - not an officially
        # designated shelter registry (none exists publicly for Ghana),
        # but genuine places, not generic "{district} Senior High School"
        # placeholder text repeated for every district.
        "shelter_names": get_shelter_names(body.location),
        # Honest dam/reservoir disclosure (src/hydrology/dam_intelligence.py)
        # for the 3 tracked districts genuinely downstream of a dam this
        # platform knows about - [] for the other 6. Each entry is either
        # real data (Akosombo, if DAHITI_API_KEY is configured) or an
        # explicit available=False with the real reason no live feed
        # exists, never a fabricated reservoir level.
        "dam_intelligence": get_dam_intelligence_for_district(body.location),
        # Real river water level via DAHITI satellite altimetry
        # (src/hydrology/river_level_intelligence.py) - available=True
        # only for Tamale (the one tracked district with a real gauge
        # close enough to be meaningful), available=False with an honest
        # reason for the other 8. Set unconditionally, independent of the
        # satellite fetch below.
        "river_gauge": get_river_level_for_district(body.location),
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
                rainfall_mm=body.precipitation,
            )
        )

    # rainfall_mm/river_level_m/soil_saturation_percent are each their own
    # independent real call (DAHITI, SMAP) - previously all three, plus
    # satellite, were nested inside `if hydrology:`, which meant a single
    # unrelated failure in the now-removed composite pipeline above could
    # silently blank out real, independently-fetched DAHITI/SMAP data too.
    # Not gated on anything now; each field honestly reports its own
    # availability instead of inheriting an unrelated call's success.
    response["rainfall_mm"] = body.precipitation
    # river_level_m used to come from src/hydrology/river_intelligence.py's
    # get_river_status(), which is entirely
    # np.random.seed(hash(gauge_id))-fabricated - a sine wave plus
    # noise around a static threshold, with zero connection to any
    # real input. Now sourced from response["river_gauge"] (real
    # DAHITI data for Tamale, honestly None for the other 8 tracked
    # districts) instead - see src/hydrology/river_level_intelligence.py.
    river_gauge = response["river_gauge"]
    response["river_level_m"] = (
        river_gauge.get("level_above_baseline_m") if river_gauge["available"] else None
    )
    # Real NASA SMAP satellite soil moisture (src/hydrology/
    # smap_soil_moisture.py) - src/hydrology/soil_moisture.py's
    # get_soil_moisture() generates "saturation_percent" via
    # random.seed(hash(f"{district}_{date}")) with zero connection
    # to any real input - the same undisclosed-fabrication pattern
    # already fixed this session for river levels and satellite
    # confidence. Honestly None (not the old fabricated number)
    # when Earth Engine can't reach a real SMAP reading.
    soil_moisture = get_soil_moisture_for_district(body.location)
    response["soil_moisture"] = soil_moisture
    response["soil_saturation_percent"] = (
        soil_moisture.get("saturation_percent_estimate")
        if soil_moisture.get("available")
        else None
    )
    # Real Sentinel-1 SAR satellite flood detection (Google Earth
    # Engine, via src/hydrology/sentinel_processor.py) when reachable;
    # satellite["source"] says "Sentinel-1 SAR" for a real detection
    # or "Sentinel-1 (simulated)"/"(unavailable)" otherwise - always
    # check this field before treating the numbers as real. Falls back
    # to an explicit "(unavailable)" dict, matching sentinel_processor's
    # own honest-failure shape, if the try/except above caught an error.
    response["satellite"] = satellite or {
        "water_detected": False,
        "flood_extent_km2": 0,
        "acquisition_date": None,
        "source": "Sentinel-1 (unavailable)",
        "confidence": 0,
    }

    # Risk timeline: real Open-Meteo forecast rainfall (see
    # src/hydrology/weather_forecast.py), layered on top of the current
    # precipitation input and scored through the same calculate_score()
    # used everywhere else - "now" always matches the score above exactly;
    # future points show what the real forecast implies is coming, instead
    # of a fixed +15/+10/+5 synthetic offset with no forecast behind it at
    # all (the dashboard's old behavior).
    try:
        forecast = weather_forecast.get_forecast_for_district(body.location)
        cumulative = forecast.get("cumulative_6h", {})
        timeline = [{"hour": "Now", "score": score, "risk_tier": risk_tier}]
        for h in [6, 12, 18, 24]:
            future_precip = body.precipitation + cumulative.get(str(h), 0.0)
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
        # Real current temperature/sky condition (src/hydrology/
        # weather_forecast.py, Open-Meteo's "current" block) - the
        # system stays useful outside rainy season, when score/risk_tier
        # sit near zero for every district: a citizen or operator still
        # gets a real reading of what it's actually like outside right
        # now. "fallback" values (forecast_source == "fallback") are a
        # climatological estimate, never a live measurement - always
        # check forecast_source before treating this as a real reading.
        response["temperature_c"] = forecast.get("temperature_c")
        response["temperature_f"] = forecast.get("temperature_f")
        response["weather_description"] = forecast.get("weather_description")
        response["weather_icon"] = forecast.get("weather_icon")
        response["is_day"] = forecast.get("is_day")
        response["is_raining_now"] = forecast.get("is_raining_now")
        # Real "chance of rain" (Open-Meteo's own forecast model output) -
        # deliberately separate from score/risk_tier above, which is
        # this platform's own derived FLOOD risk given an assumed
        # rainfall amount, not a probability rain happens at all.
        response["rain_probability_now_percent"] = forecast.get(
            "rain_probability_now_percent"
        )
        response["rain_probability_today_percent"] = forecast.get(
            "rain_probability_today_percent"
        )
    except Exception as e:
        logger.error(f"Weather forecast failed for {body.location}: {e}")

    return response


@router.post("/situation", dependencies=[Depends(verify_api_key)])
# 30/minute per IP - a security audit found slowapi's Limiter was
# instantiated (src/api/auth.py) but never actually applied anywhere in
# the codebase, leaving this endpoint - which calls Google Earth Engine
# and Google Cloud APIs on every request - with no inbound throttling at
# all. 30/minute comfortably covers a real user, the kiosk view's 90s
# auto-refresh (well under 1/minute), and the 3-hourly automated
# assessment script, while still bounding how fast one source can drive
# up Earth Engine usage/cost.
@limiter.limit("30/minute")
async def get_situation(request: Request, body: SituationRequest):
    """Thin HTTP entry point - see _build_situation_response for the
    real logic. request: Request is required by slowapi's
    @limiter.limit decorator (it inspects the endpoint's own signature
    for a real starlette.Request instance)."""
    return await _build_situation_response(body)
