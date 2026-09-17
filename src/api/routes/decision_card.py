"""The AI Decision Engine's structured output: a grounded DecisionCard.

Everything this endpoint says is derived from POST /situation's already-
real response (src/api/routes/situation.py) - this file adds no new data
source of its own. It exists to turn that data into a single, structured,
schema-validated decision object (action/priority/evidence/confidence/
data_gaps) instead of leaving each consumer (the dashboard, a future
Copilot, a partner integration) to independently reinterpret raw
situation fields into its own ad hoc "reasons" text - which is exactly
how hackathon/app/pages/dashboard.py's render_ai_decision_center() ended
up with hardcoded, occasionally fabricated claims before this endpoint
existed (see that function's docstring for the specific bug).

Every EvidenceItem carries `available` explicitly - a missing signal
(hydrology call failed, no dam data, zero citizen reports) is a visible,
typed fact, not silent omission. `reason` is built by concatenating only
the evidence items that are actually available, mirroring the
"citation contract" pattern from grounded-generation research (every
claim traces to a specific retrieved fact; the system abstains rather
than inventing one it doesn't have).

`status` starts at "DRAFT" always - this endpoint has no side effects
and never calls AlertEngine. A DecisionCard is advisory output for a
human reviewer, not itself part of the human-in-the-loop approval chain
(src/api/routes/alert_review.py remains the only place that can trigger
a real send).
"""

import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.api.routes.situation import SituationRequest, get_situation
from src.exposure.community_names import get_affected_communities

router = APIRouter(prefix="/decision", tags=["decision-intelligence"])

# JMA-style action per tier (Japan's 5-level warning system ties each
# level to WHO must act, not just a severity label) - matches the
# response_guidance vocabulary already used in
# src/api/routes/alert_review.py for consistency across the platform.
_ACTION_BY_TIER = {
    "EXTREME": ("EVACUATE_ALL", "Issue mandatory evacuation order"),
    "CRITICAL": ("EVACUATE_VULNERABLE", "Evacuate vulnerable residents now; others prepare"),
    "HIGH": ("PREPARE", "Prepare for evacuation"),
    "MODERATE": ("MONITOR", "Issue public awareness message"),
    "LOW": ("MONITOR", "Continue normal monitoring"),
}
_PRIORITY_BY_TIER = {
    "EXTREME": "CRITICAL",
    "CRITICAL": "CRITICAL",
    "HIGH": "URGENT",
    "MODERATE": "ELEVATED",
    "LOW": "ROUTINE",
}


class EvidenceItem(BaseModel):
    field: str
    value: Optional[Any] = None
    source: str
    available: bool
    as_of: Optional[str] = None


class ConfidenceBlock(BaseModel):
    value: int
    basis: List[str]
    method: str = (
        "Weighted agreement across available real signals on top of a "
        "conservative baseline - not the forecast's own uncertainty, "
        "since the risk score is a deterministic function of real "
        "rainfall. See src/api/routes/decision_card.py for the exact "
        "weights and why overconfidence here is treated as a real risk."
    )


class LocationBlock(BaseModel):
    district: str
    communities: List[str]
    source: str = "src/exposure/community_names.py"


class ActionBlock(BaseModel):
    type: str
    label: str


class ExpectedImpact(BaseModel):
    population_exposed: Optional[int] = None
    children_exposed: Optional[int] = None
    elderly_exposed: Optional[int] = None
    estimated_cost_ghs: Optional[float] = None
    cost_basis: str = "Illustrative per-person estimate - no calibrated operations-cost model exists"


class DecisionCard(BaseModel):
    decision_id: str
    generated_at: str
    # Real risk_tier/score from the same /situation call this card is
    # built from (src/alerts/formatter.py:get_risk_tier) - included so a
    # consumer (the dashboard) can render the same tier badge/color/emoji
    # used everywhere else on the platform without recomputing it, rather
    # than having two independent "what tier is this" implementations
    # that could drift apart.
    risk_tier: str
    score: float
    location: LocationBlock
    action: ActionBlock
    priority: str
    time_window_hours: Optional[int] = None
    confidence: ConfidenceBlock
    evidence: List[EvidenceItem]
    expected_impact: ExpectedImpact
    reason: str
    data_gaps: List[str]
    status: str = "DRAFT"


class DecisionCardRequest(BaseModel):
    location: str = Field(..., description="District location")
    precipitation: float = Field(..., description="Precipitation in mm", ge=0)


# Cost-per-person multipliers by tier - same illustrative figures
# originally in hackathon/app/pages/dashboard.py's render_ai_decision_center
# before it was migrated to call this endpoint instead of computing its
# own. LOW has no multiplier because LOW's cost isn't population-scaled -
# see the flat _LOW_TIER_FLAT_COST_GHS below, matching the dashboard's
# original "routine monitoring has a baseline cost even if exposure is
# near zero" behavior, which population_exposed * 0 would have silently
# dropped to zero.
_COST_PER_PERSON_BY_TIER = {
    "EXTREME": 15,
    "CRITICAL": 15,
    "HIGH": 8,
    "MODERATE": 1.25,
}
_LOW_TIER_FLAT_COST_GHS = 5000


@router.post("/card", response_model=DecisionCard)
async def get_decision_card(request: DecisionCardRequest) -> DecisionCard:
    """Grounded decision output for one district - see module docstring."""
    situation = await get_situation(
        SituationRequest(location=request.location, precipitation=request.precipitation)
    )

    tier = situation.get("risk_tier", "LOW")
    evidence: List[EvidenceItem] = []
    reason_parts: List[str] = []
    data_gaps: List[str] = []

    rainfall = situation.get("rainfall_mm")
    evidence.append(
        EvidenceItem(
            field="rainfall_mm",
            value=rainfall,
            source="user-supplied precipitation input",
            available=rainfall is not None,
        )
    )
    if rainfall:
        reason_parts.append(f"Rainfall driving this assessment: {rainfall:.0f}mm")

    forecast_24h = situation.get("forecast_24h_mm")
    evidence.append(
        EvidenceItem(
            field="forecast_24h_mm",
            value=forecast_24h,
            source=situation.get("forecast_source", "open-meteo"),
            available=forecast_24h is not None,
        )
    )
    if forecast_24h:
        reason_parts.append(f"Forecast next 24h: {forecast_24h:.0f}mm additional")

    river_level = situation.get("river_level_m")
    evidence.append(
        EvidenceItem(
            field="river_level_m",
            value=river_level,
            source="src/hydrology/unified_intelligence.py",
            available=river_level is not None,
        )
    )
    if river_level:
        reason_parts.append(f"River level: {river_level:.1f}m")

    soil = situation.get("soil_saturation_percent")
    evidence.append(
        EvidenceItem(
            field="soil_saturation_percent",
            value=soil,
            source="src/hydrology/unified_intelligence.py",
            available=soil is not None,
        )
    )
    if soil:
        reason_parts.append(f"Soil saturation: {soil:.0f}%")

    satellite = situation.get("satellite") or {}
    sat_source = satellite.get("source", "")
    sat_confirmed = bool(satellite.get("water_detected")) and sat_source == "Sentinel-1 SAR"
    evidence.append(
        EvidenceItem(
            field="satellite_water_detected",
            value=satellite.get("water_detected"),
            source=sat_source or "unavailable",
            available=bool(satellite) and "SAR" in sat_source,
            as_of=satellite.get("acquisition_date"),
        )
    )
    if sat_confirmed:
        extent = satellite.get("flood_extent_km2", 0)
        reason_parts.append(f"Satellite (Sentinel-1 SAR) confirms {extent:.1f} km² water extent")

    verified = situation.get("verified_reports", 0)
    evidence.append(
        EvidenceItem(
            field="verified_reports",
            value=verified,
            source="src/community/community_memory.py",
            available=True,
        )
    )
    if verified > 0:
        reason_parts.append(f"{verified} citizen report(s) verified on the ground")
    elif tier in ("EXTREME", "CRITICAL", "HIGH"):
        reason_parts.append("No verified citizen reports yet for this area")

    for dam in situation.get("dam_intelligence", []):
        dam_available = dam.get("available", False)
        evidence.append(
            EvidenceItem(
                field=f"dam_{dam.get('dam', 'unknown').lower()}",
                value=dam.get("water_surface_elevation_m"),
                source=dam.get("source", dam.get("dam", "dam_intelligence")),
                available=dam_available,
                as_of=dam.get("observation_date"),
            )
        )
        if not dam_available:
            data_gaps.append(f"{dam.get('dam', 'Dam')}: {dam.get('reason', 'data unavailable')}")
        elif dam.get("water_surface_elevation_m") is not None:
            reason_parts.append(
                f"{dam['dam']} water surface elevation: {dam['water_surface_elevation_m']}m "
                f"(as of {dam.get('observation_date', 'unknown date')})"
            )

    if not reason_parts:
        reason_parts.append(
            "Assessment based on real-time rainfall data only - "
            "no additional corroborating signals available"
        )

    # Confidence: conservative baseline, real corroboration raises it,
    # capped well short of certainty - see ConfidenceBlock.method and
    # module docstring for why overconfidence here is treated as a real
    # risk, not a hypothetical one.
    confidence = 60
    basis = ["Rainfall-driven risk score"]
    if sat_confirmed:
        confidence += 20
        basis.append("Satellite confirmation")
    if verified >= 3:
        confidence += 15
        basis.append(f"{verified} verified citizen reports")
    elif verified > 0:
        confidence += 7
        basis.append(f"{verified} verified citizen report")
    confidence = min(confidence, 95)

    action_type, action_label = _ACTION_BY_TIER.get(tier, _ACTION_BY_TIER["LOW"])
    priority = _PRIORITY_BY_TIER.get(tier, "ROUTINE")
    lead_time_hours = situation.get("lead_time_hours")
    population_exposed = situation.get("population_exposed")
    if tier in ("LOW", "VERY_LOW"):
        cost = _LOW_TIER_FLAT_COST_GHS
    elif population_exposed is not None:
        cost = population_exposed * _COST_PER_PERSON_BY_TIER.get(tier, 0)
    else:
        cost = None

    return DecisionCard(
        decision_id=str(uuid.uuid4()),
        generated_at=datetime.now(timezone.utc).isoformat(),
        risk_tier=tier,
        score=situation.get("score", 0.0),
        location=LocationBlock(
            district=request.location,
            communities=get_affected_communities(request.location),
        ),
        action=ActionBlock(type=action_type, label=action_label),
        priority=priority,
        time_window_hours=lead_time_hours,
        confidence=ConfidenceBlock(value=confidence, basis=basis),
        evidence=evidence,
        expected_impact=ExpectedImpact(
            population_exposed=population_exposed,
            children_exposed=situation.get("children_exposed"),
            elderly_exposed=situation.get("elderly_exposed"),
            estimated_cost_ghs=cost,
        ),
        reason=". ".join(reason_parts) + ".",
        data_gaps=data_gaps,
        status="DRAFT",
    )
