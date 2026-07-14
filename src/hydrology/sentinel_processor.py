"""Sentinel-1 SAR flood mapping and change detection."""

import ee
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SentinelProcessor:
    """
    Sentinel-1 SAR processing for flood mapping.
    Implements change detection and flood extent extraction.
    """

    def __init__(self):
        self.ee_initialized = False

        # Earth Engine initialization
        try:
            ee.Initialize()
            self.ee_initialized = True
            logger.info("Earth Engine initialized for Sentinel-1 processing")
        except Exception as e:
            logger.warning(f"Earth Engine not available: {e}")

        self.cache_path = Path("data/flood_polygons/sentinel")
        self.cache_path.mkdir(parents=True, exist_ok=True)

        # District geometries (simplified)
        self.districts = self._load_districts()

        logger.info("Sentinel-1 Processor initialized")

    def _load_districts(self) -> Dict:
        """Load district geometries."""
        return {
            "Accra Central": {"lat": 5.560, "lon": -0.210, "radius": 0.05},
            "Accra West": {"lat": 5.550, "lon": -0.230, "radius": 0.05},
            "Accra East": {"lat": 5.565, "lon": -0.190, "radius": 0.05},
            "Tema": {"lat": 5.650, "lon": -0.020, "radius": 0.05},
            "Kumasi": {"lat": 6.670, "lon": -1.620, "radius": 0.08},
            "Tamale": {"lat": 9.400, "lon": -0.840, "radius": 0.08},
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

            # Filter by date
            if date:
                target_date = datetime.strptime(date, "%Y-%m-%d")
                after_date = date
                baseline_end = (target_date - timedelta(days=30)).strftime("%Y-%m-%d")
                baseline_start = (target_date - timedelta(days=60)).strftime("%Y-%m-%d")
            else:
                # Latest available
                after_date = datetime.now().strftime("%Y-%m-%d")
                baseline_end = (datetime.now() - timedelta(days=30)).strftime(
                    "%Y-%m-%d"
                )
                baseline_start = (datetime.now() - timedelta(days=60)).strftime(
                    "%Y-%m-%d"
                )

            # Get before and after images
            before = (
                sentinel1.filterDate(baseline_start, baseline_end)
                .filterBounds(bbox)
                .filter(ee.Filter.eq("instrumentMode", "IW"))
                .select(["VH", "VV"])
                .median()
            )

            after_collection = (
                sentinel1.filterDate(after_date, after_date)
                .filterBounds(bbox)
                .filter(ee.Filter.eq("instrumentMode", "IW"))
                .select(["VH", "VV"])
            )

            after = after_collection.first()

            if not after:
                return self._simulate_flood_detection(district)

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
                "acquisition_date": after_date,
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
