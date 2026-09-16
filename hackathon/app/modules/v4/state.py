"""
CivicFlood AI - State Management
Enterprise-grade state for the National Flood Command Center
"""

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List

# Real count of districts this app actually has hydrology/impact data for
# (dashboard.py's get_district_data lists all 9: Accra Central/West/East,
# Tema, Kumasi, Tamale, Cape Coast, Ho, Sunyani). Ghana has 261 real MMDAs;
# the "Districts Monitored" stat used to just hardcode "10", matching
# neither number.
TRACKED_DISTRICT_COUNT = 9


@dataclass
class DashboardState:
    """Complete state for the CivicFlood AI dashboard."""

    # ============================================================
    # SYSTEM STATUS
    # ============================================================
    api_connected: bool = True
    api_version: str = "3.0.0"
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    active_sources_count: int = 6
    data_quality_score: float = 92.0

    # ============================================================
    # RISK ASSESSMENT
    # ============================================================
    risk_score: float = 50.0
    risk_category: str = "MODERATE"
    risk_color: str = "#ffaa00"
    risk_emoji: str = "🟡"
    risk_confidence: float = 0.80

    # ============================================================
    # LOCATION
    # ============================================================
    district: str = "Accra Central"
    region: str = "Greater Accra"
    lat: float = 5.560
    lon: float = -0.210
    elevation_m: float = 10.0
    area_km2: float = 45.5
    population: int = 187928

    # ============================================================
    # WEATHER & ENVIRONMENT
    # ============================================================
    rainfall_mm: float = 75.0
    river_level_m: float = 1.5
    soil_saturation_percent: float = 65.0
    forecast_24h_mm: float = 45.0
    forecast_48h_mm: float = 60.0
    forecast_72h_mm: float = 30.0
    # Real forecast-driven risk timeline from /situation (see
    # src/api/routes/situation.py), when available - list of
    # {"hour", "score", "risk_tier"}. Empty when /situation wasn't called
    # or the forecast call failed; render_risk_timeline falls back to a
    # synthetic offset from risk_score in that case.
    risk_timeline: List[Dict[str, Any]] = field(default_factory=list)
    # Real, named public buildings for the selected district (see
    # src/exposure/shelter_candidates.py via /situation) - empty when
    # /situation wasn't called, in which case the Operations panel falls
    # back to a generic "{district} X" pattern.
    shelter_names: List[str] = field(default_factory=list)

    # ============================================================
    # POPULATION IMPACT
    # ============================================================
    population_exposed: int = 0
    exposure_percentage: float = 0.0
    children_exposed: int = 0
    elderly_exposed: int = 0
    households_affected: int = 0
    communities_affected: int = 0
    affected_communities: List[str] = field(default_factory=list)

    # ============================================================
    # INFRASTRUCTURE IMPACT
    # ============================================================
    schools_exposed: int = 0
    hospitals_exposed: int = 0
    markets_exposed: int = 0
    power_substations_affected: int = 0

    # ============================================================
    # ECONOMIC IMPACT
    # ============================================================
    residential_loss_ghs: float = 0.0
    infrastructure_loss_ghs: float = 0.0
    agricultural_loss_ghs: float = 0.0
    total_loss_ghs: float = 0.0
    recovery_time_weeks: int = 0

    # ============================================================
    # REPORTS
    # ============================================================
    total_reports: int = 0
    verified_reports: int = 0
    shelters_available: int = 3

    # ============================================================
    # RESOURCES
    # ============================================================
    rescue_boats: int = 3
    ambulances: int = 5
    pumps: int = 10
    rescue_teams: int = 4

    # ============================================================
    # LEAD TIME
    # ============================================================
    lead_time_hours: int = 24
    lead_time_action: str = "MONITOR CONDITIONS"

    # ============================================================
    # EVIDENCE CONFIDENCE SCORES
    # ============================================================
    evidence_rainfall_confidence: float = 85.0
    evidence_river_confidence: float = 78.0
    evidence_soil_confidence: float = 72.0
    evidence_satellite_confidence: float = 80.0
    evidence_citizen_confidence: float = 65.0
    evidence_overall_confidence: float = 80.0

    # ============================================================
    # AI DECISION CENTER
    # ============================================================
    recommended_action: str = ""
    action_confidence: float = 85.0
    action_reason: List[str] = field(default_factory=list)
    action_impact: str = ""
    action_cost_ghs: float = 0.0
    action_time_window: str = ""

    # ============================================================
    # IMPACT BREAKDOWN
    # ============================================================
    impact_people: Dict[str, Any] = field(default_factory=dict)
    impact_infrastructure: Dict[str, Any] = field(default_factory=dict)
    impact_economy: Dict[str, Any] = field(default_factory=dict)
    impact_environment: Dict[str, Any] = field(default_factory=dict)


# Single source of truth for risk-tier -> label/color/emoji, matching
# src/alerts/formatter.py:get_risk_tier exactly (5 tiers, 30/50/70/85
# thresholds). Every module that used to re-derive this locally (its own
# if/elif chain on risk_score, almost always a stale 4-tier version with no
# EXTREME and different breakpoints) should call get_risk_tier_style()
# instead, so a single edit here fixes every display consistently.
TIER_STYLE = {
    "EXTREME": {"color": "#cc0000", "emoji": "🔴"},
    "CRITICAL": {"color": "#ff0000", "emoji": "🔴"},
    "HIGH": {"color": "#ff6600", "emoji": "🟠"},
    "MODERATE": {"color": "#ffaa00", "emoji": "🟡"},
    "LOW": {"color": "#00cc00", "emoji": "🟢"},
}


def tier_from_score(score: float) -> str:
    """Map a 0-100 risk score to a tier name, matching the backend exactly."""
    if score >= 85:
        return "EXTREME"
    elif score >= 70:
        return "CRITICAL"
    elif score >= 50:
        return "HIGH"
    elif score >= 30:
        return "MODERATE"
    else:
        return "LOW"


def get_risk_tier_style(score: float = None, tier: str = None) -> dict:
    """Resolve a risk tier's label/color/emoji.

    Pass `tier` when you already have the backend's real risk_tier string
    (preferred - e.g. state.risk_category); pass `score` to derive one
    locally when no real tier is available yet. Returns
    {"tier", "color", "emoji"}.
    """
    if tier not in TIER_STYLE:
        tier = tier_from_score(score if score is not None else 0)
    return {"tier": tier, **TIER_STYLE[tier]}


def create_state_from_api(api_data: dict) -> DashboardState:
    """Create a DashboardState from API response data."""

    state = DashboardState()

    if "error" in api_data:
        state.api_connected = False
        return state

    # Extract risk data. The real /score endpoint (src/api/main.py) returns
    # a field named "score", not "risk_score" - this used to always fall
    # through to the 50.0 default regardless of what the backend computed,
    # so the headline risk number never actually moved with the rainfall
    # input despite "API Connected" showing true.
    risk_score = api_data.get("score", api_data.get("risk_score", 50.0))
    state.risk_score = float(risk_score)

    # Prefer the backend's own risk_tier (src/alerts/formatter.py:get_risk_tier)
    # over re-deriving a category from score thresholds locally.
    style = get_risk_tier_style(score=state.risk_score, tier=api_data.get("risk_tier"))
    state.risk_category = style["tier"]
    state.risk_color = style["color"]
    state.risk_emoji = style["emoji"]

    # Extract other data
    state.population_exposed = api_data.get("population_exposed", 0)
    state.exposure_percentage = api_data.get("exposure_percentage", 0.0)
    state.communities_affected = api_data.get("communities_affected", 0)
    state.total_reports = api_data.get("total_reports", 0)
    state.verified_reports = api_data.get("verified_reports", 0)

    # Evidence confidence - these represent fixed trust in each data
    # source's general reliability (e.g. "how much do we trust CHIRPS
    # satellite rainfall data"), not a per-request measurement, so there's
    # no live value to pull from the API; defaults stand deliberately.
    state.evidence_rainfall_confidence = api_data.get("rainfall_confidence", 85.0)
    state.evidence_river_confidence = api_data.get("river_confidence", 78.0)
    state.evidence_soil_confidence = api_data.get("soil_confidence", 72.0)
    state.evidence_satellite_confidence = api_data.get("satellite_confidence", 80.0)
    state.evidence_citizen_confidence = api_data.get("citizen_confidence", 65.0)
    state.evidence_overall_confidence = api_data.get("overall_confidence", 80.0)

    # Lead time - from src/exposure/impact_estimator.py via /situation,
    # keyed off the real risk_tier above.
    state.lead_time_hours = api_data.get("lead_time_hours", 24)
    state.lead_time_action = api_data.get("lead_time_action", "MONITOR CONDITIONS")

    # Weather
    state.rainfall_mm = api_data.get("rainfall_mm", 75.0)
    state.river_level_m = api_data.get("river_level_m", state.river_level_m)
    state.soil_saturation_percent = api_data.get(
        "soil_saturation_percent", state.soil_saturation_percent
    )
    state.forecast_24h_mm = api_data.get("forecast_24h_mm", 45.0)
    state.forecast_48h_mm = api_data.get("forecast_48h_mm", 60.0)
    state.forecast_72h_mm = api_data.get("forecast_72h_mm", 30.0)
    state.risk_timeline = api_data.get("risk_timeline", [])
    state.shelter_names = api_data.get("shelter_names", [])

    # Population/infrastructure impact - from src/exposure/impact_estimator.py
    # via /situation. Falls back to the dashboard's own demo generator
    # (state_fallback.get_fallback_data) only when /situation wasn't called
    # or returned nothing for these fields (population_exposed stays 0).
    if "population_total" in api_data:
        state.population = api_data["population_total"]
    state.children_exposed = api_data.get("children_exposed", 0)
    state.elderly_exposed = api_data.get("elderly_exposed", 0)
    state.households_affected = api_data.get("households_affected", 0)
    state.schools_exposed = api_data.get("schools_exposed", 0)
    state.hospitals_exposed = api_data.get("hospitals_exposed", 0)
    state.markets_exposed = api_data.get("markets_exposed", 0)
    state.power_substations_affected = api_data.get("power_substations_affected", 0)
    if "area_km2" in api_data:
        state.area_km2 = api_data["area_km2"]

    # Economic impact - see src/api/routes/situation.py for the (simple,
    # uncalibrated) loss-estimate formula.
    state.residential_loss_ghs = api_data.get("residential_loss_ghs", 0.0)
    state.infrastructure_loss_ghs = api_data.get("infrastructure_loss_ghs", 0.0)
    state.agricultural_loss_ghs = api_data.get("agricultural_loss_ghs", 0.0)
    state.total_loss_ghs = api_data.get("total_loss_ghs", 0.0)

    return state


# Default state for testing
default_state = DashboardState()
