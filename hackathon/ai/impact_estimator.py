"""Impact Estimator - Estimates population, infrastructure exposure."""

import logging
from dataclasses import dataclass
from typing import Any, Dict

logger = logging.getLogger("hackathon.impact")


@dataclass
class ImpactEstimate:
    """Estimated impact of flood event."""

    population_exposed: int
    schools_affected: int
    roads_affected_km: float
    health_facilities_affected: int
    confidence: float


class ImpactEstimator:
    """Estimate impact based on flood risk and location data."""

    # District profiles (simplified for hackathon)
    DISTRICT_PROFILES = {
        "Accra Central": {
            "population": 150000,
            "schools": 45,
            "roads_km": 120,
            "health": 8,
        },
        "Accra East": {
            "population": 120000,
            "schools": 38,
            "roads_km": 95,
            "health": 6,
        },
        "Accra West": {
            "population": 100000,
            "schools": 32,
            "roads_km": 85,
            "health": 5,
        },
        "Tema": {"population": 180000, "schools": 52, "roads_km": 140, "health": 10},
        "Kumasi": {"population": 250000, "schools": 68, "roads_km": 180, "health": 12},
        "Takoradi": {"population": 90000, "schools": 28, "roads_km": 75, "health": 5},
        "Tamale": {"population": 80000, "schools": 25, "roads_km": 70, "health": 4},
    }

    # Default profile for unknown districts
    DEFAULT_PROFILE = {"population": 50000, "schools": 15, "roads_km": 50, "health": 3}

    def __init__(self):
        pass

    def estimate(self, risk_score: float, district: str) -> ImpactEstimate:
        """Estimate impact based on risk score and district."""
        profile = self.DISTRICT_PROFILES.get(district, self.DEFAULT_PROFILE)

        # Risk factor: higher risk = higher percentage of exposure
        risk_factor = min(1.0, risk_score / 100)

        # Calculate exposed population (percentage of total)
        population_exposed = int(profile["population"] * risk_factor)

        # Calculate affected schools
        schools_affected = max(1, int(profile["schools"] * risk_factor))

        # Calculate affected roads (km)
        roads_affected = round(profile["roads_km"] * risk_factor, 1)

        # Calculate affected health facilities
        health_affected = max(1, int(profile["health"] * risk_factor))

        # Calculate confidence (higher for extreme risks)
        confidence = min(0.95, 0.5 + (risk_score / 200))

        return ImpactEstimate(
            population_exposed=population_exposed,
            schools_affected=schools_affected,
            roads_affected_km=roads_affected,
            health_facilities_affected=health_affected,
            confidence=round(confidence, 2),
        )

    def format_for_dashboard(self, estimate: ImpactEstimate) -> Dict[str, Any]:
        """Format impact estimate for dashboard display."""
        return {
            "population_exposed": f"{estimate.population_exposed:,}",
            "schools_affected": estimate.schools_affected,
            "roads_affected_km": estimate.roads_affected_km,
            "health_facilities_affected": estimate.health_facilities_affected,
            "confidence": f"{int(estimate.confidence * 100)}%",
        }

    def format_for_whatsapp(self, estimate: ImpactEstimate, district: str) -> str:
        """Format impact estimate for WhatsApp message."""
        return f"""
*Impact Estimate for {district}*

👥 Population at risk: {estimate.population_exposed:,}
🏫 Schools affected: {estimate.schools_affected}
🛣️ Roads affected: {estimate.roads_affected_km} km
🏥 Health facilities affected: {estimate.health_facilities_affected}

Confidence: {int(estimate.confidence * 100)}%
"""


# Singleton instance
impact_estimator = ImpactEstimator()
