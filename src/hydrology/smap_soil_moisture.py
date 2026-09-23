"""Real soil moisture via NASA SMAP (Soil Moisture Active Passive),
replacing src/hydrology/soil_moisture.py's get_soil_moisture() - which
generates its "saturation_percent" via
random.seed(hash(f"{district}_{date}")) with zero connection to any
real input, the same undisclosed-fabrication pattern already found and
fixed this session for river levels, satellite confidence, and the
dashboard's "Data Sources" panel.

Uses NASA/SMAP/SPL4SMGP/008 (SMAP L4 Global 3-hourly 9-km Surface and
Root Zone Soil Moisture) via Google Earth Engine - real, active,
public-domain satellite data, available since 2015-03-31. 3-hourly
cadence is a genuinely low-latency real signal (unlike CHIRPS's
near-real-time product, which was found this session to lag 18+ days
in practice) - soil moisture responds to and helps corroborate real
antecedent rainfall accumulation.

Reports the real measured volumetric water content (m3/m3, the
band's native, physically meaningful unit) rather than inventing a
"percent saturation" - that would require each location's real soil
porosity/field capacity, which isn't available here. A rough 0-100
`saturation_percent_estimate` is also given (VWC as a percentage of
the sensor's 0-0.9 measurement range), explicitly disclosed as an
approximation of sensor range, not of this specific soil's own
saturation point, so it isn't quietly mistaken for the same precision
as the real VWC figure it's derived from.
"""

import logging
import time
from datetime import date, timedelta
from typing import Dict, Tuple

from src.exposure.districts import get_district
from src.hydrology.ee_auth import initialize_earth_engine

logger = logging.getLogger("nfcc.hydrology.smap_soil_moisture")

_SMAP_COLLECTION = "NASA/SMAP/SPL4SMGP/008"
_SMAP_SCALE_M = 11000  # native ~11km grid

# SMAP L4 has ~2-3 day latency in practice for the public EE mirror on
# top of its real 3-hourly cadence; widen the search window well past
# that so a real recent image is still found (same lesson learned this
# session with CHIRPS's near-real-time product needing a 60-day window
# despite being nominally "near-real-time").
_FETCH_WINDOW_DAYS = 10
_STALE_AFTER_HOURS = 72

# The sensor's own documented measurement range (0-0.9 m3/m3) - used
# only to express VWC as a rough percentage of sensor range, not as a
# claim about this soil's actual saturation point.
_SENSOR_MAX_VWC = 0.9

# Per-district in-memory cache, keyed by district name -> (fetched_at
# unix time, result dict). A codebase audit found this made a live,
# synchronous Earth Engine query on every single /situation call with
# no caching at all - real waste (SMAP's own data only refreshes every
# few hours) and a real quota/latency risk now that the kiosk view polls
# /situation every 90 seconds. 3 hours matches SMAP L4's own native
# refresh cadence: caching any longer would risk serving data older than
# the source itself updates on, any shorter buys no real freshness given
# the ~2-3 day EE mirror latency already noted above. In-memory (not
# Redis/a DB) is a deliberate, honest limitation: it resets on every
# Cloud Run cold start/new revision and isn't shared across instances if
# Cloud Run ever scales beyond one - acceptable here because the cost of
# a cache miss is just one real Earth Engine call, never stale-looking
# fabricated data.
_CACHE_TTL_SECONDS = 3 * 3600
_cache: Dict[str, Tuple[float, Dict]] = {}


def get_soil_moisture_for_district(district: str) -> Dict:
    """Real root-zone + surface soil moisture (volumetric water
    content) for a district, or an honest available=False - never a
    fabricated fallback value. Cached per district for
    _CACHE_TTL_SECONDS - see that constant's comment for why."""
    cached = _cache.get(district)
    if cached is not None:
        fetched_at, result = cached
        if time.time() - fetched_at < _CACHE_TTL_SECONDS:
            return result

    result = _fetch_soil_moisture_for_district(district)
    # Only cache a real, successful reading - never cache an
    # available=False response, so a transient Earth Engine outage
    # doesn't get "stuck" honestly-unavailable for a full 3 hours once
    # EE recovers on the very next request.
    if result.get("available"):
        _cache[district] = (time.time(), result)
    return result


def _fetch_soil_moisture_for_district(district: str) -> Dict:
    """The real, uncached Earth Engine fetch - see
    get_soil_moisture_for_district for the caching wrapper every real
    caller should use instead of this."""
    district_info = get_district(district)
    if district_info is None:
        return {
            "district": district,
            "available": False,
            "reason": f"'{district}' is not one of the 9 districts with real coordinates registered",
        }

    if not initialize_earth_engine():
        return {
            "district": district,
            "available": False,
            "reason": "Earth Engine unavailable",
        }

    import ee

    try:
        point = ee.Geometry.Point(district_info.lon, district_info.lat)
        end_date = (date.today() + timedelta(days=1)).isoformat()
        start_date = (date.today() - timedelta(days=_FETCH_WINDOW_DAYS)).isoformat()
        collection = (
            ee.ImageCollection(_SMAP_COLLECTION)
            .filterDate(start_date, end_date)
            .select(["sm_surface", "sm_rootzone"])
            .sort("system:time_start", False)
        )
        latest = collection.first()
        if latest is None:
            return {
                "district": district,
                "available": False,
                "reason": f"No real SMAP image in the last {_FETCH_WINDOW_DAYS} days",
            }

        values = latest.reduceRegion(
            reducer=ee.Reducer.first(), geometry=point, scale=_SMAP_SCALE_M
        ).getInfo()
        surface_vwc = values.get("sm_surface")
        rootzone_vwc = values.get("sm_rootzone")
        timestamp_ms = latest.get("system:time_start").getInfo()

        if rootzone_vwc is None and surface_vwc is None:
            return {
                "district": district,
                "available": False,
                "reason": "SMAP image found but no valid pixel at this location",
            }

        from datetime import datetime

        observation_date = datetime.utcfromtimestamp(timestamp_ms / 1000)
        age_hours = (datetime.utcnow() - observation_date).total_seconds() / 3600.0
        stale = age_hours > _STALE_AFTER_HOURS

        primary_vwc = rootzone_vwc if rootzone_vwc is not None else surface_vwc
        saturation_percent_estimate = (
            round(min(100.0, 100.0 * primary_vwc / _SENSOR_MAX_VWC), 1)
            if primary_vwc is not None
            else None
        )

        return {
            "district": district,
            "available": True,
            "surface_vwc_m3m3": (
                round(surface_vwc, 3) if surface_vwc is not None else None
            ),
            "root_zone_vwc_m3m3": (
                round(rootzone_vwc, 3) if rootzone_vwc is not None else None
            ),
            "saturation_percent_estimate": saturation_percent_estimate,
            "observation_date": observation_date.isoformat(),
            "age_hours": round(age_hours, 1),
            "stale": stale,
            "source": "NASA SMAP L4 (SPL4SMGP.008), real satellite soil moisture",
            "note": (
                "saturation_percent_estimate is root-zone VWC expressed as a "
                "percentage of the sensor's 0-0.9 m3/m3 measurement range, "
                "not this soil's own specific saturation point (real "
                "porosity data isn't available) - a rough indicator, not a "
                "precise percentage."
            ),
        }
    except Exception as e:
        logger.warning(f"SMAP fetch failed for {district}: {e}")
        return {
            "district": district,
            "available": False,
            "reason": f"SMAP request failed: {e}",
        }
