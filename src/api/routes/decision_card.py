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

from src.alerts.formatter import get_risk_tier
from src.api.routes.situation import SituationRequest, get_situation
from src.exposure.community_names import get_affected_communities
from src.hydrology.fluvial_pathway import build_fluvial_sources
from src.hydrology.river_level_intelligence import has_river_coverage
from src.models.multi_source_confidence import (
    CITIZEN_REPORTS_PARTIAL_WEIGHT,
    CITIZEN_REPORTS_VERIFIED_WEIGHT,
    RAINFALL_WEIGHT,
    SATELLITE_CONFIRMED_WEIGHT,
    OverallFusionResult,
    Pathway,
    SourceReading,
    combine_pathways,
)

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


def build_evidence(tier: str, situation: dict):
    """The single place evidence/reason/data_gaps are derived from a
    /situation response - shared by get_decision_card (this file) and
    GET /v1/districts/{district}/evidence (src/api/v1/evidence.py) so
    there is exactly one evidence-gathering implementation, not two that
    could drift the way this platform's district lists and lead-time
    tables already have.

    Returns (evidence: List[EvidenceItem], reason: str,
    data_gaps: List[str], sat_confirmed: bool, verified: int) - the last
    two are returned alongside because _compute_confidence below needs
    them too, without re-deriving satellite/report logic a second time."""
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

    # river_level_m itself (src/hydrology/unified_intelligence.py) is
    # entirely np.random.seed(hash(gauge_id))-fabricated with no real
    # input behind it at all (confirmed by reading river_intelligence.py's
    # _generate_gauge_data - a sine wave plus noise, never driven by real
    # rainfall or any other real signal) - it used to be cited here as
    # available=True unconditionally, the same undisclosed-fabrication
    # bug already fixed for satellite/dam evidence elsewhere in this
    # function, just undiscovered until directly checked. Real coverage
    # (src/hydrology/river_level_intelligence.py, DAHITI satellite
    # altimetry) exists only for Tamale; every other district honestly
    # reports available=False instead.
    river_gauge = situation.get("river_gauge") or {}
    river_available = river_gauge.get("available", False)
    evidence.append(
        EvidenceItem(
            field="river_water_level",
            value=river_gauge.get("water_surface_elevation_m"),
            source=river_gauge.get("source", "unavailable"),
            available=river_available,
            as_of=river_gauge.get("observation_date"),
        )
    )
    if river_available:
        reason_parts.append(
            f"{river_gauge['river']} water surface elevation: "
            f"{river_gauge['water_surface_elevation_m']}m "
            f"(real gauge {river_gauge['distance_km']}km from this district, "
            f"as of {river_gauge.get('observation_date', 'unknown date')})"
        )

    soil_moisture = situation.get("soil_moisture") or {}
    soil_available = bool(soil_moisture.get("available"))
    soil = soil_moisture.get("saturation_percent_estimate")
    evidence.append(
        EvidenceItem(
            field="soil_saturation_percent",
            value=soil,
            source=soil_moisture.get("source", "unavailable"),
            available=soil_available,
            as_of=soil_moisture.get("observation_date"),
        )
    )
    if soil_available and soil is not None:
        reason_parts.append(f"Soil moisture (NASA SMAP): {soil:.0f}% of sensor range")

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

    return evidence, ". ".join(reason_parts) + ".", data_gaps, sat_confirmed, verified


# Satellite SAR with no confirmed water is real evidence, but weak:
# Sentinel-1's revisit interval (days, not continuous) means "no
# detection" doesn't strongly imply "no flood" the way a confirmed
# detection strongly implies one does exist - real remote-sensing
# flood-mapping practice values SAR confirmation far more than SAR
# absence. See SATELLITE_CONFIRMED_WEIGHT for the positive case.
_SATELLITE_NO_DETECTION_RISK = 20.0
_SATELLITE_NO_DETECTION_WEIGHT = 0.3


def build_confidence(
    district: str, situation: dict, sat_confirmed: bool, verified: int
) -> OverallFusionResult:
    """Real skill-weighted, coverage+agreement confidence
    (src/models/multi_source_confidence.py) - replaces the old fixed
    `60 + 20·sat + 15·reports` heuristic, which never actually used
    rainfall, river, or dam evidence in the number itself despite
    ConfidenceBlock.method's old wording claiming it did. Shared by
    get_decision_card and GET /v1/districts/{district}/evidence for the
    same reason build_evidence is shared above.

    Sources are grouped into INDEPENDENT CAUSAL PATHWAYS, not fused as
    one flat list - see multi_source_confidence.py's module docstring
    for the real-world reasoning: rainfall (pluvial) and river/dam
    levels (fluvial) are independent ways a district can flood. A dam
    overflowing with zero local rainfall must show as real high risk,
    not get averaged down by calm rainfall; two pathways disagreeing is
    the normal signature of "one real threat, one not," not
    measurement noise to be penalized as low confidence.

    - pluvial: rainfall/forecast.
    - fluvial: real river gauge AND real dam/upstream-proxy levels
      (both now classified via the same percentile-threshold method,
      src/hydrology/altimetry_thresholds.py) - grouped together because
      they're both real manifestations of "is this watercourse/
      reservoir system dangerously high," whatever is driving it
      upstream.
    - observation: satellite SAR confirmation and verified citizen
      reports - direct evidence a flood is already happening."""
    pluvial_sources: List[SourceReading] = [
        SourceReading(
            name="rainfall",
            display_name="rainfall forecasts",
            applicable=True,
            available=situation.get("score") is not None,
            risk_0_100=situation.get("score"),
            weight=RAINFALL_WEIGHT,
            unavailable_reason="no precipitation input" if situation.get("score") is None else None,
        )
    ]

    fluvial_sources = build_fluvial_sources(
        river_gauge=situation.get("river_gauge") or {},
        dam_intelligence=situation.get("dam_intelligence", []),
        river_applicable=has_river_coverage(district),
    )

    observation_sources: List[SourceReading] = []
    satellite = situation.get("satellite") or {}
    sat_source = satellite.get("source", "")
    sat_ran_for_real = "SAR" in sat_source
    if sat_confirmed:
        observation_sources.append(
            SourceReading(
                name="satellite_sar",
                display_name="satellite-derived indicators",
                applicable=True,
                available=True,
                risk_0_100=95.0,
                weight=SATELLITE_CONFIRMED_WEIGHT,
            )
        )
    elif sat_ran_for_real:
        # A real check ran and found nothing - weak, non-degrading
        # evidence (see module comment above), not a missing source.
        observation_sources.append(
            SourceReading(
                name="satellite_sar",
                display_name="satellite-derived indicators",
                applicable=False,
                available=True,
                risk_0_100=_SATELLITE_NO_DETECTION_RISK,
                weight=_SATELLITE_NO_DETECTION_WEIGHT,
            )
        )
    else:
        observation_sources.append(
            SourceReading(
                name="satellite_sar",
                display_name="satellite-derived indicators",
                applicable=True,
                available=False,
                unavailable_reason="Earth Engine unavailable",
            )
        )

    if verified >= 3:
        observation_sources.append(
            SourceReading(
                name="citizen_reports",
                display_name="verified citizen reports",
                applicable=True,
                available=True,
                risk_0_100=90.0,
                weight=CITIZEN_REPORTS_VERIFIED_WEIGHT,
            )
        )
    elif verified > 0:
        observation_sources.append(
            SourceReading(
                name="citizen_reports",
                display_name="verified citizen reports",
                applicable=True,
                available=True,
                risk_0_100=65.0,
                weight=CITIZEN_REPORTS_PARTIAL_WEIGHT,
            )
        )
    else:
        # Zero verified reports is a real, working check that came back
        # non-informative - not a missing source (see satellite comment
        # above for the same asymmetry).
        observation_sources.append(
            SourceReading(
                name="citizen_reports",
                display_name="verified citizen reports",
                applicable=False,
                available=True,
            )
        )

    return combine_pathways(
        [
            Pathway("pluvial", "rainfall", pluvial_sources),
            Pathway("fluvial", "river/dam", fluvial_sources),
            Pathway("observation", "direct observation", observation_sources),
        ]
    )


class ConfidenceBlock(BaseModel):
    value: int
    basis: List[str]
    coverage: float
    agreement: float
    degraded: bool
    explanation: str
    method: str = (
        "Skill-and-coverage-weighted fusion across available real "
        "signals, grouped into independent causal pathways - rainfall "
        "(pluvial), river/dam levels (fluvial), direct observation "
        "(src/models/multi_source_confidence.py). Agreement WITHIN a "
        "pathway raises confidence; pathways disagreeing with each "
        "other does NOT lower confidence, since that's the normal "
        "signature of one real threat being active while another is "
        "not (see module docstring's pluvial/fluvial/noisy-OR "
        "reasoning) - only missing/unavailable pathways do. Not the "
        "forecast's own uncertainty, since the risk score is a "
        "deterministic function of real rainfall. See "
        "src/api/routes/decision_card.py for the exact weights."
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
    # Real noisy-OR combination of independent causal pathways
    # (src/models/multi_source_confidence.py) - distinct from score/
    # risk_tier above, which remain rainfall-only (unchanged, so
    # nothing already depending on them is affected). fused_risk_tier
    # can be HIGHER than risk_tier when a dam/river pathway is elevated
    # while local rainfall is calm - exactly the "dam overflow floods a
    # district with no rain" scenario risk_tier alone cannot see.
    fused_risk_score: Optional[float] = None
    fused_risk_tier: Optional[str] = None
    risk_attribution: str = ""
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


def basis_from_fusion(result: OverallFusionResult) -> List[str]:
    basis = [
        f"{r.display_name.capitalize()} available"
        for pathway in result.pathways.values()
        for r in pathway.present
    ]
    if result.degraded:
        basis += [
            f"{r.display_name.capitalize()} unavailable"
            for pathway in result.pathways.values()
            for r in pathway.missing
        ]
    return basis or ["No real evidence sources available"]


@router.post("/card", response_model=DecisionCard)
async def get_decision_card(request: DecisionCardRequest) -> DecisionCard:
    """Grounded decision output for one district - see module docstring."""
    situation = await get_situation(
        SituationRequest(location=request.location, precipitation=request.precipitation)
    )

    tier = situation.get("risk_tier", "LOW")
    evidence, reason, data_gaps, sat_confirmed, verified = build_evidence(tier, situation)
    fusion = build_confidence(request.location, situation, sat_confirmed, verified)

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

    fused_risk_tier = (
        get_risk_tier(fusion.unified_risk) if fusion.unified_risk is not None else None
    )

    return DecisionCard(
        decision_id=str(uuid.uuid4()),
        generated_at=datetime.now(timezone.utc).isoformat(),
        risk_tier=tier,
        score=situation.get("score", 0.0),
        fused_risk_score=fusion.unified_risk,
        fused_risk_tier=fused_risk_tier,
        risk_attribution=fusion.risk_attribution,
        location=LocationBlock(
            district=request.location,
            communities=get_affected_communities(request.location),
        ),
        action=ActionBlock(type=action_type, label=action_label),
        priority=priority,
        time_window_hours=lead_time_hours,
        confidence=ConfidenceBlock(
            value=round(fusion.confidence),
            basis=basis_from_fusion(fusion),
            coverage=fusion.coverage_factor,
            agreement=fusion.agreement_factor,
            degraded=fusion.degraded,
            explanation=fusion.explanation,
        ),
        evidence=evidence,
        expected_impact=ExpectedImpact(
            population_exposed=population_exposed,
            children_exposed=situation.get("children_exposed"),
            elderly_exposed=situation.get("elderly_exposed"),
            estimated_cost_ghs=cost,
        ),
        reason=reason,
        data_gaps=data_gaps,
        status="DRAFT",
    )
