"""Impact Estimator - Estimates flood impacts on communities."""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger("hackathon.impact")


@dataclass
class ImpactResult:
    """Human-readable impact assessment."""

    total_exposed: int
    children_exposed: int
    elderly_exposed: int
    households_affected: int
    schools_exposed: int
    hospitals_exposed: int
    markets_exposed: int
    residential_loss_ghs: float
    infrastructure_loss_ghs: float
    total_loss_ghs: float
    recovery_weeks: float


class ImpactEstimator:
    """Estimate flood impacts based on risk score and population data."""

    def __init__(self):
        self.population_data = {
            "Accra Central": {
                "total": 187928,
                "children_pct": 0.32,
                "elderly_pct": 0.08,
                "households": 46982,
                "schools": 12,
                "hospitals": 3,
                "markets": 8,
            },
            "Accra West": {
                "total": 203461,
                "children_pct": 0.30,
                "elderly_pct": 0.09,
                "households": 50865,
                "schools": 14,
                "hospitals": 4,
                "markets": 10,
            },
            "Kumasi": {
                "total": 443981,
                "children_pct": 0.35,
                "elderly_pct": 0.07,
                "households": 110995,
                "schools": 28,
                "hospitals": 8,
                "markets": 20,
            },
            "Tamale": {
                "total": 371578,
                "children_pct": 0.38,
                "elderly_pct": 0.06,
                "households": 92894,
                "schools": 22,
                "hospitals": 6,
                "markets": 15,
            },
            "Cape Coast": {
                "total": 169894,
                "children_pct": 0.28,
                "elderly_pct": 0.10,
                "households": 42473,
                "schools": 10,
                "hospitals": 3,
                "markets": 6,
            },
        }

    def estimate(
        self,
        district: str,
        risk_score: float,
        rainfall_mm: float,
    ) -> ImpactResult:
        """Estimate impacts based on district and risk score."""

        pop_data = self.population_data.get(
            district, self.population_data["Accra Central"]
        )

        # Calculate exposure based on risk score (0-100)
        exposure_pct = risk_score / 100

        # People impacted
        total_exposed = int(pop_data["total"] * exposure_pct * 0.7)
        children_exposed = int(total_exposed * pop_data["children_pct"])
        elderly_exposed = int(total_exposed * pop_data["elderly_pct"])
        households_affected = int(pop_data["households"] * exposure_pct * 0.6)

        # Infrastructure impacted
        schools_exposed = max(0, int(pop_data["schools"] * exposure_pct * 0.8))
        hospitals_exposed = max(0, int(pop_data["hospitals"] * exposure_pct * 0.6))
        markets_exposed = max(0, int(pop_data["markets"] * exposure_pct * 0.7))

        # Economic impacts
        avg_household_loss = 5000 + (risk_score * 500)  # GHS
        residential_loss = households_affected * avg_household_loss

        infra_loss_per_school = 200000 + (risk_score * 5000)
        infra_loss_per_hospital = 500000 + (risk_score * 10000)
        infra_loss_per_market = 300000 + (risk_score * 8000)

        infrastructure_loss = (
            schools_exposed * infra_loss_per_school
            + hospitals_exposed * infra_loss_per_hospital
            + markets_exposed * infra_loss_per_market
        )

        total_loss = residential_loss + infrastructure_loss

        # Recovery time (weeks)
        recovery_weeks = 2 + (risk_score / 20)

        return ImpactResult(
            total_exposed=total_exposed,
            children_exposed=children_exposed,
            elderly_exposed=elderly_exposed,
            households_affected=households_affected,
            schools_exposed=schools_exposed,
            hospitals_exposed=hospitals_exposed,
            markets_exposed=markets_exposed,
            residential_loss_ghs=residential_loss,
            infrastructure_loss_ghs=infrastructure_loss,
            total_loss_ghs=total_loss,
            recovery_weeks=recovery_weeks,
        )

    def format_for_dashboard(self, impact: ImpactResult) -> Dict:
        """Format impact results for dashboard display."""
        return {
            "total_exposed": impact.total_exposed,
            "children_exposed": impact.children_exposed,
            "elderly_exposed": impact.elderly_exposed,
            "households_affected": impact.households_affected,
            "schools_exposed": impact.schools_exposed,
            "hospitals_exposed": impact.hospitals_exposed,
            "markets_exposed": impact.markets_exposed,
            "residential_loss_ghs": impact.residential_loss_ghs,
            "infrastructure_loss_ghs": impact.infrastructure_loss_ghs,
            "total_loss_ghs": impact.total_loss_ghs,
            "recovery_weeks": impact.recovery_weeks,
        }


# Singleton instance
impact_estimator = ImpactEstimator()
