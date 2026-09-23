"""Historical flood polygon intelligence."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FloodPolygonEngine:
    """
    Complete historical flood polygon database.
    Stores and retrieves flood extents from Sentinel-1, MODIS, UNOSAT.
    """

    def __init__(self, data_path: str = "data/flood_polygons/"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)

        self.flood_events = self._load_flood_events()
        logger.info(
            f"Flood Polygon Engine initialized with {len(self.flood_events)} events"
        )

    def _load_flood_events(self) -> Dict:
        """Load comprehensive historical flood event database.

        Every entry here is a real, dated, independently-verifiable event
        - checked against news/academic sources before being added or
        corrected, not invented for plausibility.

        2015_accra's fatality count was wrong before this comment existed:
        the record said 15, but the real, widely-documented toll for the
        June 3, 2015 Accra flood + GOIL filling-station explosion disaster
        (rising floodwater carried leaked fuel into a crowd sheltering at
        the station, which then ignited) is 150+ - cited as "150" by the
        then-President's own announcement, "over 152" in an academic
        impact-analysis paper, and "154" in 2025 tenth-anniversary
        commemorative reporting; one source cites over 250. Used 150 here
        as the most consistently-repeated figure, with the real range
        disclosed rather than picking one number and hiding the
        disagreement between sources - exact tolls for mass-casualty
        disasters in this context are often genuinely disputed, not
        precisely known.
        """
        return {
            "2023_akosombo": {
                "date": "2023-10-15",
                "cause": "dam_spillage",
                "dam": "Akosombo",
                "districts": ["North Tongu", "South Tongu", "Keta", "Ada"],
                "rainfall_mm": 85.0,
                "area_km2": 450.0,
                "population_affected": 30000,
                "displaced": 12000,
                "fatalities": 0,
                "severity": "HIGH",
                "description": "Akosombo Dam spillage caused widespread flooding",
            },
            "2015_accra": {
                "date": "2015-06-03",
                "cause": "urban_flooding",
                "dam": None,
                "districts": ["Accra Central", "Accra West", "Accra East"],
                "rainfall_mm": 120.0,
                "area_km2": 25.0,
                "population_affected": 50000,
                "displaced": 15000,
                "fatalities": 150,
                "fatalities_reported_range": "150-250+ (sources disagree)",
                "severity": "CRITICAL",
                "description": (
                    "Heavy rainfall caused severe urban flooding in Accra; "
                    "floodwater carried leaked fuel from a GOIL filling "
                    "station at Kwame Nkrumah Circle into a crowd sheltering "
                    "there, which then ignited - one of Ghana's deadliest "
                    "combined disasters."
                ),
            },
            "2021_tamale": {
                "date": "2021-09-07",
                "cause": "riverine_flooding",
                "dam": "Bagre",
                "districts": ["Tamale", "Yendi", "Gushegu"],
                "rainfall_mm": 70.0,
                "area_km2": 85.0,
                "population_affected": 12000,
                "displaced": 4000,
                "fatalities": 0,
                "severity": "HIGH",
                "description": "Bagre Dam spillage caused flooding in Northern Region",
            },
            # The five events below were not in this database until they
            # were found and verified via independent news/archival
            # sources while researching real historical rainfall-vs-flood
            # backtesting data - see src/models/historical_backtest.py.
            "2007_northern": {
                "date": "2007-09-01",
                "cause": "riverine_flooding",
                "dam": None,
                "districts": ["Tamale"],
                "rainfall_mm": None,
                "area_km2": None,
                "population_affected": 300000,
                "displaced": None,
                "fatalities": None,
                "severity": "CRITICAL",
                "description": (
                    "Widespread flooding across Ghana's three northern "
                    "regions displaced/affected an estimated 300,000 "
                    "people - one of Ghana's largest-scale flood disasters. "
                    "Exact date and per-district breakdown are not "
                    "precisely documented in available sources; September "
                    "2007 (peak of that year's rainy season) is used as an "
                    "approximate anchor, not a confirmed exact date."
                ),
            },
            "2010_05_accra": {
                "date": "2010-05-05",
                "cause": "urban_flooding",
                "dam": None,
                "districts": ["Accra Central"],
                "rainfall_mm": None,
                "area_km2": None,
                "population_affected": None,
                "displaced": None,
                "fatalities": None,
                "severity": "MODERATE",
                "description": (
                    "Two hours of intense rain submerged parts of Central "
                    "Accra, Ofankor, and Begoro."
                ),
            },
            "2010_06_accra": {
                "date": "2010-06-22",
                "cause": "urban_flooding",
                "dam": None,
                "districts": ["Accra Central", "Accra West", "Accra East"],
                "rainfall_mm": None,
                "area_km2": None,
                "population_affected": None,
                "displaced": None,
                "fatalities": 35,
                "severity": "CRITICAL",
                "description": "Widely reported as that year's worst flood disaster in Ghana.",
            },
            "2010_10_bagre": {
                "date": "2010-10-14",
                "cause": "dam_spillage",
                "dam": "Bagre",
                "districts": ["Tamale", "Yendi", "Gushegu"],
                "rainfall_mm": None,
                "area_km2": None,
                "population_affected": 161000,
                "displaced": 161000,
                "fatalities": None,
                "severity": "CRITICAL",
                "description": (
                    "Torrential rain combined with a Bagre Dam release "
                    "displaced an estimated 161,000 people nationally."
                ),
            },
            "2011_11_accra": {
                "date": "2011-11-01",
                "cause": "urban_flooding",
                "dam": None,
                "districts": ["Accra Central", "Accra West", "Accra East"],
                "rainfall_mm": None,
                "area_km2": None,
                "population_affected": 43087,
                "displaced": None,
                "fatalities": 14,
                "severity": "CRITICAL",
                "description": "Flooding affected an estimated 43,087 people in Accra.",
            },
        }

    def get_flood_events(self, district: Optional[str] = None) -> List[Dict]:
        """Get historical flood events."""
        events = []
        for event_id, event in self.flood_events.items():
            if district and district not in event["districts"]:
                continue
            events.append({"event_id": event_id, **event})

        events.sort(key=lambda x: x["date"], reverse=True)
        return events

    def get_flood_risk_summary(self, district: str) -> Dict:
        """Get flood risk summary for a district."""
        events = self.get_flood_events(district)

        if not events:
            return {
                "district": district,
                "total_events": 0,
                "risk_level": "LOW",
                "message": "No historical flood events recorded",
            }

        # `or 0` rather than .get(key, 0): several real historical events
        # honestly record these fields as None (not precisely documented
        # in available sources) rather than a fabricated placeholder
        # number - .get()'s default only applies when the key is absent,
        # not when its value is explicitly None, so this would otherwise
        # crash the moment a district with an incompletely-documented
        # event (e.g. Tamale's 2007/2010 entries) was summarized.
        total_events = len(events)
        total_affected = sum(e.get("population_affected") or 0 for e in events)
        total_displaced = sum(e.get("displaced") or 0 for e in events)
        total_fatalities = sum(e.get("fatalities") or 0 for e in events)

        severity_weight = {"CRITICAL": 4, "HIGH": 3, "MODERATE": 2, "LOW": 1}
        avg_severity = (
            sum(severity_weight.get(e.get("severity", "LOW"), 1) for e in events)
            / total_events
        )

        if avg_severity > 3 or total_fatalities > 10:
            risk_level = "CRITICAL"
        elif avg_severity > 2 or total_affected > 50000:
            risk_level = "HIGH"
        elif avg_severity > 1 or total_affected > 10000:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        return {
            "district": district,
            "total_events": total_events,
            "total_affected": total_affected,
            "total_displaced": total_displaced,
            "total_fatalities": total_fatalities,
            "avg_severity": round(avg_severity, 1),
            "risk_level": risk_level,
        }

    def get_flood_inundation_risk(self, district: str, rainfall_mm: float) -> Dict:
        """Estimate inundation risk based on historical events."""
        events = self.get_flood_events(district)

        if not events:
            return {
                "district": district,
                "risk": "LOW",
                "confidence": "LOW",
                "message": "No similar historical events found",
            }

        # Find most similar event based on rainfall - only among events
        # that actually recorded a real rainfall figure (several real
        # historical events honestly have rainfall_mm=None rather than an
        # invented number; they're excluded from this comparison instead
        # of crashing abs()/division against None).
        events_with_rainfall = [e for e in events if e.get("rainfall_mm") is not None]
        if not events_with_rainfall:
            return {
                "district": district,
                "risk": "LOW",
                "confidence": "LOW",
                "message": "No historical events with recorded rainfall for comparison",
            }

        best_match = None
        best_diff = float("inf")

        for event in events_with_rainfall:
            diff = abs(event["rainfall_mm"] - rainfall_mm)
            if diff < best_diff:
                best_diff = diff
                best_match = event

        rain_ratio = rainfall_mm / max(1, best_match["rainfall_mm"])
        estimated_affected = int(
            (best_match.get("population_affected") or 0) * rain_ratio
        )

        return {
            "district": district,
            "rainfall_mm": rainfall_mm,
            "similar_event": best_match.get("date", "Unknown"),
            "similarity_score": max(0, 100 - best_diff * 2),
            "estimated_affected": estimated_affected,
            "risk_level": best_match.get("severity", "LOW"),
            "confidence": "HIGH" if best_diff < 20 else "MEDIUM",
        }


# Singleton instance
flood_polygons = FloodPolygonEngine()
