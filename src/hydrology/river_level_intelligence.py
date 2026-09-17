"""Honest real-vs-unavailable river level disclosure.

src/hydrology/river_intelligence.py's get_river_status() - which feeds
src/hydrology/unified_intelligence.py's "river" block, which used to feed
POST /situation's river_level_m field directly - is entirely
np.random.seed(hash(gauge_id))-fabricated: a sine wave plus small noise
around a static per-river threshold, with ZERO connection to any real
input (not even the real rainfall already available) and no disclosure
anywhere in what it returns. This is the same undisclosed-fabrication
pattern as src/hydrology/reservoir_intelligence.py and vra_telemetry.py,
just one this session's evidence-gathering work (src/api/routes/
decision_card.py's build_evidence) hadn't checked until directly traced.

Real coverage exists for exactly one of the 9 tracked districts: Tamale,
via DAHITI's White Volta river station (target id 9087, ~45.5km from
Tamale - the nearest real satellite altimetry gauge). Checked the other
8 districts directly against DAHITI's get-nearest-target API (by
district centroid AND by each real dam's own coordinates - Bui, Weija,
Barekese, Owabi, Tono, Vea): all come back 65km+ away, or (Weija/Densu,
~120km+) simply have no altimetry-resolvable water body nearby at all -
small reservoirs like Weija (5.5M m3) are physically too small for
satellite altimetry's ground-track resolution, not merely "unconfigured".
Those districts get available=False with the real reason rather than a
fabricated number.

Reports water_surface_elevation_m (absolute elevation from satellite
altimetry, e.g. ~81m) AND a derived level_above_baseline_m - baseline is
the real 5th percentile of this river's own full historical DAHITI
series (531 readings back to 2002), so "how high above typical low" is
computed from actual measured history, not invented. warning_level_m/
danger_level_m/flood_stage_m are likewise the real 75th/90th/95th
percentiles of that same series, relative to baseline - replacing
river_intelligence.py's entirely-invented, disconnected-from-any-real-
measurement 2.0/2.8/3.2m thresholds with ones derived from this specific
river's actual measured range.

download-discharge (actual river discharge, m3/s - the more directly
useful hydrological quantity) returned 403 Permission Denied when tried
with this project's DAHITI key - that product requires a higher access
tier this registration doesn't have. Only water level is available here.
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

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

_UNAVAILABLE_REASONS = {
    # Districts checked against their own real dam's coordinates
    # specifically (not just district centroid) - see module docstring.
    "Accra West": (
        "Weija Dam (Densu River, the real reservoir nearest this "
        "district) is only ~5.5M m3 - too small for satellite "
        "altimetry's ground-track resolution to register at all. "
        "Nearest real DAHITI target of any kind is Lake Volta, 122km away."
    ),
}
_DEFAULT_UNAVAILABLE_REASON = (
    "No real river gauge or satellite altimetry station close enough to "
    "represent local conditions for this district - checked directly "
    "against DAHITI's station network (both district centroid and the "
    "nearest real dam's own coordinates); the nearest real target is "
    "65km+ away"
)


def _compute_relative_thresholds(readings: List[dict]) -> Optional[Dict[str, float]]:
    """Real, data-derived reference levels from this river's own full
    historical DAHITI series - not arbitrary constants. baseline = 5th
    percentile (typical dry-season low); warning/danger/flood_stage =
    75th/90th/95th percentiles of the same real distribution, expressed
    relative to baseline."""
    elevations = sorted(r["wse"] for r in readings if r.get("wse") is not None)
    n = len(elevations)
    if n < 20:
        return None

    def pct(p: float) -> float:
        return elevations[min(int(n * p), n - 1)]

    baseline = pct(0.05)
    return {
        "baseline_m": round(baseline, 3),
        "warning_level_m": round(pct(0.75) - baseline, 3),
        "danger_level_m": round(pct(0.90) - baseline, 3),
        "flood_stage_m": round(pct(0.95) - baseline, 3),
    }


def get_river_level_for_district(district: str) -> Dict:
    """Real river water level for a district, or an honest
    available=False when no sufficiently close real gauge exists."""
    coverage = _DISTRICT_RIVER_COVERAGE.get(district)
    if coverage is None:
        return {
            "available": False,
            "reason": _UNAVAILABLE_REASONS.get(district, _DEFAULT_UNAVAILABLE_REASON),
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
        elevation = latest.get("wse")

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

        thresholds = _compute_relative_thresholds(readings)
        level_above_baseline_m = None
        status = "UNKNOWN"
        if thresholds and elevation is not None:
            level_above_baseline_m = round(elevation - thresholds["baseline_m"], 3)
            if level_above_baseline_m >= thresholds["flood_stage_m"]:
                status = "FLOOD"
            elif level_above_baseline_m >= thresholds["danger_level_m"]:
                status = "DANGER"
            elif level_above_baseline_m >= thresholds["warning_level_m"]:
                status = "WARNING"
            else:
                status = "NORMAL"

        result = {
            "available": True,
            "river": river_name,
            "water_surface_elevation_m": elevation,
            "level_above_baseline_m": level_above_baseline_m,
            "status": status,
            "uncertainty_m": latest.get("wse_u"),
            "observation_date": observation_date,
            "age_days": age_days,
            "stale": stale,
            "distance_km": distance_km,
            "source": "DAHITI satellite altimetry",
            "note": (
                f"Nearest real river gauge to {district} is {distance_km}km "
                "away - satellite altimetry, not real-time (10-35 day "
                "revisit interval plus 1-2 day processing delay). Level "
                "shown is height above this river's own real historical "
                "5th-percentile low, not an absolute stage against a "
                "physical gauge datum."
            ),
        }
        if thresholds:
            result.update(thresholds)
        return result
    except Exception as e:
        logger.warning(f"DAHITI river level request failed: {e}")
        return {"available": False, "reason": f"DAHITI request failed: {e}"}
