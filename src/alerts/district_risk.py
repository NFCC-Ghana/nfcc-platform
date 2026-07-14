"""District-specific risk profiles for intelligent alerting."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class DistrictProfile:
    """Risk profile for a district."""

    name: str
    base_risk_factor: float  # 0-1, multiplies raw score
    vulnerability_score: float  # 0-1, population/infrastructure vulnerability
    historical_flood_probability: float  # 0-1, historical flooding frequency
    alert_threshold_adjustment: float  # -15 to +15, adjusts alert thresholds

    @property
    def effective_threshold(self) -> float:
        """Calculate adjusted alert threshold."""
        base = 30  # MODERATE threshold
        adjusted = base - self.alert_threshold_adjustment
        return max(10, min(50, adjusted))  # Clamp between 10 and 50


# District risk profiles for Ghana
DISTRICT_PROFILES: Dict[str, DistrictProfile] = {
    "Accra Central": DistrictProfile(
        name="Accra Central",
        base_risk_factor=1.0,
        vulnerability_score=0.95,
        historical_flood_probability=0.85,
        alert_threshold_adjustment=-10,  # Alert earlier (20 instead of 30)
    ),
    "Accra East": DistrictProfile(
        name="Accra East",
        base_risk_factor=0.95,
        vulnerability_score=0.85,
        historical_flood_probability=0.75,
        alert_threshold_adjustment=-5,
    ),
    "Accra West": DistrictProfile(
        name="Accra West",
        base_risk_factor=0.92,
        vulnerability_score=0.82,
        historical_flood_probability=0.72,
        alert_threshold_adjustment=-3,
    ),
    "Tema": DistrictProfile(
        name="Tema",
        base_risk_factor=0.88,
        vulnerability_score=0.78,
        historical_flood_probability=0.65,
        alert_threshold_adjustment=0,
    ),
    "Kumasi": DistrictProfile(
        name="Kumasi",
        base_risk_factor=0.75,
        vulnerability_score=0.70,
        historical_flood_probability=0.55,
        alert_threshold_adjustment=5,
    ),
    "Takoradi": DistrictProfile(
        name="Takoradi",
        base_risk_factor=0.72,
        vulnerability_score=0.65,
        historical_flood_probability=0.50,
        alert_threshold_adjustment=5,
    ),
    "Tamale": DistrictProfile(
        name="Tamale",
        base_risk_factor=0.65,
        vulnerability_score=0.60,
        historical_flood_probability=0.40,
        alert_threshold_adjustment=8,
    ),
}


def get_district_profile(location: str) -> DistrictProfile:
    """Get risk profile for a district, returning default if not found."""
    # Try exact match first
    for name, profile in DISTRICT_PROFILES.items():
        if location.lower() in name.lower():
            return profile

    # Return default profile
    return DistrictProfile(
        name=location,
        base_risk_factor=0.8,
        vulnerability_score=0.7,
        historical_flood_probability=0.5,
        alert_threshold_adjustment=0,
    )


def calculate_adjusted_score(raw_score: float, location: str) -> float:
    """Calculate location-adjusted risk score."""
    profile = get_district_profile(location)
    adjusted = raw_score * profile.base_risk_factor

    # Add vulnerability component
    adjusted = adjusted * (1 + profile.vulnerability_score) / 2

    return min(100, max(0, adjusted))


def should_alert_for_district(score: float, location: str) -> bool:
    """Determine if alert should be sent for this district."""
    profile = get_district_profile(location)
    threshold = profile.effective_threshold

    return score >= threshold
