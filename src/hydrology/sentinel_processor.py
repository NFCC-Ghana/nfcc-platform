"""Sentinel-1 SAR flood mapping and change detection."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ee
import numpy as np

from .ee_auth import initialize_earth_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SentinelProcessor:
    """
    Sentinel-1 SAR processing for flood mapping.
    Implements change detection and flood extent extraction.
    """

    def __init__(self):
        # Was a bare ee.Initialize() with no service account/project - that
        # silently fails in any non-interactive environment (Cloud Run,
        # CI), which is why this always fell back to
        # _simulate_flood_detection()'s random numbers in production
        # despite the real Earth Engine credentials already being set up
        # and working for the CHIRPS rainfall pull.
        self.ee_initialized = initialize_earth_engine()
        if self.ee_initialized:
            logger.info("Earth Engine initialized for Sentinel-1 processing")

        self.cache_path = Path("data/flood_polygons/sentinel")
        self.cache_path.mkdir(parents=True, exist_ok=True)

        # District geometries (simplified)
        self.districts = self._load_districts()

        logger.info("Sentinel-1 Processor initialized")

    def _load_districts(self) -> Dict:
        """Load district geometries - matches
        hackathon/app/pages/dashboard.py's get_district_data and
        src/hydrology/weather_forecast.py's district_coords, the other two
        places these are listed. This list previously only had the
        original 6 districts, silently missing Cape Coast/Ho/Sunyani
        added later - any request for one of those returned a plain
        {"error": ...} dict with none of detect_flood()'s normal fields,
        which unified_intelligence.py's satellite block then silently
        absorbed via its own .get(..., default) fallbacks rather than
        surfacing as an actual error."""
        return {
            "Accra Central": {"lat": 5.560, "lon": -0.210, "radius": 0.05},
            "Accra West": {"lat": 5.550, "lon": -0.230, "radius": 0.05},
            "Accra East": {"lat": 5.565, "lon": -0.190, "radius": 0.05},
            "Tema": {"lat": 5.650, "lon": -0.020, "radius": 0.05},
            "Kumasi": {"lat": 6.670, "lon": -1.620, "radius": 0.08},
            "Tamale": {"lat": 9.400, "lon": -0.840, "radius": 0.08},
            "Cape Coast": {"lat": 5.100, "lon": -1.250, "radius": 0.05},
            "Ho": {"lat": 6.601, "lon": 0.471, "radius": 0.05},
            "Sunyani": {"lat": 7.333, "lon": -2.333, "radius": 0.05},
        }

    def detect_flood(self, district: str, date: Optional[str] = None) -> Dict:
        """
        Detect flood extent using Sentinel-1 change detection.

        Args:
            district: District name
            date: Date to analyze (YYYY-MM-DD), defaults to latest

        Returns:
            Flood detection results
        """
        if not self.ee_initialized:
            return self._simulate_flood_detection(district)

        try:
            if district not in self.districts:
                return {"error": f"District {district} not found"}

            coords = self.districts[district]
            point = ee.Geometry.Point(coords["lon"], coords["lat"])
            bbox = point.buffer(0.05)

            # Get Sentinel-1 imagery
            sentinel1 = ee.ImageCollection("COPERNICUS/S1_GRD")

            # Filter by date. "after" uses a 12-day window ending on the
            # target date, not that single exact day - Sentinel-1's revisit
            # time over Ghana is roughly 6-12 days, so filtering for one
            # specific day almost never actually finds an image, and this
            # collection being empty was never being detected (see below),
            # silently deferring an "Empty date ranges" error to the
            # getInfo() call much further down instead of failing fast here.
            reference_date = (
                datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
            )
            after_end = reference_date.strftime("%Y-%m-%d")
            after_start = (reference_date - timedelta(days=12)).strftime("%Y-%m-%d")
            baseline_end = (reference_date - timedelta(days=30)).strftime("%Y-%m-%d")
            baseline_start = (reference_date - timedelta(days=60)).strftime("%Y-%m-%d")

            # Get before and after images
            before = (
                sentinel1.filterDate(baseline_start, baseline_end)
                .filterBounds(bbox)
                .filter(ee.Filter.eq("instrumentMode", "IW"))
                .select(["VH", "VV"])
                .median()
            )

            after_collection = (
                sentinel1.filterDate(after_start, after_end)
                .filterBounds(bbox)
                .filter(ee.Filter.eq("instrumentMode", "IW"))
                .select(["VH", "VV"])
            )

            # ee.Image objects are always truthy in Python regardless of
            # whether the collection they came from was empty - `if not
            # after:` never actually caught this, letting an empty
            # collection's null image flow all the way down to the
            # getInfo() call below before failing. size().getInfo() is a
            # real, immediate check, same pattern already used correctly
            # in scripts/daily_chirps_pull.py.
            if after_collection.size().getInfo() == 0:
                logger.info(
                    f"No Sentinel-1 imagery for {district} in "
                    f"{after_start} to {after_end}"
                )
                return self._simulate_flood_detection(district)

            after = after_collection.median()

            # Change detection
            vh_diff = before.select("VH").subtract(after.select("VH"))
            vv_diff = before.select("VV").subtract(after.select("VV"))

            # Water detection threshold
            water = vh_diff.gt(3.0).And(vv_diff.gt(1.5))

            # Calculate area
            area = water.multiply(ee.Image.pixelArea()).reduceRegion(
                reducer=ee.Reducer.sum(), geometry=bbox, scale=10, maxPixels=1e9
            )

            area_km2 = area.getInfo().get("VH", 0) / 1e6

            return {
                "district": district,
                "water_detected": area_km2 > 0.1,
                "flood_extent_km2": round(area_km2, 2),
                "acquisition_date": f"{after_start} to {after_end}",
                "baseline_date": f"{baseline_start} to {baseline_end}",
                "source": "Sentinel-1 SAR",
                "confidence": 0.85,
            }

        except Exception as e:
            logger.error(f"Sentinel-1 processing failed: {e}")
            return self._simulate_flood_detection(district)

    def _simulate_flood_detection(self, district: str) -> Dict:
        """Generate simulated flood detection."""
        import random

        random.seed(hash(district + datetime.now().strftime("%Y%m%d")) % 2**32)

        # More likely in wet season
        month = datetime.now().month
        is_rainy = month in [5, 6, 7, 9, 10]

        if is_rainy:
            area = random.uniform(0.5, 10.0)
            detected = area > 1.0
        else:
            area = random.uniform(0, 2.0)
            detected = area > 0.5

        return {
            "district": district,
            "water_detected": detected,
            "flood_extent_km2": round(area, 2),
            "acquisition_date": datetime.now().strftime("%Y-%m-%d"),
            "baseline_date": f"{(datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')} to {(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')}",
            "source": "Sentinel-1 (simulated)",
            "confidence": 0.75,
        }

    def get_flood_extent_geojson(self, district: str) -> Optional[Dict]:
        """
        Get flood extent as GeoJSON (for visualization).

        Args:
            district: District name

        Returns:
            GeoJSON feature collection or None
        """
        try:
            coords = self.districts[district]

            # Create a simple rectangle for demo
            lat = coords["lat"]
            lon = coords["lon"]
            radius = coords["radius"] * 0.5

            polygon = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [lon - radius, lat - radius],
                                    [lon + radius, lat - radius],
                                    [lon + radius, lat + radius],
                                    [lon - radius, lat + radius],
                                    [lon - radius, lat - radius],
                                ]
                            ],
                        },
                        "properties": {
                            "district": district,
                            "type": "flood_extent",
                            "timestamp": datetime.now().isoformat(),
                        },
                    }
                ],
            }

            return polygon

        except Exception as e:
            logger.error(f"GeoJSON generation failed: {e}")
            return None


# Singleton instance
sentinel_processor = SentinelProcessor()
