"""Population and infrastructure exposure analysis."""

from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImpactEstimator:
    """
    Complete exposure analysis engine.
    Estimates population, schools, hospitals affected by flooding.
    """
    
    def __init__(self):
        self.district_data = self._load_district_data()
        logger.info("Impact Estimator initialized")
    
    def _load_district_data(self) -> Dict:
        """Load district population and infrastructure data."""
        return {
            "Accra Central": {
                "population": 187928,
                "schools": 52,
                "hospitals": 8,
                "markets": 15,
                "area_km2": 45.5
            },
            "Accra West": {
                "population": 203461,
                "schools": 42,
                "hospitals": 6,
                "markets": 10,
                "area_km2": 52.3
            },
            "Accra East": {
                "population": 142587,
                "schools": 38,
                "hospitals": 5,
                "markets": 8,
                "area_km2": 38.2
            },
            "Tema": {
                "population": 198742,
                "schools": 58,
                "hospitals": 10,
                "markets": 18,
                "area_km2": 38.7
            },
            "Kumasi": {
                "population": 443981,
                "schools": 85,
                "hospitals": 12,
                "markets": 25,
                "area_km2": 98.2
            },
            "Tamale": {
                "population": 371578,
                "schools": 42,
                "hospitals": 6,
                "markets": 14,
                "area_km2": 67.4
            },
            "Sekondi-Takoradi": {
                "population": 245567,
                "schools": 35,
                "hospitals": 5,
                "markets": 12,
                "area_km2": 85.2
            },
            "Cape Coast": {
                "population": 169894,
                "schools": 28,
                "hospitals": 4,
                "markets": 10,
                "area_km2": 62.4
            },
            "Ho": {
                "population": 153705,
                "schools": 30,
                "hospitals": 4,
                "markets": 8,
                "area_km2": 58.3
            },
            "Sunyani": {
                "population": 138256,
                "schools": 25,
                "hospitals": 3,
                "markets": 7,
                "area_km2": 55.7
            }
        }
    
    def estimate_impact(self, district: str, risk_score: float) -> Dict:
        """
        Estimate impact based on risk score.
        
        Args:
            district: District name
            risk_score: Risk score (0-100)
        
        Returns:
            Impact estimates for population and infrastructure
        """
        if district not in self.district_data:
            return {'error': f'District {district} not found'}
        
        data = self.district_data[district]
        risk_factor = risk_score / 100
        
        return {
            'district': district,
            'population_total': data['population'],
            'population_exposed': int(data['population'] * risk_factor * 0.6),
            'children_exposed': int(data['population'] * risk_factor * 0.18),
            'elderly_exposed': int(data['population'] * risk_factor * 0.06),
            'schools_exposed': int(data['schools'] * risk_factor * 0.5),
            'hospitals_exposed': int(data['hospitals'] * risk_factor * 0.5),
            'markets_exposed': int(data['markets'] * risk_factor * 0.5),
            'area_km2': data['area_km2'],
            'exposure_percentage': round(risk_factor * 60, 1),
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
    
    def get_vulnerable_population(self, district: str) -> Dict:
        """Get detailed vulnerable population breakdown."""
        if district not in self.district_data:
            return {'error': f'District {district} not found'}
        
        pop = self.district_data[district]['population']
        
        return {
            'district': district,
            'total_population': pop,
            'children_under_18': int(pop * 0.30),
            'elderly_over_60': int(pop * 0.10),
            'disabled': int(pop * 0.02),
            'pregnant_women': int(pop * 0.015),
            'households': int(pop / 4)
        }

# Singleton instance
impact_estimator = ImpactEstimator()
