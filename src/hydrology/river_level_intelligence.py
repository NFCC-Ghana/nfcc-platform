"""Honest real-vs-unavailable river level disclosure.

src/hydrology/river_intelligence.py's get_river_status() - which feeds
src/hydrology/unified_intelligence.py's "river" block, which feeds
POST /situation's river_level_m field - is entirely
np.random.seed(hash(gauge_id))-fabricated: a sine wave plus small noise
around a static per-river threshold, with ZERO connection to any real
input (not even the real rainfall already available) and no disclosure
anywhere in what it returns. This is the same undisclosed-fabrication
pattern as src/hydrology/reservoir_intelligence.py and vra_telemetry.py,
just one this session's evidence-gathering work (src/api/routes/
decision_card.py's build_evidence) hadn't checked yet - despite having
shown it as real corroborating evidence ("River level: Xm") in every
Decision Card and evidence response built so far.

Real coverage exists for exactly one of the 9 tracked districts: Tamale,
via DAHITI's White Volta river station (target id 9087, ~45.5km from
Tamale - the nearest real satellite altimetry gauge). Checked the other
8 districts directly against DAHITI's get-nearest-target API: their
nearest real target is 80-140km away (Lake Volta or a distant river),
too far to honestly represent local conditions - those districts get
available=False rather than a fabricated number.

Deliberately reports water_surface_elevation_m (absolute elevation from
satellite altimetry, e.g. ~81m), NOT a replacement for the fake
current_level_m (a relative stage height compared against 2-4m warning/
danger thresholds) - these are different units on different scales, and
conflating them would produce a nonsensical comparison
("81m exceeds the 2.8m danger level"). This is real evidence in its own
right, not a drop-in fix for the old field's threshold system.

download-discharge (actual river discharge, m3/s - the more directly
useful hydrological quantity) returned 403 Permission Denied when tried
with this project's DAHITI key - that product requires a higher access
tier this registration doesn't have. Only water level is available here.
"""

import logging
import os
from datetime import datetime
from typing import Dict

import requests

logger = logging.getLogger("nfcc.hydrology.river_level_intelligence")

_DAHITI_API_URL = "https://dahiti.dgfi.tum.de/api/v2/download-water-level/"

# (river name, DAHITI target id, real distance in km from the district,
# confirmed live against DAHITI's get-nearest-target API) - only
# districts with a real target close enough to be meaningful are listed;
# the other 8 tracked districts intentionally have no entry here.
_DISTRICT_RIVER_COVERAGE = {
    "Tamale": ("White Volta", 9087, 45.5),
}


def get_river_level_for_district(district: str) -> Dict:
    """Real river water level for a district, or an honest
    available=False when no sufficiently close real gauge exists."""
    coverage = _DISTRICT_RIVER_COVERAGE.get(district)
    if coverage is None:
        return {
            "available": False,
            "reason": (
                "No real river gauge or satellite altimetry station close "
                "enough to represent local conditions for this district - "
                "checked directly against DAHITI's station network; the "
                "nearest real target is 80km+ away"
            ),
        }

    river_name, dahiti_id, distance_km = coverage
    api_key = os.getenv("DAHITI_API_KEY")
    if not api_key:
        return {
            "available": False,
            "reason": "DAHITI_API_KEY not configured",
        }

    try:
        resp = requests.get(
            _DAHITI_API_URL,
            params={"api_key": api_key, "dahiti_id": dahiti_id, "format": "json"},
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        readings = payload.get("data") or []
        if not readings:
            return {
                "available": False,
                "reason": f"DAHITI returned no readings for {river_name}",
            }
        latest = readings[-1]
        observation_date = latest.get("datetime")

        age_days = None
        stale = False
        if observation_date:
            try:
                age_days = (
                    datetime.utcnow() - datetime.fromisoformat(observation_date)
                ).days
                stale = age_days > 45
            except ValueError:
                pass

        return {
            "available": True,
            "river": river_name,
            "water_surface_elevation_m": latest.get("wse"),
            "uncertainty_m": latest.get("wse_u"),
            "observation_date": observation_date,
            "age_days": age_days,
            "stale": stale,
            "distance_km": distance_km,
            "source": "DAHITI satellite altimetry",
            "note": (
                f"Nearest real river gauge to {district} is {distance_km}km "
                "away - satellite altimetry, not real-time (10-35 day "
                "revisit interval plus 1-2 day processing delay)"
            ),
        }
    except Exception as e:
        logger.warning(f"DAHITI river level request failed: {e}")
        return {"available": False, "reason": f"DAHITI request failed: {e}"}
