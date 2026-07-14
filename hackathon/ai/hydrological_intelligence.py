"""CivicFlood AI - Hydrological Intelligence Module.

This module provides the complete hydrological intelligence integration
for the CivicFlood AI hackathon dashboard.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Add src to path for hydrology modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.hydrology.flood_polygons import flood_polygons
from src.hydrology.rainfall_history import rainfall_history
from src.hydrology.reservoir_intelligence import reservoir_intelligence
from src.hydrology.river_intelligence import river_intelligence
from src.hydrology.soil_moisture import soil_moisture
from src.hydrology.unified_intelligence import unified_intelligence


class CivicFloodHydrologicalIntelligence:
    """
    CivicFlood AI wrapper for hydrological intelligence.

    Provides clean API for the hackathon dashboard.
    """

    def __init__(self):
        self.unified = unified_intelligence

    def get_community_risk(self, district: str, rainfall_mm: float = None) -> Dict:
        """Get complete flood risk for a community."""
        return self.unified.get_complete_risk_assessment(district, rainfall_mm)

    def get_historical_context(self, district: str) -> Dict:
        """Get historical flood context for a community."""
        history = flood_polygons.get_flood_risk_summary(district)
        similar = flood_polygons.get_similar_events(district, 50)

        return {
            "district": district,
            "total_events": history.get("total_events", 0),
            "risk_level": history.get("risk_level", "LOW"),
            "similar_events": similar[:3],
            "primary_causes": history.get("primary_causes", []),
        }

    def get_river_alert(self, district: str) -> Dict:
        """Get river alert for a community."""
        river = river_intelligence.get_river_status(district)
        return {
            "river": river.get("river", "Unknown"),
            "level_m": river.get("current_level_m", 0),
            "status": river.get("status", "NORMAL"),
            "trend": river.get("trend", "STABLE"),
            "hours_to_flood": river.get("hours_to_flood"),
        }

    def get_dam_alert(self, district: str) -> Dict:
        """Get dam alert for a community."""
        dam = reservoir_intelligence.get_downstream_risk(district)
        return {
            "total_risk": dam.get("total_risk", "LOW"),
            "dams_at_risk": len(dam.get("dams_at_risk", [])),
            "details": dam.get("dams_at_risk", []),
        }

    def get_soil_status(self, district: str) -> Dict:
        """Get soil moisture status for a community."""
        soil = soil_moisture.get_soil_moisture(district)
        return {
            "saturation_index": soil.get("saturation_index", 0.5),
            "runoff_potential": soil.get("runoff_potential", "LOW"),
            "flash_flood_risk": soil.get("flash_flood_risk", "LOW"),
        }

    def get_rainfall_analysis(self, district: str, rainfall_mm: float) -> Dict:
        """Get rainfall analysis with historical context."""
        features = rainfall_history.get_district_rainfall_features(district)
        features["current_rainfall"] = rainfall_mm
        features["is_extreme"] = rainfall_mm > 50
        return features

    def get_complete_dashboard_data(
        self, district: str, rainfall_mm: float = None
    ) -> Dict:
        """Get complete dashboard data."""
        if rainfall_mm is None:
            features = rainfall_history.get_district_rainfall_features(district)
            rainfall_mm = features.get("rainfall_mm", 0)

        risk = self.get_community_risk(district, rainfall_mm)
        river = self.get_river_alert(district)
        dam = self.get_dam_alert(district)
        soil = self.get_soil_status(district)
        history = self.get_historical_context(district)

        return {
            "district": district,
            "timestamp": datetime.now().isoformat(),
            "risk": {
                "score": risk.get("composite_risk", {}).get("score", 50),
                "category": risk.get("composite_risk", {}).get("category", "LOW"),
                "confidence": risk.get("composite_risk", {}).get("confidence", 0.5),
            },
            "rainfall": {
                "current_mm": rainfall_mm,
                "rain_3d": risk.get("rainfall", {}).get("rain_3d_mm", 0),
                "rain_7d": risk.get("rainfall", {}).get("rain_7d_mm", 0),
                "rain_30d": risk.get("rainfall", {}).get("rain_30d_mm", 0),
                "percentile": risk.get("rainfall", {}).get("percentile_rank", 50),
                "is_extreme": risk.get("rainfall", {}).get("is_extreme", False),
            },
            "river": river,
            "dam": dam,
            "soil": soil,
            "history": history,
            "recommendations": risk.get("recommendations", []),
            "risk_factors": risk.get("details", {}).get("risk_factors", {}),
        }


# Singleton instance
civicflood_hydrological = CivicFloodHydrologicalIntelligence()
