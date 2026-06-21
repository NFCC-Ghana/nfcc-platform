"""Urban drainage mapping and flood routing for Accra."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UrbanDrainage:
    """
    Urban drainage mapping for flood routing.
    Uses OpenStreetMap and drainage network data.
    """

    def __init__(self):
        self.data_path = Path("data/urban/drainage")
        self.data_path.mkdir(parents=True, exist_ok=True)

        # Drainage network for Accra (simplified)
        self.drainage_network = self._load_drainage_network()

        logger.info("Urban Drainage initialized")

    def _load_drainage_network(self) -> Dict:
        """Load drainage network data."""
        return {
            "primary": {
                "Odaw": {
                    "type": "river",
                    "capacity_m3s": 150,
                    "status": "POOR",
                    "areas": ["Central Accra", "Kaneshie", "Mamobi"],
                },
                "Densu": {
                    "type": "river",
                    "capacity_m3s": 100,
                    "status": "POOR",
                    "areas": ["Weija", "Mallam"],
                },
                "Korle": {
                    "type": "lagoon",
                    "capacity_m3s": 50,
                    "status": "POOR",
                    "areas": ["Korle", "Chorkor"],
                },
            },
            "secondary": {
                "Ring Road": {
                    "type": "drainage_channel",
                    "capacity_m3s": 20,
                    "status": "BLOCKED",
                    "areas": ["Ring Road Central", "Ayalolo"],
                },
                "Odaw Tributary": {
                    "type": "drainage_channel",
                    "capacity_m3s": 15,
                    "status": "POOR",
                    "areas": ["Nima", "Alajo"],
                },
            },
            "urban_drainage": {
                "Alajo": {"type": "open_drain", "capacity_m3s": 5, "status": "BLOCKED"},
                "Kaneshie": {"type": "open_drain", "capacity_m3s": 8, "status": "POOR"},
                "Circle": {
                    "type": "open_drain",
                    "capacity_m3s": 3,
                    "status": "BLOCKED",
                },
                "Nima": {"type": "open_drain", "capacity_m3s": 4, "status": "POOR"},
                "Mamobi": {
                    "type": "open_drain",
                    "capacity_m3s": 3,
                    "status": "BLOCKED",
                },
                "Dansoman": {"type": "open_drain", "capacity_m3s": 6, "status": "POOR"},
            },
        }

    def get_drainage_status(self, district: str) -> Dict:
        """
        Get drainage status for a district.

        Args:
            district: District name

        Returns:
            Drainage status dictionary
        """
        # Map district to areas
        area_map = {
            "Accra Central": ["Central Accra", "Kaneshie", "Ring Road Central"],
            "Accra West": ["Weija", "Mallam"],
            "Accra East": ["Korle", "Chorkor"],
            "Tema": ["Tema", "Community 1"],
            "Kumasi": ["Kumasi", "Atwima"],
            "Tamale": ["Tamale", "Gushegu"],
        }

        areas = area_map.get(district, [])

        # Find relevant drainage
        drainage = []
        for name, data in self.drainage_network["primary"].items():
            if any(area in data["areas"] for area in areas):
                drainage.append(
                    {
                        "name": name,
                        "type": data["type"],
                        "status": data["status"],
                        "capacity_m3s": data["capacity_m3s"],
                    }
                )

        # Urban drainage
        urban = []
        for name, data in self.drainage_network["urban_drainage"].items():
            if name in areas:
                urban.append(
                    {
                        "name": name,
                        "type": data["type"],
                        "status": data["status"],
                        "capacity_m3s": data["capacity_m3s"],
                    }
                )

        return {
            "district": district,
            "primary_drainage": drainage,
            "urban_drainage": urban,
            "overall_status": self._calculate_overall_status(drainage, urban),
        }

    def _calculate_overall_status(self, primary: List, urban: List) -> str:
        """Calculate overall drainage status."""
        if not primary and not urban:
            return "UNKNOWN"

        statuses = [d.get("status", "UNKNOWN") for d in primary + urban]

        if "BLOCKED" in statuses:
            return "CRITICAL"
        elif "POOR" in statuses:
            return "POOR"
        elif "FAIR" in statuses:
            return "FAIR"
        else:
            return "GOOD"

    def get_flood_risk_factor(self, district: str, rainfall_mm: float) -> float:
        """
        Calculate flood risk factor based on drainage capacity.

        Returns:
            Risk multiplier (1.0 = baseline)
        """
        status = self.get_drainage_status(district)
        overall = status.get("overall_status", "UNKNOWN")

        # Base multiplier
        if overall == "CRITICAL":
            base = 1.5
        elif overall == "POOR":
            base = 1.2
        elif overall == "FAIR":
            base = 1.0
        else:
            base = 0.8

        # Rainfall factor
        if rainfall_mm > 80:
            rainfall_multiplier = 1.3
        elif rainfall_mm > 50:
            rainfall_multiplier = 1.1
        else:
            rainfall_multiplier = 1.0

        return round(base * rainfall_multiplier, 2)


# Singleton instance
urban_drainage = UrbanDrainage()
