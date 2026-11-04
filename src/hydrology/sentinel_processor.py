"""Sentinel-1 SAR flood mapping and change detection."""

import json
import logging
import time
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

# Newly flooded land smaller than this is treated as noise - the same 1 km2
# floor the research label audit uses (research/flood_experiments/config.py
# SAR_MIN_KM2), against a 0.1-0.16 degree box of roughly 120-310 km2.
_MIN_FLOOD_KM2 = 1.0

# JRC Global Surface Water occurrence (% of months observed as water) at or
# above which a pixel is permanent water or sea, not flooding.
_PERMANENT_WATER_OCCURRENCE = 50

# A newly flooded pixel must also look like open water after the change
# (calm water reflects the radar away: VH typically below about -20 dB).
# Without this, ploughed, burned or drying land that loses 3 dB is counted
# as water. Checked on the Akosombo spill: Mepe, 25 Oct 2023, 5.3 km2 of new
# water, against 0.4 km2 in the same window of 2024 with no spill, and
# <0.1 km2 over Accra and Tamale in a dry week.
_WATER_VH_MAX_DB = -20.0

# Sentinel-1 revisits Ghana every 6-12 days, so a live result stays valid
# for hours; /situation calls detect_flood on every request.
_LIVE_CACHE_SECONDS = 3 * 3600

# 30 m is enough for a >= 1 km2 decision and is ~10x faster than 10 m.
_ANALYSIS_SCALE_M = 30


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
        # Earth Engine auth via the shared service-account helper; without
        # it every request reports the satellite reading as unavailable.
        self.ee_initialized = initialize_earth_engine()
        if self.ee_initialized:
            logger.info("Earth Engine initialized for Sentinel-1 processing")

        self.cache_path = Path("data/flood_polygons/sentinel")
        self.cache_path.mkdir(parents=True, exist_ok=True)

        # District geometries (simplified)
        self.districts = self._load_districts()
        self._live_cache: Dict[str, Tuple[float, Dict]] = {}

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
            return self._unavailable(district, "Earth Engine unavailable")
        if district not in self.districts:
            return {"error": f"District {district} not found"}
        if date is None:
            cached = self._live_cache.get(district)
            if cached and time.time() - cached[0] < _LIVE_CACHE_SECONDS:
                return cached[1]
        coords = self.districts[district]
        result = self.detect_flood_at(
            district, coords["lat"], coords["lon"], coords["radius"], date
        )
        if date is None and result.get("source") == "Sentinel-1 SAR":
            self._live_cache[district] = (time.time(), result)
        return result

    def detect_flood_at(
        self,
        label: str,
        lat: float,
        lon: float,
        radius_deg: float,
        date: Optional[str] = None,
    ) -> Dict:
        """Change detection over a lat/lon box of +-radius_deg degrees.

        The analysis area was once `point.buffer(0.05)` - but Earth Engine
        buffers in METRES, so that was a 5 cm circle containing no 10 m
        pixel, and no water could ever be detected. It is now an explicit
        degree box. Before and after composites use the same orbit
        direction (ascending/descending geometry otherwise changes
        backscatter on its own), are lightly smoothed against speckle, and
        sea and permanent water (JRC Global Surface Water occurrence >= 50%)
        are masked out, since a box on the coast is partly sea.
        """
        try:
            region = ee.Geometry.Rectangle(
                [lon - radius_deg, lat - radius_deg, lon + radius_deg, lat + radius_deg]
            )
            reference_date = (
                datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
            )
            after_end = reference_date.strftime("%Y-%m-%d")
            after_start = (reference_date - timedelta(days=12)).strftime("%Y-%m-%d")
            baseline_end = (reference_date - timedelta(days=30)).strftime("%Y-%m-%d")
            baseline_start = (reference_date - timedelta(days=60)).strftime("%Y-%m-%d")

            s1 = (
                ee.ImageCollection("COPERNICUS/S1_GRD")
                .filterBounds(region)
                .filter(ee.Filter.eq("instrumentMode", "IW"))
                .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
            )
            after_collection = s1.filterDate(after_start, after_end)
            if after_collection.size().getInfo() == 0:
                logger.info(
                    f"No Sentinel-1 imagery for {label} in {after_start} to {after_end}"
                )
                return self._unavailable(
                    label, f"no Sentinel-1 image between {after_start} and {after_end}"
                )
            orbit_pass = (
                after_collection.sort("system:time_start", False)
                .first()
                .get("orbitProperties_pass")
            )
            same_pass = ee.Filter.eq("orbitProperties_pass", orbit_pass)
            after_collection = after_collection.filter(same_pass)
            before_collection = s1.filterDate(baseline_start, baseline_end).filter(
                same_pass
            )
            if before_collection.size().getInfo() == 0:
                return self._unavailable(
                    label,
                    f"no same-orbit Sentinel-1 baseline between {baseline_start} "
                    f"and {baseline_end}",
                )

            def smooth(img):
                return img.select(["VH", "VV"]).focalMedian(30, "circle", "meters")

            before = before_collection.map(smooth).median()
            after = after_collection.map(smooth).median()
            vh_diff = before.select("VH").subtract(after.select("VH"))
            vv_diff = before.select("VV").subtract(after.select("VV"))

            land = (
                ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
                .select("occurrence")
                .unmask(0)
                .lt(_PERMANENT_WATER_OCCURRENCE)
            )
            water = (
                vh_diff.gt(_VH_THRESHOLD_DB)
                .And(vv_diff.gt(_VV_THRESHOLD_DB))
                .And(after.select("VH").lt(_WATER_VH_MAX_DB))
                .And(land)
            )
            stats = ee.Dictionary(
                {
                    "area": water.multiply(ee.Image.pixelArea())
                    .reduceRegion(
                        ee.Reducer.sum(),
                        region,
                        _ANALYSIS_SCALE_M,
                        maxPixels=1e10,
                        tileScale=4,
                    )
                    .get("VH"),
                    "diff": vh_diff.addBands(vv_diff)
                    .updateMask(land)
                    .reduceRegion(
                        ee.Reducer.mean(),
                        region,
                        _ANALYSIS_SCALE_M,
                        maxPixels=1e10,
                        tileScale=4,
                    ),
                }
            ).getInfo()
            area_km2 = (stats.get("area") or 0) / 1e6
            diff = stats.get("diff") or {}
            confidence = _confidence_from_sar_margins(diff.get("VH"), diff.get("VV"))

            return {
                "district": label,
                "water_detected": area_km2 >= _MIN_FLOOD_KM2,
                "flood_extent_km2": round(area_km2, 2),
                "acquisition_date": f"{after_start} to {after_end}",
                "baseline_date": f"{baseline_start} to {baseline_end}",
                "analysis_area_km2": round(
                    (2 * radius_deg * 111.32) ** 2 * np.cos(np.radians(lat)), 1
                ),
                "source": "Sentinel-1 SAR",
                "confidence": confidence,
            }

        except Exception as e:
            logger.error(f"Sentinel-1 processing failed: {e}")
            return self._unavailable(label, f"processing failed: {type(e).__name__}")

    def _unavailable(self, district: str, reason: str) -> Dict:
        """No Sentinel-1 reading: no Earth Engine, no image in the last 12
        days (Ghana is imaged every 6-12 days), or a processing error.

        Reports "unavailable" with no detection and no area. A warning
        system must not show a satellite reading it does not have:
        risk decisions only ever count source == "Sentinel-1 SAR", but
        random values here were still displayed on the dashboard.
        """
        return {
            "district": district,
            "water_detected": False,
            "flood_extent_km2": None,
            "acquisition_date": None,
            "baseline_date": None,
            "source": "Sentinel-1 (unavailable)",
            "confidence": 0,
            "reason": reason,
        }


# Singleton instance
sentinel_processor = SentinelProcessor()
