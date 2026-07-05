"""DashboardState - Single source of truth for all dashboard data."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class DashboardState:
    """Complete dashboard state - the single source of truth."""
    
    # District & Location
    district: str = "Accra Central"
    region: str = "Greater Accra"
    population: int = 187928
    lat: float = 5.560
    lon: float = -0.210
    
    # Weather & Rainfall
    rainfall_mm: float = 75.0
    rain_3d: float = 0.0
    rain_7d: float = 0.0
    rain_30d: float = 0.0
    
    # Risk Assessment
    risk_score: float = 50.0
    risk_category: str = "MODERATE"
    confidence: float = 0.80
    
    # River Intelligence
    river_name: str = "Odaw"
    river_level_m: float = 0.45
    river_status: str = "NORMAL"
    river_flow_m3s: float = 0.0
    
    # Soil Intelligence
    soil_saturation: float = 65.0
    runoff_potential: str = "MODERATE"
    flash_flood_risk: str = "LOW"
    
    # Dam Intelligence
    dam_risk: str = "LOW"
    dams_at_risk: int = 0
    
    # Historical Context
    past_events: int = 1
    historical_risk: str = "LOW"
    
    # Impact Assessment
    population_exposed: int = 0
    children_exposed: int = 0
    elderly_exposed: int = 0
    disabled_exposed: int = 0
    schools_exposed: int = 0
    hospitals_exposed: int = 0
    markets_exposed: int = 0
    
    # Economic Impact
    residential_loss_ghs: float = 0.0
    infrastructure_loss_ghs: float = 0.0
    total_loss_ghs: float = 0.0
    recovery_weeks: float = 0.0
    
    # Community Reports
    community_reports: List[Dict] = field(default_factory=list)
    verified_reports: int = 0
    total_reports: int = 0
    
    # Recommendations
    recommendations: List[Dict] = field(default_factory=list)
    
    # Timestamp
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Data Sources
    active_sources: List[str] = field(default_factory=list)
    
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
    
    def to_dict(self) -> Dict:
        return {
            "district": self.district,
            "region": self.region,
            "population": self.population,
            "rainfall_mm": self.rainfall_mm,
            "risk_score": self.risk_score,
            "risk_category": self.risk_category,
            "confidence": self.confidence,
            "river_name": self.river_name,
            "river_level_m": self.river_level_m,
            "river_status": self.river_status,
            "soil_saturation": self.soil_saturation,
            "active_sources": self.active_sources,
            "active_sources_count": self.active_sources_count,
            "timestamp": self.timestamp
        }


def create_state_from_api(api_data: Dict) -> DashboardState:
    """Create a DashboardState from API response."""
    state = DashboardState()
    
    if "location" in api_data:
        state.district = api_data["location"]
    
    if "score" in api_data:
        state.risk_score = api_data["score"]
    
    if "risk_tier" in api_data:
        state.risk_category = api_data["risk_tier"]
    
    if "precipitation" in api_data:
        state.rainfall_mm = api_data["precipitation"]
    
    state.active_sources = [
        "CHIRPS Rainfall",
        "Open-Meteo Forecast",
        "NASA SMAP",
        "Sentinel-1 SAR",
        "Ghana River Gauges",
        "Dam Database"
    ]
    
    return state


default_state = DashboardState()
