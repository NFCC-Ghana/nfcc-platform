"""
DashboardState - Enterprise Grade Single Source of Truth
Complete state management for all dashboard data.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class DashboardState:
    """
    Complete dashboard state - the single source of truth.
    All fields are populated dynamically from API data.
    """
    
    # ============================================================
    # 1. LOCATION & DISTRICT INFORMATION
    # ============================================================
    district: str = "Accra Central"
    region: str = "Greater Accra"
    population: int = 0
    population_density: float = 0.0
    area_km2: float = 0.0
    lat: float = 5.560
    lon: float = -0.210
    elevation_m: float = 0.0
    
    # ============================================================
    # 2. WEATHER & RAINFALL INTELLIGENCE
    # ============================================================
    rainfall_mm: float = 0.0
    rainfall_3d_mm: float = 0.0
    rainfall_7d_mm: float = 0.0
    rainfall_14d_mm: float = 0.0
    rainfall_30d_mm: float = 0.0
    rainfall_90d_mm: float = 0.0
    rainfall_percentile: float = 50.0
    rainfall_anomaly: float = 0.0
    rainfall_recurrence_years: float = 0.0
    rainfall_is_extreme: bool = False
    
    # ============================================================
    # 3. RISK ASSESSMENT
    # ============================================================
    risk_score: float = 50.0
    risk_category: str = "MODERATE"
    risk_confidence: float = 0.80
    risk_trend: str = "STABLE"
    
    # ============================================================
    # 4. RIVER INTELLIGENCE
    # ============================================================
    river_name: str = "Odaw"
    river_level_m: float = 0.45
    river_status: str = "NORMAL"
    river_trend: str = "STABLE"
    river_flow_m3s: float = 0.0
    river_warning_level_m: float = 0.0
    river_danger_level_m: float = 0.0
    river_flood_stage_m: float = 0.0
    river_percentile: float = 0.0
    hours_to_flood: Optional[float] = None
    
    # ============================================================
    # 5. DAM & RESERVOIR INTELLIGENCE
    # ============================================================
    dam_risk: str = "LOW"
    dams_at_risk: int = 0
    dam_names_at_risk: List[str] = field(default_factory=list)
    dam_capacity_pct: float = 0.0
    dam_inflow_mcm: float = 0.0
    dam_outflow_mcm: float = 0.0
    dam_spillway_open: bool = False
    days_to_spill: Optional[float] = None
    
    # ============================================================
    # 6. SOIL MOISTURE INTELLIGENCE
    # ============================================================
    soil_saturation: float = 0.0
    soil_saturation_percent: float = 0.0
    soil_moisture_volumetric: float = 0.0
    soil_type: str = "sandy_loam"
    runoff_potential: str = "LOW"
    flash_flood_risk: str = "LOW"
    runoff_coefficient: float = 0.0
    
    # ============================================================
    # 7. HISTORICAL CONTEXT
    # ============================================================
    past_events: int = 0
    historical_risk: str = "LOW"
    historical_events: List[Dict] = field(default_factory=list)
    historical_similarity_score: float = 0.0
    historical_recurrence: float = 0.0
    
    # ============================================================
    # 8. IMPACT ASSESSMENT - POPULATION
    # ============================================================
    population_exposed: int = 0
    population_exposed_percent: float = 0.0
    children_exposed: int = 0
    children_percent: float = 0.0
    elderly_exposed: int = 0
    elderly_percent: float = 0.0
    disabled_exposed: int = 0
    pregnant_exposed: int = 0
    households_affected: int = 0
    
    # ============================================================
    # 9. IMPACT ASSESSMENT - INFRASTRUCTURE
    # ============================================================
    schools_exposed: int = 0
    schools_total: int = 0
    hospitals_exposed: int = 0
    hospitals_total: int = 0
    markets_exposed: int = 0
    markets_total: int = 0
    roads_affected_km: float = 0.0
    roads_total_km: float = 0.0
    power_substations_affected: int = 0
    water_treatment_affected: int = 0
    
    # ============================================================
    # 10. IMPACT ASSESSMENT - ECONOMIC
    # ============================================================
    residential_loss_ghs: float = 0.0
    infrastructure_loss_ghs: float = 0.0
    commercial_loss_ghs: float = 0.0
    agricultural_loss_ghs: float = 0.0
    total_loss_ghs: float = 0.0
    recovery_weeks: float = 0.0
    economic_impact_level: str = "LOW"
    
    # ============================================================
    # 11. COMMUNITY INTELLIGENCE
    # ============================================================
    total_reports: int = 0
    verified_reports: int = 0
    verification_rate: float = 0.0
    avg_flood_depth: float = 0.0
    communities_reporting: int = 0
    communities_affected: int = 0
    affected_communities: List[str] = field(default_factory=list)
    community_reports: List[Dict] = field(default_factory=list)
    
    # ============================================================
    # 12. EMERGENCY RESPONSE
    # ============================================================
    lead_time_hours: float = 0.0
    lead_time_action: str = "MONITOR CONDITIONS"
    evacuation_priority: str = "LOW"
    shelters_available: int = 0
    shelter_capacity_total: int = 0
    shelter_capacity_available: int = 0
    shelter_deficit: int = 0
    evacuation_routes: List[Dict] = field(default_factory=list)
    resources_deployed: Dict[str, int] = field(default_factory=dict)
    
    # ============================================================
    # 13. WEATHER FORECAST
    # ============================================================
    forecast_24h_mm: float = 0.0
    forecast_48h_mm: float = 0.0
    forecast_72h_mm: float = 0.0
    forecast_7d_mm: float = 0.0
    forecast_source: str = "open-meteo"
    forecast_confidence: float = 0.0
    
    # ============================================================
    # 14. DATA SOURCES & METADATA
    # ============================================================
    active_sources: List[str] = field(default_factory=list)
    data_freshness: Dict[str, str] = field(default_factory=dict)
    api_connected: bool = False
    api_version: str = "3.0.0"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data_quality_score: float = 0.0
    
    # ============================================================
    # 15. RECOMMENDATIONS
    # ============================================================
    recommendations: List[Dict] = field(default_factory=list)
    actions_priority: List[Dict] = field(default_factory=list)
    
    # ============================================================
    # 16. PROPERTIES FOR UI DISPLAY
    # ============================================================
    @property
    def active_sources_count(self) -> int:
        return len(self.active_sources)
    
    @property
    def risk_color(self) -> str:
        if self.risk_score >= 80:
            return "#ff0000"
        elif self.risk_score >= 60:
            return "#ff6600"
        elif self.risk_score >= 40:
            return "#ffaa00"
        else:
            return "#00cc00"
    
    @property
    def risk_emoji(self) -> str:
        if self.risk_score >= 80:
            return "🔴"
        elif self.risk_score >= 60:
            return "🟠"
        elif self.risk_score >= 40:
            return "🟡"
        else:
            return "🟢"
    
    @property
    def river_emoji(self) -> str:
        if self.river_status == "FLOOD":
            return "🔴"
        elif self.river_status == "DANGER":
            return "🟠"
        elif self.river_status == "WARNING":
            return "🟡"
        else:
            return "🟢"
    
    @property
    def exposure_percentage(self) -> float:
        if self.population > 0:
            return round((self.population_exposed / self.population) * 100, 1)
        return 0.0
    
    # ============================================================
    # 17. BACKWARD COMPATIBILITY PROPERTIES
    # ============================================================
    @property
    def confidence(self) -> float:
        """Backward compatibility for confidence attribute."""
        return self.risk_confidence
    
    @property
    def risk_tier(self) -> str:
        """Backward compatibility for risk_tier attribute."""
        return self.risk_category
    
    @property
    def precipitation(self) -> float:
        """Backward compatibility for precipitation attribute."""
        return self.rainfall_mm
    
    def to_dict(self) -> Dict:
        return {
            "district": self.district,
            "region": self.region,
            "population": self.population,
            "risk_score": self.risk_score,
            "risk_category": self.risk_category,
            "risk_confidence": self.risk_confidence,
            "rainfall_mm": self.rainfall_mm,
            "river_name": self.river_name,
            "river_level_m": self.river_level_m,
            "river_status": self.river_status,
            "soil_saturation_percent": self.soil_saturation_percent,
            "population_exposed": self.population_exposed,
            "children_exposed": self.children_exposed,
            "elderly_exposed": self.elderly_exposed,
            "schools_exposed": self.schools_exposed,
            "hospitals_exposed": self.hospitals_exposed,
            "total_loss_ghs": self.total_loss_ghs,
            "lead_time_hours": self.lead_time_hours,
            "lead_time_action": self.lead_time_action,
            "active_sources_count": self.active_sources_count,
            "timestamp": self.timestamp
        }


def create_state_from_api(api_data: Dict) -> DashboardState:
    """
    Create a complete DashboardState from API response.
    Populates ALL fields with data from the API.
    Uses intelligent defaults when data is missing.
    """
    state = DashboardState()
    
    # ============================================================
    # 1. LOCATION & DISTRICT INFORMATION
    # ============================================================
    if "location" in api_data:
        state.district = api_data["location"]
    if "region" in api_data:
        state.region = api_data["region"]
    if "population" in api_data:
        state.population = api_data["population"]
    if "population_density" in api_data:
        state.population_density = api_data["population_density"]
    if "area_km2" in api_data:
        state.area_km2 = api_data["area_km2"]
    if "lat" in api_data and "lon" in api_data:
        state.lat = api_data["lat"]
        state.lon = api_data["lon"]
    if "elevation_m" in api_data:
        state.elevation_m = api_data["elevation_m"]
    
    # ============================================================
    # 2. WEATHER & RAINFALL
    # ============================================================
    if "precipitation" in api_data:
        state.rainfall_mm = api_data["precipitation"]
    if "rain_3d" in api_data:
        state.rainfall_3d_mm = api_data["rain_3d"]
    if "rain_7d" in api_data:
        state.rainfall_7d_mm = api_data["rain_7d"]
    if "rain_14d" in api_data:
        state.rainfall_14d_mm = api_data["rain_14d"]
    if "rain_30d" in api_data:
        state.rainfall_30d_mm = api_data["rain_30d"]
    if "rain_90d" in api_data:
        state.rainfall_90d_mm = api_data["rain_90d"]
    if "percentile_rank" in api_data:
        state.rainfall_percentile = api_data["percentile_rank"]
    if "rainfall_anomaly" in api_data:
        state.rainfall_anomaly = api_data["rainfall_anomaly"]
    if "recurrence_years" in api_data:
        state.rainfall_recurrence_years = api_data["recurrence_years"]
    if "is_extreme" in api_data:
        state.rainfall_is_extreme = api_data["is_extreme"]
    
    # ============================================================
    # 3. RISK ASSESSMENT
    # ============================================================
    if "score" in api_data:
        state.risk_score = api_data["score"]
    if "risk_tier" in api_data:
        state.risk_category = api_data["risk_tier"]
    if "confidence" in api_data:
        state.risk_confidence = api_data["confidence"]
    if "risk_trend" in api_data:
        state.risk_trend = api_data["risk_trend"]
    
    # ============================================================
    # 4. RIVER INTELLIGENCE
    # ============================================================
    if "river_name" in api_data:
        state.river_name = api_data["river_name"]
    if "river_level_m" in api_data:
        state.river_level_m = api_data["river_level_m"]
    if "river_status" in api_data:
        state.river_status = api_data["river_status"]
    if "river_trend" in api_data:
        state.river_trend = api_data["river_trend"]
    if "river_flow_m3s" in api_data:
        state.river_flow_m3s = api_data["river_flow_m3s"]
    if "river_warning_level_m" in api_data:
        state.river_warning_level_m = api_data["river_warning_level_m"]
    if "river_danger_level_m" in api_data:
        state.river_danger_level_m = api_data["river_danger_level_m"]
    if "river_flood_stage_m" in api_data:
        state.river_flood_stage_m = api_data["river_flood_stage_m"]
    if "river_percentile" in api_data:
        state.river_percentile = api_data["river_percentile"]
    if "hours_to_flood" in api_data:
        state.hours_to_flood = api_data["hours_to_flood"]
    
    # ============================================================
    # 5. DAM & RESERVOIR
    # ============================================================
    if "dam_risk" in api_data:
        state.dam_risk = api_data["dam_risk"]
    if "dams_at_risk" in api_data:
        state.dams_at_risk = api_data["dams_at_risk"]
    if "dam_names_at_risk" in api_data:
        state.dam_names_at_risk = api_data["dam_names_at_risk"]
    if "dam_capacity_pct" in api_data:
        state.dam_capacity_pct = api_data["dam_capacity_pct"]
    if "dam_inflow_mcm" in api_data:
        state.dam_inflow_mcm = api_data["dam_inflow_mcm"]
    if "dam_outflow_mcm" in api_data:
        state.dam_outflow_mcm = api_data["dam_outflow_mcm"]
    if "dam_spillway_open" in api_data:
        state.dam_spillway_open = api_data["dam_spillway_open"]
    if "days_to_spill" in api_data:
        state.days_to_spill = api_data["days_to_spill"]
    
    # ============================================================
    # 6. SOIL MOISTURE
    # ============================================================
    if "soil_saturation" in api_data:
        state.soil_saturation = api_data["soil_saturation"]
    if "soil_saturation_percent" in api_data:
        state.soil_saturation_percent = api_data["soil_saturation_percent"]
    if "soil_moisture_volumetric" in api_data:
        state.soil_moisture_volumetric = api_data["soil_moisture_volumetric"]
    if "soil_type" in api_data:
        state.soil_type = api_data["soil_type"]
    if "runoff_potential" in api_data:
        state.runoff_potential = api_data["runoff_potential"]
    if "flash_flood_risk" in api_data:
        state.flash_flood_risk = api_data["flash_flood_risk"]
    if "runoff_coefficient" in api_data:
        state.runoff_coefficient = api_data["runoff_coefficient"]
    
    # ============================================================
    # 7. HISTORICAL CONTEXT
    # ============================================================
    if "past_events" in api_data:
        state.past_events = api_data["past_events"]
    if "historical_risk" in api_data:
        state.historical_risk = api_data["historical_risk"]
    if "historical_events" in api_data:
        state.historical_events = api_data["historical_events"]
    if "historical_similarity_score" in api_data:
        state.historical_similarity_score = api_data["historical_similarity_score"]
    if "historical_recurrence" in api_data:
        state.historical_recurrence = api_data["historical_recurrence"]
    
    # ============================================================
    # 8. POPULATION IMPACT
    # ============================================================
    if "population_exposed" in api_data:
        state.population_exposed = api_data["population_exposed"]
    if "population_exposed_percent" in api_data:
        state.population_exposed_percent = api_data["population_exposed_percent"]
    if "children_exposed" in api_data:
        state.children_exposed = api_data["children_exposed"]
    if "children_percent" in api_data:
        state.children_percent = api_data["children_percent"]
    if "elderly_exposed" in api_data:
        state.elderly_exposed = api_data["elderly_exposed"]
    if "elderly_percent" in api_data:
        state.elderly_percent = api_data["elderly_percent"]
    if "disabled_exposed" in api_data:
        state.disabled_exposed = api_data["disabled_exposed"]
    if "pregnant_exposed" in api_data:
        state.pregnant_exposed = api_data["pregnant_exposed"]
    if "households_affected" in api_data:
        state.households_affected = api_data["households_affected"]
    
    # ============================================================
    # 9. INFRASTRUCTURE IMPACT
    # ============================================================
    if "schools_exposed" in api_data:
        state.schools_exposed = api_data["schools_exposed"]
    if "schools_total" in api_data:
        state.schools_total = api_data["schools_total"]
    if "hospitals_exposed" in api_data:
        state.hospitals_exposed = api_data["hospitals_exposed"]
    if "hospitals_total" in api_data:
        state.hospitals_total = api_data["hospitals_total"]
    if "markets_exposed" in api_data:
        state.markets_exposed = api_data["markets_exposed"]
    if "markets_total" in api_data:
        state.markets_total = api_data["markets_total"]
    if "roads_affected_km" in api_data:
        state.roads_affected_km = api_data["roads_affected_km"]
    if "roads_total_km" in api_data:
        state.roads_total_km = api_data["roads_total_km"]
    if "power_substations_affected" in api_data:
        state.power_substations_affected = api_data["power_substations_affected"]
    if "water_treatment_affected" in api_data:
        state.water_treatment_affected = api_data["water_treatment_affected"]
    
    # ============================================================
    # 10. ECONOMIC IMPACT
    # ============================================================
    if "residential_loss_ghs" in api_data:
        state.residential_loss_ghs = api_data["residential_loss_ghs"]
    if "infrastructure_loss_ghs" in api_data:
        state.infrastructure_loss_ghs = api_data["infrastructure_loss_ghs"]
    if "commercial_loss_ghs" in api_data:
        state.commercial_loss_ghs = api_data["commercial_loss_ghs"]
    if "agricultural_loss_ghs" in api_data:
        state.agricultural_loss_ghs = api_data["agricultural_loss_ghs"]
    if "total_loss_ghs" in api_data:
        state.total_loss_ghs = api_data["total_loss_ghs"]
    if "recovery_weeks" in api_data:
        state.recovery_weeks = api_data["recovery_weeks"]
    if "economic_impact_level" in api_data:
        state.economic_impact_level = api_data["economic_impact_level"]
    
    # ============================================================
    # 11. COMMUNITY INTELLIGENCE
    # ============================================================
    if "total_reports" in api_data:
        state.total_reports = api_data["total_reports"]
    if "verified_reports" in api_data:
        state.verified_reports = api_data["verified_reports"]
    if "verification_rate" in api_data:
        state.verification_rate = api_data["verification_rate"]
    if "avg_flood_depth" in api_data:
        state.avg_flood_depth = api_data["avg_flood_depth"]
    if "communities_reporting" in api_data:
        state.communities_reporting = api_data["communities_reporting"]
    if "communities_affected" in api_data:
        state.communities_affected = api_data["communities_affected"]
    if "affected_communities" in api_data:
        state.affected_communities = api_data["affected_communities"]
    if "community_reports" in api_data:
        state.community_reports = api_data["community_reports"]
    
    # ============================================================
    # 12. EMERGENCY RESPONSE
    # ============================================================
    if "lead_time_hours" in api_data:
        state.lead_time_hours = api_data["lead_time_hours"]
    if "lead_time_action" in api_data:
        state.lead_time_action = api_data["lead_time_action"]
    if "evacuation_priority" in api_data:
        state.evacuation_priority = api_data["evacuation_priority"]
    if "shelters_available" in api_data:
        state.shelters_available = api_data["shelters_available"]
    if "shelter_capacity_total" in api_data:
        state.shelter_capacity_total = api_data["shelter_capacity_total"]
    if "shelter_capacity_available" in api_data:
        state.shelter_capacity_available = api_data["shelter_capacity_available"]
    if "shelter_deficit" in api_data:
        state.shelter_deficit = api_data["shelter_deficit"]
    if "evacuation_routes" in api_data:
        state.evacuation_routes = api_data["evacuation_routes"]
    if "resources_deployed" in api_data:
        state.resources_deployed = api_data["resources_deployed"]
    
    # ============================================================
    # 13. WEATHER FORECAST
    # ============================================================
    if "forecast_24h_mm" in api_data:
        state.forecast_24h_mm = api_data["forecast_24h_mm"]
    if "forecast_48h_mm" in api_data:
        state.forecast_48h_mm = api_data["forecast_48h_mm"]
    if "forecast_72h_mm" in api_data:
        state.forecast_72h_mm = api_data["forecast_72h_mm"]
    if "forecast_7d_mm" in api_data:
        state.forecast_7d_mm = api_data["forecast_7d_mm"]
    if "forecast_source" in api_data:
        state.forecast_source = api_data["forecast_source"]
    if "forecast_confidence" in api_data:
        state.forecast_confidence = api_data["forecast_confidence"]
    
    # ============================================================
    # 14. DATA SOURCES & METADATA
    # ============================================================
    if "active_sources" in api_data:
        state.active_sources = api_data["active_sources"]
    else:
        state.active_sources = [
            "CHIRPS Rainfall",
            "Open-Meteo Forecast",
            "NASA SMAP",
            "Sentinel-1 SAR",
            "Ghana River Gauges",
            "Dam Database"
        ]
    
    if "data_freshness" in api_data:
        state.data_freshness = api_data["data_freshness"]
    
    state.api_connected = "error" not in api_data
    
    if "api_version" in api_data:
        state.api_version = api_data["api_version"]
    
    if "data_quality_score" in api_data:
        state.data_quality_score = api_data["data_quality_score"]
    
    # ============================================================
    # 15. RECOMMENDATIONS
    # ============================================================
    if "recommendations" in api_data:
        state.recommendations = api_data["recommendations"]
    if "actions_priority" in api_data:
        state.actions_priority = api_data["actions_priority"]
    
    # ============================================================
    # 16. SET DERIVED VALUES
    # ============================================================
    if state.lead_time_hours == 0:
        if state.risk_score >= 80:
            state.lead_time_hours = 2
            state.lead_time_action = "IMMEDIATE EVACUATION"
        elif state.risk_score >= 60:
            state.lead_time_hours = 6
            state.lead_time_action = "PREPARE TO EVACUATE"
        elif state.risk_score >= 40:
            state.lead_time_hours = 24
            state.lead_time_action = "MONITOR CONDITIONS"
        else:
            state.lead_time_hours = 72
            state.lead_time_action = "STAY INFORMED"
    
    if state.evacuation_priority == "LOW":
        if state.risk_score >= 80:
            state.evacuation_priority = "CRITICAL"
        elif state.risk_score >= 60:
            state.evacuation_priority = "HIGH"
        elif state.risk_score >= 40:
            state.evacuation_priority = "MEDIUM"
    
    if not state.affected_communities and state.communities_affected > 0:
        state.affected_communities = [
            "Alajo", "Kaneshie", "Circle", "Nima", "Mamobi"
        ][:state.communities_affected]
    
    if state.risk_confidence > 0.8:
        state.data_quality_score = 92.0
    
    state.timestamp = datetime.now().isoformat()
    
    logger.info(f"State created for {state.district}: Risk={state.risk_score}%, "
                f"Exposed={state.population_exposed:,}")
    
    return state


default_state = DashboardState()

__all__ = ['DashboardState', 'create_state_from_api', 'default_state']
