"""Real GloFAS-based river discharge (Open-Meteo's Flood API) - real
river gauge data doesn't exist anywhere in this codebase;
src/hydrology/river_gauge_api.py's configured endpoint, hydrology.gov.gh,
doesn't resolve.

Extracted 2026-09-27 from src/api/routes/situation.py (where it
originally lived as a private helper backing GET /national/summary's
"active flood zone" flag) into its own module so
src/models/real_forecast_fusion.py could reuse the same real fetch and
the same real _ELEVATED_DISCHARGE_RATIO threshold without situation.py
and real_forecast_fusion.py importing from each other (situation.py also
needs to call into real_forecast_fusion.py to surface its result on
POST /situation - a genuine circular import otherwise).
"""

import logging
from datetime import date, timedelta
from functools import lru_cache
from statistics import median
from typing import List, Optional

import requests

logger = logging.getLogger("nfcc.hydrology.glofas_discharge")

_FLOOD_API_URL = "https://flood-api.open-meteo.com/v1/flood"

# A district counts as an "active flood zone" (GET /national/summary)
# when today's simulated river discharge is running well above its
# day-of-year median over the previous ten years. 1.5x is an illustrative
# threshold, not a calibrated hydrological one - no flood-stage threshold
# per Ghana river exists publicly.
ELEVATED_DISCHARGE_RATIO = 1.5


# Day-of-year climatology: the median of every day within +-15 days of
# today's date in the previous ~10 years of GloFAS reanalysis/forecast.
_CLIMATOLOGY_DAYS = 3650
_SEASON_HALF_WINDOW_DAYS = 15


def _seasonal_median(
    times: List[str], values: List[Optional[float]]
) -> Optional[float]:
    today = date.fromisoformat(times[-1])
    doy = today.timetuple().tm_yday
    ref = []
    for t, v in zip(times, values):
        d = date.fromisoformat(t)
        if v is None or (today - d).days < 365:
            continue
        gap = abs(d.timetuple().tm_yday - doy)
        if min(gap, 365 - gap) <= _SEASON_HALF_WINDOW_DAYS:
            ref.append(v)
    return median(ref) if len(ref) >= 30 else None


@lru_cache(maxsize=64)
def _cached_ratio(lat: float, lon: float, day: str) -> Optional[float]:
    end = date.fromisoformat(day)
    resp = requests.get(
        _FLOOD_API_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": "river_discharge",
            "start_date": (end - timedelta(days=_CLIMATOLOGY_DAYS)).isoformat(),
            "end_date": end.isoformat(),
        },
        timeout=20,
    )
    resp.raise_for_status()
    daily = resp.json().get("daily", {})
    times, values = daily.get("time") or [], daily.get("river_discharge") or []
    if not times or len(times) != len(values) or values[-1] is None:
        return None
    clim = _seasonal_median(times, values)
    if not clim:
        return None
    return values[-1] / clim


def fetch_glofas_discharge_ratio(lat: float, lon: float) -> Optional[float]:
    """Today's GloFAS discharge divided by its day-of-year median over the
    previous ten years at this point, or None when unavailable.

    This used to divide by the API's `river_discharge_mean` - which in the
    Open-Meteo Flood API is the mean of today's ENSEMBLE members, not a
    climatology - so the ratio was always about 1 and "elevated (>1.5x)"
    could practically never fire. Cached per point per day."""
    try:
        return _cached_ratio(round(lat, 4), round(lon, 4), date.today().isoformat())
    except Exception as e:
        logger.warning(f"Flood API call failed for ({lat},{lon}): {e}")
        return None


def is_discharge_elevated(lat: float, lon: float) -> Optional[bool]:
    """True if a district's real-time river discharge is elevated relative
    to its seasonal mean; None if the Flood API call failed."""
    ratio = fetch_glofas_discharge_ratio(lat, lon)
    if ratio is None:
        return None
    return ratio > ELEVATED_DISCHARGE_RATIO
