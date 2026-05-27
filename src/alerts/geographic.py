"""Geographic intelligence for flood risk assessment."""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class GeographicRisk:
    """Geographic risk factors for a location."""

    elevation_meters: float
    distance_to_river_km: float
    distance_to_coast_km: float
    drainage_capacity: float  # 0-1, higher is better
    soil_saturation_factor: float  # 0-1
    flood_protection_present: bool

    @property
    def geographic_risk_multiplier(self) -> float:
        """Calculate geographic risk multiplier (higher = worse)."""
        multiplier = 1.0

        # Low elevation increases risk
        if self.elevation_meters < 5:
            multiplier *= 1.5
        elif self.elevation_meters < 10:
            multiplier *= 1.2

        # Proximity to river
        if self.distance_to_river_km < 1:
            multiplier *= 1.4
        elif self.distance_to_river_km < 3:
            multiplier *= 1.2

        # Poor drainage
        multiplier *= 2 - self.drainage_capacity

        # Flood protection helps
        if self.flood_protection_present:
            multiplier *= 0.7

        return min(2.5, max(0.5, multiplier))


# Geographic database for Ghana districts
GEOGRAPHIC_DATA: Dict[str, GeographicRisk] = {
    "Accra Central": GeographicRisk(
        elevation_meters=5,
        distance_to_river_km=0.5,
        distance_to_coast_km=2,
        drainage_capacity=0.3,
        soil_saturation_factor=0.7,
        flood_protection_present=False,
    ),
    "Accra East": GeographicRisk(
        elevation_meters=8,
        distance_to_river_km=1.2,
        distance_to_coast_km=5,
        drainage_capacity=0.4,
        soil_saturation_factor=0.6,
        flood_protection_present=False,
    ),
    "Tema": GeographicRisk(
        elevation_meters=3,
        distance_to_river_km=0.8,
        distance_to_coast_km=1,
        drainage_capacity=0.35,
        soil_saturation_factor=0.75,
        flood_protection_present=True,
    ),
    "Kumasi": GeographicRisk(
        elevation_meters=250,
        distance_to_river_km=2,
        distance_to_coast_km=200,
        drainage_capacity=0.6,
        soil_saturation_factor=0.5,
        flood_protection_present=False,
    ),
    "Tamale": GeographicRisk(
        elevation_meters=150,
        distance_to_river_km=3,
        distance_to_coast_km=500,
        drainage_capacity=0.5,
        soil_saturation_factor=0.4,
        flood_protection_present=False,
    ),
}


def get_geographic_risk(location: str) -> GeographicRisk:
    """Get geographic risk factors for a location."""
    for name, risk in GEOGRAPHIC_DATA.items():
        if location.lower() in name.lower():
            return risk

    # Default moderate risk
    return GeographicRisk(
        elevation_meters=20,
        distance_to_river_km=5,
        distance_to_coast_km=50,
        drainage_capacity=0.5,
        soil_saturation_factor=0.5,
        flood_protection_present=False,
    )


def apply_geographic_weight(score: float, location: str) -> float:
    """Apply geographic weighting to risk score."""
    risk = get_geographic_risk(location)
    multiplier = risk.geographic_risk_multiplier
    adjusted = score * multiplier
    return min(100, max(0, adjusted))
