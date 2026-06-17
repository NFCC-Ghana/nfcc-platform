"""Soil moisture intelligence with proper saturation calculation."""

import random
from datetime import datetime
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SoilMoistureEngine:
    """Soil moisture intelligence with proper saturation calculation."""

    def __init__(self):
        self.soil_types = self._load_soil_types()
        self.historical_baseline = self._load_historical_baseline()

    def _load_soil_types(self) -> Dict:
        return {
            "Accra Central": {"type": "sandy_loam", "field_capacity": 0.35,
                              "wilting_point": 0.15, "saturation_point": 0.45,
                              "permeability": "moderate", "drainage": "poor"},
            "Accra West": {"type": "sandy_loam", "field_capacity": 0.35,
                           "wilting_point": 0.15, "saturation_point": 0.45,
                           "permeability": "moderate", "drainage": "poor"},
            "Accra East": {"type": "loam", "field_capacity": 0.40,
                           "wilting_point": 0.18, "saturation_point": 0.50,
                           "permeability": "good", "drainage": "fair"},
            "Tema": {"type": "sandy", "field_capacity": 0.25,
                     "wilting_point": 0.10, "saturation_point": 0.35,
                     "permeability": "high", "drainage": "good"},
            "Kumasi": {"type": "clay_loam", "field_capacity": 0.45,
                       "wilting_point": 0.20, "saturation_point": 0.55,
                       "permeability": "low", "drainage": "poor"},
            "Tamale": {"type": "sandy_loam", "field_capacity": 0.30,
                       "wilting_point": 0.12, "saturation_point": 0.40,
                       "permeability": "moderate", "drainage": "fair"},
            "Sekondi-Takoradi": {"type": "loam", "field_capacity": 0.38,
                                 "wilting_point": 0.16, "saturation_point": 0.48,
                                 "permeability": "good", "drainage": "fair"},
            "Cape Coast": {"type": "clay_loam", "field_capacity": 0.42,
                           "wilting_point": 0.18, "saturation_point": 0.52,
                           "permeability": "low", "drainage": "poor"},
            "Ho": {"type": "loam", "field_capacity": 0.38,
                   "wilting_point": 0.16, "saturation_point": 0.48,
                   "permeability": "moderate", "drainage": "fair"},
            "Sunyani": {"type": "clay_loam", "field_capacity": 0.42,
                        "wilting_point": 0.18, "saturation_point": 0.52,
                        "permeability": "low", "drainage": "poor"}
        }

    def _load_historical_baseline(self) -> Dict:
        return {
            1: 0.22, 2: 0.20, 3: 0.23, 4: 0.28,
            5: 0.35, 6: 0.38, 7: 0.40, 8: 0.38,
            9: 0.36, 10: 0.32, 11: 0.28, 12: 0.24
        }

    def get_soil_moisture(self, district: str, rainfall_mm: float = None) -> Dict:
        """Get current soil moisture for a district."""
        if district not in self.soil_types:
            return {
                'saturation_index': 0.4,
                'saturation_percent': 40,
                'runoff_potential': 'MODERATE',
                'flash_flood_risk': 'LOW'
            }

        soil = self.soil_types[district]
        current_month = datetime.now().month
        baseline = self.historical_baseline.get(current_month, 0.30)

        current_moisture = baseline

        if rainfall_mm is not None:
            rain_effect = min(0.12, rainfall_mm / 600)
            current_moisture = min(soil['saturation_point'] * 0.9, baseline + rain_effect)

        random.seed(hash(f"{district}_{datetime.now().date()}") % 2**32)
        variation = random.uniform(-0.015, 0.015)
        current_moisture = max(0.05, min(soil['saturation_point'] * 0.9, current_moisture + variation))

        saturation_index = (current_moisture - soil['wilting_point']) / (soil['saturation_point'] - soil['wilting_point'])
        saturation_index = max(0, min(0.92, saturation_index))

        if saturation_index > 0.75:
            runoff_potential, flash_flood_risk = 'HIGH', 'HIGH'
        elif saturation_index > 0.55:
            runoff_potential, flash_flood_risk = 'MODERATE', 'MODERATE'
        elif saturation_index > 0.35:
            runoff_potential, flash_flood_risk = 'LOW', 'LOW'
        else:
            runoff_potential, flash_flood_risk = 'VERY_LOW', 'VERY_LOW'

        return {
            'district': district,
            'soil_type': soil['type'],
            'field_capacity': soil['field_capacity'],
            'wilting_point': soil['wilting_point'],
            'saturation_point': soil['saturation_point'],
            'saturation_index': round(saturation_index, 2),
            'saturation_percent': round(saturation_index * 100, 1),
            'runoff_potential': runoff_potential,
            'flash_flood_risk': flash_flood_risk,
            'drainage': soil['drainage'],
            'permeability': soil['permeability'],
            'timestamp': datetime.now().isoformat()
        }

    def get_runoff_forecast(self, district: str, rainfall_mm: float) -> Dict:
        """Forecast runoff based on soil moisture and rainfall."""
        soil = self.get_soil_moisture(district, rainfall_mm)
        saturation_index = soil['saturation_index']
        runoff_coefficient = 0.05 + (0.80 * saturation_index)

        if rainfall_mm > 50:
            extra_rain = min(0.2, (rainfall_mm - 50) / 300)
            runoff_coefficient = min(0.90, runoff_coefficient + extra_rain)

        runoff_mm = rainfall_mm * runoff_coefficient

        if runoff_mm > 25:
            runoff_risk = 'EXTREME'
        elif runoff_mm > 12:
            runoff_risk = 'HIGH'
        elif runoff_mm > 4:
            runoff_risk = 'MODERATE'
        else:
            runoff_risk = 'LOW'

        return {
            'district': district,
            'rainfall_mm': rainfall_mm,
            'saturation_percent': soil['saturation_percent'],
            'runoff_coefficient': round(runoff_coefficient, 2),
            'estimated_runoff_mm': round(runoff_mm, 1),
            'runoff_risk': runoff_risk,
            'flash_flood_risk': soil['flash_flood_risk']
        }


soil_moisture = SoilMoistureEngine()
