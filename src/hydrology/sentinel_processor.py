"""Sentinel-1 SAR flood mapping and change detection."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ee
import numpy as np

from src.exposure.districts import list_districts

from .ee_auth import initialize_earth_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The real water-detection threshold detect_flood() classifies against
# (vh_diff.gt(_VH_THRESHOLD_DB).And(vv_diff.gt(_VV_THRESHOLD_DB))) - kept
# as module constants so _confidence_from_sar_margins below stays
# grounded in the exact same numbers the classification itself uses,
# rather than a second, independently-chosen pair that could drift from
# it.
_VH_THRESHOLD_DB = 3.0
_VV_THRESHOLD_DB = 1.5

# Per-district SAR analysis bounding-box radius (degrees) - larger for
# Kumasi/Tamale's bigger urban extent, 0.05 default for everyone else.
# Not a canonical-registry fact (see _load_districts' docstring for why).
_DISTRICT_SAR_RADIUS = {"Kumasi": 0.08, "Tamale": 0.08}


def _confidence_from_sar_margins(
    vh_diff_mean: Optional[float], vv_diff_mean: Optional[float]
) -> float:
    """Real proxy for Sentinel-1 change-detection confidence: how far the
    scene's actual mean VH/VV backscatter differential sits from the
    water-detection threshold that produced the classification, in
    either direction - a change value barely crossing (or barely
    missing) the threshold is inherently less certain than one clearly
    on one side of it. Symmetric by design: a strongly negative margin
    (clearly no water) deserves the same confidence boost as a strongly
    positive one (clearly water), since the question this answers is "how
    decisive was this specific classification," not "how much water was
    found."

    This replaced an earlier version that scaled confidence with how many
    images fed the "after" composite - a plausible-sounding but
    scientifically shaky proxy: median-compositing over more images can
    just as easily dilute a real but brief flood signal as reduce speckle
    noise, so "more images" doesn't reliably mean "more confident" for a
    transient event. Distance-from-threshold is what the classifier
    itself actually relies on to decide water/no-water, so it directly
    reflects how decisive that specific decision was.

    Returns a real floor (0.55) rather than guessing when either mean is
    unavailable (e.g. an empty reduceRegion result) - never overclaims.
    Pulled out as a standalone, directly-testable function since
    detect_flood()'s real Earth Engine call chain has no test coverage in
    this codebase (a pre-existing gap, not one introduced by isolating
    this arithmetic) and would need heavy, fragile mocking to exercise
    end-to-end - this way the actual math, where a fix could introduce a
    real bug, is verified directly instead of going untested entirely.
    """
    if vh_diff_mean is None or vv_diff_mean is None:
        return 0.55
    vh_margin = (vh_diff_mean - _VH_THRESHOLD_DB) / _VH_THRESHOLD_DB
    vv_margin = (vv_diff_mean - _VV_THRESHOLD_DB) / _VV_THRESHOLD_DB
    distance_from_boundary = abs((vh_margin + vv_margin) / 2)
    return round(min(0.90, 0.55 + 0.35 * min(1.0, distance_from_boundary)), 2)


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
        """Load district geometries - real lat/lon now from
        src/exposure/districts.py, the canonical registry (this used to be
        its own independent lat/lon copy, one of 5+ scattered district
        datasets found in a 2026-09-27 audit, hand-matched against
        weather_forecast.py's and dashboard.py's own copies rather than
        sharing one real source). radius stays a local lookup - it's a
        bounding-box sizing choice for this specific SAR analysis (larger
        for Kumasi/Tamale's bigger urban extent), not a real-world fact
        the canonical registry should carry alongside population/area.

        This list previously only had the original 6 districts, silently
        missing Cape Coast/Ho/Sunyani added later - any request for one of
        those returned a plain {"error": ...} dict with none of
        detect_flood()'s normal fields, which unified_intelligence.py's
        satellite block then silently absorbed via its own
        .get(..., default) fallbacks rather than surfacing as an actual
        error. Reading from the canonical registry now makes that specific
        failure mode structurally impossible - every real tracked district
        is included by construction."""
        return {
            district.name: {
                "lat": district.lat,
                "lon": district.lon,
                "radius": _DISTRICT_SAR_RADIUS.get(district.name, 0.05),
            }
            for district in list_districts()
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
            after_image_count = after_collection.size().getInfo()
            if after_image_count == 0:
                logger.info(
                    f"No Sentinel-1 imagery for {district} in "
                    f"{after_start} to {after_end}"
                )
                return self._simulate_flood_detection(district)

            after = after_collection.median()

            # Change detection
            vh_diff = before.select("VH").subtract(after.select("VH"))
            vv_diff = before.select("VV").subtract(after.select("VV"))

            # Water detection threshold - _VH_THRESHOLD_DB/_VV_THRESHOLD_DB
            # module constants, shared with _confidence_from_sar_margins
            # below so confidence is always grounded in the exact same
            # numbers this classification itself used, not a second,
            # independently-chosen pair that could drift from it.
            water = vh_diff.gt(_VH_THRESHOLD_DB).And(vv_diff.gt(_VV_THRESHOLD_DB))

            # Calculate area
            area = water.multiply(ee.Image.pixelArea()).reduceRegion(
                reducer=ee.Reducer.sum(), geometry=bbox, scale=10, maxPixels=1e9
            )

            area_km2 = area.getInfo().get("VH", 0) / 1e6

            # Real proxy for detection confidence: how far the scene's
            # actual mean backscatter differential sits from the water-
            # detection threshold that produced this classification - see
            # _confidence_from_sar_margins' docstring (a standalone,
            # directly-tested pure function - this method's EE calls have
            # no test coverage in this codebase at all, being a long real
            # Earth Engine chain that's expensive to mock faithfully, but
            # the arithmetic itself, where a fix could actually introduce
            # a bug, is isolated and unit-tested independently of that).
            vh_diff_mean = vh_diff.reduceRegion(
                reducer=ee.Reducer.mean(), geometry=bbox, scale=10, maxPixels=1e9
            ).getInfo().get("VH")
            vv_diff_mean = vv_diff.reduceRegion(
                reducer=ee.Reducer.mean(), geometry=bbox, scale=10, maxPixels=1e9
            ).getInfo().get("VV")
            confidence = _confidence_from_sar_margins(vh_diff_mean, vv_diff_mean)

            return {
                "district": district,
                "water_detected": area_km2 > 0.1,
                "flood_extent_km2": round(area_km2, 2),
                "acquisition_date": f"{after_start} to {after_end}",
                "baseline_date": f"{baseline_start} to {baseline_end}",
                "source": "Sentinel-1 SAR",
                "confidence": confidence,
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
