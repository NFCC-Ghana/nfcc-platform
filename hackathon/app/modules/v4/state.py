"""
CivicFlood AI - State Management
Enterprise-grade state for the National Flood Command Center
"""

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List


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


def create_state_from_api(api_data: dict) -> DashboardState:
    """Create a DashboardState from API response data."""

    state = DashboardState()

    if "error" in api_data:
        state.api_connected = False
        return state

    # Extract risk data
    risk_score = api_data.get("risk_score", 50.0)
    state.risk_score = float(risk_score)

    # Determine risk category
    if state.risk_score >= 80:
        state.risk_category = "CRITICAL"
        state.risk_color = "#ff0000"
        state.risk_emoji = "🔴"
    elif state.risk_score >= 60:
        state.risk_category = "HIGH"
        state.risk_color = "#ff6600"
        state.risk_emoji = "🟠"
    elif state.risk_score >= 40:
        state.risk_category = "MODERATE"
        state.risk_color = "#ffaa00"
        state.risk_emoji = "🟡"
    else:
        state.risk_category = "LOW"
        state.risk_color = "#00cc00"
        state.risk_emoji = "🟢"

    # Extract other data
    state.population_exposed = api_data.get("population_exposed", 0)
    state.exposure_percentage = api_data.get("exposure_percentage", 0.0)
    state.communities_affected = api_data.get("communities_affected", 0)
    state.total_reports = api_data.get("total_reports", 0)
    state.verified_reports = api_data.get("verified_reports", 0)

    # Evidence confidence
    state.evidence_rainfall_confidence = api_data.get("rainfall_confidence", 85.0)
    state.evidence_river_confidence = api_data.get("river_confidence", 78.0)
    state.evidence_soil_confidence = api_data.get("soil_confidence", 72.0)
    state.evidence_satellite_confidence = api_data.get("satellite_confidence", 80.0)
    state.evidence_citizen_confidence = api_data.get("citizen_confidence", 65.0)
    state.evidence_overall_confidence = api_data.get("overall_confidence", 80.0)

    # Lead time
    state.lead_time_hours = api_data.get("lead_time_hours", 24)
    state.lead_time_action = api_data.get("lead_time_action", "MONITOR CONDITIONS")

    # Weather
    state.rainfall_mm = api_data.get("rainfall_mm", 75.0)
    state.forecast_24h_mm = api_data.get("forecast_24h_mm", 45.0)
    state.forecast_48h_mm = api_data.get("forecast_48h_mm", 60.0)
    state.forecast_72h_mm = api_data.get("forecast_72h_mm", 30.0)

    return state


# Default state for testing
default_state = DashboardState()
