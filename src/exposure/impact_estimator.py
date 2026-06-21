"""Complete impact estimator with lead time and vulnerable populations."""

from typing import Dict, List, Optional
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImpactEstimator:
    """
    Complete impact estimation with:
    - Population exposed (total, children, elderly, disabled)
    - Schools at risk
    - Hospitals affected
    - Lead time before flooding
    - Actionable recommendations
    """

    def __init__(self):
        self.district_data = self._load_district_data()
        self.lead_time_estimates = self._load_lead_time_estimates()
        logger.info("Impact Estimator initialized")

    def _load_district_data(self) -> Dict:
        """Load district population and infrastructure data."""
        return {
            "Accra Central": {
                "population": 187928,
                "schools": 52,
                "hospitals": 8,
                "markets": 15,
                "area_km2": 45.5,
                "children_pct": 0.30,
                "elderly_pct": 0.10,
                "disabled_pct": 0.02,
                "pregnant_pct": 0.015,
            },
            "Accra West": {
                "population": 203461,
                "schools": 42,
                "hospitals": 6,
                "markets": 10,
                "area_km2": 52.3,
                "children_pct": 0.30,
                "elderly_pct": 0.10,
                "disabled_pct": 0.02,
                "pregnant_pct": 0.015,
            },
            "Accra East": {
                "population": 142587,
                "schools": 38,
                "hospitals": 5,
                "markets": 8,
                "area_km2": 38.2,
                "children_pct": 0.28,
                "elderly_pct": 0.12,
                "disabled_pct": 0.02,
                "pregnant_pct": 0.012,
            },
            "Tema": {
                "population": 198742,
                "schools": 58,
                "hospitals": 10,
                "markets": 18,
                "area_km2": 38.7,
                "children_pct": 0.29,
                "elderly_pct": 0.09,
                "disabled_pct": 0.02,
                "pregnant_pct": 0.014,
            },
            "Kumasi": {
                "population": 443981,
                "schools": 85,
                "hospitals": 12,
                "markets": 25,
                "area_km2": 98.2,
                "children_pct": 0.31,
                "elderly_pct": 0.09,
                "disabled_pct": 0.02,
                "pregnant_pct": 0.013,
            },
            "Tamale": {
                "population": 371578,
                "schools": 42,
                "hospitals": 6,
                "markets": 14,
                "area_km2": 67.4,
                "children_pct": 0.32,
                "elderly_pct": 0.08,
                "disabled_pct": 0.02,
                "pregnant_pct": 0.016,
            },
            "Sekondi-Takoradi": {
                "population": 245567,
                "schools": 35,
                "hospitals": 5,
                "markets": 12,
                "area_km2": 85.2,
                "children_pct": 0.28,
                "elderly_pct": 0.10,
                "disabled_pct": 0.02,
                "pregnant_pct": 0.012,
            },
            "Cape Coast": {
                "population": 169894,
                "schools": 28,
                "hospitals": 4,
                "markets": 10,
                "area_km2": 62.4,
                "children_pct": 0.27,
                "elderly_pct": 0.11,
                "disabled_pct": 0.02,
                "pregnant_pct": 0.011,
            },
            "Ho": {
                "population": 153705,
                "schools": 30,
                "hospitals": 4,
                "markets": 8,
                "area_km2": 58.3,
                "children_pct": 0.28,
                "elderly_pct": 0.10,
                "disabled_pct": 0.02,
                "pregnant_pct": 0.012,
            },
            "Sunyani": {
                "population": 138256,
                "schools": 25,
                "hospitals": 3,
                "markets": 7,
                "area_km2": 55.7,
                "children_pct": 0.27,
                "elderly_pct": 0.11,
                "disabled_pct": 0.02,
                "pregnant_pct": 0.011,
            },
        }

    def _load_lead_time_estimates(self) -> Dict:
        """Load lead time estimates based on risk tier."""
        return {
            "EXTREME": {"hours": 2, "action": "IMMEDIATE EVACUATION", "color": "red"},
            "HIGH": {"hours": 6, "action": "PREPARE TO EVACUATE", "color": "orange"},
            "MODERATE": {
                "hours": 24,
                "action": "MONITOR CONDITIONS",
                "color": "yellow",
            },
            "LOW": {"hours": 72, "action": "STAY INFORMED", "color": "green"},
            "VERY_LOW": {"hours": 96, "action": "NORMAL ACTIVITIES", "color": "blue"},
        }

    def estimate_impact(
        self, district: str, risk_score: float, risk_tier: str = None
    ) -> Dict:
        """
        Estimate complete impact based on risk score.

        Args:
            district: District name
            risk_score: Risk score (0-100)
            risk_tier: Risk tier (EXTREME/HIGH/MODERATE/LOW)

        Returns:
            Complete impact estimates with lead time
        """
        if district not in self.district_data:
            return {"error": f"District {district} not found"}

        data = self.district_data[district]

        # Determine risk tier if not provided
        if risk_tier is None:
            risk_tier = self._get_risk_tier(risk_score)

        risk_factor = risk_score / 100

        # Get lead time
        lead_time = self.lead_time_estimates.get(
            risk_tier, self.lead_time_estimates["LOW"]
        )

        # Calculate exposed populations
        pop_exposed = int(data["population"] * risk_factor * 0.6)

        return {
            "district": district,
            "population_total": data["population"],
            "population_exposed": pop_exposed,
            "children_exposed": int(pop_exposed * data["children_pct"]),
            "elderly_exposed": int(pop_exposed * data["elderly_pct"]),
            "disabled_exposed": int(pop_exposed * data["disabled_pct"]),
            "pregnant_exposed": int(pop_exposed * data["pregnant_pct"]),
            "schools_exposed": int(data["schools"] * risk_factor * 0.5),
            "hospitals_exposed": int(data["hospitals"] * risk_factor * 0.5),
            "markets_exposed": int(data["markets"] * risk_factor * 0.5),
            "exposure_percentage": round(risk_factor * 60, 1),
            "lead_time_hours": lead_time["hours"],
            "lead_time_action": lead_time["action"],
            "lead_time_color": lead_time["color"],
            "risk_tier": risk_tier,
            "risk_score": round(risk_score, 1),
            "area_km2": data["area_km2"],
            "timestamp": datetime.now().isoformat(),
        }

    def _get_risk_tier(self, score: float) -> str:
        """Convert risk score to tier."""
        if score >= 80:
            return "EXTREME"
        elif score >= 60:
            return "HIGH"
        elif score >= 40:
            return "MODERATE"
        elif score >= 20:
            return "LOW"
        else:
            return "VERY_LOW"

    def get_vulnerable_population(self, district: str) -> Dict:
        """Get detailed vulnerable population breakdown."""
        if district not in self.district_data:
            return {"error": f"District {district} not found"}

        data = self.district_data[district]
        pop = data["population"]

        return {
            "district": district,
            "total_population": pop,
            "children_under_18": int(pop * data["children_pct"]),
            "elderly_over_60": int(pop * data["elderly_pct"]),
            "disabled": int(pop * data["disabled_pct"]),
            "pregnant_women": int(pop * data["pregnant_pct"]),
            "households": int(pop / 4.5),
        }

    def get_national_summary(self, district_impacts: Dict[str, Dict]) -> Dict:
        """Get national impact summary."""
        total_pop = 0
        total_exposed = 0
        total_schools = 0
        total_hospitals = 0

        for impact in district_impacts.values():
            total_pop += impact.get("population_total", 0)
            total_exposed += impact.get("population_exposed", 0)
            total_schools += impact.get("schools_exposed", 0)
            total_hospitals += impact.get("hospitals_exposed", 0)

        return {
            "districts_analyzed": len(district_impacts),
            "total_population": total_pop,
            "population_exposed": total_exposed,
            "exposure_percentage": (
                round((total_exposed / total_pop) * 100, 2) if total_pop > 0 else 0
            ),
            "schools_at_risk": total_schools,
            "hospitals_at_risk": total_hospitals,
            "timestamp": datetime.now().isoformat(),
        }


# Singleton instance
impact_estimator = ImpactEstimator()
