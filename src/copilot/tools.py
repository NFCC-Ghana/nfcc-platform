"""Evidence/retrieval layer for the AI Copilot (src/copilot/engine.py).

Each function here is a plain async tool the Copilot can call - passed
directly to Gemini's automatic function calling (google-genai), which
generates the tool schema from these signatures/docstrings and executes
them itself, so no decorator is needed. Every one wraps ONE existing,
already-deployed /v1/* computation - the exact same service-layer
function that route already calls - in-process (no HTTP round trip to
this same service). This is the grounding mechanism: the Copilot has no
tool that returns free-text "knowledge", only tools that return real,
live, structured platform state. See engine.py's module docstring for
why this is an architectural constraint, not a prompting choice.

Nothing here recomputes a number a route already computes. Where a tool
needs "current precipitation" and the caller didn't supply one, it uses
the platform's own existing forecast module (src/hydrology/
weather_forecast.py, Open-Meteo-backed) - the same real source
src/api/v1/forecast.py already serves - and always labels which one it
used, never inventing a number.
"""

import dataclasses
import logging
from typing import Optional

from src.api.routes.decision_card import (
    DecisionCardRequest,
    basis_from_fusion,
    build_confidence,
    build_evidence,
    get_decision_card,
)
from src.api.routes.situation import SituationRequest, _build_situation_response
from src.database.risk_history_db import get_risk_history
from src.exposure.districts import (
    District,
    TRACKED_DISTRICT_NAMES,
    get_district,
    list_districts,
)
from src.exposure.shelter_candidates import get_shelter_names
from src.hydrology.weather_forecast import weather_forecast

logger = logging.getLogger("nfcc.copilot.tools")


def _district_to_dict(district: District) -> dict:
    return dataclasses.asdict(district)


def _not_tracked_error(district: str) -> dict:
    return {
        "error": (
            f"'{district}' is not one of the {len(TRACKED_DISTRICT_NAMES)} "
            f"districts this platform tracks: {', '.join(TRACKED_DISTRICT_NAMES)}. "
            "Call list_tracked_districts for full details."
        )
    }


async def _live_precipitation_mm(district: str) -> tuple[float, str]:
    """Real 24h forecasted rainfall for `district` (src/hydrology/
    weather_forecast.py, Open-Meteo-backed) - used only when a tool call
    doesn't specify precipitation_mm itself. Returns (value, source_label)
    so callers never present an auto-fetched number as if it were
    operator-confirmed."""
    forecast = weather_forecast.get_forecast_for_district(district)
    return (
        forecast.get("24h", 0.0),
        "auto: Open-Meteo 24h forecast (no precipitation_mm supplied)",
    )


async def list_tracked_districts() -> dict:
    """List every district this platform actually tracks, with region,
    population, area, and the real named communities within it. Call
    this first whenever the user names a place you are not certain is
    tracked, or asks a "which districts" question generically - never
    guess a district name or community that isn't in this list.
    """
    districts = [_district_to_dict(d) for d in list_districts()]
    return {"count": len(districts), "districts": districts}


async def get_current_risk_overview() -> dict:
    """Get the most recently recorded real risk snapshot for every
    tracked district, plus the snapshot before it, from the platform's
    persisted risk-history log (recorded automatically every 3 hours by
    the scheduled assessment job - not recomputed live). Use this to
    answer "which districts are at highest risk right now" (rank by
    latest.score) and "what changed since the previous update" (compare
    latest vs previous). If a district has no recorded snapshot yet, say
    so honestly instead of guessing its risk.
    """
    overview = []
    for name in TRACKED_DISTRICT_NAMES:
        history = get_risk_history(name, limit=2)
        entry = {"district": name}
        if not history:
            entry["status"] = "no_recorded_snapshot"
        else:
            entry["latest"] = history[0]
            entry["previous"] = history[1] if len(history) > 1 else None
        overview.append(entry)
    return {"districts": overview}


async def get_district_decision(
    district: str, precipitation_mm: Optional[float] = None
) -> dict:
    """Get the full AI Decision Card for one district: risk_tier, score,
    fused_risk_score/tier (combining rainfall with river/dam/satellite
    pathways), the recommended action and priority, a confidence block
    (coverage/agreement/degraded + plain-language explanation), the full
    evidence list behind the tier, expected population/child/elderly
    exposure, and any data_gaps. This is the primary tool for "why is
    district X classified as Y" and "should we evacuate" questions.

    Args:
        district: One of the tracked district names (see
            list_tracked_districts if unsure).
        precipitation_mm: Current precipitation in mm. If omitted, a
            real live 24h forecast value is fetched automatically and
            labeled as such in the response.
    """
    if get_district(district) is None:
        return _not_tracked_error(district)

    precip_source = "user-specified"
    if precipitation_mm is None:
        precipitation_mm, precip_source = await _live_precipitation_mm(district)

    card = await get_decision_card(
        DecisionCardRequest(location=district, precipitation=precipitation_mm)
    )
    result = card.model_dump()
    result["precipitation_mm_used"] = precipitation_mm
    result["precipitation_source"] = precip_source
    return result


async def get_district_evidence(
    district: str, precipitation_mm: Optional[float] = None
) -> dict:
    """Get just the evidence array and confidence block behind a
    district's current risk tier, without the full decision card. Use
    this for "what evidence supports the current risk" questions.

    Args:
        district: One of the tracked district names.
        precipitation_mm: Current precipitation in mm. If omitted, a
            real live 24h forecast value is fetched automatically and
            labeled as such in the response.
    """
    if get_district(district) is None:
        return _not_tracked_error(district)

    precip_source = "user-specified"
    if precipitation_mm is None:
        precipitation_mm, precip_source = await _live_precipitation_mm(district)

    situation = await _build_situation_response(
        SituationRequest(location=district, precipitation=precipitation_mm)
    )
    tier = situation.get("risk_tier", "LOW")
    evidence, reason, data_gaps, sat_confirmed, verified = build_evidence(
        tier, situation
    )
    fusion = build_confidence(district, situation, sat_confirmed, verified)

    return {
        "district": district,
        "risk_tier": tier,
        "evidence": [e.model_dump() for e in evidence],
        "reason": reason,
        "data_gaps": data_gaps,
        "confidence": {
            "value": round(fusion.confidence),
            "basis": basis_from_fusion(fusion),
            "coverage": fusion.coverage_factor,
            "agreement": fusion.agreement_factor,
            "degraded": fusion.degraded,
            "explanation": fusion.explanation,
        },
        "precipitation_mm_used": precipitation_mm,
        "precipitation_source": precip_source,
    }


async def get_district_forecast(
    district: str, current_precipitation_mm: Optional[float] = None
) -> dict:
    """Get the real rainfall forecast (24h/48h/72h/daily) and the
    resulting risk projection at +6h/+12h/+18h/+24h for a district. Use
    this for "what's expected in the next 6 hours" questions.

    Args:
        district: One of the tracked district names.
        current_precipitation_mm: Current precipitation in mm, used to
            anchor the risk projection's "Now" point. If omitted, a real
            live 24h forecast value is fetched automatically.
    """
    if get_district(district) is None:
        return _not_tracked_error(district)

    precip_source = "user-specified"
    if current_precipitation_mm is None:
        current_precipitation_mm, precip_source = await _live_precipitation_mm(district)

    from src.alerts.formatter import calculate_score, get_risk_tier

    forecast = weather_forecast.get_forecast_for_district(district)
    cumulative = forecast.get("cumulative_6h", {})
    score_now = calculate_score(current_precipitation_mm)
    timeline = [
        {"hour": "Now", "score": score_now, "risk_tier": get_risk_tier(score_now)}
    ]
    for h in (6, 12, 18, 24):
        future_precip = current_precipitation_mm + cumulative.get(str(h), 0.0)
        future_score = calculate_score(future_precip)
        timeline.append(
            {
                "hour": f"{h}h",
                "score": future_score,
                "risk_tier": get_risk_tier(future_score),
            }
        )

    return {
        "district": district,
        "forecast_24h_mm": forecast.get("24h", 0.0),
        "forecast_48h_mm": forecast.get("48h", 0.0),
        "forecast_72h_mm": forecast.get("72h", 0.0),
        "cumulative_6h_mm": cumulative,
        "daily": forecast.get("daily", []),
        "risk_timeline": timeline,
        "source": forecast.get("source", "unknown"),
        "generated_at": forecast.get("timestamp", ""),
        "current_precipitation_mm_used": current_precipitation_mm,
        "precipitation_source": precip_source,
    }


async def get_district_resources(
    district: str, precipitation_mm: Optional[float] = None
) -> dict:
    """Get real operational resources for a district: named public
    buildings that could serve as shelters, real dam disclosure
    (availability, water level, downstream communities), and
    infrastructure exposure counts (schools/hospitals/markets/power).
    Use this for "which shelters are available" questions. Deliberately
    excludes rescue boats/ambulances/pumps - no real inventory system
    for those exists in this platform.

    Args:
        district: One of the tracked district names.
        precipitation_mm: Current precipitation in mm, used to compute
            infrastructure exposure. If omitted, a real live 24h
            forecast value is fetched automatically.
    """
    if get_district(district) is None:
        return _not_tracked_error(district)

    precip_source = "user-specified"
    if precipitation_mm is None:
        precipitation_mm, precip_source = await _live_precipitation_mm(district)

    situation = await _build_situation_response(
        SituationRequest(location=district, precipitation=precipitation_mm)
    )

    return {
        "district": district,
        "shelters": get_shelter_names(district),
        "dams": situation.get("dam_intelligence", []),
        "schools_exposed": situation.get("schools_exposed"),
        "hospitals_exposed": situation.get("hospitals_exposed"),
        "markets_exposed": situation.get("markets_exposed"),
        "power_substations_affected": situation.get("power_substations_affected"),
        "precipitation_mm_used": precipitation_mm,
        "precipitation_source": precip_source,
    }


async def get_data_source_health() -> dict:
    """Get real connectivity status for every data source this platform
    depends on (Earth Engine/Sentinel-1 SAR, DAHITI dam altimetry,
    Open-Meteo, Ghana river gauges, community reports database). Use
    this for "which data sources are currently unavailable" questions -
    status is one of connected/configured/not_configured/unavailable,
    never guessed.
    """
    # Imported here, not at module level: src.api.v1.health is a
    # submodule of the src.api.v1 package, whose __init__ also mounts
    # this module's own copilot router - a module-level import would be
    # circular (src.api.v1 -> copilot route -> engine -> tools ->
    # src.api.v1.health -> triggers src.api.v1/__init__ again).
    from src.api.v1.health import get_data_source_health as _get_data_source_health

    health = await _get_data_source_health()
    return health.model_dump()


async def get_data_quality_report() -> dict:
    """Get a deeper per-source quality report (freshness, plausible-range
    validity, completeness) than get_data_source_health provides - a
    source can be reachable but still return a stale or suspect reading,
    which only this tool catches. Use this as a follow-up when the user
    asks why a specific source's evidence should or shouldn't be
    trusted.
    """
    # Imported here for the same circular-import reason as
    # get_data_source_health above.
    from src.api.v1.data_quality import get_data_quality as _get_data_quality

    return await _get_data_quality()
