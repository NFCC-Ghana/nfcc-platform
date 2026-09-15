"""Unified Hydrological Intelligence - Complete integration of all components."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from .flood_polygons import flood_polygons
from .rainfall_history import rainfall_history
from .reservoir_intelligence import reservoir_intelligence
from .river_intelligence import river_intelligence
from .soil_moisture import soil_moisture

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UnifiedHydrologicalIntelligence:
    """Unified intelligence integrating all hydrological components."""

    def __init__(self):
        self.components = {
            "rainfall": rainfall_history,
            "rivers": river_intelligence,
            "reservoirs": reservoir_intelligence,
            "soil": soil_moisture,
            "floods": flood_polygons,
        }
        logger.info("Unified Hydrological Intelligence initialized")

    def get_complete_risk_assessment(
        self, district: str, rainfall_mm: Optional[float] = None
    ) -> Dict:
        """Get complete flood risk assessment for a district."""
        try:
            # 1. Get rainfall features
            rainfall_data = rainfall_history.get_district_rainfall_features(district)
            if rainfall_mm is None:
                rainfall_mm = rainfall_data.get("rainfall_mm", 0)
            rainfall_data["rainfall_mm"] = rainfall_mm

            # 2. Get river status
            river_status = river_intelligence.get_river_status(district)

            # 3. Get reservoir/dam status
            dam_risk = reservoir_intelligence.get_downstream_risk(district)

            # 4. Get soil moisture
            soil_status = soil_moisture.get_soil_moisture(district, rainfall_mm)

            # 5. Get historical flood risk
            flood_history = flood_polygons.get_flood_risk_summary(district)

            # 6. Get inundation risk
            inundation_risk = flood_polygons.get_flood_inundation_risk(
                district, rainfall_mm
            )

            # 7. Get runoff forecast
            runoff_forecast = soil_moisture.get_runoff_forecast(district, rainfall_mm)

            # 8. Calculate composite risk score
            risk_factors = self._calculate_risk_factors(
                rainfall_data, river_status, dam_risk, soil_status, flood_history
            )

            # 9. Generate recommendations
            recommendations = self._generate_recommendations(
                district,
                risk_factors,
                river_status,
                dam_risk,
                soil_status,
                runoff_forecast,
            )

            return {
                "district": district,
                "timestamp": datetime.now().isoformat(),
                "rainfall": {
                    "current_mm": rainfall_mm,
                    "rain_3d_mm": rainfall_data.get("rain_3d", 0),
                    "rain_7d_mm": rainfall_data.get("rain_7d", 0),
                    "rain_30d_mm": rainfall_data.get("rain_30d", 0),
                    "percentile_rank": rainfall_data.get("percentile_rank", 50),
                    "seasonal_anomaly": rainfall_data.get("seasonal_anomaly", 0),
                    "is_extreme": rainfall_data.get("is_extreme", False),
                    "recurrence_years": rainfall_data.get("recurrence_years", 0),
                },
                "river": river_status,
                "dam_risk": dam_risk,
                "soil": {
                    "saturation_index": soil_status.get("saturation_index", 0.5),
                    "saturation_percent": soil_status.get("saturation_percent", 50),
                    "runoff_potential": soil_status.get("runoff_potential", "LOW"),
                    "flash_flood_risk": soil_status.get("flash_flood_risk", "LOW"),
                    "runoff_description": soil_status.get("runoff_description", ""),
                    "runoff_forecast": runoff_forecast,
                },
                "history": {
                    "total_events": flood_history.get("total_events", 0),
                    "risk_level": flood_history.get("risk_level", "LOW"),
                    "similar_events": inundation_risk.get("similar_event", "None"),
                    "estimated_affected": inundation_risk.get("estimated_affected", 0),
                },
                "composite_risk": {
                    "score": risk_factors["total_score"],
                    "category": risk_factors["category"],
                    "confidence": risk_factors["confidence"],
                },
                "recommendations": recommendations,
                "details": {
                    "risk_factors": risk_factors,
                    "rainfall_data": rainfall_data,
                    "river_data": river_status,
                    "dam_data": dam_risk,
                    "soil_data": soil_status,
                    "historical_data": flood_history,
                    "inundation_data": inundation_risk,
                },
            }
        except Exception as e:
            logger.error(f"Error in risk assessment: {e}")
            return self._get_fallback_assessment(district, rainfall_mm)

    def _get_fallback_assessment(self, district: str, rainfall_mm: float) -> Dict:
        """Return fallback assessment when main calculation fails."""
        return {
            "district": district,
            "timestamp": datetime.now().isoformat(),
            "rainfall": {
                "current_mm": rainfall_mm,
                "rain_3d_mm": rainfall_mm * 2.3,
                "rain_7d_mm": rainfall_mm * 4.9,
                "rain_30d_mm": rainfall_mm * 21.2,
                "percentile_rank": 50,
                "seasonal_anomaly": 0,
                "is_extreme": rainfall_mm > 50,
                "recurrence_years": 0,
            },
            "river": {"river": "Unknown", "current_level_m": 0.5, "status": "NORMAL"},
            "dam_risk": {"total_risk": "LOW", "dams_at_risk": 0},
            "soil": {
                "saturation_index": 0.5,
                "saturation_percent": 50,
                "runoff_potential": "MODERATE",
                "flash_flood_risk": "LOW",
                "runoff_description": "Soil moderately wet",
                "runoff_forecast": {"runoff_risk": "LOW"},
            },
            "history": {"total_events": 0, "risk_level": "LOW"},
            "composite_risk": {"score": 50, "category": "MODERATE", "confidence": 0.7},
            "recommendations": [
                {
                    "priority": "LOW",
                    "action": "Monitor conditions",
                    "target": "All residents",
                    "timeframe": "Ongoing",
                }
            ],
            "details": {
                "risk_factors": {
                    "factors": {
                        "rainfall": 50,
                        "river": 30,
                        "dam": 20,
                        "soil": 50,
                        "history": 20,
                    }
                }
            },
        }

    def _calculate_risk_factors(
        self, rainfall: Dict, river: Dict, dam: Dict, soil: Dict, history: Dict
    ) -> Dict:
        """Calculate composite risk factors."""
        weights = {
            "rainfall": 0.25,
            "river": 0.20,
            "dam": 0.15,
            "soil": 0.20,
            "history": 0.20,
        }
        factors = {}

        # Rainfall factor
        rain_30d = rainfall.get("rain_30d", 0)
        rain_score = min(100, rain_30d * 0.8)
        if rainfall.get("is_extreme"):
            rain_score = min(100, rain_score + 20)
        factors["rainfall"] = rain_score

        # River factor
        river_status = river.get("status", "NORMAL")
        if river_status == "FLOOD":
            river_score = 100
        elif river_status == "DANGER":
            river_score = 85
        elif river_status == "WARNING":
            river_score = 65
        else:
            river_score = 30
        factors["river"] = river_score

        # Dam factor
        dam_risk = dam.get("total_risk", "LOW")
        factors["dam"] = (
            80 if dam_risk == "HIGH" else 50 if dam_risk == "MEDIUM" else 20
        )

        # Soil factor
        saturation = soil.get("saturation_index", 0.5)
        factors["soil"] = min(100, saturation * 100)

        # Historical factor
        hist_risk = history.get("risk_level", "LOW")
        if hist_risk == "CRITICAL":
            hist_score = 90
        elif hist_risk == "HIGH":
            hist_score = 70
        elif hist_risk == "MODERATE":
            hist_score = 45
        else:
            hist_score = 20
        factors["history"] = hist_score

        # Weighted total
        total_score = sum(factors[k] * weights[k] for k in factors)
        total_score = min(100, total_score)

        if total_score >= 80:
            category, confidence = "EXTREME", 0.9
        elif total_score >= 60:
            category, confidence = "HIGH", 0.8
        elif total_score >= 40:
            category, confidence = "MODERATE", 0.7
        elif total_score >= 20:
            category, confidence = "LOW", 0.6
        else:
            category, confidence = "VERY_LOW", 0.5

        return {
            "factors": factors,
            "total_score": round(total_score, 1),
            "category": category,
            "confidence": confidence,
        }

    def _generate_recommendations(
        self,
        district: str,
        risk: Dict,
        river: Dict,
        dam: Dict,
        soil: Dict,
        runoff: Dict,
    ) -> List[Dict]:
        """Generate actionable recommendations."""
        recommendations = []
        score = risk["total_score"]

        # Critical: Immediate evacuation
        if score >= 80:
            recommendations.append(
                {
                    "priority": "CRITICAL",
                    "action": "🚨 IMMEDIATE EVACUATION - Seek higher ground",
                    "target": "All residents",
                    "timeframe": "Now",
                }
            )

        # Soil saturation recommendations
        saturation = soil.get("saturation_percent", 50)
        if saturation > 80:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "action": f"💧 Soil saturation at {saturation:.0f}% - Expect rapid runoff",
                    "target": "Communities in low-lying areas",
                    "timeframe": "Next 24 hours",
                }
            )
        elif saturation > 60:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "action": f"💧 Soil saturation at {saturation:.0f}% - Monitor for runoff",
                    "target": "Communities near rivers",
                    "timeframe": "Today",
                }
            )

        # Runoff recommendations
        runoff_risk = runoff.get("runoff_risk", "LOW")
        if runoff_risk == "EXTREME":
            recommendations.append(
                {
                    "priority": "CRITICAL",
                    "action": "🌊 EXTREME runoff expected - Flash flooding imminent",
                    "target": "All residents in flood zones",
                    "timeframe": "Next 6 hours",
                }
            )
        elif runoff_risk == "HIGH":
            recommendations.append(
                {
                    "priority": "HIGH",
                    "action": "⚠️ Significant runoff expected - Prepare for flooding",
                    "target": "Residents near drainage channels",
                    "timeframe": "Next 12 hours",
                }
            )

        # River-specific
        river_status = river.get("status", "NORMAL")
        if river_status in ["FLOOD", "DANGER"]:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "action": f"🌊 River level at {river.get('current_level_m', 0)}m - Avoid flood zones",
                    "target": f"Communities near {river.get('river', 'river')}",
                    "timeframe": "Immediate",
                }
            )

        # Dam-specific
        dam_risk = dam.get("total_risk", "LOW")
        if dam_risk == "HIGH":
            for d in dam.get("dams_at_risk", []):
                recommendations.append(
                    {
                        "priority": "HIGH",
                        "action": f"🏗️ {d.get('dam_name', 'Dam')} at spillage risk - Monitor closely",
                        "target": "Downstream communities",
                        "timeframe": "Next 48 hours",
                    }
                )

        # Historical pattern
        if risk.get("factors", {}).get("history", 0) > 60:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "action": "📊 Similar to past flood events - Review preparedness",
                    "target": "District NADMO",
                    "timeframe": "Today",
                }
            )

        # General awareness
        if score >= 40:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "action": "📢 Issue public awareness messages",
                    "target": "All residents",
                    "timeframe": "Today",
                }
            )

        # Default
        if not recommendations:
            recommendations.append(
                {
                    "priority": "LOW",
                    "action": "✅ No immediate flood risk - Continue monitoring",
                    "target": "All residents",
                    "timeframe": "Ongoing",
                }
            )

        # Sort by priority
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 4))
        return recommendations


# Singleton instance
unified_intelligence = UnifiedHydrologicalIntelligence()
