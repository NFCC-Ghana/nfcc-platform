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
from typing import Optional

import requests

logger = logging.getLogger("nfcc.hydrology.glofas_discharge")

_FLOOD_API_URL = "https://flood-api.open-meteo.com/v1/flood"

# A district counts as an "active flood zone" (GET /national/summary)
# when today's simulated river discharge is running well above its
# long-term seasonal mean for that day. 1.5x is an illustrative
# threshold, not a calibrated hydrological one - no flood-stage threshold
# per Ghana river exists publicly.
ELEVATED_DISCHARGE_RATIO = 1.5


def fetch_glofas_discharge_ratio(lat: float, lon: float) -> Optional[float]:
    """Real GloFAS-based river discharge, today's value relative to its
    own long-term seasonal mean - None if the API call failed or no
    river is resolved within Open-Meteo's 5km grid at this point (a
    documented limitation, Cape Coast hits this in practice)."""
    try:
        resp = requests.get(
            _FLOOD_API_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "river_discharge,river_discharge_mean",
                "forecast_days": 1,
            },
            timeout=8,
        )
        resp.raise_for_status()
        daily = resp.json().get("daily", {})
        discharge = daily.get("river_discharge", [])
        mean = daily.get("river_discharge_mean", [])
        # Open-Meteo returns null for either value at some coastal points
        # where no river is resolved within their 5km grid (documented
        # limitation, not an error) - Cape Coast hits this in practice.
        if not discharge or not mean:
            return None
        latest_discharge, latest_mean = discharge[-1], mean[-1]
        if latest_discharge is None or not latest_mean:
            return None
        return latest_discharge / latest_mean
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
